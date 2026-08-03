"""Graph state.

One typed object flows through every node. Each node reads what it needs and
writes a declared subset, so the trace log shows exactly which node produced
which field. That is what makes a bad answer attributable to a step instead of
to a prompt.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from deduction_graph.retrieval.schema import RetrievedChunk
from deduction_graph.types import (
    Citation,
    ComputationStep,
    Scope,
    TaxpayerProfile,
    ToolResult,
)


class Outcome(str, Enum):
    PENDING = "pending"
    ANSWERED = "answered"
    CLARIFICATION_NEEDED = "clarification_needed"
    ESCALATED = "escalated"


def _last(a: Any, b: Any) -> Any:
    """Reducer: last write wins. Explicit so LangGraph does not guess."""
    return b if b is not None else a


class GraphState(BaseModel):
    """The full state object.

    Mutable by design (LangGraph updates it), but every field is typed and every
    node declares what it writes in its docstring.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Input
    question: str
    profile: TaxpayerProfile | None = None
    conversation: list[dict[str, str]] = Field(default_factory=list)

    # intake node writes
    rewritten_question: str | None = None
    intent: str | None = None

    # scope node writes
    scope: Scope = Field(default_factory=Scope)
    clarifying_question: str | None = None

    # retrieval node writes
    retrieved: list[RetrievedChunk] = Field(default_factory=list)

    # computation node writes
    tool_results: list[ToolResult] = Field(default_factory=list)
    computation_trail: list[ComputationStep] = Field(default_factory=list)

    # synthesis node writes
    draft_answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)

    # self-check node writes
    groundedness_passed: bool | None = None
    check_notes: list[str] = Field(default_factory=list)

    # terminal
    outcome: Outcome = Outcome.PENDING
    final_answer: str | None = None
    escalation_reason: str | None = None

    # cross-cutting
    unverified_parameters: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)

    def record(self, node: str, **fields: Any) -> None:
        """Append a structured trace entry."""
        self.trace.append({"node": node, **fields})
