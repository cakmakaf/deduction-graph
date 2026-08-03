"""Tool base contract.

Every calculation tool is a pure function of (profile, ruleset) with a typed
return. No tool calls an LLM, performs retrieval, or reads global state. That
constraint is what makes the numeric-correctness eval layer meaningful: the same
inputs always produce the same number, so a golden file is a real test.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import ROUND_HALF_UP, Decimal

from deduction_graph.rules import RuleSet
from deduction_graph.types import (
    Money,
    Provision,
    TaxpayerProfile,
    ToolResult,
    money,
)

CENTS = Decimal("0.01")


def quantize(amount: Decimal) -> Decimal:
    """Round half up to cents, which is the convention tax forms use."""
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def clamp_non_negative(amount: Decimal) -> Decimal:
    return amount if amount > 0 else Decimal("0")


class DeductionTool(ABC):
    """A typed, deterministic calculation unit."""

    name: str
    provision: Provision
    description: str

    @abstractmethod
    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        """Return the deductible amount plus a reproducible audit trail."""

    def __call__(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        if profile.tax_year != rules.tax_year:
            raise ValueError(
                f"Tax year mismatch: profile is {profile.tax_year}, rules are "
                f"{rules.tax_year}. This guard exists because a silent mismatch "
                "here is the single most dangerous bug in the system."
            )
        with rules.tracking_scope():
            result = self.compute(profile, rules)
            return result.model_copy(
                update={"unverified_parameters": rules.unverified_reads()}
            )

    def _result(
        self,
        *,
        profile: TaxpayerProfile,
        value: Decimal | Money,
        steps: tuple,
        citations: tuple = (),
        warnings: tuple = (),
    ) -> ToolResult:
        amount = value.amount if isinstance(value, Money) else value
        return ToolResult(
            tool=self.name,
            provision=self.provision,
            tax_year=profile.tax_year,
            value=money(quantize(amount)),
            steps=steps,
            citations=citations,
            warnings=warnings,
        )
