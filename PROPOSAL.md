# Project Proposal: `deduction-graph`

**An auditable agentic assistant for U.S. federal income tax deduction questions**

Author: Ahmet Faruk Cakmak, Ph.D.
Status: Proposal
Last updated: August 2026

---

## 1. Why this project exists

Most public LLM portfolio projects are a vector store, a retrieval call, and a prompt. They demonstrate that a person can wire up a framework. They do not demonstrate the thing that actually decides whether an LLM feature ships inside a regulated enterprise: bounded control flow, retrieval that respects scope as a hard constraint, deterministic computation held outside the model, and an evaluation harness that gates releases.

This repository is an independent, from-scratch build that demonstrates those properties in a domain where the stakes are legible to anyone: personal income tax deductions. It uses only publicly available IRS guidance and fully synthetic taxpayer data. No employer data, code, or internal documentation is involved.

It is also a teaching artifact. I facilitate machine learning and AI cohorts for UC Berkeley and Carnegie Mellon through Emeritus, and this repository is intended to be readable as a reference implementation of a governed agentic system, not just runnable.

**This is not tax advice.** The system is a software engineering demonstration and will state so prominently in the README, in the API response envelope, and in the CLI banner.

---

## 2. The problem being modeled

A taxpayer asks: *"I paid $14,200 in mortgage interest and $9,800 in state and local taxes. Should I itemize?"*

That question cannot be answered by retrieving a document. It requires:

1. **Scope resolution.** Which tax year? Filing status? Are they subject to a phase-out or a cap?
2. **Authoritative retrieval.** The rule text that is actually in effect for that year and that filing status, not a similar-sounding rule from a different year.
3. **Deterministic computation.** Standard deduction comparison, SALT cap application, AGI-dependent limits. Arithmetic, not token prediction.
4. **A grounded, cited answer, or an escalation.** With a traceable path from the number back to the rule.

### The failure mode that drives the design

The dangerous output is not an answer that sounds wrong. It is a **confidently correct-sounding answer computed under the wrong tax year or the wrong filing status.** Tax law changes on an annual cadence, and provisions sunset. Standard deduction amounts, contribution limits, and phase-out thresholds all shift. A naive RAG system retrieves the semantically nearest chunk, and near-identical wording across tax years makes that chunk very likely to be the wrong one.

Making that class of error *structurally impossible* rather than *statistically unlikely* is the central engineering claim of this repository.

---

## 3. Architecture

An explicit **LangGraph state graph**, not a free-running agent loop. Every transition is defined, inspectable, and logged.

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
                             ▼  (tax_year, filing_status, jurisdiction, provision_set)
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

### 3.1 Scope resolution and scoped retrieval

The engineering centerpiece. Every corpus chunk carries metadata:

| Field | Example |
|---|---|
| `tax_year` | 2024, 2025 |
| `filing_status` | single, mfj, mfs, hoh, qss |
| `provision` | standard_deduction, salt, mortgage_interest, charitable, hsa, student_loan_interest |
| `source` | Pub 17, Pub 501, Pub 526, Pub 936, Pub 969, 1040 Instructions |
| `effective_range` | date interval |
| `authority_tier` | statute, regulation, publication, instruction |

The scope-resolution node resolves these **before** retrieval runs, so they enter the retrieval call as **hard pre-filters**, not as soft signals for the ranker. If scope cannot be resolved from the query and conversation state, the graph asks a clarifying question rather than resolving optimistically.

Retrieval itself is hybrid dense plus BM25 with a cross-encoder rerank, because provision text across tax years differs by a handful of tokens and pure embedding similarity cannot reliably discriminate.

### 3.2 Deterministic computation

**No tax arithmetic inside the LLM.** All computation runs in typed tools with Pydantic-validated schemas:

- `compare_standard_vs_itemized(profile, tax_year) -> DeductionComparison`
- `apply_salt_cap(state_local_taxes, filing_status, tax_year) -> CappedAmount`
- `mortgage_interest_deduction(balance, interest_paid, acquisition_date, tax_year) -> Deduction`
- `charitable_limit(agi, contribution_type, amount, tax_year) -> Limit`
- `contribution_limit(account_type, age, coverage, tax_year) -> Limit`
- `phase_out(agi, provision, filing_status, tax_year) -> PhaseOutResult`

Rule parameters live in versioned YAML keyed by tax year, so a rule change is a data change with a diff and a test, not a prompt edit. Every tool returns a structured trace that becomes part of the answer envelope.

### 3.3 Observability

Per-node structured trace logging, so any bad answer attributes to the step that produced it rather than to an opaque prompt. MLflow tracks eval runs, prompt versions, and retrieval configurations, so a quality regression is attributable to a specific change.

---

## 4. The evaluation harness

Built **before** anything user-facing, and treated as the primary deliverable of the repository. Five layers:

1. **Retrieval quality.** Recall@k and MRR against a hand-labeled query-to-chunk set.
2. **Scope precision.** The layer this project exists to demonstrate. An adversarial set of queries about provisions whose text is near-identical across tax years, measuring how often the system retrieves or cites the wrong year or filing status. Target: zero, because it is enforced structurally.
3. **Numeric correctness.** Golden-file tests. Synthetic taxpayer profiles with independently hand-computed expected deductions. Exact match required.
4. **Groundedness.** Every factual claim in the answer must trace to a retrieved span or a tool output. Scored automatically, spot-checked manually.
5. **Escalation preference.** Deliberately out-of-scope and under-specified queries. The system is expected to escalate or ask rather than guess. Coverage is explicitly **not** the optimization target.

All five run in CI as a release gate. Results published to a scorecard in the README so the numbers are visible without cloning.

---

## 5. Data

| Asset | Source | Notes |
|---|---|---|
| Rule corpus | IRS Publications 17, 501, 526, 936, 969 and Form 1040 Instructions | Public domain U.S. government works |
| Rule parameters | Same, transcribed into versioned YAML | Reviewed against source, cited per value |
| Taxpayer profiles | Synthetic, seeded generator | No real PII, ever |
| Eval sets | Hand-authored, committed to the repo | Including adversarial cross-year cases |

Scope for v1: **individual federal income tax deductions, tax years 2024 and 2025.** No state returns, no business returns, no credits. Narrow and correct beats broad and approximate, and a defensible scope boundary is itself part of the demonstration.

---

## 6. Repository layout

```
deduction-graph/
├── README.md                  scorecard, architecture diagram, disclaimer
├── docs/
│   ├── PROPOSAL.md            this document
│   ├── ARCHITECTURE.md        node-by-node walkthrough
│   ├── EVALUATION.md          harness design and current results
│   └── adr/                   architecture decision records
├── src/deduction_graph/
│   ├── graph/                 LangGraph nodes, state schema, edges
│   ├── retrieval/             ingest, chunking, metadata, hybrid search, rerank
│   ├── tools/                 typed calculation tools
│   ├── rules/                 versioned YAML by tax year
│   ├── observability/         trace logging, MLflow integration
│   └── api/                   FastAPI service
├── evals/                     five harness layers, golden files, adversarial sets
├── notebooks/                 retrieval ablations, teaching walkthroughs
├── tests/
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/         lint, type-check, tests, eval gate
```

---

## 7. Milestones

| # | Milestone | Deliverable |
|---|---|---|
| 0 | Scaffold | Repo, packaging, CI skeleton, pre-commit, disclaimer in place |
| 1 | Rules and tools | Versioned YAML for 2024 and 2025, typed calculation tools, golden-file numeric tests passing |
| 2 | Corpus and retrieval | Ingest pipeline, metadata schema, hybrid retrieval with hard pre-filters, retrieval eval baseline |
| 3 | Graph | LangGraph nodes and state, clarifying-question path, escalation path, end-to-end run |
| 4 | Evaluation harness | All five layers, CI gate, published scorecard |
| 5 | Observability | Per-node traces, MLflow runs, trace viewer notebook |
| 6 | Serving | FastAPI service, Dockerfile, compose stack, CLI |
| 7 | Ablation study | Naive RAG vs scoped retrieval on the adversarial cross-year set, written up as the headline result |

Milestone 7 is the one that carries the project. A published side-by-side showing naive semantic retrieval failing on cross-year queries while scoped retrieval does not is a concrete, reproducible claim rather than an architecture diagram.

---

## 8. What this repository is meant to demonstrate

- Bounded, inspectable agent control flow rather than a free-running loop
- Scope as a hard retrieval constraint rather than a ranking hint
- Deterministic computation held strictly outside the model
- Evaluation as a release gate, with escalation preferred over confident guessing
- Observability sufficient to attribute a failure to a node
- Production packaging: typed interfaces, CI, containerization, versioned rule data

---

## 9. Open decisions

1. **Name.** `deduction-graph`, `taxgraph`, or `form1040-agent`. Current preference is the first, because it names the domain and the architecture.
2. **Vector store.** Local first for reproducibility, Chroma or LanceDB, with a pluggable interface so a hosted store can be swapped in.
3. **Model provider.** Provider-agnostic behind an interface, with a documented reference configuration and per-run cost tracking in the eval harness.
4. **Rerank model.** A local cross-encoder keeps the repo fully runnable offline for the reader. Worth benchmarking against a hosted reranker in the ablation.
5. **Depth of the state-tax boundary.** Excluded from v1, but worth documenting as a stated extension so the scope decision reads as deliberate.

---

*Disclaimer: This project is a software engineering demonstration. It does not provide tax advice, and its outputs must not be relied upon for filing. Consult a qualified tax professional.*
