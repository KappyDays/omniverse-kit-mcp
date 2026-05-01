"""Keyboard state tracking for WASD/QE/ESC.

Subscribes to carb.input keyboard events via
``omni.appwindow.get_default_app_window().get_keyboard()`` and exposes a
simple snapshot via ``current()`` / ``snapshot()``.  ESC is reported as a
one-shot edge to be polled by the controller (cleared after read).

Two public classes:

* ``PureKeyState`` — carb-free, used by unit tests (no Kit runtime needed).
* ``KeyboardSubscription`` — carb wrapper that owns the subscription.
* ``InputState`` — alias for ``KeyboardSubscription`` (backward-compat with
  ``interaction_controller.py``).
"""

from __future__ import annotations

# carb.input is not available in plain pytest.  Install stubs first (the test
# file does this), or fall back gracefully inside the classes themselves.
try:
    import carb
    import carb.input
    _CARB_AVAILABLE = True
except Exception:
    _CARB_AVAILABLE = False

try:
    import omni.appwindow  # type: ignore[import]  # may not exist in plain pytest
    _APPWINDOW_AVAILABLE = True
except Exception:
    _APPWINDOW_AVAILABLE = False

from .camera_math import MovementInput

_SOURCE = "omni.mycompany.usd_mouse_interact.input_state"


# ---------------------------------------------------------------------------
# Stand-alone state machine (no carb dependency) — used by unit tests.
# ---------------------------------------------------------------------------


class PureKeyState:
    """Carb-free reimplementation for unit tests.

    Mirrors the press/release accumulation + ESC edge semantics but accepts
    abstract key tokens (any hashable) so tests don't need carb.input enums.
    """

    ESCAPE = "ESCAPE"
    W = "W"
    A = "A"
    S = "S"
    D = "D"
    Q = "Q"
    E = "E"

    def __init__(self) -> None:
        self._pressed: set = set()
        self._escape_edge = False

    def press(self, key) -> None:
        self._pressed.add(key)
        if key == self.ESCAPE:
            self._escape_edge = True

    def release(self, key) -> None:
        self._pressed.discard(key)

    def is_down(self, key) -> bool:
        return key in self._pressed

    def snapshot(self) -> MovementInput:
        return MovementInput(
            forward=self.W in self._pressed,
            backward=self.S in self._pressed,
            left=self.A in self._pressed,
            right=self.D in self._pressed,
            up=self.E in self._pressed,
            down=self.Q in self._pressed,
        )

    def consume_escape(self) -> bool:
        edge = self._escape_edge
        self._escape_edge = False
        return edge


# ---------------------------------------------------------------------------
# carb-touching wrapper
# ---------------------------------------------------------------------------


class KeyboardSubscription:
    """Subscribe to carb keyboard events on the default app window keyboard.

    API mirrors the old ``InputState`` so ``interaction_controller.py`` keeps
    working unchanged:  ``subscribe()`` / ``unsubscribe()`` / ``current()`` /
    ``consume_escape()``.
    """

    def __init__(self) -> None:
        self._input: object | None = None
        self._keyboard: object | None = None
        self._sub_id: object | None = None
        self._pressed: set[int] = set()
        self._escape_edge = False

        # Resolve carb input interface at construction time so subscribe()
        # doesn't have to repeat the error handling.
        if _CARB_AVAILABLE:
            try:
                self._input = carb.input.acquire_input_interface()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[{_SOURCE}] acquire_input_interface failed: {exc!r}")

        if _APPWINDOW_AVAILABLE:
            try:
                aw = omni.appwindow.get_default_app_window()
                if aw is not None:
                    self._keyboard = aw.get_keyboard()
            except Exception as exc:  # noqa: BLE001
                if _CARB_AVAILABLE:
                    carb.log_warn(f"[{_SOURCE}] keyboard handle resolve failed: {exc!r}")

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def subscribe(self) -> None:
        """Start listening to keyboard events (idempotent)."""
        if self._keyboard is None or self._sub_id is not None:
            return
        if self._input is None:
            return
        try:
            self._sub_id = self._input.subscribe_to_keyboard_events(
                self._keyboard, self._on_keyboard_event
            )
        except Exception as exc:  # noqa: BLE001
            if _CARB_AVAILABLE:
                carb.log_warn(f"[{_SOURCE}] keyboard subscribe failed: {exc!r}")
            self._sub_id = None

    # activate() is the plan-style alias for subscribe().
    def activate(self) -> bool:
        """Activate subscription.  Returns True on success."""
        self.subscribe()
        return self._sub_id is not None

    def unsubscribe(self) -> None:
        """Stop listening and reset state."""
        if self._sub_id is not None and self._keyboard is not None and self._input is not None:
            try:
                self._input.unsubscribe_to_keyboard_events(self._keyboard, self._sub_id)
            except Exception as exc:  # noqa: BLE001
                if _CARB_AVAILABLE:
                    carb.log_warn(f"[{_SOURCE}] keyboard unsubscribe failed: {exc!r}")
        self._sub_id = None
        self._pressed.clear()
        self._escape_edge = False

    # deactivate() is the plan-style alias for unsubscribe().
    def deactivate(self) -> None:
        self.unsubscribe()

    # ------------------------------------------------------------------
    # event handler
    # ------------------------------------------------------------------

    def _on_keyboard_event(self, event) -> bool:  # carb.input.KeyboardEvent
        try:
            etype = event.type
            key = event.input
        except AttributeError:
            return True

        try:
            press_types = (
                carb.input.KeyboardEventType.KEY_PRESS,
                carb.input.KeyboardEventType.KEY_REPEAT,
            )
            release_type = carb.input.KeyboardEventType.KEY_RELEASE
        except AttributeError:
            return True

        if etype in press_types:
            self._pressed.add(int(key))
            if key == carb.input.KeyboardInput.ESCAPE:
                self._escape_edge = True
        elif etype == release_type:
            self._pressed.discard(int(key))

        # carb.input convention: callback returns True → event propagates to
        # other subscribers, False → event consumed. We consume our captured
        # navigation keys (W/A/S/D/Q/E + R) so USD Composer's viewport gizmo
        # hotkeys (W = Translate, E = Rotate, R = Scale, Q = Select) do NOT
        # toggle while the ext is in active fly mode. R is *not* a movement
        # key for us, but the gizmo binding is what we want to hide.
        #
        # ESCAPE is intentionally LEFT propagating — the controller's
        # _on_update tick polls _escape_edge to deactivate, but consuming
        # ESC at the callback level would steal the first ESC from any host
        # modal dialog (Save confirm, etc.) since this subscription is
        # bound to the *app-window* keyboard, not viewport-scoped. We still
        # latch the edge above for our own deactivation; the host gets the
        # same event in parallel.
        if key in self._consumed_keys():
            return False
        return True

    @staticmethod
    def _consumed_keys() -> set:
        """Set of carb.input.KeyboardInput values we hide from other handlers."""
        if not _CARB_AVAILABLE:
            return set()
        try:
            ki = carb.input.KeyboardInput
            return {ki.W, ki.A, ki.S, ki.D, ki.Q, ki.E, ki.R}
        except AttributeError:
            return set()

    # ------------------------------------------------------------------
    # accessors
    # ------------------------------------------------------------------

    def _is_down(self, key: "carb.input.KeyboardInput") -> bool:
        return int(key) in self._pressed

    def current(self) -> MovementInput:
        """Snapshot of WASD + QE state."""
        if not _CARB_AVAILABLE:
            return MovementInput()
        try:
            return MovementInput(
                forward=self._is_down(carb.input.KeyboardInput.W),
                backward=self._is_down(carb.input.KeyboardInput.S),
                left=self._is_down(carb.input.KeyboardInput.A),
                right=self._is_down(carb.input.KeyboardInput.D),
                up=self._is_down(carb.input.KeyboardInput.E),
                down=self._is_down(carb.input.KeyboardInput.Q),
            )
        except Exception:  # noqa: BLE001
            return MovementInput()

    def consume_escape(self) -> bool:
        """Return True iff ESCAPE was pressed since the last call (then clear)."""
        edge = self._escape_edge
        self._escape_edge = False
        return edge

    # consume_esc_edge() is the plan-style alias for consume_escape().
    def consume_esc_edge(self) -> bool:
        return self.consume_escape()


# ---------------------------------------------------------------------------
# Backward-compat alias — interaction_controller imports ``InputState``.
# ---------------------------------------------------------------------------

InputState = KeyboardSubscription
