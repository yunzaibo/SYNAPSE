"""Watchlist Generator — Daily fresh watchlist from events, signals, positions.

ADR-009: Daily regeneration (not incremental).
- Each morning, regenerate the full watchlist
- Combines event attention, sector signals, and portfolio review triggers
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

# --- Ranking & Filtering ---

DEFAULT_MAX_ENTRIES = 20
DEFAULT_MIN_PRIORITY_SCORE = 0.1


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


def rank_entries(entries: list[WatchlistEntry]) -> list[WatchlistEntry]:
    """Stable sort entries by priority_score descending, tie-break by ticker.

    Uses Python's stable sort so entries with the same score preserve their
    original relative order when ticker is also tied.

    Args:
        entries: List of WatchlistEntry objects with priority_score set.

    Returns:
        New list sorted by priority_score desc, then ticker asc.
    """
    return sorted(entries, key=lambda e: (-e.priority_score, e.ticker))


def filter_entries(
    entries: list[WatchlistEntry],
    max_entries: int = DEFAULT_MAX_ENTRIES,
    min_priority_score: float = DEFAULT_MIN_PRIORITY_SCORE,
    exclude_triggers: Optional[list[TriggerType]] = None,
) -> list[WatchlistEntry]:
    """Filter and deduplicate entries after ranking.

    Steps applied in order:
    1. Exclude entries whose trigger_type is in exclude_triggers.
    2. Exclude entries below min_priority_score.
    3. Deduplicate by ticker — keep highest score per ticker.
    4. Apply top-N cutoff (max_entries).

    Args:
        entries: Already-ranked list (sorted by priority_score desc).
        max_entries: Maximum entries to return (default 20).
        min_priority_score: Minimum score threshold (default 0.1).
        exclude_triggers: Trigger types to exclude entirely.

    Returns:
        Filtered list, still in priority order.
    """
    exclude_set = set(exclude_triggers) if exclude_triggers else set()

    # Step 1 & 2: exclude by trigger type and min score
    candidates = [
        e for e in entries
        if e.trigger_type not in exclude_set and e.priority_score >= min_priority_score
    ]

    # Step 3: dedup by ticker — first occurrence wins (highest score due to ranking)
    seen_tickers: set[str] = set()
    deduped: list[WatchlistEntry] = []
    for e in candidates:
        if e.ticker not in seen_tickers:
            seen_tickers.add(e.ticker)
            deduped.append(e)

    # Step 4: top-N cutoff
    return deduped[:max_entries]


def generate_daily(
    events: list[Event],
    signals: list[Signal],
    positions: list[Position],
    target_date: Optional[date] = None,
    market_data: Optional["MarketData"] = None,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    min_priority_score: float = DEFAULT_MIN_PRIORITY_SCORE,
    exclude_triggers: Optional[list[TriggerType]] = None,
) -> list[WatchlistEntry]:
    """Generate a fresh daily watchlist.

    This is a full regeneration -- not incremental update.
    Called each morning to produce the day's research queue.

    Steps:
        1. Build entries from events, signals, positions.
        2. Score all entries via the scoring engine.
        3. Rank by priority_score (descending), tie-break by ticker.
        4. Filter: exclude triggers, min score, dedup, top-N.

    Args:
        events: Market events to consider.
        signals: Independent signals to consider.
        positions: Current positions for portfolio review.
        target_date: Date to generate watchlist for (defaults to today).
        market_data: Optional market-level data for scoring.
        max_entries: Max entries in final watchlist (default 20).
        min_priority_score: Minimum score to keep (default 0.1).
        exclude_triggers: Trigger types to exclude entirely.

    Returns:
        List of WatchlistEntry objects for the target date,
        ranked, deduplicated, and filtered.
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

    # 4. Score entries using the scoring engine
    if entries:
        from synapse.core.projection.scoring.engine import ScoringEngine
        from synapse.core.projection.scoring.types import ScoringContext

        engine = ScoringEngine()
        context = ScoringContext(
            events=events,
            signals=signals,
            positions=positions,
            target_date=target_date,
            market_data=market_data,
        )
        result = engine.score(entries, context)

        # Update entries with scores and reasons
        scored_entries: list[WatchlistEntry] = []
        for scored in result.entries:
            entry = scored.entry
            entry.priority_score = scored.total_score
            entry.reason = scored.reason
            scored_entries.append(entry)

        # 5. Rank by priority_score desc, tie-break by ticker asc
        ranked = rank_entries(scored_entries)

        # 6. Filter: min score, dedup, top-N
        filtered = filter_entries(
            ranked,
            max_entries=max_entries,
            min_priority_score=min_priority_score,
            exclude_triggers=exclude_triggers,
        )

        return filtered

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
