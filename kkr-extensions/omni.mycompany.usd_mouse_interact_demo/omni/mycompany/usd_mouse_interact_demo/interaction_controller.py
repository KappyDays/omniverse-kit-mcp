"""Top-level orchestration: timeline → activation toggle → per-frame update.

State machine
-------------
IDLE  ── timeline PLAY ─────►  ACTIVE
ACTIVE ── timeline STOP/PAUSE ─►  IDLE
ACTIVE ── ESC pressed ─────────►  IDLE

The state-only logic lives in ``InteractionStateMachine`` so it can be unit
tested without Kit / USD imports. ``InteractionController`` glues that machine
to the carb-backed components.
"""

from __future__ import annotations

import time

import carb

from .camera_controller import CameraController
from .crosshair_overlay import CrosshairOverlay
from .dev_panel import DevPanel
from .info_overlay import InfoOverlay
from .input_state import InputState
from .mouse_capture import MouseCaptureSession
from .pick_highlighter import PickHighlighter
from .state_machine import InteractionStateMachine, State  # noqa: F401

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.interaction_controller"

# Carb settings overridden during fly mode and restored on deactivate.
#
# scaleMultiplier=0 collapses the Move/Rotate/Scale transform manipulator
# (the axis-arrow gizmo) to zero size so it doesn't render over hovered
# prims. The selection outline (Kit's default orange) stays intact.
#
# Why this key (and not /app/transform/operation = "select"):
#   Setting transform/operation to "select" *also* hides the gizmo, but
#   it disables selection-outline rendering on Kit 110 / USD Composer —
#   verified by A/B capture comparison (2026-04-27). The manipulator's
#   own scaleMultiplier toggles only the axis arrows, leaving selection
#   display untouched. Source for the key:
#   omni.kit.manipulator.transform/settings_constants.py:41
#   (Constants.MANIPULATOR_SCALE_SETTING). Default value is the user's
#   chosen visual size (typically 1.0).
_FLY_MODE_SETTING_OVERRIDES = {
    "/persistent/exts/omni.kit.manipulator.transform/manipulator/scaleMultiplier": 0.0,
}


class InteractionController:

    def __init__(self, source: str = _SOURCE, build_panel: bool = True) -> None:
        self._source = source
        self._build_panel = bool(build_panel)
        self._sm = InteractionStateMachine()

        self._input_state = InputState()
        self._camera = CameraController()
        self._mouse = MouseCaptureSession()
        self._crosshair = CrosshairOverlay()
        self._info = InfoOverlay()
        self._highlighter = PickHighlighter(self._info)
        self._fps_input_router = self._build_fps_input_router()

        self._timeline_sub = None
        self._update_sub = None
        self._stage_sub = None
        self._timeline = None
        self._dev_panel: DevPanel | None = None

        # Saved fly-mode setting overrides captured at _activate; values
        # may be None when the host had not initialised that key — we
        # still restore by rewriting whatever we captured. Keys mirror
        # _FLY_MODE_SETTING_OVERRIDES.
        self._saved_overrides: dict[str, object] = {}

        # Per-user-facing settings (exposed to dev_panel sliders later)
        self.speed: int = 500
        self.sensitivity: int = 25
        # ABGR int — translucent red default. Backed by CrosshairOverlay.
        # Keep in sync with crosshair_overlay._DEFAULT_COLOR.
        self.crosshair_color: int = 0xCC0000FF
        # Run-arm gate. When False, timeline PLAY does NOT drop us into
        # ACTIVE. The DevPanel "Run mouse-interaction" checkbox flips this
        # via set_armed(). Default Off so an existing scene's Play button
        # behaves normally until the operator opts in.
        self._armed: bool = False

    # ------------------------------------------------------------------
    # public state property (spec §Phase 8 + dev_panel)
    # ------------------------------------------------------------------

    @property
    def state(self) -> State:
        return self._sm.state

    @property
    def info_overlay(self) -> InfoOverlay:
        return self._info

    # ------------------------------------------------------------------
    # lifecycle — extension.py calls start() / stop()
    # ------------------------------------------------------------------

    def start(self) -> None:
        try:
            import omni.kit.app
            import omni.timeline
            import omni.usd
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{self._source}] kit imports failed: {exc!r}")
            return

        self._timeline = omni.timeline.get_timeline_interface()
        try:
            self._timeline_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
                self._on_timeline_event, name="usd_mouse_interact_demo_timeline"
            )
        except TypeError:
            self._timeline_sub = (
                self._timeline.get_timeline_event_stream().create_subscription_to_pop(
                    self._on_timeline_event
                )
            )

        try:
            self._update_sub = (
                omni.kit.app.get_app()
                .get_update_event_stream()
                .create_subscription_to_pop(
                    self._on_update, name="usd_mouse_interact_demo_update"
                )
            )
        except TypeError:
            self._update_sub = (
                omni.kit.app.get_app()
                .get_update_event_stream()
                .create_subscription_to_pop(self._on_update)
            )

        # Stage event subscription — reload whitelist metadata on stage open.
        try:
            stage_events = omni.usd.get_context().get_stage_event_stream()
            self._stage_sub = stage_events.create_subscription_to_pop(
                self._on_stage_event, name="usd_mouse_interact_demo_stage"
            )
        except TypeError:
            try:
                stage_events = omni.usd.get_context().get_stage_event_stream()
                self._stage_sub = stage_events.create_subscription_to_pop(
                    self._on_stage_event
                )
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[{self._source}] stage event sub failed: {exc!r}")

        # Pre-load whitelist from current stage (if one is open already).
        try:
            self._highlighter.reload_from_stage()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] initial reload_from_stage failed: {exc!r}")

        if self._build_panel:
            # Build operator panel — whitelist editor + tuning sliders.
            try:
                self._dev_panel = DevPanel(controller=self)
                self._dev_panel.build()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[{self._source}] dev panel build failed: {exc!r}")

        # If timeline is already playing when we start, activate immediately
        # — but only when the operator has armed Run on the DevPanel.
        try:
            if self._armed and self._timeline.is_playing():
                if self._sm.on_play():
                    self._activate()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] is_playing probe failed: {exc!r}")

        # Push initial status to DevPanel.
        self._set_status_label("Idle")

        carb.log_warn(f"[{self._source}] subscribed (timeline + update + stage)")

    def _build_fps_input_router(self):
        try:
            from .fps_input_router import FpsInputRouter
            from .stream_input_backend import StreamMessageBackend

            return FpsInputRouter([StreamMessageBackend()])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] stream input router init failed: {exc!r}")
            return None

    def stop(self) -> None:
        # Force state machine to IDLE first. Without this, the timeline-event
        # path (which gates _deactivate on _sm.on_stop()) is bypassed when stop()
        # is called directly during ACTIVE — a window opens where _on_update can
        # fire against a deactivating controller.
        self._sm.on_stop()
        self._deactivate()
        # Kit IEventStream subscriptions are reference-counted; dropping the
        # Python ref is the documented release mechanism. Null the attributes
        # so no other path can keep the callback alive.
        self._timeline_sub = None
        self._update_sub = None
        self._stage_sub = None
        self._timeline = None
        try:
            self._crosshair.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] crosshair destroy failed: {exc!r}")
        try:
            self._info.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] info overlay destroy failed: {exc!r}")
        try:
            if self._dev_panel is not None:
                self._dev_panel.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] dev panel destroy failed: {exc!r}")
        self._dev_panel = None

    # ------------------------------------------------------------------
    # event handlers
    # ------------------------------------------------------------------

    def _on_timeline_event(self, event) -> None:
        try:
            import omni.timeline

            etype = event.type
        except Exception:  # noqa: BLE001
            return
        try:
            t_play = int(omni.timeline.TimelineEventType.PLAY)
            t_stop = int(omni.timeline.TimelineEventType.STOP)
            t_pause = int(omni.timeline.TimelineEventType.PAUSE)
        except Exception:  # noqa: BLE001
            return

        if etype == t_play:
            if self._armed and self._sm.on_play():
                self._activate()
        elif etype in (t_stop, t_pause):
            if self._sm.on_stop():
                self._deactivate()

    def _on_stage_event(self, event) -> None:
        try:
            import omni.usd

            if event.type == int(omni.usd.StageEventType.OPENED):
                self._highlighter.reload_from_stage()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] stage event handler failed: {exc!r}")

    def _on_update(self, event) -> None:
        if not self._sm.is_active():
            return

        if self._input_state.consume_escape():
            if self._sm.on_escape():
                self._deactivate()
            return

        # Crosshair follow-up + mouse delta
        try:
            self._crosshair.update_position()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] crosshair update failed: {exc!r}")

        center = self._mouse.viewport_window_center()
        now_s = time.monotonic()
        dx, dy, keys, _backend_name = self._sample_existing_local_input(center, now_s)

        # dt — prefer event payload, fall back to 1/60
        try:
            payload = event.payload
            dt = float(payload["dt"])
        except Exception:  # noqa: BLE001
            dt = 1.0 / 60.0

        try:
            self._camera.apply(
                dx, dy, keys,
                float(self.speed), float(self.sensitivity), dt
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] camera apply failed: {exc!r}")

        try:
            self._highlighter.update_at_center()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] highlighter failed: {exc!r}")

    def _sample_existing_local_input(self, center, now_s):
        router = getattr(self, "_fps_input_router", None)
        if router is not None:
            try:
                sample = router.sample(center, now_s)
                if sample is not None and sample.active:
                    return sample.dx, sample.dy, sample.keys, sample.backend_name
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{self._source}] fps input router sample failed: {exc!r}")
        dx = dy = 0.0
        if center is not None:
            dx, dy = self._mouse.read_delta_and_warp(*center)
        return dx, dy, self._input_state.current(), "local-cursor-warp"

    # ------------------------------------------------------------------
    # activation
    # ------------------------------------------------------------------

    def _activate(self) -> bool:
        carb.log_warn(f"[{self._source}] ACTIVATE")
        try:
            if not self._camera.activate():
                carb.log_warn(f"[{self._source}] camera activate failed — aborting activation")
                self._sm.on_stop()   # roll back state machine
                return False
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] camera activate exc: {exc!r}")
            self._sm.on_stop()
            return False
        try:
            self._input_state.subscribe()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] input subscribe failed: {exc!r}")
        try:
            if self._fps_input_router is not None:
                self._fps_input_router.activate()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] fps input router activate failed: {exc!r}")
        try:
            self._mouse.activate()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] mouse activate failed: {exc!r}")
        try:
            self._crosshair.show()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] crosshair show failed: {exc!r}")
        try:
            self._highlighter.reload_from_stage()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] reload_from_stage on activate failed: {exc!r}")
        self._set_status_label("Active")
        # Apply fly-mode setting overrides (e.g. shrink the transform
        # manipulator so it doesn't draw over hovered prims). Restored
        # in _deactivate. See _FLY_MODE_SETTING_OVERRIDES.
        try:
            settings = carb.settings.get_settings()
            self._saved_overrides.clear()
            for key, override in _FLY_MODE_SETTING_OVERRIDES.items():
                self._saved_overrides[key] = settings.get(key)
                settings.set(key, override)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] fly mode override failed: {exc!r}")
            self._saved_overrides.clear()
        return True

    def _deactivate(self) -> None:
        carb.log_warn(f"[{self._source}] DEACTIVATE")
        try:
            self._mouse.deactivate()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] mouse deactivate failed: {exc!r}")
        try:
            if self._fps_input_router is not None:
                self._fps_input_router.deactivate()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] fps input router deactivate failed: {exc!r}")
        try:
            self._input_state.unsubscribe()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] input unsubscribe failed: {exc!r}")
        try:
            self._crosshair.hide()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] crosshair hide failed: {exc!r}")
        try:
            self._info.hide()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] info hide failed: {exc!r}")
        try:
            self._highlighter.clear()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] highlighter clear failed: {exc!r}")
        try:
            self._camera.deactivate()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] camera deactivate failed: {exc!r}")
        # Restore fly-mode setting overrides. None saved values are skipped
        # (the host hadn't initialised that key — leaving the override in
        # place would be wrong, but explicit set(key, None) raises on some
        # carb builds; safer to leave Kit's default to re-establish itself).
        if self._saved_overrides:
            try:
                settings = carb.settings.get_settings()
                for key, saved in self._saved_overrides.items():
                    if saved is None:
                        continue
                    try:
                        settings.set(key, saved)
                    except Exception as exc:  # noqa: BLE001
                        carb.log_info(f"[{self._source}] restore {key} failed: {exc!r}")
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{self._source}] override restore failed: {exc!r}")
            self._saved_overrides.clear()
        self._set_status_label("Idle")

    # ------------------------------------------------------------------
    # introspection (helpers for tests / status panels)
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._sm.is_active()

    @property
    def is_armed(self) -> bool:
        return self._armed

    def set_armed(self, value: bool) -> bool:
        """Toggle the run-arm gate from the DevPanel.

        - True: subsequent timeline PLAY drops us into ACTIVE; if the
          timeline is already playing, activate now.
        - False: if currently ACTIVE, deactivate immediately.
        """
        new_armed = bool(value)
        if new_armed == self._armed:
            return True
        self._armed = new_armed
        if not new_armed:
            if self._sm.on_stop():
                self._deactivate()
            else:
                self._set_status_label("Idle")
            return True
        # Armed True — opportunistically activate when timeline is already
        # playing. Otherwise the next PLAY event will pick us up.
        try:
            if self._timeline is not None and self._timeline.is_playing():
                if self._sm.on_play():
                    return self._activate()
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] is_playing probe in set_armed failed: {exc!r}")
        self._set_status_label("Idle")
        return True

    def _set_status_label(self, text: str) -> None:
        """Push a one-word state ('Active' / 'Idle') to the DevPanel.

        Best-effort — DevPanel may not be built yet at start-time, and the
        panel may have torn down before stop() finishes. Either path is
        non-fatal.
        """
        if self._dev_panel is None:
            return
        try:
            self._dev_panel.set_status(text)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] set_status failed: {exc!r}")

    # reload_metadata — called from stage OPENED or externally (DevPanel save).
    def reload_metadata(self) -> None:
        if self._timeline is None:
            # Pre-start() — no Kit context wired yet; defer.
            return
        self._highlighter.reload_from_stage()

    # set_crosshair_color — called from DevPanel ColorWidget on change.
    def set_crosshair_color(self, rgba: int) -> None:
        self.crosshair_color = int(rgba)
        try:
            self._crosshair.set_color(self.crosshair_color)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{self._source}] set_crosshair_color failed: {exc!r}")
