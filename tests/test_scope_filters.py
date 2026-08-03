"""Scope filtering. The architectural guarantee lives here."""

from __future__ import annotations

import pytest

from deduction_graph.retrieval.filters import (
    ScopeNotResolvedError,
    passes,
    to_store_filter,
)
from deduction_graph.types import FilingStatus, Provision, Scope
from evals.datasets.fixture_corpus import FIXTURE_CHUNKS


def _scope(year: int = 2024, **kw) -> Scope:
    kw.setdefault("provisions", (Provision.STANDARD_DEDUCTION,))
    return Scope(tax_year=year, **kw)


def test_unresolved_scope_cannot_retrieve():
    """Retrieval without a resolved tax year must be impossible, not unlikely."""
    with pytest.raises(ScopeNotResolvedError):
        to_store_filter(Scope())
    with pytest.raises(ScopeNotResolvedError):
        passes(FIXTURE_CHUNKS[0], Scope())


def test_missing_reports_what_to_ask_for():
    assert Scope().missing() == ("tax_year", "provision")
    assert Scope(tax_year=2024).missing() == ("provision",)


def test_wrong_year_chunk_is_filtered_out():
    scope = _scope(2024)
    chunk_2025 = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2025:sd-single"
    )
    assert not passes(chunk_2025, scope)


def test_right_year_chunk_passes():
    scope = _scope(2024)
    chunk_2024 = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2024:sd-single"
    )
    assert passes(chunk_2024, scope)


def test_provision_filter_excludes_other_provisions():
    scope = _scope(2024, provisions=(Provision.SALT,))
    sd_chunk = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2024:sd-single"
    )
    assert not passes(sd_chunk, scope)


def test_filing_status_filter():
    scope = _scope(2024, filing_status=FilingStatus.MARRIED_FILING_JOINTLY)
    single_chunk = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "pub501-2024:sd-single"
    )
    assert not passes(single_chunk, scope)


def test_empty_filing_statuses_means_universal():
    """A chunk with no declared statuses must not be filtered by status."""
    scope = _scope(2024, filing_status=FilingStatus.SINGLE, provisions=(Provision.SALT,))
    salt_chunk = next(
        c for c in FIXTURE_CHUNKS if c.metadata.chunk_id == "scha-2024:salt-cap"
    )
    assert salt_chunk.metadata.filing_statuses == ()
    assert passes(salt_chunk, scope)


def test_store_filter_and_in_memory_filter_agree():
    """The two implementations must not drift.

    The in-memory store is what CI runs; a production store is what users hit.
    If their scope semantics diverge, CI is green while production is wrong.
    """
    scope = _scope(2024, provisions=(Provision.STANDARD_DEDUCTION, Provision.SALT))
    store_filter = to_store_filter(scope)
    clauses = {list(c.keys())[0] for c in store_filter["$and"]}
    assert clauses == {"tax_year", "jurisdiction", "provision"}

    for chunk in FIXTURE_CHUNKS:
        expected = (
            chunk.metadata.tax_year == 2024
            and chunk.metadata.provision in scope.provisions
            and chunk.metadata.jurisdiction == "US-federal"
        )
        assert passes(chunk, scope) == expected, chunk.metadata.chunk_id


def test_retriever_never_returns_wrong_year(scoped_retriever):
    for year in (2024, 2025):
        scope = _scope(year, provisions=tuple(Provision))
        results = scoped_retriever.retrieve("standard deduction limit amount", scope, k=20)
        assert results, "expected some results"
        assert all(r.chunk.metadata.tax_year == year for r in results)
