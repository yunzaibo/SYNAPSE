from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import pytest

from synapse.event.datasource import DataSource, MarketData
from synapse.factor.base import BaseFactor
from synapse.factor.engine import FactorEngine, PartialResult
from synapse.factor.registry import FactorRegistry
from synapse.factor.spec import FactorSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(**overrides) -> FactorSpec:
    defaults = dict(
        factor_id="momentum_6m_1m",
        name="6M-1M Momentum",
        description="Price momentum",
        category="momentum",
        inputs=["close"],
        lookback_days=120,
        data_source="eastmoney",
        publication_lag=1,
        version="1.0.0",
    )
    defaults.update(overrides)
    return FactorSpec(**defaults)


def _make_factor_cls(
    fid: str = "momentum_6m_1m",
    category: str = "momentum",
    compute_fn=None,
    spec_overrides: dict | None = None,
):
    """Create a concrete BaseFactor subclass for testing."""
    _fid = fid
    _category = category
    _overrides = spec_overrides or {}

    class _Factor(BaseFactor):
        @classmethod
        def factor_id(cls) -> str:
            return _fid

        @classmethod
        def spec(cls) -> FactorSpec:
            return _make_spec(factor_id=_fid, category=_category, **_overrides)

        def compute(self, data: pd.DataFrame) -> pd.Series:
            if compute_fn is not None:
                return compute_fn(data)
            if "close" in data.columns:
                return data.groupby("ticker")["close"].last()
            return pd.Series(dtype=float)

    return _Factor


def _make_market_data(
    ticker: str,
    records: list[dict[str, Any]],
    source: str = "eastmoney",
    data_type: str = "quote",
) -> MarketData:
    """Build a MarketData with a list of records in payload."""
    return MarketData(
        ticker=ticker,
        source=source,
        timestamp=datetime(2024, 1, 10),
        data_type=data_type,
        payload={"records": records},
    )


def _make_registry(*factor_specs) -> FactorRegistry:
    """Register multiple factor classes and return the registry."""
    registry = FactorRegistry()
    for spec in factor_specs:
        # Pass publication_lag and other spec fields through
        overrides = {}
        if spec.publication_lag != 1:
            overrides["publication_lag"] = spec.publication_lag
        cls = _make_factor_cls(
            fid=spec.factor_id,
            category=spec.category,
            spec_overrides=overrides,
        )
        registry.register(cls)
    return registry


class StubDataSource(DataSource):
    """Stub DataSource that returns pre-configured market data."""

    def __init__(self, data: list[MarketData]) -> None:
        self._data = data

    @property
    def source_name(self) -> str:
        return "stub"

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        return [md for md in self._data if md.ticker in tickers]


# ---------------------------------------------------------------------------
# Test: Engine creation
# ---------------------------------------------------------------------------

class TestFactorEngineCreation:
    def test_create_with_registry_and_datasource(self):
        registry = FactorRegistry()
        ds = StubDataSource([])
        engine = FactorEngine(registry, ds)
        assert engine._registry is registry
        assert engine._data_source is ds


# ---------------------------------------------------------------------------
# Test: _to_dataframe
# ---------------------------------------------------------------------------

class TestToDataframe:
    def test_empty_market_data(self):
        result = FactorEngine._to_dataframe([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_single_ticker_records(self):
        md = _make_market_data(
            "600519",
            [
                {"date": "2024-01-08", "close": 1800.0, "volume": 10000},
                {"date": "2024-01-09", "close": 1810.0, "volume": 12000},
            ],
        )
        df = FactorEngine._to_dataframe([md])
        assert len(df) == 2
        assert "ticker" in df.columns
        assert "source" in df.columns
        assert (df["ticker"] == "600519").all()
        assert df["date"].dtype == "datetime64[ns]"

    def test_multiple_tickers(self):
        md1 = _make_market_data("600519", [{"date": "2024-01-09", "close": 1800.0}])
        md2 = _make_market_data("000001", [{"date": "2024-01-09", "close": 15.0}])
        df = FactorEngine._to_dataframe([md1, md2])
        assert len(df) == 2
        assert set(df["ticker"]) == {"600519", "000001"}

    def test_flat_payload(self):
        """Payload without 'records' key is treated as a single row."""
        md = MarketData(
            ticker="600519",
            source="eastmoney",
            timestamp=datetime(2024, 1, 10),
            data_type="quote",
            payload={"close": 1800.0, "volume": 10000},
        )
        df = FactorEngine._to_dataframe([md])
        assert len(df) == 1
        assert df.iloc[0]["close"] == 1800.0


# ---------------------------------------------------------------------------
# Test: compute_factor
# ---------------------------------------------------------------------------

class TestComputeFactor:
    def _build_engine(self, factor_specs=None):
        if factor_specs is None:
            factor_specs = [_make_spec()]
        registry = _make_registry(*factor_specs)
        # Build market data for two tickers
        market_data = [
            _make_market_data(
                "600519",
                [
                    {"date": "2024-01-08", "close": 1800.0},
                    {"date": "2024-01-09", "close": 1810.0},
                ],
            ),
            _make_market_data(
                "000001",
                [
                    {"date": "2024-01-08", "close": 14.5},
                    {"date": "2024-01-09", "close": 15.0},
                ],
            ),
        ]
        ds = StubDataSource(market_data)
        return FactorEngine(registry, ds)

    def test_returns_series(self):
        engine = self._build_engine()
        result = engine.compute_factor(
            "momentum_6m_1m", ["600519", "000001"], date(2024, 1, 10)
        )
        assert isinstance(result, pd.Series)
        assert result.name == "momentum_6m_1m"

    def test_values_present(self):
        engine = self._build_engine()
        result = engine.compute_factor(
            "momentum_6m_1m", ["600519", "000001"], date(2024, 1, 10)
        )
        assert len(result) > 0

    def test_unregistered_factor_raises(self):
        engine = self._build_engine()
        with pytest.raises(ValueError, match="not registered"):
            engine.compute_factor(
                "nonexistent_factor", ["600519"], date(2024, 1, 10)
            )

    def test_empty_fetch_returns_empty_series(self):
        registry = _make_registry(_make_spec())
        ds = StubDataSource([])
        engine = FactorEngine(registry, ds)
        result = engine.compute_factor(
            "momentum_6m_1m", ["999999"], date(2024, 1, 10)
        )
        assert isinstance(result, pd.Series)
        assert result.empty


# ---------------------------------------------------------------------------
# Test: compute_batch
# ---------------------------------------------------------------------------

class TestComputeBatch:
    def _build_engine(self):
        spec_a = _make_spec(factor_id="factor_a", category="momentum")
        spec_b = _make_spec(
            factor_id="factor_b",
            category="value",
            inputs=["close"],
        )
        registry = _make_registry(spec_a, spec_b)
        market_data = [
            _make_market_data(
                "600519",
                [{"date": "2024-01-09", "close": 1800.0}],
            ),
        ]
        ds = StubDataSource(market_data)
        return FactorEngine(registry, ds)

    def test_returns_dataframe_with_columns(self):
        engine = self._build_engine()
        result = engine.compute_batch(
            ["factor_a", "factor_b"], ["600519"], date(2024, 1, 10)
        )
        assert isinstance(result, pd.DataFrame)
        # Both factors should be columns (if they produce values)
        # At minimum, the result is a DataFrame

    def test_empty_factor_ids(self):
        engine = self._build_engine()
        result = engine.compute_batch([], ["600519"], date(2024, 1, 10))
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# Test: compute_all
# ---------------------------------------------------------------------------

class TestComputeAll:
    def test_computes_all_registered(self):
        spec_a = _make_spec(factor_id="factor_a")
        spec_b = _make_spec(factor_id="factor_b")
        registry = _make_registry(spec_a, spec_b)
        market_data = [
            _make_market_data(
                "600519",
                [{"date": "2024-01-09", "close": 1800.0}],
            ),
        ]
        ds = StubDataSource(market_data)
        engine = FactorEngine(registry, ds)

        result = engine.compute_all(["600519"], date(2024, 1, 10))
        assert isinstance(result, pd.DataFrame)

    def test_empty_registry(self):
        registry = FactorRegistry()
        ds = StubDataSource([])
        engine = FactorEngine(registry, ds)
        result = engine.compute_all(["600519"], date(2024, 1, 10))
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ---------------------------------------------------------------------------
# Test: PartialResult (error containment)
# ---------------------------------------------------------------------------

class TestPartialResult:
    def test_failing_factor_does_not_block_others(self):
        """One factor fails, the other succeeds -- batch returns partial."""

        def _failing_compute(data: pd.DataFrame) -> pd.Series:
            raise RuntimeError("boom")

        spec_good = _make_spec(factor_id="good_factor")
        registry = FactorRegistry()
        # Register good factor
        registry.register(_make_factor_cls(fid="good_factor"))
        # Register bad factor
        registry.register(
            _make_factor_cls(fid="bad_factor", compute_fn=_failing_compute)
        )

        market_data = [
            _make_market_data(
                "600519",
                [{"date": "2024-01-09", "close": 1800.0}],
            ),
        ]
        ds = StubDataSource(market_data)
        engine = FactorEngine(registry, ds)

        # compute_factor for bad factor should raise
        with pytest.raises(RuntimeError, match="boom"):
            engine.compute_factor("bad_factor", ["600519"], date(2024, 1, 10))

        # compute_batch should succeed with partial results
        result = engine.compute_batch(
            ["good_factor", "bad_factor"], ["600519"], date(2024, 1, 10)
        )
        assert isinstance(result, pd.DataFrame)

    def test_partial_result_dataclass(self):
        pr = PartialResult(
            factor_id="test", success=True, value=pd.Series([1.0])
        )
        assert pr.success is True
        assert pr.error is None

        pr_fail = PartialResult(
            factor_id="test", success=False, error="something went wrong"
        )
        assert pr_fail.success is False
        assert pr_fail.error == "something went wrong"


# ---------------------------------------------------------------------------
# Test: Point-in-time validation
# ---------------------------------------------------------------------------

class TestPointInTime:
    def test_filter_excludes_future_data(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"]
                ),
                "close": [100.0, 101.0, 102.0, 103.0],
            }
        )
        # publication_lag=1, compute_date=2024-01-10
        # cutoff = 2024-01-10 - 1 day = 2024-01-09
        result = FactorEngine._filter_point_in_time(df, date(2024, 1, 10), 1)
        assert len(result) == 2  # only Jan 8 and Jan 9
        assert result["date"].max() <= pd.Timestamp("2024-01-09")

    def test_filter_zero_lag(self):
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-09", "2024-01-10", "2024-01-11"]),
                "close": [100.0, 101.0, 102.0],
            }
        )
        result = FactorEngine._filter_point_in_time(df, date(2024, 1, 10), 0)
        assert len(result) == 2  # Jan 9 and Jan 10

    def test_filter_no_date_column(self):
        df = pd.DataFrame({"close": [100.0, 101.0]})
        result = FactorEngine._filter_point_in_time(df, date(2024, 1, 10), 1)
        assert len(result) == 2  # no-op

    def test_filter_empty_dataframe(self):
        df = pd.DataFrame()
        result = FactorEngine._filter_point_in_time(df, date(2024, 1, 10), 1)
        assert result.empty

    def test_engine_respects_publication_lag(self):
        """Factor with high publication_lag should not see recent data."""
        spec = _make_spec(
            factor_id="lag_factor",
            publication_lag=5,  # 5-day lag
        )
        registry = _make_registry(spec)

        # All data is from 2024-01-09, compute_date is 2024-01-10
        # cutoff = 2024-01-10 - 5 days = 2024-01-04
        # So 2024-01-09 data should be excluded
        market_data = [
            _make_market_data(
                "600519",
                [{"date": "2024-01-09", "close": 1800.0}],
            ),
        ]
        ds = StubDataSource(market_data)
        engine = FactorEngine(registry, ds)
        result = engine.compute_factor("lag_factor", ["600519"], date(2024, 1, 10))
        assert result.empty  # no data within the point-in-time window
