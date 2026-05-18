"""Tests for Event Schema v3.0, EventContract, and PropagationEdge (IMPL-001)."""

from datetime import date, datetime

import pytest

from synapse.core.schemas.event import (
    Event,
    EventType,
    ImpactLevel,
    EventSourceType,
    PropagationState,
)
from synapse.core.schemas.event_contract import EventContract, SettlementStatus
from synapse.core.schemas.propagation_edge import PropagationEdge
from synapse.core.temporal import CST


# ---------------------------------------------------------------------------
# TestEventV3RoundTrip -- 3 tests
# ---------------------------------------------------------------------------


class TestEventV3RoundTrip:
    def test_v3_to_dict_contains_all_new_fields(self):
        evt = Event(
            id="evt_001",
            title="Test Event",
            event_type=EventType.SENTIMENT,
            severity=0.7,
            confidence=0.8,
            decay_rate=0.05,
            source=EventSourceType.AI_DETECTED,
            propagation_state=PropagationState.PROPAGATING,
            propagation_graph_id="pg_001",
            contract_id="ec_001",
        )
        d = evt.to_dict()
        assert d["schema_version"] == "3.0"
        assert d["severity"] == 0.7
        assert d["confidence"] == 0.8
        assert d["decay_rate"] == 0.05
        assert d["source"] == "ai_detected"
        assert d["propagation_state"] == "propagating"
        assert d["propagation_graph_id"] == "pg_001"
        assert d["contract_id"] == "ec_001"

    def test_v3_from_dict_restores_all_new_fields(self):
        data = {
            "id": "evt_002",
            "schema_version": "3.0",
            "status": "active",
            "created_at": "2026-05-18T09:00:00+08:00",
            "updated_at": "2026-05-18T09:00:00+08:00",
            "source_type": "human_written",
            "created_by": "human",
            "market_context": {
                "research_date": "2026-05-18",
                "market_date": "2026-05-18",
                "trading_session": "normal",
            },
            "event_type": "theme",
            "title": "AI Theme",
            "description": "AI sector theme event",
            "event_date": "2026-05-18",
            "related_tickers": ["002415"],
            "impact_level": "high",
            "severity": 0.9,
            "confidence": 0.6,
            "decay_rate": 0.15,
            "source": "data_feed",
            "propagation_state": "settled",
            "propagation_graph_id": "pg_002",
            "contract_id": "ec_002",
        }
        evt = Event.from_dict(data)
        assert evt.id == "evt_002"
        assert evt.severity == 0.9
        assert evt.confidence == 0.6
        assert evt.decay_rate == 0.15
        assert evt.source == EventSourceType.DATA_FEED
        assert evt.propagation_state == PropagationState.SETTLED
        assert evt.propagation_graph_id == "pg_002"
        assert evt.contract_id == "ec_002"

    def test_v3_round_trip_preserves_all_fields(self):
        evt = Event(
            id="evt_003",
            event_type=EventType.CAPITAL_FLOW,
            title="Capital Flow Event",
            description="Northbound inflow surge",
            event_date=date(2026, 5, 18),
            related_tickers=["600519", "000858"],
            impact_level=ImpactLevel.HIGH,
            severity=0.85,
            confidence=0.75,
            decay_rate=0.12,
            source=EventSourceType.NEWS,
            propagation_state=PropagationState.DETECTED,
            propagation_graph_id="pg_003",
            contract_id="ec_003",
        )
        d = evt.to_dict()
        evt2 = Event.from_dict(d)
        assert evt2.id == "evt_003"
        assert evt2.event_type == EventType.CAPITAL_FLOW
        assert evt2.event_date == date(2026, 5, 18)
        assert evt2.related_tickers == ["600519", "000858"]
        assert evt2.impact_level == ImpactLevel.HIGH
        assert evt2.severity == 0.85
        assert evt2.confidence == 0.75
        assert evt2.decay_rate == 0.12
        assert evt2.source == EventSourceType.NEWS
        assert evt2.propagation_state == PropagationState.DETECTED
        assert evt2.propagation_graph_id == "pg_003"
        assert evt2.contract_id == "ec_003"


# ---------------------------------------------------------------------------
# TestLazyUpcast -- 2 tests
# ---------------------------------------------------------------------------


class TestLazyUpcast:
    def test_v2_dict_creates_valid_v3_event_with_defaults(self):
        """A v2.0 dict (missing all v3 fields) should produce a valid v3.0 Event."""
        v2_data = {
            "id": "evt_upcast_001",
            "schema_version": "2.0",
            "status": "active",
            "created_at": "2026-05-18T09:00:00+08:00",
            "updated_at": "2026-05-18T09:00:00+08:00",
            "source_type": "human_written",
            "created_by": "human",
            "market_context": {
                "research_date": "2026-05-18",
                "market_date": "2026-05-18",
                "trading_session": "normal",
            },
            "event_type": "earnings",
            "title": "Legacy Event",
            "description": "From v2.0",
            "related_tickers": ["600519"],
            "impact_level": "medium",
            "outcome_tracking": [],
            "linked_review_ids": [],
            "calibration_score": None,
        }
        evt = Event.from_dict(v2_data)
        # v3.0 defaults applied
        assert evt.severity == 0.5
        assert evt.confidence == 0.5
        assert evt.decay_rate == 0.1
        assert evt.source == EventSourceType.MANUAL
        assert evt.propagation_state == PropagationState.DETECTED
        assert evt.propagation_graph_id is None
        assert evt.contract_id is None
        # v2.0 fields preserved
        assert evt.title == "Legacy Event"
        assert evt.event_type == EventType.EARNINGS
        assert evt.related_tickers == ["600519"]

    def test_partial_v3_dict_overrides_defaults(self):
        """A v2.0 dict with some v3 fields set should use those values."""
        partial = {
            "id": "evt_upcast_002",
            "schema_version": "2.0",
            "status": "active",
            "created_at": "2026-05-18T09:00:00+08:00",
            "updated_at": "2026-05-18T09:00:00+08:00",
            "source_type": "human_written",
            "created_by": "human",
            "market_context": {
                "research_date": "2026-05-18",
                "market_date": "2026-05-18",
                "trading_session": "normal",
            },
            "event_type": "policy",
            "title": "Partial v3",
            "severity": 0.3,
            "source": "ai_detected",
            # Other v3 fields omitted -- should get defaults
        }
        evt = Event.from_dict(partial)
        assert evt.severity == 0.3
        assert evt.source == EventSourceType.AI_DETECTED
        assert evt.confidence == 0.5  # default


# ---------------------------------------------------------------------------
# TestEventContractRoundTrip -- 3 tests
# ---------------------------------------------------------------------------


class TestEventContractRoundTrip:
    def test_contract_to_dict(self):
        ec = EventContract(
            id="ec_001",
            contract_id="ec_001",
            event_id="evt_001",
            affected_theses=["ths_001"],
            affected_positions=["pos_001", "pos_002"],
            impact_scores={"ths_001": 0.8, "pos_001": 0.6},
            aggregate_impact=0.7,
            propagation_depth=2,
        )
        d = ec.to_dict()
        assert d["contract_id"] == "ec_001"
        assert d["event_id"] == "evt_001"
        assert d["affected_theses"] == ["ths_001"]
        assert d["affected_positions"] == ["pos_001", "pos_002"]
        assert d["impact_scores"] == {"ths_001": 0.8, "pos_001": 0.6}
        assert d["aggregate_impact"] == 0.7
        assert d["propagation_depth"] == 2
        assert d["settled_at"] is None
        assert "created_at" in d

    def test_contract_from_dict(self):
        data = {
            "id": "ec_002",
            "schema_version": "1.0",
            "status": "active",
            "created_at": "2026-05-18T09:00:00+08:00",
            "updated_at": "2026-05-18T09:00:00+08:00",
            "source_type": "human_written",
            "created_by": "human",
            "market_context": {
                "research_date": "2026-05-18",
                "market_date": "2026-05-18",
                "trading_session": "normal",
            },
            "contract_id": "ec_002",
            "event_id": "evt_002",
            "affected_theses": ["ths_001", "ths_002"],
            "affected_positions": ["pos_001"],
            "impact_scores": {"ths_001": 0.5, "pos_001": 0.3},
            "aggregate_impact": 0.4,
            "propagation_depth": 1,
            "settled_at": "2026-05-20T15:00:00+08:00",
        }
        ec = EventContract.from_dict(data)
        assert ec.contract_id == "ec_002"
        assert ec.event_id == "evt_002"
        assert ec.affected_theses == ["ths_001", "ths_002"]
        assert ec.impact_scores == {"ths_001": 0.5, "pos_001": 0.3}
        assert ec.propagation_depth == 1
        assert ec.settled_at == datetime(2026, 5, 20, 15, 0, 0, tzinfo=CST)

    def test_contract_round_trip_preserves_impact_scores(self):
        ec = EventContract(
            id="ec_003",
            contract_id="ec_003",
            event_id="evt_003",
            affected_theses=["ths_001"],
            affected_positions=[],
            impact_scores={"ths_001": 0.95, "pos_005": 0.12},
            aggregate_impact=0.535,
            propagation_depth=3,
        )
        d = ec.to_dict()
        ec2 = EventContract.from_dict(d)
        assert ec2.id == "ec_003"
        assert ec2.impact_scores == {"ths_001": 0.95, "pos_005": 0.12}
        assert ec2.aggregate_impact == 0.535
        assert ec2.propagation_depth == 3


# ---------------------------------------------------------------------------
# TestPropagationEdgeRoundTrip -- 2 tests
# ---------------------------------------------------------------------------


class TestPropagationEdgeRoundTrip:
    def test_edge_to_dict_and_from_dict(self):
        pe = PropagationEdge(
            id="pe_001",
            edge_id="pe_001",
            source_id="evt_001",
            src_entity_type="event",
            target_id="ths_001",
            tgt_entity_type="thesis",
            weight=0.8,
            decay_rate=0.05,
            edge_type="influence",
        )
        d = pe.to_dict()
        pe2 = PropagationEdge.from_dict(d)
        assert pe2.edge_id == "pe_001"
        assert pe2.source_id == "evt_001"
        assert pe2.src_entity_type == "event"
        assert pe2.target_id == "ths_001"
        assert pe2.tgt_entity_type == "thesis"
        assert pe2.weight == 0.8
        assert pe2.decay_rate == 0.05
        assert pe2.edge_type == "influence"

    def test_edge_defaults(self):
        pe = PropagationEdge(id="pe_002", edge_id="pe_002")
        d = pe.to_dict()
        pe2 = PropagationEdge.from_dict(d)
        assert pe2.weight == 0.5
        assert pe2.decay_rate == 0.1
        assert pe2.src_entity_type == ""
        assert pe2.tgt_entity_type == ""


# ---------------------------------------------------------------------------
# TestConstraintValidation -- 2 tests
# ---------------------------------------------------------------------------


class TestConstraintValidation:
    def test_severity_out_of_range_raises(self):
        with pytest.raises(ValueError, match="severity must be in"):
            Event(id="evt_bad", severity=-0.1)

    def test_weight_out_of_range_raises(self):
        with pytest.raises(ValueError, match="weight must be in"):
            PropagationEdge(id="pe_bad", weight=1.5)


# ---------------------------------------------------------------------------
# TestSettlementLifecycle -- 5 tests
# ---------------------------------------------------------------------------


class TestSettlementLifecycle:
    def test_default_status_pending(self):
        """New EventContract defaults to PENDING status."""
        c = EventContract(id="ec1", contract_id="c1", event_id="e1")
        assert c.settlement_status == SettlementStatus.PENDING
        assert c.settlement_result is None
        assert c.settlement_metadata == {}

    def test_settle_works(self):
        """settle() sets status, result, metadata, and timestamp."""
        c = EventContract(id="ec2", contract_id="c2", event_id="e2")
        c.settle("impacted_theses", metadata={"decay_factor": 0.8, "affected_count": 3})
        assert c.settlement_status == SettlementStatus.SETTLED
        assert c.settlement_result == "impacted_theses"
        assert c.settlement_metadata == {"decay_factor": 0.8, "affected_count": 3}
        assert c.settled_at is not None

    def test_expire_works(self):
        """expire() sets status to EXPIRED and timestamps."""
        c = EventContract(id="ec3", contract_id="c3", event_id="e3")
        c.expire()
        assert c.settlement_status == SettlementStatus.EXPIRED
        assert c.settled_at is not None

    def test_round_trip_serialization(self):
        """to_dict/from_dict preserves all settlement fields."""
        c = EventContract(id="ec4", contract_id="c4", event_id="e4")
        c.settle("no_impact", metadata={"propagation_depth": 2})
        d = c.to_dict()
        c2 = EventContract.from_dict(d)
        assert c2.settlement_status == SettlementStatus.SETTLED
        assert c2.settlement_result == "no_impact"
        assert c2.settlement_metadata == {"propagation_depth": 2}
        assert c2.settled_at is not None

    def test_lazy_upcast_backward_compatible(self):
        """v1.0 dict without settlement fields creates valid EventContract."""
        old_dict = {
            "id": "ec5",
            "contract_id": "c5",
            "event_id": "e5",
            "affected_theses": ["ths_1"],
            "impact_scores": {"ths_1": 0.7},
        }
        c = EventContract.from_dict(old_dict)
        assert c.settlement_status == SettlementStatus.PENDING
        assert c.settlement_result is None
        assert c.settlement_metadata == {}
        assert c.settled_at is None
