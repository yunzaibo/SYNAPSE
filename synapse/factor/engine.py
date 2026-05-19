"""FactorEngine -- orchestrates factor computation across data sources and registry.

Provides compute_factor, compute_batch, and compute_all methods.
Handles DataSource fetching, MarketData-to-DataFrame conversion,
point-in-time validation, and PartialResult error containment.

Part of P6 Factor Research Engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import pandas as pd

from synapse.event.datasource import DataSource, MarketData
from synapse.factor.registry import FactorRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PartialResult
# ---------------------------------------------------------------------------

@dataclass
class PartialResult:
    """Result for a single factor that may have failed during computation."""

    factor_id: str
    success: bool
    value: Optional[pd.Series] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# FactorEngine
# ---------------------------------------------------------------------------

class FactorEngine:
    """Orchestrates factor computation given a registry and data source.

    Responsibilities:
    - Fetch market data via DataSource
    - Convert MarketData list to a single DataFrame
    - Compute individual, batch, or all factors
    - Apply point-in-time validation (publication_lag)
    - Contain factor failures via PartialResult
    """

    def __init__(self, registry: FactorRegistry, data_source: DataSource) -> None:
        self._registry = registry
        self._data_source = data_source

    # ------------------------------------------------------------------
    # Data conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dataframe(market_data: list[MarketData]) -> pd.DataFrame:
        """Convert a list of MarketData records into a single DataFrame.

        Each MarketData.payload is expected to contain a ``records`` key
        with a list of dicts (each dict representing one row), or be a flat
        dict that gets wrapped into a single-row DataFrame.

        The resulting DataFrame always has a ``ticker`` column and a
        ``source`` column added from the MarketData envelope.
        """
        rows: list[dict[str, Any]] = []
        for md in market_data:
            payload = md.payload
            if "records" in payload:
                for record in payload["records"]:
                    row = dict(record)
                    row["ticker"] = md.ticker
                    row["source"] = md.source
                    rows.append(row)
            else:
                row = dict(payload)
                row["ticker"] = md.ticker
                row["source"] = md.source
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Ensure ``date`` column is datetime if present
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        return df

    # ------------------------------------------------------------------
    # Point-in-time validation
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_point_in_time(
        df: pd.DataFrame, compute_date: date, publication_lag: int
    ) -> pd.DataFrame:
        """Filter rows so that data is available before or on compute_date.

        ``publication_lag`` shifts the cutoff earlier by the specified number
        of calendar days. For example, a publication_lag of 1 with
        compute_date=2024-01-10 means data from 2024-01-09 onward is usable.

        If the DataFrame has no ``date`` column, the filter is a no-op.
        """
        if "date" not in df.columns or df.empty:
            return df

        cutoff = pd.Timestamp(compute_date) - pd.Timedelta(days=publication_lag)
        mask = df["date"] <= cutoff
        return df.loc[mask].copy()

    # ------------------------------------------------------------------
    # Single factor
    # ------------------------------------------------------------------

    def compute_factor(
        self, factor_id: str, tickers: list[str], target_date: date
    ) -> pd.Series:
        """Compute a single factor for the given tickers and date.

        Parameters
        ----------
        factor_id:
            Registered factor identifier.
        tickers:
            Stock ticker symbols to include.
        target_date:
            The computation date (point-in-time anchor).

        Returns
        -------
        pd.Series
            Factor values indexed by ticker.

        Raises
        ------
        ValueError
            If factor_id is not registered.
        """
        factor_cls = self._registry.get_factor(factor_id)
        if factor_cls is None:
            raise ValueError(f"Factor '{factor_id}' is not registered")

        market_data = self._data_source.fetch(tickers)
        df = self._to_dataframe(market_data)

        if df.empty:
            return pd.Series(dtype=float, name=factor_id)

        spec = factor_cls.spec()
        df = self._filter_point_in_time(df, target_date, spec.publication_lag)

        if df.empty:
            return pd.Series(dtype=float, name=factor_id)

        factor_instance = factor_cls()
        result = factor_instance.compute(df)
        result.name = factor_id
        return result

    # ------------------------------------------------------------------
    # Batch computation
    # ------------------------------------------------------------------

    def compute_batch(
        self, factor_ids: list[str], tickers: list[str], target_date: date
    ) -> pd.DataFrame:
        """Compute multiple factors and combine into a single DataFrame.

        Each factor is computed independently. Failures are captured as
        PartialResult with error info and excluded from the output.

        Returns
        -------
        pd.DataFrame
            Columns correspond to factor_ids, rows to tickers.
        """
        parts: dict[str, pd.Series] = {}

        for fid in factor_ids:
            partial = self._compute_with_error_handling(fid, tickers, target_date)
            if partial.success and partial.value is not None and not partial.value.empty:
                parts[fid] = partial.value

        if not parts:
            return pd.DataFrame()

        return pd.DataFrame(parts)

    # ------------------------------------------------------------------
    # Compute all
    # ------------------------------------------------------------------

    def compute_all(
        self, tickers: list[str], target_date: date
    ) -> pd.DataFrame:
        """Compute every registered factor and combine into a single DataFrame.

        Returns
        -------
        pd.DataFrame
            Columns correspond to factor_ids, rows to tickers.
        """
        factor_ids = list(self._registry.list_factors().keys())
        return self.compute_batch(factor_ids, tickers, target_date)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_with_error_handling(
        self, factor_id: str, tickers: list[str], target_date: date
    ) -> PartialResult:
        """Wrap compute_factor with error containment."""
        try:
            value = self.compute_factor(factor_id, tickers, target_date)
            return PartialResult(factor_id=factor_id, success=True, value=value)
        except Exception as exc:
            logger.warning(
                "Factor '%s' computation failed: %s", factor_id, exc, exc_info=True
            )
            return PartialResult(
                factor_id=factor_id, success=False, error=str(exc)
            )
