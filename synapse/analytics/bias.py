"""Bias Detector — Analyze decision distribution for attention and horizon bias.

Computes entropy-based imbalance scores for attention_origin and
time_horizon distributions across a set of decisions.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from synapse.core.schemas.decision import Decision, AttentionOrigin, TimeHorizon


@dataclass
class BiasReport:
    """Output of decision bias analysis."""

    attention_imbalance_score: float  # 0 = perfectly balanced, 1 = fully concentrated
    horizon_concentration_score: float  # 0 = balanced, 1 = concentrated
    attention_distribution: dict[str, float]
    horizon_distribution: dict[str, float]
    threshold_breaches: list[str]
    recommended_focus: str

    def to_dict(self) -> dict:
        return {
            "attention_imbalance_score": self.attention_imbalance_score,
            "horizon_concentration_score": self.horizon_concentration_score,
            "attention_distribution": self.attention_distribution,
            "horizon_distribution": self.horizon_distribution,
            "threshold_breaches": self.threshold_breaches,
            "recommended_focus": self.recommended_focus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BiasReport:
        return cls(
            attention_imbalance_score=float(data["attention_imbalance_score"]),
            horizon_concentration_score=float(data["horizon_concentration_score"]),
            attention_distribution=dict(data["attention_distribution"]),
            horizon_distribution=dict(data["horizon_distribution"]),
            threshold_breaches=list(data["threshold_breaches"]),
            recommended_focus=str(data["recommended_focus"]),
        )


class BiasDetector:
    """Detects distributional bias in decision attributes."""

    def analyze(
        self,
        decisions: list[Decision],
        threshold: float = 0.7,
    ) -> BiasReport:
        """Analyze decisions for attention and horizon distribution bias.

        Args:
            decisions: List of Decision objects to analyze.
            threshold: Concentration threshold (0-1) for breach detection.
                       Any origin above this share triggers a breach.

        Returns:
            BiasReport with imbalance scores and distribution details.
        """
        if not decisions:
            return BiasReport(
                attention_imbalance_score=0.0,
                horizon_concentration_score=0.0,
                attention_distribution={},
                horizon_distribution={},
                threshold_breaches=[],
                recommended_focus="",
            )

        # Compute distributions
        attention_counts = Counter(d.attention_origin.value for d in decisions)
        horizon_counts = Counter(d.time_horizon.value for d in decisions)

        total = len(decisions)

        attention_dist = {
            k: v / total for k, v in attention_counts.items()
        }
        horizon_dist = {
            k: v / total for k, v in horizon_counts.items()
        }

        # Imbalance scores (1 - normalized_entropy)
        att_score = self._compute_imbalance_score(attention_dist)
        hor_score = self._compute_imbalance_score(horizon_dist)

        # Threshold breaches: origins exceeding the threshold concentration
        breaches = self._find_breaches(attention_dist, threshold)

        # Recommended focus: most underrepresented attention origin
        recommended = self._compute_recommended_focus(attention_dist)

        return BiasReport(
            attention_imbalance_score=att_score,
            horizon_concentration_score=hor_score,
            attention_distribution=attention_dist,
            horizon_distribution=horizon_dist,
            threshold_breaches=breaches,
            recommended_focus=recommended,
        )

    def _compute_imbalance_score(self, distribution: dict[str, float]) -> float:
        """Compute imbalance score using normalized entropy.

        Score = 1 - H / H_max where H is Shannon entropy and H_max = log(n).
        Score of 0 means perfectly balanced; 1 means fully concentrated.
        """
        values = list(distribution.values())
        n = len(values)

        if n <= 1:
            return 0.0

        # Shannon entropy
        h = -sum(v * math.log(v) for v in values if v > 0)
        h_max = math.log(n)

        if h_max == 0:
            return 0.0

        return round(1.0 - h / h_max, 4)

    def _find_breaches(
        self, distribution: dict[str, float], threshold: float
    ) -> list[str]:
        """Find distribution entries that exceed the threshold concentration."""
        return sorted(
            [k for k, v in distribution.items() if v > threshold]
        )

    def _compute_recommended_focus(self, distribution: dict[str, float]) -> str:
        """Identify the most underrepresented attention origin.

        Considers all known AttentionOrigin values, including those with
        0 presence in the data. Returns the origin with the lowest share,
        or empty string if distribution is empty or perfectly balanced.
        """
        if not distribution:
            return ""

        # Include all known origins (missing ones default to 0.0)
        full_distribution = {
            ao.value: distribution.get(ao.value, 0.0)
            for ao in AttentionOrigin
        }

        min_share = min(full_distribution.values())
        # If perfectly balanced, no recommendation
        if min_share == max(full_distribution.values()):
            return ""

        underrep = [k for k, v in full_distribution.items() if v == min_share]
        return underrep[0] if underrep else ""
