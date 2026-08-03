"""Configuration from environment.

No secrets in code, no secrets in the repo. See .env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("DG_LLM_PROVIDER", "none")
    primary_model: str = os.getenv("DG_PRIMARY_MODEL", "")
    cheap_model: str = os.getenv("DG_CHEAP_MODEL", "")
    vector_store: str = os.getenv("DG_VECTOR_STORE", "memory")
    chroma_persist_dir: str = os.getenv("DG_CHROMA_DIR", ".chroma")
    reranker: str = os.getenv("DG_RERANKER", "identity")
    mlflow_tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow_experiment: str = os.getenv("DG_MLFLOW_EXPERIMENT", "deduction-graph")
    strict_verified_only: bool = os.getenv("DG_STRICT_VERIFIED", "false").lower() == "true"
    log_level: str = os.getenv("DG_LOG_LEVEL", "INFO")

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none"


def settings() -> Settings:
    return Settings()
