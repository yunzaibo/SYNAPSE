"""Correlation Intelligence -- Event-to-Review Linkage Analysis.

Links Events to Reviews via two paths:
  1. Event.outcome_tracking[].review_id -- direct linkage
  2. Event.linked_review_ids -- explicit Event-side linkage

Computes success rates per event_type, impact calibration, and
identifies unlinked events.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from synapse.core.schemas.event import Event, ImpactLevel
from synapse.core.schemas.review import Review, ReviewOutcome


# --- Calibration mapping: impact_level -> expected outcome倾向 ---

_IMPACT_OUTCOME_MAP: dict[str, dict[str, float]] = {
    # For HIGH impact events, thesis_confirmed is the strong expected outcome
    "high": {
        "thesis_confirmed": 0.9,
        "partially_confirmed": 0.5,
        "thesis_invalidated": 0.1,
    },
    "medium": {
        "thesis_confirmed": 0.7,
        "partially_confirmed": 0.7,
        "thesis_invalidated": 0.3,
    },
    "low": {
        "thesis_confirmed": 0.5,
        "partially_confirmed": 0.8,
        "thesis_invalidated": 0.5,
    },
    "unknown": {
        "thesis_confirmed": 0.5,
        "partially_confirmed": 0.5,
        "thesis_invalidated": 0.5,
    },
}


def _impact_calibration_score(
    impact_level: str, review_outcome: str
) -> float:
    """Return calibration score for a single event-review pair.

    Score = how well the actual review_outcome matches the expected outcome
    given the event's impact_level.  1.0 = perfect match, 0.0 = worst mismatch.
    """
    expectations = _IMPACT_OUTCOME_MAP.get(
        impact_level, _IMPACT_OUTCOME_MAP["unknown"]
    )
    return expectations.get(review_outcome, 0.5)


@dataclass
class CorrelationReport:
    """Output of Event-to-Review correlation analysis.

    Fields:
        event_type_success_rate: success rate (confirmed/total) per event_type
        impact_calibration: calibration detail per impact_level
        correlation_strength: fraction of events that are linked to at least one review
        total_event_review_pairs: number of established event-review links
        unlinked_events: event IDs with no linked review
        overall_calibration_score: average calibration across all linked pairs
    """

    event_type_success_rate: dict[str, float] = field(default_factory=dict)
    impact_calibration: dict[str, dict] = field(default_factory=dict)
    correlation_strength: float = 0.0
    total_event_review_pairs: int = 0
    unlinked_events: list[str] = field(default_factory=list)
    overall_calibration_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "event_type_success_rate": dict(self.event_type_success_rate),
            "impact_calibration": dict(self.impact_calibration),
            "correlation_strength": self.correlation_strength,
            "total_event_review_pairs": self.total_event_review_pairs,
            "unlinked_events": list(self.unlinked_events),
            "overall_calibration_score": self.overall_calibration_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CorrelationReport:
        return cls(
            event_type_success_rate=dict(data.get("event_type_success_rate", {})),
            impact_calibration=dict(data.get("impact_calibration", {})),
            correlation_strength=float(data.get("correlation_strength", 0.0)),
            total_event_review_pairs=int(data.get("total_event_review_pairs", 0)),
            unlinked_events=list(data.get("unlinked_events", [])),
            overall_calibration_score=float(
                data.get("overall_calibration_score", 0.0)
            ),
        )


@dataclass
class _LinkedPair:
    """Internal: a single event-review linkage."""

    event: Event
    review: Review


class CorrelationAnalyzer:
    """Analyzes correlation between Events and Reviews.

    Links are established via:
      1. Event.outcome_tracking[].review_id -> Review.id  (primary)
      2. Event.linked_review_ids -> Review.id              (secondary)
    """

    def analyze(
        self, events: list[Event], reviews: list[Review]
    ) -> CorrelationReport:
        """Compute correlation report for the given events and reviews.

        Args:
            events: list of Event objects to analyze.
            reviews: list of Review objects available for linkage.

        Returns:
            CorrelationReport with linkage metrics and calibration data.
        """
        if not events:
            return CorrelationReport()

        review_by_id: dict[str, Review] = {r.id: r for r in reviews}

        # --- Establish linkage ---
        pairs: list[_LinkedPair] = []
        linked_event_ids: set[str] = set()

        for event in events:
            # Path 1: outcome_tracking[].review_id
            for ot in event.outcome_tracking:
                review = review_by_id.get(ot.review_id)
                if review is not None:
                    pairs.append(_LinkedPair(event=event, review=review))
                    linked_event_ids.add(event.id)

            # Path 2: linked_review_ids (only if not already linked via path 1)
            if event.id not in linked_event_ids:
                for rev_id in event.linked_review_ids:
                    review = review_by_id.get(rev_id)
                    if review is not None:
                        pairs.append(_LinkedPair(event=event, review=review))
                        linked_event_ids.add(event.id)
                        break  # one link is enough

        # --- Compute metrics ---
        event_type_success_rate = self._compute_success_rates(pairs)
        impact_calibration = self._compute_impact_calibration(pairs)
        calibration_scores = [
            _impact_calibration_score(
                p.event.impact_level.value, p.review.review_outcome.value
            )
            for p in pairs
        ]
        overall_calibration = (
            sum(calibration_scores) / len(calibration_scores)
            if calibration_scores
            else 0.0
        )

        total_pairs = len(pairs)
        correlation_strength = len(linked_event_ids) / len(events) if events else 0.0
        unlinked = [e.id for e in events if e.id not in linked_event_ids]

        return CorrelationReport(
            event_type_success_rate=event_type_success_rate,
            impact_calibration=impact_calibration,
            correlation_strength=correlation_strength,
            total_event_review_pairs=total_pairs,
            unlinked_events=unlinked,
            overall_calibration_score=overall_calibration,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_success_rates(
        self, pairs: list[_LinkedPair]
    ) -> dict[str, float]:
        """Compute success rate (confirmed/total) per event_type.

        An event is considered "successful" when its linked review outcome
        is THESIS_CONFIRMED or PARTIALLY_CONFIRMED.
        """
        if not pairs:
            return {}

        type_total: dict[str, int] = {}
        type_confirmed: dict[str, int] = {}

        for pair in pairs:
            etype = pair.event.event_type.value
            type_total[etype] = type_total.get(etype, 0) + 1
            if pair.review.review_outcome in (
                ReviewOutcome.THESIS_CONFIRMED,
                ReviewOutcome.PARTIALLY_CONFIRMED,
            ):
                type_confirmed[etype] = type_confirmed.get(etype, 0) + 1

        return {
            etype: type_confirmed.get(etype, 0) / total
            for etype, total in type_total.items()
        }

    def _compute_impact_calibration(
        self, pairs: list[_LinkedPair]
    ) -> dict[str, dict]:
        """Compute calibration detail per impact_level.

        Returns a dict keyed by impact_level value, each containing:
          - count: number of pairs with this impact_level
          - avg_calibration: average calibration score
          - outcome_distribution: {outcome_value: count}
        """
        if not pairs:
            return {}

        by_impact: dict[str, list[_LinkedPair]] = {}
        for pair in pairs:
            level = pair.event.impact_level.value
            by_impact.setdefault(level, []).append(pair)

        result: dict[str, dict] = {}
        for level, level_pairs in by_impact.items():
            scores = [
                _impact_calibration_score(level, p.review.review_outcome.value)
                for p in level_pairs
            ]
            outcome_dist: dict[str, int] = {}
            for p in level_pairs:
                outcome = p.review.review_outcome.value
                outcome_dist[outcome] = outcome_dist.get(outcome, 0) + 1

            result[level] = {
                "count": len(level_pairs),
                "avg_calibration": sum(scores) / len(scores) if scores else 0.0,
                "outcome_distribution": outcome_dist,
            }

        return result
