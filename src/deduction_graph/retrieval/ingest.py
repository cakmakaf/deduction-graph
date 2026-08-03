"""Corpus ingestion.

TODO(milestone-2): fetch and parse the IRS publications listed in
docs/PROPOSAL.md section 5. Downloaded PDFs are gitignored; the parsed and
metadata-tagged output is what gets committed, so a reader can run the evals
without re-downloading anything.

Provenance requirement: every chunk's `source` must name the publication and the
tax year, because that string is what appears in a user-facing citation.
"""

from __future__ import annotations

from pathlib import Path

from deduction_graph.retrieval.schema import Chunk

CORPUS_DIR = Path("data/corpus")


def load_committed_corpus(path: Path = CORPUS_DIR) -> list[Chunk]:
    """Load pre-parsed, metadata-tagged chunks from JSONL.

    TODO(milestone-2): implement.
    """
    raise NotImplementedError("See milestone 2 in docs/PROPOSAL.md")


def build_fixture_corpus() -> list[Chunk]:
    """Small hand-authored corpus for tests and the ablation study.

    Lives in evals/datasets/fixture_corpus.py so the adversarial cross-year cases
    and the corpus they run against stay together.
    """
    from evals.datasets.fixture_corpus import FIXTURE_CHUNKS

    return list(FIXTURE_CHUNKS)
