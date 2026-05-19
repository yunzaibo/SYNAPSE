"""Tests for Northbound Flow Module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from synapse.core.market.northbound import (
    NorthChannel,
    NorthboundFlow,
    fetch_northbound_flow,
    index_change_to_signals,
    load_northbound_flow,
    northbound_momentum,
    northbound_to_signals,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_flow() -> NorthboundFlow:
    return NorthboundFlow(
        date=date(2026, 1, 10),
        channel=NorthChannel.HGT,
        buy_amount=Decimal("150.5"),
        sell_amount=Decimal("120.3"),
        net_amount=Decimal("30.2"),
        total_buy=Decimal("1500.0"),
        total_sell=Decimal("1200.0"),
        quota_used_pct=Decimal("45.5"),
        source="akshare",
    )


@pytest.fixture
def sample_csv_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample northbound CSV data."""
    nb_dir = tmp_path / "northbound"
    nb_dir.mkdir(parents=True)

    df = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"],
        "channel": ["沪股通"] * 5,
        "buy_amount": [100.0, 110.0, 95.0, 120.0, 105.0],
        "sell_amount": [80.0, 90.0, 85.0, 100.0, 95.0],
        "net_amount": [20.0, 20.0, 10.0, 20.0, 10.0],
        "total_buy": [1000.0, 1110.0, 1205.0, 1325.0, 1430.0],
        "total_sell": [800.0, 890.0, 975.0, 1075.0, 1170.0],
        "quota_used_pct": [30.0, 35.0, 28.0, 40.0, 33.0],
        "source": ["akshare"] * 5,
    })
    df.to_csv(nb_dir / "沪股通.csv", index=False)

    return tmp_path


@pytest.fixture
def sample_parquet_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample northbound Parquet data."""
    nb_dir = tmp_path / "northbound"
    nb_dir.mkdir(parents=True)

    df = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07"],
        "channel": ["深股通"] * 3,
        "buy_amount": [80.0, 85.0, 90.0],
        "sell_amount": [70.0, 75.0, 80.0],
        "net_amount": [10.0, 10.0, 10.0],
        "total_buy": [800.0, 885.0, 975.0],
        "total_sell": [700.0, 775.0, 855.0],
        "quota_used_pct": [25.0, 27.0, 30.0],
        "source": ["akshare"] * 3,
    })
    df.to_parquet(nb_dir / "深股通.parquet", index=False)

    return tmp_path


# ---------------------------------------------------------------------------
# NorthChannel enum
# ---------------------------------------------------------------------------

class TestNorthChannel:
    def test_hgt_value(self):
        assert NorthChannel.HGT.value == "沪股通"

    def test_sgt_value(self):
        assert NorthChannel.SGT.value == "深股通"

    def test_str_enum(self):
        assert str(NorthChannel.HGT) == "NorthChannel.HGT"
        assert NorthChannel.HGT == "沪股通"

    def test_members_count(self):
        assert len(NorthChannel) == 2


# ---------------------------------------------------------------------------
# NorthboundFlow dataclass
# ---------------------------------------------------------------------------

class TestNorthboundFlow:
    def test_frozen(self, sample_flow: NorthboundFlow):
        with pytest.raises(FrozenInstanceError):
            sample_flow.source = "new_source"  # type: ignore[misc]

    def test_to_dict(self, sample_flow: NorthboundFlow):
        d = sample_flow.to_dict()
        assert d["date"] == "2026-01-10"
        assert d["channel"] == "沪股通"
        assert d["buy_amount"] == "150.5"
        assert d["net_amount"] == "30.2"
        assert d["source"] == "akshare"
        assert len(d) == 9

    def test_from_dict(self, sample_flow: NorthboundFlow):
        d = sample_flow.to_dict()
        restored = NorthboundFlow.from_dict(d)
        assert restored == sample_flow

    def test_roundtrip(self, sample_flow: NorthboundFlow):
        d = sample_flow.to_dict()
        restored = NorthboundFlow.from_dict(d)
        assert restored.to_dict() == d

    def test_from_dict_with_numeric_values(self):
        """from_dict accepts numeric (int/float) values, not just strings."""
        d = {
            "date": "2026-01-10",
            "channel": "沪股通",
            "buy_amount": 150.5,
            "sell_amount": 120.3,
            "net_amount": 30.2,
            "total_buy": 1500.0,
            "total_sell": 1200.0,
            "quota_used_pct": 45.5,
            "source": "akshare",
        }
        restored = NorthboundFlow.from_dict(d)
        assert restored.buy_amount == Decimal("150.5")


# ---------------------------------------------------------------------------
# load_northbound_flow
# ---------------------------------------------------------------------------

class TestLoadNorthboundFlow:
    def test_load_from_csv(self, sample_csv_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 9),
            data_dir=sample_csv_dir,
        )
        assert len(df) == 5
        assert "net_amount" in df.columns

    def test_load_from_parquet(self, sample_parquet_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 7),
            channel=NorthChannel.SGT,
            data_dir=sample_parquet_dir,
        )
        assert len(df) == 3

    def test_load_filtered_range(self, sample_csv_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 6), date(2026, 1, 8),
            data_dir=sample_csv_dir,
        )
        assert len(df) == 3

    def test_load_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="No northbound data file found"):
            load_northbound_flow(
                date(2026, 1, 5), date(2026, 1, 9),
                data_dir=tmp_path,
            )

    def test_load_sorted_by_date(self, sample_csv_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 9),
            data_dir=sample_csv_dir,
        )
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    def test_load_includes_source_column(self, sample_csv_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 9),
            data_dir=sample_csv_dir,
        )
        assert "source" in df.columns

    def test_load_channel_specific(self, sample_csv_dir: Path):
        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 9),
            channel=NorthChannel.HGT,
            data_dir=sample_csv_dir,
        )
        assert len(df) == 5

    def test_load_both_channels(self, sample_csv_dir: Path):
        """Loading without channel filter concatenates both channels."""
        # Add a parquet file for SGT in the same northbound dir
        nb_dir = sample_csv_dir / "northbound"
        df_sgt = pd.DataFrame({
            "date": ["2026-01-05", "2026-01-06", "2026-01-07"],
            "channel": ["深股通"] * 3,
            "buy_amount": [80.0, 85.0, 90.0],
            "sell_amount": [70.0, 75.0, 80.0],
            "net_amount": [10.0, 10.0, 10.0],
            "total_buy": [800.0, 885.0, 975.0],
            "total_sell": [700.0, 775.0, 855.0],
            "quota_used_pct": [25.0, 27.0, 30.0],
            "source": ["akshare"] * 3,
        })
        df_sgt.to_parquet(nb_dir / "深股通.parquet", index=False)

        df = load_northbound_flow(
            date(2026, 1, 5), date(2026, 1, 9),
            data_dir=sample_csv_dir,
        )
        assert len(df) == 8  # 5 HGT + 3 SGT


# ---------------------------------------------------------------------------
# fetch_northbound_flow
# ---------------------------------------------------------------------------

class TestFetchNorthboundFlow:
    def _make_adapter(self, records):
        adapter = MagicMock()
        adapter.source_name = "test_source"
        adapter.fetch.return_value = records
        return adapter

    def _make_market_data(self, payload):
        from synapse.event.datasource import MarketData
        from datetime import datetime
        return MarketData(
            ticker="",
            source="test",
            timestamp=datetime(2026, 1, 10),
            data_type="northbound_flow",
            payload=payload,
        )

    def test_fetch_with_mock_adapter(self):
        records = [
            self._make_market_data({
                "date": "2026-01-10",
                "channel": "沪股通",
                "buy_amount": "100.0",
                "sell_amount": "80.0",
                "net_amount": "20.0",
                "source": "test",
            }),
        ]
        adapter = self._make_adapter(records)
        df = fetch_northbound_flow(adapter, date(2026, 1, 10), date(2026, 1, 10))
        assert len(df) == 1
        assert df.iloc[0]["net_amount"] == "20.0"

    def test_fetch_empty_result(self):
        adapter = self._make_adapter([])
        df = fetch_northbound_flow(adapter, date(2026, 1, 10), date(2026, 1, 10))
        assert len(df) == 0

    def test_fetch_api_failure_returns_empty(self):
        adapter = MagicMock()
        adapter.source_name = "test_source"
        adapter.fetch.side_effect = RuntimeError("API down")
        df = fetch_northbound_flow(adapter, date(2026, 1, 10), date(2026, 1, 10))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_fetch_filters_by_channel(self):
        records = [
            self._make_market_data({
                "date": "2026-01-10",
                "channel": "沪股通",
                "buy_amount": "100.0",
                "sell_amount": "80.0",
                "net_amount": "20.0",
                "source": "test",
            }),
            self._make_market_data({
                "date": "2026-01-10",
                "channel": "深股通",
                "buy_amount": "50.0",
                "sell_amount": "30.0",
                "net_amount": "20.0",
                "source": "test",
            }),
        ]
        adapter = self._make_adapter(records)
        df = fetch_northbound_flow(
            adapter, date(2026, 1, 10), date(2026, 1, 10),
            channel=NorthChannel.HGT,
        )
        assert len(df) == 1

    def test_fetch_filters_by_date(self):
        records = [
            self._make_market_data({
                "date": "2026-01-10",
                "channel": "沪股通",
                "buy_amount": "100.0",
                "sell_amount": "80.0",
                "net_amount": "20.0",
                "source": "test",
            }),
            self._make_market_data({
                "date": "2026-01-15",
                "channel": "沪股通",
                "buy_amount": "110.0",
                "sell_amount": "90.0",
                "net_amount": "20.0",
                "source": "test",
            }),
        ]
        adapter = self._make_adapter(records)
        df = fetch_northbound_flow(adapter, date(2026, 1, 10), date(2026, 1, 12))
        assert len(df) == 1

    def test_fetch_skips_non_northbound_data(self):
        from synapse.event.datasource import MarketData
        from datetime import datetime
        records = [
            MarketData(
                ticker="000001",
                source="test",
                timestamp=datetime(2026, 1, 10),
                data_type="quote",
                payload={"close": 10.5},
            ),
        ]
        adapter = self._make_adapter(records)
        df = fetch_northbound_flow(adapter, date(2026, 1, 10), date(2026, 1, 10))
        assert len(df) == 0


# ---------------------------------------------------------------------------
# northbound_momentum
# ---------------------------------------------------------------------------

class TestNorthboundMomentum:
    def test_rolling_sum(self):
        df = pd.DataFrame({
            "net_amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        })
        mom = northbound_momentum(df, window=3)
        assert mom.iloc[0] is pd.NA or pd.isna(mom.iloc[0])
        assert mom.iloc[2] == 60.0  # 10+20+30
        assert mom.iloc[4] == 120.0  # 30+40+50

    def test_window_1(self):
        df = pd.DataFrame({"net_amount": [10.0, 20.0, 30.0]})
        mom = northbound_momentum(df, window=1)
        assert mom.tolist() == [10.0, 20.0, 30.0]

    def test_window_equals_length(self):
        df = pd.DataFrame({"net_amount": [10.0, 20.0, 30.0]})
        mom = northbound_momentum(df, window=3)
        assert mom.iloc[2] == 60.0

    def test_missing_column_raises(self):
        df = pd.DataFrame({"wrong_col": [1, 2, 3]})
        with pytest.raises(ValueError, match="net_amount"):
            northbound_momentum(df)


# ---------------------------------------------------------------------------
# northbound_to_signals
# ---------------------------------------------------------------------------

class TestNorthboundToSignals:
    def _make_flow(self, net_amount: float, channel=NorthChannel.HGT) -> NorthboundFlow:
        return NorthboundFlow(
            date=date(2026, 1, 10),
            channel=channel,
            buy_amount=Decimal("100"),
            sell_amount=Decimal("80"),
            net_amount=Decimal(str(net_amount)),
            total_buy=Decimal("1000"),
            total_sell=Decimal("800"),
            quota_used_pct=Decimal("50"),
            source="akshare",
        )

    def test_large_inflow_generates_signal(self):
        # 30 亿元 > threshold 1e9 / 1e8 = 10 亿元
        flow = self._make_flow(30.0)
        signals = northbound_to_signals([flow], threshold=1e9)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "northbound_inflow"
        assert signals[0]["source"] == "akshare"

    def test_large_outflow_generates_signal(self):
        flow = self._make_flow(-30.0)
        signals = northbound_to_signals([flow], threshold=1e9)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "northbound_outflow"

    def test_small_flow_filtered(self):
        # 5 亿元 < threshold 1e9 / 1e8 = 10 亿元
        flow = self._make_flow(5.0)
        signals = northbound_to_signals([flow], threshold=1e9)
        assert len(signals) == 0

    def test_threshold_custom(self):
        flow = self._make_flow(5.0)
        signals = northbound_to_signals([flow], threshold=1e8)
        assert len(signals) == 1

    def test_multiple_flows(self):
        flows = [
            self._make_flow(30.0),
            self._make_flow(5.0),  # below threshold
            self._make_flow(-20.0),
        ]
        signals = northbound_to_signals(flows, threshold=1e9)
        assert len(signals) == 2

    def test_signal_has_required_keys(self):
        flow = self._make_flow(30.0)
        signals = northbound_to_signals([flow])
        required = {"signal_type", "ticker", "strength", "reason", "source", "timestamp"}
        assert required.issubset(signals[0].keys())

    def test_sgt_channel_ticker(self):
        flow = self._make_flow(30.0, channel=NorthChannel.SGT)
        signals = northbound_to_signals([flow])
        assert signals[0]["ticker"] == "SZ"


# ---------------------------------------------------------------------------
# index_change_to_signals
# ---------------------------------------------------------------------------

class TestIndexChangeToSignals:
    def test_detect_added(self):
        old = [{"code": "600519", "name": "贵州茅台"}]
        new = [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000858", "name": "五粮液"},
        ]
        signals = index_change_to_signals(old, new)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "index_add"
        assert signals[0]["ticker"] == "000858"

    def test_detect_removed(self):
        old = [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000858", "name": "五粮液"},
        ]
        new = [{"code": "600519", "name": "贵州茅台"}]
        signals = index_change_to_signals(old, new)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "index_remove"
        assert signals[0]["ticker"] == "000858"

    def test_no_changes(self):
        old = [{"code": "600519", "name": "贵州茅台"}]
        new = [{"code": "600519", "name": "贵州茅台"}]
        signals = index_change_to_signals(old, new)
        assert len(signals) == 0

    def test_add_and_remove(self):
        old = [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000001", "name": "平安银行"},
        ]
        new = [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000858", "name": "五粮液"},
        ]
        signals = index_change_to_signals(old, new)
        types = {s["signal_type"] for s in signals}
        assert "index_add" in types
        assert "index_remove" in types
        assert len(signals) == 2

    def test_empty_lists(self):
        signals = index_change_to_signals([], [])
        assert len(signals) == 0

    def test_signal_has_required_keys(self):
        old = []
        new = [{"code": "600519", "name": "贵州茅台"}]
        signals = index_change_to_signals(old, new)
        required = {"signal_type", "ticker", "strength", "reason", "source", "timestamp"}
        assert required.issubset(signals[0].keys())
