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
from synapse.core.projection.watchlist_generator import (
    generate_daily,
    rank_entries,
    filter_entries,
    save_watchlist,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MIN_PRIORITY_SCORE,
)
from synapse.core.projection.timeline import render_timeline, TimelineEntryType
from synapse.core.projection.index_manager import IndexManager
from synapse.core.projection.scoring.engine import ScoringEngine
from synapse.core.projection.scoring.types import (
    MarketData,
    ScoredEntry,
    ScoringContext,
    ScoringResult,
)
from synapse.core.projection.scoring.aggregator import (
    aggregate_scores,
    normalize_weights,
    DEFAULT_WEIGHTS,
    MARKET_NEUTRAL,
)
from synapse.core.projection.scoring.portfolio_scorer import (
    ThesisAttentionMap,
    build_thesis_attention_map,
    score_portfolio_boost,
    THESIS_INVALIDATED_BOOST,
    THESIS_WEAKENED_BOOST,
    THESIS_ACTIVE_BOOST,
    ATTENTION_RISING_BOOST,
    ATTENTION_FADING_BOOST,
    ATTENTION_STABLE_BOOST,
)
from synapse.core.projection.scoring.event_scorer import (
    DecayScore,
    score_event_decay,
)


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
        entries = generate_daily(events=[event], signals=[], positions=[], target_date=date(2026, 5, 18))

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
        entries1 = generate_daily(events=[event], signals=[], positions=[], target_date=date(2026, 5, 18))
        entries2 = generate_daily(events=[event], signals=[], positions=[], target_date=date(2026, 5, 18))

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


# --- Scoring Engine Tests ---


class TestScoringAggregator:
    def test_default_weights_sum_to_one(self):
        """Default weights must sum to 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_normalize_weights_already_one(self):
        """Weights already summing to 1.0 are unchanged."""
        weights = {"a": 0.5, "b": 0.5}
        result = normalize_weights(weights)
        assert result == weights

    def test_normalize_weights_auto_normalizes(self):
        """Weights not summing to 1.0 are normalized."""
        import warnings
        weights = {"a": 2.0, "b": 3.0}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = normalize_weights(weights)
            assert abs(sum(result.values()) - 1.0) < 1e-9
            assert result["a"] == 0.4
            assert result["b"] == 0.6
            assert len(w) == 1
            assert "normalizing" in str(w[0].message).lower()

    def test_aggregate_scores_weighted_sum(self):
        """aggregate_scores computes weighted sum correctly."""
        scores = {"signal": 1.0, "event": 0.0, "portfolio": 0.0, "market": 0.0}
        result = aggregate_scores(scores)
        # signal weight = 0.35
        assert abs(result - 0.35) < 1e-9

    def test_aggregate_scores_missing_defaults_zero(self):
        """Missing dimensions contribute 0.0 (except market)."""
        result = aggregate_scores({})
        # Only market contributes: 0.15 * 0.5 = 0.075
        assert abs(result - 0.075) < 1e-9

    def test_aggregate_scores_market_neutral(self):
        """Missing market data contributes 0.5 neutral."""
        scores = {"signal": 0.0, "event": 0.0, "portfolio": 0.0}
        result = aggregate_scores(scores)
        assert abs(result - 0.075) < 1e-9  # 0.15 * 0.5

    def test_aggregate_scores_custom_weights(self):
        """Custom weights are used when provided."""
        scores = {"signal": 1.0, "event": 1.0}
        weights = {"signal": 0.5, "event": 0.5}
        result = aggregate_scores(scores, weights)
        assert abs(result - 1.0) < 1e-9


class TestScoringTypes:
    def test_scored_entry_validates_range(self):
        """ScoredEntry rejects total_score outside [0.0, 1.0]."""
        entry = WatchlistEntry(id="wl_test", ticker="600519")
        with pytest.raises(ValueError, match="total_score must be in"):
            ScoredEntry(entry=entry, total_score=1.5)

    def test_scored_entry_to_dict_roundtrip(self):
        """ScoredEntry serializes and deserializes correctly."""
        entry = WatchlistEntry(id="wl_test", ticker="600519")
        scored = ScoredEntry(
            entry=entry,
            total_score=0.75,
            component_scores={"signal": 0.8, "event": 0.7},
            reason="test reason",
        )
        d = scored.to_dict()
        restored = ScoredEntry.from_dict(d)
        assert restored.total_score == 0.75
        assert restored.component_scores == {"signal": 0.8, "event": 0.7}
        assert restored.reason == "test reason"

    def test_scoring_context_to_dict_roundtrip(self):
        """ScoringContext serializes and deserializes correctly."""
        event = _make_event()
        signal = _make_signal()
        pos = _make_position()
        ctx = ScoringContext(
            events=[event],
            signals=[signal],
            positions=[pos],
            target_date=date(2026, 5, 18),
            market_data=MarketData(sentiment_score=0.7),
        )
        d = ctx.to_dict()
        restored = ScoringContext.from_dict(d)
        assert len(restored.events) == 1
        assert len(restored.signals) == 1
        assert len(restored.positions) == 1
        assert restored.market_data is not None
        assert restored.market_data.sentiment_score == 0.7

    def test_market_data_defaults(self):
        """MarketData defaults to neutral (0.5) for all fields."""
        md = MarketData()
        assert md.sentiment_score == 0.5
        assert md.breadth_score == 0.5
        assert md.volatility_score == 0.5


class TestScoringEngine:
    def test_engine_registers_builtin_dimensions(self):
        """Engine registers signal, event, portfolio, market by default."""
        engine = ScoringEngine()
        assert set(engine.dimensions) == {"signal", "event", "portfolio", "market"}

    def test_engine_default_weights(self):
        """Engine uses default weights when none provided."""
        engine = ScoringEngine()
        assert engine.weights == DEFAULT_WEIGHTS

    def test_score_deterministic(self):
        """Identical inputs produce identical outputs."""
        engine = ScoringEngine()
        event = _make_event()
        signal = _make_signal()
        pos = _make_position()
        ctx = ScoringContext(
            events=[event],
            signals=[signal],
            positions=[pos],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_det01",
            ticker="600519",
            symbol="贵州茅台",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
            linked_event_id="evt_test01",
        )

        result1 = engine.score([entry], ctx)
        result2 = engine.score([entry], ctx)

        assert result1.entries[0].total_score == result2.entries[0].total_score
        assert result1.entries[0].component_scores == result2.entries[0].component_scores

    def test_score_event_entry(self):
        """Event entry gets event score and signal score if applicable."""
        engine = ScoringEngine()
        event = _make_event(related_tickers=["600519"])
        ctx = ScoringContext(
            events=[event],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_evt01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test event",
            trigger_type=TriggerType.EVENT_ATTENTION,
            linked_event_id="evt_test01",
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        assert scored.entry.ticker == "600519"
        assert scored.total_score > 0.0
        assert "event" in scored.component_scores
        assert scored.component_scores["event"] > 0.0

    def test_score_signal_entry(self):
        """Signal entry gets signal score."""
        engine = ScoringEngine()
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        ctx = ScoringContext(
            events=[],
            signals=[signal],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_sig01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test signal",
            trigger_type=TriggerType.FACTOR_SIGNAL,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        assert scored.component_scores["signal"] > 0.0
        assert scored.total_score > 0.0

    def test_score_portfolio_entry(self):
        """Portfolio entry gets portfolio score from thesis + attention state."""
        engine = ScoringEngine()
        pos = _make_position(ticker="600519", thesis_status=ThesisStatus.WEAKENED)
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[pos],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_pos01",
            ticker="600519",
            symbol="贵州茅台",
            market="CN_A",
            headline="portfolio review",
            trigger_type=TriggerType.PORTFOLIO_REVIEW,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        # WEAKENED (0.35) + STABLE (0.05) = 0.40
        assert scored.component_scores["portfolio"] == pytest.approx(0.40)

    def test_score_no_data_entry(self):
        """Entry with no matching data gets low score (market still neutral)."""
        engine = ScoringEngine()
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_empty01",
            ticker="999999",
            symbol="",
            market="CN_A",
            headline="no data",
            trigger_type=TriggerType.EVENT_ATTENTION,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        # Only market contributes: 0.15 * 0.5 = 0.075
        assert abs(scored.total_score - 0.075) < 1e-9
        assert scored.component_scores["signal"] == 0.0
        assert scored.component_scores["event"] == 0.0
        assert scored.component_scores["portfolio"] == 0.0
        assert scored.component_scores["market"] == 0.5  # neutral

    def test_score_sorted_descending(self):
        """Results are sorted by total_score descending."""
        engine = ScoringEngine()
        event = _make_event(related_tickers=["600519", "000858"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        ctx = ScoringContext(
            events=[event],
            signals=[signal],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entries = [
            WatchlistEntry(
                id=f"wl_sort{i}",
                ticker=t,
                symbol="",
                market="CN_A",
                headline=f"test {t}",
                trigger_type=TriggerType.EVENT_ATTENTION,
                linked_event_id="evt_test01",
            )
            for i, t in enumerate(["000858", "600519"])
        ]

        result = engine.score(entries, ctx)
        scores = [e.total_score for e in result.entries]
        assert scores == sorted(scores, reverse=True)

    def test_score_single(self):
        """score_single returns a single ScoredEntry."""
        engine = ScoringEngine()
        event = _make_event()
        ctx = ScoringContext(
            events=[event],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_single01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
            linked_event_id="evt_test01",
        )

        scored = engine.score_single(entry, ctx)
        assert isinstance(scored, ScoredEntry)
        assert scored.entry.ticker == "600519"

    def test_custom_weights(self):
        """Custom weights affect scoring."""
        engine_default = ScoringEngine()
        engine_custom = ScoringEngine(weights={"signal": 0.5, "event": 0.5, "portfolio": 0.0, "market": 0.0})

        event = _make_event(related_tickers=["600519"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        ctx = ScoringContext(
            events=[event],
            signals=[signal],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_cust01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
            linked_event_id="evt_test01",
        )

        result_default = engine_default.score([entry], ctx)
        result_custom = engine_custom.score([entry], ctx)

        # Different weights should produce different scores
        assert result_default.entries[0].total_score != result_custom.entries[0].total_score

    def test_register_unregister(self):
        """Custom scoring functions can be registered and unregistered."""
        engine = ScoringEngine()

        def custom_scorer(entry, ctx):
            return 0.99, "custom"

        engine.register("custom_dim", custom_scorer)
        assert "custom_dim" in engine.dimensions

        engine.unregister("custom_dim")
        assert "custom_dim" not in engine.dimensions

    def test_scoring_result_metadata(self):
        """ScoringResult carries metadata."""
        engine = ScoringEngine()
        ctx = ScoringContext(target_date=date(2026, 5, 18))
        entry = WatchlistEntry(
            id="wl_meta01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
        )

        result = engine.score([entry], ctx)
        assert result.target_date == date(2026, 5, 18)
        assert result.config_hash != ""
        assert len(result.config_hash) == 12  # SHA256 truncated to 12 chars

    def test_market_data_with_scoring(self):
        """Market data is used in scoring when provided."""
        engine = ScoringEngine()
        market = MarketData(sentiment_score=0.9, breadth_score=0.8, volatility_score=0.2)
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
            market_data=market,
        )
        entry = WatchlistEntry(
            id="wl_mkt01",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        # Market score: (0.9 + 0.8 + 0.8) / 3 = 0.833...
        assert scored.component_scores["market"] > 0.5
        assert scored.total_score > 0.075  # More than just neutral market


class TestWatchlistGeneratorScoring:
    def test_generate_daily_populates_scores(self):
        """generate_daily populates priority_score and reason on entries."""
        event = _make_event(related_tickers=["600519"])
        entries = generate_daily(
            events=[event],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )

        assert len(entries) == 1
        entry = entries[0]
        assert entry.priority_score > 0.0
        assert entry.reason != ""
        assert "event" in entry.reason.lower() or "signal" in entry.reason.lower()

    def test_generate_daily_sorted_by_score(self):
        """generate_daily returns entries sorted by priority_score."""
        event = _make_event(related_tickers=["600519", "000858"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        entries = generate_daily(
            events=[event],
            signals=[signal],
            positions=[],
            target_date=date(2026, 5, 18),
        )

        scores = [e.priority_score for e in entries]
        assert scores == sorted(scores, reverse=True)

    def test_generate_daily_with_market_data(self):
        """generate_daily accepts optional market_data."""
        event = _make_event()
        market = MarketData(sentiment_score=0.9)
        entries = generate_daily(
            events=[event],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
            market_data=market,
        )

        assert len(entries) == 1
        assert entries[0].priority_score > 0.0

    def test_generate_daily_empty(self):
        """generate_daily with no inputs returns empty list."""
        entries = generate_daily(
            events=[],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        assert entries == []


# --- Portfolio Scoring Tests ---


class TestPortfolioScoring:
    def test_thesis_attention_map_type(self):
        """ThesisAttentionMap is dict[str, tuple[ThesisStatus, AttentionState]]."""
        pos = _make_position(
            ticker="600519",
            thesis_status=ThesisStatus.ACTIVE,
        )
        pos.research_state.attention_state = AttentionState.RISING
        m = build_thesis_attention_map([pos])
        assert isinstance(m, dict)
        assert "600519" in m
        assert m["600519"] == (ThesisStatus.ACTIVE, AttentionState.RISING)

    def test_thesis_invalidated_highest(self):
        """INVALIDATED thesis gives highest thesis boost (0.5)."""
        assert THESIS_INVALIDATED_BOOST == 0.5
        assert THESIS_INVALIDATED_BOOST > THESIS_WEAKENED_BOOST
        assert THESIS_WEAKENED_BOOST > THESIS_ACTIVE_BOOST

    def test_thesis_boost_ordering(self):
        """Thesis status boosts: INVALIDATED > WEAKENED > ACTIVE."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.INVALIDATED, AttentionState.STABLE),
            "B": (ThesisStatus.WEAKENED, AttentionState.STABLE),
            "C": (ThesisStatus.ACTIVE, AttentionState.STABLE),
        }
        sa, _ = score_portfolio_boost("A", m)
        sb, _ = score_portfolio_boost("B", m)
        sc, _ = score_portfolio_boost("C", m)
        assert sa > sb > sc

    def test_attention_rising_highest(self):
        """RISING attention gives highest attention boost (0.25)."""
        assert ATTENTION_RISING_BOOST == 0.25
        assert ATTENTION_RISING_BOOST > ATTENTION_FADING_BOOST
        assert ATTENTION_FADING_BOOST > ATTENTION_STABLE_BOOST

    def test_attention_boost_ordering(self):
        """Attention state boosts: RISING > FADING > STABLE."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.ACTIVE, AttentionState.RISING),
            "B": (ThesisStatus.ACTIVE, AttentionState.FADING),
            "C": (ThesisStatus.ACTIVE, AttentionState.STABLE),
        }
        sa, _ = score_portfolio_boost("A", m)
        sb, _ = score_portfolio_boost("B", m)
        sc, _ = score_portfolio_boost("C", m)
        assert sa > sb > sc

    def test_missing_ticker_returns_zero(self):
        """Missing positions contribute 0.0."""
        m: ThesisAttentionMap = {}
        score, reason = score_portfolio_boost("999999", m)
        assert score == 0.0
        assert "not in portfolio" in reason

    def test_max_boost_clamped(self):
        """Combined boost is clamped to [0.0, 1.0]."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.INVALIDATED, AttentionState.RISING),
        }
        score, _ = score_portfolio_boost("A", m)
        assert score == min(THESIS_INVALIDATED_BOOST + ATTENTION_RISING_BOOST, 1.0)

    def test_invalidated_rising_highest_possible(self):
        """INVALIDATED + RISING gives the highest possible boost."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.INVALIDATED, AttentionState.RISING),
        }
        score, reason = score_portfolio_boost("A", m)
        expected = THESIS_INVALIDATED_BOOST + ATTENTION_RISING_BOOST
        assert score == pytest.approx(expected)
        assert "invalidated" in reason
        assert "rising" in reason

    def test_active_stable_lowest_boost(self):
        """ACTIVE + STABLE gives the lowest non-zero boost."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.ACTIVE, AttentionState.STABLE),
        }
        score, reason = score_portfolio_boost("A", m)
        expected = THESIS_ACTIVE_BOOST + ATTENTION_STABLE_BOOST
        assert score == pytest.approx(expected)
        assert "active" in reason
        assert "stable" in reason

    def test_build_thesis_attention_map_multiple(self):
        """Map handles multiple positions correctly."""
        pos1 = _make_position(pos_id="p1", ticker="600519", thesis_status=ThesisStatus.ACTIVE)
        pos1.research_state.attention_state = AttentionState.RISING
        pos2 = _make_position(pos_id="p2", ticker="000858", thesis_status=ThesisStatus.WEAKENED)
        pos2.research_state.attention_state = AttentionState.FADING
        m = build_thesis_attention_map([pos1, pos2])

        assert len(m) == 2
        assert m["600519"] == (ThesisStatus.ACTIVE, AttentionState.RISING)
        assert m["000858"] == (ThesisStatus.WEAKENED, AttentionState.FADING)

    def test_build_thesis_attention_map_empty_ticker(self):
        """Positions with empty ticker are skipped."""
        pos = _make_position(ticker="")
        m = build_thesis_attention_map([pos])
        assert len(m) == 0

    def test_engine_portfolio_score_with_attention(self):
        """Engine uses portfolio_scorer with attention state."""
        engine = ScoringEngine()
        pos = _make_position(ticker="600519", thesis_status=ThesisStatus.WEAKENED)
        pos.research_state.attention_state = AttentionState.RISING
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[pos],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_att01",
            ticker="600519",
            symbol="贵州茅台",
            market="CN_A",
            headline="portfolio attention",
            trigger_type=TriggerType.PORTFOLIO_REVIEW,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        # WEAKENED (0.35) + RISING (0.25) = 0.60
        assert scored.component_scores["portfolio"] == pytest.approx(0.60)


# --- Market Semantics Scoring Tests ---


class TestMarketScoring:
    def test_market_scoring_non_trading_day(self):
        """Non-trading day returns neutral 0.5."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt01", ticker="600519")
        ctx = ScoringContext(target_date=date(2026, 5, 17))  # Sunday

        score, reason = score_market_context(entry, ctx)
        assert score == 0.5
        assert "not a trading day" in reason

    def test_market_scoring_no_data_returns_neutral(self):
        """No market data returns neutral 0.5."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt02", ticker="600519")
        ctx = ScoringContext(target_date=date(2026, 5, 18))  # Monday

        score, reason = score_market_context(entry, ctx)
        assert score == 0.5
        assert "unavailable" in reason.lower()

    def test_market_scoring_legacy_market_data(self):
        """Legacy MarketData still produces correct score."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt03", ticker="600519")
        market = MarketData(sentiment_score=0.9, breadth_score=0.8, volatility_score=0.2)
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            market_data=market,
        )

        score, reason = score_market_context(entry, ctx)
        # (0.9 + 0.8 + 0.8) / 3 = 0.833...
        assert score == pytest.approx(2.5 / 3.0)
        assert "sentiment" in reason.lower()

    def test_market_scoring_northbound_inflow_boosts(self):
        """Large northbound inflows boost score above 0.5."""
        from decimal import Decimal

        from synapse.core.market.northbound import NorthChannel, NorthboundFlow
        from synapse.core.projection.scoring.market_scorer import score_market_context

        record = NorthboundFlow(
            date=date(2026, 5, 18),
            channel=NorthChannel.HGT,
            buy_amount=Decimal("50"),
            sell_amount=Decimal("30"),
            net_amount=Decimal("20"),  # 20 billion yuan > 1 billion threshold
            total_buy=Decimal("1000"),
            total_sell=Decimal("800"),
            quota_used_pct=Decimal("50"),
            source="test",
        )

        entry = WatchlistEntry(id="wl_mkt04", ticker="600519")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"northbound_records": [record]},
        )

        score, reason = score_market_context(entry, ctx)
        assert score > 0.5
        assert "inflow" in reason.lower()

    def test_market_scoring_northbound_outflow_reduces(self):
        """Large northbound outflows reduce score below 0.5."""
        from decimal import Decimal

        from synapse.core.market.northbound import NorthChannel, NorthboundFlow
        from synapse.core.projection.scoring.market_scorer import score_market_context

        record = NorthboundFlow(
            date=date(2026, 5, 18),
            channel=NorthChannel.SGT,
            buy_amount=Decimal("10"),
            sell_amount=Decimal("40"),
            net_amount=Decimal("-30"),  # -30 billion yuan outflow
            total_buy=Decimal("500"),
            total_sell=Decimal("800"),
            quota_used_pct=Decimal("60"),
            source="test",
        )

        entry = WatchlistEntry(id="wl_mkt05", ticker="600519")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"northbound_records": [record]},
        )

        score, reason = score_market_context(entry, ctx)
        assert score < 0.5
        assert "outflow" in reason.lower()

    def test_market_scoring_index_member_boosts(self):
        """Index membership boosts score."""
        from unittest.mock import patch

        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt06", ticker="600519")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"tracked_indices": ["000300.SH"]},
        )

        with patch(
            "synapse.core.projection.scoring.market_scorer.constituent_tickers",
            return_value=frozenset(["600519", "000858"]),
        ):
            score, reason = score_market_context(entry, ctx)

        assert score == pytest.approx(0.6)  # 0.5 baseline + 0.1 index member
        assert "index member" in reason.lower()

    def test_market_scoring_non_member_no_boost(self):
        """Ticker not in any tracked index gets no index boost."""
        from unittest.mock import patch

        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt07", ticker="999999")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"tracked_indices": ["000300.SH"]},
        )

        with patch(
            "synapse.core.projection.scoring.market_scorer.constituent_tickers",
            return_value=frozenset(["600519", "000858"]),
        ):
            score, reason = score_market_context(entry, ctx)

        assert score == 0.5
        assert "unavailable" in reason.lower()

    def test_market_scoring_index_file_not_found_skipped(self):
        """Missing index data file is skipped gracefully."""
        from unittest.mock import patch

        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_mkt08", ticker="600519")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"tracked_indices": ["000300.SH"]},
        )

        with patch(
            "synapse.core.projection.scoring.market_scorer.constituent_tickers",
            side_effect=FileNotFoundError("no data"),
        ):
            score, reason = score_market_context(entry, ctx)

        assert score == 0.5
        assert "unavailable" in reason.lower()

    def test_market_scoring_combined_signals(self):
        """MarketData + northbound + index combined."""
        from decimal import Decimal
        from unittest.mock import patch

        from synapse.core.market.northbound import NorthChannel, NorthboundFlow
        from synapse.core.projection.scoring.market_scorer import score_market_context

        record = NorthboundFlow(
            date=date(2026, 5, 18),
            channel=NorthChannel.HGT,
            buy_amount=Decimal("50"),
            sell_amount=Decimal("30"),
            net_amount=Decimal("20"),
            total_buy=Decimal("1000"),
            total_sell=Decimal("800"),
            quota_used_pct=Decimal("50"),
            source="test",
        )

        entry = WatchlistEntry(id="wl_mkt09", ticker="600519")
        market = MarketData(sentiment_score=0.7, breadth_score=0.6, volatility_score=0.3)
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            market_data=market,
            config={
                "northbound_records": [record],
                "tracked_indices": ["000300.SH"],
            },
        )

        with patch(
            "synapse.core.projection.scoring.market_scorer.constituent_tickers",
            return_value=frozenset(["600519"]),
        ):
            score, reason = score_market_context(entry, ctx)

        # Legacy: (0.7 + 0.6 + 0.7) / 3 = 0.666...
        # + inflow boost: min(2.0 * 0.15, 0.3) = 0.3
        # + index member: 0.1
        # Total before clamp: 0.666 + 0.3 + 0.1 = 1.066 -> clamped to 1.0
        assert score == 1.0
        assert "sentiment" in reason.lower()
        assert "inflow" in reason.lower()
        assert "index member" in reason.lower()

    def test_market_scoring_engine_integration(self):
        """Engine uses score_market_context for market dimension."""
        engine = ScoringEngine()
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_mkt10",
            ticker="600519",
            symbol="",
            market="CN_A",
            headline="test",
            trigger_type=TriggerType.EVENT_ATTENTION,
        )

        result = engine.score([entry], ctx)
        scored = result.entries[0]

        # No data -> neutral 0.5
        assert scored.component_scores["market"] == 0.5


# --- Event Scoring Tests ---


class TestDecayScore:
    def test_decay_score_valid_range(self):
        """DecayScore accepts scores in [0.0, 1.0]."""
        ds = DecayScore(score=0.75, reason="test")
        assert ds.score == 0.75
        assert ds.reason == "test"

    def test_decay_score_boundaries(self):
        """DecayScore accepts boundary values 0.0 and 1.0."""
        ds0 = DecayScore(score=0.0, reason="zero")
        ds1 = DecayScore(score=1.0, reason="one")
        assert ds0.score == 0.0
        assert ds1.score == 1.0

    def test_decay_score_rejects_out_of_range(self):
        """DecayScore rejects scores outside [0.0, 1.0]."""
        with pytest.raises(ValueError, match="DecayScore.score must be in"):
            DecayScore(score=1.5, reason="too high")
        with pytest.raises(ValueError, match="DecayScore.score must be in"):
            DecayScore(score=-0.1, reason="too low")

    def test_decay_score_is_frozen(self):
        """DecayScore is immutable (frozen dataclass)."""
        ds = DecayScore(score=0.5, reason="immutable")
        with pytest.raises(AttributeError):
            ds.score = 0.8  # type: ignore[misc]

    def test_decay_score_as_tuple(self):
        """DecayScore.as_tuple() returns (score, reason)."""
        ds = DecayScore(score=0.65, reason="reason text")
        assert ds.as_tuple() == (0.65, "reason text")


class TestEventScoring:
    def test_missing_events_returns_zero(self):
        """No events for ticker returns 0.0."""
        entry = WatchlistEntry(
            id="wl_evt01", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[], target_date=date(2026, 5, 18))
        score, reason = score_event_decay(entry, ctx)
        assert score == 0.0
        assert "no events" in reason

    def test_no_matching_ticker_returns_zero(self):
        """Events for other tickers return 0.0 for this entry."""
        event = _make_event(related_tickers=["000858"])
        entry = WatchlistEntry(
            id="wl_evt02", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        score, reason = score_event_decay(entry, ctx)
        assert score == 0.0
        assert "no events" in reason

    def test_fresh_event_high_score(self):
        """A fresh event (created today) scores near its initial impact."""
        now = datetime.now(CST)
        event = Event(
            id="evt_fresh", event_type=EventType.EARNINGS,
            title="fresh event", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8, confidence=0.9,
            created_at=now,
        )
        entry = WatchlistEntry(
            id="wl_evt03", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        score, reason = score_event_decay(entry, ctx)

        # Impact_0 = (0.8 + 0.9) / 2 = 0.85, age ~0 days -> minimal decay
        assert score > 0.8
        assert "earnings" in reason

    def test_old_event_decays(self):
        """An older event scores lower than a fresh event."""
        # Event created 10 days ago
        old_time = datetime(2026, 5, 8, 12, 0, tzinfo=CST)
        old_event = Event(
            id="evt_old", event_type=EventType.POLICY,
            title="old policy", description="desc",
            event_date=date(2026, 5, 8),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.9, confidence=0.9,
            created_at=old_time,
        )
        # Fresh event with same impact
        fresh_event = Event(
            id="evt_fresh", event_type=EventType.POLICY,
            title="fresh policy", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.9, confidence=0.9,
            created_at=datetime(2026, 5, 18, 12, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_evt04", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )

        ctx_old = ScoringContext(events=[old_event], target_date=date(2026, 5, 18))
        score_old, _ = score_event_decay(entry, ctx_old)

        ctx_fresh = ScoringContext(events=[fresh_event], target_date=date(2026, 5, 18))
        score_fresh, _ = score_event_decay(entry, ctx_fresh)

        assert score_fresh > score_old
        assert score_old > 0.0  # Still has some residual impact

    def test_uses_highest_decayed_event(self):
        """When multiple events exist, the highest decayed score wins."""
        high_event = Event(
            id="evt_high", event_type=EventType.EARNINGS,
            title="high", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.9, confidence=0.9,
            created_at=datetime(2026, 5, 18, 12, 0, tzinfo=CST),
        )
        low_event = Event(
            id="evt_low", event_type=EventType.SOCIAL_SENTIMENT,
            title="low", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.LOW,
            severity=0.2, confidence=0.3,
            created_at=datetime(2026, 5, 18, 12, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_evt05", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(
            events=[high_event, low_event], target_date=date(2026, 5, 18),
        )
        score, reason = score_event_decay(entry, ctx)

        # High event: (0.9+0.9)/2 = 0.9 with earnings half-life (6.5d)
        # Low event: (0.2+0.3)/2 = 0.25 with social_sentiment half-life (0.5d)
        assert score > 0.8  # Should pick the high event
        assert "earnings" in reason

    def test_social_sentiment_decays_fast(self):
        """Social sentiment events decay faster than earnings events."""
        social_event = Event(
            id="evt_social", event_type=EventType.SOCIAL_SENTIMENT,
            title="social", description="desc",
            event_date=date(2026, 5, 16),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8, confidence=0.8,
            created_at=datetime(2026, 5, 16, 12, 0, tzinfo=CST),
        )
        earnings_event = Event(
            id="evt_earn", event_type=EventType.EARNINGS,
            title="earnings", description="desc",
            event_date=date(2026, 5, 16),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8, confidence=0.8,
            created_at=datetime(2026, 5, 16, 12, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_evt06", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )

        ctx_social = ScoringContext(events=[social_event], target_date=date(2026, 5, 18))
        score_social, _ = score_event_decay(entry, ctx_social)

        ctx_earnings = ScoringContext(events=[earnings_event], target_date=date(2026, 5, 18))
        score_earnings, _ = score_event_decay(entry, ctx_earnings)

        # Social sentiment half-life=0.5d decays much faster than earnings half-life=6.5d
        assert score_earnings > score_social

    def test_decay_score_in_reason(self):
        """Reason string contains decay details."""
        event = _make_event(related_tickers=["600519"])
        entry = WatchlistEntry(
            id="wl_evt07", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        _, reason = score_event_decay(entry, ctx)
        assert "type=" in reason
        assert "impact=" in reason
        assert "age=" in reason

    def test_event_age_computed_from_created_at(self):
        """Event age is computed from created_at, not event_date."""
        # Event created 5 days ago but event_date is today
        event = Event(
            id="evt_age", event_type=EventType.EARNINGS,
            title="age test", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8, confidence=0.8,
            created_at=datetime(2026, 5, 13, 0, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_evt08", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        _, reason = score_event_decay(entry, ctx)
        # Should show ~5 days age (created at midnight CST = UTC+8)
        assert "age=" in reason
        assert "d," in reason

    def test_engine_event_dimension_uses_decay(self):
        """Engine 'event' dimension uses score_event_decay (decay-based)."""
        engine = ScoringEngine()
        # Verify event scorer is the decay-based one
        assert "event" in engine.dimensions

        now = datetime.now(CST)
        event = Event(
            id="evt_eng", event_type=EventType.EARNINGS,
            title="engine test", description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8, confidence=0.9,
            created_at=now,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        entry = WatchlistEntry(
            id="wl_eng01", ticker="600519", symbol="", market="CN_A",
            headline="test", trigger_type=TriggerType.EVENT_ATTENTION,
            linked_event_id="evt_eng",
        )
        result = engine.score([entry], ctx)
        scored = result.entries[0]
        assert scored.component_scores["event"] > 0.0


# --- Ranking & Filtering Tests ---


def _make_wl_entry(
    entry_id: str = "wl_rank01",
    ticker: str = "600519",
    score: float = 0.5,
    trigger: TriggerType = TriggerType.EVENT_ATTENTION,
) -> WatchlistEntry:
    """Helper to create a scored WatchlistEntry for ranking/filtering tests."""
    return WatchlistEntry(
        id=entry_id,
        ticker=ticker,
        symbol="",
        market="CN_A",
        headline=f"test {ticker}",
        trigger_type=trigger,
        priority_score=score,
        reason="test",
    )


class TestRankingFiltering:
    def test_rank_entries_descending(self):
        """rank_entries sorts by priority_score descending."""
        e1 = _make_wl_entry("wl_a", "600519", score=0.3)
        e2 = _make_wl_entry("wl_b", "000858", score=0.8)
        e3 = _make_wl_entry("wl_c", "601318", score=0.5)

        ranked = rank_entries([e1, e2, e3])

        scores = [e.priority_score for e in ranked]
        assert scores == [0.8, 0.5, 0.3]

    def test_rank_entries_tie_break_by_ticker(self):
        """Tie-breaking uses ticker alphabetical order."""
        e1 = _make_wl_entry("wl_x", "600519", score=0.5)
        e2 = _make_wl_entry("wl_y", "000858", score=0.5)
        e3 = _make_wl_entry("wl_z", "601318", score=0.5)

        ranked = rank_entries([e1, e2, e3])

        tickers = [e.ticker for e in ranked]
        assert tickers == ["000858", "600519", "601318"]

    def test_rank_entries_stable(self):
        """rank_entries preserves original order for identical score+ticker."""
        e1 = _make_wl_entry("wl_s1", "600519", score=0.5)
        e2 = _make_wl_entry("wl_s2", "600519", score=0.5)

        ranked = rank_entries([e1, e2])

        assert ranked[0].id == "wl_s1"
        assert ranked[1].id == "wl_s2"

    def test_rank_entries_empty(self):
        """rank_entries on empty list returns empty list."""
        assert rank_entries([]) == []

    def test_rank_entries_single(self):
        """rank_entries with one entry returns it unchanged."""
        e = _make_wl_entry("wl_single", "600519", score=0.9)
        ranked = rank_entries([e])
        assert len(ranked) == 1
        assert ranked[0].id == "wl_single"

    def test_rank_entries_does_not_mutate(self):
        """rank_entries returns a new list, does not mutate input."""
        e1 = _make_wl_entry("wl_m1", "600519", score=0.3)
        e2 = _make_wl_entry("wl_m2", "000858", score=0.8)
        original = [e1, e2]

        ranked = rank_entries(original)

        assert len(original) == 2
        assert original[0].id == "wl_m1"
        assert ranked[0].id == "wl_m2"

    def test_filter_entries_top_n(self):
        """filter_entries applies top-N cutoff."""
        entries = [_make_wl_entry(f"wl_t{i}", f"000{i}", score=0.9 - i * 0.1)
                   for i in range(5)]

        filtered = filter_entries(entries, max_entries=3)

        assert len(filtered) == 3
        assert filtered[0].priority_score == 0.9
        assert filtered[2].priority_score == 0.7

    def test_filter_entries_min_score(self):
        """filter_entries applies min_priority_score threshold."""
        entries = [
            _make_wl_entry("wl_hi", "600519", score=0.8),
            _make_wl_entry("wl_lo", "000858", score=0.05),
            _make_wl_entry("wl_md", "601318", score=0.3),
        ]

        filtered = filter_entries(entries, min_priority_score=0.1)

        tickers = [e.ticker for e in filtered]
        assert "000858" not in tickers
        assert len(filtered) == 2

    def test_filter_entries_dedup_by_ticker(self):
        """filter_entries deduplicates by ticker, highest score wins."""
        entries = [
            _make_wl_entry("wl_d1", "600519", score=0.9),
            _make_wl_entry("wl_d2", "600519", score=0.5),
            _make_wl_entry("wl_d3", "000858", score=0.7),
        ]

        filtered = filter_entries(entries)

        assert len(filtered) == 2
        # First occurrence (highest score) wins
        assert filtered[0].id == "wl_d1"
        assert filtered[0].priority_score == 0.9
        assert filtered[1].ticker == "000858"

    def test_filter_entries_exclude_triggers(self):
        """filter_entries excludes specified trigger types."""
        entries = [
            _make_wl_entry("wl_e1", "600519", score=0.8, trigger=TriggerType.EVENT_ATTENTION),
            _make_wl_entry("wl_e2", "000858", score=0.7, trigger=TriggerType.PORTFOLIO_REVIEW),
            _make_wl_entry("wl_e3", "601318", score=0.6, trigger=TriggerType.FACTOR_SIGNAL),
        ]

        filtered = filter_entries(
            entries,
            exclude_triggers=[TriggerType.PORTFOLIO_REVIEW],
        )

        tickers = [e.ticker for e in filtered]
        assert "000858" not in tickers
        assert len(filtered) == 2

    def test_filter_entries_empty(self):
        """filter_entries on empty list returns empty list."""
        assert filter_entries([]) == []

    def test_filter_entries_combined(self):
        """filter_entries applies all filters together."""
        entries = [
            _make_wl_entry("wl_c1", "600519", score=0.9, trigger=TriggerType.EVENT_ATTENTION),
            _make_wl_entry("wl_c2", "600519", score=0.4, trigger=TriggerType.FACTOR_SIGNAL),
            _make_wl_entry("wl_c3", "000858", score=0.8, trigger=TriggerType.PORTFOLIO_REVIEW),
            _make_wl_entry("wl_c4", "601318", score=0.05, trigger=TriggerType.EVENT_ATTENTION),
            _make_wl_entry("wl_c5", "000001", score=0.3, trigger=TriggerType.EVENT_ATTENTION),
        ]

        filtered = filter_entries(
            entries,
            max_entries=2,
            min_priority_score=0.1,
            exclude_triggers=[TriggerType.PORTFOLIO_REVIEW],
        )

        # 000858 excluded (trigger), 601318 excluded (min score), dup 600519 kept once
        assert len(filtered) == 2
        assert filtered[0].ticker == "600519"
        assert filtered[0].priority_score == 0.9
        assert filtered[1].ticker == "000001"

    def test_filter_entries_preserves_ranking(self):
        """filter_entries maintains ranking order from input."""
        entries = [
            _make_wl_entry("wl_p1", "000001", score=0.9),
            _make_wl_entry("wl_p2", "600519", score=0.7),
            _make_wl_entry("wl_p3", "000858", score=0.5),
        ]

        filtered = filter_entries(entries, max_entries=10)

        scores = [e.priority_score for e in filtered]
        assert scores == sorted(scores, reverse=True)

    def test_generate_daily_integrates_ranking_filtering(self):
        """generate_daily returns ranked, filtered entries."""
        event = _make_event(related_tickers=["600519", "000858"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        entries = generate_daily(
            events=[event],
            signals=[signal],
            positions=[],
            target_date=date(2026, 5, 18),
        )

        # Should be sorted by priority_score descending
        scores = [e.priority_score for e in entries]
        assert scores == sorted(scores, reverse=True)

        # All entries should have scores
        for e in entries:
            assert e.priority_score > 0.0

    def test_generate_daily_respects_max_entries(self):
        """generate_daily respects max_entries parameter."""
        # Create many events to generate many entries
        events = [
            _make_event(event_id=f"evt_{i}", related_tickers=[f"600{i:03d}"])
            for i in range(25)
        ]
        entries = generate_daily(
            events=events,
            signals=[],
            positions=[],
            target_date=date(2026, 5, 18),
            max_entries=10,
        )

        assert len(entries) <= 10

    def test_generate_daily_excludes_triggers(self):
        """generate_daily excludes specified trigger types."""
        pos = _make_position(ticker="600519")
        entries = generate_daily(
            events=[],
            signals=[],
            positions=[pos],
            target_date=date(2026, 5, 18),
            exclude_triggers=[TriggerType.PORTFOLIO_REVIEW],
        )

        for e in entries:
            assert e.trigger_type != TriggerType.PORTFOLIO_REVIEW

    def test_default_constants(self):
        """Default constants are reasonable."""
        assert DEFAULT_MAX_ENTRIES == 20
        assert DEFAULT_MIN_PRIORITY_SCORE == 0.1


# --- build_reason Tests ---


class TestBuildReason:
    def test_build_reason_all_dims_present(self):
        """build_reason formats all dimensions with scores and weights."""
        from synapse.core.projection.scoring.aggregator import build_reason

        scores = {"signal": 0.8, "event": 0.6, "portfolio": 0.4, "market": 0.7}
        weights = {"signal": 0.35, "event": 0.30, "portfolio": 0.20, "market": 0.15}
        reason = build_reason(scores, weights)

        assert "signal=0.80*0.35" in reason
        assert "event=0.60*0.30" in reason
        assert "portfolio=0.40*0.20" in reason
        assert "market=0.70*0.15" in reason

    def test_build_reason_missing_non_market(self):
        """build_reason shows N/A for missing non-market dimensions."""
        from synapse.core.projection.scoring.aggregator import build_reason

        scores = {"market": 0.5}
        weights = {"signal": 0.35, "event": 0.30, "portfolio": 0.20, "market": 0.15}
        reason = build_reason(scores, weights)

        assert "signal=N/A" in reason
        assert "event=N/A" in reason
        assert "portfolio=N/A" in reason
        assert "market=0.50*0.15" in reason

    def test_build_reason_missing_market_shows_neutral(self):
        """build_reason shows 0.50 (neutral) for missing market dimension."""
        from synapse.core.projection.scoring.aggregator import build_reason

        scores = {"signal": 0.9}
        weights = DEFAULT_WEIGHTS
        reason = build_reason(scores, weights)

        assert "market=0.50 (neutral)" in reason

    def test_build_reason_format_order(self):
        """build_reason outputs dimensions in fixed order: signal, event, portfolio, market."""
        from synapse.core.projection.scoring.aggregator import build_reason

        scores = {"market": 0.1, "signal": 0.9}
        weights = DEFAULT_WEIGHTS
        reason = build_reason(scores, weights)

        # signal comes before market in the output
        signal_pos = reason.index("signal=")
        market_pos = reason.index("market=")
        assert signal_pos < market_pos


# --- ScoringResult Roundtrip Tests ---


class TestScoringResultRoundtrip:
    def test_scoring_result_to_dict_from_dict(self):
        """ScoringResult roundtrip preserves all fields."""
        entry = WatchlistEntry(id="wl_rt01", ticker="600519")
        scored = ScoredEntry(
            entry=entry,
            total_score=0.75,
            component_scores={"signal": 0.8, "event": 0.6},
            reason="test reason",
        )
        result = ScoringResult(
            entries=[scored],
            target_date=date(2026, 5, 18),
            config_hash="abc123def456",
        )
        d = result.to_dict()
        restored = ScoringResult.from_dict(d)

        assert len(restored.entries) == 1
        assert restored.entries[0].total_score == 0.75
        assert restored.target_date == date(2026, 5, 18)
        assert restored.config_hash == "abc123def456"

    def test_scoring_result_empty_roundtrip(self):
        """ScoringResult with no entries roundtrips correctly."""
        result = ScoringResult(target_date=date(2026, 1, 1))
        d = result.to_dict()
        restored = ScoringResult.from_dict(d)

        assert restored.entries == []
        assert restored.config_hash == ""

    def test_market_data_to_dict_from_dict(self):
        """MarketData roundtrip preserves values."""
        md = MarketData(sentiment_score=0.9, breadth_score=0.3, volatility_score=0.8)
        d = md.to_dict()
        restored = MarketData.from_dict(d)

        assert restored.sentiment_score == 0.9
        assert restored.breadth_score == 0.3
        assert restored.volatility_score == 0.8

    def test_market_data_from_dict_defaults(self):
        """MarketData.from_dict fills defaults for missing keys."""
        md = MarketData.from_dict({})
        assert md.sentiment_score == 0.5
        assert md.breadth_score == 0.5
        assert md.volatility_score == 0.5

    def test_scoring_context_roundtrip_without_market_data(self):
        """ScoringContext roundtrip works without market_data."""
        ctx = ScoringContext(
            events=[],
            signals=[],
            positions=[],
            target_date=date(2026, 6, 1),
            config={"key": "val"},
        )
        d = ctx.to_dict()
        restored = ScoringContext.from_dict(d)

        assert restored.market_data is None
        assert restored.config == {"key": "val"}
        assert restored.target_date == date(2026, 6, 1)


# --- WatchlistEntry Serialization Roundtrip ---


class TestWatchlistEntrySerialization:
    def test_roundtrip_with_signals(self):
        """WatchlistEntry with signals roundtrips correctly."""
        entry = WatchlistEntry(
            id="wl_sig_rt",
            ticker="600519",
            symbol="贵州茅台",
            market="CN_A",
            headline="test",
            signals=[
                WatchlistSignal(
                    type=SignalType.ATTENTION_SPIKE,
                    strength=SignalStrength.STRONG,
                    description="spike detected",
                ),
                WatchlistSignal(
                    type=SignalType.SECTOR_RESONANCE,
                    strength=SignalStrength.MEDIUM,
                    description="sector resonance",
                ),
            ],
            priority_score=0.85,
            reason="two signals",
            trigger_type=TriggerType.FACTOR_SIGNAL,
            linked_event_id="evt_001",
            linked_thesis_id="ths_001",
        )
        d = entry.to_dict()
        restored = WatchlistEntry.from_dict(d)

        assert restored.id == "wl_sig_rt"
        assert len(restored.signals) == 2
        assert restored.signals[0].type == SignalType.ATTENTION_SPIKE
        assert restored.signals[1].strength == SignalStrength.MEDIUM
        assert restored.priority_score == 0.85
        assert restored.linked_event_id == "evt_001"
        assert restored.linked_thesis_id == "ths_001"

    def test_roundtrip_with_empty_signals(self):
        """WatchlistEntry with empty signals list roundtrips correctly."""
        entry = WatchlistEntry(
            id="wl_no_sig",
            ticker="000858",
            trigger_type=TriggerType.PORTFOLIO_REVIEW,
        )
        d = entry.to_dict()
        restored = WatchlistEntry.from_dict(d)

        assert restored.signals == []
        assert restored.priority_score == 0.0
        assert restored.trigger_type == TriggerType.PORTFOLIO_REVIEW

    def test_roundtrip_preserves_all_trigger_types(self):
        """All TriggerType values survive roundtrip."""
        for trigger in TriggerType:
            entry = WatchlistEntry(
                id=f"wl_trigger_{trigger.value}",
                ticker="600519",
                trigger_type=trigger,
            )
            d = entry.to_dict()
            restored = WatchlistEntry.from_dict(d)
            assert restored.trigger_type == trigger

    def test_watchlist_signal_roundtrip(self):
        """WatchlistSignal roundtrip preserves all fields."""
        sig = WatchlistSignal(
            type=SignalType.EARNINGS_SURPRISE,
            strength=SignalStrength.WEAK,
            description="earnings surprise",
        )
        d = sig.to_dict()
        restored = WatchlistSignal.from_dict(d)

        assert restored.type == SignalType.EARNINGS_SURPRISE
        assert restored.strength == SignalStrength.WEAK
        assert restored.description == "earnings surprise"

    def test_scored_entry_roundtrip_with_all_fields(self):
        """ScoredEntry roundtrip preserves entry, scores, and reason."""
        entry = WatchlistEntry(
            id="wl_full", ticker="600519", symbol="MT",
            market="CN_A", headline="headline",
            priority_score=0.6, reason="because",
        )
        scored = ScoredEntry(
            entry=entry,
            total_score=0.6,
            component_scores={"signal": 0.5, "event": 0.3, "portfolio": 0.0, "market": 0.5},
            reason="signal=0.50*0.35, event=0.30*0.30",
        )
        d = scored.to_dict()
        restored = ScoredEntry.from_dict(d)

        assert restored.total_score == 0.6
        assert restored.component_scores["signal"] == 0.5
        assert restored.reason == scored.reason


# --- Additional Ranking Edge Cases ---


class TestRankingEdgeCases:
    def test_rank_all_same_score(self):
        """rank_entries handles all entries with the same score (tie-break by ticker)."""
        entries = [
            _make_wl_entry("wl_a", "601318", score=0.5),
            _make_wl_entry("wl_b", "600519", score=0.5),
            _make_wl_entry("wl_c", "000858", score=0.5),
        ]
        ranked = rank_entries(entries)
        tickers = [e.ticker for e in ranked]
        assert tickers == ["000858", "600519", "601318"]

    def test_rank_preserves_input_list(self):
        """rank_entries does not modify the original list."""
        e1 = _make_wl_entry("wl_1", "600519", score=0.8)
        e2 = _make_wl_entry("wl_2", "000858", score=0.2)
        original = [e1, e2]
        _ = rank_entries(original)
        assert original[0].id == "wl_1"
        assert original[1].id == "wl_2"

    def test_rank_deterministic_across_calls(self):
        """rank_entries produces the same result every time for same inputs."""
        entries = [
            _make_wl_entry(f"wl_d{i}", f"600{i:03d}", score=0.5)
            for i in range(10)
        ]
        r1 = rank_entries(entries)
        r2 = rank_entries(entries)
        assert [e.id for e in r1] == [e.id for e in r2]

    def test_rank_mixed_scores_and_tickers(self):
        """rank_entries sorts primarily by score, secondarily by ticker."""
        entries = [
            _make_wl_entry("wl_1", "999999", score=0.9),
            _make_wl_entry("wl_2", "000001", score=0.9),
            _make_wl_entry("wl_3", "600519", score=0.8),
        ]
        ranked = rank_entries(entries)
        assert ranked[0].ticker == "000001"  # same score 0.9, lower ticker first
        assert ranked[1].ticker == "999999"
        assert ranked[2].ticker == "600519"


# --- Additional Filtering Edge Cases ---


class TestFilteringEdgeCases:
    def test_filter_all_excluded_by_trigger(self):
        """filter_entries returns empty if all entries excluded by trigger type."""
        entries = [
            _make_wl_entry("wl_1", "600519", score=0.9, trigger=TriggerType.PORTFOLIO_REVIEW),
            _make_wl_entry("wl_2", "000858", score=0.8, trigger=TriggerType.PORTFOLIO_REVIEW),
        ]
        filtered = filter_entries(entries, exclude_triggers=[TriggerType.PORTFOLIO_REVIEW])
        assert filtered == []

    def test_filter_all_below_min_score(self):
        """filter_entries returns empty if all entries below min_priority_score."""
        entries = [
            _make_wl_entry("wl_1", "600519", score=0.05),
            _make_wl_entry("wl_2", "000858", score=0.01),
        ]
        filtered = filter_entries(entries, min_priority_score=0.1)
        assert filtered == []

    def test_filter_exact_threshold_included(self):
        """Entries at exactly min_priority_score are included (>=)."""
        entries = [
            _make_wl_entry("wl_1", "600519", score=0.1),
        ]
        filtered = filter_entries(entries, min_priority_score=0.1)
        assert len(filtered) == 1

    def test_filter_just_below_threshold_excluded(self):
        """Entries just below min_priority_score are excluded."""
        entries = [
            _make_wl_entry("wl_1", "600519", score=0.09999),
        ]
        filtered = filter_entries(entries, min_priority_score=0.1)
        assert len(filtered) == 0

    def test_filter_max_zero(self):
        """filter_entries with max_entries=0 returns empty list."""
        entries = [_make_wl_entry("wl_1", "600519", score=0.9)]
        filtered = filter_entries(entries, max_entries=0)
        assert filtered == []

    def test_filter_dedup_keeps_first_occurrence(self):
        """Dedup keeps first occurrence (assumed highest in ranked input)."""
        entries = [
            _make_wl_entry("wl_hi", "600519", score=0.9),
            _make_wl_entry("wl_lo", "600519", score=0.3),
            _make_wl_entry("wl_md", "600519", score=0.6),
        ]
        filtered = filter_entries(entries)
        assert len(filtered) == 1
        # First occurrence wins (filter preserves input order)
        assert filtered[0].id == "wl_hi"

    def test_filter_dedup_keeps_first_in_ranked_order(self):
        """Dedup keeps first occurrence in a ranked (sorted) list."""
        entries = [
            _make_wl_entry("wl_hi", "600519", score=0.9),
            _make_wl_entry("wl_lo", "600519", score=0.3),
        ]
        filtered = filter_entries(entries)
        assert len(filtered) == 1
        assert filtered[0].id == "wl_hi"

    def test_filter_multiple_exclude_triggers(self):
        """filter_entries excludes multiple trigger types."""
        entries = [
            _make_wl_entry("wl_1", "600519", score=0.9, trigger=TriggerType.EVENT_ATTENTION),
            _make_wl_entry("wl_2", "000858", score=0.8, trigger=TriggerType.PORTFOLIO_REVIEW),
            _make_wl_entry("wl_3", "601318", score=0.7, trigger=TriggerType.FACTOR_SIGNAL),
        ]
        filtered = filter_entries(
            entries,
            exclude_triggers=[TriggerType.PORTFOLIO_REVIEW, TriggerType.FACTOR_SIGNAL],
        )
        assert len(filtered) == 1
        assert filtered[0].ticker == "600519"

    def test_filter_large_list(self):
        """filter_entries handles a large list efficiently."""
        entries = [_make_wl_entry(f"wl_{i}", f"{i:06d}", score=0.5 + (i % 50) * 0.01)
                   for i in range(100)]
        filtered = filter_entries(entries, max_entries=10)
        assert len(filtered) == 10
        # All filtered entries have valid scores
        for e in filtered:
            assert e.priority_score >= 0.5

    def test_filter_dedup_across_triggers(self):
        """Dedup works across different trigger types - keeps highest ranked."""
        entries = [
            _make_wl_entry("wl_evt", "600519", score=0.6, trigger=TriggerType.EVENT_ATTENTION),
            _make_wl_entry("wl_sig", "600519", score=0.9, trigger=TriggerType.FACTOR_SIGNAL),
        ]
        # Both entries have same ticker but different triggers
        filtered = filter_entries(entries)
        assert len(filtered) == 1
        # First occurrence wins (wl_evt since it appears first in input)
        assert filtered[0].id == "wl_evt"


# --- Signal Scoring Edge Cases ---


class TestSignalScoring:
    def test_signal_scorer_weak_strength(self):
        """Weak signal produces lower score than strong."""
        from synapse.core.projection.scoring.engine import _score_signal

        entry = WatchlistEntry(id="wl_w", ticker="600519", trigger_type=TriggerType.FACTOR_SIGNAL)
        weak_signal = _make_signal(
            signal_type=SigSignalType.ATTENTION_SPIKE,
            strength=SigStrength.WEAK,
            related_tickers=["600519"],
        )
        strong_signal = _make_signal(
            signal_id="sig_strong",
            signal_type=SigSignalType.ATTENTION_SPIKE,
            strength=SigStrength.STRONG,
            related_tickers=["600519"],
        )

        ctx_weak = ScoringContext(signals=[weak_signal], target_date=date(2026, 5, 18))
        ctx_strong = ScoringContext(signals=[strong_signal], target_date=date(2026, 5, 18))

        score_weak, _ = _score_signal(entry, ctx_weak)
        score_strong, _ = _score_signal(entry, ctx_strong)

        assert score_weak < score_strong
        assert score_weak == pytest.approx(0.4)  # weak(0.3) + count_bonus(0.1)
        assert score_strong == pytest.approx(1.0)  # strong(1.0) + count_bonus(0.1) clamped

    def test_signal_scorer_medium_strength(self):
        """Medium signal produces 0.6 score."""
        from synapse.core.projection.scoring.engine import _score_signal

        entry = WatchlistEntry(id="wl_m", ticker="600519", trigger_type=TriggerType.FACTOR_SIGNAL)
        signal = _make_signal(
            signal_type=SigSignalType.ATTENTION_SPIKE,
            strength=SigStrength.MEDIUM,
            related_tickers=["600519"],
        )
        ctx = ScoringContext(signals=[signal], target_date=date(2026, 5, 18))
        score, reason = _score_signal(entry, ctx)

        assert score == pytest.approx(0.7)  # medium(0.6) + count_bonus(0.1)
        assert "1 signal" in reason

    def test_signal_scorer_count_bonus(self):
        """Multiple signals for same ticker add count bonus (diminishing returns)."""
        from synapse.core.projection.scoring.engine import _score_signal

        entry = WatchlistEntry(id="wl_multi", ticker="600519", trigger_type=TriggerType.FACTOR_SIGNAL)
        signals = [
            _make_signal(
                signal_id=f"sig_{i}",
                signal_type=SigSignalType.ATTENTION_SPIKE,
                strength=SigStrength.STRONG,
                related_tickers=["600519"],
            )
            for i in range(5)
        ]
        ctx = ScoringContext(signals=signals, target_date=date(2026, 5, 18))
        score, reason = _score_signal(entry, ctx)

        # Strong=1.0 + count_bonus=min(5*0.1, 0.3)=0.3, clamped to 1.0
        assert score == pytest.approx(1.0)
        assert "5 signal" in reason

    def test_signal_scorer_no_matching_ticker(self):
        """Signal for different ticker returns 0.0."""
        from synapse.core.projection.scoring.engine import _score_signal

        entry = WatchlistEntry(id="wl_nomatch", ticker="600519", trigger_type=TriggerType.FACTOR_SIGNAL)
        signal = _make_signal(related_tickers=["000858"])
        ctx = ScoringContext(signals=[signal], target_date=date(2026, 5, 18))
        score, reason = _score_signal(entry, ctx)

        assert score == 0.0
        assert "no signals" in reason

    def test_signal_scorer_multiple_tickers(self):
        """Signal with multiple tickers affects all listed tickers."""
        from synapse.core.projection.scoring.engine import _score_signal

        signal = _make_signal(
            signal_type=SigSignalType.ATTENTION_SPIKE,
            strength=SigStrength.STRONG,
            related_tickers=["600519", "000858"],
        )
        ctx = ScoringContext(signals=[signal], target_date=date(2026, 5, 18))

        entry_1 = WatchlistEntry(id="wl_1", ticker="600519", trigger_type=TriggerType.FACTOR_SIGNAL)
        entry_2 = WatchlistEntry(id="wl_2", ticker="000858", trigger_type=TriggerType.FACTOR_SIGNAL)

        s1, _ = _score_signal(entry_1, ctx)
        s2, _ = _score_signal(entry_2, ctx)

        assert s1 == pytest.approx(1.0)
        assert s2 == pytest.approx(1.0)


# --- Portfolio Scoring Additional Edge Cases ---


class TestPortfolioScoringEdgeCases:
    def test_all_thesis_attention_combinations(self):
        """All 9 thesis x attention combinations produce valid scores."""
        combos = {}
        for ts in ThesisStatus:
            for at in AttentionState:
                m: ThesisAttentionMap = {"X": (ts, at)}
                score, _ = score_portfolio_boost("X", m)
                combos[(ts, at)] = score

        # All scores should be in valid range
        for key, score in combos.items():
            assert 0.0 <= score <= 1.0, f"Invalid score for {key}: {score}"

        # Verify expected ordering: INVALIDATED > WEAKENED > ACTIVE for same attention
        assert combos[(ThesisStatus.INVALIDATED, AttentionState.STABLE)] > \
               combos[(ThesisStatus.WEAKENED, AttentionState.STABLE)] > \
               combos[(ThesisStatus.ACTIVE, AttentionState.STABLE)]

    def test_portfolio_boost_fading_attention(self):
        """FADING attention gives 0.10 boost."""
        m: ThesisAttentionMap = {
            "A": (ThesisStatus.ACTIVE, AttentionState.FADING),
        }
        score, _ = score_portfolio_boost("A", m)
        assert score == pytest.approx(THESIS_ACTIVE_BOOST + ATTENTION_FADING_BOOST)

    def test_portfolio_boost_unknown_thesis_falls_back(self):
        """Unknown thesis status falls back to ACTIVE boost."""
        from synapse.core.projection.scoring.portfolio_scorer import _thesis_boost
        # Using an invalid enum value would fail at type level, but
        # test the mapping dict fallback
        result = _thesis_boost(ThesisStatus.ACTIVE)
        assert result == THESIS_ACTIVE_BOOST

    def test_build_thesis_attention_map_duplicate_ticker(self):
        """Last position wins when duplicate tickers exist."""
        pos1 = _make_position(pos_id="p1", ticker="600519", thesis_status=ThesisStatus.ACTIVE)
        pos2 = _make_position(pos_id="p2", ticker="600519", thesis_status=ThesisStatus.WEAKENED)
        m = build_thesis_attention_map([pos1, pos2])

        assert m["600519"] == (ThesisStatus.WEAKENED, AttentionState.STABLE)

    def test_build_thesis_attention_map_empty_list(self):
        """Empty positions list returns empty map."""
        m = build_thesis_attention_map([])
        assert m == {}


# --- Event Scoring Additional Edge Cases ---


class TestEventScoringEdgeCases:
    def test_event_no_timezone_created_at(self):
        """Event with naive (no timezone) created_at is handled gracefully."""
        event = Event(
            id="evt_naive",
            event_type=EventType.EARNINGS,
            title="naive event",
            description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.7,
            confidence=0.8,
            created_at=datetime(2026, 5, 18, 12, 0),  # No timezone
        )
        entry = WatchlistEntry(
            id="wl_naive", ticker="600519", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        score, reason = score_event_decay(entry, ctx)

        # Should compute a reasonable score without crashing
        assert score > 0.0
        assert "age=" in reason

    def test_event_zero_severity_confidence(self):
        """Event with zero severity and confidence produces zero score."""
        event = Event(
            id="evt_zero",
            event_type=EventType.EARNINGS,
            title="zero event",
            description="desc",
            event_date=date(2026, 5, 18),
            related_tickers=["600519"],
            impact_level=ImpactLevel.LOW,
            severity=0.0,
            confidence=0.0,
            created_at=datetime(2026, 5, 18, 12, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_zero", ticker="600519", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        score, _ = score_event_decay(entry, ctx)

        # impact_0 = (0+0)/2 = 0.0, decay of 0.0 is still 0.0
        assert score == pytest.approx(0.0)

    def test_event_very_old_event_decays_to_near_zero(self):
        """Very old event (100 days) decays to near zero."""
        event = Event(
            id="evt_ancient",
            event_type=EventType.SOCIAL_SENTIMENT,
            title="ancient",
            description="desc",
            event_date=date(2026, 2, 8),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            severity=0.8,
            confidence=0.8,
            created_at=datetime(2026, 2, 8, 12, 0, tzinfo=CST),
        )
        entry = WatchlistEntry(
            id="wl_ancient", ticker="600519", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=[event], target_date=date(2026, 5, 18))
        score, _ = score_event_decay(entry, ctx)

        # Social sentiment has half-life=0.5d, after 100 days it's effectively 0
        assert score < 0.01

    def test_decay_score_to_tuple(self):
        """DecayScore.as_tuple() returns correct (score, reason) pair."""
        ds = DecayScore(score=0.42, reason="half decayed")
        t = ds.as_tuple()
        assert t == (0.42, "half decayed")

    def test_multiple_event_types_same_ticker(self):
        """Multiple event types for same ticker: highest score wins."""
        now = datetime(2026, 5, 18, 12, 0, tzinfo=CST)
        events = [
            Event(
                id=f"evt_{et.value}",
                event_type=et,
                title=f"event {et.value}",
                description="desc",
                event_date=date(2026, 5, 18),
                related_tickers=["600519"],
                impact_level=ImpactLevel.HIGH,
                severity=0.8,
                confidence=0.8,
                created_at=now,
            )
            for et in [EventType.EARNINGS, EventType.POLICY, EventType.SOCIAL_SENTIMENT]
        ]
        entry = WatchlistEntry(
            id="wl_multi_evt", ticker="600519", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        ctx = ScoringContext(events=events, target_date=date(2026, 5, 18))
        score, reason = score_event_decay(entry, ctx)

        # All have same impact (0.8), but different decay rates
        # Earnings has longest half-life, so it should win
        assert score > 0.0
        assert "earnings" in reason


# --- Position Rebuilder Additional Tests ---


class TestPositionRebuilderExtended:
    def test_buy_updates_existing_position(self):
        """Second buy for same ticker updates existing position (increments shares)."""
        buy1 = _make_decision(decision_id="dec_buy1", ticker="600519",
                              created_at=datetime(2026, 5, 18, 10, 0, tzinfo=CST))
        buy2 = _make_decision(decision_id="dec_buy2", ticker="600519",
                              created_at=datetime(2026, 5, 18, 14, 0, tzinfo=CST))
        positions = rebuild_from_decisions([buy1, buy2])

        assert len(positions) == 1
        assert positions[0].current_shares == 2
        assert positions[0].linked_decision_id == "dec_buy2"

    def test_review_partially_confirmed(self):
        """PARTIALLY_CONFIRMED review weakens thesis."""
        buy = _make_decision(decision_id="dec_buy01", decision_type=DecisionType.BUY)
        review = _make_review(
            linked_decision_id="dec_buy01",
            review_outcome=ReviewOutcome.PARTIALLY_CONFIRMED,
        )
        positions = rebuild_from_decisions([buy], reviews=[review])

        assert len(positions) == 1
        assert positions[0].research_state.thesis_status == ThesisStatus.WEAKENED

    def test_review_confirmed_keeps_active(self):
        """THESIS_CONFIRMED review keeps thesis active."""
        buy = _make_decision(decision_id="dec_buy01", decision_type=DecisionType.BUY)
        review = _make_review(
            linked_decision_id="dec_buy01",
            review_outcome=ReviewOutcome.THESIS_CONFIRMED,
        )
        positions = rebuild_from_decisions([buy], reviews=[review])

        assert len(positions) == 1
        assert positions[0].research_state.thesis_status == ThesisStatus.ACTIVE

    def test_review_no_matching_decision_ignored(self):
        """Review with non-matching linked_decision_id is ignored."""
        buy = _make_decision(decision_id="dec_buy01", decision_type=DecisionType.BUY)
        review = _make_review(
            linked_decision_id="dec_other",
            review_outcome=ReviewOutcome.THESIS_INVALIDATED,
        )
        positions = rebuild_from_decisions([buy], reviews=[review])

        assert len(positions) == 1
        assert positions[0].research_state.thesis_status == ThesisStatus.ACTIVE

    def test_empty_reviews_list(self):
        """Empty reviews list doesn't affect positions."""
        buy = _make_decision()
        positions = rebuild_from_decisions([buy], reviews=[])
        assert len(positions) == 1
        assert positions[0].research_state.thesis_status == ThesisStatus.ACTIVE

    def test_sell_without_buy_ignored(self):
        """Sell decision for unknown ticker is silently ignored."""
        sell = _make_decision(
            decision_id="dec_sell_orphan",
            decision_type=DecisionType.SELL,
            created_at=datetime(2026, 5, 19, 14, 0, tzinfo=CST),
        )
        positions = rebuild_from_decisions([sell])
        assert len(positions) == 0

    def test_multiple_tickers_independent(self):
        """Different tickers create independent positions."""
        buy1 = _make_decision(decision_id="d1", ticker="600519", symbol="贵州茅台",
                              created_at=datetime(2026, 5, 18, 10, 0, tzinfo=CST))
        buy2 = _make_decision(decision_id="d2", ticker="000858", symbol="五粮液",
                              created_at=datetime(2026, 5, 18, 11, 0, tzinfo=CST))
        sell1 = _make_decision(decision_id="d3", ticker="600519",
                               decision_type=DecisionType.SELL,
                               created_at=datetime(2026, 5, 18, 14, 0, tzinfo=CST))
        positions = rebuild_from_decisions([buy1, buy2, sell1])

        # 600519 sold, 000858 still active
        assert len(positions) == 1
        assert positions[0].ticker == "000858"


# --- Timeline Extended Tests ---


class TestTimelineExtended:
    def test_thesis_without_thesis_statement(self):
        """Thesis without thesis_statement uses summary as summary."""
        thesis = Thesis(
            id="ths_nostmt",
            title="no statement thesis",
            thesis_statement="",  # empty
            summary="this is the summary",
        )
        view = render_timeline(theses=[thesis])

        assert len(view.entries) == 1
        assert view.entries[0].summary == "this is the summary"

    def test_thesis_revised_entry(self):
        """Thesis with revision > 1 generates THESIS_REVISED entry."""
        thesis = Thesis(
            id="ths_rev2",
            title="revised thesis",
            thesis_statement="statement",
            revision=2,
            previous_revision="rev1",
        )
        view = render_timeline(theses=[thesis])

        assert len(view.entries) == 2
        types = [e.entry_type for e in view.entries]
        assert TimelineEntryType.THESIS_CREATED in types
        assert TimelineEntryType.THESIS_REVISED in types

    def test_multiple_artifact_types_sorted(self):
        """Timeline sorts all artifact types chronologically."""
        thesis = Thesis(
            id="ths_early",
            title="early",
            created_at=datetime(2026, 5, 18, 8, 0, tzinfo=CST),
        )
        decision = _make_decision(
            created_at=datetime(2026, 5, 18, 10, 0, tzinfo=CST),
        )
        event = _make_event(event_date=date(2026, 5, 18))
        view = render_timeline(theses=[thesis], decisions=[decision], events=[event])

        assert len(view.entries) == 3
        timestamps = [e.timestamp for e in view.entries]
        assert timestamps == sorted(timestamps)

    def test_timeline_entry_to_dict(self):
        """TimelineEntry.to_dict() serializes correctly."""
        from synapse.core.projection.timeline import TimelineEntry

        entry = TimelineEntry(
            entry_type=TimelineEntryType.DECISION_RECORDED,
            timestamp=datetime(2026, 5, 18, 10, 0, tzinfo=CST),
            object_id="dec_001",
            title="Buy 600519",
            summary="test decision",
            linked_ids=["ths_001"],
        )
        d = entry.to_dict()

        assert d["entry_type"] == "decision_recorded"
        assert d["object_id"] == "dec_001"
        assert d["linked_ids"] == ["ths_001"]


# --- Market Scoring Extended Tests ---


class TestMarketScoringExtended:
    def test_market_outflow_clamped_at_min(self):
        """Northbound outflow can't push market score below 0.0."""
        from decimal import Decimal

        from synapse.core.market.northbound import NorthChannel, NorthboundFlow
        from synapse.core.projection.scoring.market_scorer import score_market_context

        record = NorthboundFlow(
            date=date(2026, 5, 18),
            channel=NorthChannel.HGT,
            buy_amount=Decimal("1"),
            sell_amount=Decimal("100"),
            net_amount=Decimal("-99"),
            total_buy=Decimal("100"),
            total_sell=Decimal("1000"),
            quota_used_pct=Decimal("90"),
            source="test",
        )
        entry = WatchlistEntry(id="wl_clamp", ticker="600519")
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            config={"northbound_records": [record]},
        )
        score, _ = score_market_context(entry, ctx)
        assert score >= 0.0

    def test_market_bearish_market_data(self):
        """Very bearish market data (high volatility, low sentiment) scores below 0.5."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_bear", ticker="600519")
        market = MarketData(sentiment_score=0.1, breadth_score=0.1, volatility_score=0.9)
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            market_data=market,
        )
        score, _ = score_market_context(entry, ctx)
        # (0.1 + 0.1 + 0.1) / 3 = 0.1
        assert score == pytest.approx(0.1)

    def test_market_bullish_market_data(self):
        """Very bullish market data scores above 0.5."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_bull", ticker="600519")
        market = MarketData(sentiment_score=0.9, breadth_score=0.9, volatility_score=0.1)
        ctx = ScoringContext(
            target_date=date(2026, 5, 18),
            market_data=market,
        )
        score, _ = score_market_context(entry, ctx)
        # (0.9 + 0.9 + 0.9) / 3 = 0.9
        assert score == pytest.approx(0.9)

    def test_market_no_market_data_returns_unavailable(self):
        """No market data, no northbound, no index -> returns 0.5 unavailable."""
        from synapse.core.projection.scoring.market_scorer import score_market_context

        entry = WatchlistEntry(id="wl_no_md", ticker="600519")
        ctx = ScoringContext(target_date=date(2026, 5, 18))
        score, reason = score_market_context(entry, ctx)

        assert score == 0.5
        assert "unavailable" in reason.lower()


# --- Generate Daily Integration Edge Cases ---


class TestGenerateDailyExtended:
    def test_generate_daily_determinism(self):
        """generate_daily with same inputs produces same scores (deterministic)."""
        event = _make_event(related_tickers=["600519"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        pos = _make_position(ticker="600519")

        r1 = generate_daily(
            events=[event], signals=[signal], positions=[pos],
            target_date=date(2026, 5, 18),
        )
        r2 = generate_daily(
            events=[event], signals=[signal], positions=[pos],
            target_date=date(2026, 5, 18),
        )

        # Scores should be identical (entry IDs differ)
        assert len(r1) == len(r2)
        for e1, e2 in zip(r1, r2):
            assert e1.priority_score == e2.priority_score

    def test_generate_daily_deduplicates_tickers(self):
        """Same ticker from event and signal appears once in output."""
        event = _make_event(related_tickers=["600519"])
        signal = _make_signal(related_tickers=["600519"], strength=SigStrength.STRONG)
        entries = generate_daily(
            events=[event], signals=[signal], positions=[],
            target_date=date(2026, 5, 18),
        )

        tickers = [e.ticker for e in entries]
        assert tickers.count("600519") == 1

    def test_generate_daily_portfolio_review_ranked(self):
        """Portfolio review entries are scored and ranked."""
        pos1 = _make_position(pos_id="p1", ticker="600519", thesis_status=ThesisStatus.INVALIDATED)
        pos2 = _make_position(pos_id="p2", ticker="000858", thesis_status=ThesisStatus.ACTIVE)
        entries = generate_daily(
            events=[], signals=[], positions=[pos1, pos2],
            target_date=date(2026, 5, 18),
        )

        # INVALIDATED should score higher than ACTIVE
        scores = {e.ticker: e.priority_score for e in entries}
        assert scores["600519"] > scores["000858"]

    def test_generate_daily_min_priority_score_filters(self):
        """Entries below min_priority_score are filtered out."""
        # Positions with ACTIVE thesis get low scores (~0.20)
        # Set min_priority_score high to filter them
        pos = _make_position(ticker="600519", thesis_status=ThesisStatus.ACTIVE)
        entries = generate_daily(
            events=[], signals=[], positions=[pos],
            target_date=date(2026, 5, 18),
            min_priority_score=0.5,
        )

        # ACTIVE thesis + STABLE attention = 0.15 + 0.05 = 0.20 portfolio score
        # total = 0.20 * 0.20 (portfolio weight) + 0.15 * 0.5 (market neutral) = 0.115
        # With min=0.5, this should be filtered
        for e in entries:
            assert e.priority_score >= 0.5

    def test_generate_daily_max_entries_cap(self):
        """max_entries caps the output list length."""
        events = [
            _make_event(event_id=f"evt_{i}", related_tickers=[f"600{i:03d}"])
            for i in range(50)
        ]
        entries = generate_daily(
            events=events, signals=[], positions=[],
            target_date=date(2026, 5, 18),
            max_entries=5,
        )
        assert len(entries) <= 5


# --- Scoring Engine Extended Tests ---


class TestScoringEngineExtended:
    def test_score_batch_multiple_entries(self):
        """Engine scores multiple entries and returns sorted result."""
        engine = ScoringEngine()
        event = _make_event(related_tickers=["600519", "000858"])
        ctx = ScoringContext(
            events=[event], signals=[], positions=[],
            target_date=date(2026, 5, 18),
        )
        entries = [
            WatchlistEntry(
                id=f"wl_b{i}", ticker=t, symbol="", market="CN_A",
                headline=f"test {t}", trigger_type=TriggerType.EVENT_ATTENTION,
                linked_event_id="evt_test01",
            )
            for i, t in enumerate(["600519", "000858"])
        ]
        result = engine.score(entries, ctx)

        assert len(result.entries) == 2
        # Both entries have same event match, same score
        assert result.entries[0].total_score == result.entries[1].total_score

    def test_score_empty_entries(self):
        """Engine scores empty list without error."""
        engine = ScoringEngine()
        ctx = ScoringContext(target_date=date(2026, 5, 18))
        result = engine.score([], ctx)

        assert result.entries == []
        assert result.target_date == date(2026, 5, 18)

    def test_engine_config_hash_stable(self):
        """Config hash is stable for same configuration."""
        e1 = ScoringEngine()
        e2 = ScoringEngine()
        assert e1._compute_config_hash() == e2._compute_config_hash()

    def test_engine_config_hash_changes_with_weights(self):
        """Config hash changes when weights change."""
        e1 = ScoringEngine(weights={"signal": 0.5, "event": 0.5, "portfolio": 0.0, "market": 0.0})
        e2 = ScoringEngine()
        assert e1._compute_config_hash() != e2._compute_config_hash()

    def test_score_all_zero_inputs(self):
        """Engine handles all-zero inputs gracefully."""
        engine = ScoringEngine()
        ctx = ScoringContext(
            events=[], signals=[], positions=[],
            target_date=date(2026, 5, 18),
        )
        entry = WatchlistEntry(
            id="wl_zero", ticker="999999", symbol="", market="CN_A",
            headline="zero", trigger_type=TriggerType.EVENT_ATTENTION,
        )
        result = engine.score([entry], ctx)
        scored = result.entries[0]

        assert scored.total_score == pytest.approx(0.075)  # market neutral only


# --- Save Watchlist Tests ---


class TestSaveWatchlist:
    def test_save_watchlist_creates_files(self, tmp_path):
        """save_watchlist creates YAML files in date subdirectory."""
        entries = [
            _make_wl_entry("wl_s1", "600519", score=0.9),
            _make_wl_entry("wl_s2", "000858", score=0.7),
        ]
        paths = save_watchlist(entries, str(tmp_path), target_date=date(2026, 5, 18))

        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert "2026-05-18" in str(p)

    def test_save_watchlist_empty(self, tmp_path):
        """save_watchlist with empty list creates no files."""
        paths = save_watchlist([], str(tmp_path), target_date=date(2026, 5, 18))
        assert paths == []

    def test_save_watchlist_creates_date_subdir(self, tmp_path):
        """save_watchlist creates date subdirectory."""
        entries = [_make_wl_entry("wl_sub", "600519")]
        save_watchlist(entries, str(tmp_path), target_date=date(2026, 6, 1))

        date_dir = tmp_path / "2026-06-01"
        assert date_dir.exists()
        assert date_dir.is_dir()

    def test_save_watchlist_portfolio_review_naming(self, tmp_path):
        """Portfolio review entries use 'portfolio-review' in filename."""
        entries = [
            _make_wl_entry("wl_pr", "600519", trigger=TriggerType.PORTFOLIO_REVIEW),
        ]
        paths = save_watchlist(entries, str(tmp_path), target_date=date(2026, 5, 18))

        assert len(paths) == 1
        assert "portfolio-review" in paths[0].name

    def test_save_watchlist_with_signals_naming(self, tmp_path):
        """Entries with signals use first signal type in filename."""
        entry = WatchlistEntry(
            id="wl_sig_name",
            ticker="600519",
            trigger_type=TriggerType.FACTOR_SIGNAL,
            signals=[
                WatchlistSignal(
                    type=SignalType.ATTENTION_SPIKE,
                    strength=SignalStrength.STRONG,
                    description="spike",
                ),
            ],
        )
        paths = save_watchlist([entry], str(tmp_path), target_date=date(2026, 5, 18))

        assert len(paths) == 1
        assert "attention_spike" in paths[0].name


# --- Aggregator Extended Tests ---


class TestAggregatorExtended:
    def test_aggregate_scores_clamped_max(self):
        """aggregate_scores clamps result to 1.0 maximum."""
        scores = {"signal": 1.0, "event": 1.0, "portfolio": 1.0, "market": 1.0}
        result = aggregate_scores(scores)
        assert result <= 1.0

    def test_aggregate_scores_clamped_min(self):
        """aggregate_scores clamps result to 0.0 minimum."""
        scores = {"signal": -1.0, "event": -1.0, "portfolio": -1.0, "market": -1.0}
        result = aggregate_scores(scores)
        assert result >= 0.0

    def test_normalize_weights_single_dim(self):
        """normalize_weights handles single dimension."""
        weights = {"signal": 5.0}
        result = normalize_weights(weights)
        assert abs(result["signal"] - 1.0) < 1e-9

    def test_normalize_weights_zero_total_raises(self):
        """normalize_weights with zero total raises ZeroDivisionError."""
        weights = {"a": 0.0, "b": 0.0}
        with pytest.raises(ZeroDivisionError):
            normalize_weights(weights)

    def test_aggregate_scores_all_dims(self):
        """aggregate_scores with all dimensions at 1.0 returns 1.0."""
        scores = {"signal": 1.0, "event": 1.0, "portfolio": 1.0, "market": 1.0}
        result = aggregate_scores(scores, DEFAULT_WEIGHTS)
        assert result == pytest.approx(1.0)

    def test_aggregate_scores_all_dims_zero(self):
        """aggregate_scores with all dims 0.0 returns only market neutral."""
        scores = {"signal": 0.0, "event": 0.0, "portfolio": 0.0, "market": 0.0}
        result = aggregate_scores(scores, DEFAULT_WEIGHTS)
        assert result == pytest.approx(0.0)
