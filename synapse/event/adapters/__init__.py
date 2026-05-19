"""Data Source Adapters -- Pluggable market data providers.

Each adapter implements the DataSource ABC from synapse.event.datasource.
Optional dependencies are handled via try/except ImportError patterns.
"""

from __future__ import annotations

import logging
from typing import Any

from synapse.event.datasource import DataSource, MarketData
from synapse.event.streaming import PollingSource

logger = logging.getLogger(__name__)


def adapter_fetch_fn(adapter: DataSource):
    """Create a fetch_fn compatible with StreamingIngestion.set_fetch_fn().

    Wraps a DataSource adapter so it can be used as the fetch function
    in a polling-based streaming pipeline.

    Parameters
    ----------
    adapter:
        Any DataSource subclass instance (EastMoneyAdapter, AkshareAdapter, etc.).

    Returns
    -------
    Callable[[PollingSource], list[dict]]
        A function that fetches data from the adapter and returns it as
        a list of dicts (MarketData.payload).

    Example::

        from synapse.event.adapters import EastMoneyAdapter, adapter_fetch_fn
        from synapse.event.streaming import StreamingIngestion, PollingSource

        adapter = EastMoneyAdapter()
        ingestion = StreamingIngestion()
        ingestion.set_fetch_fn(adapter_fetch_fn(adapter))
        ingestion.register_source(PollingSource(
            source_id="eastmoney",
            name="eastmoney_quotes",
            poll_interval_sec=60,
        ))
    """

    def _fetch(source: PollingSource) -> list[dict[str, Any]]:
        """Fetch from adapter, return list of payload dicts."""
        try:
            # Extract tickers from source params (comma-separated)
            tickers_str = source.params.get("tickers", "")
            tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
            if not tickers:
                logger.warning("No tickers configured for source=%s", source.source_id)
                return []

            data = adapter.fetch(tickers)
            return [
                {
                    "ticker": d.ticker,
                    "source": d.source,
                    "timestamp": d.timestamp.isoformat(),
                    "data_type": d.data_type,
                    "payload": d.payload,
                }
                for d in data
            ]
        except Exception:
            logger.error("Fetch failed for source=%s", source.source_id, exc_info=True)
            return []

    return _fetch
