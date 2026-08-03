#!/usr/bin/env python3
"""Synthetic taxpayer profile generator.

Seeded and deterministic, so a generated set is reproducible from the seed alone
and does not need to be committed.

No real PII. Ever. That is not a policy note, it is the reason this generator
exists instead of a sample of real records.

    python scripts/generate_synthetic_profiles.py --count 200 --year 2025 --out profiles.json
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date
from pathlib import Path

from deduction_graph import SUPPORTED_TAX_YEARS
from deduction_graph.types import FilingStatus, TaxpayerProfile, money

COVERAGE = ("none", "self_only", "family")


def generate(seed: int, count: int, tax_year: int) -> list[TaxpayerProfile]:
    rng = random.Random(seed)
    profiles: list[TaxpayerProfile] = []

    for i in range(count):
        status = rng.choice(list(FilingStatus))
        agi = rng.randrange(25_000, 750_000, 500)
        married = status.is_married
        age = rng.randint(22, 82)
        has_mortgage = rng.random() < 0.55
        balance = rng.randrange(80_000, 1_400_000, 5_000) if has_mortgage else 0
        # Roughly plausible interest, not a real amortization schedule.
        interest = int(balance * rng.uniform(0.028, 0.068)) if has_mortgage else 0

        profiles.append(
            TaxpayerProfile(
                profile_id=f"syn-{tax_year}-{seed}-{i:05d}",
                tax_year=tax_year,
                filing_status=status,
                agi=money(agi),
                magi=money(agi),
                age=age,
                spouse_age=rng.randint(22, 82) if married else None,
                is_blind=rng.random() < 0.02,
                spouse_is_blind=married and rng.random() < 0.02,
                state_local_income_or_sales_tax=money(int(agi * rng.uniform(0.0, 0.09))),
                state_local_property_tax=money(rng.randrange(0, 30_000, 250)),
                mortgage_interest_paid=money(interest),
                mortgage_balance=money(balance),
                mortgage_origination_date=(
                    date(rng.randint(2005, tax_year), rng.randint(1, 12), rng.randint(1, 28))
                    if has_mortgage
                    else None
                ),
                charitable_cash=money(rng.randrange(0, 40_000, 100)),
                charitable_noncash=money(rng.randrange(0, 15_000, 100)),
                medical_expenses=money(rng.randrange(0, 60_000, 100)),
                student_loan_interest_paid=money(rng.randrange(0, 4_000, 50)),
                hsa_coverage=rng.choice(COVERAGE),
                hsa_contributions=money(rng.randrange(0, 10_000, 50)),
                ira_contributions=money(rng.randrange(0, 8_000, 100)),
            )
        )
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--year", type=int, default=2025, choices=SUPPORTED_TAX_YEARS)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic_profiles.json"))
    args = parser.parse_args()

    profiles = generate(args.seed, args.count, args.year)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps([p.model_dump(mode="json") for p in profiles], indent=2)
    )
    print(f"Wrote {len(profiles)} synthetic profiles for {args.year} to {args.out}")
    print(f"Reproduce with --seed {args.seed} --count {args.count} --year {args.year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
