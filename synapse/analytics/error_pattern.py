"""Error Pattern Analysis — Review accuracy aggregation.

Aggregates signal accuracy from Review.signal_evaluations[].was_accurate
across all reviews to identify per-signal-type accuracy rates, worst
performers, and temporal trends.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.review import Review
from synapse.core.schemas.signal import Signal, SignalType


class TrendDirection(str, Enum):
    """Direction of accuracy trend over time."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class ErrorPatternReport:
    """Aggregated error pattern analysis from review signal evaluations."""

    overall_accuracy: float = 0.0
    per_signal_type_accuracy: dict[str, float] = field(default_factory=dict)
    worst_performers: list[str] = field(default_factory=list)
    total_reviews: int = 0
    total_signals_evaluated: int = 0
    trend: TrendDirection = TrendDirection.STABLE

    def to_dict(self) -> dict:
        return {
            "overall_accuracy": self.overall_accuracy,
            "per_signal_type_accuracy": dict(self.per_signal_type_accuracy),
            "worst_performers": list(self.worst_performers),
            "total_reviews": self.total_reviews,
            "total_signals_evaluated": self.total_signals_evaluated,
            "trend": self.trend.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ErrorPatternReport:
        return cls(
            overall_accuracy=float(data.get("overall_accuracy", 0.0)),
            per_signal_type_accuracy={
                k: float(v)
                for k, v in data.get("per_signal_type_accuracy", {}).items()
            },
            worst_performers=list(data.get("worst_performers", [])),
            total_reviews=int(data.get("total_reviews", 0)),
            total_signals_evaluated=int(data.get("total_signals_evaluated", 0)),
            trend=TrendDirection(data.get("trend", "stable")),
        )


class ErrorPatternAnalyzer:
    """Analyzes signal accuracy across reviews to identify error patterns."""

    def analyze(
        self,
        reviews: list[Review],
        signals: Optional[list[Signal]] = None,
    ) -> ErrorPatternReport:
        """Aggregate signal accuracy from reviews.

        Args:
            reviews: List of Review objects containing signal_evaluations.
            signals: Optional list of Signal objects used to resolve
                signal_type from linked_signal_id. If not provided,
                per-type accuracy and worst performers will be empty.

        Returns:
            ErrorPatternReport with aggregated accuracy metrics.
        """
        if not reviews:
            return ErrorPatternReport()

        # Build signal_id -> signal_type lookup
        signal_type_map: dict[str, str] = {}
        if signals:
            for sig in signals:
                signal_type_map[sig.id] = sig.signal_type.value

        total_correct = 0
        total_evaluated = 0
        type_correct: dict[str, int] = defaultdict(int)
        type_total: dict[str, int] = defaultdict(int)

        # Collect (timestamp, was_accurate) for trend analysis
        trend_points: list[tuple[datetime, bool]] = []

        for review in reviews:
            for se in review.signal_evaluations:
                total_evaluated += 1
                if se.was_accurate:
                    total_correct += 1

                # Resolve signal type
                sig_type = signal_type_map.get(se.linked_signal_id)
                if sig_type:
                    type_total[sig_type] += 1
                    if se.was_accurate:
                        type_correct[sig_type] += 1

                trend_points.append((review.created_at, se.was_accurate))

        overall_accuracy = total_correct / total_evaluated if total_evaluated > 0 else 0.0

        # Per-signal-type accuracy
        per_type_accuracy: dict[str, float] = {}
        for sig_type_name, count in type_total.items():
            per_type_accuracy[sig_type_name] = type_correct[sig_type_name] / count

        # Worst performers: signal types with accuracy below 50%
        worst_performers = sorted(
            [st for st, acc in per_type_accuracy.items() if acc < 0.5],
            key=lambda st: per_type_accuracy[st],
        )

        # Trend analysis
        trend = self._compute_trend(trend_points)

        return ErrorPatternReport(
            overall_accuracy=overall_accuracy,
            per_signal_type_accuracy=per_type_accuracy,
            worst_performers=worst_performers,
            total_reviews=len(reviews),
            total_signals_evaluated=total_evaluated,
            trend=trend,
        )

    def _compute_trend(
        self, points: list[tuple[datetime, bool]]
    ) -> TrendDirection:
        """Compute accuracy trend from temporally ordered points.

        Splits points into two halves (by time) and compares average
        accuracy. A meaningful shift (> 10 percentage points) indicates
        improving or declining; otherwise stable.
        """
        if len(points) < 2:
            return TrendDirection.STABLE

        # Already sorted by review timestamp from caller
        mid = len(points) // 2
        first_half = points[:mid]
        second_half = points[mid:]

        if not first_half or not second_half:
            return TrendDirection.STABLE

        acc_first = sum(1 for _, ok in first_half if ok) / len(first_half)
        acc_second = sum(1 for _, ok in second_half if ok) / len(second_half)

        diff = acc_second - acc_first
        if diff > 0.1:
            return TrendDirection.IMPROVING
        elif diff < -0.1:
            return TrendDirection.DECLINING
        else:
            return TrendDirection.STABLE
