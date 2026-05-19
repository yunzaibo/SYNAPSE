"""Market Semantics Scorer — Market-level scoring using trading calendar, northbound flow, index membership.

Uses:
- TradingCalendar (is_trading_day) for date validation
- NorthboundFlow (northbound_to_signals) for capital flow signals
- IndexConstituent (constituent_tickers) for universe filtering

Part of IMPL-5: Market Semantics Scoring.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from synapse.core.market.calendar import is_trading_day
from synapse.core.market.constituent import constituent_tickers
from synapse.core.market.northbound import northbound_to_signals

if TYPE_CHECKING:
    from synapse.core.projection.scoring.types import ScoringContext
    from synapse.core.schemas.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)


def score_market_context(
    entry: WatchlistEntry,
    ctx: ScoringContext,
) -> tuple[float, str]:
    """Score based on market semantics: trading calendar, northbound flow, index membership.

    Combines legacy MarketData scoring with new market semantics:
    - TradingCalendar validates target_date is a trading day
    - NorthboundFlow boosts/reduces score for large inflows/outflows
    - IndexConstituent filters universe to tracked indices

    Returns neutral 0.5 when no market data is available.

    Args:
        entry: WatchlistEntry to score.
        ctx: ScoringContext with target_date, market_data, and config.

    Returns:
        (score, reason) tuple. Score in [0.0, 1.0].
    """
    # 1. Validate trading day
    if not is_trading_day(ctx.target_date):
        return 0.5, "not a trading day (neutral)"

    parts: list[str] = []
    score = 0.5  # neutral baseline

    # 2. Legacy MarketData (sentiment, breadth, volatility)
    if ctx.market_data is not None:
        md = ctx.market_data
        score = (md.sentiment_score + md.breadth_score + (1.0 - md.volatility_score)) / 3.0
        parts.append(f"sentiment={md.sentiment_score:.2f}")
        parts.append(f"breadth={md.breadth_score:.2f}")
        parts.append(f"volatility={md.volatility_score:.2f}")

    # 3. Northbound flow signals
    northbound_records = ctx.config.get("northbound_records")
    if northbound_records:
        nb_signals = northbound_to_signals(northbound_records)
        inflow = [s for s in nb_signals if "inflow" in s.get("signal_type", "")]
        outflow = [s for s in nb_signals if "outflow" in s.get("signal_type", "")]

        if inflow:
            strength = max(s.get("strength", 0) for s in inflow)
            score += min(strength * 0.15, 0.3)
            parts.append(f"{len(inflow)} northbound inflow(s)")
        if outflow:
            strength = max(s.get("strength", 0) for s in outflow)
            score -= min(strength * 0.1, 0.2)
            parts.append(f"{len(outflow)} northbound outflow(s)")

    # 4. Index constituent membership
    tracked_indices = ctx.config.get("tracked_indices", [])
    data_dir = ctx.config.get("data_dir", "data/market")
    for index_code in tracked_indices:
        try:
            members = constituent_tickers(index_code, ctx.target_date, data_dir=data_dir)
            if entry.ticker in members:
                score += 0.1
                parts.append(f"index member ({index_code})")
                break
        except FileNotFoundError:
            continue

    # 5. Clamp and build reason
    score = max(0.0, min(1.0, score))

    if not parts:
        return 0.5, "Market data unavailable"

    reason = ", ".join(parts)
    return score, reason
