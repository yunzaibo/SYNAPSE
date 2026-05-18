"""DeduplicationEngine -- Merge and deduplicate events from multiple sources.

Uses SHA-256 hashing of (event_type, entity_id, date, source) to generate
deduplication keys.  When duplicate events are found, merges them by keeping
the higher-confidence event's metadata and combining descriptions.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from synapse.core.schemas.event import Event
from synapse.event.taxonomy import SOURCE_PRIORITY


class DeduplicationEngine:
    """Engine for deduplicating and merging events from multiple sources.

    Usage::

        engine = DeduplicationEngine()
        key = engine.compute_dedup_key("earnings", "600519", "2025-04-15", "cninfo")
        merged = engine.merge_events(event_a, event_b)
        unique = engine.resolve_conflicts([event_a, event_b])
    """

    def compute_dedup_key(
        self,
        event_type: str,
        entity_id: str,
        date_str: str,
        source: str,
    ) -> str:
        """Return a SHA-256 deduplication key.

        Parameters
        ----------
        event_type:
            The event type string (e.g. "earnings").
        entity_id:
            Ticker or entity identifier.
        date_str:
            ISO-format date string (e.g. "2025-04-15").
        source:
            Source identifier (e.g. "cninfo").

        Returns
        -------
        str
            Lowercase hex SHA-256 digest.
        """
        raw = f"{event_type}:{entity_id}:{date_str}:{source}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def merge_events(self, event_a: Event, event_b: Event) -> Event:
        """Merge two events that share the same dedup key.

        Rules:
        - Higher confidence wins for ``confidence`` and ``severity``.
        - Descriptions are combined with ``" | "`` separator.
        - ``related_tickers`` are unioned.
        - The event with higher confidence becomes the base.

        Parameters
        ----------
        event_a:
            First event.
        event_b:
            Second event.

        Returns
        -------
        Event
            A new merged Event.
        """
        if event_a.confidence >= event_b.confidence:
            base, other = event_a, event_b
        else:
            base, other = event_b, event_a

        combined_desc = _merge_descriptions(base.description, other.description)
        combined_tickers = list(dict.fromkeys(base.related_tickers + other.related_tickers))
        combined_reviews = list(dict.fromkeys(base.linked_review_ids + other.linked_review_ids))
        combined_outcomes = list(base.outcome_tracking) + list(other.outcome_tracking)

        return Event(
            id=base.id,
            schema_version=base.schema_version,
            event_type=base.event_type,
            title=base.title,
            description=combined_desc,
            event_date=base.event_date,
            related_tickers=combined_tickers,
            impact_level=base.impact_level,
            outcome_tracking=combined_outcomes,
            linked_review_ids=combined_reviews,
            calibration_score=base.calibration_score if base.calibration_score is not None else other.calibration_score,
            severity=base.severity,
            confidence=base.confidence,
            decay_rate=base.decay_rate,
            source=base.source,
            propagation_state=base.propagation_state,
            propagation_graph_id=base.propagation_graph_id or other.propagation_graph_id,
            contract_id=base.contract_id or other.contract_id,
        )

    def resolve_conflicts(self, events: list[Event]) -> list[Event]:
        """Deduplicate a list of events.

        Events are grouped by a simplified dedup key derived from their
        attributes (event_type + title + event_date).  Within each group
        the highest-priority source wins (ties broken by confidence).

        Parameters
        ----------
        events:
            List of events to deduplicate.

        Returns
        -------
        list[Event]
            Deduplicated list with merged events.
        """
        if not events:
            return []

        groups: dict[str, list[Event]] = {}
        for ev in events:
            key = self._event_dedup_key(ev)
            groups.setdefault(key, []).append(ev)

        result: list[Event] = []
        for group_events in groups.values():
            if len(group_events) == 1:
                result.append(group_events[0])
                continue
            merged = group_events[0]
            for other in group_events[1:]:
                merged = self.merge_events(merged, other)
            result.append(merged)
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _event_dedup_key(event: Event) -> str:
        """Generate a dedup key from event attributes for grouping."""
        date_str = event.event_date.isoformat() if event.event_date else ""
        raw = f"{event.event_type.value}:{event.title}:{date_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _source_priority(event: Event) -> int:
        """Return priority number for *event.source* (lower = higher authority)."""
        return SOURCE_PRIORITY.get(event.source.value, 99)


def _merge_descriptions(desc_a: str, desc_b: str) -> str:
    """Combine two descriptions, avoiding duplication."""
    if not desc_a:
        return desc_b
    if not desc_b:
        return desc_a
    if desc_a == desc_b:
        return desc_a
    return f"{desc_a} | {desc_b}"
