"""Behavioral Statistics -- Decision Pattern Replay.

Replays Decision objects to compute behavioral statistics:
decision type distribution, attention origin distribution,
time horizon distribution, decision frequency, and average signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from synapse.core.schemas.decision import Decision, DecisionType, TimeHorizon, AttentionOrigin


@dataclass
class BehavioralStatsReport:
    """Aggregated behavioral statistics from Decision replay."""

    decision_type_distribution: dict[str, float] = field(default_factory=dict)
    attention_origin_distribution: dict[str, float] = field(default_factory=dict)
    time_horizon_distribution: dict[str, float] = field(default_factory=dict)
    decision_frequency_per_week: float = 0.0
    avg_signals_per_decision: float = 0.0
    total_decisions: int = 0
    period_days: int = 0

    def to_dict(self) -> dict:
        return {
            "decision_type_distribution": self.decision_type_distribution,
            "attention_origin_distribution": self.attention_origin_distribution,
            "time_horizon_distribution": self.time_horizon_distribution,
            "decision_frequency_per_week": self.decision_frequency_per_week,
            "avg_signals_per_decision": self.avg_signals_per_decision,
            "total_decisions": self.total_decisions,
            "period_days": self.period_days,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BehavioralStatsReport:
        return cls(
            decision_type_distribution=data.get("decision_type_distribution", {}),
            attention_origin_distribution=data.get("attention_origin_distribution", {}),
            time_horizon_distribution=data.get("time_horizon_distribution", {}),
            decision_frequency_per_week=float(data.get("decision_frequency_per_week", 0.0)),
            avg_signals_per_decision=float(data.get("avg_signals_per_decision", 0.0)),
            total_decisions=int(data.get("total_decisions", 0)),
            period_days=int(data.get("period_days", 0)),
        )


def _compute_distribution(items: list[str]) -> dict[str, float]:
    """Compute percentage distribution from a list of category strings."""
    if not items:
        return {}
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    total = len(items)
    return {k: round(v / total * 100, 2) for k, v in sorted(counts.items())}


class BehavioralStatsAnalyzer:
    """Replays Decision objects to compute behavioral statistics."""

    def analyze(self, decisions: list[Decision]) -> BehavioralStatsReport:
        """Analyze a list of Decision objects and produce a stats report.

        Args:
            decisions: List of Decision objects to analyze.

        Returns:
            BehavioralStatsReport with aggregated statistics.
        """
        if not decisions:
            return BehavioralStatsReport()

        total = len(decisions)

        # Distributions
        decision_types = [d.decision_type.value for d in decisions]
        attention_origins = [d.attention_origin.value for d in decisions]
        time_horizons = [d.time_horizon.value for d in decisions]

        decision_type_dist = _compute_distribution(decision_types)
        attention_origin_dist = _compute_distribution(attention_origins)
        time_horizon_dist = _compute_distribution(time_horizons)

        # Frequency: decisions per week from timestamp span
        timestamps = []
        for d in decisions:
            if d.created_at is not None:
                timestamps.append(d.created_at)
        timestamps.sort()

        if len(timestamps) >= 2:
            span = timestamps[-1] - timestamps[0]
            period_days = max(span.days, 1)
        elif len(timestamps) == 1:
            period_days = 0
        else:
            period_days = 0

        if period_days > 0:
            freq = round(total / (period_days / 7), 2)
        else:
            freq = 0.0

        # Average signals per decision
        total_signals = sum(len(d.signals) for d in decisions)
        avg_signals = round(total_signals / total, 2)

        return BehavioralStatsReport(
            decision_type_distribution=decision_type_dist,
            attention_origin_distribution=attention_origin_dist,
            time_horizon_distribution=time_horizon_dist,
            decision_frequency_per_week=freq,
            avg_signals_per_decision=avg_signals,
            total_decisions=total,
            period_days=period_days,
        )
