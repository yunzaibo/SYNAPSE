"""Data Source Adapter Protocol -- Unified interface for market data providers.

Defines DataSource ABC and MarketData schema for pluggable data source
integration. All adapters (EastMoney, Akshare, etc.) implement this protocol.

Part of P5 Real-time Data Source Integration.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class MarketData:
    """Standardized market data record returned by DataSource adapters.

    Attributes
    ----------
    ticker:
        Stock ticker symbol (e.g. "600519", "000001").
    source:
        Data source identifier (e.g. "eastmoney", "akshare").
    timestamp:
        Data timestamp (UTC).
    data_type:
        Data category (e.g. "quote", "capital_flow", "lhb").
    payload:
        Raw data dict from the source API.
    """

    ticker: str
    source: str
    timestamp: datetime
    data_type: str
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class DataSource(ABC):
    """Abstract base class for market data source adapters.

    Subclasses must implement:
    - ``source_name``: Unique identifier for this data source.
    - ``fetch(tickers)``: Fetch data for given tickers.
    - ``fetch_batch(tickers)``: Batch fetch with optional rate limiting.

    Example::

        class EastMoneyAdapter(DataSource):
            @property
            def source_name(self) -> str:
                return "eastmoney"

            def fetch(self, tickers: list[str]) -> list[MarketData]:
                ...
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this data source (e.g. 'eastmoney')."""
        ...

    @abstractmethod
    def fetch(self, tickers: list[str]) -> list[MarketData]:
        """Fetch market data for the given list of tickers.

        Parameters
        ----------
        tickers:
            List of stock ticker symbols to query.

        Returns
        -------
        list[MarketData]
            Standardized market data records. Empty list on failure.
        """
        ...

    def fetch_batch(
        self,
        tickers: list[str],
        batch_size: int = 50,
    ) -> list[MarketData]:
        """Batch fetch with automatic chunking.

        Default implementation splits tickers into batches and calls ``fetch``
        for each. Subclasses may override for more efficient batch APIs.

        Parameters
        ----------
        tickers:
            List of stock ticker symbols.
        batch_size:
            Max tickers per API call. Default 50.

        Returns
        -------
        list[MarketData]
            Combined results from all batches.
        """
        results: list[MarketData] = []
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            try:
                results.extend(self.fetch(batch))
            except Exception:
                logger.warning(
                    "Batch %d failed for source=%s, tickers=%s",
                    i // batch_size + 1,
                    self.source_name,
                    batch,
                    exc_info=True,
                )
        return results
