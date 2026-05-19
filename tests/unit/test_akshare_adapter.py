"""Tests for AkshareAdapter -- 龙虎榜 + 资金面 data adapter.

Covers:
- source_name property
- fetch_lhb parsing
- fetch_capital_flow parsing
- fetch (combined) returns both dimensions
- graceful degradation when akshare is not installed
- API error handling (exceptions from akshare)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from synapse.event.adapters.akshare_adapter import (
    AkshareAdapter,
    _parse_capital_flow_rows,
    _parse_lhb_rows,
    _safe_float,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_lhb_df() -> pd.DataFrame:
    """Return a minimal 龙虎榜 DataFrame matching akshare output shape."""
    return pd.DataFrame(
        {
            "代码": ["600519"],
            "名称": ["贵州茅台"],
            "收盘价": [1800.0],
            "涨跌幅": [2.5],
            "龙虎榜净买额": [50000000.0],
            "龙虎榜买入额": [80000000.0],
            "龙虎榜卖出额": [30000000.0],
            "上榜原因": ["日涨幅偏离值达7%"],
        }
    )


def _make_capital_flow_df() -> pd.DataFrame:
    """Return a minimal capital-flow DataFrame matching akshare output shape."""
    return pd.DataFrame(
        {
            "日期": ["2026-01-15", "2026-01-16"],
            "收盘价": [1800.0, 1810.0],
            "涨跌幅": [2.5, 0.56],
            "主力净流入-净额": [50000000.0, -10000000.0],
            "主力净流入-净占比": [5.2, -1.1],
            "超大单净流入-净额": [30000000.0, -5000000.0],
            "大单净流入-净额": [20000000.0, -5000000.0],
            "中单净流入-净额": [-10000000.0, 3000000.0],
            "小单净流入-净额": [-5000000.0, 2000000.0],
        }
    )


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------


class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float(3.14) == 3.14

    def test_string_number(self):
        assert _safe_float("42") == 42.0

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_none_returns_custom_default(self):
        assert _safe_float(None, -1.0) == -1.0

    def test_invalid_string_returns_default(self):
        assert _safe_float("abc") == 0.0


# ---------------------------------------------------------------------------
# _parse_lhb_rows
# ---------------------------------------------------------------------------


class TestParseLhbRows:
    def test_empty_df(self):
        empty = pd.DataFrame()
        assert _parse_lhb_rows(empty, "600519") == []

    def test_none_df(self):
        assert _parse_lhb_rows(None, "600519") == []  # type: ignore[arg-type]

    def test_single_row(self):
        df = _make_lhb_df()
        results = _parse_lhb_rows(df, "600519")
        assert len(results) == 1
        md = results[0]
        assert md.ticker == "600519"
        assert md.source == "akshare"
        assert md.data_type == "lhb"
        assert md.payload["代码"] == "600519"
        assert md.payload["龙虎榜净买额"] == 50000000.0
        assert isinstance(md.timestamp, datetime)

    def test_multiple_rows(self):
        df = pd.DataFrame(
            {
                "代码": ["600519", "600519"],
                "名称": ["贵州茅台", "贵州茅台"],
                "收盘价": [1800.0, 1805.0],
                "涨跌幅": [2.5, 0.28],
                "龙虎榜净买额": [50000000.0, -10000000.0],
                "上榜原因": ["日涨幅偏离值达7%", "日换手率达20%"],
            }
        )
        results = _parse_lhb_rows(df, "600519")
        assert len(results) == 2
        assert results[0].payload["收盘价"] == 1800.0
        assert results[1].payload["收盘价"] == 1805.0


# ---------------------------------------------------------------------------
# _parse_capital_flow_rows
# ---------------------------------------------------------------------------


class TestParseCapitalFlowRows:
    def test_empty_df(self):
        empty = pd.DataFrame()
        assert _parse_capital_flow_rows(empty, "600519") == []

    def test_none_df(self):
        assert _parse_capital_flow_rows(None, "600519") == []  # type: ignore[arg-type]

    def test_multiple_rows(self):
        df = _make_capital_flow_df()
        results = _parse_capital_flow_rows(df, "600519")
        assert len(results) == 2
        md = results[0]
        assert md.ticker == "600519"
        assert md.source == "akshare"
        assert md.data_type == "capital_flow"
        assert md.payload["主力净流入-净额"] == 50000000.0
        # Date should be converted to ISO string
        assert isinstance(md.payload["日期"], str)


# ---------------------------------------------------------------------------
# AkshareAdapter -- source_name
# ---------------------------------------------------------------------------


class TestAkshareAdapterSourceName:
    def test_source_name(self):
        adapter = AkshareAdapter()
        assert adapter.source_name == "akshare"


# ---------------------------------------------------------------------------
# AkshareAdapter -- fetch_lhb
# ---------------------------------------------------------------------------


class TestAkshareAdapterFetchLhb:
    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_success(self, mock_ak: MagicMock):
        mock_ak.stock_lhb_detail_em.return_value = _make_lhb_df()
        adapter = AkshareAdapter()
        results = adapter.fetch_lhb("600519")
        assert len(results) == 1
        assert results[0].data_type == "lhb"
        mock_ak.stock_lhb_detail_em.assert_called_once_with(symbol="600519")

    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_api_exception_returns_empty(self, mock_ak: MagicMock):
        mock_ak.stock_lhb_detail_em.side_effect = RuntimeError("API error")
        adapter = AkshareAdapter()
        results = adapter.fetch_lhb("600519")
        assert results == []

    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_none_response(self, mock_ak: MagicMock):
        mock_ak.stock_lhb_detail_em.return_value = None
        adapter = AkshareAdapter()
        results = adapter.fetch_lhb("600519")
        assert results == []


# ---------------------------------------------------------------------------
# AkshareAdapter -- fetch_capital_flow
# ---------------------------------------------------------------------------


class TestAkshareAdapterFetchCapitalFlow:
    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_success_shares(self, mock_ak: MagicMock):
        mock_ak.stock_individual_fund_flow.return_value = _make_capital_flow_df()
        adapter = AkshareAdapter()
        results = adapter.fetch_capital_flow("600519")
        assert len(results) == 2
        assert results[0].data_type == "capital_flow"
        mock_ak.stock_individual_fund_flow.assert_called_once_with(
            stock="600519", market="sh"
        )

    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_success_sz_ticker(self, mock_ak: MagicMock):
        mock_ak.stock_individual_fund_flow.return_value = _make_capital_flow_df()
        adapter = AkshareAdapter()
        adapter.fetch_capital_flow("000001")
        mock_ak.stock_individual_fund_flow.assert_called_once_with(
            stock="000001", market="sz"
        )

    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_api_exception_returns_empty(self, mock_ak: MagicMock):
        mock_ak.stock_individual_fund_flow.side_effect = RuntimeError("timeout")
        adapter = AkshareAdapter()
        results = adapter.fetch_capital_flow("600519")
        assert results == []


# ---------------------------------------------------------------------------
# AkshareAdapter -- fetch (combined)
# ---------------------------------------------------------------------------


class TestAkshareAdapterFetch:
    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_combined_fetch(self, mock_ak: MagicMock):
        mock_ak.stock_lhb_detail_em.return_value = _make_lhb_df()
        mock_ak.stock_individual_fund_flow.return_value = _make_capital_flow_df()
        adapter = AkshareAdapter()
        results = adapter.fetch(["600519"])
        # 1 lhb + 2 capital_flow rows = 3
        assert len(results) == 3
        types = {r.data_type for r in results}
        assert types == {"lhb", "capital_flow"}

    def test_fetch_empty_tickers(self):
        adapter = AkshareAdapter()
        assert adapter.fetch([]) == []

    @patch("synapse.event.adapters.akshare_adapter.ak")
    def test_fetch_multiple_tickers(self, mock_ak: MagicMock):
        mock_ak.stock_lhb_detail_em.return_value = _make_lhb_df()
        mock_ak.stock_individual_fund_flow.return_value = _make_capital_flow_df()
        adapter = AkshareAdapter()
        results = adapter.fetch(["600519", "000001"])
        assert mock_ak.stock_lhb_detail_em.call_count == 2
        assert mock_ak.stock_individual_fund_flow.call_count == 2


# ---------------------------------------------------------------------------
# Graceful degradation -- akshare not installed
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Verify the adapter works when akshare import fails."""

    def test_fetch_returns_empty_when_ak_none(self):
        """Simulate akshare not installed by setting ak = None."""
        import synapse.event.adapters.akshare_adapter as mod

        original_ak = mod.ak
        try:
            mod.ak = None
            adapter = AkshareAdapter()
            results = adapter.fetch(["600519"])
            assert results == []
        finally:
            mod.ak = original_ak

    def test_fetch_lhb_returns_empty_when_ak_none(self):
        import synapse.event.adapters.akshare_adapter as mod

        original_ak = mod.ak
        try:
            mod.ak = None
            adapter = AkshareAdapter()
            assert adapter.fetch_lhb("600519") == []
        finally:
            mod.ak = original_ak

    def test_fetch_capital_flow_returns_empty_when_ak_none(self):
        import synapse.event.adapters.akshare_adapter as mod

        original_ak = mod.ak
        try:
            mod.ak = None
            adapter = AkshareAdapter()
            assert adapter.fetch_capital_flow("600519") == []
        finally:
            mod.ak = original_ak

    def test_source_name_still_works_when_ak_none(self):
        import synapse.event.adapters.akshare_adapter as mod

        original_ak = mod.ak
        try:
            mod.ak = None
            adapter = AkshareAdapter()
            assert adapter.source_name == "akshare"
        finally:
            mod.ak = original_ak
