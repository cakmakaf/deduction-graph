"""Command line interface.

    python -m deduction_graph.cli ask "standard deduction for a single filer in 2024"
    python -m deduction_graph.cli tools
    python -m deduction_graph.cli rules 2025 --unverified
"""

from __future__ import annotations

import argparse
import json
import sys

from deduction_graph import SUPPORTED_TAX_YEARS, __version__
from deduction_graph.api.schemas import DISCLAIMER
from deduction_graph.graph.build import run_sequential
from deduction_graph.graph.nodes.retrieve import set_retriever
from deduction_graph.graph.state import GraphState
from deduction_graph.observability.trace import configure_logging
from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore
from deduction_graph.rules import load_rules
from deduction_graph.tools.registry import tool_schemas


def _wire_retriever() -> None:
    from evals.datasets.fixture_corpus import FIXTURE_CHUNKS

    store = InMemoryStore()
    store.add(list(FIXTURE_CHUNKS))
    set_retriever(HybridRetriever(sparse=store))


def cmd_ask(args: argparse.Namespace) -> int:
    _wire_retriever()
    state = run_sequential(GraphState(question=args.question))

    print()
    print(f"[{state.outcome.value}]")
    print(state.final_answer or "(no answer produced)")
    if state.computation_trail:
        print()
        print("Computation trail:")
        for step in state.computation_trail:
            value = f"  {step.value}" if step.value is not None else ""
            print(f"  - {step.label}:{value}")
            print(f"      {step.detail}")
    if state.unverified_parameters:
        print()
        print("Unverified rule parameters used:")
        for path in state.unverified_parameters:
            print(f"  - {path}")
    if state.warnings:
        print()
        print("Warnings:")
        for w in state.warnings:
            print(f"  - {w}")
    print()
    print(DISCLAIMER)
    return 0


def cmd_tools(args: argparse.Namespace) -> int:
    print(json.dumps(tool_schemas(), indent=2))
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    rules = load_rules(args.tax_year)
    params = rules.all_parameters()
    if args.unverified:
        params = [p for p in params if not p.verified]
    for p in params:
        flag = "OK " if p.verified else "TODO"
        print(f"{flag}  {p.path:60s} {str(p.value):>14s}  {p.source}")
    print()
    verified = sum(1 for p in rules.all_parameters() if p.verified)
    total = len(rules.all_parameters())
    print(f"{verified}/{total} parameters verified for tax year {args.tax_year}")
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="deduction-graph", description=DISCLAIMER)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="Ask a deduction question")
    p_ask.add_argument("question")
    p_ask.set_defaults(func=cmd_ask)

    p_tools = sub.add_parser("tools", help="List the deterministic calculation tools")
    p_tools.set_defaults(func=cmd_tools)

    p_rules = sub.add_parser("rules", help="Inspect rule parameters and verification state")
    p_rules.add_argument("tax_year", type=int, choices=SUPPORTED_TAX_YEARS)
    p_rules.add_argument("--unverified", action="store_true", help="Only unverified")
    p_rules.set_defaults(func=cmd_rules)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
