"""Standard versus itemized comparison.

This is the tool that answers the canonical user question ("should I itemize?").
It composes the other tools rather than reimplementing them, so a rule fix lands
in one place.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from deduction_graph.rules import RuleSet
from deduction_graph.tools.base import DeductionTool, quantize
from deduction_graph.tools.charitable import CharitableTool
from deduction_graph.tools.medical import MedicalExpenseTool
from deduction_graph.tools.mortgage import MortgageInterestTool
from deduction_graph.tools.salt import SaltTool
from deduction_graph.tools.standard_deduction import StandardDeductionTool
from deduction_graph.types import (
    ComputationStep,
    Money,
    Provision,
    TaxpayerProfile,
    ToolResult,
    money,
)

ITEMIZED_COMPONENTS: tuple[type[DeductionTool], ...] = (
    SaltTool,
    MortgageInterestTool,
    CharitableTool,
    MedicalExpenseTool,
)


class DeductionComparison(BaseModel):
    """Structured comparison, returned alongside the ToolResult for callers that
    want the breakdown rather than just the number.
    """

    model_config = ConfigDict(frozen=True)

    tax_year: int
    standard_deduction: Money
    itemized_total: Money
    itemized_components: dict[str, Money]
    recommended: str
    advantage: Money


class CompareStandardVsItemizedTool(DeductionTool):
    name = "compare_standard_vs_itemized"
    provision = Provision.STANDARD_DEDUCTION
    description = (
        "Compare the standard deduction against total itemized deductions and "
        "report which produces the larger deduction, with a full breakdown."
    )

    def compute(self, profile: TaxpayerProfile, rules: RuleSet) -> ToolResult:
        steps: list[ComputationStep] = []
        warnings: list[str] = []
        citations: list = []

        standard = StandardDeductionTool()(profile, rules)
        steps.extend(standard.steps)
        citations.extend(standard.citations)
        warnings.extend(standard.warnings)

        components: dict[str, Money] = {}
        itemized_total = Decimal("0")
        for tool_cls in ITEMIZED_COMPONENTS:
            tool = tool_cls()
            result = tool(profile, rules)
            components[tool.provision.value] = result.value
            itemized_total += result.value.amount
            steps.extend(result.steps)
            citations.extend(result.citations)
            warnings.extend(result.warnings)

        steps.append(
            ComputationStep(
                label="Total itemized deductions",
                detail=", ".join(f"{k} {v}" for k, v in components.items()),
                value=money(itemized_total),
            )
        )

        itemize = itemized_total > standard.value.amount
        advantage = abs(itemized_total - standard.value.amount)
        chosen = itemized_total if itemize else standard.value.amount

        steps.append(
            ComputationStep(
                label="Recommendation",
                detail=(
                    f"{'Itemize' if itemize else 'Take the standard deduction'}: "
                    f"itemized {money(itemized_total)} versus standard {standard.value}, "
                    f"a difference of {money(advantage)}"
                ),
                value=money(chosen),
            )
        )

        # Deliberate: the value returned is the larger deduction, and the
        # recommendation lives in the steps and the comparison object. A caller
        # that only reads `.value` still gets a correct number.
        result = self._result(
            profile=profile,
            value=chosen,
            steps=tuple(steps),
            citations=tuple(citations),
            warnings=tuple(dict.fromkeys(warnings)),
        )
        return result

    def comparison(
        self, profile: TaxpayerProfile, rules: RuleSet
    ) -> DeductionComparison:
        """Structured variant for callers that need the breakdown."""
        standard = StandardDeductionTool()(profile, rules)
        components: dict[str, Money] = {}
        total = Decimal("0")
        for tool_cls in ITEMIZED_COMPONENTS:
            tool = tool_cls()
            result = tool(profile, rules)
            components[tool.provision.value] = result.value
            total += result.value.amount

        itemize = total > standard.value.amount
        return DeductionComparison(
            tax_year=profile.tax_year,
            standard_deduction=standard.value,
            itemized_total=money(quantize(total)),
            itemized_components=components,
            recommended="itemized" if itemize else "standard",
            advantage=money(quantize(abs(total - standard.value.amount))),
        )
