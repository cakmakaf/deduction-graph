"""API request and response models.

The response envelope carries the disclaimer, the citations, the computation
trail, and the unverified-parameter list as first-class fields rather than as
prose the client can drop. A consumer cannot render an answer from this API
without also having the material needed to audit it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from deduction_graph.types import Citation, TaxpayerProfile

DISCLAIMER = (
    "This is a software engineering demonstration, not tax advice. Figures must "
    "not be relied upon for filing. Consult a qualified tax professional."
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    profile: TaxpayerProfile | None = None
    conversation: list[dict[str, str]] = Field(default_factory=list)


class TrailStep(BaseModel):
    label: str
    detail: str
    amount: str | None = None
    rule_source: str | None = None


class AskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome: str
    answer: str | None
    tax_year: int | None
    provisions: list[str]
    computation_trail: list[TrailStep]
    citations: list[Citation]
    unverified_parameters: list[str]
    warnings: list[str]
    escalation_reason: str | None = None
    run_id: str | None = None
    disclaimer: str = DISCLAIMER


class HealthResponse(BaseModel):
    status: str
    version: str
    supported_tax_years: list[int]
    llm_configured: bool
    corpus_chunks: int
