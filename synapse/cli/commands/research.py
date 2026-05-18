"""CLI command: synapse research daily [--date]

Run the daily research workflow to generate watchlist entries.
"""

from __future__ import annotations

import argparse
from datetime import date

from synapse.core.workflow.daily_research import DailyResearchResult, run_daily_research
from synapse.core.schemas.event import Event
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.position import Position


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the research subcommand."""
    parser = subparsers.add_parser(
        "research",
        help="Research workflows",
        description="Research workflows for market analysis.",
    )
    research_sub = parser.add_subparsers(dest="research_command", help="Research commands")

    # daily subcommand
    daily_parser = research_sub.add_parser(
        "daily",
        help="Run daily research workflow",
        description="Generate a fresh daily watchlist from events, signals, and positions.",
    )
    daily_parser.add_argument(
        "--date",
        default=None,
        help="Target date (YYYY-MM-DD, default: today)",
    )
    daily_parser.set_defaults(func=run_daily)


def run_daily(args: argparse.Namespace) -> int:
    """Execute the daily research command."""
    target_date = (
        date.fromisoformat(args.date) if args.date else date.today()
    )

    # P1: Load from empty lists (no data sources yet)
    events: list[Event] = []
    signals: list[Signal] = []
    positions: list[Position] = []

    result: DailyResearchResult = run_daily_research(
        target_date=target_date,
        events=events,
        signals=signals,
        positions=positions,
    )

    print(f"Daily research for {target_date}:")
    print(f"  Watchlist entries: {result.watchlist_count}")
    print(f"  Events loaded: {result.events_loaded}")
    print(f"  Signals loaded: {result.signals_loaded}")
    print(f"  Positions loaded: {result.positions_loaded}")

    return 0
