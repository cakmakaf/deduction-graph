"""Scope to hard filter translation.

Separated from the store implementations so the same filter semantics apply to
every backend, and so a test can assert the filter directly instead of asserting
on retrieval output.
"""

from __future__ import annotations

from deduction_graph.retrieval.schema import Chunk
from deduction_graph.types import Scope


class ScopeNotResolvedError(RuntimeError):
    """Raised when retrieval is attempted with an unresolved scope.

    This is a hard error, not a warning. Retrieval without a resolved tax year
    is the failure mode the system exists to prevent, so the code makes it
    impossible to reach rather than merely unlikely.
    """


def to_store_filter(scope: Scope) -> dict:
    """Build a metadata filter for the vector store.

    Uses the Chroma-style ``$and`` / ``$in`` dialect. Adapters for other stores
    translate from this canonical form.
    """
    if not scope.is_resolved:
        raise ScopeNotResolvedError(
            f"Cannot retrieve with unresolved scope. Missing: {scope.missing()}. "
            "The scope-resolution node must either resolve these or route to a "
            "clarifying question."
        )

    clauses: list[dict] = [
        {"tax_year": {"$eq": scope.tax_year}},
        {"jurisdiction": {"$eq": scope.jurisdiction}},
        {"provision": {"$in": [p.value for p in scope.provisions]}},
    ]
    return {"$and": clauses} if len(clauses) > 1 else clauses[0]


def passes(chunk: Chunk, scope: Scope) -> bool:
    """In-memory equivalent of the store filter.

    Kept deliberately close in structure to ``to_store_filter`` so that the
    in-memory store used in tests and the production store cannot silently
    disagree about scope semantics.
    """
    if not scope.is_resolved:
        raise ScopeNotResolvedError(f"Unresolved scope. Missing: {scope.missing()}")

    md = chunk.metadata
    if md.tax_year != scope.tax_year:
        return False
    if md.jurisdiction != scope.jurisdiction:
        return False
    if md.provision not in scope.provisions:
        return False
    # Empty filing_statuses means universally applicable.
    if (
        scope.filing_status is not None
        and md.filing_statuses
        and scope.filing_status not in md.filing_statuses
    ):
        return False
    return True
