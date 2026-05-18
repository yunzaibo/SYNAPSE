"""Event-Review Integration — Bidirectional event-review linkage.

Provides EventReviewIntegrator for linking events to reviews,
detecting post-event thesis revisions, and validating referential integrity.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from synapse.core.schemas.event import Event
from synapse.core.schemas.review import Review
from synapse.core.schemas.thesis import Thesis


class EventReviewIntegrator:
    """Bidirectional event-review linkage and post-event revision detection."""

    def __init__(self, default_window_days: int = 30) -> None:
        self._window_days = default_window_days
        self._event_reviews: dict[str, list[str]] = {}   # event_id -> [review_ids]
        self._review_events: dict[str, str] = {}          # review_id -> event_id

    def link_event_to_review(
        self,
        event: Event,
        review: Review,
        trigger_type: str = "direct",
    ) -> None:
        """Set bidirectional references between event and review.

        trigger_type: "direct" | "propagated" | "manual"
        """
        # Event -> Review
        if review.id not in event.linked_review_ids:
            event.linked_review_ids.append(review.id)
        # Review -> Event
        review.event_id = event.id
        review.event_trigger_type = trigger_type
        # Internal tracking
        self._event_reviews.setdefault(event.id, []).append(review.id)
        self._review_events[review.id] = event.id

    def detect_post_event_revision(
        self,
        event: Event,
        thesis: Thesis,
        revision_date: date,
        window_days: Optional[int] = None,
    ) -> bool:
        """Check if thesis revision falls within window after event.

        Returns True if revision is within window (should be linked).
        """
        if event.event_date is None:
            return False
        window = window_days or self._window_days
        cutoff = event.event_date + timedelta(days=window)
        return event.event_date <= revision_date <= cutoff

    def validate_referential_integrity(
        self,
        events: list[Event],
        reviews: list[Review],
    ) -> list[str]:
        """Check all links are consistent. Returns list of error messages (empty = valid)."""
        errors: list[str] = []
        event_ids = {e.id for e in events}
        review_ids = {r.id for r in reviews}

        for event in events:
            for rid in event.linked_review_ids:
                if rid not in review_ids:
                    errors.append(f"Event {event.id} links to non-existent review {rid}")

        for review in reviews:
            if review.event_id is not None:
                if review.event_id not in event_ids:
                    errors.append(f"Review {review.id} links to non-existent event {review.event_id}")
                # Check reverse link
                event = next((e for e in events if e.id == review.event_id), None)
                if event is not None and review.id not in event.linked_review_ids:
                    errors.append(
                        f"Review {review.id} -> Event {review.event_id} but reverse link missing"
                    )

        return errors
