"""Structured per-node trace logging.

The requirement this satisfies: any bad answer must be attributable to the node
that produced it. Not to a prompt, not to "the model." A JSON line per node with
the run id, node name, timing, and the fields that node wrote.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any

from deduction_graph.config import settings

LOGGER = logging.getLogger("deduction_graph.trace")


def configure_logging() -> None:
    cfg = settings()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger("deduction_graph")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(cfg.log_level)
    root.propagate = False


class TraceLogger:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or str(uuid.uuid4())
        self.entries: list[dict[str, Any]] = []

    @contextmanager
    def node(self, name: str) -> Iterator[dict[str, Any]]:
        started = time.perf_counter()
        payload: dict[str, Any] = {}
        error: str | None = None
        try:
            yield payload
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            entry = {
                "run_id": self.run_id,
                "node": name,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": error,
                **payload,
            }
            self.entries.append(entry)
            LOGGER.info(json.dumps(entry, default=str))

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e, default=str) for e in self.entries)
