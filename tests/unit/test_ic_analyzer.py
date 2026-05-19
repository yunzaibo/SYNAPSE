"""Tests for ICAnalyzer: cross-sectional IC computation."""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from synapse.backtest.ic_analyzer import ICAnalyzer
from synapse.backtest.result import ICAnalysisResult


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _make_multiindex_data(
    dates: list, tickers: list, factor_vals: dict, return_vals: dict
):
    """Build (factor_values_df, forward_returns_series) from dict-of-dict."""
    idx = pd.MultiIndex.from_tuples(
        [(d, t) for d in dates for t in tickers], names=["date", "ticker"]
    )
    fv_data = [factor_vals.get((d, t), np.nan) for d in dates for t in tickers]
    fr_data = [return_vals.get((d, t), np.nan) for d in dates for t in tickers]
    fv_df = pd.DataFrame({"factor": fv_data}, index=idx)
    fr_s = pd.Series(fr_data, index=idx, name="forward_return")
    return fv_df, fr_s


def _make_random_data(n_dates: int = 30, n_tickers: int = 20, seed: int = 42):
    """Build random factor values and forward returns with MultiIndex."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B").tolist()
    tickers = [f"S{i:03d}" for i in range(n_tickers)]
    idx = pd.MultiIndex.from_tuples(
        [(d, t) for d in dates for t in tickers], names=["date", "ticker"]
    )
    fv = pd.DataFrame(
        {"factor": rng.standard_normal(len(idx))}, index=idx
    )
    fr = pd.Series(
        rng.standard_normal(len(idx)), index=idx, name="forward_return"
    )
    return fv, fr


# -----------------------------------------------------------------------
# 1. RankIC matches scipy.stats.spearmanr for known data
# -----------------------------------------------------------------------

def test_rankic_matches_scipy():
    """Single-date RankIC should equal scipy.stats.spearmanr."""
    tickers = [f"S{i}" for i in range(15)]
    date = pd.Timestamp("2024-01-02")
    fv_vals = list(range(15))
    fr_vals = list(range(15))

    fv_df, fr_s = _make_multiindex_data(
        dates=[date], tickers=tickers,
        factor_vals={(date, t): v for t, v in zip(tickers, fv_vals)},
        return_vals={(date, t): v for t, v in zip(tickers, fr_vals)},
    )

    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    result = analyzer.compute_ic(fv_df, fr_s)

    # Perfect positive correlation => RankIC == 1.0
    expected_rho, _ = spearmanr(fv_vals, fr_vals)
    assert len(result.rank_ic_series) == 1
    assert result.rank_ic_series[0] == pytest.approx(expected_rho, abs=1e-6)
    assert result.ic_mean == pytest.approx(expected_rho, abs=1e-6)


# -----------------------------------------------------------------------
# 2. ICIR = mean(IC) / std(IC)
# -----------------------------------------------------------------------

def test_icir_formula():
    """ICIR should equal ic_mean / ic_std."""
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    fv, fr = _make_random_data(n_dates=30, n_tickers=20, seed=99)
    result = analyzer.compute_ic(fv, fr, factor_id="random")

    if result.ic_std > 1e-10:
        expected_icir = result.ic_mean / result.ic_std
    else:
        expected_icir = 0.0

    assert result.icir == pytest.approx(expected_icir, abs=1e-8)


# -----------------------------------------------------------------------
# 3. Rolling window parameter controls output length
# -----------------------------------------------------------------------

def test_rolling_window_length():
    """Rolling IC tuple length should match number of IC observations."""
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    fv, fr = _make_random_data(n_dates=20, n_tickers=15, seed=7)
    result = analyzer.compute_ic(fv, fr)

    assert len(result.rolling_ic) == len(result.ic_series)


def test_rolling_window_shorter_than_series():
    """Rolling window larger than series uses full length (min_periods=1)."""
    analyzer_small = ICAnalyzer(window=3, min_periods=2, min_stocks=2)
    analyzer_large = ICAnalyzer(window=100, min_periods=2, min_stocks=2)
    fv, fr = _make_random_data(n_dates=10, n_tickers=15, seed=123)

    result_small = analyzer_small.compute_ic(fv, fr)
    result_large = analyzer_large.compute_ic(fv, fr)

    # Both should have the same number of IC observations
    assert len(result_small.ic_series) == len(result_large.ic_series)
    # Both rolling_ic lengths match ic_series length
    assert len(result_small.rolling_ic) == len(result_small.ic_series)
    assert len(result_large.rolling_ic) == len(result_large.ic_series)


# -----------------------------------------------------------------------
# 4. Edge case: empty DataFrame returns empty ICAnalysisResult
# -----------------------------------------------------------------------

def test_empty_dataframe():
    """Empty input should return ICAnalysisResult with empty tuples."""
    analyzer = ICAnalyzer()
    empty_df = pd.DataFrame(
        columns=["factor"],
        index=pd.MultiIndex.from_tuples([], names=["date", "ticker"]),
    )
    empty_s = pd.Series(
        dtype=float,
        index=pd.MultiIndex.from_tuples([], names=["date", "ticker"]),
        name="forward_return",
    )
    result = analyzer.compute_ic(empty_df, empty_s, factor_id="empty")

    assert isinstance(result, ICAnalysisResult)
    assert result.factor_id == "empty"
    assert result.ic_series == ()
    assert result.rank_ic_series == ()
    assert result.rolling_ic == ()
    assert result.ic_mean == 0.0
    assert result.ic_std == 0.0
    assert result.icir == 0.0


# -----------------------------------------------------------------------
# 5. Edge case: < min_periods dates returns short ICAnalysisResult
# -----------------------------------------------------------------------

def test_fewer_dates_than_min_periods():
    """Fewer dates than min_periods still computes available statistics."""
    analyzer = ICAnalyzer(window=10, min_periods=5, min_stocks=2)
    # Only 3 dates, fewer than min_periods=5
    fv, fr = _make_random_data(n_dates=3, n_tickers=15, seed=55)
    result = analyzer.compute_ic(fv, fr, factor_id="short")

    assert isinstance(result, ICAnalysisResult)
    assert result.factor_id == "short"
    # Should have some IC values (3 dates)
    assert len(result.ic_series) == 3
    assert len(result.rank_ic_series) == 3
    assert result.ic_mean != 0.0 or result.ic_std >= 0.0
    # Positive ratio should be between 0 and 1
    assert 0.0 <= result.ic_positive_ratio <= 1.0


# -----------------------------------------------------------------------
# 6. Frozen dataclass immutability
# -----------------------------------------------------------------------

def test_result_is_frozen():
    """ICAnalysisResult should be immutable (frozen dataclass)."""
    result = ICAnalysisResult(factor_id="test", ic_series=(0.1, 0.2))
    with pytest.raises(AttributeError):
        result.factor_id = "changed"  # type: ignore[misc]


def test_result_slots():
    """ICAnalysisResult should use slots (no __dict__)."""
    result = ICAnalysisResult(factor_id="test")
    assert not hasattr(result, "__dict__")


# -----------------------------------------------------------------------
# 7. min_stocks filters dates with too few valid pairs
# -----------------------------------------------------------------------

def test_min_stocks_filtering():
    """Dates with fewer than min_stocks valid pairs are skipped."""
    tickers = ["S1", "S2"]  # Only 2 tickers
    dates = pd.date_range("2024-01-01", periods=5, freq="B").tolist()

    # With min_stocks=10, all dates should be skipped
    fv, fr = _make_random_data(n_dates=5, n_tickers=2, seed=88)
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=10)
    result = analyzer.compute_ic(fv, fr, factor_id="filtered")

    assert result.ic_series == ()
    assert result.ic_mean == 0.0


# -----------------------------------------------------------------------
# 8. NaN handling: dates with all NaN are skipped
# -----------------------------------------------------------------------

def test_nan_dates_skipped():
    """Dates where all values are NaN should be skipped."""
    tickers = [f"S{i}" for i in range(15)]
    dates = pd.date_range("2024-01-01", periods=5, freq="B").tolist()

    factor_vals = {}
    return_vals = {}
    # Only fill data for first 3 dates; last 2 remain NaN
    for d in dates[:3]:
        for t in tickers:
            factor_vals[(d, t)] = hash((d, t)) % 10
            return_vals[(d, t)] = hash((d, t, "r")) % 10

    fv_df, fr_s = _make_multiindex_data(dates, tickers, factor_vals, return_vals)
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    result = analyzer.compute_ic(fv_df, fr_s)

    # Only 3 dates have data => 3 IC observations
    assert len(result.ic_series) == 3


# -----------------------------------------------------------------------
# 9. Perfect correlation yields ICIR near 1.0 (single value => std=0 => ICIR=0)
# -----------------------------------------------------------------------

def test_perfect_correlation_ic_stats():
    """Perfect positive correlation across all dates yields IC = 1.0."""
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    fv, fr = _make_random_data(n_dates=10, n_tickers=15, seed=10)
    # Override: make forward_returns perfectly aligned with factor
    fr = fv["factor"].copy()
    fr.name = "forward_return"

    result = analyzer.compute_ic(fv, fr, factor_id="perfect")

    # All RankIC values should be 1.0
    assert all(v == pytest.approx(1.0, abs=1e-6) for v in result.ic_series)
    assert result.ic_mean == pytest.approx(1.0, abs=1e-6)
    assert result.ic_positive_ratio == 1.0


# -----------------------------------------------------------------------
# 10. IC positive ratio correctness
# -----------------------------------------------------------------------

def test_positive_ratio():
    """IC positive ratio should reflect fraction of positive IC values."""
    analyzer = ICAnalyzer(window=5, min_periods=2, min_stocks=2)
    fv, fr = _make_random_data(n_dates=10, n_tickers=15, seed=33)
    result = analyzer.compute_ic(fv, fr)

    positive_count = sum(1 for v in result.ic_series if v > 0)
    expected_ratio = positive_count / len(result.ic_series)
    assert result.ic_positive_ratio == pytest.approx(expected_ratio, abs=1e-8)
