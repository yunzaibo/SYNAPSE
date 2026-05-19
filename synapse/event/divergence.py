"""CapitalFlowDivergence -- Schema and scoring for institutional vs retail flow divergence.

Tracks divergence between institutional (mainforce) and retail (small order) capital
flows, computes normalized divergence scores in [-1, 1], and integrates with
EventContract for settlement lifecycle.

Part of the event-driven propagation graph (P3).
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from synapse.core.schemas.event import Event, EventType
from synapse.core.temporal import CST


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class CapitalFlowDivergence:
    """Divergence between institutional and retail capital flows.

    10-field schema following the F-008 feature spec.
    Standalone dataclass (no BaseSchema inheritance) for clean round-trip.
    """

    # --- Identity ---
    divergence_id: str = ""
    ticker: str = ""
    sector: str = ""

    # --- Flow data (positive = inflow) ---
    institutional_flow: float = 0.0
    retail_flow: float = 0.0

    # --- Computed ---
    divergence_score: float = 0.0
    classification: str = "neutral"  # bullish_divergence / bearish_divergence / neutral
    magnitude: float = 0.5  # Flow strength [0, 1]

    # --- Window ---
    window_days: int = 5

    # --- Timestamps ---
    computed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not (-1.0 <= self.divergence_score <= 1.0):
            raise ValueError(
                f"divergence_score must be in [-1, 1], got {self.divergence_score}"
            )
        if not (0.0 <= self.magnitude <= 1.0):
            raise ValueError(
                f"magnitude must be in [0, 1], got {self.magnitude}"
            )
        valid_cls = ("bullish_divergence", "bearish_divergence", "neutral")
        if self.classification not in valid_cls:
            raise ValueError(
                f"classification must be one of {valid_cls}, got {self.classification!r}"
            )

    def to_dict(self) -> dict:
        """Serialize to dict for YAML/JSON round-trip."""
        return {
            "divergence_id": self.divergence_id,
            "ticker": self.ticker,
            "sector": self.sector,
            "institutional_flow": self.institutional_flow,
            "retail_flow": self.retail_flow,
            "divergence_score": self.divergence_score,
            "classification": self.classification,
            "magnitude": self.magnitude,
            "window_days": self.window_days,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CapitalFlowDivergence:
        """Deserialize from dict (Lazy Upcast compatible)."""
        computed_raw = data.get("computed_at")
        return cls(
            divergence_id=data.get("divergence_id", ""),
            ticker=data.get("ticker", ""),
            sector=data.get("sector", ""),
            institutional_flow=float(data.get("institutional_flow", 0.0)),
            retail_flow=float(data.get("retail_flow", 0.0)),
            divergence_score=float(data.get("divergence_score", 0.0)),
            classification=data.get("classification", "neutral"),
            magnitude=float(data.get("magnitude", 0.5)),
            window_days=int(data.get("window_days", 5)),
            computed_at=datetime.fromisoformat(computed_raw) if computed_raw else None,
        )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_EPSILON = 1e-9


def compute_divergence_score(
    inst_flow: float,
    retail_flow: float,
) -> float:
    """Compute normalized divergence score between institutional and retail flow.

    Formula: (inst - retail) / (|inst| + |retail| + epsilon)

    Parameters
    ----------
    inst_flow:
        Net institutional capital flow. Positive = inflow.
    retail_flow:
        Net retail capital flow. Positive = inflow.

    Returns
    -------
    float in [-1.0, 1.0]. Positive = institutional bullish, negative = retail bullish.
    """
    numerator = inst_flow - retail_flow
    denominator = math.fabs(inst_flow) + math.fabs(retail_flow) + _EPSILON
    return numerator / denominator


def classify_divergence(score: float) -> str:
    """Classify divergence score into a directional label.

    Thresholds (from F-008 spec):
    - score > 0.3  -> bullish_divergence (institutional buying, retail selling)
    - score < -0.3 -> bearish_divergence (institutional selling, retail buying)
    - otherwise    -> neutral

    Parameters
    ----------
    score:
        Normalized divergence score in [-1, 1].

    Returns
    -------
    One of "bullish_divergence", "bearish_divergence", "neutral".
    """
    if score > 0.3:
        return "bullish_divergence"
    if score < -0.3:
        return "bearish_divergence"
    return "neutral"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_divergence_from_flows(
    events: list[Event],
    ticker: str,
    sector: str = "",
    window_days: int = 5,
) -> CapitalFlowDivergence:
    """Aggregate capital flow events and build a CapitalFlowDivergence.

    Filters events for CAPITAL_FLOW type, sums institutional and retail flows
    within the given window, then computes score and classification.

    Parameters
    ----------
    events:
        List of Event objects. Non-capital-flow events are ignored.
    ticker:
        Ticker symbol for the divergence record.
    sector:
        Optional sector label.
    window_days:
        Rolling window in trading days (default 5).

    Returns
    -------
    CapitalFlowDivergence with computed score, classification, and magnitude.
    """
    inst_total = 0.0
    retail_total = 0.0
    flow_count = 0

    for ev in events:
        if not hasattr(ev, "event_type"):
            continue
        if ev.event_type != EventType.CAPITAL_FLOW:
            continue

        meta = getattr(ev, "_flow_data", None) or {}
        # Also check if event description contains structured flow data
        if not meta and hasattr(ev, "description"):
            meta = _parse_flow_from_description(ev.description)

        inst_total += meta.get("institutional_flow", 0.0)
        retail_total += meta.get("retail_flow", 0.0)
        flow_count += 1

    score = compute_divergence_score(inst_total, retail_total)
    cls_label = classify_divergence(score)

    # Magnitude: fraction of window filled (capped at 1.0)
    magnitude = min(flow_count / max(window_days, 1), 1.0)

    divergence_id = f"div-{ticker}-{uuid.uuid4().hex[:8]}"

    return CapitalFlowDivergence(
        divergence_id=divergence_id,
        ticker=ticker,
        sector=sector,
        institutional_flow=inst_total,
        retail_flow=retail_total,
        divergence_score=score,
        classification=cls_label,
        magnitude=magnitude,
        window_days=window_days,
        computed_at=datetime.now(tz=CST),
    )


def _parse_flow_from_description(description: str) -> dict[str, float]:
    """Best-effort parse of flow data from event description text.

    Expects key=value pairs like "institutional_flow=123.4 retail_flow=-56.7".
    Returns empty dict if parsing fails.
    """
    result: dict[str, float] = {}
    for token in description.split():
        if "=" in token:
            key, _, val = token.partition("=")
            key = key.strip()
            if key in ("institutional_flow", "retail_flow"):
                try:
                    result[key] = float(val)
                except (ValueError, TypeError):
                    pass
    return result


# ---------------------------------------------------------------------------
# Settlement Integration
# ---------------------------------------------------------------------------


def settle_divergence_contract(
    divergence: CapitalFlowDivergence,
    contract: Any,
) -> None:
    """Settle an EventContract using divergence classification results.

    Delegates to EventContract.settle() with divergence-specific metadata.
    Uses duck-typing with hasattr guards for cross-module imports.

    Parameters
    ----------
    divergence:
        The computed divergence to settle against.
    contract:
        The EventContract to settle. Must have a settle() method (duck-typed).

    Raises
    ------
    TypeError:
        If contract does not implement settle().
    """
    if not hasattr(contract, "settle"):
        raise TypeError(
            f"contract must have settle() method, got {type(contract).__name__}"
        )

    result_map = {
        "bullish_divergence": "bullish_divergence",
        "bearish_divergence": "bearish_divergence",
        "neutral": "no_divergence",
    }
    settlement_result = result_map.get(divergence.classification, "no_divergence")

    metadata = {
        "divergence_score": divergence.divergence_score,
        "flow_magnitude": divergence.magnitude,
        "institutional_flow": divergence.institutional_flow,
        "retail_flow": divergence.retail_flow,
        "classification": divergence.classification,
        "window_days": divergence.window_days,
    }

    contract.settle(result=settlement_result, metadata=metadata)
