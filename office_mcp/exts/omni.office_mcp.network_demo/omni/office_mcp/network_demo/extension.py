"""Office-DataCenter Network Demo — extension entry point.

UI: a single window with a ``Load Scene`` button and a status ``Label``
(English only — Kit 107 font atlas has no CJK glyphs).

Flow (SPEC §7):
  Load Scene -> fresh stage + deadlock-safe reference + tag discovery + bind
  native Play -> picker armed, label "Ready"
  viewport click on PC power button -> SELECTION_CHANGED -> transmission.start()
  per-frame update -> progress wave (cable emissive) + sequential server LEDs
"""

from __future__ import annotations

import time

import omni.ext
import omni.ui as ui

from . import scene_tags, telemetry
from .click_picker import RESULT_TRIGGER, RESULT_TRIGGER_BLOCKED, ClickPicker
from .scene_loader import load_scene
from .transmission import STATUS_DELIVERED, STATUS_TRANSMITTING, TransmissionController

_SOURCE = "omni.office_mcp.network_demo"
_WINDOW_TITLE = "Office Network Demo"
_HINT_SECONDS = 2.5

# Module-level handle to the live extension instance — lets self-test / MCP
# automation reach the running controller (robot_lidar pattern). Not used by
# the demo flow itself.
_INSTANCE = None


def get_instance():
    return _INSTANCE


class OfficeNetworkDemoExtension(omni.ext.IExt):

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def on_startup(self, ext_id: str) -> None:
        import carb

        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        global _INSTANCE
        _INSTANCE = self
        self._ext_id = ext_id
        # USD-load deadlock invariant: never register a carb logger on startup.
        self._log_capture = None

        self._window: ui.Window | None = None
        self._status_label: ui.Label | None = None
        self._btn_load: ui.Button | None = None
        self._last_label: str | None = None

        self._scene_loaded = False
        self._loading = False
        self._playing = False
        self._error = ""
        self._hint_until = 0.0

        self._transmission = TransmissionController()
        self._picker = ClickPicker()

        self._update_sub = None
        self._timeline_sub = None
        self._stage_sub = None
        self._timeline = None

        self._build_window()
        self._subscribe()

    def on_shutdown(self) -> None:
        import carb

        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        global _INSTANCE
        if _INSTANCE is self:
            _INSTANCE = None
        self._update_sub = None
        self._timeline_sub = None
        self._stage_sub = None
        self._timeline = None
        try:
            self._transmission.unbind()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] transmission unbind soft-fail: {exc!r}")
        # Zombie-window cleanup (ext-reload invariant L16).
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[{_SOURCE}] window destroy soft-fail: {exc!r}")
            self._window = None
        self._status_label = None
        self._btn_load = None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_window(self) -> None:
        existing = ui.Workspace.get_window(_WINDOW_TITLE)
        if existing is not None:
            try:
                existing.visible = False
                existing.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._window = ui.Window(_WINDOW_TITLE, width=440, height=150)
        with self._window.frame:
            with ui.VStack(spacing=8, height=0):
                ui.Label(
                    "Office - DataCenter Network Demo",
                    height=0,
                    style={"font_size": 16},
                )
                self._btn_load = ui.Button(
                    "Load Scene", height=32, clicked_fn=self._on_load,
                )
                self._status_label = ui.Label(
                    telemetry.format_status(telemetry.PHASE_NO_SCENE),
                    height=0,
                    word_wrap=True,
                )
        self._last_label = None
        self._refresh_label()

    # ------------------------------------------------------------------
    # event subscriptions
    # ------------------------------------------------------------------
    def _subscribe(self) -> None:
        import carb
        import omni.kit.app
        import omni.timeline
        import omni.usd

        self._timeline = omni.timeline.get_timeline_interface()
        try:
            self._update_sub = (
                omni.kit.app.get_app()
                .get_update_event_stream()
                .create_subscription_to_pop(self._on_update, name=f"{_SOURCE}.update")
            )
            self._timeline_sub = (
                self._timeline.get_timeline_event_stream()
                .create_subscription_to_pop(self._on_timeline_event, name=f"{_SOURCE}.timeline")
            )
            self._stage_sub = (
                omni.usd.get_context()
                .get_stage_event_stream()
                .create_subscription_to_pop(self._on_stage_event, name=f"{_SOURCE}.stage")
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] subscribe failed: {exc!r}")
        # Reflect current play state immediately (scene may already be playing).
        try:
            self._playing = bool(self._timeline.is_playing())
            self._picker.set_playing(self._playing)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Load Scene
    # ------------------------------------------------------------------
    def _on_load(self) -> None:
        import omni.kit.async_engine

        if self._loading:
            return
        self._loading = True
        self._error = ""
        self._refresh_label()
        if self._btn_load is not None:
            self._btn_load.enabled = False
        omni.kit.async_engine.run_coroutine(self._do_load())

    async def _do_load(self) -> None:
        import carb
        import omni.usd

        try:
            result = await load_scene()
            stage = omni.usd.get_context().get_stage()
            tags = result.get("tags")
            if not result.get("ok"):
                self._error = result.get("error", "load failed")
                self._scene_loaded = False
                carb.log_error(f"[{_SOURCE}] load failed: {self._error}")
                return
            self._picker.set_tags(tags)
            bound = self._transmission.bind(stage, tags)
            if not bound:
                self._error = "No emissive material inputs found on cables/LEDs"
                self._scene_loaded = False
                return
            self._scene_loaded = True
            self._error = ""
            carb.log_warn(
                f"[{_SOURCE}] scene loaded: trigger={tags.trigger} "
                f"cables={len(tags.cables)} servers={len(tags.server_leds)}"
            )
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            self._scene_loaded = False
            carb.log_error(f"[{_SOURCE}] _do_load exception: {exc!r}")
        finally:
            self._loading = False
            if self._btn_load is not None:
                self._btn_load.enabled = True
            self._refresh_label()

    # ------------------------------------------------------------------
    # per-frame + events
    # ------------------------------------------------------------------
    def _on_update(self, event) -> None:
        try:
            dt = float(event.payload["dt"])
        except Exception:  # noqa: BLE001
            dt = 1.0 / 60.0
        try:
            self._transmission.on_update(dt)
        except Exception as exc:  # noqa: BLE001
            import carb
            carb.log_info(f"[{_SOURCE}] transmission update soft-fail: {exc!r}")
        self._refresh_label()

    def _on_timeline_event(self, event) -> None:
        import omni.timeline

        try:
            etype = event.type
            t_play = int(omni.timeline.TimelineEventType.PLAY)
            t_stop = int(omni.timeline.TimelineEventType.STOP)
            t_pause = int(omni.timeline.TimelineEventType.PAUSE)
        except Exception:  # noqa: BLE001
            return
        if etype == t_play:
            self._playing = True
        elif etype in (t_stop, t_pause):
            self._playing = False
            if etype == t_stop:
                try:
                    self._transmission.reset_visuals()
                except Exception:  # noqa: BLE001
                    pass
        self._picker.set_playing(self._playing)

    def _on_stage_event(self, event) -> None:
        import carb
        import omni.usd

        try:
            if event.type != int(omni.usd.StageEventType.SELECTION_CHANGED):
                return
        except Exception:  # noqa: BLE001
            return
        if not self._scene_loaded:
            return
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        try:
            result = self._picker.on_selection_changed(stage)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] picker soft-fail: {exc!r}")
            return
        if result == RESULT_TRIGGER:
            self._transmission.start()
            # Clear selection so the same button can be clicked again to restart.
            try:
                omni.usd.get_context().get_selection().set_selected_prim_paths([], True)
            except Exception:  # noqa: BLE001
                pass
        elif result == RESULT_TRIGGER_BLOCKED:
            self._hint_until = time.time() + _HINT_SECONDS

    # ------------------------------------------------------------------
    # status label
    # ------------------------------------------------------------------
    def _current_phase(self) -> str:
        if self._loading:
            return telemetry.PHASE_LOADING
        if self._error:
            return telemetry.PHASE_ERROR
        if not self._scene_loaded:
            return telemetry.PHASE_NO_SCENE
        if time.time() < self._hint_until:
            return telemetry.PHASE_NOT_PLAYING
        model = self._transmission.model
        if model is not None:
            if model.status == STATUS_TRANSMITTING:
                return telemetry.PHASE_TRANSMITTING
            if model.status == STATUS_DELIVERED:
                return telemetry.PHASE_DELIVERED
        if self._playing:
            return telemetry.PHASE_READY
        return telemetry.PHASE_SCENE_LOADED

    def _refresh_label(self) -> None:
        if self._status_label is None:
            return
        phase = self._current_phase()
        model = self._transmission.model
        progress = model.progress if model is not None else 0.0
        target = model.current_target() if model is not None else 0
        total = len(model.server_orders) if model is not None else 0
        lit = model.lit_count() if model is not None else 0
        text = telemetry.format_status(
            phase,
            progress=progress,
            target_server=target,
            total_servers=total,
            lit_servers=lit,
            detail=self._error,
        )
        if text != self._last_label:
            try:
                self._status_label.text = text
            except Exception:  # noqa: BLE001
                return
            self._last_label = text
