"""Tests for the 13 traditional factor implementations (F-013)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from synapse.factor.base import BaseFactor
from synapse.factor.registry import FactorRegistry
from synapse.factor.spec import FactorSpec

from synapse.factor.factors.momentum import Momentum1M, Momentum3M, Momentum6M1M
from synapse.factor.factors.value import EP, BP, SP
from synapse.factor.factors.quality import ROE, GrossMargin, DebtToAsset
from synapse.factor.factors.volatility import RealizedVol20D, IdiosyncraticVol
from synapse.factor.factors.liquidity import Turnover20D, AmihudIlliquidity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_data(n: int = 150, start_price: float = 10.0) -> pd.DataFrame:
    """Generate synthetic daily price data with a trend."""
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(end=pd.Timestamp("2025-01-01"), periods=n)
    returns = rng.normal(0.0005, 0.02, n)
    prices = start_price * (1 + returns).cumprod()
    volumes = rng.integers(1_000_000, 10_000_000, n).astype(float)
    float_shares = np.full(n, 50_000_000.0)
    return pd.DataFrame(
        {
            "date": dates,
            "close": prices,
            "volume": volumes,
            "float_shares": float_shares,
        }
    )


def _make_fundamental_data(n: int = 5) -> pd.DataFrame:
    """Generate synthetic fundamental data for value/quality factors."""
    return pd.DataFrame(
        {
            "net_profit_ttm": [1.0e8, 2.0e8, 3.0e8, 4.0e8, 5.0e8][:n],
            "market_cap": [1.0e9, 2.0e9, 3.0e9, 4.0e9, 5.0e9][:n],
            "net_asset": [5.0e8, 1.0e9, 1.5e9, 2.0e9, 2.5e9][:n],
            "revenue_ttm": [3.0e8, 6.0e8, 9.0e8, 1.2e9, 1.5e9][:n],
            "net_profit": [0.8e8, 1.6e8, 2.4e8, 3.2e8, 4.0e8][:n],
            "gross_profit": [1.5e8, 3.0e8, 4.5e8, 6.0e8, 7.5e8][:n],
            "revenue": [3.0e8, 6.0e8, 9.0e8, 1.2e9, 1.5e9][:n],
            "total_debt": [2.0e8, 4.0e8, 6.0e8, 8.0e8, 1.0e9][:n],
            "total_asset": [1.0e9, 2.0e9, 3.0e9, 4.0e9, 5.0e9][:n],
        }
    )


ALL_FACTOR_CLASSES: list[type[BaseFactor]] = [
    Momentum1M,
    Momentum3M,
    Momentum6M1M,
    EP,
    BP,
    SP,
    ROE,
    GrossMargin,
    DebtToAsset,
    RealizedVol20D,
    IdiosyncraticVol,
    Turnover20D,
    AmihudIlliquidity,
]

ALL_FACTOR_IDS: list[str] = [
    "momentum_1m",
    "momentum_3m",
    "momentum_6m_1m",
    "ep",
    "bp",
    "sp",
    "roe",
    "gross_margin",
    "debt_to_asset",
    "realized_vol_20d",
    "idiosyncratic_vol",
    "turnover_20d",
    "amihud_illiquidity",
]


# ---------------------------------------------------------------------------
# Factor identity and spec tests
# ---------------------------------------------------------------------------

class TestFactorIdentity:
    """Each factor class must have a unique, correct factor_id and spec."""

    @pytest.mark.parametrize("factor_cls", ALL_FACTOR_CLASSES, ids=lambda c: c.factor_id())
    def test_factor_id_matches_spec(self, factor_cls: type[BaseFactor]) -> None:
        assert factor_cls.factor_id() == factor_cls.spec().factor_id

    @pytest.mark.parametrize("factor_cls", ALL_FACTOR_CLASSES, ids=lambda c: c.factor_id())
    def test_spec_fields_not_empty(self, factor_cls: type[BaseFactor]) -> None:
        spec = factor_cls.spec()
        assert spec.name
        assert spec.description
        assert spec.category
        assert spec.inputs
        assert spec.lookback_days > 0
        assert spec.data_source

    @pytest.mark.parametrize("factor_cls", ALL_FACTOR_CLASSES, ids=lambda c: c.factor_id())
    def test_is_base_factor_subclass(self, factor_cls: type[BaseFactor]) -> None:
        assert issubclass(factor_cls, BaseFactor)

    @pytest.mark.parametrize(
        ("factor_cls", "expected_id"),
        list(zip(ALL_FACTOR_CLASSES, ALL_FACTOR_IDS)),
        ids=ALL_FACTOR_IDS,
    )
    def test_factor_id_value(
        self, factor_cls: type[BaseFactor], expected_id: str
    ) -> None:
        assert factor_cls.factor_id() == expected_id


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------

class TestFactorCategories:
    def test_momentum_category(self) -> None:
        for cls in [Momentum1M, Momentum3M, Momentum6M1M]:
            assert cls.spec().category == "momentum"

    def test_value_category(self) -> None:
        for cls in [EP, BP, SP]:
            assert cls.spec().category == "value"

    def test_quality_category(self) -> None:
        for cls in [ROE, GrossMargin, DebtToAsset]:
            assert cls.spec().category == "quality"

    def test_volatility_category(self) -> None:
        for cls in [RealizedVol20D, IdiosyncraticVol]:
            assert cls.spec().category == "volatility"

    def test_liquidity_category(self) -> None:
        for cls in [Turnover20D, AmihudIlliquidity]:
            assert cls.spec().category == "liquidity"


# ---------------------------------------------------------------------------
# Lookback days tests
# ---------------------------------------------------------------------------

class TestLookbackDays:
    def test_short_term(self) -> None:
        assert Momentum1M.spec().lookback_days == 20
        assert RealizedVol20D.spec().lookback_days == 20
        assert Turnover20D.spec().lookback_days == 20
        assert AmihudIlliquidity.spec().lookback_days == 20

    def test_medium_term(self) -> None:
        assert Momentum3M.spec().lookback_days == 60
        assert IdiosyncraticVol.spec().lookback_days == 60

    def test_long_term(self) -> None:
        assert Momentum6M1M.spec().lookback_days == 120

    def test_fundamental(self) -> None:
        for cls in [EP, BP, SP, ROE, GrossMargin, DebtToAsset]:
            assert cls.spec().lookback_days == 1


# ---------------------------------------------------------------------------
# Compute tests — price-based factors
# ---------------------------------------------------------------------------

class TestMomentumCompute:
    def test_momentum_1m(self) -> None:
        df = _make_price_data()
        result = Momentum1M().compute(df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)
        # First 20 values are NaN
        assert result.iloc[:20].isna().all()
        # After lookback, values are finite
        assert result.iloc[20:].notna().all()

    def test_momentum_3m(self) -> None:
        df = _make_price_data()
        result = Momentum3M().compute(df)
        assert isinstance(result, pd.Series)
        assert result.iloc[:60].isna().all()
        assert result.iloc[60:].notna().all()

    def test_momentum_6m_1m(self) -> None:
        df = _make_price_data()
        result = Momentum6M1M().compute(df)
        assert isinstance(result, pd.Series)
        assert result.iloc[:120].isna().all()
        assert result.iloc[120:].notna().all()

    def test_momentum_1m_is_negative_of_price_return(self) -> None:
        """momentum_1m should equal -(close / close.shift(20) - 1)."""
        df = _make_price_data()
        result = Momentum1M().compute(df)
        expected = -(df["close"] / df["close"].shift(20) - 1)
        pd.testing.assert_series_equal(result.iloc[20:], expected.iloc[20:], check_names=False)


class TestVolatilityCompute:
    def test_realized_vol_20d(self) -> None:
        df = _make_price_data()
        result = RealizedVol20D().compute(df)
        assert isinstance(result, pd.Series)
        # pct_change loses first row, rolling(20) loses 19 more -> first valid at index 20
        assert result.iloc[:20].isna().all()
        assert result.iloc[20:].notna().all()
        # Volatility must be non-negative
        assert (result.dropna() >= 0).all()

    def test_idiosyncratic_vol(self) -> None:
        df = _make_price_data()
        result = IdiosyncraticVol().compute(df)
        assert isinstance(result, pd.Series)
        # pct_change loses 1, rolling(60) mean loses 59, rolling(60) std loses 59 more
        # First valid value at index 119 (0-based)
        assert result.iloc[:119].isna().all()
        valid = result.iloc[119:].dropna()
        assert len(valid) > 0
        assert (valid >= 0).all()


class TestLiquidityCompute:
    def test_turnover_20d(self) -> None:
        df = _make_price_data()
        result = Turnover20D().compute(df)
        assert isinstance(result, pd.Series)
        # rolling(20) with min_periods=20 -> first valid at index 19
        assert result.iloc[:19].isna().all()
        assert result.iloc[19:].notna().all()

    def test_amihud_illiquidity(self) -> None:
        df = _make_price_data()
        result = AmihudIlliquidity().compute(df)
        assert isinstance(result, pd.Series)
        assert result.iloc[:20].isna().all()
        valid = result.iloc[20:].dropna()
        assert len(valid) > 0
        # Amihud ratio is non-negative
        assert (valid >= 0).all()


# ---------------------------------------------------------------------------
# Compute tests — fundamental factors
# ---------------------------------------------------------------------------

class TestValueCompute:
    def test_ep(self) -> None:
        df = _make_fundamental_data()
        result = EP().compute(df)
        assert isinstance(result, pd.Series)
        expected = df["net_profit_ttm"] / df["market_cap"]
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_bp(self) -> None:
        df = _make_fundamental_data()
        result = BP().compute(df)
        expected = df["net_asset"] / df["market_cap"]
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_sp(self) -> None:
        df = _make_fundamental_data()
        result = SP().compute(df)
        expected = df["revenue_ttm"] / df["market_cap"]
        pd.testing.assert_series_equal(result, expected, check_names=False)


class TestQualityCompute:
    def test_roe(self) -> None:
        df = _make_fundamental_data()
        result = ROE().compute(df)
        expected = df["net_profit"] / df["net_asset"]
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_gross_margin(self) -> None:
        df = _make_fundamental_data()
        result = GrossMargin().compute(df)
        expected = df["gross_profit"] / df["revenue"]
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_debt_to_asset(self) -> None:
        df = _make_fundamental_data()
        result = DebtToAsset().compute(df)
        expected = df["total_debt"] / df["total_asset"]
        pd.testing.assert_series_equal(result, expected, check_names=False)


# ---------------------------------------------------------------------------
# Required columns tests
# ---------------------------------------------------------------------------

class TestRequiredColumns:
    def test_price_factors(self) -> None:
        assert Momentum1M.required_columns() == ["close"]
        assert Momentum3M.required_columns() == ["close"]
        assert Momentum6M1M.required_columns() == ["close"]
        assert RealizedVol20D.required_columns() == ["close"]
        assert IdiosyncraticVol.required_columns() == ["close"]

    def test_value_factors(self) -> None:
        assert EP.required_columns() == ["net_profit_ttm", "market_cap"]
        assert BP.required_columns() == ["net_asset", "market_cap"]
        assert SP.required_columns() == ["revenue_ttm", "market_cap"]

    def test_quality_factors(self) -> None:
        assert ROE.required_columns() == ["net_profit", "net_asset"]
        assert GrossMargin.required_columns() == ["gross_profit", "revenue"]
        assert DebtToAsset.required_columns() == ["total_debt", "total_asset"]

    def test_liquidity_factors(self) -> None:
        assert Turnover20D.required_columns() == ["volume", "float_shares"]
        assert AmihudIlliquidity.required_columns() == ["close", "volume"]


# ---------------------------------------------------------------------------
# Registry integration tests
# ---------------------------------------------------------------------------

class TestRegistryIntegration:
    def test_all_13_factors_register(self) -> None:
        registry = FactorRegistry()
        for cls in ALL_FACTOR_CLASSES:
            registry.register(cls)
        assert len(registry.list_factors()) == 13

    def test_all_factor_ids_present(self) -> None:
        registry = FactorRegistry()
        for cls in ALL_FACTOR_CLASSES:
            registry.register(cls)
        for fid in ALL_FACTOR_IDS:
            assert registry.get_factor(fid) is not None

    def test_category_filtering(self) -> None:
        registry = FactorRegistry()
        for cls in ALL_FACTOR_CLASSES:
            registry.register(cls)
        momentum = registry.list_by_category("momentum")
        assert len(momentum) == 3
        value = registry.list_by_category("value")
        assert len(value) == 3
        quality = registry.list_by_category("quality")
        assert len(quality) == 3
        volatility = registry.list_by_category("volatility")
        assert len(volatility) == 2
        liquidity = registry.list_by_category("liquidity")
        assert len(liquidity) == 2

    def test_no_duplicate_factor_ids(self) -> None:
        ids = [cls.factor_id() for cls in ALL_FACTOR_CLASSES]
        assert len(ids) == len(set(ids)), f"Duplicate factor IDs found: {ids}"
