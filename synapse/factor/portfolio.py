"""Factor Portfolio Optimizer -- equal-weight, IC-weighted, and risk-parity methods.

Provides FactorPortfolioOptimizer with three optimization strategies,
FactorPortfolio dataclass for portfolio metadata, and helper functions
for turnover calculation and constraint checking.

Part of P6 Factor Research Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# FactorPortfolio
# ---------------------------------------------------------------------------

@dataclass
class FactorPortfolio:
    """Portfolio combining multiple factors with computed weights."""

    name: str
    weights: dict[str, float]      # factor_id -> weight
    method: str                     # "equal" | "ic_weighted" | "risk_parity"
    expected_ic: float
    expected_risk: float
    rebalance_freq: str = "daily"   # "daily" | "weekly" | "monthly"
    created_at: datetime = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()


# ---------------------------------------------------------------------------
# FactorPortfolioOptimizer
# ---------------------------------------------------------------------------

class FactorPortfolioOptimizer:
    """Optimize factor portfolio weights using various methods."""

    def equal_weight(self, factor_values: pd.DataFrame) -> dict[str, float]:
        """Equal-weight: all factors receive the same weight.

        Parameters
        ----------
        factor_values : pd.DataFrame
            Factor values indexed by ticker with factor_id columns.

        Returns
        -------
        dict[str, float]
            Weight dict summing to 1.0.
        """
        if factor_values.empty:
            return {}
        cols = list(factor_values.columns)
        n = len(cols)
        w = 1.0 / n
        return {col: w for col in cols}

    def ic_weighted(
        self,
        factor_values: pd.DataFrame,
        ic_history: pd.DataFrame,
    ) -> dict[str, float]:
        """IC-weighted: weights proportional to absolute IC mean.

        Parameters
        ----------
        factor_values : pd.DataFrame
            Factor values (columns are factor_ids). Used for column reference.
        ic_history : pd.DataFrame
            Historical IC values with columns matching factor_ids.

        Returns
        -------
        dict[str, float]
            Weight dict summing to 1.0. Factors with zero IC get equal share.
        """
        cols = list(factor_values.columns)
        if not cols:
            return {}

        # Compute absolute IC mean for each factor
        abs_ic_means: dict[str, float] = {}
        for col in cols:
            if col in ic_history.columns:
                series = ic_history[col].dropna()
                abs_ic_means[col] = float(series.abs().mean()) if len(series) > 0 else 0.0
            else:
                abs_ic_means[col] = 0.0

        total = sum(abs_ic_means.values())

        # All zeros -> fall back to equal weight
        if total < 1e-12:
            n = len(cols)
            return {col: 1.0 / n for col in cols}

        return {col: val / total for col, val in abs_ic_means.items()}

    def risk_parity(self, factor_values: pd.DataFrame) -> dict[str, float]:
        """Risk-parity: weights inversely proportional to factor volatility.

        Parameters
        ----------
        factor_values : pd.DataFrame
            Factor values indexed by ticker with factor_id columns.

        Returns
        -------
        dict[str, float]
            Weight dict summing to 1.0.
        """
        if factor_values.empty:
            return {}

        # Compute std for each factor column
        stds = factor_values.std(axis=0)

        # Replace zero std with a tiny value to avoid division by zero
        inv_stds = 1.0 / stds.replace(0, np.finfo(float).eps)

        total = inv_stds.sum()
        if total < 1e-12:
            n = len(factor_values.columns)
            return {col: 1.0 / n for col in factor_values.columns}

        weights = inv_stds / total
        return weights.to_dict()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def compute_turnover(
    old_weights: dict[str, float], new_weights: dict[str, float]
) -> float:
    """Calculate portfolio turnover between two weight snapshots.

    Turnover = sum(|new_weight - old_weight|) / 2

    Parameters
    ----------
    old_weights : dict[str, float]
        Previous factor weights.
    new_weights : dict[str, float]
        New factor weights.

    Returns
    -------
    float
        Turnover ratio in [0, 1].
    """
    all_keys = set(old_weights.keys()) | set(new_weights.keys())
    if not all_keys:
        return 0.0

    total_diff = 0.0
    for k in all_keys:
        old = old_weights.get(k, 0.0)
        new = new_weights.get(k, 0.0)
        total_diff += abs(new - old)

    return total_diff / 2.0


def check_constraints(
    portfolio: FactorPortfolio,
    max_single_weight: float = 0.3,
) -> list[str]:
    """Check portfolio for constraint violations.

    Parameters
    ----------
    portfolio : FactorPortfolio
        The portfolio to check.
    max_single_weight : float
        Maximum allowed weight for any single factor (default 0.3).

    Returns
    -------
    list[str]
        List of violation descriptions. Empty if all constraints pass.
    """
    violations: list[str] = []

    # Check single-factor weight limit
    for fid, w in portfolio.weights.items():
        if w > max_single_weight + 1e-9:
            violations.append(
                f"Factor '{fid}' weight {w:.4f} exceeds max {max_single_weight:.4f}"
            )

    # Check weight sum
    total = sum(portfolio.weights.values())
    if abs(total - 1.0) > 1e-6:
        violations.append(f"Total weight {total:.6f} deviates from 1.0")

    return violations
