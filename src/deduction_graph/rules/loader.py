"""Versioned rule parameter loading.

Design decision (see docs/adr/0004-rules-as-versioned-data.md): tax parameters
are DATA, not code and not prompt text. A statutory change is then a reviewable
diff with a test attached, and the same code path serves every tax year.

Every parameter carries a `source` and a `verified` flag. Reading an unverified
parameter is allowed but always recorded, so an answer built on unverified data
says so instead of looking identical to a verified one.
"""

from __future__ import annotations

import contextlib
import functools
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

DATA_DIR = Path(__file__).parent / "data"


class UnverifiedParameterError(RuntimeError):
    """Raised only in strict mode, used by the numeric-correctness eval layer."""


class Parameter(BaseModel):
    """A single rule value plus its provenance."""

    model_config = ConfigDict(frozen=True)

    path: str
    value: Any
    source: str
    verified: bool
    note: str | None = None

    @property
    def decimal(self) -> Decimal:
        return Decimal(str(self.value))


class RuleSet:
    """Parameters for one tax year, with provenance tracking on every read."""

    def __init__(self, tax_year: int, raw: dict[str, Any], *, strict: bool = False):
        self.tax_year = tax_year
        self._raw = raw
        self._strict = strict
        self._reads: list[Parameter] = []
        self._depth = 0

    # -- lookup ----------------------------------------------------------------

    def get(self, path: str, *, value_key: str | None = None) -> Parameter:
        """Fetch a parameter by dotted path.

        `value_key` names the field holding the value when it is not the
        conventional `amount`. Falls back through amount, rate, value.
        """
        node = self._resolve(path)
        if not isinstance(node, dict):
            raise KeyError(f"{path!r} is a leaf, not a parameter block")

        keys = [value_key] if value_key else ["amount", "rate", "value"]
        for key in keys:
            if key and key in node:
                param = Parameter(
                    path=f"{path}.{key}",
                    value=node[key],
                    source=node.get("source", "MISSING SOURCE"),
                    verified=bool(node.get("verified", False)),
                    note=node.get("note"),
                )
                break
        else:
            raise KeyError(
                f"No value key {keys} under {path!r} in tax year {self.tax_year}. "
                f"Available: {sorted(node)}"
            )

        if not param.verified:
            if self._strict:
                raise UnverifiedParameterError(
                    f"{param.path} (tax year {self.tax_year}) is unverified. "
                    f"Source to check: {param.source}"
                )
        self._reads.append(param)
        return param

    def get_optional(self, path: str, *, value_key: str | None = None) -> Parameter | None:
        try:
            return self.get(path, value_key=value_key)
        except KeyError:
            return None

    def raw_block(self, path: str) -> dict[str, Any]:
        node = self._resolve(path)
        if not isinstance(node, dict):
            raise KeyError(f"{path!r} is not a block")
        return node

    def has(self, path: str) -> bool:
        try:
            self._resolve(path)
            return True
        except KeyError:
            return False

    def _resolve(self, path: str) -> Any:
        node: Any = self._raw
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                raise KeyError(
                    f"Rule path {path!r} not found for tax year {self.tax_year} "
                    f"(failed at {part!r})"
                )
            node = node[part]
        return node

    # -- provenance ------------------------------------------------------------

    @property
    def reads(self) -> tuple[Parameter, ...]:
        return tuple(self._reads)

    def unverified_reads(self) -> tuple[str, ...]:
        # Deduplicated, order preserved. A composite tool reads the same
        # parameter more than once and the user should see it listed once.
        return tuple(dict.fromkeys(p.path for p in self._reads if not p.verified))

    def reset_reads(self) -> None:
        self._reads.clear()

    @contextlib.contextmanager
    def tracking_scope(self) -> Iterator["RuleSet"]:
        """Re-entrant provenance tracking.

        Composite tools call other tools with the same RuleSet. A naive reset at
        the top of every tool call wipes the parent's accumulated reads, so the
        outer result under-reports which parameters it actually depended on. That
        is a provenance bug rather than a cosmetic one: an answer would claim
        fewer unverified inputs than it really used. Only the outermost scope
        resets.
        """
        if self._depth == 0:
            self._reads.clear()
        self._depth += 1
        try:
            yield self
        finally:
            self._depth -= 1

    # -- introspection used by tests and CI ------------------------------------

    def all_parameters(self) -> list[Parameter]:
        """Flatten every parameter block in the file, for the verification gate."""
        found: list[Parameter] = []

        def walk(node: Any, prefix: str) -> None:
            if not isinstance(node, dict):
                return
            if "source" in node:
                for key in ("amount", "rate", "value"):
                    if key in node:
                        found.append(
                            Parameter(
                                path=f"{prefix}.{key}" if prefix else key,
                                value=node[key],
                                source=node["source"],
                                verified=bool(node.get("verified", False)),
                                note=node.get("note"),
                            )
                        )
                        break
                else:
                    found.append(
                        Parameter(
                            path=prefix or "<root>",
                            value=None,
                            source=node["source"],
                            verified=bool(node.get("verified", False)),
                            note=node.get("note"),
                        )
                    )
            for key, child in node.items():
                if isinstance(child, dict):
                    walk(child, f"{prefix}.{key}" if prefix else key)

        walk(self._raw, "")
        return found


@functools.lru_cache(maxsize=None)
def _load_raw(tax_year: int) -> dict[str, Any]:
    path = DATA_DIR / f"{tax_year}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in DATA_DIR.glob("*.yaml"))
        raise FileNotFoundError(
            f"No rule data for tax year {tax_year}. Available: {available}. "
            "Refusing to fall back to an adjacent year, which is the exact error "
            "class this system exists to prevent."
        )
    with path.open() as fh:
        raw = yaml.safe_load(fh)
    if raw.get("tax_year") != tax_year:
        raise ValueError(
            f"{path.name} declares tax_year={raw.get('tax_year')!r}, expected {tax_year}"
        )
    return raw


def load_rules(tax_year: int, *, strict: bool = False) -> RuleSet:
    """Load a RuleSet for the given tax year.

    Deliberately has no default year and no nearest-year fallback. A caller that
    does not know the tax year must resolve it first.
    """
    return RuleSet(tax_year, _load_raw(tax_year), strict=strict)
