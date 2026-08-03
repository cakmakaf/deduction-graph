"""Student loan interest deduction, an above-the-line deduction with a MAGI
phase-out and a filing-status eligibility bar.
"""

from __future__ import annotations

from decimal import Decimal

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


class StudentLoanInterestTool(DeductionTool):
    name = "student_loan_interest_deduction"
    provision = Provision.STUDENT_LOAN_INTEREST
    description = (
        "Compute the student loan interest deduction after the statutory maximum "
        "and the MAGI phase-out, including filing-status ineligibility."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        status = profile.filing_status.value
        block = rules.raw_block(f"student_loan_interest.phase_out.{status}")

        if block.get("ineligible"):
            steps.append(
                ComputationStep(
                    label="Ineligible filing status",
                    detail=f"{status} cannot claim this deduction",
                    value=money(0),
                    rule_source=block.get("source"),
                )
            )
            return self._result(profile=profile, value=Decimal("0"), steps=tuple(steps))

        max_param = rules.get("student_loan_interest.max_deduction")
        capped = min(profile.student_loan_interest_paid.amount, max_param.decimal)
        steps.append(
            ComputationStep(
                label="Interest before phase-out",
                detail=(
                    f"lesser of interest paid {profile.student_loan_interest_paid} and "
                    f"the {money(max_param.decimal)} statutory maximum"
                ),
                value=money(capped),
                rule_source=max_param.source,
            )
        )

        start = Decimal(str(block["start"]))
        end = Decimal(str(block["end"]))
        magi = profile.effective_magi.amount

        if magi <= start:
            deductible = capped
            steps.append(
                ComputationStep(
                    label="No phase-out",
                    detail=f"MAGI {profile.effective_magi} is at or below {money(start)}",
                    value=money(deductible),
                    rule_source=block.get("source"),
                )
            )
        elif magi >= end:
            deductible = Decimal("0")
            steps.append(
                ComputationStep(
                    label="Fully phased out",
                    detail=f"MAGI {profile.effective_magi} is at or above {money(end)}",
                    value=money(deductible),
                    rule_source=block.get("source"),
                )
            )
        else:
            reduction_fraction = (magi - start) / (end - start)
            deductible = clamp_non_negative(capped * (Decimal("1") - reduction_fraction))
            steps.append(
                ComputationStep(
                    label="Partial phase-out",
                    detail=(
                        f"MAGI {profile.effective_magi} falls between {money(start)} and "
                        f"{money(end)}; reduce by {reduction_fraction:.6f} of "
                        f"{money(capped)}"
                    ),
                    value=money(deductible),
                    rule_source=block.get("source"),
                )
            )

        return self._result(
            profile=profile,
            value=deductible,
            steps=tuple(steps),
            citations=(
                Citation(
                    source=max_param.source,
                    tax_year=profile.tax_year,
                    provision=self.provision,
                    authority_tier=AuthorityTier.STATUTE,
                ),
            ),
        )
