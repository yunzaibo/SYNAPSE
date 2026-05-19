"""Index Constituent Module — Point-in-time index membership tracking.

Handles loading, change detection, and membership checks for
China A-share index constituents (CSI300, CSI500, CSI1000, SSE50, etc.).

Data layout on disk:
  data/market/index/{index_code}/members.csv  — latest snapshot per date
  data/market/index/{index_code}/changes.csv  — add/remove events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IndexCode enum
# ---------------------------------------------------------------------------

class IndexCode(str, Enum):
    """Well-known China A-share index codes."""

    CSI300 = "000300.SH"
    CSI500 = "000905.SH"
    CSI1000 = "000852.SH"
    SSE50 = "000016.SH"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# ConstituentSnapshot frozen dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConstituentSnapshot:
    """Point-in-time snapshot of index membership."""

    index_code: str
    date: date
    members: frozenset[str]
    weights: dict[str, Decimal] | None

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "index_code": self.index_code,
            "date": self.date.isoformat(),
            "members": sorted(self.members),
            "weights": (
                {k: str(v) for k, v in self.weights.items()}
                if self.weights is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, d: dict) -> ConstituentSnapshot:
        """Deserialize from dict."""
        weights_raw = d.get("weights")
        weights: dict[str, Decimal] | None = None
        if weights_raw is not None:
            weights = {k: Decimal(v) for k, v in weights_raw.items()}
        return cls(
            index_code=d["index_code"],
            date=date.fromisoformat(d["date"]),
            members=frozenset(d["members"]),
            weights=weights,
        )


# ---------------------------------------------------------------------------
# ConstituentChange frozen dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ConstituentChange:
    """A single constituent add/remove event."""

    date: date
    ticker: str
    action: Literal["add", "remove"]
    index_code: str
    reason: str  # "rebalance", "ipo", "delist", "suspend"

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "date": self.date.isoformat(),
            "ticker": self.ticker,
            "action": self.action,
            "index_code": self.index_code,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ConstituentChange:
        """Deserialize from dict."""
        return cls(
            date=date.fromisoformat(d["date"]),
            ticker=d["ticker"],
            action=d["action"],
            index_code=d["index_code"],
            reason=d["reason"],
        )


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _index_dir(index_code: str, data_dir: str | Path) -> Path:
    """Resolve the directory for an index's data files."""
    return Path(data_dir) / "index" / index_code


def _load_members_csv(path: Path) -> pd.DataFrame:
    """Load members CSV, returning empty DataFrame if file is missing."""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


def _load_changes_csv(path: Path) -> pd.DataFrame:
    """Load changes CSV, returning empty DataFrame if file is missing."""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_constituents(
    index_code: str,
    d: date,
    data_dir: str | Path = "data/market",
) -> ConstituentSnapshot:
    """Load index constituents for a given date (point-in-time).

    Resolves to the latest snapshot on or before the target date.
    Uses string comparison on YYYY-MM-DD formatted dates for sorting
    to avoid pandas Timestamp roundtrip issues.

    Args:
        index_code: Index code string (e.g. "000300.SH").
        d: Target date.
        data_dir: Base directory for market data.

    Returns:
        ConstituentSnapshot with members and optional weights.

    Raises:
        FileNotFoundError: If the index directory does not exist.
    """
    idx_dir = _index_dir(index_code, data_dir)
    if not idx_dir.exists():
        raise FileNotFoundError(
            f"Index directory not found: {idx_dir}. "
            f"Create it and place members.csv inside."
        )

    members_path = idx_dir / "members.csv"
    df = _load_members_csv(members_path)

    if df.empty:
        return ConstituentSnapshot(
            index_code=index_code,
            date=d,
            members=frozenset(),
            weights=None,
        )

    # Ensure 'date' column is string-sorted
    if "date" not in df.columns:
        # Single-snapshot file without date column — treat as always valid
        return _build_snapshot_from_df(df, index_code, d)

    df["date"] = df["date"].astype(str)
    target_str = d.isoformat()

    # Filter rows where date <= target
    df_valid = df[df["date"] <= target_str]
    if df_valid.empty:
        # All snapshots are after the target date — use earliest available
        earliest = df["date"].min()
        df_valid = df[df["date"] == earliest]
        logger.info(
            "No snapshot for %s on or before %s; using earliest: %s",
            index_code, d, earliest,
        )
    else:
        # Use the latest valid snapshot
        latest = df_valid["date"].max()
        df_valid = df_valid[df_valid["date"] == latest]

    return _build_snapshot_from_df(df_valid, index_code, d)


def _build_snapshot_from_df(
    df: pd.DataFrame,
    index_code: str,
    target_date: date,
) -> ConstituentSnapshot:
    """Build a ConstituentSnapshot from a filtered DataFrame."""
    tickers = set()
    weights: dict[str, Decimal] | None = None

    if "ticker" in df.columns:
        tickers = set(df["ticker"].dropna().tolist())

    if "weight" in df.columns:
        weight_series = df.set_index("ticker")["weight"].dropna()
        if not weight_series.empty:
            weights = {k: Decimal(str(v)) for k, v in weight_series.items()}

    # Determine snapshot date from the data
    snapshot_date = target_date
    if "date" in df.columns and not df["date"].empty:
        try:
            snapshot_date = date.fromisoformat(df["date"].iloc[0])
        except (ValueError, TypeError):
            pass

    return ConstituentSnapshot(
        index_code=index_code,
        date=snapshot_date,
        members=frozenset(tickers),
        weights=weights,
    )


def load_constituent_changes(
    index_code: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/market",
) -> list[ConstituentChange]:
    """Load constituent changes within a date range, sorted by date.

    Args:
        index_code: Index code string.
        start: Start date (inclusive).
        end: End date (inclusive).
        data_dir: Base directory for market data.

    Returns:
        Sorted list of ConstituentChange objects.
    """
    idx_dir = _index_dir(index_code, data_dir)
    changes_path = idx_dir / "changes.csv"
    df = _load_changes_csv(changes_path)

    if df.empty:
        return []

    df["date"] = df["date"].astype(str)
    start_str = start.isoformat()
    end_str = end.isoformat()

    df_filtered = df[(df["date"] >= start_str) & (df["date"] <= end_str)]
    df_filtered = df_filtered.sort_values("date").reset_index(drop=True)

    changes: list[ConstituentChange] = []
    for _, row in df_filtered.iterrows():
        changes.append(ConstituentChange(
            date=date.fromisoformat(row["date"]),
            ticker=row["ticker"],
            action=row["action"],
            index_code=index_code,
            reason=row.get("reason", "rebalance"),
        ))

    return changes


def is_member(
    index_code: str,
    ticker: str,
    d: date,
    data_dir: str | Path = "data/market",
) -> bool:
    """Quick membership check for a ticker in an index on a given date.

    Args:
        index_code: Index code string.
        ticker: Stock ticker.
        d: Target date.
        data_dir: Base directory for market data.

    Returns:
        True if the ticker is a member.
    """
    snapshot = load_constituents(index_code, d, data_dir=data_dir)
    return ticker in snapshot.members


def constituent_tickers(
    index_code: str,
    d: date,
    data_dir: str | Path = "data/market",
) -> frozenset[str]:
    """Return the set of member tickers for an index on a given date.

    Args:
        index_code: Index code string.
        d: Target date.
        data_dir: Base directory for market data.

    Returns:
        Frozenset of ticker strings.
    """
    snapshot = load_constituents(index_code, d, data_dir=data_dir)
    return snapshot.members
