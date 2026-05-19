"""Tests for synapse.factor.portfolio (F-014: Factor Portfolio Optimizer)."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from synapse.factor.portfolio import (
    FactorPortfolio,
    FactorPortfolioOptimizer,
    check_constraints,
    compute_turnover,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_factor_values(n: int = 50, cols: int = 3) -> pd.DataFrame:
    """Synthetic factor values: n rows, cols factor columns."""
    rng = np.random.default_rng(42)
    col_names = [f"factor_{i}" for i in range(cols)]
    data = rng.standard_normal((n, cols))
    return pd.DataFrame(data, columns=col_names)


def _make_ic_history(cols: int = 3, n_periods: int = 20) -> pd.DataFrame:
    """Synthetic IC history: n_periods rows, cols factor columns."""
    rng = np.random.default_rng(99)
    col_names = [f"factor_{i}" for i in range(cols)]
    # Different IC magnitudes per factor
    scales = [0.05, 0.10, 0.02]
    data = rng.standard_normal((n_periods, cols)) * scales[:cols]
    return pd.DataFrame(data, columns=col_names)


# ---------------------------------------------------------------------------
# Test: FactorPortfolio dataclass
# ---------------------------------------------------------------------------

class TestFactorPortfolio:
    def test_creation(self):
        p = FactorPortfolio(
            name="test_portfolio",
            weights={"a": 0.5, "b": 0.5},
            method="equal",
            expected_ic=0.05,
            expected_risk=0.10,
        )
        assert p.name == "test_portfolio"
        assert p.weights == {"a": 0.5, "b": 0.5}
        assert p.method == "equal"
        assert p.expected_ic == 0.05
        assert p.expected_risk == 0.10
        assert p.rebalance_freq == "daily"
        assert isinstance(p.created_at, datetime)

    def test_custom_rebalance_freq(self):
        p = FactorPortfolio(
            name="monthly",
            weights={"x": 1.0},
            method="risk_parity",
            expected_ic=0.0,
            expected_risk=0.0,
            rebalance_freq="monthly",
        )
        assert p.rebalance_freq == "monthly"


# ---------------------------------------------------------------------------
# Test: equal_weight
# ---------------------------------------------------------------------------

class TestEqualWeight:
    def test_equal_weights_sum_to_one(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        w = opt.equal_weight(fv)
        assert len(w) == 3
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_all_weights_equal(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        w = opt.equal_weight(fv)
        vals = list(w.values())
        assert all(abs(v - vals[0]) < 1e-9 for v in vals)

    def test_single_factor(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values(cols=1)
        w = opt.equal_weight(fv)
        assert abs(w["factor_0"] - 1.0) < 1e-9

    def test_empty_input(self):
        opt = FactorPortfolioOptimizer()
        fv = pd.DataFrame()
        w = opt.equal_weight(fv)
        assert w == {}


# ---------------------------------------------------------------------------
# Test: ic_weighted
# ---------------------------------------------------------------------------

class TestIcWeighted:
    def test_weights_proportional_to_ic(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        ic = _make_ic_history()
        w = opt.ic_weighted(fv, ic)
        # factor_1 has highest IC, factor_2 has lowest
        assert w["factor_1"] > w["factor_0"] > w["factor_2"]

    def test_weights_sum_to_one(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        ic = _make_ic_history()
        w = opt.ic_weighted(fv, ic)
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_fallback_equal_when_all_zero_ic(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        ic = pd.DataFrame(
            {"factor_0": [0.0, 0.0], "factor_1": [0.0, 0.0], "factor_2": [0.0, 0.0]}
        )
        w = opt.ic_weighted(fv, ic)
        # All zero IC -> equal weight
        vals = list(w.values())
        assert all(abs(v - 1.0 / 3) < 1e-9 for v in vals)

    def test_missing_ic_column(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        ic = pd.DataFrame({"factor_0": [0.1]})
        w = opt.ic_weighted(fv, ic)
        assert abs(sum(w.values()) - 1.0) < 1e-9
        # factor_0 has IC 0.1, others have 0 -> factor_0 gets full weight
        assert w["factor_0"] > 0.99

    def test_single_factor(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values(cols=1)
        ic = pd.DataFrame({"factor_0": [0.1, 0.2]})
        w = opt.ic_weighted(fv, ic)
        assert abs(w["factor_0"] - 1.0) < 1e-9

    def test_empty_input(self):
        opt = FactorPortfolioOptimizer()
        fv = pd.DataFrame()
        ic = pd.DataFrame()
        w = opt.ic_weighted(fv, ic)
        assert w == {}


# ---------------------------------------------------------------------------
# Test: risk_parity
# ---------------------------------------------------------------------------

class TestRiskParity:
    def test_weights_inversely_proportional_to_vol(self):
        opt = FactorPortfolioOptimizer()
        # Create data with known volatilities
        fv = pd.DataFrame(
            {
                "low_vol":  [1.0, 1.1, 1.0, 1.1, 1.0],   # std ~ 0.05
                "mid_vol":  [1.0, 1.2, 1.0, 1.2, 1.0],   # std ~ 0.10
                "high_vol": [1.0, 1.5, 1.0, 1.5, 1.0],   # std ~ 0.22
            }
        )
        w = opt.risk_parity(fv)
        # Low vol should get highest weight
        assert w["low_vol"] > w["mid_vol"] > w["high_vol"]

    def test_weights_sum_to_one(self):
        opt = FactorPortfolioOptimizer()
        fv = _make_factor_values()
        w = opt.risk_parity(fv)
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_single_factor(self):
        opt = FactorPortfolioOptimizer()
        fv = pd.DataFrame({"only_factor": [1.0, 2.0, 3.0]})
        w = opt.risk_parity(fv)
        assert abs(w["only_factor"] - 1.0) < 1e-9

    def test_zero_vol_fallback(self):
        """Constant column (zero std) should not crash."""
        opt = FactorPortfolioOptimizer()
        fv = pd.DataFrame(
            {
                "constant": [1.0, 1.0, 1.0],
                "varying":  [1.0, 2.0, 3.0],
            }
        )
        w = opt.risk_parity(fv)
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_empty_input(self):
        opt = FactorPortfolioOptimizer()
        fv = pd.DataFrame()
        w = opt.risk_parity(fv)
        assert w == {}


# ---------------------------------------------------------------------------
# Test: compute_turnover
# ---------------------------------------------------------------------------

class TestComputeTurnover:
    def test_same_weights_zero_turnover(self):
        w1 = {"a": 0.5, "b": 0.5}
        assert compute_turnover(w1, w1) == 0.0

    def test_known_turnover(self):
        old = {"a": 0.6, "b": 0.4}
        new = {"a": 0.4, "b": 0.6}
        # |0.4-0.6| + |0.6-0.4| = 0.4 -> /2 = 0.2
        assert abs(compute_turnover(old, new) - 0.2) < 1e-9

    def test_full_replacement(self):
        old = {"a": 1.0, "b": 0.0}
        new = {"a": 0.0, "b": 1.0}
        # |0.0-1.0| + |1.0-0.0| = 2.0 -> /2 = 1.0
        assert abs(compute_turnover(old, new) - 1.0) < 1e-9

    def test_empty_dicts(self):
        assert compute_turnover({}, {}) == 0.0

    def test_new_factor_added(self):
        old = {"a": 1.0}
        new = {"a": 0.5, "b": 0.5}
        # |0.5-1.0| + |0.5-0.0| = 1.0 -> /2 = 0.5
        assert abs(compute_turnover(old, new) - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Test: check_constraints
# ---------------------------------------------------------------------------

class TestCheckConstraints:
    def test_valid_portfolio(self):
        p = FactorPortfolio(
            name="ok",
            weights={"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25},
            method="equal",
            expected_ic=0.05,
            expected_risk=0.10,
        )
        violations = check_constraints(p)
        assert violations == []

    def test_excessive_single_weight(self):
        p = FactorPortfolio(
            name="bad",
            weights={"a": 0.5, "b": 0.5},
            method="equal",
            expected_ic=0.05,
            expected_risk=0.10,
        )
        violations = check_constraints(p, max_single_weight=0.3)
        assert len(violations) == 2
        assert any("'a'" in v for v in violations)
        assert any("'b'" in v for v in violations)

    def test_weight_sum_violation(self):
        p = FactorPortfolio(
            name="wrong_sum",
            weights={"a": 0.6, "b": 0.6},
            method="equal",
            expected_ic=0.05,
            expected_risk=0.10,
        )
        violations = check_constraints(p)
        assert any("1.2" in v for v in violations)

    def test_borderline_weight_passes(self):
        p = FactorPortfolio(
            name="borderline",
            weights={"a": 0.3, "b": 0.3, "c": 0.4},
            method="ic_weighted",
            expected_ic=0.05,
            expected_risk=0.10,
        )
        violations = check_constraints(p, max_single_weight=0.3)
        # 0.3 is allowed (<= 0.3), 0.4 should violate
        assert len(violations) == 1
        assert "'c'" in violations[0]
