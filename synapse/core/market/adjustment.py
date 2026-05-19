"""Ex-Right Adjustment Module — Price adjustment for corporate actions.

Handles forward (前复权) and backward (后复权) price adjustments
for dividends, splits, and bonus shares on China A-Shares.

All financial calculations use Decimal with ROUND_HALF_UP for precision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)


class AdjustmentType(Enum):
    """Price adjustment type."""

    FORWARD = "forward"   # 前复权: adjust historical prices to current level
    BACKWARD = "backward"  # 后复权: adjust current prices to historical level
    NONE = "none"          # No adjustment (raw prices)


def _dec(val: float | int | str | Decimal) -> Decimal:
    """Convert to Decimal safely."""
    return Decimal(str(val))


@dataclass(frozen=True, slots=True)
class AdjustmentEvent:
    """A single corporate action event with adjustment factor."""

    date: date
    factor: Decimal
    event_type: str  # "dividend", "split", "bonus"
    cash_dividend: Decimal  # yuan per share before tax
    stock_dividend: Decimal  # shares per 10 shares

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "date": self.date.isoformat(),
            "factor": str(self.factor),
            "event_type": self.event_type,
            "cash_dividend": str(self.cash_dividend),
            "stock_dividend": str(self.stock_dividend),
        }

    @classmethod
    def from_dict(cls, d: dict) -> AdjustmentEvent:
        """Deserialize from dict."""
        return cls(
            date=date.fromisoformat(d["date"]),
            factor=_dec(d["factor"]),
            event_type=d["event_type"],
            cash_dividend=_dec(d["cash_dividend"]),
            stock_dividend=_dec(d["stock_dividend"]),
        )


@dataclass(frozen=True, slots=True)
class AdjustmentFactors:
    """Collection of adjustment events for a single symbol."""

    symbol: str
    events: tuple[AdjustmentEvent, ...]  # sorted by date ascending
    _cumulative: tuple[Decimal, ...] = ()  # running product of factors

    def __post_init__(self) -> None:
        """Compute cumulative factors if not provided."""
        if not self._cumulative and self.events:
            cumul: list[Decimal] = []
            product = _dec(1)
            for evt in self.events:
                product *= evt.factor
                cumul.append(product)
            object.__setattr__(self, "_cumulative", tuple(cumul))

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "symbol": self.symbol,
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, d: dict) -> AdjustmentFactors:
        """Deserialize from dict."""
        events = tuple(AdjustmentEvent.from_dict(e) for e in d["events"])
        return cls(symbol=d["symbol"], events=events)

    @property
    def cumulative(self) -> tuple[Decimal, ...]:
        """Return cumulative factors."""
        return self._cumulative

    def factor_for_date(self, target_date: date) -> Decimal:
        """Get cumulative adjustment factor for a given date.

        Returns the product of all factors for events on or before target_date.
        Returns 1.0 if no events apply.
        """
        if not self.events:
            return _dec(1)

        result = _dec(1)
        for evt, cum in zip(self.events, self._cumulative):
            if evt.date <= target_date:
                result = cum
            else:
                break
        return result


def get_adjustment_factors(
    symbol: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/adjustments",
) -> AdjustmentFactors:
    """Load adjustment factors from Parquet file.

    Expected file: {data_dir}/{symbol}.parquet
    Columns: [date, factor, event_type, cash_dividend, stock_dividend]

    Args:
        symbol: Stock symbol (e.g., "000001.SZ").
        start: Start date (inclusive) — used to filter events.
        end: End date (inclusive) — used to filter events.
        data_dir: Directory containing adjustment data files.

    Returns:
        AdjustmentFactors with events sorted by date ascending.
        Returns empty factors if file not found.
    """
    data_path = Path(data_dir)
    parquet_path = data_path / f"{symbol}.parquet"
    csv_path = data_path / f"{symbol}.csv"

    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
    else:
        logger.warning(
            "No adjustment data file found for %s in %s — returning empty factors",
            symbol,
            data_path,
        )
        return AdjustmentFactors(symbol=symbol, events=())

    # Normalize date column
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date

    # Filter by date range
    mask = (df["date"] >= start) & (df["date"] <= end)
    df = df.loc[mask].sort_values("date").reset_index(drop=True)

    # Validate required columns
    required_cols = {"date", "factor", "event_type", "cash_dividend", "stock_dividend"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.warning(
            "Missing columns in adjustment data for %s: %s — returning empty factors",
            symbol,
            missing,
        )
        return AdjustmentFactors(symbol=symbol, events=())

    events: list[AdjustmentEvent] = []
    for _, row in df.iterrows():
        factor = _dec(row["factor"])
        # Validate factor range
        if factor < _dec(0) or factor > _dec(10):
            logger.warning(
                "Skipping invalid factor %.4f for %s on %s (must be 0..10)",
                float(factor),
                symbol,
                row["date"],
            )
            continue

        events.append(
            AdjustmentEvent(
                date=row["date"],
                factor=factor,
                event_type=str(row["event_type"]),
                cash_dividend=_dec(row["cash_dividend"]),
                stock_dividend=_dec(row["stock_dividend"]),
            )
        )

    return AdjustmentFactors(symbol=symbol, events=tuple(events))


def adjust_prices(
    df: pd.DataFrame,
    factors: AdjustmentFactors,
    adj_type: AdjustmentType = AdjustmentType.FORWARD,
) -> pd.DataFrame:
    """Adjust OHLC prices using adjustment factors.

    Adds columns: adj_open, adj_high, adj_low, adj_close.
    Original columns are preserved.

    Args:
        df: DataFrame with columns [date, open, high, low, close, ...].
        factors: Adjustment factors for the symbol.
        adj_type: Forward, backward, or none adjustment.

    Returns:
        DataFrame with additional adj_* columns.
    """
    if adj_type == AdjustmentType.NONE or not factors.events:
        # No adjustment — copy raw prices as adj_*
        result = df.copy()
        for col in ("open", "high", "low", "close"):
            result[f"adj_{col}"] = result[col]
        return result

    result = df.copy()
    price_cols = ["open", "high", "low", "close"]

    if adj_type == AdjustmentType.FORWARD:
        # Forward: multiply by factor / latest_cumulative
        # This brings historical prices to current level
        latest_cum = factors.cumulative[-1] if factors.cumulative else _dec(1)
        for idx, row in result.iterrows():
            row_date = row["date"]
            if isinstance(row_date, pd.Timestamp):
                row_date = row_date.date()
            cum_factor = factors.factor_for_date(row_date)
            divisor = latest_cum / cum_factor if cum_factor != 0 else _dec(1)
            for col in price_cols:
                raw = _dec(row[col])
                adjusted = (raw * divisor).quantize(
                    _dec("0.01"), rounding=ROUND_HALF_UP
                )
                result.at[idx, f"adj_{col}"] = float(adjusted)

    elif adj_type == AdjustmentType.BACKWARD:
        # Backward: multiply by cumulative factor
        # This adjusts current prices back to historical level
        for idx, row in result.iterrows():
            row_date = row["date"]
            if isinstance(row_date, pd.Timestamp):
                row_date = row_date.date()
            cum_factor = factors.factor_for_date(row_date)
            for col in price_cols:
                raw = _dec(row[col])
                adjusted = (raw * cum_factor).quantize(
                    _dec("0.01"), rounding=ROUND_HALF_UP
                )
                result.at[idx, f"adj_{col}"] = float(adjusted)

    return result


def adjust_single_price(
    price: float,
    target_date: date,
    factors: AdjustmentFactors,
    adj_type: AdjustmentType = AdjustmentType.FORWARD,
) -> float:
    """Adjust a single price point.

    Args:
        price: Raw price to adjust.
        target_date: Date of the price.
        factors: Adjustment factors for the symbol.
        adj_type: Forward, backward, or none adjustment.

    Returns:
        Adjusted price as float.
    """
    if adj_type == AdjustmentType.NONE or not factors.events:
        return price

    cum_factor = factors.factor_for_date(target_date)
    raw = _dec(price)

    if adj_type == AdjustmentType.FORWARD:
        latest_cum = factors.cumulative[-1] if factors.cumulative else _dec(1)
        divisor = latest_cum / cum_factor if cum_factor != 0 else _dec(1)
        adjusted = (raw * divisor).quantize(_dec("0.01"), rounding=ROUND_HALF_UP)
    else:  # BACKWARD
        adjusted = (raw * cum_factor).quantize(_dec("0.01"), rounding=ROUND_HALF_UP)

    return float(adjusted)
