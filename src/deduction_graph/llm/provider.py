"""LLM provider abstraction.

Provider-agnostic behind a narrow interface, for two reasons. First, the eval
harness compares providers, so the code cannot be coupled to one. Second, a
public repository should be runnable by a reader who has a key for a different
provider than the author.

`get_llm` returns None when no provider is configured, and every node has a
degraded path for that case. The graph therefore runs end to end with no API key
at all, which is what lets the deterministic eval layers run in CI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from deduction_graph.config import settings


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str: ...


class AnthropicClient:
    """TODO(milestone-3): implement against the Anthropic messages API."""

    def __init__(self, model: str):
        self.model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        raise NotImplementedError("See milestone 3 in docs/PROPOSAL.md")


class OpenAIClient:
    """TODO(milestone-3): implement."""

    def __init__(self, model: str):
        self.model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        raise NotImplementedError("See milestone 3 in docs/PROPOSAL.md")


def get_llm(*, role: str = "primary") -> LLMClient | None:
    """Return a client for the given role, or None if unconfigured.

    Roles: "primary" for synthesis, "cheap" for intake and scope fallback.
    """
    cfg = settings()
    if not cfg.llm_enabled:
        return None

    model = cfg.primary_model if role == "primary" else cfg.cheap_model
    if cfg.llm_provider == "anthropic":
        return AnthropicClient(model)
    if cfg.llm_provider == "openai":
        return OpenAIClient(model)
    raise ValueError(
        f"Unknown DG_LLM_PROVIDER={cfg.llm_provider!r}. Use anthropic, openai, or none."
    )
