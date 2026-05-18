"""Thesis Drift Detector -- Track thesis health via state transitions.

Maps Position.research_state.thesis_status transitions (active -> weakened ->
invalidated) to compute drift metrics: health score, velocity, weakening
signals, and recovery count.  Pure projection from canonical Position +
Thesis objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from synapse.core.schemas.position import Position, ThesisStatus
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.schemas.thesis import Thesis
from synapse.core.temporal import CST


# ---------------------------------------------------------------------------
# Health mapping
# ---------------------------------------------------------------------------

HEALTH_MAP: dict[ThesisStatus, float] = {
    ThesisStatus.ACTIVE: 1.0,
    ThesisStatus.WEAKENED: 0.5,
    ThesisStatus.INVALIDATED: 0.0,
}

# ReviewOutcome -> implied thesis_status
REVIEW_OUTCOME_STATUS: dict[ReviewOutcome, ThesisStatus] = {
    ReviewOutcome.THESIS_CONFIRMED: ThesisStatus.ACTIVE,
    ReviewOutcome.PARTIALLY_CONFIRMED: ThesisStatus.WEAKENED,
    ReviewOutcome.THESIS_INVALIDATED: ThesisStatus.INVALIDATED,
}


# ---------------------------------------------------------------------------
# DriftReport
# ---------------------------------------------------------------------------


@dataclass
class DriftReport:
    """Output of thesis drift analysis."""

    drift_velocity_per_day: float
    health_score: float  # 0.0 - 1.0
    weakening_signals: list[str]
    recovery_count: int
    total_positions_tracked: int
    drift_timeline: list[dict]

    def to_dict(self) -> dict:
        return {
            "drift_velocity_per_day": self.drift_velocity_per_day,
            "health_score": self.health_score,
            "weakening_signals": list(self.weakening_signals),
            "recovery_count": self.recovery_count,
            "total_positions_tracked": self.total_positions_tracked,
            "drift_timeline": list(self.drift_timeline),
        }

    @classmethod
    def from_dict(cls, data: dict) -> DriftReport:
        return cls(
            drift_velocity_per_day=float(data["drift_velocity_per_day"]),
            health_score=float(data["health_score"]),
            weakening_signals=list(data["weakening_signals"]),
            recovery_count=int(data["recovery_count"]),
            total_positions_tracked=int(data["total_positions_tracked"]),
            drift_timeline=list(data["drift_timeline"]),
        )


# ---------------------------------------------------------------------------
# DriftDetector
# ---------------------------------------------------------------------------


class DriftDetector:
    """Detects thesis drift via Position.research_state transitions."""

    def detect(
        self,
        positions: list[Position],
        theses: list[Thesis] | None = None,
        reviews: list[Review] | None = None,
    ) -> DriftReport:
        """Analyze thesis health across positions.

        Args:
            positions: Current positions to evaluate.
            theses: Optional thesis list (reserved for future lineage use).
            reviews: Reviews used to infer state transitions.

        Returns:
            DriftReport with health metrics and transition timeline.
        """
        theses = theses or []
        reviews = reviews or []

        if not positions:
            return DriftReport(
                drift_velocity_per_day=0.0,
                health_score=0.0,
                weakening_signals=[],
                recovery_count=0,
                total_positions_tracked=0,
                drift_timeline=[],
            )

        # --- Current health score from position thesis_status ---
        health_scores = [
            HEALTH_MAP[p.research_state.thesis_status] for p in positions
        ]
        health_score = sum(health_scores) / len(health_scores)

        # --- Weakening signals ---
        weakening_signals = [
            p.id
            for p in positions
            if p.research_state.thesis_status == ThesisStatus.WEAKENED
        ]

        # --- Build timeline from reviews ---
        timeline = self._build_timeline(reviews, positions)

        # --- Recovery count: weakened -> active transitions ---
        recovery_count = sum(
            1
            for entry in timeline
            if entry["from"] == "weakened" and entry["to"] == "active"
        )

        # --- Velocity: transitions per day ---
        velocity = self._compute_velocity(timeline)

        return DriftReport(
            drift_velocity_per_day=velocity,
            health_score=health_score,
            weakening_signals=weakening_signals,
            recovery_count=recovery_count,
            total_positions_tracked=len(positions),
            drift_timeline=timeline,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_timeline(
        self,
        reviews: list[Review],
        positions: list[Position],
    ) -> list[dict]:
        """Build ordered state-transition timeline from review outcomes.

        Each review implies a transition for the linked position (matched
        via linked_thesis_id -> position.linked_thesis_id).  The 'from'
        state is inferred from the review_outcome:
            thesis_confirmed    -> active   (stable)
            partially_confirmed -> weakened
            thesis_invalidated -> invalidated

        Timeline entries are sorted by review.created_at.
        """
        position_by_thesis: dict[str, Position] = {}
        for p in positions:
            if p.linked_thesis_id:
                position_by_thesis[p.linked_thesis_id] = p

        entries: list[dict] = []
        for review in reviews:
            thesis_id = review.linked_thesis_id
            if not thesis_id or thesis_id not in position_by_thesis:
                continue

            position = position_by_thesis[thesis_id]
            new_status = REVIEW_OUTCOME_STATUS.get(review.review_outcome)
            if new_status is None:
                continue

            old_status = position.research_state.thesis_status
            # Skip no-op transitions
            if old_status == new_status:
                continue

            entries.append(
                {
                    "position_id": position.id,
                    "thesis_id": thesis_id,
                    "from": old_status.value,
                    "to": new_status.value,
                    "timestamp": review.created_at.isoformat(),
                    "review_id": review.id,
                }
            )

        entries.sort(key=lambda e: e["timestamp"])
        return entries

    def _compute_velocity(self, timeline: list[dict]) -> float:
        """Compute drift velocity (transitions per day) from timeline.

        Velocity = number of transitions / span in days.
        Returns 0.0 for empty or single-point timelines.
        """
        if len(timeline) < 2:
            return 0.0

        timestamps = sorted(datetime.fromisoformat(e["timestamp"]) for e in timeline)
        span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0

        if span_days <= 0:
            # All transitions on same day -- velocity = count
            return float(len(timeline))

        return len(timeline) / span_days
