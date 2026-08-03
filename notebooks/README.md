# Notebooks

Exploratory and teaching notebooks. Nothing here is on the release path: the
eval harness in `evals/` is what gates a release, and these are for looking at
things.

Planned:

- `01_retrieval_ablation.ipynb` — the milestone 7 result with plots. The table
  from `python -m evals.ablation` is the source of truth; this visualizes it.
- `02_trace_viewer.ipynb` — load a run's JSONL trace and walk it node by node,
  which is how you demonstrate that a bad answer attributes to a step.
- `03_rule_diff_2024_2025.ipynb` — diff the two rule files and show which
  taxpayer profiles change outcome as a result. This is the clearest way to see
  why tax year cannot be a soft retrieval signal.
- `04_teaching_walkthrough.ipynb` — the graph explained node by node, for cohort
  use.

Keep outputs cleared before committing.
