"""Hybrid dense plus sparse retrieval with reciprocal rank fusion.

TODO(milestone-2): wire the dense side to ChromaStore. The fusion logic and the
scope-filter contract are already fixed, so the remaining work is embedding and
indexing, not architecture.
"""

from __future__ import annotations

from deduction_graph.retrieval.schema import RetrievedChunk
from deduction_graph.retrieval.store import VectorStore
from deduction_graph.types import Scope

RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[RetrievedChunk]], *, k: int = RRF_K
) -> list[RetrievedChunk]:
    """Fuse multiple ranked lists without needing comparable score scales.

    Chosen over score normalization because BM25 scores and cosine similarities
    are not on the same scale and normalizing them introduces a tuning parameter
    that has to be re-tuned whenever the corpus changes.
    """
    scores: dict[str, float] = {}
    best: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            cid = item.chunk.metadata.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            if cid not in best:
                best[cid] = item
    fused = [
        best[cid].model_copy(update={"score": score, "retrieval_method": "hybrid"})
        for cid, score in scores.items()
    ]
    fused.sort(key=lambda r: r.score, reverse=True)
    return fused


class HybridRetriever:
    def __init__(
        self,
        sparse: VectorStore,
        dense: VectorStore | None = None,
        reranker: "object | None" = None,
    ):
        self.sparse = sparse
        self.dense = dense
        self.reranker = reranker

    def retrieve(
        self, query: str, scope: Scope, *, k: int = 8, fetch_k: int = 24
    ) -> list[RetrievedChunk]:
        rankings = [self.sparse.search(query, scope, k=fetch_k)]
        if self.dense is not None:
            rankings.append(self.dense.search(query, scope, k=fetch_k))

        fused = reciprocal_rank_fusion(rankings)

        if self.reranker is not None:
            fused = self.reranker.rerank(query, fused)  # type: ignore[attr-defined]

        return fused[:k]
