"""Cross-encoder reranking.

TODO(milestone-2): implement with a local cross-encoder so the repository stays
runnable offline.

Note on why reranking is necessary but not sufficient: a reranker only reorders
the candidate set. It cannot recover from a candidate set that contains the wrong
tax year, and it will happily rank a well-worded wrong-year passage first. The
scope pre-filter is what makes that impossible; the reranker is what improves
ordering among correctly scoped candidates. Both, in that order.
"""

from __future__ import annotations

from deduction_graph.retrieval.schema import RetrievedChunk


class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        raise NotImplementedError(
            "CrossEncoderReranker is scaffolded but not implemented. See milestone 2."
        )


class IdentityReranker:
    """Pass-through, so the pipeline is runnable before the reranker exists."""

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        return candidates
