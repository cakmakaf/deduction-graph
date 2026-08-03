# ADR 0004: Rule parameters as versioned data with mandatory provenance

**Status:** Accepted
**Date:** 2026-08

## Context

Deduction amounts, caps, thresholds, and phase-out ranges change annually, and
occasionally mid-year by legislation. They can live in three places: hardcoded in
calculation logic, embedded in prompt text, or as external data.

## Decision

Rule parameters live in per-tax-year YAML under
`src/deduction_graph/rules/data/<year>.yaml`. Every parameter block carries:

- `source` — the citation, statute or publication, specific enough to check against
- `verified` — whether a human has confirmed the value against that source
- `note` — optional, used where the mechanics are uncertain

The loader records every parameter read, and `ToolResult.unverified_parameters`
carries the unverified ones to the caller, into the API response envelope, and to
the user. An answer built on unverified data does not look identical to one built
on verified data.

Values ship as `verified: false`. `tests/test_verified_flags.py` is an `xfail` that
becomes a permanent gate once verification is complete, at which point a newly
added unverified parameter fails CI.

## Alternatives considered

**Hardcoded in tool logic.** Fastest to write. Rejected: a rule change becomes a
code change, provenance lives in a comment if anywhere, and there is no way to
report that a figure is unconfirmed.

**In prompt text.** Rejected outright. It makes correctness a function of prompt
adherence, offers no diff granularity, and the model can silently paraphrase a
threshold.

**A database.** Better for a multi-tenant production system with an update
workflow. Rejected for a public repository, where a YAML diff in a pull request is
the reviewable artifact and a database would make the rules invisible to a reader.

**Ship values as verified and fix later.** Rejected, and this is the decision that
matters most. A project whose central claim is "the wrong year's figure is the
dangerous failure mode" cannot assert its own figures are correct before anyone has
checked them. The unverified flag is not an unfinished-work marker, it is the
project applying its own thesis to itself.

## Consequences

Positive: adding a tax year is a data change plus golden cases, with no code
change. Provenance is per-parameter and machine-readable, so the verification work
queue is generated rather than tracked by hand. The same code path serves every
year, so a fix cannot land in one year and miss another.

Negative: a fresh clone has a failing test, which needs the README to explain it or
it reads as a broken repository. Verification is genuinely tedious: every threshold
needs a source check, and correcting a value requires recomputing the affected
golden cases by hand. That is the cost of the guarantee being real.
