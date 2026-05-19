"""Event-Driven Scoring — Decay-aware event scoring for watchlist priority.

Reuses apply_category_decay() from event/lifecycle.py to compute
time-decayed event impact scores. Newer events rank higher, stale
events decay toward zero. Missing events contribute 0.0.

Design:
  - DecayScore: immutable value object (score, reason)
  - score_event_decay(): ScoringFunction-compatible entry point
  - Reuses CATEGORY_HALF_LIVES from event/lifecycle.py
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from synapse.core.projection.scoring.types import ScoringContext
from synapse.core.schemas.event import Event
from synapse.core.schemas.watchlist import WatchlistEntry
from synapse.event.lifecycle import apply_category_decay


# ---------------------------------------------------------------------------
# Value Object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecayScore:
    """Immutable value object for decay-based event scoring result.

    Attributes:
        score: Decay-adjusted impact score in [0.0, 1.0].
        reason: Human-readable explanation of the decay computation.
    """

    score: float
    reason: str

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"DecayScore.score must be in [0.0, 1.0], got {self.score}"
            )

    def as_tuple(self) -> tuple[float, str]:
        """Convert to (score, reason) tuple for ScoringFunction interface."""
        return (self.score, self.reason)


# ---------------------------------------------------------------------------
# Core Scoring Function
# ---------------------------------------------------------------------------


def score_event_decay(
    entry: WatchlistEntry, ctx: ScoringContext
) -> tuple[float, str]:
    """Score event impact with time-decay applied.

    For each event linked to the entry's ticker:
      1. Compute age in days from event.created_at to ctx.target_date
      2. Apply category-specific exponential decay via apply_category_decay()
      3. Initial impact = (severity + confidence) / 2

    Returns the highest decayed score across all relevant events.
    Missing events (no linked events) contribute 0.0.

    Args:
        entry: WatchlistEntry to score.
        ctx: ScoringContext with events and target_date.

    Returns:
        (score, reason) tuple compatible with ScoringFunction interface.
    """
    relevant = [
        e for e in ctx.events if entry.ticker in e.related_tickers
    ]

    if not relevant:
        return 0.0, "no events"

    best = DecayScore(score=0.0, reason="no decay")

    for event in relevant:
        decay_result = _compute_event_decay(event, ctx.target_date)
        if decay_result.score > best.score:
            best = decay_result

    return best.as_tuple()


def _compute_event_decay(event: Event, target_date: date) -> DecayScore:
    """Compute decay score for a single event.

    Args:
        event: The event to compute decay for.
        target_date: Reference date for age computation.

    Returns:
        DecayScore with decayed impact and reason.
    """
    # Compute age in days from event.created_at to target_date
    # Use datetime.combine to align date precision with created_at
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    created_at = event.created_at

    # Ensure both are timezone-aware for subtraction
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    delta = target_dt - created_at
    days = max(delta.total_seconds() / 86400.0, 0.0)

    # Initial impact: same formula as legacy _score_event
    impact_0 = (event.severity + event.confidence) / 2.0
    impact_0 = max(0.0, min(1.0, impact_0))

    # Apply category-specific decay
    event_type_str = event.event_type.value
    decayed = apply_category_decay(event_type_str, impact_0, days)
    decayed = max(0.0, min(1.0, decayed))

    reason = (
        f"type={event_type_str}, impact={impact_0:.2f}, "
        f"age={days:.1f}d, decayed={decayed:.4f}"
    )
    return DecayScore(score=decayed, reason=reason)
