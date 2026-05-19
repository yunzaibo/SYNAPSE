"""China Market Semantics Layer.

ADR-005/006: China A-Shares market-specific semantics including:
- Trading calendar (holidays, trading days, sessions)
- T+1 settlement semantics
- Price limit semantics (涨跌停)
- Suspension semantics (停牌)
- Ex-right adjustment (复权)
- Northbound flow (北向资金)
- Index constituent (指数成分)
- Data loading for market data
"""

from synapse.core.market.calendar import (
    is_trading_day,
    next_trading_day,
    trading_days_between,
    TradingSession,
    TradingCalendar,
    add_trading_days,
    trading_day_offset,
    is_trading_session,
    trading_sessions_between,
    load_holidays,
    refresh_calendar,
)
from synapse.core.market.semantics import (
    price_limit,
    is_suspended,
    validate_t1_settlement,
)
from synapse.core.market.data_loader import load_daily
from synapse.core.market.adjustment import (
    AdjustmentType,
    AdjustmentEvent,
    AdjustmentFactors,
    get_adjustment_factors,
    adjust_prices,
    adjust_single_price,
)
from synapse.core.market.northbound import (
    NorthChannel,
    NorthboundFlow,
    load_northbound_flow,
    fetch_northbound_flow,
    northbound_momentum,
    northbound_to_signals,
    index_change_to_signals,
)
from synapse.core.market.constituent import (
    IndexCode,
    ConstituentSnapshot,
    ConstituentChange,
    load_constituents,
    load_constituent_changes,
    is_member,
    constituent_tickers,
)

__all__ = [
    # Calendar
    "is_trading_day",
    "next_trading_day",
    "trading_days_between",
    "TradingSession",
    "TradingCalendar",
    "add_trading_days",
    "trading_day_offset",
    "is_trading_session",
    "trading_sessions_between",
    "load_holidays",
    "refresh_calendar",
    # Semantics
    "price_limit",
    "is_suspended",
    "validate_t1_settlement",
    # Data loader
    "load_daily",
    # Adjustment
    "AdjustmentType",
    "AdjustmentEvent",
    "AdjustmentFactors",
    "get_adjustment_factors",
    "adjust_prices",
    "adjust_single_price",
    # Northbound
    "NorthChannel",
    "NorthboundFlow",
    "load_northbound_flow",
    "fetch_northbound_flow",
    "northbound_momentum",
    "northbound_to_signals",
    "index_change_to_signals",
    # Constituent
    "IndexCode",
    "ConstituentSnapshot",
    "ConstituentChange",
    "load_constituents",
    "load_constituent_changes",
    "is_member",
    "constituent_tickers",
]
