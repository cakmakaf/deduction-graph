"""Charitable contribution deduction with AGI percentage limits."""

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


class CharitableTool(DeductionTool):
    name = "charitable_limit"
    provision = Provision.CHARITABLE
    description = (
        "Compute the deductible charitable contribution after AGI percentage "
        "limits, reporting any carryforward."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        warnings: list[str] = []
        agi = profile.agi.amount

        cash = profile.charitable_cash.amount
        noncash = profile.charitable_noncash.amount

        cash_rate = rules.get("charitable.agi_limits.cash_public_charity")
        noncash_rate = rules.get("charitable.agi_limits.noncash_public_charity")

        cash_ceiling = agi * cash_rate.decimal
        allowed_cash = min(cash, cash_ceiling)
        steps.append(
            ComputationStep(
                label="Cash contribution limit",
                detail=(
                    f"{cash_rate.decimal * 100:.0f} percent of AGI {profile.agi} = "
                    f"{money(cash_ceiling)}; contributed {money(cash)}"
                ),
                value=money(allowed_cash),
                rule_source=cash_rate.source,
            )
        )

        noncash_ceiling = agi * noncash_rate.decimal
        remaining_headroom = max(noncash_ceiling - allowed_cash, Decimal("0"))
        allowed_noncash = min(noncash, remaining_headroom)
        if noncash > 0:
            steps.append(
                ComputationStep(
                    label="Non-cash contribution limit",
                    detail=(
                        f"{noncash_rate.decimal * 100:.0f} percent of AGI = "
                        f"{money(noncash_ceiling)}, reduced by cash already allowed; "
                        f"headroom {money(remaining_headroom)}, contributed {money(noncash)}"
                    ),
                    value=money(allowed_noncash),
                    rule_source=noncash_rate.source,
                )
            )
            warnings.append(
                "Non-cash contributions have category-specific limits (appreciated "
                "capital gain property, private foundations) that v1 does not fully "
                "model. The 50 percent ordering used here is a simplification."
            )

        total = allowed_cash + allowed_noncash
        carryforward = (cash + noncash) - total
        if carryforward > 0:
            years = rules.get("charitable.carryforward_years")
            steps.append(
                ComputationStep(
                    label="Carryforward",
                    detail=f"disallowed this year, carried forward up to {years.value} years",
                    value=money(carryforward),
                    rule_source=years.source,
                )
            )

        steps.append(
            ComputationStep(
                label="Deductible charitable contributions",
                detail="cash plus allowed non-cash, after AGI limits",
                value=money(total),
            )
        )

        return self._result(
            profile=profile,
            value=total,
            steps=tuple(steps),
            citations=(
                Citation(
                    source=cash_rate.source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.STATUTE,
                ),
            ),
            warnings=tuple(warnings),
        )
