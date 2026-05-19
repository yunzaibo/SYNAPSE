"""EastMoneyAdapter -- 行情 + 资金流向 via 东方财富 HTTP API.

No authentication required. Public push API endpoints:
- Stock quotes: ``push2.eastmoney.com/api/qt/ulist.np/get``
- Capital flow klines: ``push2.eastmoney.com/api/qt/stock/fflow/kline/get``

Built-in rate limiting (min 1 s between requests) to respect API limits.

Part of P5 Real-time Data Source Integration.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from synapse.event.datasource import DataSource, MarketData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_QUOTE_URL = "http://push2.eastmoney.com/api/qt/ulist.np/get"
_CAPITAL_FLOW_URL = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"

_QUOTE_FIELDS = "f2,f3,f4,f12,f14,f15,f16,f17,f18"
_CAPITAL_FLOW_FIELDS = (
    "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
)

# Mapping of 东方财富 field codes to human-readable names
_QUOTE_FIELD_MAP: dict[str, str] = {
    "f2": "price",
    "f3": "change_pct",
    "f4": "change_amount",
    "f12": "code",
    "f14": "name",
    "f15": "high",
    "f16": "low",
    "f17": "open",
    "f18": "prev_close",
}

_CAPITAL_FLOW_FIELD_MAP: dict[str, str] = {
    # f51 = date, handled separately from the kline string.
    "f52": "main_net_inflow",
    "f53": "small_net_inflow",
    "f54": "medium_net_inflow",
    "f55": "large_net_inflow",
    "f56": "super_large_net_inflow",
    "f57": "main_net_inflow_pct",
    "f58": "small_net_inflow_pct",
    "f59": "medium_net_inflow_pct",
    "f60": "large_net_inflow_pct",
    "f61": "super_large_net_inflow_pct",
    "f62": "main_net_amount",
    "f63": "small_net_amount",
    "f64": "medium_net_amount",
    "f65": "large_net_amount",
}

_DEFAULT_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_market(ticker: str) -> str:
    """Return 东方财富 market prefix: ``'1'`` for SH (6xxx), ``'0'`` for SZ.

    Ticker format: bare code like ``'600519'`` or ``'000001'``.
    """
    return "1" if ticker.startswith("6") else "0"


def _to_secid(ticker: str) -> str:
    """Convert bare ticker to 东方财富 secid format ``'market.code'``."""
    return f"{_detect_market(ticker)}.{ticker}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert *value* to float, returning *default* on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class EastMoneyAdapter(DataSource):
    """DataSource adapter backed by 东方财富 HTTP push API.

    Covers two data dimensions:
    - **行情** (stock quotes) via ``/api/qt/ulist.np/get``
    - **资金流向** (capital flow klines) via ``/api/qt/stock/fflow/kline/get``

    Built-in rate limiting ensures at least *min_interval_sec* between
    consecutive HTTP requests. No authentication is needed.
    """

    # Sentinel: no request has been made yet.
    _NEVER: float = -1.0

    def __init__(self, *, min_interval_sec: float = 1.0, timeout: int = _DEFAULT_TIMEOUT):
        """
        Parameters
        ----------
        min_interval_sec:
            Minimum seconds between consecutive API requests.
        timeout:
            HTTP request timeout in seconds.
        """
        self._min_interval_sec = min_interval_sec
        self._timeout = timeout
        self._last_request_ts: float = self._NEVER

    @property
    def source_name(self) -> str:
        return "eastmoney"

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Sleep if needed to respect the minimum interval between requests."""
        now = time.monotonic()
        if self._last_request_ts != self._NEVER:
            elapsed = now - self._last_request_ts
            if elapsed < self._min_interval_sec:
                time.sleep(self._min_interval_sec - elapsed)
        self._last_request_ts = time.monotonic()

    # ------------------------------------------------------------------
    # fetch -- ABC entry point (quotes)
    # ------------------------------------------------------------------

    def fetch(self, tickers: list[str]) -> list[MarketData]:
        """Fetch stock quotes for *tickers*.

        Returns an empty list when tickers is empty or on API errors.
        """
        if not tickers:
            return []
        return self.fetch_quotes(tickers)

    # ------------------------------------------------------------------
    # Per-dimension fetchers
    # ------------------------------------------------------------------

    def fetch_quotes(self, tickers: list[str]) -> list[MarketData]:
        """Fetch real-time quotes for a list of tickers.

        Calls ``/api/qt/ulist.np/get`` with batched secids and parses
        the result into ``MarketData`` records with ``data_type='quote'``.
        """
        if not tickers:
            return []

        secids = ",".join(_to_secid(t) for t in tickers)
        params = {
            "fltt": 2,
            "invt": 2,
            "fields": _QUOTE_FIELDS,
            "secids": secids,
        }

        try:
            self._throttle()
            resp = requests.get(_QUOTE_URL, params=params, timeout=self._timeout)
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException:
            logger.warning("EastMoney quote request failed", exc_info=True)
            return []

        if body.get("rc", -1) != 0:
            logger.warning("EastMoney quote API returned rc=%s", body.get("rc"))
            return []

        data = body.get("data")
        if not data:
            return []

        diff = data.get("diff", [])
        if not diff:
            return []

        now = datetime.now(timezone.utc)
        results: list[MarketData] = []
        for item in diff:
            code = str(item.get("f12", ""))
            payload: dict[str, Any] = {}
            for raw_key, nice_key in _QUOTE_FIELD_MAP.items():
                payload[nice_key] = item.get(raw_key)
            # Also store raw fields for downstream flexibility
            payload["_raw"] = item

            results.append(
                MarketData(
                    ticker=code,
                    source=self.source_name,
                    timestamp=now,
                    data_type="quote",
                    payload=payload,
                )
            )
        return results

    def fetch_capital_flow(self, ticker: str) -> list[MarketData]:
        """Fetch daily capital-flow klines for *ticker*.

        Calls ``/api/qt/stock/fflow/kline/get`` and parses the klines
        into ``MarketData`` records with ``data_type='capital_flow'``.
        """
        secid = _to_secid(ticker)
        params = {
            "lmt": 1,
            "klt": 101,
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": _CAPITAL_FLOW_FIELDS,
        }

        try:
            self._throttle()
            resp = requests.get(_CAPITAL_FLOW_URL, params=params, timeout=self._timeout)
            resp.raise_for_status()
            body = resp.json()
        except requests.RequestException:
            logger.warning(
                "EastMoney capital flow request failed for %s", ticker, exc_info=True
            )
            return []

        if body.get("rc", -1) != 0:
            logger.warning(
                "EastMoney capital flow API returned rc=%s for %s",
                body.get("rc"),
                ticker,
            )
            return []

        data = body.get("data")
        if not data:
            return []

        klines = data.get("klines", [])
        if not klines:
            return []

        now = datetime.now(timezone.utc)
        results: list[MarketData] = []

        for kline_str in klines:
            parts = kline_str.split(",")
            # First element is date (f51), remaining are field values
            if len(parts) < 2:
                continue

            payload: dict[str, Any] = {"date": parts[0]}
            # Map field values to named keys: parts[1] -> f52, parts[2] -> f53, ...
            for idx, (_, nice_key) in enumerate(_CAPITAL_FLOW_FIELD_MAP.items()):
                val_idx = idx + 1  # +1 to skip date at parts[0]
                if val_idx < len(parts):
                    payload[nice_key] = parts[val_idx]

            results.append(
                MarketData(
                    ticker=ticker,
                    source=self.source_name,
                    timestamp=now,
                    data_type="capital_flow",
                    payload=payload,
                )
            )
        return results
