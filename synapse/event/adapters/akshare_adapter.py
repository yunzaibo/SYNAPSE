"""AkshareAdapter -- 龙虎榜 + 资金面 data via akshare library.

akshare is an OPTIONAL dependency. When not installed the adapter degrades
gracefully: fetch() returns an empty list and emits a warning log.

Data dimensions
---------------
- 龙虎榜 (dragon-tiger list): ``ak.stock_lhb_detail_em()``
- 资金面 (capital flow):       ``ak.stock_individual_fund_flow()``

Part of P5 Real-time Data Source Integration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from synapse.event.datasource import DataSource, MarketData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency -- akshare
# ---------------------------------------------------------------------------

try:
    import akshare as ak  # type: ignore[import-untyped]
except ImportError:
    ak = None  # type: ignore[assignment]
    logger.warning(
        "akshare is not installed -- AkshareAdapter will return empty results. "
        "Install with: pip install akshare"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, returning *default* on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_lhb_rows(df: "Any", ticker: str) -> list[MarketData]:
    """Convert a 龙虎榜 DataFrame into a list of MarketData records.

    Expected columns from ``ak.stock_lhb_detail_em()``:
        序号, 代码, 名称, 解读, 收盘价, 涨跌幅, 龙虎榜净买额,
        龙虎榜买入额, 龙虎榜卖出额, 龙虎榜成交额, 市场总成交额,
        净买额占总成交比, 成交额占总成交比, 换手率, 流通市值, 上榜原因
    """
    if df is None or df.empty:
        return []

    now = datetime.now(timezone.utc)
    results: list[MarketData] = []

    for _, row in df.iterrows():
        payload: dict[str, Any] = {}
        for col in df.columns:
            val = row[col]
            # Convert numpy types to plain Python
            if hasattr(val, "item"):
                val = val.item()
            payload[col] = val

        results.append(
            MarketData(
                ticker=ticker,
                source="akshare",
                timestamp=now,
                data_type="lhb",
                payload=payload,
            )
        )
    return results


def _parse_capital_flow_rows(df: "Any", ticker: str) -> list[MarketData]:
    """Convert a capital-flow DataFrame into a list of MarketData records.

    Expected columns from ``ak.stock_individual_fund_flow()``:
        日期, 收盘价, 涨跌幅, 主力净流入-净额, 主力净流入-净占比,
        超大单净流入-净额, 超大单净流入-净占比, 大单净流入-净额,
        大单净流入-净占比, 中单净流入-净额, 中单净流入-净占比,
        小单净流入-净额, 小单净流入-净占比
    """
    if df is None or df.empty:
        return []

    now = datetime.now(timezone.utc)
    results: list[MarketData] = []

    for _, row in df.iterrows():
        payload: dict[str, Any] = {}
        for col in df.columns:
            val = row[col]
            if hasattr(val, "item"):
                val = val.item()
            # Convert Timestamp to ISO string
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            payload[col] = val

        results.append(
            MarketData(
                ticker=ticker,
                source="akshare",
                timestamp=now,
                data_type="capital_flow",
                payload=payload,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AkshareAdapter(DataSource):
    """DataSource adapter backed by the akshare library.

    Covers two data dimensions:
    - **龙虎榜** (dragon-tiger list) via ``ak.stock_lhb_detail_em()``
    - **资金面** (individual capital flow) via ``ak.stock_individual_fund_flow()``

    When akshare is not installed all public methods return empty results and
    log a warning -- the adapter never raises ``ImportError`` at runtime.
    """

    @property
    def source_name(self) -> str:
        return "akshare"

    # ------------------------------------------------------------------
    # fetch -- unified entry point
    # ------------------------------------------------------------------

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        """Fetch both 龙虎榜 and 资金面 for *tickers*.

        Returns an empty list when akshare is unavailable or on API errors.
        """
        if ak is None:
            logger.warning("akshare unavailable, returning empty results")
            return []

        results: list[MarketData] = []
        for ticker in tickers:
            results.extend(self.fetch_lhb(ticker))
            results.extend(self.fetch_capital_flow(ticker))
        return results

    # ------------------------------------------------------------------
    # Per-dimension fetchers
    # ------------------------------------------------------------------

    def fetch_lhb(self, ticker: str) -> list[MarketData]:
        """Fetch 龙虎榜 (dragon-tiger list) detail for *ticker*.

        Calls ``ak.stock_lhb_detail_em()`` and parses the result into
        standardised ``MarketData`` records with ``data_type="lhb"``.
        """
        if ak is None:
            return []

        try:
            df = ak.stock_lhb_detail_em(symbol=ticker)
            return _parse_lhb_rows(df, ticker)
        except Exception:
            logger.warning(
                "Failed to fetch LHB for %s", ticker, exc_info=True
            )
            return []

    def fetch_capital_flow(self, ticker: str) -> list[MarketData]:
        """Fetch 个股资金流向 (individual capital flow) for *ticker*.

        Calls ``ak.stock_individual_fund_flow()`` and parses the result into
        standardised ``MarketData`` records with ``data_type="capital_flow"``.
        """
        if ak is None:
            return []

        try:
            df = ak.stock_individual_fund_flow(stock=ticker, market="sh" if ticker.startswith("6") else "sz")
            return _parse_capital_flow_rows(df, ticker)
        except Exception:
            logger.warning(
                "Failed to fetch capital flow for %s", ticker, exc_info=True
            )
            return []
