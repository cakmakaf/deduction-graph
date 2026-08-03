"""Core domain models.

Everything that crosses a node boundary or a tool boundary is typed. The graph
carries these, not free-form dicts, so that a malformed intermediate state
fails loudly at the boundary that produced it rather than silently downstream.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FilingStatus(str, Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"

    @property
    def is_married(self) -> bool:
        return self in {
            FilingStatus.MARRIED_FILING_JOINTLY,
            FilingStatus.MARRIED_FILING_SEPARATELY,
            FilingStatus.QUALIFYING_SURVIVING_SPOUSE,
        }


class Provision(str, Enum):
    """Deduction provisions in scope for v1.

    Used both as a tool selector and as retrieval metadata, so the retrieval
    filter and the calculation registry cannot drift apart.
    """

    STANDARD_DEDUCTION = "standard_deduction"
    SALT = "salt"
    MORTGAGE_INTEREST = "mortgage_interest"
    CHARITABLE = "charitable"
    MEDICAL = "medical"
    STUDENT_LOAN_INTEREST = "student_loan_interest"
    HSA = "hsa"
    IRA = "ira"
    SENIOR_DEDUCTION = "senior_deduction"


class AuthorityTier(str, Enum):
    """Ranked weight of a source. Statute beats a publication when they appear
    to conflict, and the synthesis node is told so explicitly.
    """

    STATUTE = "statute"
    REGULATION = "regulation"
    PUBLICATION = "publication"
    INSTRUCTION = "instruction"


class Money(BaseModel):
    """Exact currency. Never a float.

    Tax arithmetic is exact arithmetic. Binary floating point silently
    introduces error that then gets rounded into a dollar figure a user might
    file against, so Decimal is enforced at the type boundary.
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(..., description="Exact amount in whole dollars and cents")

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce(cls, v: object) -> Decimal:
        if isinstance(v, float):
            raise TypeError(
                "Money rejects float. Pass a str, int, or Decimal to avoid binary "
                "floating point error in tax arithmetic."
            )
        return Decimal(str(v))

    def __add__(self, other: "Money") -> "Money":
        return Money(amount=self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(amount=self.amount - other.amount)

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"${self.amount:,.2f}"


def money(v: object) -> Money:
    """Convenience constructor."""
    return Money(amount=v)  # type: ignore[arg-type]


ZERO = money(0)


class TaxpayerProfile(BaseModel):
    """A synthetic taxpayer. No real PII enters this system, ever."""

    model_config = ConfigDict(frozen=True)

    profile_id: str
    tax_year: int
    filing_status: FilingStatus
    agi: Money
    magi: Money | None = Field(
        default=None,
        description="Modified AGI. Falls back to AGI when not supplied.",
    )

    age: int | None = None
    spouse_age: int | None = None
    is_blind: bool = False
    spouse_is_blind: bool = False
    can_be_claimed_as_dependent: bool = False

    # Itemizable inputs
    state_local_income_or_sales_tax: Money = ZERO
    state_local_property_tax: Money = ZERO
    mortgage_interest_paid: Money = ZERO
    mortgage_balance: Money = ZERO
    mortgage_origination_date: date | None = None
    charitable_cash: Money = ZERO
    charitable_noncash: Money = ZERO
    medical_expenses: Money = ZERO

    # Above-the-line inputs
    student_loan_interest_paid: Money = ZERO
    hsa_contributions: Money = ZERO
    hsa_coverage: Literal["self_only", "family", "none"] = "none"
    ira_contributions: Money = ZERO

    @property
    def effective_magi(self) -> Money:
        return self.magi if self.magi is not None else self.agi

    @property
    def additional_standard_deduction_count(self) -> int:
        """Number of qualifying conditions (age 65 or older, blind), counting
        both spouses on a joint return.
        """
        count = 0
        if self.age is not None and self.age >= 65:
            count += 1
        if self.is_blind:
            count += 1
        if self.filing_status in {
            FilingStatus.MARRIED_FILING_JOINTLY,
            FilingStatus.QUALIFYING_SURVIVING_SPOUSE,
        }:
            if self.spouse_age is not None and self.spouse_age >= 65:
                count += 1
            if self.spouse_is_blind:
                count += 1
        return count


class Citation(BaseModel):
    """A pointer back to authority. Every claim in a final answer carries one."""

    model_config = ConfigDict(frozen=True)

    source: str
    tax_year: int
    provision: Provision
    authority_tier: AuthorityTier = AuthorityTier.PUBLICATION
    span: str | None = Field(default=None, description="Quoted or located text span")
    chunk_id: str | None = None


class ComputationStep(BaseModel):
    """One line of the audit trail.

    The trail is the deliverable, not a debugging aid. A user or a reviewer
    should be able to reproduce the number by hand from these steps.
    """

    model_config = ConfigDict(frozen=True)

    label: str
    detail: str
    value: Money | None = None
    rule_source: str | None = None


class ToolResult(BaseModel):
    """Uniform return type for every calculation tool."""

    model_config = ConfigDict(frozen=True)

    tool: str
    provision: Provision
    tax_year: int
    value: Money
    steps: tuple[ComputationStep, ...] = ()
    citations: tuple[Citation, ...] = ()
    warnings: tuple[str, ...] = ()
    unverified_parameters: tuple[str, ...] = Field(
        default=(),
        description=(
            "Rule parameters used whose `verified` flag was false. Surfaced all "
            "the way to the user rather than swallowed."
        ),
    )


class Scope(BaseModel):
    """Resolved retrieval and computation scope.

    Produced by the scope-resolution node BEFORE retrieval runs, so these become
    hard pre-filters rather than soft ranking signals. If a field cannot be
    resolved, the graph asks rather than guesses.
    """

    model_config = ConfigDict(frozen=True)

    tax_year: int | None = None
    filing_status: FilingStatus | None = None
    provisions: tuple[Provision, ...] = ()
    jurisdiction: str = "US-federal"

    @property
    def is_resolved(self) -> bool:
        return self.tax_year is not None and bool(self.provisions)

    def missing(self) -> tuple[str, ...]:
        gaps: list[str] = []
        if self.tax_year is None:
            gaps.append("tax_year")
        if not self.provisions:
            gaps.append("provision")
        return tuple(gaps)
