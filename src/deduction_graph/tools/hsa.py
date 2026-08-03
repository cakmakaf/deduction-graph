"""HSA contribution deduction, with the coverage-tier limit and catch-up."""

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


class HsaContributionTool(DeductionTool):
    name = "contribution_limit_hsa"
    provision = Provision.HSA
    description = (
        "Compute the deductible HSA contribution given coverage tier, age, and the "
        "annual limit, flagging any excess contribution."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        warnings: list[str] = []

        if profile.hsa_coverage == "none":
            steps.append(
                ComputationStep(
                    label="No HDHP coverage recorded",
                    detail="HSA contributions require high deductible health plan coverage",
                    value=money(0),
                )
            )
            warnings.append(
                "Coverage tier is 'none'. If the taxpayer did have HDHP coverage, "
                "scope resolution failed and this should be escalated."
            )
            return self._result(
                profile=profile,
                value=Decimal("0"),
                steps=tuple(steps),
                warnings=tuple(warnings),
            )

        limit_param = rules.get(f"hsa.contribution_limit.{profile.hsa_coverage}")
        limit = limit_param.decimal
        steps.append(
            ComputationStep(
                label="Annual contribution limit",
                detail=f"{profile.hsa_coverage} coverage, tax year {profile.tax_year}",
                value=money(limit),
                rule_source=limit_param.source,
            )
        )

        catch_up_block = rules.raw_block("hsa.catch_up")
        catch_up_age = int(catch_up_block["age"])
        if profile.age is not None and profile.age >= catch_up_age:
            catch_up = rules.get("hsa.catch_up")
            limit += catch_up.decimal
            steps.append(
                ComputationStep(
                    label="Catch-up contribution",
                    detail=f"age {profile.age} is at or above {catch_up_age}",
                    value=money(catch_up.decimal),
                    rule_source=catch_up.source,
                )
            )

        contributed = profile.hsa_contributions.amount
        deductible = min(contributed, limit)
        if contributed > limit:
            warnings.append(
                f"Contributions of {money(contributed)} exceed the {money(limit)} "
                "limit. Excess contributions may be subject to an excise tax, which "
                "v1 does not calculate."
            )

        steps.append(
            ComputationStep(
                label="Deductible HSA contribution",
                detail=f"lesser of contributed {money(contributed)} and limit {money(limit)}",
                value=money(deductible),
            )
        )

        return self._result(
            profile=profile,
            value=deductible,
            steps=tuple(steps),
            citations=(
                Citation(
                    source=limit_param.source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.PUBLICATION,
                ),
            ),
            warnings=tuple(warnings),
        )
