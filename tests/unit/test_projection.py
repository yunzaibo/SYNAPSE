"""Tests for Projection Engine (TASK-005)."""

from datetime import date, datetime, timedelta

import pytest

from synapse.core.schemas.base import MarketContext, ObjectStatus
from synapse.core.schemas.decision import Decision, DecisionType, TimeHorizon, AttentionOrigin
from synapse.core.schemas.event import Event, EventType, ImpactLevel
from synapse.core.schemas.position import Position, ResearchState, ThesisStatus, AttentionState
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.schemas.signal import Signal, SignalType as SigSignalType, SignalStrength as SigStrength
from synapse.core.schemas.thesis import Thesis, Confidence
from synapse.core.schemas.watchlist import (
    WatchlistEntry, WatchlistSignal, TriggerType, SignalType, SignalStrength,
)
from synapse.core.temporal import CST

from synapse.core.projection.position_rebuilder import rebuild_from_decisions
from synapse.core.projection.watchlist_generator import generate_daily
from synapse.core.projection.timeline import render_timeline, TimelineEntryType
from synapse.core.projection.index_manager import IndexManager


# --- Test Helpers ---


def _make_decision(
    decision_id: str = "dec_test01",
    ticker: str = "600519",
    symbol: str = "贵州茅台",
    decision_type: DecisionType = DecisionType.BUY,
    thesis: str = "测试 thesis",
    linked_thesis_id: str = "ths_test01",
    created_at: datetime | None = None,
) -> Decision:
    return Decision(
        id=decision_id,
        ticker=ticker,
        symbol=symbol,
        market="CN_A",
        decision_type=decision_type,
        thesis=thesis,
        linked_thesis_id=linked_thesis_id,
        created_at=created_at or datetime(2026, 5, 18, 14, 0, tzinfo=CST),
    )


def _make_review(
    review_id: str = "rev_test01",
    linked_decision_id: str = "dec_test01",
    linked_thesis_id: str = "ths_test01",
    review_outcome: ReviewOutcome = ReviewOutcome.THESIS_CONFIRMED,
) -> Review:
    return Review(
        id=review_id,
        linked_decision_id=linked_decision_id,
        linked_thesis_id=linked_thesis_id,
        review_outcome=review_outcome,
        review_note="测试 review",
    )


def _make_event(
    event_id: str = "evt_test01",
    title: str = "测试事件",
    event_date: date | None = None,
    related_tickers: list[str] | None = None,
) -> Event:
    return Event(
        id=event_id,
        event_type=EventType.EARNINGS,
        title=title,
        description="测试事件描述",
        event_date=event_date or date(2026, 5, 18),
        related_tickers=related_tickers or ["600519"],
        impact_level=ImpactLevel.HIGH,
    )


def _make_signal(
    signal_id: str = "sig_test01",
    signal_type: SigSignalType = SigSignalType.ATTENTION_SPIKE,
    strength: SigStrength = SigStrength.STRONG,
    related_tickers: list[str] | None = None,
) -> Signal:
    return Signal(
        id=signal_id,
        signal_type=signal_type,
        strength=strength,
        description="测试信号",
        related_tickers=related_tickers or ["600519"],
    )


def _make_position(
    pos_id: str = "pos_test01",
    ticker: str = "600519",
    thesis_status: ThesisStatus = ThesisStatus.ACTIVE,
) -> Position:
    return Position(
        id=pos_id,
        ticker=ticker,
        symbol="贵州茅台",
        market="CN_A",
        thesis_at_entry="测试 thesis",
        research_state=ResearchState(thesis_status=thesis_status),
    )


# --- Position Rebuilder Tests ---


class TestPositionRebuilder:
    def test_buy_creates_position(self):
        """Decision.recorded (buy) → creates Position."""
        decision = _make_decision(decision_type=DecisionType.BUY)
        positions = rebuild_from_decisions([decision])

        assert len(positions) == 1
        pos = positions[0]
        assert pos.ticker == "600519"
        assert pos.symbol == "贵州茅台"
        assert pos.linked_decision_id == "dec_test01"
        assert pos.research_state.thesis_status == ThesisStatus.ACTIVE

    def test_sell_closes_position(self):
        """Decision.sold → closes Position."""
        buy = _make_decision(decision_id="dec_buy01", decision_type=DecisionType.BUY)
        sell = _make_decision(
            decision_id="dec_sell01",
            decision_type=DecisionType.SELL,
            created_at=datetime(2026, 5, 19, 14, 0, tzinfo=CST),
        )
        positions = rebuild_from_decisions([buy, sell])

        # Closed positions are filtered out
        assert len(positions) == 0

    def test_chronological_order(self):
        """Decisions are replayed in chronological order."""
        buy1 = _make_decision(
            decision_id="dec_001",
            ticker="600519",
            created_at=datetime(2026, 5, 18, 10, 0, tzinfo=CST),
        )
        buy2 = _make_decision(
            decision_id="dec_002",
            ticker="000858",
            symbol="五粮液",
            created_at=datetime(2026, 5, 18, 14, 0, tzinfo=CST),
        )
        positions = rebuild_from_decisions([buy2, buy1])  # Out of order

        assert len(positions) == 2
        tickers = {p.ticker for p in positions}
        assert tickers == {"600519", "000858"}

    def test_review_updates_research_state(self):
        """Review.completed → updates Position.research_state."""
        buy = _make_decision(decision_id="dec_buy01", decision_type=DecisionType.BUY)
        review = _make_review(
            linked_decision_id="dec_buy01",
            review_outcome=ReviewOutcome.THESIS_INVALIDATED,
        )
        positions = rebuild_from_decisions([buy], reviews=[review])

        assert len(positions) == 1
        assert positions[0].research_state.thesis_status == ThesisStatus.INVALIDATED

    def test_empty_decisions(self):
        """No decisions → empty positions."""
        positions = rebuild_from_decisions([])
        assert positions == []


# --- Watchlist Generator Tests ---


class TestWatchlistGenerator:
    def test_generates_from_events(self):
        """Events generate watchlist entries."""
        event = _make_event(related_tickers=["600519", "000858"])
        entries = generate_daily(events=[event], signals=[], positions=[])

        assert len(entries) == 2
        tickers = {e.ticker for e in entries}
        assert tickers == {"600519", "000858"}

    def test_generates_from_signals(self):
        """Signals generate watchlist entries."""
        signal = _make_signal(related_tickers=["600519"])
        entries = generate_daily(events=[], signals=[signal], positions=[])

        assert len(entries) == 1
        assert entries[0].ticker == "600519"
        assert entries[0].trigger_type == TriggerType.FACTOR_SIGNAL

    def test_generates_portfolio_review(self):
        """Positions generate portfolio review entries."""
        pos = _make_position()
        entries = generate_daily(events=[], signals=[], positions=[pos])

        assert len(entries) == 1
        assert entries[0].trigger_type == TriggerType.PORTFOLIO_REVIEW

    def test_daily_fresh_not_incremental(self):
        """Each call generates a fresh watchlist (not incremental)."""
        event = _make_event()
        entries1 = generate_daily(events=[event], signals=[], positions=[])
        entries2 = generate_daily(events=[event], signals=[], positions=[])

        # Same content, different entry IDs
        assert len(entries1) == len(entries2)
        assert entries1[0].id != entries2[0].id

    def test_filters_by_date(self):
        """Only events matching target_date are included."""
        event_today = _make_event(event_date=date(2026, 5, 18))
        event_tomorrow = _make_event(
            event_id="evt_tomorrow",
            title="明天事件",
            event_date=date(2026, 5, 19),
        )
        entries = generate_daily(
            events=[event_today, event_tomorrow],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )

        assert len(entries) == 1
        assert entries[0].linked_event_id == "evt_test01"


# --- Timeline Tests ---


class TestTimeline:
    def test_renders_thesis(self):
        """Thesis objects appear in timeline."""
        thesis = Thesis(
            id="ths_test01",
            title="测试 thesis",
            thesis_statement="测试 statement",
        )
        view = render_timeline(theses=[thesis])

        assert not view.is_empty
        assert view.entries[0].entry_type == TimelineEntryType.THESIS_CREATED
        assert view.entries[0].object_id == "ths_test01"

    def test_renders_decision(self):
        """Decision objects appear in timeline."""
        decision = _make_decision()
        view = render_timeline(decisions=[decision])

        assert len(view.entries) == 1
        assert view.entries[0].entry_type == TimelineEntryType.DECISION_RECORDED

    def test_renders_review(self):
        """Review objects appear in timeline."""
        review = _make_review()
        view = render_timeline(reviews=[review])

        assert len(view.entries) == 1
        assert view.entries[0].entry_type == TimelineEntryType.REVIEW_COMPLETED

    def test_renders_event(self):
        """Event objects appear in timeline."""
        event = _make_event()
        view = render_timeline(events=[event])

        assert len(view.entries) == 1
        assert view.entries[0].entry_type == TimelineEntryType.EVENT_OCCURRED

    def test_sorted_by_timestamp(self):
        """Entries are sorted chronologically."""
        thesis = Thesis(
            id="ths_001",
            title="早期",
            created_at=datetime(2026, 5, 18, 8, 0, tzinfo=CST),
        )
        decision = _make_decision(
            created_at=datetime(2026, 5, 18, 14, 0, tzinfo=CST),
        )
        review = _make_review()
        # Review created_at defaults to now, so it will be last

        view = render_timeline(theses=[thesis], decisions=[decision], reviews=[review])

        timestamps = [e.timestamp for e in view.entries]
        assert timestamps == sorted(timestamps)

    def test_empty_timeline(self):
        """No artifacts → empty timeline."""
        view = render_timeline()
        assert view.is_empty
        assert view.to_dict()["count"] == 0

    def test_to_dict(self):
        """TimelineView serializes correctly."""
        thesis = Thesis(id="ths_001", title="测试")
        view = render_timeline(theses=[thesis])
        d = view.to_dict()

        assert "entries" in d
        assert d["count"] == 1
        assert d["entries"][0]["entry_type"] == "thesis_created"


# --- Index Manager Tests ---


class TestIndexManager:
    def test_index_and_query(self):
        """Index an object and query it back."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                thesis = Thesis(id="ths_idx01", title="索引测试")
                mgr.index_object(thesis)

                results = mgr.query_objects(obj_type="thesis")
                assert len(results) == 1
                assert results[0]["id"] == "ths_idx01"
            finally:
                mgr.close()

    def test_index_objects_batch(self):
        """Index multiple objects at once."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                objects = [
                    Thesis(id="ths_b01", title="批量1"),
                    Thesis(id="ths_b02", title="批量2"),
                    _make_decision(decision_id="dec_b01"),
                ]
                count = mgr.index_objects(objects)

                assert count == 3
                assert mgr.count_objects("thesis") == 2
                assert mgr.count_objects("decision") == 1
            finally:
                mgr.close()

    def test_query_by_ticker(self):
        """Query objects by ticker."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                dec1 = _make_decision(decision_id="dec_t1", ticker="600519")
                dec2 = _make_decision(decision_id="dec_t2", ticker="000858")
                mgr.index_objects([dec1, dec2])

                results = mgr.query_objects(ticker="600519")
                assert len(results) == 1
                assert results[0]["ticker"] == "600519"
            finally:
                mgr.close()

    def test_query_by_status(self):
        """Query objects by status."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                thesis = Thesis(id="ths_s01", title="状态测试")
                mgr.index_object(thesis)

                results = mgr.query_objects(status="active")
                assert len(results) == 1

                results = mgr.query_objects(status="archived")
                assert len(results) == 0
            finally:
                mgr.close()

    def test_clear_index(self):
        """Clear index removes all data."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                thesis = Thesis(id="ths_c01", title="清除测试")
                mgr.index_object(thesis)
                assert mgr.count_objects() == 1

                mgr.clear_index()
                assert mgr.count_objects() == 0
            finally:
                mgr.close()

    def test_count_objects(self):
        """Count objects correctly."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mgr = IndexManager(db_path)

            try:
                mgr.index_objects([
                    Thesis(id="ths_ct1", title="计数1"),
                    Thesis(id="ths_ct2", title="计数2"),
                    _make_decision(decision_id="dec_ct1"),
                ])

                assert mgr.count_objects() == 3
                assert mgr.count_objects("thesis") == 2
                assert mgr.count_objects("decision") == 1
                assert mgr.count_objects("event") == 0
            finally:
                mgr.close()
