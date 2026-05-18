"""BaseDetector -- Abstract interface for pluggable event detectors.

Each concrete detector implements detect() to scan incoming data and
return an Event if conditions match, or None otherwise.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from synapse.core.schemas.event import Event


class BaseDetector(ABC):
    """Abstract base class for event detectors.

    Subclasses must implement:
    - detect(data) -> Optional[Event]
    - event_type() -> str (instance method)
    - event_type(cls) -> str (classmethod)
    - confidence_score(data) -> float
    """

    @abstractmethod
    def detect(self, data: dict) -> Optional[Event]:
        """Analyze *data* and return an Event if detected, else None.

        Parameters
        ----------
        data:
            Arbitrary dict of raw signals (news text, financial data, etc.).

        Returns
        -------
        Event or None
        """

    @classmethod
    @abstractmethod
    def event_type(cls) -> str:
        """Return the event type string this detector handles.

        Must match one of the values in synapse.event.taxonomy.EVENT_TYPES.
        """

    @abstractmethod
    def confidence_score(self, data: dict) -> float:
        """Return a confidence score in [0.0, 1.0] for the given *data*.

        Parameters
        ----------
        data:
            Same dict that would be passed to detect().

        Returns
        -------
        float in [0.0, 1.0]
        """
