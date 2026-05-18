"""Daily Research Workflow — Orchestrate the daily research loop.

ADR-009: Watchlist regeneration is daily (not incremental).
ADR-010: Logs watchlist.generated to activity.jsonl.

Flow:
1. Load events and signals for the target date
2. Load current positions (for portfolio review)
3. Generate fresh daily watchlist
4. Log activity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from synapse.core.activity import ActivityLog, ActivityType
from synapse.core.projection.watchlist_generator import generate_daily, save_watchlist
from synapse.core.schemas.event import Event
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.position import Position
from synapse.core.schemas.watchlist import WatchlistEntry


@dataclass
class DailyResearchResult:
    """Result of a daily research run."""

    target_date: date
    watchlist_entries: list[WatchlistEntry] = field(default_factory=list)
    events_loaded: int = 0
    signals_loaded: int = 0
    positions_loaded: int = 0
    activity_logged: bool = False

    @property
    def watchlist_count(self) -> int:
        return len(self.watchlist_entries)

    def to_dict(self) -> dict:
        return {
            "target_date": self.target_date.isoformat(),
            "watchlist_count": self.watchlist_count,
            "events_loaded": self.events_loaded,
            "signals_loaded": self.signals_loaded,
            "positions_loaded": self.positions_loaded,
            "activity_logged": self.activity_logged,
        }


def run_daily_research(
    target_date: date,
    events: list[Event],
    signals: list[Signal],
    positions: list[Position],
    activity_log: Optional[ActivityLog] = None,
    watchlist_output_dir: Optional[str | Path] = None,
) -> DailyResearchResult:
    """Run the daily research workflow.

    Steps:
    1. Generate fresh watchlist from events, signals, and positions
    2. Save watchlist entries to YAML files
    3. Log watchlist.generated activity

    Args:
        target_date: Date to generate research for.
        events: Market events to consider.
        signals: Independent signals to consider.
        positions: Current positions for portfolio review.
        activity_log: ActivityLog to write to. If None, activity is not logged.
        watchlist_output_dir: Directory to save watchlist files. If None, files are not saved.

    Returns:
        DailyResearchResult with generated watchlist and metadata.
    """
    # Step 1: Generate fresh daily watchlist
    entries = generate_daily(
        events=events,
        signals=signals,
        positions=positions,
        target_date=target_date,
    )

    # Step 2: Save watchlist entries if output dir provided
    if watchlist_output_dir is not None:
        save_watchlist(entries, watchlist_output_dir, target_date)

    # Step 3: Log activity
    activity_logged = False
    if activity_log is not None:
        activity_log.append(
            activity_type=ActivityType.WATCHLIST_GENERATED.value,
            obj_id=f"watchlist_{target_date.isoformat()}",
            actor="ai",
            summary=f"生成 {target_date.isoformat()} 每日研究队列 ({len(entries)} 条)",
        )
        activity_logged = True

    return DailyResearchResult(
        target_date=target_date,
        watchlist_entries=entries,
        events_loaded=len(events),
        signals_loaded=len(signals),
        positions_loaded=len(positions),
        activity_logged=activity_logged,
    )
