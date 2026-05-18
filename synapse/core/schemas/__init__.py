"""Research Object Schemas — 9 core objects for the daily research loop.

All schemas inherit from BaseSchema and follow Weak Schema + Lazy Upcast strategy.
"""

from synapse.core.schemas.base import BaseSchema, MarketContext, ObjectStatus, SourceType, CreatorType
from synapse.core.schemas.watchlist import WatchlistEntry, WatchlistSignal, TriggerType
from synapse.core.schemas.thesis import Thesis, Confidence, RelatedSecurity, Evidence
from synapse.core.schemas.decision import Decision, DecisionType, TimeHorizon, AttentionOrigin
from synapse.core.schemas.review import Review, ReviewOutcome, SignalEvaluation, RiskEvaluation
from synapse.core.schemas.position import Position, ResearchState, ThesisStatus, AttentionState
from synapse.core.schemas.signal import Signal, SignalType, SignalStrength
from synapse.core.schemas.risk import Risk, RiskType, Severity
from synapse.core.schemas.event import (
    Event, EventType, ImpactLevel, EventSourceType, PropagationState,
)
from synapse.core.schemas.event_contract import EventContract
from synapse.core.schemas.propagation_edge import PropagationEdge
from synapse.core.schemas.topic import ResearchTopic

__all__ = [
    # Base
    "BaseSchema",
    "MarketContext",
    "ObjectStatus",
    "SourceType",
    "CreatorType",
    # WatchlistEntry
    "WatchlistEntry",
    "WatchlistSignal",
    "TriggerType",
    # Thesis
    "Thesis",
    "Confidence",
    "RelatedSecurity",
    "Evidence",
    # Decision
    "Decision",
    "DecisionType",
    "TimeHorizon",
    "AttentionOrigin",
    # Review
    "Review",
    "ReviewOutcome",
    "SignalEvaluation",
    "RiskEvaluation",
    # Position
    "Position",
    "ResearchState",
    "ThesisStatus",
    "AttentionState",
    # Signal
    "Signal",
    "SignalType",
    "SignalStrength",
    # Risk
    "Risk",
    "RiskType",
    "Severity",
    # Event
    "Event",
    "EventType",
    "ImpactLevel",
    "EventSourceType",
    "PropagationState",
    # EventContract
    "EventContract",
    # PropagationEdge
    "PropagationEdge",
    # ResearchTopic
    "ResearchTopic",
]
