"""Projection Engine — Compute views from canonical artifacts.

Projections are derived/cached data, not truth sources.
They can be deleted and rebuilt from canonical artifacts at any time.

Components:
- position_rebuilder: Rebuilds Position from Decision/Review changes
- watchlist_generator: Daily fresh watchlist from events/signals/positions
- timeline: Append-only research timeline view
- index_manager: SQLite index for fast object queries
"""

from synapse.core.projection.position_rebuilder import rebuild_from_decisions
from synapse.core.projection.watchlist_generator import generate_daily
from synapse.core.projection.timeline import render_timeline
from synapse.core.projection.index_manager import IndexManager

__all__ = [
    "rebuild_from_decisions",
    "generate_daily",
    "render_timeline",
    "IndexManager",
]
