"""Cross-sectional IC analysis for factor evaluation.

Computes per-date Spearman RankIC, rolling IC, ICIR, and IC positive ratio
from factor values aligned with forward returns.

Uses scipy.stats.spearmanr for RankIC computation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from synapse.backtest.result import ICAnalysisResult


class ICAnalyzer:
    """Cross-sectional Information Coefficient analyzer.

    Parameters
    ----------
    window : int
        Rolling window size for computing rolling IC mean (default 20).
    min_periods : int
        Minimum number of valid IC observations required for rolling mean
        computation (default 10).  Also used as the floor for short-series
        statistics -- if fewer dates exist, statistics are still computed over
        the available data.
    min_stocks : int
        Minimum number of valid stock pairs at a single date to compute
        that date's RankIC (default 10).
    """

    def __init__(
        self, window: int = 20, min_periods: int = 10, min_stocks: int = 10
    ) -> None:
        self.window = window
        self.min_periods = min_periods
        self.min_stocks = min_stocks

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_ic(
        self,
        factor_values: pd.DataFrame,
        forward_returns: pd.Series,
        factor_id: str = "",
    ) -> ICAnalysisResult:
        """Compute cross-sectional IC analysis for a single factor.

        Parameters
        ----------
        factor_values : pd.DataFrame
            Factor values with MultiIndex ``(date, ticker)`` and a single column.
        forward_returns : pd.Series
            Next-period returns with MultiIndex ``(date, ticker)``.
        factor_id : str
            Identifier for the factor (stored in the result).

        Returns
        -------
        ICAnalysisResult
            Immutable result container with IC series, statistics, and rolling IC.
        """
        # --- Edge case: empty input --------------------------------------
        if factor_values.empty or forward_returns.empty:
            return ICAnalysisResult(factor_id=factor_id)

        # Ensure inputs share the same index
        common_index = factor_values.index.intersection(forward_returns.index)
        if len(common_index) == 0:
            return ICAnalysisResult(factor_id=factor_id)

        fv_aligned = factor_values.loc[common_index]
        fr_aligned = forward_returns.loc[common_index]

        # Get the single column of factor values
        if isinstance(fv_aligned, pd.DataFrame):
            fv_col = fv_aligned.iloc[:, 0]
        else:
            fv_col = fv_aligned

        # Extract unique dates (first level of MultiIndex)
        dates = fv_col.index.get_level_values(0).unique()
        dates = sorted(dates)

        rank_ic_values: list[float] = []

        for dt in dates:
            # Slice cross-section for this date
            mask = fv_col.index.get_level_values(0) == dt
            fv_cs = fv_col.loc[mask]
            if isinstance(fr_aligned, pd.Series):
                fr_cs = fr_aligned.loc[mask]
            else:
                fr_cs = fr_aligned.iloc[:, 0].loc[mask]

            # Drop NaN pairs
            valid = pd.DataFrame({"fv": fv_cs, "fr": fr_cs}).dropna()

            if len(valid) < self.min_stocks:
                continue

            rho, _ = spearmanr(valid["fv"].values, valid["fr"].values)
            if np.isfinite(rho):
                rank_ic_values.append(float(rho))

        # --- Build result -----------------------------------------------
        if len(rank_ic_values) == 0:
            return ICAnalysisResult(factor_id=factor_id)

        ic_series = tuple(rank_ic_values)
        ic_s = pd.Series(rank_ic_values, dtype=float)

        # Rolling IC (mean over window)
        rolling_s = ic_s.rolling(window=min(self.window, len(ic_s)), min_periods=1).mean()
        rolling_ic = tuple(rolling_s.tolist())

        # Statistics
        ic_mean = float(ic_s.mean())
        ic_std = float(ic_s.std(ddof=1)) if len(ic_s) > 1 else 0.0
        icir = ic_mean / ic_std if ic_std > 1e-10 else 0.0

        # RankIC == IC in this implementation (both are Spearman RankIC)
        rank_ic_mean = ic_mean
        rank_ic_std = ic_std
        rank_icir = icir

        # Positive ratio
        positive_count = int((ic_s > 0).sum())
        ic_positive_ratio = positive_count / len(rank_ic_values)

        return ICAnalysisResult(
            factor_id=factor_id,
            ic_series=ic_series,
            rank_ic_series=ic_series,
            ic_mean=ic_mean,
            ic_std=ic_std,
            icir=icir,
            rank_ic_mean=rank_ic_mean,
            rank_ic_std=rank_ic_std,
            rank_icir=rank_icir,
            rolling_ic=rolling_ic,
            ic_positive_ratio=ic_positive_ratio,
        )
