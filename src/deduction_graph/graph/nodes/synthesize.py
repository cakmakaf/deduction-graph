"""Synthesis.

Writes: draft_answer, citations.

The LLM's only job in this graph: turn retrieved rule text and computed numbers
into readable prose. It is explicitly forbidden from producing a figure that is
not already in the computation trail.
"""

from __future__ import annotations

from deduction_graph.graph.state import GraphState
from deduction_graph.llm.provider import get_llm

SYSTEM_PROMPT = """You explain U.S. federal income tax deduction rules.

Hard constraints:
1. Every dollar figure in your answer MUST appear in the supplied computation \
trail. Never compute, estimate, adjust, or round a figure yourself.
2. Every rule statement MUST be supported by the supplied excerpts. If an \
excerpt does not cover something the user asked, say so plainly.
3. State the tax year explicitly in your answer. The rules differ by year and \
an answer without a year is not usable.
4. If parameters are flagged unverified, say the figures need confirmation \
against the cited source.
5. You are not providing tax advice. Do not tell the user what to do; explain \
what the rules produce for the inputs given.

Be direct and brief. No preamble."""


def _render_context(state: GraphState) -> str:
    excerpts = "\n\n".join(
        f"[{r.chunk.metadata.chunk_id}] {r.chunk.metadata.source}\n{r.chunk.text}"
        for r in state.retrieved
    )
    trail = "\n".join(
        f"- {s.label}: {s.value if s.value is not None else ''} ({s.detail})"
        for s in state.computation_trail
    )
    return f"TAX YEAR: {state.scope.tax_year}\n\nEXCERPTS:\n{excerpts}\n\nCOMPUTATION TRAIL:\n{trail}"


def synthesize_node(state: GraphState) -> GraphState:
    llm = get_llm(role="primary")
    if llm is None:
        # Degraded path: emit the computation trail directly. Less readable, but
        # correct and fully cited, which is the right failure direction.
        lines = [f"Tax year {state.scope.tax_year}."]
        if state.computation_trail:
            lines.append("")
            for step in state.computation_trail:
                value = f" {step.value}" if step.value is not None else ""
                lines.append(f"- {step.label}:{value} ({step.detail})")
        elif state.retrieved:
            # No taxpayer profile, so nothing was computed. Return the governing
            # rule text with its citation rather than an empty answer: it is what
            # the user asked for, and it is fully grounded.
            lines.append("")
            lines.append("Applicable guidance:")
            for r in state.retrieved[:3]:
                lines.append(f"- {r.chunk.metadata.source}: {r.chunk.text}")
        else:
            lines.append("")
            lines.append(
                "No applicable guidance was retrieved for this scope, so there is "
                "nothing grounded to report."
            )
        if state.unverified_parameters:
            lines.append("")
            lines.append(
                "Note: some figures come from rule parameters that are not yet "
                "verified against their cited source."
            )
        state.draft_answer = "\n".join(lines)
        state.citations = [c for r in state.tool_results for c in r.citations]
        state.record("synthesize", degraded=True, reason="no LLM configured")
        return state

    # TODO(milestone-3): call the LLM with SYSTEM_PROMPT and _render_context.
    raise NotImplementedError("See milestone 3 in docs/PROPOSAL.md")
