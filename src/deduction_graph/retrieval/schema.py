"""Chunk metadata schema.

This is the heart of the project. Every chunk carries the fields the scope
resolver produces, so scope becomes a hard pre-filter on the candidate set
rather than a soft signal handed to a ranker and hoped for.

The distinction matters because provision text across adjacent tax years differs
by a handful of tokens. Embedding similarity cannot reliably discriminate
"2024 standard deduction is $14,600" from "2025 standard deduction is $15,750",
and a reranker only reorders what retrieval already returned. If the wrong year
is in the candidate set, it can be selected. If it is filtered out before search,
it cannot.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from deduction_graph.types import AuthorityTier, FilingStatus, Provision


class ChunkMetadata(BaseModel):
    """Filterable metadata attached to every indexed chunk."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    source: str = Field(..., description="Human-readable citation, e.g. 'Pub 501 (2024)'")
    source_url: str | None = None

    tax_year: int
    provision: Provision
    authority_tier: AuthorityTier

    filing_statuses: tuple[FilingStatus, ...] = Field(
        default=(),
        description=(
            "Filing statuses this chunk applies to. Empty means universally "
            "applicable, which is treated as always passing the filter."
        ),
    )
    jurisdiction: str = "US-federal"

    effective_start: date | None = None
    effective_end: date | None = None

    section: str | None = None
    page: int | None = None

    def to_store_dict(self) -> dict:
        """Flatten for vector stores that only accept scalar metadata values."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source": self.source,
            "source_url": self.source_url or "",
            "tax_year": self.tax_year,
            "provision": self.provision.value,
            "authority_tier": self.authority_tier.value,
            "filing_statuses": ",".join(s.value for s in self.filing_statuses),
            "jurisdiction": self.jurisdiction,
            "section": self.section or "",
            "page": self.page or 0,
        }


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    metadata: ChunkMetadata


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    score: float
    retrieval_method: str = Field(
        default="hybrid", description="dense, sparse, hybrid, or rerank"
    )
