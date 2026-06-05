"""Unit tests for the carb-free PureKeyState mirror of InputState."""

from __future__ import annotations

# input_state.py imports carb at module load — so we import only the
# carb-independent class via a side import. To keep the test file fully
# Kit-free we re-import the module with a stub carb if necessary.

import sys
import types


def _install_carb_stubs():
    """Provide minimal carb / carb.input stubs so input_state imports cleanly."""
    if "carb" in sys.modules:
        return
    carb = types.ModuleType("carb")

    def _noop(*_a, **_kw):
        return None

    carb.log_warn = _noop
    carb.log_info = _noop
    carb.log_error = _noop

    carb_input = types.ModuleType("carb.input")

    class _KeyboardInput:
        W = "W"
        A = "A"
        S = "S"
        D = "D"
        Q = "Q"
        E = "E"
        ESCAPE = "ESCAPE"

    class _KeyboardEventType:
        KEY_PRESS = "PRESS"
        KEY_RELEASE = "RELEASE"
        KEY_REPEAT = "REPEAT"

    def _acquire_input_interface():
        return None

    carb_input.KeyboardInput = _KeyboardInput
    carb_input.KeyboardEventType = _KeyboardEventType
    carb_input.acquire_input_interface = _acquire_input_interface

    carb.input = carb_input

    sys.modules["carb"] = carb
    sys.modules["carb.input"] = carb_input


_install_carb_stubs()


from omni.mycompany.usd_mouse_interact.input_state import PureKeyState  # noqa: E402


def test_initial_state_no_keys_pressed():
    s = PureKeyState()
    snap = s.snapshot()
    assert not any(
        [snap.forward, snap.backward, snap.left, snap.right, snap.up, snap.down]
    )


def test_press_w_sets_forward():
    s = PureKeyState()
    s.press("W")
    assert s.snapshot().forward is True
    assert s.snapshot().backward is False


def test_release_clears_state():
    s = PureKeyState()
    s.press("W")
    s.release("W")
    assert s.snapshot().forward is False


def test_press_idempotent():
    s = PureKeyState()
    s.press("W")
    s.press("W")
    s.release("W")
    assert s.snapshot().forward is False


def test_multiple_keys_simultaneous():
    s = PureKeyState()
    s.press("W")
    s.press("D")
    snap = s.snapshot()
    assert snap.forward and snap.right
    assert not snap.backward
    assert not snap.left


def test_qe_map_to_down_up():
    s = PureKeyState()
    s.press("E")
    assert s.snapshot().up is True
    s.press("Q")
    assert s.snapshot().down is True


def test_escape_edge_consumed_once():
    s = PureKeyState()
    s.press("ESCAPE")
    assert s.consume_escape() is True
    assert s.consume_escape() is False  # already consumed


def test_escape_edge_only_on_press():
    s = PureKeyState()
    # not pressed → no edge
    assert s.consume_escape() is False
    s.release("ESCAPE")
    assert s.consume_escape() is False


def test_release_other_keys_does_not_clear_escape_edge():
    s = PureKeyState()
    s.press("ESCAPE")
    s.press("W")
    s.release("W")
    assert s.consume_escape() is True
