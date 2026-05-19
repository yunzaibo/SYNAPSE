"""Barra-style factor model return attribution engine.

Implements OLS-based attribution of portfolio returns to factor exposures
and residual components. Designed for P2 single/multi-factor use cases.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from synapse.backtest.result import AttributionResult

logger = logging.getLogger(__name__)

_MIN_POINTS_PER_FACTOR = 2  # minimum data points per factor for OLS


class AttributionEngine:
    """Barra-style factor model return attribution.

    Decomposes portfolio returns into factor-driven and residual components
    via ordinary least squares (OLS) regression against factor return series.
    """

    def compute(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
        factor_exposures: Optional[pd.DataFrame] = None,
    ) -> AttributionResult:
        """Compute factor attribution via OLS regression.

        Args:
            portfolio_returns: Series indexed by dates, values are portfolio returns.
            factor_returns: DataFrame indexed by dates, columns are factor IDs (int),
                values are factor returns.
            factor_exposures: Optional DataFrame of factor loadings (reserved for
                multi-factor with pre-specified exposures; currently unused in P2).

        Returns:
            AttributionResult with factor contributions, residual series, and R-squared.
        """
        # --- empty-data guard ---
        if factor_returns.empty or portfolio_returns.empty:
            logger.debug("AttributionEngine: empty input, returning zero attribution")
            return AttributionResult()

        # --- align on common dates ---
        common_idx = portfolio_returns.index.intersection(factor_returns.index)
        if common_idx.empty:
            logger.debug("AttributionEngine: no overlapping dates")
            return AttributionResult()

        y = portfolio_returns.loc[common_idx].values.astype(float)
        X = factor_returns.loc[common_idx].values.astype(float)
        n_obs, n_factors = X.shape

        # --- insufficient data guard ---
        if n_obs <= n_factors:
            logger.warning(
                "AttributionEngine: insufficient data points (%d obs, %d factors)",
                n_obs,
                n_factors,
            )
            return AttributionResult()

        # --- OLS regression ---
        loadings, residuals, rank, _sval = np.linalg.lstsq(X, y, rcond=None)
        # residuals may be empty when n_obs == n_factors; recompute explicitly
        fitted = X @ loadings
        residual_values = y - fitted

        # --- factor contribution per factor ---
        factor_ids = list(factor_returns.columns)
        # beta_i * mean(factor_return_i) for each factor
        mean_factor_rets = factor_returns.loc[common_idx].mean(axis=0).values
        factor_contributions = {
            int(fid): float(loadings[i] * mean_factor_rets[i])
            for i, fid in enumerate(factor_ids)
        }
        total_factor_return = float(sum(factor_contributions.values()))

        # --- R-squared ---
        var_total = float(np.var(y))
        if var_total == 0.0:
            r_squared = 0.0
        else:
            var_residual = float(np.var(residual_values))
            r_squared = 1.0 - var_residual / var_total

        return AttributionResult(
            factor_returns=factor_contributions,
            residual_returns=tuple(residual_values.tolist()),
            total_factor_return=total_factor_return,
            residual_return=float(np.mean(residual_values)),
            r_squared=r_squared,
        )
