"""Layer 4: groundedness.

Every dollar figure in a produced answer must be grounded, in the computation
trail or verbatim in a retrieved excerpt. Reuses the same deterministic check the
self-check node runs, deliberately: the eval and the runtime guard should not be
able to disagree.

Gate: 1.0. An ungrounded figure in a tax answer is not a quality issue, it is a
fabricated number.
"""

from __future__ import annotations

from deduction_graph.graph.nodes.selfcheck import extract_amounts, selfcheck_node
from deduction_graph.graph.state import GraphState
from deduction_graph.rules import load_rules
from deduction_graph.tools.registry import BY_NAME
from deduction_graph.types import Provision, Scope
from evals.datasets.golden_profiles import GOLDEN_CASES
from evals.result import CaseResult, LayerResult

# Answers that a broken synthesis step might plausibly produce. Injected directly
# so this layer runs with no LLM and still tests the guard.
INJECTED_UNGROUNDED = (
    ("inj-invented-figure", "Your standard deduction for 2024 is $13,850."),
    ("inj-missing-year", "Your standard deduction is $14,600."),
)


def _state_for(case) -> GraphState:
    tool = BY_NAME[case.tool]
    result = tool(case.profile, load_rules(case.profile.tax_year))
    state = GraphState(question="(eval)", profile=case.profile)
    state.scope = Scope(
        tax_year=case.profile.tax_year,
        filing_status=case.profile.filing_status,
        provisions=(Provision(result.provision),),
    )
    state.tool_results = [result]
    state.computation_trail = list(result.steps)
    state.unverified_parameters = list(result.unverified_parameters)
    return state


def run_groundedness() -> LayerResult:
    cases: list[CaseResult] = []

    # Positive control: an answer built only from trail figures must pass.
    for case in GOLDEN_CASES[:10]:
        state = _state_for(case)
        state.draft_answer = (
            f"For tax year {case.profile.tax_year}, the amount is "
            f"${case.expected:,.2f}. These figures are drafted and need "
            "verification against the cited source."
        )
        state = selfcheck_node(state)
        cases.append(
            CaseResult(
                case_id=f"grounded-{case.case_id}",
                passed=bool(state.groundedness_passed),
                detail="; ".join(state.check_notes),
            )
        )

    # Negative control: the guard must REJECT these. Passing here means the
    # check correctly refused, so a layer that silently stopped working shows up
    # as a failure rather than as a suspiciously perfect score.
    base = GOLDEN_CASES[0]
    for case_id, bad_answer in INJECTED_UNGROUNDED:
        state = _state_for(base)
        state.draft_answer = bad_answer
        state = selfcheck_node(state)
        caught = not state.groundedness_passed
        cases.append(
            CaseResult(
                case_id=case_id,
                passed=caught,
                detail="" if caught else "guard failed to reject an ungrounded answer",
            )
        )

    return LayerResult(
        layer="groundedness",
        cases=tuple(cases),
        gate_threshold=1.0,
        metrics={"case_count": float(len(cases))},
    )
