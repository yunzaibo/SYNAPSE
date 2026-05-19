"""Tests for DataSource adapter protocol."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from synapse.event.datasource import DataSource, MarketData


# ---------------------------------------------------------------------------
# MarketData schema tests
# ---------------------------------------------------------------------------


class TestMarketData:
    """MarketData dataclass validation."""

    def test_create_minimal(self):
        md = MarketData(
            ticker="600519",
            source="eastmoney",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            data_type="quote",
        )
        assert md.ticker == "600519"
        assert md.source == "eastmoney"
        assert md.payload == {}

    def test_create_with_payload(self):
        payload = {"price": 1800.0, "volume": 12345}
        md = MarketData(
            ticker="600519",
            source="eastmoney",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            data_type="quote",
            payload=payload,
        )
        assert md.payload == payload

    def test_from_dict_like(self):
        """Simulate constructing from API response dict."""
        data = {
            "ticker": "000001",
            "source": "akshare",
            "timestamp": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "data_type": "lhb",
            "payload": {"net_buy": 5000},
        }
        md = MarketData(**data)
        assert md.ticker == "000001"
        assert md.data_type == "lhb"


# ---------------------------------------------------------------------------
# DataSource ABC tests
# ---------------------------------------------------------------------------


class ConcreteAdapter(DataSource):
    """Minimal concrete implementation for ABC testing."""

    @property
    def source_name(self) -> str:
        return "test_source"

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return [
            MarketData(ticker=t, source=self.source_name, timestamp=ts, data_type="quote")
            for t in tickers
        ]


class FailingAdapter(DataSource):
    """Adapter that raises on fetch for error handling tests."""

    @property
    def source_name(self) -> str:
        return "failing_source"

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        raise ConnectionError("Network error")


class TestDataSourceABC:
    """DataSource ABC contract tests."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataSource()  # type: ignore[abstract]

    def test_concrete_adapter_source_name(self):
        adapter = ConcreteAdapter()
        assert adapter.source_name == "test_source"

    def test_concrete_adapter_fetch(self):
        adapter = ConcreteAdapter()
        results = adapter.fetch(["600519", "000001"])
        assert len(results) == 2
        assert results[0].ticker == "600519"
        assert results[1].ticker == "000001"
        assert all(r.source == "test_source" for r in results)

    def test_fetch_empty_list(self):
        adapter = ConcreteAdapter()
        results = adapter.fetch([])
        assert results == []

    def test_fetch_batch_default_chunking(self):
        adapter = ConcreteAdapter()
        tickers = [f"{i:06d}" for i in range(120)]
        results = adapter.fetch_batch(tickers, batch_size=50)
        assert len(results) == 120

    def test_fetch_batch_with_failure(self):
        adapter = FailingAdapter()
        # Should not raise — failures are logged and skipped
        results = adapter.fetch_batch(["600519", "000001"])
        assert results == []

    def test_subclass_must_implement_fetch(self):
        """Subclass without fetch should fail instantiation."""
        class Incomplete(DataSource):
            @property
            def source_name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_source_name(self):
        """Subclass without source_name should fail instantiation."""
        class Incomplete(DataSource):
            def fetch(self, tickers: list[str]) -> list[MarketData]:
                return []

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]
