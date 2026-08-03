"""The self-check guard.

Deterministic by design: the property being verified is mechanical, and a
deterministic check cannot itself hallucinate.
"""

from __future__ import annotations

from deduction_graph.graph.nodes.selfcheck import extract_amounts, selfcheck_node
from deduction_graph.graph.state import GraphState
from deduction_graph.types import ComputationStep, Scope, money


def _state(answer: str) -> GraphState:
    state = GraphState(question="q")
    state.scope = Scope(tax_year=2024, provisions=())
    state.computation_trail = [
        ComputationStep(label="Base", detail="base amount", value=money("14600.00")),
        ComputationStep(label="Total", detail="total", value=money("18500.00")),
    ]
    state.draft_answer = answer
    return state


def test_extract_amounts_normalizes():
    assert extract_amounts("$14,600 and $18,500.00") == {"14600.00", "18500.00"}


def test_grounded_answer_passes():
    state = selfcheck_node(_state("For 2024 your deduction is $18,500.00."))
    assert state.groundedness_passed


def test_invented_figure_is_caught():
    state = selfcheck_node(_state("For 2024 your deduction is $13,850.00."))
    assert not state.groundedness_passed
    assert any("13850.00" in n for n in state.check_notes)


def test_missing_tax_year_is_caught():
    """An unqualified figure is not usable, so it does not pass."""
    state = selfcheck_node(_state("Your deduction is $14,600."))
    assert not state.groundedness_passed
    assert any("tax year" in n for n in state.check_notes)


def test_figure_quoted_from_a_retrieved_excerpt_is_grounded():
    """A number quoted from a cited authority is grounded, not invented.

    Found by running the CLI: the guard originally rejected answers that quoted
    a figure straight out of a retrieved passage, because it only accepted
    computed figures. Both are legitimate grounding sources.
    """
    from deduction_graph.retrieval.schema import RetrievedChunk
    from evals.datasets.fixture_corpus import FIXTURE_CHUNKS

    chunk = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2024:sd-single"
    )
    state = _state("For 2024 the single standard deduction is $14,600.")
    state.computation_trail = []
    state.retrieved = [RetrievedChunk(chunk=chunk, score=1.0)]
    state = selfcheck_node(state)
    assert state.groundedness_passed, state.check_notes


def test_figure_in_neither_source_is_still_caught():
    from deduction_graph.retrieval.schema import RetrievedChunk
    from evals.datasets.fixture_corpus import FIXTURE_CHUNKS

    chunk = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2024:sd-single"
    )
    state = _state("For 2024 the single standard deduction is $13,850.")
    state.computation_trail = []
    state.retrieved = [RetrievedChunk(chunk=chunk, score=1.0)]
    state = selfcheck_node(state)
    assert not state.groundedness_passed


def test_undisclosed_unverified_parameters_are_caught():
    state = _state("For 2024 your deduction is $14,600.00.")
    state.unverified_parameters = ["standard_deduction.base.single.amount"]
    state = selfcheck_node(state)
    assert not state.groundedness_passed
    assert any("unverified" in n.lower() for n in state.check_notes)
