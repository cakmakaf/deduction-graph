"""Escalation.

Writes: outcome, final_answer, escalation_reason.

Escalation attaches the partial work rather than discarding it, so a human picks
up from where the system stopped instead of starting over. That detail is what
makes escalation cheap enough to prefer over guessing.
"""

from __future__ import annotations

from deduction_graph.graph.state import GraphState, Outcome


def escalate_node(state: GraphState) -> GraphState:
    reason = "; ".join(state.check_notes) or "Low confidence in the computed answer."
    state.escalation_reason = reason
    state.outcome = Outcome.ESCALATED

    parts = [
        "I am not confident enough in this answer to give you a figure to rely on.",
        f"Reason: {reason}",
    ]
    if state.computation_trail:
        parts.append("\nWork completed so far, for whoever picks this up:")
        parts.extend(
            f"- {s.label}: {s.value if s.value is not None else ''} ({s.detail})"
            for s in state.computation_trail
        )
    if state.unverified_parameters:
        parts.append(
            "\nRule parameters used that are not yet verified: "
            + ", ".join(state.unverified_parameters)
        )

    state.final_answer = "\n".join(parts)
    state.record("escalate", reason=reason)
    return state


def finalize_node(state: GraphState) -> GraphState:
    """Terminal success path. Writes: outcome, final_answer."""
    state.outcome = Outcome.ANSWERED
    state.final_answer = state.draft_answer
    state.record("finalize", outcome=state.outcome.value)
    return state
