# deduction-graph

**An auditable agentic assistant for U.S. federal income tax deduction questions.**

Most public LLM projects demonstrate that someone can wire up a framework. This
one demonstrates the properties that decide whether an LLM feature ships inside a
regulated enterprise: bounded control flow, retrieval that treats scope as a hard
constraint, deterministic computation held outside the model, and an evaluation
harness that gates releases.

> **This is not tax advice.** It is a software engineering demonstration built on
> public IRS guidance and fully synthetic taxpayer data. See [DISCLAIMER.md](DISCLAIMER.md).

---

## The headline result

Tax law changes annually. Provision text across adjacent years is often identical
except for a figure. That makes the dangerous failure mode not a wrong-sounding
answer but a **confidently correct-sounding answer computed under the wrong tax
year.**

Same corpus, same queries, same scoring function. The only difference is whether
resolved scope enters retrieval as a hard pre-filter or not at all:

| metric | naive retrieval | scoped pre-filter |
|---|---|---|
| wrong tax year at rank 1 | **6 / 12 queries** | **0 / 12** |
| wrong-year chunks in top 5 | 30 | 0 |
| precision@1 | 41.7% | **100%** |

Reproduce it: `python -m evals.ablation`

Naive retrieval puts the wrong tax year first on half the queries. Not because the
retriever is bad, but because the information needed to discriminate is metadata,
not semantics. A reranker cannot fix this; it only reorders a candidate set that
already contains the wrong answer. Filtering before search makes the error
structurally impossible rather than statistically unlikely.

## Evaluation scorecard

Five layers, all gating, all runnable with no API key and no model download.

| layer | cases | rate | gate |
|---|---|---|---|
| retrieval_quality | 12 | 100% | 90% recall@5 |
| scope_precision | 12 | 100% | **100%** |
| numeric_correctness | 25 | 100% | **100%** |
| groundedness | 12 | 100% | **100%** |
| escalation_preference | 8 | 100% | **100%** |

`python -m evals.runner` — exits non-zero if any gate fails, and CI runs it on
every pull request.

Four gates are set at 100% deliberately. For a ranking metric, 95% is respectable.
For "did we cite the wrong year's law" or "did we invent a dollar figure," 95% means
the guarantee does not hold, and the guarantee is the entire claim.

---

## Architecture

```
                    ┌─────────────────┐
   user query ─────▶│ intake &        │
                    │ query rewrite   │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐   unresolvable
                    │ scope           │──────────────────▶ clarifying question
                    │ resolution      │
                    └────────┬────────┘
                             ▼  tax_year, filing_status, jurisdiction, provisions
                    ┌─────────────────┐
                    │ retrieval       │  hard metadata pre-filters
                    │ hybrid + rerank │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ computation     │  typed tools, no LLM arithmetic
                    │ (typed tools)   │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ synthesis       │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐   fails check
                    │ self-check      │──────────────────▶ escalate
                    │ (groundedness)  │                     (with partial work)
                    └────────┬────────┘
                             ▼
                    answer + citations + computation trace
```

An explicit LangGraph state graph, not a free-running agent loop. Every edge is
declared in one file, so a reviewer can confirm there is no path from intake to
synthesis that bypasses scope resolution.

### Four design decisions worth defending

**1. Scope is a hard pre-filter, not a ranking signal.** Every chunk carries
`tax_year`, `provision`, `filing_statuses`, `jurisdiction`, `effective_range`, and
`authority_tier`. The scope node resolves those *before* retrieval, and
`ScopeNotResolvedError` makes it impossible to query without them. See
[ADR 0001](docs/adr/0001-scoped-retrieval.md).

**2. No tax arithmetic inside the LLM.** All computation runs in typed tools
returning `ToolResult` with a step-by-step audit trail. The model narrates numbers
it did not produce, and the self-check node rejects any dollar figure absent from
the trail. See [ADR 0002](docs/adr/0002-no-llm-arithmetic.md).

**3. Ask rather than guess.** When scope cannot be resolved, the graph asks. It
does not default to the current calendar year, and the rules loader refuses to
fall back to an adjacent year. Coverage is explicitly not the optimization target.
See [ADR 0003](docs/adr/0003-ask-rather-than-guess.md).

**4. Rule parameters are versioned data, not code or prompt text.** A statutory
change is a YAML diff with a citation and a test, not a prompt edit. Every
parameter carries `source` and `verified`, and reading an unverified one is
recorded and surfaced all the way to the user. See
[ADR 0004](docs/adr/0004-rules-as-versioned-data.md).

---

## Quickstart

```bash
git clone https://github.com/afcakmak/deduction-graph
cd deduction-graph
pip install -e ".[dev]"

make test        # 55 tests
make eval        # the five-layer release gate
make ablation    # the headline result
make verify      # which rule parameters still need checking
```

No API key needed for any of the above. Every node has a degraded path, so the
graph runs end to end and the harness passes with `DG_LLM_PROVIDER=none`, which is
the default. That is deliberate: a reader who cannot run the evals cannot check
the claims.

```bash
python -m deduction_graph.cli ask "What is the standard deduction for a single filer in 2024?"
python -m deduction_graph.cli rules 2025 --unverified
make serve   # FastAPI on :8000, then POST /ask
```

---

## Current status

Honest accounting of what is built and what is scaffolded.

| Component | Status |
|---|---|
| Rule engine, versioned YAML, provenance tracking | **Complete, tested** |
| Eight typed calculation tools | **Complete, 25 hand-computed golden cases** |
| Scope resolution and hard pre-filtering | **Complete, tested** |
| Sparse retrieval (BM25) with scope filter | **Complete, tested** |
| Graph state, routing, all seven nodes | **Complete**, LLM calls stubbed |
| Five-layer eval harness, CI gate | **Complete** |
| Ablation study | **Complete** |
| FastAPI service, CLI, Docker, CI | **Complete** |
| Dense retrieval, cross-encoder rerank | Scaffolded, milestone 2 |
| IRS corpus ingest | Scaffolded, milestone 2, fixture corpus meanwhile |
| LLM synthesis and intake | Scaffolded, milestone 3, degraded path works |
| MLflow run tracking | Scaffolded, milestone 5 |

**Rule parameters are drafted, not verified.** Every value carries
`verified: false` until a human confirms it against the cited primary source, and
`tests/test_verified_flags.py` is an `xfail` that becomes a permanent gate once
verification is done. This is not an oversight left in by accident; a system whose
whole premise is "the wrong year's figure is the dangerous failure" has no business
asserting its own figures are right before someone has checked them.

Tax year 2025 needs the most care. Legislation enacted in July 2025 changed the
standard deduction and the SALT cap, and the values in `2025.yaml` reflect that
legislation as drafted, with phase-down mechanics that are easy to get wrong.

Run `python scripts/verification_report.py` for the work queue, grouped by source
document.

---

## Repository layout

```
src/deduction_graph/
├── types.py          domain models; Money rejects float
├── rules/            versioned YAML by tax year + provenance-tracking loader
├── tools/            eight typed, deterministic calculation tools
├── retrieval/        metadata schema, scope filters, stores, hybrid, rerank
├── graph/            state, seven nodes, explicit edges
├── observability/    per-node trace logging, MLflow
├── llm/              provider-agnostic interface
├── api/              FastAPI
└── cli.py

evals/                the primary deliverable
├── datasets/         adversarial corpus, 25 golden cases, escalation cases
├── layers/           the five gating layers
├── ablation.py       naive vs scoped, the headline result
└── runner.py         scorecard + non-zero exit on gate failure
```

## Documentation

- [Project proposal](docs/PROPOSAL.md) — scope, milestones, open decisions
- [Architecture](docs/ARCHITECTURE.md) — node-by-node walkthrough
- [Evaluation](docs/EVALUATION.md) — harness design, why each gate is where it is
- [ADRs](docs/adr/) — the four decisions above, with the alternatives rejected

## License

MIT. IRS publications are U.S. government works in the public domain. All
taxpayer data in this repository is synthetic.
