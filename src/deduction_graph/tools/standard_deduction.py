"""Standard deduction, including the additional amount for age 65 or older and
blindness.
"""

from __future__ import annotations

from decimal import Decimal

from deduction_graph.rules import RuleSet
from deduction_graph.tools.base import DeductionTool
from deduction_graph.types import (
    AuthorityTier,
    Citation,
    ComputationStep,
    Provision,
    TaxpayerProfile,
    ToolResult,
    money,
)


class StandardDeductionTool(DeductionTool):
    name = "standard_deduction"
    provision = Provision.STANDARD_DEDUCTION
    description = (
        "Compute the standard deduction for a filing status and tax year, plus "
        "additional amounts for age 65 or older and blindness."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        warnings: list[str] = []

        base = rules.get(f"standard_deduction.base.{profile.filing_status.value}")
        total = base.decimal
        steps.append(
            ComputationStep(
                label="Base standard deduction",
                detail=f"{profile.filing_status.value}, tax year {profile.tax_year}",
                value=money(base.decimal),
                rule_source=base.source,
            )
        )

        count = profile.additional_standard_deduction_count
        if count:
            key = "married" if profile.filing_status.is_married else "unmarried"
            extra = rules.get(f"standard_deduction.additional.{key}")
            added = extra.decimal * Decimal(count)
            total += added
            steps.append(
                ComputationStep(
                    label="Additional standard deduction",
                    detail=(
                        f"{count} qualifying condition(s) at {money(extra.decimal)} each "
                        f"({key} rate)"
                    ),
                    value=money(added),
                    rule_source=extra.source,
                )
            )

        if profile.can_be_claimed_as_dependent:
            warnings.append(
                "Taxpayer can be claimed as a dependent. A separate limited "
                "standard deduction calculation applies and is not implemented in "
                "v1. Escalate rather than relying on this figure."
            )

        steps.append(
            ComputationStep(
                label="Total standard deduction",
                detail="Base plus additional amounts",
                value=money(total),
            )
        )

        return self._result(
            profile=profile,
            value=total,
            steps=tuple(steps),
            citations=(
                Citation(
                    source=base.source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.PUBLICATION,
                ),
            ),
            warnings=tuple(warnings),
        )
