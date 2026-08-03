"""The loader's refusals are the point, so they get tested first."""

from __future__ import annotations

import pytest

from deduction_graph.rules import UnverifiedParameterError, load_rules


def test_loads_both_supported_years():
    for year in (2024, 2025):
        rules = load_rules(year)
        assert rules.tax_year == year


def test_refuses_unknown_year_instead_of_falling_back():
    """The single most important negative test in the repository.

    A loader that quietly served 2024 data for a 2027 request would produce a
    confident, plausible, wrong answer. It must raise.
    """
    with pytest.raises(FileNotFoundError, match="No rule data for tax year 2027"):
        load_rules(2027)


def test_years_do_not_share_values():
    """Guards against a copy-paste that leaves two years identical."""
    y24 = load_rules(2024).get("standard_deduction.base.single").decimal
    y25 = load_rules(2025).get("standard_deduction.base.single").decimal
    assert y24 != y25


def test_unknown_path_raises_with_context():
    rules = load_rules(2024)
    with pytest.raises(KeyError, match="not found for tax year 2024"):
        rules.get("standard_deduction.base.nonexistent_status")


def test_strict_mode_rejects_unverified():
    rules = load_rules(2024, strict=True)
    with pytest.raises(UnverifiedParameterError):
        rules.get("standard_deduction.base.single")


def test_provenance_is_tracked_on_read():
    rules = load_rules(2024)
    rules.reset_reads()
    rules.get("salt.cap.default")
    assert len(rules.reads) == 1
    assert rules.reads[0].source


def test_nested_tracking_scope_does_not_lose_parent_reads():
    """Regression test for a real bug found during the initial build.

    A naive reset at the top of every tool call wiped the parent's accumulated
    reads, so composite tools under-reported which unverified parameters they
    actually depended on.
    """
    rules = load_rules(2024)
    with rules.tracking_scope():
        rules.get("salt.cap.default")
        with rules.tracking_scope():
            rules.get("medical.agi_threshold")
        assert len(rules.reads) == 2


def test_every_parameter_declares_a_source():
    for year in (2024, 2025):
        for param in load_rules(year).all_parameters():
            assert param.source and param.source != "MISSING SOURCE", (
                f"{year} {param.path} has no source"
            )
