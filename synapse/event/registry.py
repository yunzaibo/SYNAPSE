"""DetectorRegistry -- Registration and lookup for pluggable event detectors.

Holds a mapping from event_type -> detector class, and provides
convenience methods for bulk detection and enumeration.
"""

from __future__ import annotations

from typing import Optional

from synapse.core.schemas.event import Event
from synapse.event.base import BaseDetector


class DetectorRegistry:
    """Central registry that maps event types to detector classes.

    Usage::

        registry = DetectorRegistry()
        registry.register(EarningsDetector)
        detector = registry.get_detector("earnings")
    """

    def __init__(self) -> None:
        self._detectors: dict[str, type[BaseDetector]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, detector_cls: type[BaseDetector]) -> None:
        """Register *detector_cls* using its classmethod event_type().

        Parameters
        ----------
        detector_cls:
            A concrete subclass of BaseDetector.

        Raises
        ------
        TypeError
            If *detector_cls* is not a BaseDetector subclass.
        ValueError
            If *detector_cls* does not return a non-empty event_type string.
        """
        if not (isinstance(detector_cls, type) and issubclass(detector_cls, BaseDetector)):
            raise TypeError(
                f"{detector_cls!r} is not a subclass of BaseDetector"
            )
        etype = detector_cls.event_type()
        if not etype:
            raise ValueError(
                f"{detector_cls.__name__}.event_type() returned an empty string"
            )
        self._detectors[etype] = detector_cls

    def unregister(self, event_type: str) -> Optional[type[BaseDetector]]:
        """Remove and return the detector for *event_type*, or None."""
        return self._detectors.pop(event_type, None)

    def get_detector(self, event_type: str) -> Optional[type[BaseDetector]]:
        """Return the detector class registered for *event_type*, or None."""
        return self._detectors.get(event_type)

    def list_detectors(self) -> dict[str, type[BaseDetector]]:
        """Return a shallow copy of the internal mapping."""
        return dict(self._detectors)

    def detect_all(self, data: dict) -> list[Event]:
        """Run every registered detector against *data*.

        Returns a list of Event objects from detectors that fired.
        Detectors that returned None are silently skipped.
        """
        events: list[Event] = []
        for _etype, cls in self._detectors.items():
            instance = cls()
            event = instance.detect(data)
            if event is not None:
                events.append(event)
        return events
