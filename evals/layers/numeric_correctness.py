"""Layer 3: numeric correctness.

Exact match against hand-computed golden values. No tolerance. A tax figure is
either right or it is wrong, and a tolerance band is a way of not noticing which.

Gate: 1.0. Any failure blocks the release.
"""

from __future__ import annotations

from deduction_graph.rules import load_rules
from deduction_graph.tools.registry import BY_NAME
from evals.datasets.golden_profiles import GOLDEN_CASES
from evals.result import CaseResult, LayerResult


def run_numeric_correctness() -> LayerResult:
    cases: list[CaseResult] = []
    for case in GOLDEN_CASES:
        tool = BY_NAME[case.tool]
        try:
            result = tool(case.profile, load_rules(case.profile.tax_year))
            actual = result.value.amount
            passed = actual == case.expected
            detail = (
                ""
                if passed
                else f"expected {case.expected}, got {actual}. {case.rationale}"
            )
        except Exception as exc:
            passed = False
            detail = f"{type(exc).__name__}: {exc}"
        cases.append(CaseResult(case_id=case.case_id, passed=passed, detail=detail))

    return LayerResult(
        layer="numeric_correctness",
        cases=tuple(cases),
        gate_threshold=1.0,
        metrics={"case_count": float(len(cases))},
    )
