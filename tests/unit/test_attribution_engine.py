"""Tests for AttributionEngine — Barra-style factor return attribution."""

import numpy as np
import pandas as pd
import pytest

from synapse.backtest.attribution import AttributionEngine
from synapse.backtest.result import AttributionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dates(n: int = 100) -> pd.DatetimeIndex:
    return pd.bdate_range("2023-01-01", periods=n)


def _make_portfolio_returns(dates: pd.DatetimeIndex, noise: float = 0.01, seed: int = 42):
    rng = np.random.RandomState(seed)
    return pd.Series(rng.randn(len(dates)) * noise, index=dates)


def _make_factor_returns(dates: pd.DatetimeIndex, cols: int = 1, noise: float = 0.01, seed: int = 0):
    rng = np.random.RandomState(seed)
    data = rng.randn(len(dates), cols) * noise
    return pd.DataFrame(data, index=dates, columns=list(range(cols)))


def _pure_factor_portfolio(dates: pd.DatetimeIndex, noise: float = 0.005):
    """Portfolio return = exact factor return + small noise (beta ~ 1)."""
    rng = np.random.RandomState(99)
    factor = pd.DataFrame({"0": rng.randn(len(dates)) * 0.01}, index=dates)
    portfolio = factor["0"] + rng.randn(len(dates)) * noise
    return portfolio, factor


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAttributionResultFrozen:
    """AttributionResult is a frozen dataclass."""

    def test_immutable(self):
        r = AttributionResult()
        with pytest.raises(AttributeError):
            r.r_squared = 0.5  # type: ignore[misc]

    def test_default_fields(self):
        r = AttributionResult()
        assert r.factor_returns == {}
        assert r.residual_returns == ()
        assert r.total_factor_return == 0.0
        assert r.residual_return == 0.0
        assert r.r_squared == 0.0


class TestEmptyInputs:
    """Edge case: empty Series / DataFrame returns zero attribution."""

    def test_empty_portfolio_returns(self):
        engine = AttributionEngine()
        result = engine.compute(
            portfolio_returns=pd.Series(dtype=float),
            factor_returns=pd.DataFrame({"0": [1.0, 2.0]}),
        )
        assert result.factor_returns == {}
        assert result.residual_returns == ()
        assert result.r_squared == 0.0

    def test_empty_factor_returns(self):
        engine = AttributionEngine()
        result = engine.compute(
            portfolio_returns=pd.Series([0.01, 0.02]),
            factor_returns=pd.DataFrame(),
        )
        assert result.factor_returns == {}
        assert result.r_squared == 0.0

    def test_no_overlapping_dates(self):
        engine = AttributionEngine()
        dates_a = pd.bdate_range("2023-01-01", periods=5)
        dates_b = pd.bdate_range("2024-01-01", periods=5)
        result = engine.compute(
            portfolio_returns=pd.Series([0.01] * 5, index=dates_a),
            factor_returns=pd.DataFrame({"0": [0.01] * 5}, index=dates_b),
        )
        assert result.factor_returns == {}
        assert result.r_squared == 0.0


class TestZeroFactorReturns:
    """Edge case: factor returns all zero -> R-squared should be 0."""

    def test_zero_factor_returns_r_squared_zero(self):
        engine = AttributionEngine()
        dates = _dates(50)
        portfolio = pd.Series(np.ones(50) * 0.01, index=dates)
        zero_factor = pd.DataFrame({"0": np.zeros(50)}, index=dates)
        result = engine.compute(portfolio, zero_factor)
        # factor loadings will be ~0, R-squared near 0
        assert result.r_squared == pytest.approx(0.0, abs=1e-10)


class TestSingleFactorAttribution:
    """Single-factor case: OLS recovers beta ~ 1.0 by construction."""

    def test_beta_near_one(self):
        dates = _dates(200)
        portfolio, factor = _pure_factor_portfolio(dates, noise=0.0)
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        # With zero noise, beta should be very close to 1.0
        assert result.r_squared == pytest.approx(1.0, abs=1e-10)
        assert result.factor_returns[0] == pytest.approx(
            portfolio.mean(), abs=1e-10
        )


class TestMultiFactorAttribution:
    """Two-factor case: residual + factor = total."""

    def test_factor_plus_residual_equals_total(self):
        dates = _dates(200)
        rng = np.random.RandomState(7)
        f1 = pd.Series(rng.randn(200) * 0.01, index=dates)
        f2 = pd.Series(rng.randn(200) * 0.01, index=dates)
        factor_df = pd.DataFrame({"0": f1, "1": f2})
        # Portfolio = 2 * f1 - 1 * f2 + noise
        portfolio = 2 * f1 - 1 * f2 + rng.randn(200) * 0.001
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor_df)

        # sum of factor contributions + mean residual ~ mean portfolio return
        reconstructed = result.total_factor_return + result.residual_return
        assert reconstructed == pytest.approx(portfolio.mean(), abs=1e-8)


class TestRSquaredComputation:
    """R-squared via known variance decomposition."""

    def test_perfect_fit_rsquared_one(self):
        dates = _dates(100)
        rng = np.random.RandomState(12)
        factor = pd.DataFrame({"0": rng.randn(100) * 0.01}, index=dates)
        portfolio = factor["0"] * 3.0  # perfect fit, beta=3
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        assert result.r_squared == pytest.approx(1.0, abs=1e-10)

    def test_noisy_fit_rsquared_below_one(self):
        dates = _dates(200)
        rng = np.random.RandomState(55)
        factor = pd.DataFrame({"0": rng.randn(200) * 0.01}, index=dates)
        # heavy noise => low R-squared
        portfolio = factor["0"] * 0.5 + rng.randn(200) * 0.5
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        assert 0.0 < result.r_squared < 0.05  # very low fit


class TestInsufficientData:
    """When n_obs <= n_factors, return zero attribution."""

    def test_fewer_obs_than_factors(self):
        dates = pd.bdate_range("2023-01-01", periods=2)
        factor = pd.DataFrame(
            {"0": [0.01, 0.02], "1": [0.03, 0.04]}, index=dates
        )
        portfolio = pd.Series([0.05, 0.06], index=dates)
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        assert result.factor_returns == {}
        assert result.r_squared == 0.0

    def test_equal_obs_and_factors(self):
        dates = pd.bdate_range("2023-01-01", periods=2)
        factor = pd.DataFrame(
            {"0": [0.01, 0.02], "1": [0.03, 0.04]}, index=dates
        )
        portfolio = pd.Series([0.05, 0.06], index=dates)
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        # n_obs (2) <= n_factors (2) -> insufficient
        assert result.factor_returns == {}
        assert result.r_squared == 0.0


class TestResidualReturns:
    """Residual return is the mean of residual series."""

    def test_residual_mean(self):
        dates = _dates(100)
        rng = np.random.RandomState(88)
        factor = pd.DataFrame({"0": rng.randn(100) * 0.01}, index=dates)
        portfolio = factor["0"] + rng.randn(100) * 0.005
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        residual_arr = np.array(result.residual_returns)
        assert result.residual_return == pytest.approx(float(residual_arr.mean()), abs=1e-12)

    def test_residual_returns_tuple_length(self):
        dates = _dates(50)
        factor = _make_factor_returns(dates, cols=1, seed=10)
        portfolio = _make_portfolio_returns(dates, seed=20)
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor)
        assert len(result.residual_returns) == 50


class TestFactorExposuresParam:
    """factor_exposures param is accepted but unused in P2."""

    def test_accepts_optional_exposures(self):
        dates = _dates(100)
        portfolio, factor = _pure_factor_portfolio(dates, noise=0.0)
        exposures = pd.DataFrame({"0": np.ones(100)}, index=dates)
        engine = AttributionEngine()
        result = engine.compute(portfolio, factor, factor_exposures=exposures)
        assert isinstance(result, AttributionResult)
        assert result.r_squared == pytest.approx(1.0, abs=1e-10)
