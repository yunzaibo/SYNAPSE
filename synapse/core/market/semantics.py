"""Market Semantics — China A-Shares specific rules.

ADR-005/006: T+1 settlement, price limits, suspension handling.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from synapse.core.market.calendar import is_trading_day, next_trading_day


class SymbolType(str, Enum):
    """A-share symbol types with different price limits."""

    MAIN = "主板"        # SSE main board, SZSE main board: ±10%
    GEM = "创业板"       # ChiNext (创业板): ±20%
    STAR = "科创板"      # STAR Market (科创板): ±20%
    ST = "ST"            # Special Treatment: ±5%
    BSE = "北交所"       # Beijing Stock Exchange: ±30%


# Price limit percentages by symbol type
PRICE_LIMITS: dict[SymbolType, Decimal] = {
    SymbolType.MAIN: Decimal("0.10"),
    SymbolType.GEM: Decimal("0.20"),
    SymbolType.STAR: Decimal("0.20"),
    SymbolType.ST: Decimal("0.05"),
    SymbolType.BSE: Decimal("0.30"),
}


def price_limit(symbol_type: str | SymbolType) -> Decimal:
    """Get the price limit percentage for a symbol type.

    Args:
        symbol_type: The symbol type (主板, 创业板, 科创板, ST, 北交所).

    Returns:
        Price limit as a Decimal (e.g., 0.10 for 10%).

    Raises:
        ValueError: If symbol_type is not recognized.
    """
    if isinstance(symbol_type, str):
        try:
            symbol_type = SymbolType(symbol_type)
        except ValueError:
            valid_types = [s.value for s in SymbolType]
            raise ValueError(
                f"Unknown symbol type: {symbol_type!r}. "
                f"Valid types: {valid_types}"
            ) from None
    return PRICE_LIMITS[symbol_type]


def validate_t1_settlement(
    buy_date: date,
    sell_date: date,
) -> bool:
    """Validate T+1 settlement constraint.

    In China A-shares, stocks bought on day T can only be sold on day T+1 or later.
    The sell date must be at least one trading day after the buy date.

    Args:
        buy_date: The date the stock was bought.
        sell_date: The date the stock is sold.

    Returns:
        True if the sell date satisfies T+1 constraint.

    Raises:
        ValueError: If sell_date is before buy_date.
    """
    if sell_date < buy_date:
        raise ValueError(
            f"sell_date ({sell_date}) cannot be before buy_date ({buy_date})"
        )

    earliest_sell = next_trading_day(buy_date)
    return sell_date >= earliest_sell


def is_suspended(
    symbol: str,
    d: date,
    suspended_dates: Optional[set[date]] = None,
) -> bool:
    """Check if a symbol is suspended on a given date.

    P1: Accepts explicit suspended_dates set. Future versions may load
    from data source.

    Args:
        symbol: The stock symbol.
        d: The date to check.
        suspended_dates: Set of dates when the symbol is suspended.
            If None, returns False (no suspension data).

    Returns:
        True if the symbol is suspended on the given date.
    """
    if suspended_dates is None:
        return False
    return d in suspended_dates
