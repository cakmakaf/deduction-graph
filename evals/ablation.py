"""Milestone 7: the headline result.

Naive retrieval versus scoped retrieval on the adversarial cross-year set, over
the same corpus with the same query set and the same scoring function. The only
difference is whether scope enters as a hard pre-filter or not at all.

This is the measurement that makes the architecture claim falsifiable instead of
rhetorical. Run it with `python -m evals.ablation`.
"""

from __future__ import annotations

from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore, NaiveStore
from deduction_graph.types import Scope
from evals.datasets.adversarial_cross_year import ADVERSARIAL_CASES
from evals.datasets.fixture_corpus import FIXTURE_CHUNKS


def _run(retriever: HybridRetriever, k: int = 5) -> dict[str, float]:
    wrong_year = 0
    wrong_year_at_1 = 0
    correct_at_1 = 0
    total = len(ADVERSARIAL_CASES)

    for case in ADVERSARIAL_CASES:
        scope = Scope(
            tax_year=case.tax_year,
            filing_status=case.filing_status,
            provisions=case.provisions,
        )
        results = retriever.retrieve(case.question, scope, k=k)
        if not results:
            continue
        top = results[0].chunk.metadata
        if top.tax_year != case.tax_year:
            wrong_year_at_1 += 1
        if top.chunk_id in case.expected_chunk_ids:
            correct_at_1 += 1
        wrong_year += sum(
            1 for r in results if r.chunk.metadata.tax_year != case.tax_year
        )

    return {
        "cases": float(total),
        "wrong_year_chunks_in_top_k": float(wrong_year),
        "wrong_year_at_rank_1": float(wrong_year_at_1),
        "wrong_year_rate_at_1": round(wrong_year_at_1 / total, 4),
        "correct_at_rank_1": float(correct_at_1),
        "precision_at_1": round(correct_at_1 / total, 4),
    }


def run_ablation(k: int = 5) -> dict[str, dict[str, float]]:
    scoped_store = InMemoryStore()
    scoped_store.add(list(FIXTURE_CHUNKS))

    naive_store = NaiveStore()
    naive_store.add(list(FIXTURE_CHUNKS))

    return {
        "naive_no_scope_filter": _run(HybridRetriever(sparse=naive_store), k=k),
        "scoped_hard_prefilter": _run(HybridRetriever(sparse=scoped_store), k=k),
    }


def main() -> None:
    results = run_ablation()
    naive = results["naive_no_scope_filter"]
    scoped = results["scoped_hard_prefilter"]

    print("Ablation: scope as a hard pre-filter versus no scope filter")
    print(f"Corpus: {len(FIXTURE_CHUNKS)} chunks   Queries: {len(ADVERSARIAL_CASES)}")
    print()
    header = f"{'metric':34s} {'naive':>12s} {'scoped':>12s}"
    print(header)
    print("-" * len(header))
    for key in naive:
        print(f"{key:34s} {naive[key]:>12} {scoped[key]:>12}")
    print()
    print(
        "Reading: wrong_year_at_rank_1 is the number of queries where the top "
        "result came from the wrong tax year. Under scoped retrieval this is "
        "structurally zero, because out-of-scope chunks never enter the candidate "
        "set. Under naive retrieval it is whatever lexical similarity happens to "
        "produce, which is the point."
    )


if __name__ == "__main__":
    main()
