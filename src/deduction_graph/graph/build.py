"""Graph assembly.

An explicit StateGraph, not an agent loop. Every edge is declared here, so the
control flow is readable in one screen and a reviewer can see there is no path
from intake to synthesis that bypasses scope resolution.

Falls back to a plain sequential runner when langgraph is not installed, so the
repository is runnable and testable before the dependency is added.
"""

from __future__ import annotations

from collections.abc import Callable

from deduction_graph.graph.nodes.compute import compute_node
from deduction_graph.graph.nodes.escalate import escalate_node, finalize_node
from deduction_graph.graph.nodes.intake import intake_node
from deduction_graph.graph.nodes.retrieve import retrieve_node
from deduction_graph.graph.nodes.scope import scope_node
from deduction_graph.graph.nodes.selfcheck import selfcheck_node
from deduction_graph.graph.nodes.synthesize import synthesize_node
from deduction_graph.graph.state import GraphState, Outcome


def route_after_scope(state: GraphState) -> str:
    """Ask rather than guess. The single most important edge in the graph."""
    return "clarify" if not state.scope.is_resolved else "retrieve"


def route_after_selfcheck(state: GraphState) -> str:
    return "finalize" if state.groundedness_passed else "escalate"


def clarify_node(state: GraphState) -> GraphState:
    """Terminal. Returns the clarifying question as the answer."""
    state.outcome = Outcome.CLARIFICATION_NEEDED
    state.final_answer = state.clarifying_question
    state.record("clarify", question=state.clarifying_question)
    return state


def build_graph():
    """Build the LangGraph StateGraph.

    TODO(milestone-3): the node set and edges below are final; what remains is
    binding them to a compiled StateGraph with a checkpointer for multi-turn
    conversations.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "langgraph is not installed. Install with `pip install -e '.[graph]'`, "
            "or use run_sequential() which needs no extra dependency."
        ) from exc

    graph = StateGraph(GraphState)
    graph.add_node("intake", intake_node)
    graph.add_node("scope", scope_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("compute", compute_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("selfcheck", selfcheck_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "scope")
    graph.add_conditional_edges(
        "scope", route_after_scope, {"clarify": "clarify", "retrieve": "retrieve"}
    )
    graph.add_edge("retrieve", "compute")
    graph.add_edge("compute", "synthesize")
    graph.add_edge("synthesize", "selfcheck")
    graph.add_conditional_edges(
        "selfcheck",
        route_after_selfcheck,
        {"finalize": "finalize", "escalate": "escalate"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("finalize", END)
    graph.add_edge("escalate", END)
    return graph.compile()


def run_sequential(state: GraphState) -> GraphState:
    """Dependency-free runner with identical control flow.

    Exists so the eval harness and the test suite exercise the real routing
    logic without requiring langgraph, and so the two implementations can be
    diffed if they ever disagree.
    """
    steps: list[Callable[[GraphState], GraphState]] = [intake_node, scope_node]
    for step in steps:
        state = step(state)

    if not state.scope.is_resolved:
        return clarify_node(state)

    for step in (retrieve_node, compute_node, synthesize_node, selfcheck_node):
        state = step(state)

    return finalize_node(state) if state.groundedness_passed else escalate_node(state)
