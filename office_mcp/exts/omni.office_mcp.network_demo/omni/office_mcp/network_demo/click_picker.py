"""Viewport click -> PC power-button trigger judgement.

Rather than re-implement NDC raycasting + OS cursor capture, the picker rides
Kit's *native* viewport pick: a left-click in the viewport selects the prim
under the cursor and fires a ``SELECTION_CHANGED`` stage event. The extension
forwards that event here; we resolve whether the selection is the ``trigger``
prim (by path or by an ancestor's ``net:role`` customData) and gate on the
timeline being playing (R2). This is both more robust than hand-rolled
raycasting and directly exercisable in tests via
``get_selection().set_selected_prim_paths([...])``.

The pure decision (``classify_role``) is unit-testable; the stage walk is
Kit-bound but uses only methods on the passed stage object.
"""

from __future__ import annotations

from . import scene_tags

RESULT_NONE = ""
RESULT_TRIGGER = "trigger"
RESULT_TRIGGER_BLOCKED = "trigger_blocked"  # trigger clicked but timeline not playing


class ClickPicker:
    def __init__(self, source: str = "omni.office_mcp.network_demo.click_picker") -> None:
        self._source = source
        self._trigger_path: str | None = None
        self._playing = False

    def set_tags(self, tags) -> None:
        self._trigger_path = tags.trigger if tags is not None else None

    def set_playing(self, playing: bool) -> None:
        self._playing = bool(playing)

    @property
    def playing(self) -> bool:
        return self._playing

    def on_selection_changed(self, stage) -> str:
        """Inspect the current selection; return one of the RESULT_* constants."""
        import carb
        import omni.usd

        try:
            paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] selection read failed: {exc!r}")
            return RESULT_NONE
        if not paths:
            return RESULT_NONE
        for path in paths:
            if self._is_trigger(stage, path):
                return RESULT_TRIGGER if self._playing else RESULT_TRIGGER_BLOCKED
        return RESULT_NONE

    def _is_trigger(self, stage, path: str) -> bool:
        # Fast path: selected prim is the trigger or one of its descendants.
        if self._trigger_path and (
            path == self._trigger_path or path.startswith(self._trigger_path + "/")
        ):
            return True
        # Robust path: walk ancestors reading net:role customData (a click may
        # select a child mesh of the tagged power-button prim).
        try:
            prim = stage.GetPrimAtPath(path)
            while prim and prim.IsValid():
                if prim.GetCustomDataByKey(scene_tags.ROLE_KEY) == scene_tags.ROLE_TRIGGER:
                    return True
                prim = prim.GetParent()
        except Exception:  # noqa: BLE001
            return False
        return False
