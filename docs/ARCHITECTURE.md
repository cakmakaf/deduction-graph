# Architecture

Node-by-node walkthrough. For the reasoning behind the four load-bearing
decisions, see the [ADRs](adr/).

## Control flow

An explicit `StateGraph`, assembled in `src/deduction_graph/graph/build.py`. Every
edge is declared in one function so the whole control flow fits on a screen, and a
reviewer can verify there is no path from intake to synthesis that skips scope
resolution.

`run_sequential()` mirrors the same routing with no `langgraph` dependency. It
exists so the eval harness and the test suite exercise real routing logic without
the dependency, and so the two implementations can be diffed if they ever disagree.

## State

One typed `GraphState` flows through every node. Each node's docstring declares
what it writes, and `state.record(node, **fields)` appends a structured trace entry.
That is what makes a bad answer attributable to a step rather than to "the model."

## Nodes

### 1. intake

*Writes: `rewritten_question`, `intent`.*

Resolves pronouns and implicit references against conversation history so
downstream nodes see a self-contained question. Classifies intent into one of
five values. Cheap model, high volume.

Degraded path when no LLM is configured: pass the question through unchanged.
Every node has one of these, which is what lets the graph run end to end with no
API key.

### 2. scope

*Writes: `scope`, `clarifying_question`.*

The most important node. Resolves `tax_year`, `filing_status`, `provisions`, and
`jurisdiction` **before** retrieval, so they become hard pre-filters.

Order of operations, and the order matters:

1. **Jurisdiction check.** "California standard deduction" is a state return
   question and is refused. Care is needed here: "state and local tax deduction" is
   a *federal* provision, so the check explicitly does not fire on SALT keywords.
2. **Tax year.** Explicit four-digit year, else the profile's year, else `None`.
   Never the current calendar year. "This year" is treated as ambiguous.
3. **Supported year check.** A year with no rule data produces a specific
   clarifying question rather than a downstream exception.
4. **Provisions.** Deterministic keyword pass first, because it is faster, free,
   and auditable. LLM fallback only for what the keywords miss.

If scope is unresolved, the node routes to a clarifying question. It does not guess.

### 3. retrieve

*Writes: `retrieved`.*

Thin by design. All interesting behavior lives in `filters.py` and the retriever,
both independently testable. Raises `ScopeNotResolvedError` if reached with an
unresolved scope, which would be a wiring bug and should be loud.

Records the tax years present in the returned set, so a scope-filter regression is
visible in the trace rather than only in the eval.

### 4. compute

*Writes: `tool_results`, `computation_trail`, `unverified_parameters`, `warnings`.*

No LLM. Selects tools from the registry by resolved provision and runs them
deterministically. One piece of domain logic lives here: a standard-deduction
question expands to include every itemizable component, because "should I itemize"
cannot be answered from one provision.

### 5. synthesize

*Writes: `draft_answer`, `citations`.*

The model's only job. The system prompt forbids producing any figure not already in
the computation trail, requires stating the tax year, and requires disclosing
unverified parameters.

Degraded path emits the computation trail directly. Less readable, fully correct
and cited, which is the right direction to fail.

### 6. selfcheck

*Writes: `groundedness_passed`, `check_notes`.*

Three deterministic checks:

1. Every dollar figure in the answer appears in the computation trail.
2. The tax year is stated. An unqualified figure is not usable.
3. If unverified parameters were used, the answer says so.

Deterministic rather than an LLM judge, because the properties are mechanical and a
deterministic check cannot itself hallucinate. The groundedness eval layer calls
this same function, so the eval and the runtime guard cannot disagree.

### 7. escalate / finalize / clarify

Three terminals. Escalation attaches the completed partial work and the unverified
parameter list, so a human resumes rather than restarts. That detail is what makes
escalation cheap enough to actually prefer over guessing.

## Retrieval

```
Scope ──▶ to_store_filter() ──▶ hard metadata pre-filter
                                        │
                                        ▼
                        candidate set (scope-valid only)
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
                   BM25 sparse                    dense (m2)
                        └───────────────┬───────────────┘
                                        ▼
                          reciprocal rank fusion
                                        ▼
                            cross-encoder rerank (m2)
                                        ▼
                                     top k
```

RRF is used instead of score normalization because BM25 scores and cosine
similarities are not on the same scale, and normalizing introduces a tuning
parameter that has to be re-tuned whenever the corpus changes.

`filters.passes()` and `filters.to_store_filter()` are kept structurally parallel,
and a test asserts they agree on every fixture chunk. The in-memory store is what
CI runs; a production store is what users hit. If their scope semantics drift, CI
is green while production is wrong.

`NaiveStore` deliberately skips the filter. It exists only for the ablation, so the
comparison is measured rather than asserted. It is never wired into the graph.

## Computation

```
DeductionTool.__call__
  ├─ guard: profile.tax_year == rules.tax_year  (hard error on mismatch)
  ├─ rules.tracking_scope()                     (re-entrant provenance)
  ├─ compute(profile, rules) -> ToolResult
  └─ attach unverified_parameters
```

The re-entrancy matters. A naive reset at the top of every tool call wiped the
parent's accumulated reads when a composite tool called children with the same
`RuleSet`, so the outer result under-reported which unverified parameters it
depended on. That was a real bug found during the initial build, and
`test_nested_tracking_scope_does_not_lose_parent_reads` guards it.

Eight tools, all pure functions of `(profile, rules)`, all returning a
`ComputationStep` trail a reviewer can reproduce by hand.

## Observability

`TraceLogger` emits one JSON line per node with run id, node name, duration, error,
and the fields that node wrote. `MLflow` tracks eval runs, prompt versions, and
retrieval configuration, degrading to a no-op when absent so CI works without it.
