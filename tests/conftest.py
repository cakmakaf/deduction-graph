from __future__ import annotations

import pytest

from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore
from evals.datasets.fixture_corpus import FIXTURE_CHUNKS


@pytest.fixture
def scoped_retriever() -> HybridRetriever:
    store = InMemoryStore()
    store.add(list(FIXTURE_CHUNKS))
    return HybridRetriever(sparse=store)
