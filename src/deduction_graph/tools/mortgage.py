"""Home mortgage interest deduction with the acquisition debt limit.

The grandfathering rule keys off origination date, which is exactly the kind of
conditional branch that a single-prompt LLM chain gets wrong quietly.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from deduction_graph.rules import RuleSet
from deduction_graph.tools.base import DeductionTool
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


class MortgageInterestTool(DeductionTool):
    name = "mortgage_interest_deduction"
    provision = Provision.MORTGAGE_INTEREST
    description = (
        "Compute deductible home mortgage interest, applying the acquisition debt "
        "limit and the pre-2018 grandfathering rule based on origination date."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        warnings: list[str] = []
        mfs = profile.filing_status == FilingStatus.MARRIED_FILING_SEPARATELY

        interest = profile.mortgage_interest_paid.amount
        balance = profile.mortgage_balance.amount

        if profile.mortgage_origination_date is None:
            warnings.append(
                "Mortgage origination date is unknown, so the grandfathering rule "
                "cannot be determined. Assuming the post-2017 limit, which is the "
                "less favorable of the two. Escalate for a definitive answer."
            )
            grandfathered = False
        else:
            cutoff_param = rules.raw_block(
                "mortgage_interest.acquisition_debt_limit.grandfathered"
            )
            cutoff = date.fromisoformat(
                str(cutoff_param["applies_to_debt_incurred_on_or_before"])
            )
            grandfathered = profile.mortgage_origination_date <= cutoff
            steps.append(
                ComputationStep(
                    label="Grandfathering determination",
                    detail=(
                        f"origination {profile.mortgage_origination_date.isoformat()} "
                        f"{'is on or before' if grandfathered else 'is after'} "
                        f"{cutoff.isoformat()}"
                    ),
                    rule_source=cutoff_param.get("source"),
                )
            )

        block_path = (
            "mortgage_interest.acquisition_debt_limit.grandfathered"
            if grandfathered
            else "mortgage_interest.acquisition_debt_limit.post_tcja"
        )
        block = rules.raw_block(block_path)
        limit_param = rules.get(block_path)
        limit = (
            Decimal(str(block["married_filing_separately_amount"]))
            if mfs
            else limit_param.decimal
        )
        steps.append(
            ComputationStep(
                label="Acquisition debt limit",
                detail=(
                    f"{'grandfathered' if grandfathered else 'post-2017'} limit"
                    f"{', married filing separately' if mfs else ''}"
                ),
                value=money(limit),
                rule_source=limit_param.source,
            )
        )

        if balance <= 0:
            warnings.append(
                "Mortgage balance is zero or missing, so the limit cannot be "
                "proportioned. Returning interest paid unlimited."
            )
            deductible = interest
        elif balance <= limit:
            deductible = interest
            steps.append(
                ComputationStep(
                    label="Limit not binding",
                    detail=f"balance {money(balance)} is within the {money(limit)} limit",
                    value=money(deductible),
                )
            )
        else:
            ratio = limit / balance
            deductible = interest * ratio
            steps.append(
                ComputationStep(
                    label="Proportional limitation",
                    detail=(
                        f"balance {money(balance)} exceeds the {money(limit)} limit; "
                        f"deductible fraction is {limit}/{balance} = {ratio:.6f} of "
                        f"{money(interest)} interest paid"
                    ),
                    value=money(deductible),
                )
            )
            warnings.append(
                "The average-balance method in Pub 936 may produce a different "
                "figure than this simplified ratio. v1 uses the simplified method "
                "and says so."
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
                    authority_tier=AuthorityTier.STATUTE,
                ),
            ),
            warnings=tuple(warnings),
        )
