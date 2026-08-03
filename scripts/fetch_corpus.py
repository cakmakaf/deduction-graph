#!/usr/bin/env python3
"""Corpus fetch and parse.

TODO(milestone-2): download the IRS publications listed below, extract text,
split by section, assign metadata, and write metadata-tagged chunks to
data/corpus/*.jsonl.

The PDFs are gitignored. The parsed chunks are committed, so a reader can run the
eval harness without re-downloading anything and without network access in CI.

Sources for v1 (all U.S. government works, public domain):
    Pub 17    Your Federal Income Tax
    Pub 501   Dependents, Standard Deduction, and Filing Information
    Pub 526   Charitable Contributions
    Pub 936   Home Mortgage Interest Deduction
    Pub 969   HSAs and Other Tax-Favored Health Plans
    Pub 970   Tax Benefits for Education
    Schedule A (Form 1040) Instructions
    Form 1040 Instructions

The hard requirement when implementing this: every chunk's `tax_year` must come
from the document it was parsed from, never from a default and never from the
current date. A mis-tagged chunk defeats the entire scope-filter guarantee, and it
would defeat it silently.
"""

from __future__ import annotations

import sys

PUBLICATIONS = {
    "pub17": "Your Federal Income Tax",
    "pub501": "Dependents, Standard Deduction, and Filing Information",
    "pub526": "Charitable Contributions",
    "pub936": "Home Mortgage Interest Deduction",
    "pub969": "HSAs and Other Tax-Favored Health Plans",
    "pub970": "Tax Benefits for Education",
    "scha": "Schedule A (Form 1040) Instructions",
}


def main() -> int:
    print("Not yet implemented. See milestone 2 in docs/PROPOSAL.md.")
    print()
    print("Publications to ingest for tax years 2024 and 2025:")
    for key, title in PUBLICATIONS.items():
        print(f"  {key:8s} {title}")
    print()
    print("Until this exists, the fixture corpus in evals/datasets/fixture_corpus.py")
    print("backs the tests, the eval harness, and the ablation study.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
