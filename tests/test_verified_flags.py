"""The verification gate.

This test is EXPECTED TO FAIL on a fresh clone, and that is deliberate. Every
rule parameter ships with `verified: false` until a human has checked it against
the cited primary source. The failure is a work queue, not a defect.

Run `python scripts/verification_report.py` for the list.

Once every parameter is verified, delete the xfail marker so the gate becomes
permanent and a newly added unverified parameter fails CI.
"""

from __future__ import annotations

import pytest

from deduction_graph.rules import load_rules


@pytest.mark.xfail(
    reason=(
        "Rule parameters are drafted but not yet verified against primary sources. "
        "Remove this marker once verification is complete."
    ),
    strict=False,
)
@pytest.mark.parametrize("tax_year", [2024, 2025])
def test_all_parameters_verified(tax_year: int):
    unverified = [p.path for p in load_rules(tax_year).all_parameters() if not p.verified]
    assert not unverified, (
        f"{len(unverified)} unverified parameters in {tax_year}: {unverified[:5]}..."
    )


@pytest.mark.parametrize("tax_year", [2024, 2025])
def test_unverified_parameters_are_reported_not_hidden(tax_year: int):
    """Whatever the verification state, it must be visible to the caller."""
    rules = load_rules(tax_year)
    rules.reset_reads()
    rules.get("standard_deduction.base.single")
    param = rules.reads[0]
    if not param.verified:
        assert param.path in rules.unverified_reads()
