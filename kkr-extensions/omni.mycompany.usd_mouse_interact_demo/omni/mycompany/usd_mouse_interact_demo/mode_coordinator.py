"""Runtime mode coordinator for USD Mouse Interact Demo."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from . import metadata_store
from .config_model import UsdMouseInteractConfig
from .mode_state import RuntimeMode, parse_runtime_mode

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.mode_coordinator"


class ModeCoordinator:
    """Owns the shared DevPanel and switches between runtime controllers."""

    def __init__(self, source: str = _SOURCE) -> None:
        self._source = source
        self._config = UsdMouseInteractConfig.default()
        self._mode = parse_runtime_mode(self._config.runtime.default_mode)
        self._armed = False

        self._fps = None
        self._top_view = None
        self._button_mode = None
        self._dev_panel = None
        self._update_sub = None
        self._stage_sub = None

        runtime = self._config.runtime
        self._speed = int(runtime.speed)
        self._sensitivity = int(runtime.sensitivity)
        self._crosshair_color = int(runtime.crosshair_color)
        self._default_camera_applied = False

    @property
    def config(self) -> UsdMouseInteractConfig:
        return self._config

    @property
    def mode(self) -> RuntimeMode:
        return self._mode

    @property
    def is_armed(self) -> bool:
        return self._armed

    @property
    def speed(self) -> int:
        return self._speed

    @speed.setter
    def speed(self, value: int) -> None:
        self._speed = int(value)
        self._sync_runtime_config(speed=self._speed)
        if self._fps is not None:
            self._fps.speed = self._speed

    @property
    def sensitivity(self) -> int:
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, value: int) -> None:
        self._sensitivity = int(value)
        self._sync_runtime_config(sensitivity=self._sensitivity)
        if self._fps is not None:
            self._fps.sensitivity = self._sensitivity
        if self._top_view is not None:
            try:
                self._top_view.set_sensitivity(self._sensitivity)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{self._source}] top view sensitivity failed: {exc!r}")

    @property
    def crosshair_color(self) -> int:
        return self._crosshair_color

    def start(self) -> None:
        self._fps = _make_fps_controller(self._source)
        self._fps.start()

        shared_highlighter = getattr(self._fps, "_highlighter", None)
        self._top_view = _make_top_view_controller(shared_highlighter)
        self._button_mode = _make_button_mode_controller()

        stage = _get_current_stage()
        try:
            self._config = metadata_store.load_config_from_stage(stage)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{self._source}] config load failed: {exc!r}")
            self._config = UsdMouseInteractConfig.default()

        self.apply_config(self._config)

        try:
            self._dev_panel = _make_dev_panel(self)
            self._dev_panel.build()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] dev panel build failed: {exc!r}")
            self._dev_panel = None

        try:
            self._update_sub = _subscribe_update_stream(self._on_update)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] update subscription failed: {exc!r}")
            self._update_sub = None

        try:
            self._stage_sub = _subscribe_stage_stream(self._on_stage_event)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] stage subscription failed: {exc!r}")
            self._stage_sub = None

        self._set_status_label("Idle")

    def stop(self) -> None:
        self._deactivate_current()
        self._armed = False
        self._update_sub = None
        self._stage_sub = None
        try:
            if self._dev_panel is not None:
                self._dev_panel.destroy()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] dev panel destroy failed: {exc!r}")
        self._dev_panel = None
        try:
            if self._fps is not None:
                self._fps.stop()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] fps stop failed: {exc!r}")

    def apply_config(self, config: UsdMouseInteractConfig) -> None:
        self._config = config
        runtime = config.runtime
        self.speed = int(runtime.speed)
        self.sensitivity = int(runtime.sensitivity)
        self.set_crosshair_color(int(runtime.crosshair_color))

        if self._top_view is not None:
            try:
                self._top_view.configure(config.top_view)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{self._source}] top view configure failed: {exc!r}")
        if self._button_mode is not None:
            try:
                self._button_mode.configure(config.button_mode)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{self._source}] button mode configure failed: {exc!r}")

        self.set_mode(parse_runtime_mode(runtime.default_mode))
        self._refresh_dev_panel_config()

    def set_mode(self, mode: Any) -> None:
        next_mode = parse_runtime_mode(mode)
        if next_mode == self._mode:
            if self._mode is RuntimeMode.FPS and self._fps is not None:
                self._fps.set_armed(self._armed)
            return

        was_armed = self._armed
        previous_mode = self._mode
        self._deactivate_current()
        self._mode = next_mode
        self._sync_runtime_config(default_mode=self._mode.value)
        if was_armed:
            if not self._activate_current():
                self._deactivate_current()
                self._mode = previous_mode
                self._sync_runtime_config(default_mode=self._mode.value)
                if self._activate_current():
                    self._set_status_label(
                        "Idle" if self._mode is RuntimeMode.FPS else "Active"
                    )
                else:
                    self._armed = False
                    self._set_status_label("Idle")

    def set_armed(self, value: bool) -> None:
        new_armed = bool(value)
        if new_armed == self._armed:
            return
        self._armed = new_armed
        if new_armed:
            self._apply_default_camera_on_run()
            if self._activate_current():
                self._set_status_label(
                    "Idle" if self._mode is RuntimeMode.FPS else "Active"
                )
            else:
                self._armed = False
                self._set_status_label("Idle")
            return
        self._deactivate_current()
        self._restore_perspective_camera()
        self._default_camera_applied = False
        self._set_status_label("Idle")

    def update_non_fps(self) -> None:
        if not self._armed:
            return
        if self._mode is RuntimeMode.TOP_VIEW and self._top_view is not None:
            self._top_view.update()
        elif self._mode is RuntimeMode.BUTTON_MODE and self._button_mode is not None:
            update = getattr(self._button_mode, "update", None)
            if callable(update):
                update()

    def reload_metadata(self) -> None:
        if self._fps is not None:
            try:
                self._fps.reload_metadata()
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{self._source}] fps metadata reload failed: {exc!r}")
                highlighter = getattr(self._fps, "_highlighter", None)
                if highlighter is not None:
                    try:
                        highlighter.reload_from_stage()
                    except Exception as highlighter_exc:  # noqa: BLE001
                        _log_info(
                            f"[{self._source}] shared highlighter reload failed: {highlighter_exc!r}"
                        )

    def save_config(self) -> None:
        stage = _get_current_stage()
        try:
            metadata_store.save_config_to_stage(stage, self._config)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] config save failed: {exc!r}")

    def set_crosshair_color(self, rgba: int) -> None:
        self._crosshair_color = int(rgba)
        self._sync_runtime_config(crosshair_color=self._crosshair_color)
        if self._fps is not None:
            try:
                self._fps.set_crosshair_color(self._crosshair_color)
            except Exception as exc:  # noqa: BLE001
                _log_info(f"[{self._source}] fps crosshair color failed: {exc!r}")

    def _sync_runtime_config(self, **changes) -> None:
        self._config = replace(
            self._config,
            runtime=replace(self._config.runtime, **changes),
        )

    def _on_update(self, event) -> None:
        del event
        self.update_non_fps()

    def _on_stage_event(self, event) -> None:
        if not _is_stage_opened_event(event):
            return
        self.reload_metadata()
        stage = _get_current_stage()
        try:
            config = metadata_store.load_config_from_stage(stage)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{self._source}] stage config reload failed: {exc!r}")
            return
        self.apply_config(config)
        self._set_status_label(
            "Active" if self._armed and self._mode is not RuntimeMode.FPS else "Idle"
        )

    def _activate_current(self) -> bool:
        if self._mode is RuntimeMode.FPS:
            if self._fps is not None:
                if self._fps.set_armed(True) is False:
                    return False
            return True
        if self._mode is RuntimeMode.TOP_VIEW and self._top_view is not None:
            try:
                return self._top_view.activate() is not False
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{self._source}] top view activate failed: {exc!r}")
                return False
        if self._mode is RuntimeMode.BUTTON_MODE and self._button_mode is not None:
            try:
                self._button_mode.activate()
                return True
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{self._source}] button mode activate failed: {exc!r}")
                return False
        return False

    def _apply_default_camera_on_run(self) -> None:
        camera_path = str(getattr(self._config.runtime, "default_camera_path", "") or "").strip()
        if not camera_path:
            return
        try:
            from .viewport_camera import ViewportCameraSwitcher  # noqa: WPS433

            switcher = ViewportCameraSwitcher()
            if switcher.set_active_camera(camera_path):
                self._default_camera_applied = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] default camera apply failed: {exc!r}")

    def _restore_perspective_camera(self) -> None:
        try:
            from .viewport_camera import ViewportCameraSwitcher  # noqa: WPS433

            switcher = ViewportCameraSwitcher()
            if not switcher.set_perspective_camera():
                _log_warn(f"[{self._source}] perspective camera restore failed")
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{self._source}] perspective camera restore failed: {exc!r}")

    def _deactivate_current(self) -> None:
        if self._mode is RuntimeMode.FPS:
            if self._fps is not None:
                self._fps.set_armed(False)
            return
        if self._mode is RuntimeMode.TOP_VIEW and self._top_view is not None:
            self._top_view.deactivate()
        elif self._mode is RuntimeMode.BUTTON_MODE and self._button_mode is not None:
            self._button_mode.deactivate()

    def _set_status_label(self, text: str) -> None:
        if self._dev_panel is None:
            return
        try:
            self._dev_panel.set_status(text)
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{self._source}] set_status failed: {exc!r}")

    def _refresh_dev_panel_config(self) -> None:
        if self._dev_panel is None:
            return
        refresh = getattr(self._dev_panel, "refresh_config_models", None)
        if not callable(refresh):
            return
        try:
            refresh()
        except Exception as exc:  # noqa: BLE001
            _log_info(f"[{self._source}] dev panel config refresh failed: {exc!r}")


def _make_fps_controller(source: str):
    from .interaction_controller import InteractionController  # noqa: WPS433

    return InteractionController(source=source, build_panel=False)


def _make_top_view_controller(highlighter):
    from .top_view_controller import TopViewController  # noqa: WPS433

    return TopViewController(highlighter)


def _make_button_mode_controller():
    from .button_mode_controller import ButtonModeController  # noqa: WPS433

    return ButtonModeController()


def _make_dev_panel(controller: ModeCoordinator):
    from .dev_panel import DevPanel  # noqa: WPS433

    return DevPanel(controller=controller)


def _get_current_stage():
    try:
        import omni.usd as omni_usd  # noqa: WPS433

        return omni_usd.get_context().get_stage()
    except Exception as exc:  # noqa: BLE001
        _log_info(f"[{_SOURCE}] stage read failed: {exc!r}")
        return None


def _subscribe_update_stream(callback):
    import omni.kit.app  # noqa: WPS433

    update_stream = omni.kit.app.get_app().get_update_event_stream()
    try:
        return update_stream.create_subscription_to_pop(
            callback,
            name="usd_mouse_interact_demo_mode_coordinator_update",
        )
    except TypeError:
        return update_stream.create_subscription_to_pop(callback)


def _subscribe_stage_stream(callback):
    import omni.usd as omni_usd  # noqa: WPS433

    stage_stream = omni_usd.get_context().get_stage_event_stream()
    try:
        return stage_stream.create_subscription_to_pop(
            callback,
            name="usd_mouse_interact_demo_mode_coordinator_stage",
        )
    except TypeError:
        return stage_stream.create_subscription_to_pop(callback)


def _is_stage_opened_event(event) -> bool:
    try:
        import omni.usd as omni_usd  # noqa: WPS433

        return event.type == int(omni_usd.StageEventType.OPENED)
    except Exception as exc:  # noqa: BLE001
        _log_info(f"[{_SOURCE}] stage event decode failed: {exc!r}")
        return False


def _log_info(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_info(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).info(message)


def _log_warn(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning(message)
