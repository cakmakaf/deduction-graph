"""Graph routing.

Tests the edges, not the prose. The critical assertion is that no path reaches
retrieval or computation without a resolved scope.
"""

from __future__ import annotations

import pytest

from deduction_graph.graph.build import (
    route_after_scope,
    route_after_selfcheck,
    run_sequential,
)
from deduction_graph.graph.nodes.retrieve import set_retriever
from deduction_graph.graph.nodes.scope import (
    detect_out_of_scope_jurisdiction,
    detect_provisions,
    detect_tax_year,
)
from deduction_graph.graph.state import GraphState, Outcome
from deduction_graph.types import FilingStatus, Provision, TaxpayerProfile, money


@pytest.fixture(autouse=True)
def _wire_retriever(scoped_retriever):
    set_retriever(scoped_retriever)


def test_detect_tax_year_does_not_default_to_current_year():
    """"This year" is ambiguous during filing season. Never guess."""
    assert detect_tax_year("what is my standard deduction") is None
    assert detect_tax_year("what can I deduct this year") is None
    assert detect_tax_year("standard deduction for 2025") == 2025


def test_detect_provisions_keyword_pass():
    assert Provision.SALT in detect_provisions("how much state and local tax can I deduct")
    assert Provision.HSA in detect_provisions("what is my HSA limit")
    assert detect_provisions("what is the weather") == ()


def test_jurisdiction_detection_does_not_fire_on_federal_salt():
    """SALT is a federal provision. This check must not swallow it."""
    assert detect_out_of_scope_jurisdiction("state and local tax deduction 2024") is None
    assert detect_out_of_scope_jurisdiction("California standard deduction") == "california"


def test_missing_year_asks_rather_than_answers():
    state = run_sequential(GraphState(question="What is my standard deduction?"))
    assert state.outcome is Outcome.CLARIFICATION_NEEDED
    assert "tax year" in (state.final_answer or "").lower()


def test_unsupported_year_asks_rather_than_falling_back():
    state = run_sequential(
        GraphState(question="What is the standard deduction for a single filer in 2027?")
    )
    assert state.outcome is Outcome.CLARIFICATION_NEEDED
    assert "2027" in (state.final_answer or "")


def test_state_question_is_refused():
    state = run_sequential(
        GraphState(question="What is the California standard deduction for 2025?")
    )
    assert state.outcome is Outcome.CLARIFICATION_NEEDED


def test_resolved_question_runs_end_to_end_without_an_llm():
    """The degraded path must produce a correct, cited answer, not an error."""
    profile = TaxpayerProfile(
        profile_id="g-e2e",
        tax_year=2024,
        filing_status=FilingStatus.SINGLE,
        agi=money(80000),
        age=40,
        medical_expenses=money(14000),
    )
    state = run_sequential(
        GraphState(
            question="How much of my medical expenses can I deduct in 2024?",
            profile=profile,
        )
    )
    assert state.outcome in {Outcome.ANSWERED, Outcome.ESCALATED}
    assert state.scope.tax_year == 2024
    assert state.computation_trail
    assert "8,000.00" in (state.final_answer or "")


def test_routing_functions():
    unresolved = GraphState(question="q")
    assert route_after_scope(unresolved) == "clarify"

    checked = GraphState(question="q")
    checked.groundedness_passed = False
    assert route_after_selfcheck(checked) == "escalate"
    checked.groundedness_passed = True
    assert route_after_selfcheck(checked) == "finalize"


def test_every_node_writes_a_trace_entry():
    profile = TaxpayerProfile(
        profile_id="g-trace",
        tax_year=2024,
        filing_status=FilingStatus.SINGLE,
        agi=money(80000),
        medical_expenses=money(14000),
    )
    state = run_sequential(
        GraphState(question="medical expense deduction 2024", profile=profile)
    )
    nodes = [e["node"] for e in state.trace]
    for expected in ("intake", "scope", "retrieve", "compute", "synthesize", "selfcheck"):
        assert expected in nodes, f"{expected} left no trace entry"


def test_escalation_attaches_partial_work():
    """Escalation must hand off the work, not discard it."""
    from deduction_graph.graph.nodes.escalate import escalate_node
    from deduction_graph.types import ComputationStep

    state = GraphState(question="q")
    state.check_notes = ["ungrounded figure"]
    state.computation_trail = [
        ComputationStep(label="Step one", detail="did a thing", value=money(100))
    ]
    state = escalate_node(state)
    assert state.outcome is Outcome.ESCALATED
    assert "Step one" in (state.final_answer or "")
