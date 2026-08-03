# ADR 0001: Scope as a hard pre-filter, not a ranking signal

**Status:** Accepted
**Date:** 2026-08

## Context

Tax provisions are re-published annually. The 2024 and 2025 texts for a given
provision are frequently identical except for a dollar figure. A retrieval system
asked "what is the standard deduction for a single filer in 2024" must return the
2024 passage and must not return the 2025 one.

Embedding similarity cannot make that distinction reliably. The discriminating
information is a metadata attribute, not a semantic feature, and the two passages
are near-identical in the space the embedding model measures.

## Decision

Every indexed chunk carries filterable metadata: `tax_year`, `provision`,
`filing_statuses`, `jurisdiction`, `effective_range`, `authority_tier`. A dedicated
scope-resolution node resolves the applicable values **before** retrieval executes,
and those values are applied as hard pre-filters on the candidate set.

Retrieval without a resolved scope raises `ScopeNotResolvedError`. There is no code
path that queries the store without a scope filter, and adding one would be the
most damaging change possible to this repository.

## Alternatives considered

**Metadata as ranker features.** The common approach: pass year as a boost or a
soft signal. Rejected because a boost is a preference, not a guarantee. An
out-of-scope chunk remains in the candidate set and can win on lexical or semantic
similarity, which is precisely what the ablation measures happening 50% of the time.

**Reranking only.** A cross-encoder improves ordering among candidates. It cannot
remove a candidate that should never have been retrieved, and it will confidently
rank a well-worded wrong-year passage first. Reranking is kept, but downstream of
the filter rather than instead of it.

**One index per tax year.** Functionally equivalent for the year dimension and
appealingly simple, but it does not generalize to the other four scope dimensions,
and it multiplies indexes combinatorially as those are added. Metadata filtering
handles all five dimensions with one index.

**Prompt-level instruction.** Telling the model "only use 2024 sources" and hoping.
Rejected for the obvious reason: it is a request, not a constraint, and it fails
silently.

## Consequences

Positive: wrong-scope retrieval becomes structurally impossible rather than
statistically unlikely. The scope-precision eval layer can hold a 100% gate
honestly, because the guarantee is architectural. Measured effect on the
adversarial set: precision@1 rises from 41.7% to 100%.

Negative: correctness now depends on chunk metadata being right at ingest time. A
mis-tagged chunk defeats the guarantee and does so silently, which moves the risk
from retrieval into the ingest pipeline. Mitigation: metadata assignment is tested,
and `tax_year` must be derived from the source document rather than defaulted.

The scope resolver becomes a hard dependency and a single point of failure. When it
cannot resolve, the system must ask rather than proceed, which is ADR 0003.
