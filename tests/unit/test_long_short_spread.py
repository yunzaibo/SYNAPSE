"""Tests for LongShortSpread and LongShortSpreadResult."""

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.spread import LongShortSpread, LongShortSpreadResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_quintile_df(
    q5: list[float],
    q1: list[float],
    index: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Build a quintile returns DataFrame with Q1..Q5 columns."""
    if index is None:
        index = pd.date_range("2024-01-02", periods=len(q5), freq="B")
    data = {
        "Q1": q1,
        "Q2": [0.0] * len(q5),
        "Q3": [0.0] * len(q5),
        "Q4": [0.0] * len(q5),
        "Q5": q5,
    }
    return pd.DataFrame(data, index=index)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLongShortSpreadResultDataclass:
    """LongShortSpreadResult frozen dataclass behaviour."""

    def test_default_values(self) -> None:
        result = LongShortSpreadResult()
        assert result.spread_returns == ()
        assert result.cumulative_spread == ()
        assert result.benchmark_returns == ()
        assert result.excess_returns == ()
        assert result.annual_spread_return == 0.0
        assert result.annual_benchmark_return == 0.0
        assert result.annual_excess_return == 0.0

    def test_frozen_immutability(self) -> None:
        result = LongShortSpreadResult(spread_returns=(0.01,))
        with pytest.raises(AttributeError):
            result.spread_returns = (0.02,)  # type: ignore[misc]

    def test_to_dict_roundtrip(self) -> None:
        original = LongShortSpreadResult(
            spread_returns=(0.01, 0.02),
            cumulative_spread=(0.01, 0.0302),
            annual_spread_return=0.05,
        )
        data = original.to_dict()
        restored = LongShortSpreadResult.from_dict(data)
        assert restored == original

    def test_from_dict_partial(self) -> None:
        data = {"spread_returns": [0.05], "annual_spread_return": 1.23}
        result = LongShortSpreadResult.from_dict(data)
        assert result.spread_returns == (0.05,)
        assert result.annual_spread_return == 1.23
        assert result.benchmark_returns == ()
        assert result.annual_excess_return == 0.0


class TestLongShortSpread:
    """LongShortSpread.compute logic."""

    def test_spread_equals_q5_minus_q1(self) -> None:
        """Spread returns should equal Q5 - Q1 for each period."""
        df = _make_quintile_df(q5=[0.01, 0.02, 0.03], q1=[0.005, 0.01, 0.005])
        engine = LongShortSpread()
        result = engine.compute(df)

        expected = (0.005, 0.01, 0.025)
        assert result.spread_returns == pytest.approx(expected)

    def test_cumulative_spread_matches_manual(self) -> None:
        """Cumulative spread = cumprod(1 + spread) - 1."""
        df = _make_quintile_df(q5=[0.01, 0.02, 0.03], q1=[0.005, 0.01, 0.005])
        engine = LongShortSpread()
        result = engine.compute(df)

        spreads = np.array([0.005, 0.01, 0.025])
        expected_cum = np.cumprod(1.0 + spreads) - 1.0
        assert result.cumulative_spread == pytest.approx(tuple(expected_cum))

    def test_single_period_cumulative(self) -> None:
        """With a single period, cumulative_spread has one element."""
        df = _make_quintile_df(q5=[0.05], q1=[0.02])
        engine = LongShortSpread()
        result = engine.compute(df)

        assert len(result.cumulative_spread) == 1
        assert result.cumulative_spread[0] == pytest.approx(0.03)

    def test_benchmark_comparison(self) -> None:
        """With benchmark, excess_returns = spread - benchmark and annualized metrics."""
        index = pd.date_range("2024-01-02", periods=3, freq="B")
        df = _make_quintile_df(q5=[0.01, 0.02, 0.03], q1=[0.005, 0.01, 0.005], index=index)
        bm = pd.Series([0.008, 0.015, 0.01], index=index)
        engine = LongShortSpread(benchmark_returns=bm)
        result = engine.compute(df)

        spreads = np.array([0.005, 0.01, 0.025])
        bm_arr = np.array([0.008, 0.015, 0.01])
        expected_excess = spreads - bm_arr

        assert result.benchmark_returns == pytest.approx(tuple(bm_arr))
        assert result.excess_returns == pytest.approx(tuple(expected_excess))
        assert result.annual_benchmark_return == pytest.approx(
            float((1.0 + (np.cumprod(1.0 + bm_arr)[-1] - 1.0)) ** (252.0 / 3) - 1.0)
        )
        assert result.annual_excess_return == pytest.approx(
            result.annual_spread_return - result.annual_benchmark_return
        )

    def test_missing_benchmark_produces_empty_excess(self) -> None:
        """Without benchmark, excess and benchmark fields are empty."""
        df = _make_quintile_df(q5=[0.01], q1=[0.005])
        engine = LongShortSpread()
        result = engine.compute(df)

        assert result.benchmark_returns == ()
        assert result.excess_returns == ()
        assert result.annual_benchmark_return == 0.0
        assert result.annual_excess_return == 0.0

    def test_empty_quintile_returns(self) -> None:
        """Empty input yields all-zero/empty result."""
        engine = LongShortSpread()
        result = engine.compute(pd.DataFrame(columns=["Q1", "Q2", "Q3", "Q4", "Q5"]))

        assert result.spread_returns == ()
        assert result.cumulative_spread == ()
        assert result.annual_spread_return == 0.0

    def test_annualized_return_formula(self) -> None:
        """Annualized return = (1 + total_return) ^ (252/n) - 1."""
        q5 = [0.01, 0.02, 0.03, 0.04]
        q1 = [0.005, 0.01, 0.005, 0.01]
        df = _make_quintile_df(q5=q5, q1=q1)
        engine = LongShortSpread()
        result = engine.compute(df)

        spreads = np.array(q5) - np.array(q1)
        total = float(np.cumprod(1.0 + spreads)[-1] - 1.0)
        expected_annual = float((1.0 + total) ** (252.0 / 4) - 1.0)
        assert result.annual_spread_return == pytest.approx(expected_annual)
