"""Northbound Flow Module — 北向资金 (Stock Connect) data for China A-Shares.

Handles loading, fetching, momentum calculation, and signal generation
for northbound capital flow data via Shanghai/Shenzhen Stock Connect.

Part of IMPL-003: Northbound Flow integration.
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
# Enum
# ---------------------------------------------------------------------------

class NorthChannel(str, Enum):
    """Stock Connect channel."""

    HGT = "沪股通"
    SGT = "深股通"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NorthboundFlow:
    """Single northbound flow record.

    Attributes
    ----------
    date:
        Trading date.
    channel:
        Stock Connect channel (沪股通 or 深股通).
    buy_amount:
        Net buy amount in 100M yuan (亿元).
    sell_amount:
        Net sell amount in 100M yuan.
    net_amount:
        Net flow = buy - sell in 100M yuan.
    total_buy:
        Cumulative buy amount in 100M yuan.
    total_sell:
        Cumulative sell amount in 100M yuan.
    quota_used_pct:
        Daily quota usage percentage.
    source:
        Data source identifier.
    """

    date: date
    channel: NorthChannel
    buy_amount: Decimal
    sell_amount: Decimal
    net_amount: Decimal
    total_buy: Decimal
    total_sell: Decimal
    quota_used_pct: Decimal
    source: str

    def to_dict(self) -> dict:
        """Serialize to dict with string-encoded Decimal values."""
        return {
            "date": self.date.isoformat(),
            "channel": self.channel.value,
            "buy_amount": str(self.buy_amount),
            "sell_amount": str(self.sell_amount),
            "net_amount": str(self.net_amount),
            "total_buy": str(self.total_buy),
            "total_sell": str(self.total_sell),
            "quota_used_pct": str(self.quota_used_pct),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> NorthboundFlow:
        """Deserialize from dict, accepting string or numeric Decimal fields."""
        return cls(
            date=date.fromisoformat(d["date"]),
            channel=NorthChannel(d["channel"]),
            buy_amount=Decimal(str(d["buy_amount"])),
            sell_amount=Decimal(str(d["sell_amount"])),
            net_amount=Decimal(str(d["net_amount"])),
            total_buy=Decimal(str(d["total_buy"])),
            total_sell=Decimal(str(d["total_sell"])),
            quota_used_pct=Decimal(str(d["quota_used_pct"])),
            source=d["source"],
        )


# ---------------------------------------------------------------------------
# Load from local files
# ---------------------------------------------------------------------------

def load_northbound_flow(
    start: date,
    end: date,
    channel: NorthChannel | None = None,
    data_dir: str | Path = "data/market",
) -> pd.DataFrame:
    """Load northbound flow data from local CSV/Parquet files.

    File layout::

        {data_dir}/northbound/{channel.value}.csv
        {data_dir}/northbound/{channel.value}.parquet

    When *channel* is ``None``, loads and concatenates both channels.

    Returns
    -------
    pd.DataFrame
        Columns match NorthboundFlow fields. Filtered to [start, end].
        Empty DataFrame if no matching records.

    Raises
    ------
    FileNotFoundError
        If the expected data file does not exist.
    """
    nb_dir = Path(data_dir) / "northbound"

    if channel is not None:
        channels = [channel]
    else:
        channels = list(NorthChannel)

    frames: list[pd.DataFrame] = []
    last_error: FileNotFoundError | None = None

    for ch in channels:
        csv_path = nb_dir / f"{ch.value}.csv"
        parquet_path = nb_dir / f"{ch.value}.parquet"

        if csv_path.exists():
            df = pd.read_csv(csv_path, parse_dates=["date"])
        elif parquet_path.exists():
            df = pd.read_parquet(parquet_path)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
        else:
            last_error = FileNotFoundError(
                f"No northbound data file found for {ch.value} in {nb_dir}. "
                f"Expected {csv_path} or {parquet_path}"
            )
            continue

        # Normalize date column to date objects for filtering
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Filter by date range
        mask = (df["date"] >= start) & (df["date"] <= end)
        df = df.loc[mask].copy()

        if not df.empty:
            df["channel"] = ch.value
            frames.append(df)

    if not frames:
        if last_error is not None:
            raise last_error
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values("date").reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# Fetch via adapter
# ---------------------------------------------------------------------------

def fetch_northbound_flow(
    adapter,  # DataSource
    start: date,
    end: date,
    channel: NorthChannel | None = None,
) -> pd.DataFrame:
    """Fetch northbound flow data via a DataSource adapter.

    The adapter's ``fetch()`` is called with empty tickers list;
    adapters should filter by ``data_type="northbound_flow"`` in their
    implementation.

    Returns
    -------
    pd.DataFrame
        Northbound flow records. Empty DataFrame on failure (never None).
    """
    try:
        records = adapter.fetch([])
    except Exception:
        logger.warning(
            "Northbound flow fetch failed for source=%s",
            getattr(adapter, "source_name", "unknown"),
            exc_info=True,
        )
        return pd.DataFrame()

    if not records:
        return pd.DataFrame()

    rows = []
    for rec in records:
        if rec.data_type != "northbound_flow":
            continue
        payload = rec.payload
        # Filter by channel if specified
        if channel is not None and payload.get("channel") != channel.value:
            continue
        # Filter by date range
        rec_date = payload.get("date")
        if isinstance(rec_date, str):
            from datetime import date as _date
            rec_date = _date.fromisoformat(rec_date)
        if rec_date is None or rec_date < start or rec_date > end:
            continue
        rows.append(payload)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

def northbound_momentum(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """Rolling net flow momentum over *window* trading days.

    Computes the rolling sum of ``net_amount`` column.

    Parameters
    ----------
    df:
        DataFrame with ``net_amount`` column.
    window:
        Rolling window size in days. Default 5.

    Returns
    -------
    pd.Series
        Rolling momentum values. NaN for the first ``window - 1`` rows.
    """
    if "net_amount" not in df.columns:
        raise ValueError(
            f"DataFrame must contain 'net_amount' column. Found: {list(df.columns)}"
        )
    return df["net_amount"].rolling(window=window).sum()


# ---------------------------------------------------------------------------
# Signal producers
# ---------------------------------------------------------------------------

def northbound_to_signals(
    records: list[NorthboundFlow],
    threshold: float = 1e9,
) -> list[dict]:
    """Convert large northbound flows into Signal-compatible dicts.

    Parameters
    ----------
    records:
        List of NorthboundFlow records.
    threshold:
        Minimum absolute net_amount (in yuan) to trigger a signal.
        Default 1e9 = 10 亿元.

    Returns
    -------
    list[dict]
        Each dict has keys: signal_type, ticker, strength, reason, source, timestamp.
    """
    signals = []
    for rec in records:
        # net_amount is in 亿元, threshold is in 元
        net_yuan = float(rec.net_amount) * 1e8
        if abs(net_yuan) < threshold:
            continue

        direction = "inflow" if rec.net_amount > 0 else "outflow"
        ticker = "SH" if rec.channel == NorthChannel.HGT else "SZ"
        signals.append({
            "signal_type": f"northbound_{direction}",
            "ticker": ticker,
            "strength": abs(net_yuan) / threshold,
            "reason": (
                f"北向资金{'净流入' if direction == 'inflow' else '净流出'}"
                f"{abs(float(rec.net_amount)):.2f}亿元"
            ),
            "source": rec.source,
            "timestamp": rec.date.isoformat(),
        })
    return signals


def index_change_to_signals(
    old: list[dict],
    new: list[dict],
) -> list[dict]:
    """Detect index constituent changes and emit Signal-compatible dicts.

    Parameters
    ----------
    old:
        Previous index constituents. Each dict has at least ``code`` and ``name``.
    new:
        Current index constituents.

    Returns
    -------
    list[dict]
        Signals for added/removed constituents with keys:
        signal_type, ticker, strength, reason, source, timestamp.
    """
    old_codes = {item["code"] for item in old}
    new_codes = {item["code"] for item in new}

    added = new_codes - old_codes
    removed = old_codes - new_codes

    today = date.today().isoformat()
    signals = []

    for code in added:
        item = next(i for i in new if i["code"] == code)
        signals.append({
            "signal_type": "index_add",
            "ticker": code,
            "strength": 1.0,
            "reason": f"{item.get('name', code)} 纳入指数成分",
            "source": "index_change",
            "timestamp": today,
        })

    for code in removed:
        item = next(i for i in old if i["code"] == code)
        signals.append({
            "signal_type": "index_remove",
            "ticker": code,
            "strength": 1.0,
            "reason": f"{item.get('name', code)} 从指数成分剔除",
            "source": "index_change",
            "timestamp": today,
        })

    return signals
