"""Eval harness entry point.

Runs all five layers, prints a scorecard, and exits non-zero if any gate fails.
This is what CI calls, so a release genuinely cannot ship past a failing gate.

Usage:
    python -m evals.runner
    python -m evals.runner --layer scope_precision
    python -m evals.runner --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable

from evals.layers import (
    run_escalation_preference,
    run_groundedness,
    run_numeric_correctness,
    run_retrieval_quality,
    run_scope_precision,
)
from evals.result import LayerResult

LAYERS: dict[str, Callable[[], LayerResult]] = {
    "retrieval_quality": run_retrieval_quality,
    "scope_precision": run_scope_precision,
    "numeric_correctness": run_numeric_correctness,
    "groundedness": run_groundedness,
    "escalation_preference": run_escalation_preference,
}


def print_scorecard(results: list[LayerResult]) -> None:
    print()
    print("deduction-graph evaluation scorecard")
    print("=" * 72)
    header = f"{'layer':26s} {'pass':>6s} {'rate':>8s} {'gate':>8s}  {'status':>6s}"
    print(header)
    print("-" * 72)
    for r in results:
        passed = sum(1 for c in r.cases if c.passed)
        print(
            f"{r.layer:26s} {passed:>3}/{len(r.cases):<3} {r.pass_rate:>7.1%} "
            f"{r.gate_threshold:>7.0%}  {'PASS' if r.gate_passed else 'FAIL':>6s}"
        )
    print("-" * 72)

    for r in results:
        if r.metrics:
            extras = "  ".join(f"{k}={v}" for k, v in r.metrics.items())
            print(f"  {r.layer}: {extras}")

    failures = [(r.layer, c) for r in results for c in r.failures]
    if failures:
        print()
        print("Failures")
        print("-" * 72)
        for layer, case in failures:
            print(f"  [{layer}] {case.case_id}")
            if case.detail:
                print(f"      {case.detail}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deduction-graph eval harness")
    parser.add_argument("--layer", choices=sorted(LAYERS), help="Run a single layer")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    args = parser.parse_args()

    selected = [args.layer] if args.layer else list(LAYERS)
    results = [LAYERS[name]() for name in selected]

    if args.json:
        print(
            json.dumps(
                {
                    r.layer: {
                        "pass_rate": r.pass_rate,
                        "gate_threshold": r.gate_threshold,
                        "gate_passed": r.gate_passed,
                        "metrics": r.metrics,
                        "failures": [
                            {"case_id": c.case_id, "detail": c.detail} for c in r.failures
                        ],
                    }
                    for r in results
                },
                indent=2,
            )
        )
    else:
        print_scorecard(results)

    all_passed = all(r.gate_passed for r in results)
    if not all_passed:
        print("RELEASE GATE FAILED. One or more eval layers is below threshold.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
