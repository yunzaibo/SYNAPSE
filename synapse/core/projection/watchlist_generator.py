"""Watchlist Generator — Daily fresh watchlist from events, signals, positions.

ADR-009: Daily regeneration (not incremental).
- Each morning, regenerate the full watchlist
- Combines event attention, sector signals, and portfolio review triggers
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from synapse.core.schemas.base import MarketContext
from synapse.core.schemas.event import Event
from synapse.core.schemas.position import Position
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.watchlist import (
    SignalStrength,
    SignalType,
    TriggerType,
    WatchlistEntry,
    WatchlistSignal,
)
from synapse.core.identity import SecurityIdentity
from synapse.core.naming import generate_id


def _build_event_entries(events: list[Event], target_date: date) -> list[WatchlistEntry]:
    """Build watchlist entries from events for a given date."""
    entries = []
    for event in events:
        if event.event_date != target_date:
            continue

        for ticker in event.related_tickers:
            entry = WatchlistEntry(
                id=generate_id("wl"),
                ticker=ticker,
                symbol="",  # Symbol not available from Event alone
                market="CN_A",
                headline=event.title,
                why_now=event.description,
                signals=[],
                research_angle=f"关注 {event.title} 对 {ticker} 的影响",
                trigger_type=TriggerType.EVENT_ATTENTION,
                linked_event_id=event.id,
                market_context=MarketContext(
                    research_date=target_date,
                    market_date=target_date,
                ),
            )
            entries.append(entry)

    return entries


def _build_signal_entries(signals: list[Signal], target_date: date) -> list[WatchlistEntry]:
    """Build watchlist entries from independent signals."""
    entries = []
    for signal in signals:
        for ticker in signal.related_tickers:
            # Map signal type to watchlist signal type
            wl_signal_type = SignalType.ATTENTION_SPIKE
            if signal.signal_type.value in [s.value for s in SignalType]:
                wl_signal_type = SignalType(signal.signal_type.value)

            entry = WatchlistEntry(
                id=generate_id("wl"),
                ticker=ticker,
                symbol="",
                market="CN_A",
                headline=signal.description,
                why_now=f"信号触发: {signal.description}",
                signals=[
                    WatchlistSignal(
                        type=wl_signal_type,
                        strength=SignalStrength(signal.strength.value),
                        description=signal.description,
                    )
                ],
                research_angle=f"分析信号对 {ticker} 的潜在影响",
                trigger_type=TriggerType.FACTOR_SIGNAL,
                market_context=MarketContext(
                    research_date=target_date,
                    market_date=target_date,
                ),
            )
            entries.append(entry)

    return entries


def _build_portfolio_entries(positions: list[Position], target_date: date) -> list[WatchlistEntry]:
    """Build watchlist entries for portfolio review triggers."""
    entries = []
    for pos in positions:
        entry = WatchlistEntry(
            id=generate_id("wl"),
            ticker=pos.ticker,
            symbol=pos.symbol,
            market=pos.market,
            headline=f"持仓回顾: {pos.symbol or pos.ticker}",
            why_now=f"thesis 状态: {pos.research_state.thesis_status.value}",
            signals=[],
            research_angle=f"评估 {pos.ticker} 持仓 thesis 是否仍然成立",
            trigger_type=TriggerType.PORTFOLIO_REVIEW,
            linked_thesis_id=pos.linked_thesis_id,
            market_context=MarketContext(
                research_date=target_date,
                market_date=target_date,
            ),
        )
        entries.append(entry)

    return entries


def generate_daily(
    events: list[Event],
    signals: list[Signal],
    positions: list[Position],
    target_date: Optional[date] = None,
) -> list[WatchlistEntry]:
    """Generate a fresh daily watchlist.

    This is a full regeneration — not incremental update.
    Called each morning to produce the day's research queue.

    Args:
        events: Market events to consider.
        signals: Independent signals to consider.
        positions: Current positions for portfolio review.
        target_date: Date to generate watchlist for (defaults to today).

    Returns:
        List of WatchlistEntry objects for the target date.
    """
    if target_date is None:
        target_date = date.today()

    entries: list[WatchlistEntry] = []

    # 1. Event-driven entries
    entries.extend(_build_event_entries(events, target_date))

    # 2. Signal-driven entries
    entries.extend(_build_signal_entries(signals, target_date))

    # 3. Portfolio review entries
    entries.extend(_build_portfolio_entries(positions, target_date))

    return entries


def save_watchlist(entries: list[WatchlistEntry], output_dir: str | Path, target_date: Optional[date] = None) -> list[Path]:
    """Save watchlist entries to YAML files.

    Args:
        entries: WatchlistEntry objects to save.
        output_dir: Base watchlists directory (e.g. workspace/watchlists/).
        target_date: Date subdirectory (defaults to today).

    Returns:
        List of paths written.
    """
    from synapse.core.loader import save_object

    if target_date is None:
        target_date = date.today()

    watchlist_dir = Path(output_dir) / target_date.isoformat()
    watchlist_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for entry in entries:
        # Generate filename from ticker and first signal type
        reason = "daily-review"
        if entry.signals:
            reason = entry.signals[0].type.value
        elif entry.trigger_type == TriggerType.PORTFOLIO_REVIEW:
            reason = "portfolio-review"

        filename = f"wl_{entry.ticker}_{reason}.yaml"
        path = watchlist_dir / filename
        save_object(entry, path)
        paths.append(path)

    return paths
