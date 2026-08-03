"""MLflow integration for the eval harness.

Tracks eval runs, prompt versions, retrieval configuration, and per-layer scores,
so a quality regression is attributable to a specific change rather than to
vibes. Degrades to a no-op when mlflow is absent, so CI works without it.

TODO(milestone-5): log the retrieval config and prompt hashes as params, and the
five layer scores as metrics.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from deduction_graph.config import settings


class NoOpRun:
    def log_param(self, key: str, value: Any) -> None: ...
    def log_metric(self, key: str, value: float) -> None: ...
    def log_dict(self, obj: dict, path: str) -> None: ...


@contextmanager
def eval_run(name: str) -> Iterator[Any]:
    try:
        import mlflow
    except ImportError:
        yield NoOpRun()
        return

    cfg = settings()
    mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
    mlflow.set_experiment(cfg.mlflow_experiment)
    with mlflow.start_run(run_name=name):
        yield mlflow
