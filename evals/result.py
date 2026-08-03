"""Shared eval result types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    passed: bool
    detail: str = ""


class LayerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    layer: str
    cases: tuple[CaseResult, ...]
    metrics: dict[str, float] = Field(default_factory=dict)
    gate_threshold: float
    gate_metric: str = "pass_rate"

    @property
    def pass_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.passed) / len(self.cases)

    @property
    def gate_value(self) -> float:
        if self.gate_metric == "pass_rate":
            return self.pass_rate
        return self.metrics.get(self.gate_metric, 0.0)

    @property
    def gate_passed(self) -> bool:
        return self.gate_value >= self.gate_threshold

    @property
    def failures(self) -> tuple[CaseResult, ...]:
        return tuple(c for c in self.cases if not c.passed)
