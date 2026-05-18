"""Tests for Research Object Schemas (TASK-003)."""

from datetime import date, datetime, timezone, timedelta

import pytest

from synapse.core.schemas.base import BaseSchema, MarketContext, ObjectStatus, SourceType, CreatorType
from synapse.core.schemas.watchlist import (
    WatchlistEntry, WatchlistSignal, TriggerType, SignalType, SignalStrength,
)
from synapse.core.schemas.thesis import (
    Thesis, Confidence, RelatedSecurity, Evidence, Relevance,
)
from synapse.core.schemas.decision import (
    Decision, DecisionType, TimeHorizon, AttentionOrigin, DecisionSignal,
)
from synapse.core.schemas.review import (
    Review, ReviewOutcome, SignalEvaluation, RiskEvaluation,
)
from synapse.core.schemas.position import (
    Position, ResearchState, ThesisStatus, AttentionState,
)
from synapse.core.schemas.signal import Signal, SignalType as SigSignalType, SignalStrength as SigStrength
from synapse.core.schemas.risk import Risk, RiskType, Severity
from synapse.core.schemas.event import Event, EventType, ImpactLevel
from synapse.core.schemas.topic import ResearchTopic
from synapse.analytics.tracking_models import DecaySnapshot, MaterializationSnapshot, OutcomeRecord
from synapse.core.temporal import CST


# --- MarketContext Tests ---


class TestMarketContext:
    def test_create(self):
        mc = MarketContext(research_date=date(2026, 5, 18), market_date=date(2026, 5, 18))
        assert mc.research_date == date(2026, 5, 18)
        assert mc.market_date == date(2026, 5, 18)
        assert mc.trading_session.value == "normal"

    def test_to_dict(self):
        mc = MarketContext(research_date=date(2026, 5, 18), market_date=date(2026, 5, 18))
        d = mc.to_dict()
        assert d["research_date"] == "2026-05-18"
        assert d["market_date"] == "2026-05-18"
        assert d["trading_session"] == "normal"

    def test_from_dict(self):
        mc = MarketContext.from_dict({
            "research_date": "2026-05-18",
            "market_date": "2026-05-18",
            "trading_session": "normal",
        })
        assert mc.research_date == date(2026, 5, 18)
        assert mc.market_date == date(2026, 5, 18)


# --- BaseSchema Tests ---


class TestBaseSchema:
    def test_create(self):
        bs = BaseSchema(id="test_123")
        assert bs.id == "test_123"
        assert bs.schema_version == "1.0"
        assert bs.status == ObjectStatus.ACTIVE
        assert bs.created_by == CreatorType.HUMAN

    def test_to_dict(self):
        bs = BaseSchema(id="test_123")
        d = bs.to_dict()
        assert d["id"] == "test_123"
        assert d["schema_version"] == "1.0"
        assert d["status"] == "active"
        assert "market_context" in d

    def test_base_from_dict(self):
        now = datetime.now(CST)
        d = {
            "id": "test_123",
            "schema_version": "1.0",
            "status": "active",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "source_type": "human_written",
            "created_by": "human",
            "market_context": {
                "research_date": "2026-05-18",
                "market_date": "2026-05-18",
                "trading_session": "normal",
            },
        }
        kwargs = BaseSchema.base_from_dict(d)
        assert kwargs["id"] == "test_123"
        assert kwargs["schema_version"] == "1.0"


# --- WatchlistEntry Tests ---


class TestWatchlistEntry:
    def test_create(self):
        wl = WatchlistEntry(id="wl_a1b2c3", ticker="600519", symbol="贵州茅台")
        assert wl.id == "wl_a1b2c3"
        assert wl.ticker == "600519"
        assert wl.action == "值得关注"

    def test_round_trip(self):
        wl = WatchlistEntry(
            id="wl_a1b2c3",
            ticker="600519",
            symbol="贵州茅台",
            market="CN_A",
            signals=[WatchlistSignal(type=SignalType.ATTENTION_SPIKE, strength=SignalStrength.STRONG)],
        )
        d = wl.to_dict()
        wl2 = WatchlistEntry.from_dict(d)
        assert wl2.id == "wl_a1b2c3"
        assert wl2.ticker == "600519"
        assert len(wl2.signals) == 1
        assert wl2.signals[0].type == SignalType.ATTENTION_SPIKE

    def test_signal_to_dict(self):
        s = WatchlistSignal(type=SignalType.SECTOR_RESONANCE, strength=SignalStrength.MEDIUM, description="test")
        d = s.to_dict()
        assert d["type"] == "sector_resonance"
        assert d["strength"] == "medium"


# --- Thesis Tests ---


class TestThesis:
    def test_create(self):
        th = Thesis(id="ths_7f8c91", title="消费恢复 Thesis")
        assert th.id == "ths_7f8c91"
        assert th.revision == 1
        assert th.confidence == Confidence.MEDIUM

    def test_round_trip(self):
        th = Thesis(
            id="ths_7f8c91",
            slug="consumer-recovery",
            title="消费恢复 Thesis",
            thesis_statement="中国消费市场恢复",
            related_securities=[
                RelatedSecurity(ticker="600519", symbol="贵州茅台", market="CN_A", relevance=Relevance.PRIMARY)
            ],
            evidence=[Evidence(type="market_data", description="涨幅12%")],
            confidence=Confidence.HIGH,
        )
        d = th.to_dict()
        th2 = Thesis.from_dict(d)
        assert th2.id == "ths_7f8c91"
        assert th2.slug == "consumer-recovery"
        assert len(th2.related_securities) == 1
        assert th2.related_securities[0].relevance == Relevance.PRIMARY
        assert th2.confidence == Confidence.HIGH
        assert len(th2.evidence) == 1

    def test_revision_chain(self):
        th = Thesis(id="ths_7f8c91", revision=2, parent_thesis_id="ths_old")
        d = th.to_dict()
        assert d["revision"] == 2
        assert d["parent_thesis_id"] == "ths_old"
        th2 = Thesis.from_dict(d)
        assert th2.revision == 2
        assert th2.parent_thesis_id == "ths_old"


# --- Decision Tests ---


class TestDecision:
    def test_create(self):
        dec = Decision(id="dec_b4c5d6", ticker="600519", decision_type=DecisionType.BUY)
        assert dec.id == "dec_b4c5d6"
        assert dec.decision_type == DecisionType.BUY

    def test_round_trip(self):
        dec = Decision(
            id="dec_b4c5d6",
            ticker="600519",
            symbol="贵州茅台",
            decision_type=DecisionType.BUY,
            thesis="消费恢复预期",
            key_risk="估值偏高",
            time_horizon=TimeHorizon.SHORT_TERM,
            signals=[DecisionSignal(linked_signal_id="sig_xxx", role="primary")],
        )
        d = dec.to_dict()
        dec2 = Decision.from_dict(d)
        assert dec2.id == "dec_b4c5d6"
        assert dec2.decision_type == DecisionType.BUY
        assert dec2.time_horizon == TimeHorizon.SHORT_TERM
        assert len(dec2.signals) == 1


# --- Review Tests ---


class TestReview:
    def test_create(self):
        rev = Review(id="rev_e7f8g9", linked_decision_id="dec_b4c5d6")
        assert rev.id == "rev_e7f8g9"
        assert rev.review_outcome == ReviewOutcome.THESIS_CONFIRMED

    def test_round_trip(self):
        rev = Review(
            id="rev_e7f8g9",
            linked_decision_id="dec_b4c5d6",
            linked_thesis_id="ths_7f8c91",
            review_outcome=ReviewOutcome.PARTIALLY_CONFIRMED,
            signal_evaluations=[SignalEvaluation(linked_signal_id="sig_xxx", was_accurate=True)],
            risk_evaluations=[RiskEvaluation(description="估值偏高", materialized=False)],
        )
        d = rev.to_dict()
        rev2 = Review.from_dict(d)
        assert rev2.id == "rev_e7f8g9"
        assert rev2.review_outcome == ReviewOutcome.PARTIALLY_CONFIRMED
        assert len(rev2.signal_evaluations) == 1
        assert rev2.signal_evaluations[0].was_accurate is True
        assert len(rev2.risk_evaluations) == 1
        assert rev2.risk_evaluations[0].materialized is False


# --- Position Tests ---


class TestPosition:
    def test_create(self):
        pos = Position(id="pos_h1i2j3", ticker="600519")
        assert pos.id == "pos_h1i2j3"
        assert pos.research_state.thesis_status == ThesisStatus.ACTIVE

    def test_round_trip(self):
        pos = Position(
            id="pos_h1i2j3",
            ticker="600519",
            symbol="贵州茅台",
            linked_thesis_id="ths_7f8c91",
            thesis_at_entry="消费恢复预期",
            entry_price=1800.0,
            current_shares=100,
            research_state=ResearchState(thesis_status=ThesisStatus.ACTIVE, attention_state=AttentionState.RISING),
            linked_watchlist_ids=["wl_a1b2c3"],
        )
        d = pos.to_dict()
        pos2 = Position.from_dict(d)
        assert pos2.id == "pos_h1i2j3"
        assert pos2.entry_price == 1800.0
        assert pos2.current_shares == 100
        assert pos2.research_state.thesis_status == ThesisStatus.ACTIVE
        assert pos2.research_state.attention_state == AttentionState.RISING
        assert pos2.linked_watchlist_ids == ["wl_a1b2c3"]


# --- Signal Tests ---


class TestSignal:
    def test_create(self):
        sig = Signal(id="sig_a1b2c3", signal_type=SigSignalType.ATTENTION_SPIKE)
        assert sig.id == "sig_a1b2c3"
        assert sig.decay_tracking is False

    def test_round_trip(self):
        sig = Signal(
            id="sig_a1b2c3",
            signal_type=SigSignalType.SECTOR_RESONANCE,
            strength=SigStrength.STRONG,
            description="板块联动放量",
            related_tickers=["600519", "000858"],
        )
        d = sig.to_dict()
        sig2 = Signal.from_dict(d)
        assert sig2.id == "sig_a1b2c3"
        assert sig2.signal_type == SigSignalType.SECTOR_RESONANCE
        assert sig2.related_tickers == ["600519", "000858"]


# --- Risk Tests ---


class TestRisk:
    def test_create(self):
        rsk = Risk(id="rsk_d4e5f6", risk_type=RiskType.VALUATION)
        assert rsk.id == "rsk_d4e5f6"
        assert rsk.severity == Severity.MEDIUM

    def test_round_trip(self):
        rsk = Risk(
            id="rsk_d4e5f6",
            risk_type=RiskType.MACRO,
            description="宏观经济风险",
            severity=Severity.HIGH,
            related_tickers=["600519"],
            linked_decision_id="dec_b4c5d6",
        )
        d = rsk.to_dict()
        rsk2 = Risk.from_dict(d)
        assert rsk2.id == "rsk_d4e5f6"
        assert rsk2.risk_type == RiskType.MACRO
        assert rsk2.severity == Severity.HIGH
        assert rsk2.linked_decision_id == "dec_b4c5d6"


# --- Event Tests ---


class TestEvent:
    def test_create(self):
        evt = Event(id="evt_k1l2m3", event_type=EventType.EARNINGS)
        assert evt.id == "evt_k1l2m3"
        assert evt.impact_level == ImpactLevel.UNKNOWN

    def test_round_trip(self):
        evt = Event(
            id="evt_k1l2m3",
            event_type=EventType.PRODUCT_LAUNCH,
            title="茅台新品发布会",
            description="贵州茅台发布新品",
            event_date=date(2026, 5, 18),
            related_tickers=["600519", "000858"],
            impact_level=ImpactLevel.HIGH,
        )
        d = evt.to_dict()
        evt2 = Event.from_dict(d)
        assert evt2.id == "evt_k1l2m3"
        assert evt2.event_type == EventType.PRODUCT_LAUNCH
        assert evt2.event_date == date(2026, 5, 18)
        assert evt2.impact_level == ImpactLevel.HIGH


# --- ResearchTopic Tests ---


class TestResearchTopic:
    def test_create(self):
        top = ResearchTopic(id="top_g7h8i9", slug="consume")
        assert top.id == "top_g7h8i9"
        assert top.slug == "consume"

    def test_round_trip(self):
        top = ResearchTopic(
            id="top_g7h8i9",
            slug="consume",
            name="中国消费",
            description="中国消费市场恢复研究",
            thesis_ids=["ths_7f8c91"],
        )
        d = top.to_dict()
        top2 = ResearchTopic.from_dict(d)
        assert top2.id == "top_g7h8i9"
        assert top2.name == "中国消费"
        assert top2.thesis_ids == ["ths_7f8c91"]


# --- Schema v2.0 Round-Trip Tests ---


class TestSignalV2Roundtrip:
    def test_signal_v2_with_decay_history(self):
        """Signal v2.0 with decay_history round-trips correctly."""
        sig = Signal(
            id="sig_v2_001",
            signal_type=SigSignalType.ATTENTION_SPIKE,
            strength=SigStrength.STRONG,
            description="Volume spike on 600519",
            related_tickers=["600519"],
            decay_tracking=True,
            decay_history=[
                DecaySnapshot(
                    signal_id="sig_v2_001",
                    decay_pct=0.15,
                    measured_at=datetime(2026, 5, 10, 9, 0, tzinfo=CST),
                    method="rolling_avg",
                ),
                DecaySnapshot(
                    signal_id="sig_v2_001",
                    decay_pct=0.30,
                    measured_at=datetime(2026, 5, 15, 9, 0, tzinfo=CST),
                    method="rolling_avg",
                ),
            ],
            first_seen_at=datetime(2026, 5, 1, 9, 0, tzinfo=CST),
            last_evaluated_at=datetime(2026, 5, 15, 9, 0, tzinfo=CST),
        )
        d = sig.to_dict()
        assert d["schema_version"] == "2.0"
        assert d["decay_tracking"] is True
        assert len(d["decay_history"]) == 2
        assert d["decay_history"][0]["decay_pct"] == 0.15
        assert d["first_seen_at"] is not None
        assert d["last_evaluated_at"] is not None

        sig2 = Signal.from_dict(d)
        assert sig2.id == "sig_v2_001"
        assert sig2.decay_tracking is True
        assert len(sig2.decay_history) == 2
        assert sig2.decay_history[0].decay_pct == 0.15
        assert sig2.decay_history[1].method == "rolling_avg"
        assert sig2.first_seen_at is not None
        assert sig2.last_evaluated_at is not None


class TestRiskV2Roundtrip:
    def test_risk_v2_with_materialization_history(self):
        """Risk v2.0 with materialization_history round-trips correctly."""
        rsk = Risk(
            id="rsk_v2_001",
            risk_type=RiskType.MACRO,
            description="Macro risk on CN market",
            severity=Severity.HIGH,
            related_tickers=["600519"],
            materialization_tracking=True,
            materialization_history=[
                MaterializationSnapshot(
                    risk_id="rsk_v2_001",
                    materialized=False,
                    detected_at=datetime(2026, 5, 5, 9, 0, tzinfo=CST),
                    source_review_id="rev_001",
                ),
                MaterializationSnapshot(
                    risk_id="rsk_v2_001",
                    materialized=True,
                    detected_at=datetime(2026, 5, 12, 9, 0, tzinfo=CST),
                    source_review_id="rev_002",
                ),
            ],
            first_flagged_at=datetime(2026, 5, 1, 9, 0, tzinfo=CST),
            resolved_at=datetime(2026, 5, 12, 9, 0, tzinfo=CST),
        )
        d = rsk.to_dict()
        assert d["schema_version"] == "2.0"
        assert d["materialization_tracking"] is True
        assert len(d["materialization_history"]) == 2
        assert d["materialization_history"][0]["materialized"] is False
        assert d["materialization_history"][1]["materialized"] is True
        assert d["first_flagged_at"] is not None
        assert d["resolved_at"] is not None

        rsk2 = Risk.from_dict(d)
        assert rsk2.id == "rsk_v2_001"
        assert rsk2.materialization_tracking is True
        assert len(rsk2.materialization_history) == 2
        assert rsk2.materialization_history[0].materialized is False
        assert rsk2.materialization_history[1].source_review_id == "rev_002"
        assert rsk2.first_flagged_at is not None
        assert rsk2.resolved_at is not None


class TestEventV2Roundtrip:
    def test_event_v2_with_outcome_tracking(self):
        """Event v2.0 with outcome_tracking round-trips correctly."""
        evt = Event(
            id="evt_v2_001",
            event_type=EventType.EARNINGS,
            title="Q1 Earnings",
            description="Q1 2026 earnings report",
            event_date=date(2026, 5, 10),
            related_tickers=["600519"],
            impact_level=ImpactLevel.HIGH,
            outcome_tracking=[
                OutcomeRecord(
                    event_id="evt_v2_001",
                    review_id="rev_001",
                    impact_assessment="positive",
                    calibrated_at=datetime(2026, 5, 15, 9, 0, tzinfo=CST),
                ),
            ],
            linked_review_ids=["rev_001"],
            calibration_score=0.85,
        )
        d = evt.to_dict()
        assert d["schema_version"] == "3.0"
        assert len(d["outcome_tracking"]) == 1
        assert d["outcome_tracking"][0]["review_id"] == "rev_001"
        assert d["linked_review_ids"] == ["rev_001"]
        assert d["calibration_score"] == 0.85

        evt2 = Event.from_dict(d)
        assert evt2.id == "evt_v2_001"
        assert evt2.event_type == EventType.EARNINGS
        assert len(evt2.outcome_tracking) == 1
        assert evt2.outcome_tracking[0].impact_assessment == "positive"
        assert evt2.linked_review_ids == ["rev_001"]
        assert evt2.calibration_score == 0.85
