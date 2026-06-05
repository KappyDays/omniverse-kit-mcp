"""State-machine tests for InteractionStateMachine.

Imports the carb-free state_machine module directly — no Kit/USD chain.
"""

from __future__ import annotations

from omni.mycompany.usd_mouse_interact.state_machine import (
    InteractionStateMachine,
    State,
)


def test_initial_state_idle():
    sm = InteractionStateMachine()
    assert sm.state is State.IDLE
    assert sm.is_active() is False


def test_play_transitions_to_active():
    sm = InteractionStateMachine()
    assert sm.on_play() is True
    assert sm.is_active() is True


def test_play_when_already_active_is_noop():
    sm = InteractionStateMachine()
    sm.on_play()
    assert sm.on_play() is False
    assert sm.is_active() is True


def test_stop_from_active_transitions_idle():
    sm = InteractionStateMachine()
    sm.on_play()
    assert sm.on_stop() is True
    assert sm.is_active() is False


def test_stop_when_idle_is_noop():
    sm = InteractionStateMachine()
    assert sm.on_stop() is False
    assert sm.is_active() is False


def test_escape_from_active_transitions_idle():
    sm = InteractionStateMachine()
    sm.on_play()
    assert sm.on_escape() is True
    assert sm.is_active() is False


def test_escape_when_idle_is_noop():
    sm = InteractionStateMachine()
    assert sm.on_escape() is False


def test_full_cycle():
    sm = InteractionStateMachine()
    assert sm.on_play()
    assert sm.is_active()
    assert sm.on_stop()
    assert not sm.is_active()
    assert sm.on_play()
    assert sm.on_escape()
    assert not sm.is_active()
