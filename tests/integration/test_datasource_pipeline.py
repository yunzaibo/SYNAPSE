"""Integration tests for DataSource → StreamingIngestion pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from synapse.event.adapters import adapter_fetch_fn
from synapse.event.datasource import DataSource, MarketData
from synapse.event.streaming import PollingSource, StreamBuffer, StreamingIngestion


# ---------------------------------------------------------------------------
# Test adapter (mock)
# ---------------------------------------------------------------------------


class MockAdapter(DataSource):
    """Test adapter returning predictable data."""

    @property
    def source_name(self) -> str:
        return "mock_source"

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        ts = datetime(2026, 5, 19, tzinfo=timezone.utc)
        return [
            MarketData(
                ticker=t,
                source=self.source_name,
                timestamp=ts,
                data_type="quote",
                payload={"price": 100.0 + i, "volume": 1000 * (i + 1)},
            )
            for i, t in enumerate(tickers)
        ]


# ---------------------------------------------------------------------------
# adapter_fetch_fn tests
# ---------------------------------------------------------------------------


class TestAdapterFetchFn:
    """adapter_fetch_fn integration with StreamingIngestion."""

    def test_factory_returns_callable(self):
        fn = adapter_fetch_fn(MockAdapter())
        assert callable(fn)

    def test_fetch_fn_reads_tickers_from_params(self):
        fn = adapter_fetch_fn(MockAdapter())
        source = PollingSource(
            source_id="test",
            name="test",
            params={"tickers": "600519,000001"},
        )
        results = fn(source)
        assert len(results) == 2
        assert results[0]["ticker"] == "600519"
        assert results[1]["ticker"] == "000001"

    def test_fetch_fn_returns_dicts(self):
        fn = adapter_fetch_fn(MockAdapter())
        source = PollingSource(source_id="test", name="test", params={"tickers": "600519"})
        results = fn(source)
        assert isinstance(results[0], dict)
        assert "ticker" in results[0]
        assert "payload" in results[0]

    def test_fetch_fn_empty_tickers_returns_empty(self):
        fn = adapter_fetch_fn(MockAdapter())
        source = PollingSource(source_id="test", name="test", params={})
        results = fn(source)
        assert results == []

    def test_fetch_fn_exception_returns_empty(self):
        class FailingAdapter(DataSource):
            @property
            def source_name(self) -> str:
                return "fail"

            def fetch(self, tickers: list[str]) -> list[MarketData]:
                raise ConnectionError("network error")

        fn = adapter_fetch_fn(FailingAdapter())
        source = PollingSource(source_id="test", name="test", params={"tickers": "600519"})
        results = fn(source)
        assert results == []


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------


class TestDataSourcePipeline:
    """DataSource → StreamingIngestion end-to-end integration."""

    def test_poll_once_with_adapter(self):
        ingestion = StreamingIngestion(buffer_size=100)
        ingestion.set_fetch_fn(adapter_fetch_fn(MockAdapter()))
        ingestion.register_source(PollingSource(
            source_id="mock",
            name="mock_quotes",
            params={"tickers": "600519,000001"},
        ))
        count = ingestion.poll_once()
        assert count == 2
        assert ingestion.buffer.size == 2

    def test_buffer_receives_data(self):
        ingestion = StreamingIngestion(buffer_size=100)
        ingestion.set_fetch_fn(adapter_fetch_fn(MockAdapter()))
        ingestion.register_source(PollingSource(
            source_id="mock",
            name="mock_quotes",
            params={"tickers": "600519"},
        ))
        ingestion.poll_once()
        assert ingestion.buffer.size == 1

    def test_multiple_polls_accumulate(self):
        ingestion = StreamingIngestion(buffer_size=100)
        ingestion.set_fetch_fn(adapter_fetch_fn(MockAdapter()))
        ingestion.register_source(PollingSource(
            source_id="mock",
            name="mock_quotes",
            params={"tickers": "600519"},
        ))
        ingestion.poll_once()
        ingestion.poll_once()
        assert ingestion.buffer.size == 2

    def test_poll_returns_payload_dicts(self):
        ingestion = StreamingIngestion(buffer_size=100)
        ingestion.set_fetch_fn(adapter_fetch_fn(MockAdapter()))
        ingestion.register_source(PollingSource(
            source_id="mock",
            name="mock_quotes",
            params={"tickers": "600519"},
        ))
        ingestion.poll_once()
        items = ingestion.buffer.peek(1)
        assert items[0]["payload"]["price"] == 100.0
