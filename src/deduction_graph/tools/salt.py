"""State and local tax deduction, with the cap and the 2025 phase-down.

The phase-down mechanic is the most error-prone calculation in v1 and is
deliberately written as explicit steps rather than a compact formula, because
this trail is what a reviewer reads.
"""

from __future__ import annotations

from decimal import Decimal

from deduction_graph.rules import RuleSet
from deduction_graph.tools.base import DeductionTool, clamp_non_negative
from deduction_graph.types import (
    AuthorityTier,
    Citation,
    ComputationStep,
    FilingStatus,
    Provision,
    TaxpayerProfile,
    ToolResult,
    money,
)


class SaltTool(DeductionTool):
    name = "apply_salt_cap"
    provision = Provision.SALT
    description = (
        "Apply the state and local tax deduction cap for a tax year and filing "
        "status, including any income-based phase-down of the cap."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        mfs = profile.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY

        gross = (
            profile.state_local_income_or_sales_tax.amount
            + profile.state_local_property_tax.amount
        )
        steps.append(
            ComputationStep(
                label="Total state and local taxes paid",
                detail=(
                    f"income or sales tax {profile.state_local_income_or_sales_tax} "
                    f"plus property tax {profile.state_local_property_tax}"
                ),
                value=money(gross),
            )
        )

        cap_path = "salt.cap.married_filing_separately" if mfs else "salt.cap.default"
        cap_param = rules.get(cap_path)
        cap = cap_param.decimal
        steps.append(
            ComputationStep(
                label="Statutory cap",
                detail=f"tax year {profile.tax_year}, {profile.filing_status.value}",
                value=money(cap),
                rule_source=cap_param.source,
            )
        )

        phase_source: str | None = None
        if rules.has("salt.phase_down") and rules.raw_block("salt.phase_down").get(
            "enabled"
        ):
            block = rules.raw_block("salt.phase_down")
            phase_source = block.get("source")
            threshold = Decimal(
                str(
                    block["married_filing_separately_threshold"]
                    if mfs
                    else block["magi_threshold"]
                )
            )
            rate = Decimal(str(block["reduction_rate"]))
            floor = Decimal(
                str(block["married_filing_separately_floor"] if mfs else block["floor"])
            )
            magi = profile.effective_magi.amount

            if magi > threshold:
                excess = magi - threshold
                reduction = excess * rate
                reduced = clamp_non_negative(cap - reduction)
                cap = max(reduced, floor)
                steps.append(
                    ComputationStep(
                        label="Cap phase-down",
                        detail=(
                            f"MAGI {money(magi)} exceeds {money(threshold)} by "
                            f"{money(excess)}; reduce cap by {rate * 100:.0f} percent "
                            f"of the excess ({money(reduction)}), not below the "
                            f"{money(floor)} floor"
                        ),
                        value=money(cap),
                        rule_source=phase_source,
                    )
                )
            else:
                steps.append(
                    ComputationStep(
                        label="Cap phase-down not triggered",
                        detail=f"MAGI {profile.effective_magi} is at or below {money(threshold)}",
                        rule_source=phase_source,
                    )
                )

        deductible = min(gross, cap)
        steps.append(
            ComputationStep(
                label="Deductible SALT",
                detail="lesser of taxes paid and the applicable cap",
                value=money(deductible),
            )
        )

        citations = [
            Citation(
                source=cap_param.source,
                tax_year=profile.tax_year,
                provision=self.provision,
                authority_tier=AuthorityTier.STATUTE,
            )
        ]
        if phase_source:
            citations.append(
                Citation(
                    source=phase_source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.STATUTE,
                )
            )

        return self._result(
            profile=profile,
            value=deductible,
            steps=tuple(steps),
            citations=tuple(citations),
        )
