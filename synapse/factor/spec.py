from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


@dataclass
class FactorSpec:
    """Factor specification — single source of truth for a factor's identity, inputs, and metadata."""

    factor_id: str               # unique identifier, e.g. "momentum_6m_1m"
    name: str                    # human-readable name
    description: str             # what the factor measures
    category: str                # "momentum" | "value" | "quality" | "volatility" | "liquidity" | "event"
    inputs: list[str]            # dependent data fields, e.g. ["close", "volume"]
    lookback_days: int           # lookback window in trading days
    data_source: str             # "eastmoney" | "akshare" | "event"
    publication_lag: int         # data release delay in days (prevents look-ahead bias)
    compute_fn: Optional[Callable] = None  # computation function (None for abstract specs)
    version: str = "1.0.0"       # semver

    def __post_init__(self) -> None:
        if not self.factor_id:
            raise ValueError("factor_id must not be empty")

    @classmethod
    def from_yaml(cls, path: str | Path) -> FactorSpec:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Remove compute_fn from YAML data — not serializable
        data.pop("compute_fn", None)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        dump_data = asdict(self)
        # Remove compute_fn — not serializable to YAML
        dump_data.pop("compute_fn", None)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(dump_data, f, default_flow_style=False, allow_unicode=True)

    def next_version(self) -> FactorSpec:
        """Return a new FactorSpec with bumped patch version."""
        parts = self.version.split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        new = FactorSpec(**{k: v for k, v in asdict(self).items() if k != "compute_fn"})
        new.compute_fn = self.compute_fn
        new.version = f"{major}.{minor}.{patch + 1}"
        return new
