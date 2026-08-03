"""Tool registry.

The graph's computation node selects tools from here by Provision, so adding a
provision means registering one class and nothing else changes. The registry is
also what the API exposes for tool discovery and what the eval harness iterates.
"""

from __future__ import annotations

from deduction_graph.tools.base import DeductionTool
from deduction_graph.tools.charitable import CharitableTool
from deduction_graph.tools.compare import (
    CompareStandardVsItemizedTool,
    DeductionComparison,
)
from deduction_graph.tools.hsa import HsaContributionTool
from deduction_graph.tools.medical import MedicalExpenseTool
from deduction_graph.tools.mortgage import MortgageInterestTool
from deduction_graph.tools.salt import SaltTool
from deduction_graph.tools.standard_deduction import StandardDeductionTool
from deduction_graph.tools.student_loan import StudentLoanInterestTool
from deduction_graph.types import Provision

ALL_TOOLS: tuple[DeductionTool, ...] = (
    StandardDeductionTool(),
    SaltTool(),
    MortgageInterestTool(),
    CharitableTool(),
    MedicalExpenseTool(),
    StudentLoanInterestTool(),
    HsaContributionTool(),
    CompareStandardVsItemizedTool(),
)

BY_NAME: dict[str, DeductionTool] = {t.name: t for t in ALL_TOOLS}

BY_PROVISION: dict[Provision, tuple[DeductionTool, ...]] = {}
for _tool in ALL_TOOLS:
    BY_PROVISION.setdefault(_tool.provision, ())
    BY_PROVISION[_tool.provision] += (_tool,)


def get_tool(name: str) -> DeductionTool:
    if name not in BY_NAME:
        raise KeyError(f"Unknown tool {name!r}. Registered: {sorted(BY_NAME)}")
    return BY_NAME[name]


def tools_for(provisions: tuple[Provision, ...]) -> tuple[DeductionTool, ...]:
    """Select tools for a resolved scope, preserving registration order."""
    selected: list[DeductionTool] = []
    for tool in ALL_TOOLS:
        if tool.provision in provisions and tool not in selected:
            selected.append(tool)
    return tuple(selected)


def tool_schemas() -> list[dict]:
    """JSON-serializable tool descriptions, for LLM tool binding and the API."""
    return [
        {
            "name": t.name,
            "provision": t.provision.value,
            "description": t.description,
        }
        for t in ALL_TOOLS
    ]


__all__ = [
    "ALL_TOOLS",
    "BY_NAME",
    "BY_PROVISION",
    "CompareStandardVsItemizedTool",
    "DeductionComparison",
    "get_tool",
    "tool_schemas",
    "tools_for",
]
