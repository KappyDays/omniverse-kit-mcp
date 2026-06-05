"""Pure-Python state machine for the IDLE/ACTIVE toggle.

Kept Kit-free so it can be unit-tested with plain pytest.
"""

from __future__ import annotations

import enum


class State(enum.Enum):
    IDLE = "idle"
    ACTIVE = "active"


class InteractionStateMachine:

    def __init__(self) -> None:
        self._state = State.IDLE

    @property
    def state(self) -> State:
        return self._state

    def is_active(self) -> bool:
        return self._state is State.ACTIVE

    def on_play(self) -> bool:
        if self._state is State.IDLE:
            self._state = State.ACTIVE
            return True
        return False

    def on_stop(self) -> bool:
        if self._state is State.ACTIVE:
            self._state = State.IDLE
            return True
        return False

    def on_escape(self) -> bool:
        if self._state is State.ACTIVE:
            self._state = State.IDLE
            return True
        return False
