"""Medical and dental expense deduction, subject to the AGI floor."""

from __future__ import annotations

from deduction_graph.rules import RuleSet
from deduction_graph.tools.base import DeductionTool, clamp_non_negative
from deduction_graph.types import (
    AuthorityTier,
    Citation,
    ComputationStep,
    Provision,
    TaxpayerProfile,
    ToolResult,
    money,
)


class MedicalExpenseTool(DeductionTool):
    name = "medical_expense_deduction"
    provision = Provision.MEDICAL
    description = "Compute deductible medical expenses in excess of the AGI floor."

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        rate = rules.get("medical.agi_threshold")
        floor = profile.agi.amount * rate.decimal
        deductible = clamp_non_negative(profile.medical_expenses.amount - floor)

        steps = (
            ComputationStep(
                label="AGI floor",
                detail=f"{rate.decimal * 100:.1f} percent of AGI {profile.agi}",
                value=money(floor),
                rule_source=rate.source,
            ),
            ComputationStep(
                label="Deductible medical expenses",
                detail=(
                    f"expenses {profile.medical_expenses} less floor {money(floor)}, "
                    "not below zero"
                ),
                value=money(deductible),
            ),
        )

        return self._result(
            profile=profile,
            value=deductible,
            steps=steps,
            citations=(
                Citation(
                    source=rate.source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.STATUTE,
                ),
            ),
        )
