# ADR 0002: No tax arithmetic inside the language model

**Status:** Accepted
**Date:** 2026-08

## Context

Tax deduction figures are the output a user acts on. They involve percentage
floors, statutory caps, proportional limitations, phase-out interpolation, and
conditional branching on dates and filing status. Language models produce
plausible arithmetic, which is a different property from correct arithmetic, and a
plausible tax figure is indistinguishable from a correct one to the person reading
it.

## Decision

All computation runs in typed tools that are pure functions of
`(TaxpayerProfile, RuleSet)`. No tool calls an LLM, performs retrieval, or reads
global state. Each returns a `ToolResult` carrying the value, a step-by-step audit
trail, citations, warnings, and the list of unverified parameters it depended on.

The model's only job is prose. The `selfcheck` node extracts every dollar figure
from the generated answer and rejects any that does not appear in the computation
trail. That check is deterministic string comparison rather than an LLM judge,
because the property is mechanical and a deterministic check cannot itself
hallucinate.

Currency is `Decimal`, and `Money` raises on a `float` at the type boundary.

## Alternatives considered

**LLM computes, then a checker verifies.** Attractive because it needs no tool
layer, but it inverts the burden: the system generates something that might be
wrong and then tries to catch it. Every check is another thing that can miss.

**Code interpreter / generated Python.** More flexible, and genuinely useful for
open-ended analysis. Rejected here because the calculations are a known, finite,
regulated set. Generated code for a fixed rule set trades an auditable
implementation for an unauditable one, and the audit trail is the deliverable.

**Floats with rounding at the end.** Rejected. Binary floating point introduces
error that then gets rounded into a figure someone might file against. The cost of
`Decimal` is nil and the failure mode is silent.

## Consequences

Positive: numbers are reproducible, so golden-file tests are meaningful rather than
decorative. 25 hand-computed cases hold the arithmetic to exact match with no
tolerance band. The audit trail is a byproduct of the design rather than extra work.

Negative: coverage is bounded by implemented tools. A question about an
unimplemented provision cannot be answered even if the model "knows" the rule,
which pushes work into the escalation path. This is the intended trade, and the
escalation-preference eval layer is what keeps it from eroding as coverage grows.

Adding a provision means writing a tool, a rule block, and a golden case. That is
deliberate friction on the path that most needs it.
