"""Layer 1: retrieval quality.

Recall@k and MRR against the labeled query-to-chunk set. Distinct from scope
precision: this measures whether the right chunk surfaces at all, while scope
precision measures whether a wrong-scope chunk can surface. Both matter, and a
system can pass one while failing the other.

Gate: 0.90 recall@5. A real threshold rather than 1.0, because recall genuinely
trades off against corpus size and this is a ranking quality metric, not a
correctness guarantee.
"""

from __future__ import annotations

from deduction_graph.types import Scope
from evals.datasets.adversarial_cross_year import ADVERSARIAL_CASES
from evals.layers.scope_precision import build_scoped_retriever
from evals.result import CaseResult, LayerResult


def run_retrieval_quality(*, k: int = 5) -> LayerResult:
    retriever = build_scoped_retriever()
    cases: list[CaseResult] = []
    reciprocal_ranks: list[float] = []

    for case in ADVERSARIAL_CASES:
        scope = Scope(
            tax_year=case.tax_year,
            filing_status=case.filing_status,
            provisions=case.provisions,
        )
        retrieved = retriever.retrieve(case.question, scope, k=k)
        ids = [r.chunk.metadata.chunk_id for r in retrieved]

        rank = next(
            (i for i, cid in enumerate(ids, start=1) if cid in case.expected_chunk_ids),
            None,
        )
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        passed = rank is not None
        cases.append(
            CaseResult(
                case_id=case.case_id,
                passed=passed,
                detail="" if passed else f"expected chunk not in top {k}: {ids}",
            )
        )

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0
    recall = sum(1 for c in cases if c.passed) / len(cases) if cases else 0.0
    return LayerResult(
        layer="retrieval_quality",
        cases=tuple(cases),
        gate_threshold=0.90,
        gate_metric=f"recall_at_{k}",
        metrics={f"recall_at_{k}": round(recall, 4), "mrr": round(mrr, 4)},
    )
