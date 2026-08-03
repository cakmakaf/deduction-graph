"""Tool behavior beyond the golden numbers.

The golden cases prove the arithmetic. These prove the guards, the warnings, and
the audit trail, which is what makes the arithmetic trustworthy.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from deduction_graph.rules import load_rules
from deduction_graph.tools.registry import ALL_TOOLS, BY_NAME, tool_schemas, tools_for
from deduction_graph.types import FilingStatus, Money, Provision, TaxpayerProfile, money


def _profile(**kw) -> TaxpayerProfile:
    base = dict(
        profile_id="t001",
        tax_year=2024,
        filing_status=FilingStatus.SINGLE,
        agi=money(80000),
    )
    base.update(kw)
    return TaxpayerProfile(**base)


def test_money_rejects_float():
    """Binary floating point has no business in a tax calculation."""
    with pytest.raises(Exception):
        Money(amount=14600.55)


def test_money_accepts_str_int_decimal():
    assert money("14600.55").amount == Decimal("14600.55")
    assert money(14600).amount == Decimal("14600")
    assert money(Decimal("1.01")).amount == Decimal("1.01")


def test_tool_rejects_tax_year_mismatch():
    """The most dangerous silent bug in the system, so it is a hard error."""
    profile = _profile(tax_year=2024)
    with pytest.raises(ValueError, match="Tax year mismatch"):
        BY_NAME["standard_deduction"](profile, load_rules(2025))


def test_every_tool_returns_an_audit_trail():
    profile = _profile(
        hsa_coverage="self_only",
        hsa_contributions=money(3000),
        student_loan_interest_paid=money(1200),
        medical_expenses=money(9000),
        charitable_cash=money(2000),
        state_local_property_tax=money(4000),
        mortgage_interest_paid=money(9000),
        mortgage_balance=money(300000),
        mortgage_origination_date=date(2020, 1, 1),
    )
    rules = load_rules(2024)
    for tool in ALL_TOOLS:
        result = tool(profile, rules)
        assert result.steps, f"{tool.name} produced no audit trail"
        assert result.tax_year == 2024
        for step in result.steps:
            assert step.label and step.detail


def test_unverified_parameters_surface_to_the_caller():
    result = BY_NAME["standard_deduction"](_profile(), load_rules(2024))
    assert result.unverified_parameters, (
        "drafted parameters must be reported, not silently used"
    )


def test_composite_tool_aggregates_all_child_provenance():
    """Regression guard for the nested-tracking bug."""
    profile = _profile(
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        agi=money(180000),
        state_local_property_tax=money(6400),
        mortgage_interest_paid=money(14200),
        mortgage_balance=money(410000),
        mortgage_origination_date=date(2021, 6, 1),
        charitable_cash=money(3000),
    )
    result = BY_NAME["compare_standard_vs_itemized"](profile, load_rules(2024))
    paths = set(result.unverified_parameters)
    assert any("standard_deduction" in p for p in paths)
    assert any("salt" in p for p in paths)
    assert any("charitable" in p for p in paths)
    assert any("medical" in p for p in paths)


def test_dependent_status_raises_a_warning_rather_than_guessing():
    result = BY_NAME["standard_deduction"](
        _profile(can_be_claimed_as_dependent=True), load_rules(2024)
    )
    assert result.warnings
    assert "dependent" in result.warnings[0].lower()


def test_unknown_mortgage_date_warns_and_uses_less_favorable_limit():
    result = BY_NAME["mortgage_interest_deduction"](
        _profile(
            mortgage_interest_paid=money(50000),
            mortgage_balance=money(1000000),
            mortgage_origination_date=None,
        ),
        load_rules(2024),
    )
    assert result.warnings
    # 750000/1000000 = 0.75, the post-2017 limit, not the grandfathered one.
    assert result.value.amount == Decimal("37500.00")


def test_hsa_excess_contribution_warns():
    result = BY_NAME["contribution_limit_hsa"](
        _profile(hsa_coverage="self_only", hsa_contributions=money(9000)),
        load_rules(2024),
    )
    assert any("exceed" in w for w in result.warnings)


def test_charitable_carryforward_appears_in_trail():
    result = BY_NAME["charitable_limit"](
        _profile(agi=money(100000), charitable_cash=money(75000)), load_rules(2024)
    )
    labels = [s.label for s in result.steps]
    assert "Carryforward" in labels


def test_comparison_object_recommends_correctly():
    tool = BY_NAME["compare_standard_vs_itemized"]
    profile = _profile(
        filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        agi=money(180000),
        state_local_property_tax=money(6400),
        state_local_income_or_sales_tax=money(9800),
        mortgage_interest_paid=money(14200),
        mortgage_balance=money(410000),
        mortgage_origination_date=date(2021, 6, 1),
        charitable_cash=money(3000),
    )
    c24 = tool.comparison(profile, load_rules(2024))
    assert c24.recommended == "standard"

    c25 = tool.comparison(
        profile.model_copy(update={"tax_year": 2025}), load_rules(2025)
    )
    assert c25.recommended == "itemized", (
        "the raised 2025 SALT cap should flip this taxpayer to itemizing"
    )


def test_registry_selects_by_provision():
    selected = tools_for((Provision.SALT,))
    assert [t.name for t in selected] == ["apply_salt_cap"]


def test_tool_schemas_are_serializable():
    schemas = tool_schemas()
    assert schemas
    for s in schemas:
        assert set(s) == {"name", "provision", "description"}
