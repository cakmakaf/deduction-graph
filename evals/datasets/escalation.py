"""Escalation-preference cases.

The system is expected to ask or escalate rather than answer. Coverage is
explicitly not the optimization target: a benefits or tax answer that is wrong
costs more than a question that goes to a human.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ExpectedBehavior(str, Enum):
    CLARIFY = "clarification_needed"
    ESCALATE = "escalated"


class EscalationCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    question: str
    expected: ExpectedBehavior
    why: str


ESCALATION_CASES: tuple[EscalationCase, ...] = (
    EscalationCase(
        case_id="esc-no-year",
        question="What is my standard deduction?",
        expected=ExpectedBehavior.CLARIFY,
        why=(
            "No tax year stated. Defaulting to the current calendar year is wrong "
            "during filing season, when a taxpayer filing in March 2026 means 2025."
        ),
    ),
    EscalationCase(
        case_id="esc-this-year-ambiguous",
        question="How much can I deduct for state taxes this year?",
        expected=ExpectedBehavior.CLARIFY,
        why="'This year' is ambiguous. Ask which tax year rather than assume.",
    ),
    EscalationCase(
        case_id="esc-no-provision",
        question="What can I deduct in 2025?",
        expected=ExpectedBehavior.CLARIFY,
        why="Year is resolved but no provision named, so retrieval has no scope.",
    ),
    EscalationCase(
        case_id="esc-out-of-scope-state",
        question="What is the California standard deduction for 2025?",
        expected=ExpectedBehavior.CLARIFY,
        why=(
            "State returns are out of scope for v1. The jurisdiction filter should "
            "prevent a federal answer from being served as if it were a California one."
        ),
    ),
    EscalationCase(
        case_id="esc-out-of-scope-business",
        question="How do I deduct depreciation on my rental property in 2025?",
        expected=ExpectedBehavior.CLARIFY,
        why="No provision in the v1 set matches, so no tool and no corpus applies.",
    ),
    EscalationCase(
        case_id="esc-credit-not-deduction",
        question="How much is the child tax credit for 2025?",
        expected=ExpectedBehavior.CLARIFY,
        why=(
            "Credits are out of scope. A system that answers adjacent questions it "
            "was not built for is the one that gets a number wrong."
        ),
    ),
    EscalationCase(
        case_id="esc-future-year",
        question="What is the standard deduction for a single filer in 2027?",
        expected=ExpectedBehavior.CLARIFY,
        why=(
            "No rule data exists for 2027. The loader refuses to fall back to an "
            "adjacent year, which is exactly the intended behavior."
        ),
    ),
    EscalationCase(
        case_id="esc-dependent-limited-sd",
        question=(
            "I am 19, a full time student, and my parents claim me as a dependent. "
            "What is my standard deduction for 2024?"
        ),
        expected=ExpectedBehavior.ESCALATE,
        why=(
            "The dependent-limited standard deduction is not implemented in v1. The "
            "standard deduction tool raises a warning and the answer must not be served."
        ),
    ),
)
