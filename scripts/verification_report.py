#!/usr/bin/env python3
"""Rule parameter verification work queue.

Prints every unverified parameter grouped by source document, so verification can
be done one publication at a time instead of jumping between them.

    python scripts/verification_report.py
    python scripts/verification_report.py --year 2025
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from deduction_graph import SUPPORTED_TAX_YEARS
from deduction_graph.rules import load_rules


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, choices=SUPPORTED_TAX_YEARS)
    args = parser.parse_args()

    years = [args.year] if args.year else list(SUPPORTED_TAX_YEARS)
    grand_total = grand_verified = 0

    for year in years:
        params = load_rules(year).all_parameters()
        verified = [p for p in params if p.verified]
        unverified = [p for p in params if not p.verified]
        grand_total += len(params)
        grand_verified += len(verified)

        print()
        print(f"Tax year {year}: {len(verified)}/{len(params)} verified")
        print("=" * 78)

        if not unverified:
            print("  All parameters verified.")
            continue

        by_source: dict[str, list] = defaultdict(list)
        for p in unverified:
            by_source[p.source].append(p)

        for source in sorted(by_source):
            print()
            print(f"  {source}")
            for p in by_source[source]:
                print(f"    [ ] {p.path:58s} = {p.value}")
                if p.note:
                    print(f"        note: {p.note}")

    print()
    print("=" * 78)
    print(f"Total: {grand_verified}/{grand_total} parameters verified")
    print()
    print("To verify a parameter: open the cited source, confirm the value, then set")
    print("`verified: true` on that block in src/deduction_graph/rules/data/<year>.yaml.")
    print("If the value differs, correct it AND recompute any affected golden case in")
    print("evals/datasets/golden_profiles.py by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
