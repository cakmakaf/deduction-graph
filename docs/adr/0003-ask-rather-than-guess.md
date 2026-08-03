# ADR 0003: Ask rather than guess, and prefer escalation to coverage

**Status:** Accepted
**Date:** 2026-08

## Context

A user asks "what is my standard deduction?" with no tax year. The convenient
behavior is to assume the current one. During filing season that assumption is
usually wrong: a taxpayer filing in March 2026 almost always means tax year 2025.

The same pressure appears everywhere. Unknown mortgage origination date, unstated
filing status, a question about a state return, a year with no rule data. Each has
a plausible default, and each default produces a confident answer computed against
the wrong law.

## Decision

The system asks. Specifically:

- `detect_tax_year` returns `None` rather than defaulting to the current year, and
  treats "this year" as ambiguous.
- `load_rules` has no default year and no nearest-year fallback. An unsupported
  year raises rather than serving adjacent data.
- The scope node refuses out-of-scope jurisdictions (state returns) and unsupported
  tax years with a specific explanation rather than a generic failure.
- Tools that cannot compute confidently emit a warning, and a warning routes to
  escalation rather than being appended to an answer.
- Escalation attaches the completed partial work, so a human resumes rather than
  restarts.

Coverage is explicitly **not** an optimization target. This is enforced by
`escalation_preference`, a gating eval layer at 100%.

## Alternatives considered

**Default to the current year, disclose the assumption.** Rejected. Disclosure in
prose does not survive being read quickly, and the figure is what the user takes
away. An assumption that changes the answer is not a footnote.

**Answer with a confidence score.** Rejected. It moves the decision to a user who
has less information than the system does, and a calibrated confidence number on a
tax figure invites exactly the wrong kind of reliance.

**Answer for all plausible interpretations.** Genuinely tempting: give both the
2024 and 2025 figures and let the user pick. Rejected because it scales badly
across five scope dimensions, and because a user who does not know which year they
are asking about also does not know which figure to select.

## Consequences

Positive: the system's answers can be trusted precisely because it refuses
frequently. The escalation layer prevents the ratchet where every future
improvement adds coverage and quietly erodes the refusal path.

Negative: more clarifying turns, which is real friction and would show up in any
user-satisfaction metric. The trade is defensible in a regulated domain and would
not be in a general-purpose assistant.

Building this eval layer surfaced two genuine defects on first run: the scope node
resolved "California standard deduction for 2025" to a federal answer, and resolved
tax year 2027 despite no rule data existing. Both are fixed. Neither would have
been found by the unit tests, which is the argument for the layer.
