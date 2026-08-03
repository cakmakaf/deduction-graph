"""Computation.

Writes: tool_results, computation_trail, unverified_parameters, warnings.

No LLM. Tools are selected from the registry by resolved provision and executed
deterministically. The LLM never sees a number it is expected to manipulate; it
only narrates numbers this node produced.
"""

from __future__ import annotations

from deduction_graph.graph.state import GraphState
from deduction_graph.rules import load_rules
from deduction_graph.tools.registry import tools_for
from deduction_graph.types import Provision


def compute_node(state: GraphState) -> GraphState:
    if state.profile is None:
        state.record("compute", skipped=True, reason="no taxpayer profile supplied")
        return state

    assert state.scope.tax_year is not None
    rules = load_rules(state.scope.tax_year)

    provisions = state.scope.provisions
    # A "should I itemize" question needs every itemizable component, not just
    # the one the user named.
    if Provision.STANDARD_DEDUCTION in provisions:
        provisions = provisions + (
            Provision.SALT,
            Provision.MORTGAGE_INTEREST,
            Provision.CHARITABLE,
            Provision.MEDICAL,
        )

    selected = tools_for(tuple(dict.fromkeys(provisions)))
    for tool in selected:
        result = tool(state.profile, rules)
        state.tool_results.append(result)
        state.computation_trail.extend(result.steps)
        state.unverified_parameters.extend(result.unverified_parameters)
        state.warnings.extend(result.warnings)

    state.unverified_parameters = list(dict.fromkeys(state.unverified_parameters))
    state.warnings = list(dict.fromkeys(state.warnings))

    state.record(
        "compute",
        tools_run=[t.name for t in selected],
        results={r.tool: str(r.value) for r in state.tool_results},
        unverified_parameter_count=len(state.unverified_parameters),
    )
    return state
