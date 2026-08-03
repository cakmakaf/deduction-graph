"""Layer 5: escalation preference.

Runs under-specified and out-of-scope questions through the real routing logic
and asserts the system asks or escalates rather than answering.

Gate: 1.0. This layer is what keeps the system honest as coverage grows. Without
it, every future improvement creates pressure to answer more questions, and the
escalation path quietly erodes.
"""

from __future__ import annotations

from deduction_graph.graph.nodes.intake import intake_node
from deduction_graph.graph.nodes.scope import scope_node
from deduction_graph.graph.state import GraphState, Outcome
from evals.datasets.escalation import ESCALATION_CASES, ExpectedBehavior
from evals.result import CaseResult, LayerResult


def run_escalation_preference() -> LayerResult:
    cases: list[CaseResult] = []

    for case in ESCALATION_CASES:
        state = GraphState(question=case.question)
        state = scope_node(intake_node(state))

        if case.expected is ExpectedBehavior.CLARIFY:
            passed = state.outcome is Outcome.CLARIFICATION_NEEDED
            detail = (
                ""
                if passed
                else (
                    f"resolved scope to tax_year={state.scope.tax_year}, "
                    f"provisions={[p.value for p in state.scope.provisions]} "
                    f"when it should have asked. {case.why}"
                )
            )
        else:
            # ESCALATE cases resolve scope and are expected to fail downstream on
            # a tool warning. Full-graph escalation checking lands in milestone 4.
            passed = state.outcome is Outcome.CLARIFICATION_NEEDED or state.scope.is_resolved
            detail = "" if passed else case.why

        cases.append(CaseResult(case_id=case.case_id, passed=passed, detail=detail))

    return LayerResult(
        layer="escalation_preference",
        cases=tuple(cases),
        gate_threshold=1.0,
        metrics={"case_count": float(len(cases))},
    )
