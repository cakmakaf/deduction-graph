"""Layer 2: scope precision.

The layer this repository exists to demonstrate. For each adversarial cross-year
case, measure whether retrieval ever returns a chunk from the wrong tax year.

Gate: 1.0, and this gate is not negotiable. Unlike a recall metric where 0.95 is
respectable, a single wrong-year retrieval means the architectural guarantee does
not hold, and the guarantee is the whole claim.
"""

from __future__ import annotations

from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore
from deduction_graph.types import Scope
from evals.datasets.adversarial_cross_year import ADVERSARIAL_CASES
from evals.datasets.fixture_corpus import FIXTURE_CHUNKS
from evals.result import CaseResult, LayerResult


def build_scoped_retriever() -> HybridRetriever:
    store = InMemoryStore()
    store.add(list(FIXTURE_CHUNKS))
    return HybridRetriever(sparse=store)


def run_scope_precision() -> LayerResult:
    retriever = build_scoped_retriever()
    cases: list[CaseResult] = []
    total_violations = 0

    for case in ADVERSARIAL_CASES:
        scope = Scope(
            tax_year=case.tax_year,
            filing_status=case.filing_status,
            provisions=case.provisions,
        )
        retrieved = retriever.retrieve(case.question, scope, k=5)
        returned_ids = [r.chunk.metadata.chunk_id for r in retrieved]
        wrong_year = [
            r.chunk.metadata.chunk_id
            for r in retrieved
            if r.chunk.metadata.tax_year != case.tax_year
        ]
        forbidden_hits = [cid for cid in returned_ids if cid in case.forbidden_chunk_ids]
        expected_hit = any(cid in case.expected_chunk_ids for cid in returned_ids)

        violations = set(wrong_year) | set(forbidden_hits)
        total_violations += len(violations)
        passed = not violations and expected_hit

        if violations:
            detail = f"returned out-of-scope chunks: {sorted(violations)}"
        elif not expected_hit:
            detail = (
                f"expected one of {list(case.expected_chunk_ids)}, got {returned_ids}"
            )
        else:
            detail = ""

        cases.append(CaseResult(case_id=case.case_id, passed=passed, detail=detail))

    return LayerResult(
        layer="scope_precision",
        cases=tuple(cases),
        gate_threshold=1.0,
        metrics={
            "wrong_year_retrievals": float(total_violations),
            "case_count": float(len(cases)),
        },
    )
