"""Data Loader — Market data loading for China A-Shares.

P1: Supports local CSV/Parquet files.
Interface预留 API extension for future data sources.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd


def load_daily(
    symbol: str,
    start: date,
    end: date,
    data_dir: str | Path = "data/market",
) -> pd.DataFrame:
    """Load daily OHLCV data for a symbol.

    P1: Loads from local CSV/Parquet files.
    Expected file structure: {data_dir}/{symbol}.csv or {symbol}.parquet

    Args:
        symbol: Stock symbol (e.g., "000001.SZ").
        start: Start date (inclusive).
        end: End date (inclusive).
        data_dir: Directory containing market data files.

    Returns:
        DataFrame with columns: [date, open, high, low, close, volume].
        Filtered to the date range [start, end].

    Raises:
        FileNotFoundError: If data file does not exist.
        ValueError: If data file has invalid format.
    """
    data_path = Path(data_dir)
    csv_path = data_path / f"{symbol}.csv"
    parquet_path = data_path / f"{symbol}.parquet"

    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
    elif parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
    else:
        raise FileNotFoundError(
            f"No data file found for {symbol} in {data_path}. "
            f"Expected {csv_path} or {parquet_path}"
        )

    # Validate required columns
    required_cols = {"date", "open", "high", "low", "close", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Filter by date range
    df["date"] = pd.to_datetime(df["date"]).dt.date
    mask = (df["date"] >= start) & (df["date"] <= end)
    df = df.loc[mask].copy()

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df


def load_daily_from_api(
    symbol: str,
    start: date,
    end: date,
) -> pd.DataFrame:
    """Load daily data from API (placeholder for future implementation).

    P1: Raises NotImplementedError.
    Future: Connect to data providers (Tushare, AKShare, etc.).

    Args:
        symbol: Stock symbol.
        start: Start date.
        end: End date.

    Returns:
        DataFrame with daily OHLCV data.

    Raises:
        NotImplementedError: Always in P1.
    """
    raise NotImplementedError(
        f"API data loading not implemented in P1. "
        f"Use load_daily() with local files instead."
    )
