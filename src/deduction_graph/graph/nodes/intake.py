"""Intake and query rewriting.

Writes: rewritten_question, intent.

Cheap model, high volume. Resolves pronouns and implicit references against
conversation history so downstream nodes see a self-contained question.
"""

from __future__ import annotations

from deduction_graph.graph.state import GraphState
from deduction_graph.llm.provider import get_llm

REWRITE_PROMPT = """You rewrite tax questions to be self-contained.

Given the conversation history and the latest question, produce a single \
question that carries all necessary context, resolving pronouns and implicit \
references. Do not answer it. Do not add facts the user did not state.

Also classify the intent as exactly one of:
  calculation      the user wants a number
  eligibility      the user wants to know whether a rule applies to them
  explanation      the user wants a rule explained
  comparison       the user wants two options compared
  out_of_scope     not a U.S. federal individual income tax deduction question

Return JSON only: {{"question": "...", "intent": "..."}}"""


def intake_node(state: GraphState) -> GraphState:
    llm = get_llm(role="cheap")
    if llm is None:
        # Degraded path: pass the question through unchanged rather than failing.
        # Every node has one, so the graph is testable without any API key.
        state.rewritten_question = state.question
        state.intent = "calculation"
        state.record("intake", degraded=True, reason="no LLM configured")
        return state

    # TODO(milestone-3): call the LLM, parse the JSON, validate `intent` against
    # the allowed set, and fall back to the degraded path on a parse failure
    # rather than propagating a malformed intent downstream.
    raise NotImplementedError("See milestone 3 in docs/PROPOSAL.md")
