"""Security Identity — Composite Identity for financial securities.

ADR-007: Composite Security Identity format: {market}.{exchange}.{ticker}
Stable identity that survives ticker changes, ST renames, delistings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityIdentity:
    """Immutable composite security identifier.

    Format: {market}.{exchange}.{ticker}
    Examples:
        cn.sh.600519   — 贵州茅台（上海）
        cn.sz.000858   — 五粮液（深圳）
    """

    market: str
    exchange: str
    ticker: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "market", self.market.split("_")[0].lower())
        object.__setattr__(self, "exchange", self.exchange.lower())
        object.__setattr__(self, "ticker", self.ticker)

    @property
    def security_id(self) -> str:
        """Global unique stable identifier."""
        return f"{self.market}.{self.exchange}.{self.ticker}"

    @classmethod
    def from_ticker(cls, market: str, exchange: str, ticker: str) -> SecurityIdentity:
        """Factory method for creating SecurityIdentity from components."""
        return cls(market=market, exchange=exchange, ticker=ticker)

    @classmethod
    def from_string(cls, security_id: str) -> SecurityIdentity:
        """Parse a security_id string like 'cn.sh.600519'."""
        parts = security_id.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid security_id format: {security_id!r}. "
                "Expected: <market>.<exchange>.<ticker>"
            )
        market, exchange, ticker = parts
        return cls(market=market, exchange=exchange, ticker=ticker)

    def __str__(self) -> str:
        return self.security_id
