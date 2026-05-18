"""Tests for Market Data Loader."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from synapse.core.market.data_loader import load_daily, load_daily_from_api


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample market data."""
    data_dir = tmp_path / "data" / "market"
    data_dir.mkdir(parents=True)

    # Create sample CSV data
    df = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"],
        "open": [10.0, 10.5, 10.3, 10.8, 11.0],
        "high": [10.5, 10.8, 10.7, 11.0, 11.2],
        "low": [9.8, 10.2, 10.1, 10.5, 10.8],
        "close": [10.3, 10.6, 10.5, 10.9, 11.1],
        "volume": [100000, 120000, 110000, 130000, 140000],
    })
    df.to_csv(data_dir / "000001.SZ.csv", index=False)

    return data_dir


class TestLoadDaily:
    """Tests for load_daily()."""

    def test_load_full_range(self, sample_data_dir: Path):
        df = load_daily(
            "000001.SZ",
            date(2026, 1, 5),
            date(2026, 1, 9),
            data_dir=sample_data_dir,
        )
        assert len(df) == 5
        assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]

    def test_load_filtered_range(self, sample_data_dir: Path):
        df = load_daily(
            "000001.SZ",
            date(2026, 1, 6),
            date(2026, 1, 8),
            data_dir=sample_data_dir,
        )
        assert len(df) == 3
        assert df["date"].iloc[0] == date(2026, 1, 6)
        assert df["date"].iloc[-1] == date(2026, 1, 8)

    def test_load_empty_range(self, sample_data_dir: Path):
        df = load_daily(
            "000001.SZ",
            date(2026, 1, 10),
            date(2026, 1, 15),
            data_dir=sample_data_dir,
        )
        assert len(df) == 0

    def test_load_nonexistent_symbol(self, sample_data_dir: Path):
        with pytest.raises(FileNotFoundError, match="No data file found"):
            load_daily(
                "999999.SZ",
                date(2026, 1, 5),
                date(2026, 1, 9),
                data_dir=sample_data_dir,
            )

    def test_load_sorted_by_date(self, sample_data_dir: Path):
        df = load_daily(
            "000001.SZ",
            date(2026, 1, 5),
            date(2026, 1, 9),
            data_dir=sample_data_dir,
        )
        dates = df["date"].tolist()
        assert dates == sorted(dates)


class TestLoadDailyFromAPI:
    """Tests for load_daily_from_api() placeholder."""

    def test_not_implemented(self):
        with pytest.raises(NotImplementedError, match="API data loading not implemented"):
            load_daily_from_api("000001.SZ", date(2026, 1, 5), date(2026, 1, 9))
