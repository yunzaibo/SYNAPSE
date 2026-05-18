"""China Market Semantics Layer.

ADR-005/006: China A-Shares market-specific semantics including:
- Trading calendar (holidays, trading days)
- T+1 settlement semantics
- Price limit semantics (涨跌停)
- Suspension semantics (停牌)
- Data loading for market data
"""

from synapse.core.market.calendar import (
    is_trading_day,
    next_trading_day,
    trading_days_between,
)
from synapse.core.market.semantics import (
    price_limit,
    is_suspended,
    validate_t1_settlement,
)
from synapse.core.market.data_loader import load_daily

__all__ = [
    "is_trading_day",
    "next_trading_day",
    "trading_days_between",
    "price_limit",
    "is_suspended",
    "validate_t1_settlement",
    "load_daily",
]
