"""Tests for MetricsCalculator — single-pass performance metrics."""

from __future__ import annotations

import numpy as np
import pytest

from synapse.backtest.metrics import BacktestMetrics, MetricsCalculator, compute_metrics
from synapse.backtest.result import PerformanceMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EPS = 1e-6


def _assert_close(a: float, b: float, tol: float = EPS, msg: str = "") -> None:
    assert abs(a - b) < tol, f"{msg}: {a} != {b} (diff={abs(a - b)})"


# ---------------------------------------------------------------------------
# 1. Empty returns
# ---------------------------------------------------------------------------


class TestEmptyReturns:
    def test_empty_returns_all_zero(self) -> None:
        calc = MetricsCalculator()
        m = calc.compute(np.array([]))
        assert isinstance(m, PerformanceMetrics)
        assert m.annual_return == 0.0
        assert m.volatility == 0.0
        assert m.sharpe == 0.0
        assert m.max_drawdown == 0.0
        assert m.win_rate == 0.0
        assert m.profit_loss_ratio == 0.0
        assert m.calmar == 0.0
        assert m.information_ratio == 0.0


# ---------------------------------------------------------------------------
# 2. Single period
# ---------------------------------------------------------------------------


class TestSinglePeriod:
    def test_single_positive_return(self) -> None:
        calc = MetricsCalculator()
        m = calc.compute(np.array([0.01]))
        assert m.annual_return > 0
        assert m.volatility == 0.0
        assert m.win_rate == 1.0
        assert m.max_drawdown == 0.0

    def test_single_negative_return(self) -> None:
        calc = MetricsCalculator()
        m = calc.compute(np.array([-0.01]))
        assert m.annual_return < 0
        assert m.win_rate == 0.0


# ---------------------------------------------------------------------------
# 3. All positive returns — zero drawdown
# ---------------------------------------------------------------------------


class TestAllPositive:
    def test_constant_positive(self) -> None:
        returns = np.full(252, 0.0005)
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.annual_return > 0
        assert m.volatility == 0.0
        assert m.sharpe == 0.0  # zero std -> guard returns 0
        assert m.max_drawdown == 0.0
        assert m.win_rate == 1.0
        assert m.calmar == 0.0  # zero max_dd -> guard returns 0


# ---------------------------------------------------------------------------
# 4. All negative returns
# ---------------------------------------------------------------------------


class TestAllNegative:
    def test_constant_negative(self) -> None:
        returns = np.full(252, -0.001)
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.annual_return < 0
        assert m.volatility == 0.0
        assert m.win_rate == 0.0
        assert m.max_drawdown < 0
        assert m.profit_loss_ratio == 0.0  # no wins


# ---------------------------------------------------------------------------
# 5. Known annual return
# ---------------------------------------------------------------------------


class TestAnnualReturn:
    def test_known_annual_return(self) -> None:
        # 10% daily return for 1 day, annualized over 252 days
        returns = np.array([0.10])
        calc = MetricsCalculator(annualization_factor=252)
        m = calc.compute(returns)
        expected = (1.10) ** 252 - 1.0
        _assert_close(m.annual_return, round(expected, 6), msg="annual_return")

    def test_two_period_known(self) -> None:
        # Returns: +5%, -2%.  Product = 1.05 * 0.98 = 1.029
        returns = np.array([0.05, -0.02])
        calc = MetricsCalculator(annualization_factor=252)
        m = calc.compute(returns)
        expected = (1.05 * 0.98) ** (252 / 2) - 1.0
        _assert_close(m.annual_return, round(expected, 6), msg="annual_return")


# ---------------------------------------------------------------------------
# 6. Known volatility
# ---------------------------------------------------------------------------


class TestVolatility:
    def test_known_volatility(self) -> None:
        rng = np.random.RandomState(99)
        returns = rng.randn(100) * 0.02
        calc = MetricsCalculator()
        m = calc.compute(returns)
        expected = float(np.std(returns)) * np.sqrt(252)
        _assert_close(m.volatility, round(expected, 6), msg="volatility")


# ---------------------------------------------------------------------------
# 7. Known Sharpe ratio
# ---------------------------------------------------------------------------


class TestSharpe:
    def test_known_sharpe(self) -> None:
        rng = np.random.RandomState(42)
        returns = rng.randn(252) * 0.01 + 0.0003
        calc = MetricsCalculator(risk_free_rate=0.02)
        m = calc.compute(returns)
        rf_daily = 0.02 / 252
        excess = returns - rf_daily
        expected = float(np.mean(excess)) / float(np.std(excess)) * np.sqrt(252)
        _assert_close(m.sharpe, round(expected, 4), tol=1e-3, msg="sharpe")

    def test_zero_std_sharpe(self) -> None:
        returns = np.full(252, 0.001)
        calc = MetricsCalculator(risk_free_rate=0.02)
        m = calc.compute(returns)
        assert m.sharpe == 0.0  # all excess equal -> std=0 -> guard


# ---------------------------------------------------------------------------
# 8. Known max drawdown
# ---------------------------------------------------------------------------


class TestMaxDrawdown:
    def test_known_max_drawdown(self) -> None:
        # +10%, -20%: peak at 1.10, trough at 1.10*0.80=0.88
        # dd = (1.10 - 0.88) / 1.10 = 0.20
        returns = np.array([0.10, -0.20])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        _assert_close(m.max_drawdown, -0.20, msg="max_drawdown")

    def test_no_drawdown(self) -> None:
        returns = np.array([0.05, 0.03, 0.02])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.max_drawdown == 0.0


# ---------------------------------------------------------------------------
# 9. Known win rate
# ---------------------------------------------------------------------------


class TestWinRate:
    def test_known_win_rate(self) -> None:
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.03])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.win_rate == 0.6  # 3 wins out of 5


# ---------------------------------------------------------------------------
# 10. Known profit/loss ratio
# ---------------------------------------------------------------------------


class TestProfitLossRatio:
    def test_known_plr(self) -> None:
        # Wins: +0.10, +0.05  -> mean = 0.075
        # Losses: -0.02, -0.03 -> mean = -0.025
        # PLR = 0.075 / 0.025 = 3.0
        returns = np.array([0.10, -0.02, 0.05, -0.03])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        _assert_close(m.profit_loss_ratio, 3.0, msg="profit_loss_ratio")

    def test_no_losses_plr(self) -> None:
        returns = np.array([0.01, 0.02, 0.03])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.profit_loss_ratio == 0.0


# ---------------------------------------------------------------------------
# 11. Known Calmar ratio
# ---------------------------------------------------------------------------


class TestCalmar:
    def test_known_calmar(self) -> None:
        # 3 periods: +10%, -5%, +10%
        # cum = 1.10 * 0.95 * 1.10 = 1.1495
        # annual_return = (1.1495)^(252/3) - 1
        # peak = 1.10, trough = 1.045, dd = (1.10-1.045)/1.10 = 0.05
        returns = np.array([0.10, -0.05, 0.10])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        cum = 1.10 * 0.95 * 1.10
        annual_return = cum ** (252 / 3) - 1.0
        expected_calmar = annual_return / 0.05
        _assert_close(m.calmar, round(expected_calmar, 4), tol=1e-3, msg="calmar")


# ---------------------------------------------------------------------------
# 12. Known information ratio
# ---------------------------------------------------------------------------


class TestInformationRatio:
    def test_known_ir(self) -> None:
        portfolio = np.array([0.01, 0.02, -0.01, 0.03])
        benchmark = np.array([0.005, 0.01, -0.005, 0.01])
        calc = MetricsCalculator()
        m = calc.compute(portfolio, benchmark_returns=benchmark)
        active = portfolio - benchmark
        excess_return = float(np.mean(active)) * 252
        tracking_error = float(np.std(active)) * np.sqrt(252)
        expected_ir = excess_return / tracking_error
        _assert_close(m.information_ratio, round(expected_ir, 4), tol=1e-3, msg="IR")
        _assert_close(m.excess_return, round(excess_return, 6), msg="excess_return")

    def test_no_benchmark_ir(self) -> None:
        returns = np.array([0.01, 0.02, -0.01])
        calc = MetricsCalculator()  # no benchmark
        m = calc.compute(returns)
        assert m.information_ratio == 0.0
        assert m.excess_return == 0.0


# ---------------------------------------------------------------------------
# 13. Max drawdown duration
# ---------------------------------------------------------------------------


class TestMaxDrawdownDuration:
    def test_dd_duration(self) -> None:
        # [0.10, -0.05, -0.05, -0.05, 0.20]
        # cum: 1.10, 1.045, 0.99275, 0.94311, 1.13174
        # peak stays at 1.10 until last period
        # dd > 0 for periods 2,3,4 -> duration = 3
        returns = np.array([0.10, -0.05, -0.05, -0.05, 0.20])
        calc = MetricsCalculator()
        m = calc.compute(returns)
        assert m.max_drawdown_duration == 3


# ---------------------------------------------------------------------------
# 14. Single-pass matches multi-pass (numpy reference)
# ---------------------------------------------------------------------------


class TestSinglePassMatchesMultipass:
    def test_matches_numpy_reference(self) -> None:
        rng = np.random.RandomState(77)
        returns = rng.randn(504) * 0.015
        benchmark = rng.randn(504) * 0.01

        calc = MetricsCalculator(
            risk_free_rate=0.02,
            annualization_factor=252,
        )
        m = calc.compute(returns, benchmark_returns=benchmark)

        # Reference: annual return
        total_return = float(np.prod(1 + returns)) - 1
        expected_ar = (1 + total_return) ** (252 / len(returns)) - 1
        _assert_close(m.annual_return, round(expected_ar, 6), msg="annual_return")

        # Reference: volatility
        expected_vol = float(np.std(returns)) * np.sqrt(252)
        _assert_close(m.volatility, round(expected_vol, 6), msg="volatility")

        # Reference: max drawdown
        cum = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / peak
        expected_mdd = float(np.min(dd))
        _assert_close(m.max_drawdown, round(expected_mdd, 6), msg="max_drawdown")

        # Reference: win rate
        expected_wr = float(np.mean(returns > 0))
        _assert_close(m.win_rate, round(expected_wr, 4), msg="win_rate")

        # Reference: excess return and IR
        active = returns - benchmark
        expected_excess = float(np.mean(active)) * 252
        expected_te = float(np.std(active)) * np.sqrt(252)
        expected_ir = expected_excess / expected_te
        _assert_close(m.excess_return, round(expected_excess, 6), msg="excess_return")
        _assert_close(m.information_ratio, round(expected_ir, 4), tol=1e-3, msg="IR")


# ---------------------------------------------------------------------------
# 15. Legacy wrapper backward compatibility
# ---------------------------------------------------------------------------


class TestLegacyCompatibility:
    def test_compute_legacy_matches_compute_metrics(self) -> None:
        rng = np.random.RandomState(33)
        returns = rng.randn(252) * 0.01
        benchmark = rng.randn(252) * 0.005

        legacy = MetricsCalculator.compute_legacy(returns, benchmark, risk_free_rate=0.02)
        original = compute_metrics(returns, benchmark, risk_free_rate=0.02)

        assert isinstance(legacy, BacktestMetrics)
        assert legacy == original

    def test_compute_legacy_no_rf(self) -> None:
        returns = np.full(100, 0.001)
        benchmark = np.zeros(100)

        legacy = MetricsCalculator.compute_legacy(returns, benchmark)
        original = compute_metrics(returns, benchmark)
        assert legacy == original


# ---------------------------------------------------------------------------
# 16. Risk-free rate impact
# ---------------------------------------------------------------------------


class TestRiskFreeRate:
    def test_higher_rf_lower_sharpe(self) -> None:
        rng = np.random.RandomState(11)
        returns = rng.randn(252) * 0.01 + 0.0005
        m_low = MetricsCalculator(risk_free_rate=0.0).compute(returns)
        m_high = MetricsCalculator(risk_free_rate=0.05).compute(returns)
        assert m_high.sharpe <= m_low.sharpe

    def test_zero_rf_excess_return(self) -> None:
        returns = np.array([0.01, 0.02, 0.03])
        m = MetricsCalculator(risk_free_rate=0.0).compute(returns)
        # With rf=0 and no benchmark, excess_return=0 (no benchmark)
        assert m.excess_return == 0.0


# ---------------------------------------------------------------------------
# 17. Negative variance guard
# ---------------------------------------------------------------------------


class TestNumericalGuard:
    def test_zero_volatility_no_crash(self) -> None:
        returns = np.full(252, 0.001)
        calc = MetricsCalculator(risk_free_rate=0.001 * 252)  # rf = mean * 252
        m = calc.compute(returns)
        # All excess returns equal -> std=0 -> sharpe=0
        assert m.sharpe == 0.0
        assert m.volatility == 0.0

    def test_constant_excess_sharpe_zero(self) -> None:
        # All returns equal rf_daily -> excess=0 -> std=0
        rf_annual = 0.0252
        rf_daily = rf_annual / 252
        returns = np.full(252, rf_daily)
        calc = MetricsCalculator(risk_free_rate=rf_annual)
        m = calc.compute(returns)
        assert m.sharpe == 0.0
