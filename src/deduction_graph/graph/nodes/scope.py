"""Scope resolution.

Writes: scope, clarifying_question.

The most important node in the graph. It resolves tax year, filing status, and
provision set BEFORE retrieval runs, so those become hard pre-filters.

The rule it must never break: when scope cannot be resolved, ask. Do not guess,
do not default to the current year, do not fall back to an adjacent year. A
plausible guess here produces a confident answer computed against the wrong law,
which is the worst output this system can produce.
"""

from __future__ import annotations

import re

from deduction_graph.graph.state import GraphState, Outcome
from deduction_graph.llm.provider import get_llm
from deduction_graph import SUPPORTED_TAX_YEARS
from deduction_graph.types import Provision, Scope

YEAR_RE = re.compile(r"\b(20\d{2})\b")

# Out-of-scope jurisdiction signals. v1 is federal only, and a federal answer
# served to someone asking about a state return is wrong in a way the user cannot
# detect, because the number looks plausible.
STATE_SIGNALS: tuple[str, ...] = (
    "california", "new york", "new jersey", "texas", "florida", "illinois",
    "pennsylvania", "ohio", "georgia", "michigan", "north carolina", "virginia",
    "washington state", "massachusetts", "arizona", "colorado", "maryland",
    "minnesota", "oregon", "wisconsin", "state return", "state income tax return",
    "state tax return", "my state's",
)

# Deterministic first pass. Keyword matching handles the common case without a
# model call, and the LLM pass only runs on what is left over.
PROVISION_KEYWORDS: dict[Provision, tuple[str, ...]] = {
    Provision.STANDARD_DEDUCTION: ("standard deduction", "itemize", "itemizing", "schedule a"),
    Provision.SALT: ("salt", "state and local", "property tax", "state income tax"),
    Provision.MORTGAGE_INTEREST: ("mortgage", "home loan", "acquisition debt", "form 1098"),
    Provision.CHARITABLE: ("charitable", "charity", "donation", "donated", "nonprofit"),
    Provision.MEDICAL: ("medical", "dental", "health expense", "out of pocket"),
    Provision.STUDENT_LOAN_INTEREST: ("student loan", "education loan", "form 1098-e"),
    Provision.HSA: ("hsa", "health savings", "high deductible", "hdhp"),
    Provision.IRA: ("ira", "traditional ira", "retirement contribution"),
    Provision.SENIOR_DEDUCTION: ("senior deduction", "age 65 deduction", "over 65"),
}


def detect_provisions(text: str) -> tuple[Provision, ...]:
    lowered = text.lower()
    found = [
        provision
        for provision, keywords in PROVISION_KEYWORDS.items()
        if any(kw in lowered for kw in keywords)
    ]
    return tuple(found)


def detect_tax_year(text: str, profile_year: int | None = None) -> int | None:
    """Extract an explicit tax year.

    Deliberately returns None rather than defaulting to the current calendar
    year. "This year" is ambiguous during filing season, when a taxpayer filing
    in March 2026 almost always means tax year 2025.
    """
    match = YEAR_RE.search(text)
    if match:
        return int(match.group(1))
    return profile_year


def detect_out_of_scope_jurisdiction(text: str) -> str | None:
    """Return the matched state signal, or None.

    Deliberately conservative and deliberately separate from provision
    detection: "state and local tax deduction" is a federal provision, while
    "California standard deduction" is a state return question. The SALT keyword
    list matches the former, so this check must not fire on it.
    """
    lowered = text.lower()
    if "state and local" in lowered or "salt" in lowered:
        return None
    for signal in STATE_SIGNALS:
        if signal in lowered:
            return signal
    return None


def scope_node(state: GraphState) -> GraphState:
    question = state.rewritten_question or state.question
    profile_year = state.profile.tax_year if state.profile else None
    profile_status = state.profile.filing_status if state.profile else None

    jurisdiction_signal = detect_out_of_scope_jurisdiction(question)
    if jurisdiction_signal:
        state.scope = Scope()
        state.clarifying_question = (
            f"This looks like a question about a state return ({jurisdiction_signal}). "
            "I only cover U.S. federal individual income tax deductions, and state "
            "rules differ enough that a federal figure would be misleading here. "
            "If you meant the federal deduction, say so and I will answer that."
        )
        state.outcome = Outcome.CLARIFICATION_NEEDED
        state.record("scope", resolved=False, reason="out_of_scope_jurisdiction",
                     signal=jurisdiction_signal)
        return state

    tax_year = detect_tax_year(question, profile_year)
    provisions = detect_provisions(question)

    # A year the repository has no rule data for must not resolve. The rules
    # loader would raise, but failing here produces a useful question instead of
    # a stack trace, and keeps the "ask rather than guess" rule in one place.
    if tax_year is not None and tax_year not in SUPPORTED_TAX_YEARS:
        state.scope = Scope(filing_status=profile_status, provisions=provisions)
        supported = ", ".join(str(y) for y in SUPPORTED_TAX_YEARS)
        state.clarifying_question = (
            f"I do not have rule data for tax year {tax_year}. I currently cover "
            f"{supported}. I will not answer from an adjacent year, because "
            "deduction amounts and thresholds change annually and the figure would "
            "be wrong in a way that looks right."
        )
        state.outcome = Outcome.CLARIFICATION_NEEDED
        state.record("scope", resolved=False, reason="unsupported_tax_year",
                     requested_year=tax_year)
        return state

    # TODO(milestone-3): LLM fallback for provision detection when the keyword
    # pass finds nothing, and for filing status stated in prose. Keep the
    # deterministic pass first: it is faster, free, and auditable.
    llm = get_llm(role="cheap")
    if not provisions and llm is not None:
        pass

    scope = Scope(
        tax_year=tax_year,
        filing_status=profile_status,
        provisions=provisions,
    )
    state.scope = scope

    if not scope.is_resolved:
        missing = scope.missing()
        state.clarifying_question = _ask_for(missing)
        state.outcome = Outcome.CLARIFICATION_NEEDED
        state.record("scope", resolved=False, missing=list(missing))
        return state

    state.record(
        "scope",
        resolved=True,
        tax_year=scope.tax_year,
        filing_status=scope.filing_status.value if scope.filing_status else None,
        provisions=[p.value for p in scope.provisions],
    )
    return state


def _ask_for(missing: tuple[str, ...]) -> str:
    parts = []
    if "tax_year" in missing:
        parts.append(
            "which tax year you are asking about (the rules changed between 2024 "
            "and 2025, so this materially changes the answer)"
        )
    if "provision" in missing:
        parts.append("which deduction you have in mind")
    return "Before I can answer accurately I need to know " + ", and ".join(parts) + "."
