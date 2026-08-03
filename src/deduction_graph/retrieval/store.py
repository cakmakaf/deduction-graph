"""Vector store abstraction.

A Protocol plus an in-memory reference implementation. The in-memory store is not
a throwaway: it is what the retrieval and scope-precision eval layers run
against in CI, so the whole harness works with no external service and no API
key. That is a deliberate choice for a public repository, since a reader who
cannot run the evals cannot check the claims.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol, runtime_checkable

from deduction_graph.retrieval import filters
from deduction_graph.retrieval.schema import Chunk, RetrievedChunk
from deduction_graph.types import Scope

_TOKEN = re.compile(r"[a-z0-9$.,%]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@runtime_checkable
class VectorStore(Protocol):
    def add(self, chunks: list[Chunk]) -> None: ...

    def search(
        self, query: str, scope: Scope, *, k: int = 8
    ) -> list[RetrievedChunk]: ...

    def count(self) -> int: ...


class InMemoryStore:
    """BM25 over scope-filtered chunks.

    Sparse-only by design. It exists to make scope filtering testable without a
    model download, not to be the production retriever. See ChromaStore for that.
    """

    def __init__(self, *, k1: float = 1.5, b: float = 0.75):
        self._chunks: list[Chunk] = []
        self.k1 = k1
        self.b = b

    def add(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    def count(self) -> int:
        return len(self._chunks)

    def search(self, query: str, scope: Scope, *, k: int = 8) -> list[RetrievedChunk]:
        # Filter FIRST. This ordering is the entire point of the architecture:
        # out-of-scope chunks never enter the candidate set, so they cannot be
        # ranked into the answer no matter how similar their wording is.
        candidates = [c for c in self._chunks if filters.passes(c, scope)]
        if not candidates:
            return []

        docs = [tokenize(c.text) for c in candidates]
        avgdl = sum(len(d) for d in docs) / len(docs)
        n = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(d))

        q_terms = tokenize(query)
        scored: list[RetrievedChunk] = []
        for chunk, doc in zip(candidates, docs, strict=True):
            tf = Counter(doc)
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                num = tf[term] * (self.k1 + 1)
                den = tf[term] + self.k1 * (1 - self.b + self.b * len(doc) / avgdl)
                score += idf * num / den
            if score > 0:
                scored.append(
                    RetrievedChunk(chunk=chunk, score=score, retrieval_method="sparse")
                )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]


class ChromaStore:
    """Dense retrieval over a local Chroma collection.

    TODO(milestone-2): implement. The contract that matters is already fixed by
    the Protocol above, and `filters.to_store_filter(scope)` must be passed as
    the `where` clause on every query. There is no code path that queries without
    it, and adding one would be the single most damaging change possible to this
    repository.
    """

    def __init__(self, collection_name: str = "deduction_graph", persist_dir: str | None = None):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        raise NotImplementedError(
            "ChromaStore is scaffolded but not implemented. See milestone 2 in "
            "docs/PROPOSAL.md. Use InMemoryStore until then."
        )

    def add(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    def search(self, query: str, scope: Scope, *, k: int = 8) -> list[RetrievedChunk]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class NaiveStore(InMemoryStore):
    """Deliberately unscoped retrieval, used ONLY by the ablation study.

    This is the baseline the headline result argues against: semantic or lexical
    similarity with no metadata pre-filter, which is how most RAG systems are
    built. It exists so the comparison in milestone 7 is measured rather than
    asserted.

    Never wire this into the graph.
    """

    def search(self, query: str, scope: Scope, *, k: int = 8) -> list[RetrievedChunk]:
        if not self._chunks:
            return []
        docs = [tokenize(c.text) for c in self._chunks]
        avgdl = sum(len(d) for d in docs) / len(docs)
        n = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(d))

        q_terms = tokenize(query)
        scored: list[RetrievedChunk] = []
        for chunk, doc in zip(self._chunks, docs, strict=True):
            tf = Counter(doc)
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                num = tf[term] * (self.k1 + 1)
                den = tf[term] + self.k1 * (1 - self.b + self.b * len(doc) / avgdl)
                score += idf * num / den
            if score > 0:
                scored.append(
                    RetrievedChunk(chunk=chunk, score=score, retrieval_method="naive")
                )
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]
