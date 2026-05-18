"""PropagationLifecycle -- 4-state lifecycle machine + exponential decay model.

State machine:
    DETECTED -> PROPAGATING -> SETTLED
                    |
                    v
                  EXPIRED

Any state can transition to EXPIRED (timeout / stuck protection).

Decay model uses exponential decay: impact(t) = impact_0 * e^(-rate * t)
with category-specific half-lives for A-share event types.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from synapse.core.schemas.event import PropagationState

# Backward-compatible alias: LifecycleState is now PropagationState.
LifecycleState = PropagationState


# Valid transitions: frozenset of (from_state, to_state)
VALID_TRANSITIONS: frozenset[tuple[LifecycleState, LifecycleState]] = frozenset(
    {
        (LifecycleState.DETECTED, LifecycleState.PROPAGATING),
        (LifecycleState.PROPAGATING, LifecycleState.SETTLED),
        (LifecycleState.PROPAGATING, LifecycleState.EXPIRED),
        # Any state can go to EXPIRED (timeout/stuck protection)
        (LifecycleState.DETECTED, LifecycleState.EXPIRED),
        (LifecycleState.SETTLED, LifecycleState.EXPIRED),
    }
)

STUCK_TIMEOUT_DAYS = 7


class PropagationLifecycle:
    """State machine for event propagation lifecycle.

    Tracks state transitions with timestamps and detects stuck propagation
    (PROPAGATING state held for longer than STUCK_TIMEOUT_DAYS).
    """

    def __init__(
        self,
        event_id: str,
        initial_state: LifecycleState = LifecycleState.DETECTED,
    ) -> None:
        self.event_id = event_id
        self._state = initial_state
        self._state_history: list[tuple[LifecycleState, datetime]] = [
            (initial_state, datetime.now())
        ]
        self._propagating_since: Optional[datetime] = None
        if initial_state == LifecycleState.PROPAGATING:
            self._propagating_since = datetime.now()

    def transition(self, new_state: LifecycleState) -> None:
        """Transition to new_state.

        Raises ValueError if the transition is not in VALID_TRANSITIONS.
        """
        if (self._state, new_state) not in VALID_TRANSITIONS:
            raise ValueError(
                f"Invalid transition: {self._state.value} -> {new_state.value}"
            )
        self._state = new_state
        self._state_history.append((new_state, datetime.now()))
        if new_state == LifecycleState.PROPAGATING:
            self._propagating_since = datetime.now()

    def get_state(self) -> LifecycleState:
        """Return current lifecycle state."""
        return self._state

    def get_state_history(self) -> list[tuple[LifecycleState, datetime]]:
        """Return copy of state history as (state, timestamp) pairs."""
        return list(self._state_history)

    def is_stuck(self, now: Optional[datetime] = None) -> bool:
        """Check if stuck in PROPAGATING state for > STUCK_TIMEOUT_DAYS.

        Args:
            now: Optional reference time for testing. Defaults to datetime.now().

        Returns:
            True if in PROPAGATING state longer than STUCK_TIMEOUT_DAYS.
        """
        if self._state != LifecycleState.PROPAGATING or self._propagating_since is None:
            return False
        now = now or datetime.now()
        elapsed = (now - self._propagating_since).total_seconds() / 86400
        return elapsed > STUCK_TIMEOUT_DAYS


# ---------------------------------------------------------------------------
# Decay Model
# ---------------------------------------------------------------------------

CATEGORY_HALF_LIVES: dict[str, float] = {
    "earnings": 6.5,        # 5-8 days, midpoint 6.5
    "policy": 1.5,          # 1-2 days, midpoint 1.5
    "sentiment": 2.0,       # 1-3 days, midpoint 2.0
    "theme": 4.0,           # 3-5 days, midpoint 4.0
    "capital_flow": 2.0,    # 1-3 days, midpoint 2.0
    "corporate_action": 5.0,  # ~5 days
}

DEFAULT_HALF_LIFE = 5.0


def compute_decay(impact_0: float, decay_rate: float, days: float) -> float:
    """Exponential decay: impact(t) = impact_0 * e^(-decay_rate * t).

    Args:
        impact_0: Initial impact value (>= 0).
        decay_rate: Decay rate constant (> 0).
        days: Elapsed time in days (>= 0).

    Returns:
        Decayed impact value.
    """
    return impact_0 * math.exp(-decay_rate * days)


def apply_category_decay(event_type: str, impact_0: float, days: float) -> float:
    """Apply decay using category-specific half-life.

    decay_rate = ln(2) / half_life

    Args:
        event_type: Event type key (e.g., "earnings", "policy").
        impact_0: Initial impact value (>= 0).
        days: Elapsed time in days (>= 0).

    Returns:
        Decayed impact value using the category's half-life.
    """
    half_life = CATEGORY_HALF_LIVES.get(event_type, DEFAULT_HALF_LIFE)
    decay_rate = math.log(2) / half_life
    return compute_decay(impact_0, decay_rate, days)
