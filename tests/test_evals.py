"""Meta-tests on the harness itself.

A harness that silently stops testing is worse than no harness, because it
reports green. These assert the layers actually run cases and that the ablation
demonstrates what the README claims.
"""

from __future__ import annotations

import pytest

from evals.ablation import run_ablation
from evals.layers import (
    run_escalation_preference,
    run_groundedness,
    run_numeric_correctness,
    run_retrieval_quality,
    run_scope_precision,
)

LAYERS = [
    run_retrieval_quality,
    run_scope_precision,
    run_numeric_correctness,
    run_groundedness,
    run_escalation_preference,
]


@pytest.mark.parametrize("layer_fn", LAYERS, ids=lambda f: f.__name__)
def test_layer_runs_cases_and_passes_its_gate(layer_fn):
    result = layer_fn()
    assert result.cases, f"{result.layer} ran zero cases"
    assert result.gate_passed, (
        f"{result.layer} below gate {result.gate_threshold}: "
        f"{[(c.case_id, c.detail) for c in result.failures]}"
    )


def test_scope_precision_gate_is_absolute():
    """0.99 is not acceptable here. One wrong-year retrieval breaks the claim."""
    assert run_scope_precision().gate_threshold == 1.0


def test_scope_precision_reports_zero_wrong_year_retrievals():
    assert run_scope_precision().metrics["wrong_year_retrievals"] == 0.0


def test_ablation_shows_naive_retrieval_failing():
    """Guards the headline claim in the README.

    If naive retrieval ever stops failing on this corpus, the corpus has become
    too easy and the adversarial cases need to be harder. That is a real
    maintenance signal, not a flaky test.
    """
    results = run_ablation()
    naive = results["naive_no_scope_filter"]
    scoped = results["scoped_hard_prefilter"]

    assert scoped["wrong_year_at_rank_1"] == 0.0
    assert scoped["precision_at_1"] == 1.0
    assert naive["wrong_year_at_rank_1"] > 0, (
        "naive retrieval no longer fails; the adversarial set is too easy"
    )
    assert naive["precision_at_1"] < scoped["precision_at_1"]
