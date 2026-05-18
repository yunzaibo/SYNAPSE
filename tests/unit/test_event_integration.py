"""Tests for Event-Review Integration (IMPL-007)."""

import uuid
from datetime import date, timedelta

from synapse.core.schemas.event import Event, EventType
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.thesis import Thesis, Confidence
from synapse.event.integration import EventReviewIntegrator


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestSchemaExtensions
# ---------------------------------------------------------------------------


class TestSchemaExtensions:
    """Verify new event reference fields exist with correct defaults."""

    def test_review_has_event_fields(self) -> None:
        review = Review(id=_uid())
        assert review.event_id is None
        assert review.event_trigger_type is None

    def test_decision_has_event_fields(self) -> None:
        decision = Decision(id=_uid())
        assert decision.event_trigger_id is None
        assert decision.event_influence_score == 0.0

    def test_thesis_has_event_fields(self) -> None:
        thesis = Thesis(id=_uid())
        assert thesis.event_influences == []
        assert thesis.event_influence_weight == 0.0


# ---------------------------------------------------------------------------
# TestBidirectionalLink
# ---------------------------------------------------------------------------


class TestBidirectionalLink:
    """Verify link_event_to_review sets both directions."""

    def test_event_to_review_bidirectional(self) -> None:
        integrator = EventReviewIntegrator()
        event = Event(id=_uid(), event_type=EventType.EARNINGS)
        review = Review(id=_uid())

        integrator.link_event_to_review(event, review, trigger_type="direct")

        # Event -> Review
        assert review.id in event.linked_review_ids
        # Review -> Event
        assert review.event_id == event.id
        assert review.event_trigger_type == "direct"


# ---------------------------------------------------------------------------
# TestRevisionDetection
# ---------------------------------------------------------------------------


class TestRevisionDetection:
    """Verify post-event revision detection within/outside window."""

    def test_revision_within_window(self) -> None:
        integrator = EventReviewIntegrator(default_window_days=30)
        event = Event(id=_uid(), event_date=date(2025, 1, 1))
        thesis = Thesis(id=_uid())
        revision_date = date(2025, 1, 15)  # 14 days after event

        result = integrator.detect_post_event_revision(event, thesis, revision_date)
        assert result is True

    def test_revision_outside_window(self) -> None:
        integrator = EventReviewIntegrator(default_window_days=30)
        event = Event(id=_uid(), event_date=date(2025, 1, 1))
        thesis = Thesis(id=_uid())
        revision_date = date(2025, 3, 15)  # 73 days after event

        result = integrator.detect_post_event_revision(event, thesis, revision_date)
        assert result is False


# ---------------------------------------------------------------------------
# TestReferentialIntegrity
# ---------------------------------------------------------------------------


class TestReferentialIntegrity:
    """Verify referential integrity validation."""

    def test_valid_links_pass(self) -> None:
        integrator = EventReviewIntegrator()
        event = Event(id=_uid())
        review = Review(id=_uid())

        integrator.link_event_to_review(event, review)

        errors = integrator.validate_referential_integrity([event], [review])
        assert errors == []


# ---------------------------------------------------------------------------
# TestMultipleEvents
# ---------------------------------------------------------------------------


class TestMultipleEvents:
    """Verify many-to-one relationships work correctly."""

    def test_multiple_events_same_thesis(self) -> None:
        integrator = EventReviewIntegrator()
        thesis = Thesis(id=_uid())

        event1 = Event(id=_uid(), event_type=EventType.EARNINGS)
        event2 = Event(id=_uid(), event_type=EventType.POLICY)

        thesis.event_influences = [event1.id, event2.id]
        thesis.event_influence_weight = 0.7

        assert len(thesis.event_influences) == 2
        assert event1.id in thesis.event_influences
        assert event2.id in thesis.event_influences

    def test_multiple_reviews_same_event(self) -> None:
        integrator = EventReviewIntegrator()
        event = Event(id=_uid())
        review1 = Review(id=_uid())
        review2 = Review(id=_uid())

        integrator.link_event_to_review(event, review1, trigger_type="direct")
        integrator.link_event_to_review(event, review2, trigger_type="propagated")

        assert review1.id in event.linked_review_ids
        assert review2.id in event.linked_review_ids
        assert review1.event_id == event.id
        assert review2.event_id == event.id
        assert review1.event_trigger_type == "direct"
        assert review2.event_trigger_type == "propagated"


# ---------------------------------------------------------------------------
# TestDecisionEventTracking
# ---------------------------------------------------------------------------


class TestDecisionEventTracking:
    """Verify decision-level event tracking fields."""

    def test_decision_event_trigger(self) -> None:
        event_id = _uid()
        decision = Decision(
            id=_uid(),
            decision_type=DecisionType.BUY,
            ticker="600519",
            event_trigger_id=event_id,
            event_influence_score=0.85,
        )
        assert decision.event_trigger_id == event_id
        assert decision.event_influence_score == 0.85
