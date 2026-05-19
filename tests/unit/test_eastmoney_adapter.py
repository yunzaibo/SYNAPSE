"""Tests for EastMoneyAdapter -- 东方财富 行情 + 资金流向 adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from synapse.event.adapters.eastmoney import (
    EastMoneyAdapter,
    _detect_market,
    _to_secid,
)
from synapse.event.datasource import MarketData


# ---------------------------------------------------------------------------
# Helpers -- fake API responses
# ---------------------------------------------------------------------------


def _make_quote_response(items: list[dict] | None = None) -> dict:
    """Build a fake quote API response body."""
    return {
        "rc": 0,
        "rt": 4,
        "svr": 181669276,
        "lt": 1,
        "full": 1,
        "data": {
            "total": len(items) if items else 0,
            "diff": items or [],
        },
    }


def _make_capital_flow_response(klines: list[str] | None = None) -> dict:
    """Build a fake capital-flow kline API response body."""
    return {
        "rc": 0,
        "data": {
            "klines": klines or [],
        },
    }


SAMPLE_QUOTE_ITEM = {
    "f2": 1800.0,
    "f3": 1.5,
    "f4": 26.5,
    "f12": "600519",
    "f14": "贵州茅台",
    "f15": 1810.0,
    "f16": 1773.5,
    "f17": 1780.0,
    "f18": 1773.5,
}

SAMPLE_QUOTE_ITEM_SZ = {
    "f2": 15.30,
    "f3": -0.5,
    "f4": -0.08,
    "f12": "000001",
    "f14": "平安银行",
    "f15": 15.50,
    "f16": 15.10,
    "f17": 15.40,
    "f18": 15.38,
}

SAMPLE_KLINE = "2026-05-19,1234567.00,2345678.00,3456789.00,4567890.00,5678901.00"


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


class TestHelpers:
    """Test pure helper functions without HTTP calls."""

    def test_detect_market_sh(self):
        assert _detect_market("600519") == "1"
        assert _detect_market("601318") == "1"
        assert _detect_market("688001") == "1"

    def test_detect_market_sz(self):
        assert _detect_market("000001") == "0"
        assert _detect_market("002594") == "0"
        assert _detect_market("300750") == "0"

    def test_to_secid_sh(self):
        assert _to_secid("600519") == "1.600519"

    def test_to_secid_sz(self):
        assert _to_secid("000001") == "0.000001"


# ---------------------------------------------------------------------------
# Adapter instantiation
# ---------------------------------------------------------------------------


class TestEastMoneyAdapterInit:
    """Verify adapter construction and ABC compliance."""

    def test_source_name(self):
        adapter = EastMoneyAdapter()
        assert adapter.source_name == "eastmoney"

    def test_default_rate_limit(self):
        adapter = EastMoneyAdapter()
        assert adapter._min_interval_sec == 1.0

    def test_custom_rate_limit(self):
        adapter = EastMoneyAdapter(min_interval_sec=0.5)
        assert adapter._min_interval_sec == 0.5

    def test_is_datasource_subclass(self):
        from synapse.event.datasource import DataSource

        adapter = EastMoneyAdapter()
        assert isinstance(adapter, DataSource)


# ---------------------------------------------------------------------------
# fetch() / fetch_quotes() -- happy path
# ---------------------------------------------------------------------------


class TestFetchQuotes:
    """Test quote fetching with mocked HTTP."""

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_returns_market_data_list(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])

        assert len(results) == 1
        md = results[0]
        assert isinstance(md, MarketData)
        assert md.ticker == "600519"
        assert md.source == "eastmoney"
        assert md.data_type == "quote"
        assert isinstance(md.timestamp, datetime)

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_quotes_parses_fields(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])

        payload = results[0].payload
        assert payload["price"] == 1800.0
        assert payload["change_pct"] == 1.5
        assert payload["change_amount"] == 26.5
        assert payload["code"] == "600519"
        assert payload["name"] == "贵州茅台"
        assert payload["high"] == 1810.0
        assert payload["low"] == 1773.5
        assert payload["open"] == 1780.0
        assert payload["prev_close"] == 1773.5
        assert "_raw" in payload

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_multiple_tickers(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response(
            [SAMPLE_QUOTE_ITEM, SAMPLE_QUOTE_ITEM_SZ]
        )
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519", "000001"])

        assert len(results) == 2
        tickers = {r.ticker for r in results}
        assert tickers == {"600519", "000001"}

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_calls_correct_url(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        adapter.fetch(["600519"])

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "push2.eastmoney.com" in call_args[0][0]
        assert "secids" in call_args[1]["params"]
        assert call_args[1]["params"]["secids"] == "1.600519"

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_sh_ticker_secid_format(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        adapter.fetch(["600519"])

        params = mock_get.call_args[1]["params"]
        assert params["secids"] == "1.600519"
        assert params["fltt"] == 2
        assert params["invt"] == 2

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_sz_ticker_secid_format(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM_SZ])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        adapter.fetch(["000001"])

        params = mock_get.call_args[1]["params"]
        assert params["secids"] == "0.000001"


# ---------------------------------------------------------------------------
# fetch() -- edge cases
# ---------------------------------------------------------------------------


class TestFetchQuotesEdgeCases:
    """Test quote fetching edge cases."""

    def test_fetch_empty_tickers(self):
        adapter = EastMoneyAdapter()
        results = adapter.fetch([])
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_api_error_rc_nonzero(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"rc": 1, "data": None}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_api_error_no_data(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"rc": 0, "data": None}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_api_error_empty_diff(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"rc": 0, "data": {"diff": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_network_exception(self, mock_get: MagicMock):
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_http_error(self, mock_get: MagicMock):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch(["600519"])
        assert results == []


# ---------------------------------------------------------------------------
# fetch_capital_flow()
# ---------------------------------------------------------------------------


class TestFetchCapitalFlow:
    """Test capital-flow kline fetching with mocked HTTP."""

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_returns_market_data(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_capital_flow_response([SAMPLE_KLINE])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch_capital_flow("600519")

        assert len(results) == 1
        md = results[0]
        assert isinstance(md, MarketData)
        assert md.ticker == "600519"
        assert md.source == "eastmoney"
        assert md.data_type == "capital_flow"

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_parses_kline(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_capital_flow_response([SAMPLE_KLINE])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch_capital_flow("600519")

        payload = results[0].payload
        assert payload["date"] == "2026-05-19"
        assert payload["main_net_inflow"] == "1234567.00"
        assert payload["small_net_inflow"] == "2345678.00"
        assert payload["medium_net_inflow"] == "3456789.00"
        assert payload["large_net_inflow"] == "4567890.00"
        assert payload["super_large_net_inflow"] == "5678901.00"

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_calls_correct_url(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_capital_flow_response([SAMPLE_KLINE])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        adapter.fetch_capital_flow("000001")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "fflow/kline" in call_args[0][0]
        assert call_args[1]["params"]["secid"] == "0.000001"
        assert call_args[1]["params"]["klt"] == 101
        assert call_args[1]["params"]["lmt"] == 1

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_empty_klines(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_capital_flow_response([])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch_capital_flow("600519")
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_api_error(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"rc": -1, "data": None}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        results = adapter.fetch_capital_flow("600519")
        assert results == []

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_capital_flow_network_error(self, mock_get: MagicMock):
        import requests

        mock_get.side_effect = requests.ConnectionError("timeout")

        adapter = EastMoneyAdapter()
        results = adapter.fetch_capital_flow("600519")
        assert results == []


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Test built-in rate limiting behavior."""

    @patch("synapse.event.adapters.eastmoney.time.sleep")
    @patch("synapse.event.adapters.eastmoney.time.monotonic")
    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_throttle_sleeps_when_too_fast(
        self, mock_get: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Simulate: first call at t=0, second call at t=0.3 (less than 1.0)
        mock_monotonic.side_effect = [0.0, 0.0, 0.3, 0.3]

        adapter = EastMoneyAdapter(min_interval_sec=1.0)
        adapter.fetch(["600519"])
        adapter.fetch(["000001"])

        # Should have slept for 0.7 seconds (1.0 - 0.3)
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert abs(sleep_arg - 0.7) < 0.01

    @patch("synapse.event.adapters.eastmoney.time.sleep")
    @patch("synapse.event.adapters.eastmoney.time.monotonic")
    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_throttle_no_sleep_when_enough_time(
        self, mock_get: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Simulate: first call at t=0, second call at t=1.5 (more than 1.0)
        mock_monotonic.side_effect = [0.0, 0.0, 1.5, 1.5]

        adapter = EastMoneyAdapter(min_interval_sec=1.0)
        adapter.fetch(["600519"])
        adapter.fetch(["000001"])

        mock_sleep.assert_not_called()

    @patch("synapse.event.adapters.eastmoney.time.sleep")
    @patch("synapse.event.adapters.eastmoney.time.monotonic")
    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_rate_limit_between_quote_and_capital_flow(
        self, mock_get: MagicMock, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_quote_response([SAMPLE_QUOTE_ITEM])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Simulate: quote at t=0, capital flow at t=0.2
        mock_monotonic.side_effect = [0.0, 0.0, 0.2, 0.2]

        adapter = EastMoneyAdapter(min_interval_sec=1.0)
        adapter.fetch(["600519"])
        adapter.fetch_capital_flow("600519")

        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert abs(sleep_arg - 0.8) < 0.01


# ---------------------------------------------------------------------------
# fetch_batch integration
# ---------------------------------------------------------------------------


class TestFetchBatch:
    """Test inherited fetch_batch with EastMoneyAdapter."""

    @patch("synapse.event.adapters.eastmoney.requests.get")
    def test_fetch_batch_calls_fetch_per_batch(self, mock_get: MagicMock):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        items = [
            {"f2": float(i), "f3": 0.0, "f4": 0.0, "f12": f"{i:06d}", "f14": f"stock{i}"}
            for i in range(120)
        ]
        mock_resp.json.return_value = _make_quote_response(items)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        adapter = EastMoneyAdapter()
        tickers = [f"{i:06d}" for i in range(120)]
        results = adapter.fetch_batch(tickers, batch_size=50)

        # fetch_batch calls fetch() for each batch; all items from the mock
        # should be collected
        assert len(results) > 0
        assert mock_get.call_count == 3  # ceil(120/50) = 3 batches
