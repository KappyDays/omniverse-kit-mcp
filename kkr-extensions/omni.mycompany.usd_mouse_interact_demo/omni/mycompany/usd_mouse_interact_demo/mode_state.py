"""Pure runtime mode and button mode state helpers."""

from __future__ import annotations

from enum import Enum


class RuntimeMode(str, Enum):
    FPS = "fps"
    TOP_VIEW = "top_view"
    BUTTON_MODE = "button_mode"


class ButtonModeState(str, Enum):
    BUTTON_HUD = "button_hud"
    EXPLORING_READY = "exploring_ready"
    EXPLORING_TOUR = "exploring_tour"
    PREVIEW_CHOOSER = "preview_chooser"
    CAMERA_DETAIL = "camera_detail"


def parse_runtime_mode(value: object) -> RuntimeMode:
    try:
        return RuntimeMode(value)
    except (TypeError, ValueError):
        return RuntimeMode.FPS


def transition_button_state(
    state: ButtonModeState,
    action: str,
) -> ButtonModeState:
    transitions = {
        (ButtonModeState.BUTTON_HUD, "open_preview"): ButtonModeState.PREVIEW_CHOOSER,
        (ButtonModeState.PREVIEW_CHOOSER, "back"): ButtonModeState.BUTTON_HUD,
        (ButtonModeState.PREVIEW_CHOOSER, "open_detail"): ButtonModeState.CAMERA_DETAIL,
        (ButtonModeState.CAMERA_DETAIL, "back"): ButtonModeState.PREVIEW_CHOOSER,
    }
    return transitions.get((state, action), state)
