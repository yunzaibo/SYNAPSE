"""Quintile portfolio sorter.

Divides a stock universe into N equal groups (quintiles) based on
factor values, using pd.qcut for efficient assignment. Handles edge
cases: all-NaN factors, fewer stocks than quintiles, tied values.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import pandas as pd

from synapse.backtest.result import QuintilePortfolio

logger = logging.getLogger(__name__)


class QuintileSorter:
    """Sorts stocks into quintile groups based on factor values.

    Usage::

        sorter = QuintileSorter()
        portfolio = sorter.sort(factor_series, target_date, factor_name="momentum")
        timeseries = sorter.sort_timeseries(factor_df, rebalance_dates, factor_name="momentum")
    """

    def sort(
        self,
        factor_values: pd.Series,
        target_date: date,
        n_quintiles: int = 5,
        factor_name: str = "",
    ) -> Optional[QuintilePortfolio]:
        """Sort stocks into quintile groups for a single date.

        Args:
            factor_values: Series with MultiIndex (date, ticker).
            target_date: The date to extract factor values for.
            n_quintiles: Number of groups (default 5).
            factor_name: Identifier for the factor used.

        Returns:
            QuintilePortfolio with group assignments, or None if
            insufficient valid data.
        """
        # Extract values for target_date
        try:
            date_values = factor_values.xs(target_date, level="date")
        except KeyError:
            logger.warning("No factor data for date %s", target_date)
            return None

        if date_values.empty:
            return None

        universe_size = len(date_values)

        # Drop NaN values
        valid = date_values.dropna()
        valid_count = len(valid)

        if valid_count < n_quintiles:
            logger.info(
                "Skipping %s: only %d valid stocks (need %d)",
                target_date,
                valid_count,
                n_quintiles,
            )
            return None

        # Rank stocks (ascending=False: highest factor value -> rank 1)
        ranked = valid.rank(method="first", ascending=False)

        # Assign quintile labels using pd.qcut
        quintile_labels = pd.qcut(
            ranked,
            q=n_quintiles,
            labels=range(1, n_quintiles + 1),
            duplicates="drop",
        )

        # Build quintiles dict and weights dict
        quintiles: dict[int, tuple[str, ...]] = {}
        weights: dict[int, dict[str, float]] = {}

        for q_id in range(1, n_quintiles + 1):
            tickers = tuple(quintile_labels[quintile_labels == q_id].index)
            if tickers:
                quintiles[q_id] = tickers
                w = 1.0 / len(tickers)
                weights[q_id] = {t: w for t in tickers}

        return QuintilePortfolio(
            date=target_date,
            quintiles=quintiles,
            weights=weights,
            factor_name=factor_name,
            universe_size=universe_size,
            valid_count=valid_count,
        )

    def sort_timeseries(
        self,
        factor_values: pd.DataFrame,
        rebalance_dates: list[date],
        n_quintiles: int = 5,
        factor_name: str = "",
    ) -> dict[date, QuintilePortfolio]:
        """Sort stocks into quintiles for multiple rebalancing dates.

        Args:
            factor_values: DataFrame or Series with MultiIndex (date, ticker).
            rebalance_dates: List of dates to sort on.
            n_quintiles: Number of groups (default 5).
            factor_name: Identifier for the factor used.

        Returns:
            Dict mapping each successful rebalance date to its QuintilePortfolio.
        """
        # Convert DataFrame to Series if needed (use first column)
        if isinstance(factor_values, pd.DataFrame):
            if factor_values.shape[1] == 1:
                series = factor_values.iloc[:, 0]
            else:
                raise ValueError(
                    "factor_values DataFrame must have exactly one column, "
                    f"got {factor_values.shape[1]}"
                )
        else:
            series = factor_values

        result: dict[date, QuintilePortfolio] = {}
        for d in rebalance_dates:
            portfolio = self.sort(series, d, n_quintiles=n_quintiles, factor_name=factor_name)
            if portfolio is not None:
                result[d] = portfolio
        return result
