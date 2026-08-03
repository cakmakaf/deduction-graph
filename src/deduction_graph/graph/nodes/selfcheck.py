"""Self-check.

Writes: groundedness_passed, check_notes.

Verifies that every dollar figure in the draft answer is grounded, meaning it
appears either in the computation trail or verbatim in a retrieved source
excerpt. Both are legitimate grounding: one is a number the system computed and
can show the derivation for, the other is a number quoted from a cited authority.
A figure in neither set was invented.

This is a deterministic string check, not an LLM judgment, because the property
being checked is mechanical and a deterministic check cannot itself hallucinate.

Also enforces that the tax year is stated, because an unqualified answer is not
actionable and is the exact failure the project targets.
"""

from __future__ import annotations

import re

from deduction_graph.graph.state import GraphState

MONEY_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")


def _normalize(raw: str) -> str:
    value = raw.replace(",", "").strip()
    if "." not in value:
        value += ".00"
    return value


def extract_amounts(text: str) -> set[str]:
    return {_normalize(m) for m in MONEY_RE.findall(text)}


def selfcheck_node(state: GraphState) -> GraphState:
    notes: list[str] = []
    answer = state.draft_answer or ""

    # Grounding source 1: figures the system computed, with a shown derivation.
    computed = {
        _normalize(str(step.value.amount))
        for step in state.computation_trail
        if step.value is not None
    }
    computed |= {_normalize(str(result.value.amount)) for result in state.tool_results}

    # Grounding source 2: figures quoted verbatim from a retrieved, cited excerpt.
    retrieved_amounts: set[str] = set()
    for item in state.retrieved:
        retrieved_amounts |= extract_amounts(item.chunk.text)

    permitted = computed | retrieved_amounts

    claimed = extract_amounts(answer)
    ungrounded = sorted(claimed - permitted)
    if ungrounded:
        notes.append(
            "Answer contains dollar figures grounded in neither the computation "
            "trail nor a retrieved source excerpt: " + ", ".join(ungrounded)
        )

    if state.scope.tax_year and str(state.scope.tax_year) not in answer:
        notes.append(
            f"Answer does not state the tax year ({state.scope.tax_year}). An "
            "unqualified figure is not usable."
        )

    if state.unverified_parameters and "verif" not in answer.lower():
        notes.append(
            "Answer relies on unverified rule parameters but does not disclose it."
        )

    state.check_notes = notes
    state.groundedness_passed = not notes
    state.record(
        "selfcheck",
        passed=state.groundedness_passed,
        ungrounded_amounts=ungrounded,
        note_count=len(notes),
    )
    return state
