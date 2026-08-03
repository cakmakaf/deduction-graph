"""Retrieval.

Writes: retrieved.

Thin by design. All the interesting behavior lives in the scope filter and the
retriever, both of which are independently testable. This node only wires them
together and records what came back.
"""

from __future__ import annotations

from deduction_graph.graph.state import GraphState
from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore

_DEFAULT_RETRIEVER: HybridRetriever | None = None


def set_retriever(retriever: HybridRetriever) -> None:
    """Injection point, used by tests, evals, and the API startup hook."""
    global _DEFAULT_RETRIEVER
    _DEFAULT_RETRIEVER = retriever


def get_retriever() -> HybridRetriever:
    global _DEFAULT_RETRIEVER
    if _DEFAULT_RETRIEVER is None:
        _DEFAULT_RETRIEVER = HybridRetriever(sparse=InMemoryStore())
    return _DEFAULT_RETRIEVER


def retrieve_node(state: GraphState, *, k: int = 8) -> GraphState:
    question = state.rewritten_question or state.question
    # Raises ScopeNotResolvedError if scope is unresolved. That is intentional:
    # the graph edge from scope_node should have routed to clarification, so
    # reaching here unresolved is a wiring bug and should be loud.
    results = get_retriever().retrieve(question, state.scope, k=k)
    state.retrieved = results
    state.record(
        "retrieve",
        k=k,
        returned=len(results),
        chunk_ids=[r.chunk.metadata.chunk_id for r in results],
        tax_years_returned=sorted({r.chunk.metadata.tax_year for r in results}),
    )
    return state
