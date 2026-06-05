"""Controller for USD Mouse Interact Demo button mode."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .config_model import ButtonModeConfig, UsdMouseInteractConfig, camera_set_size_for_key
from .mode_state import ButtonModeState
from .preview_capture import CaptureResult, PreviewCapture

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.button_mode_controller"
_TOUR_KEYS = ("b", "a")
_RACKS_F_PRIM = "/World/Environment/A_DataCenter/Imagine_AI/Racks_F"
_RACKS_E_PRIM = "/World/Environment/A_DataCenter/Imagine_AI/Racks_E"
_BUTTON_B_CAMERA_HIDE_PRIMS = {
    4: _RACKS_F_PRIM,
    5: _RACKS_E_PRIM,
}
_BUTTON_A_CAMERA_5_HIDE_PRIMS = (
    "/World/AI_Grad_ext/AX_living_lab_building/AI_graduate_extension/windows/frame_003",
    "/World/AI_Grad_ext/AX_living_lab_building/AI_graduate_extension/building/innerwall",
    "/World/AI_Grad_ext/assembly_table_01",
    "/World/AI_Grad_ext/AX_living_lab_building/AI_graduate_extension/windows/window",
)


def _log_warn(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning(message)


class ButtonModeController:
    """Play the Exploring tour and capture previews from the active viewport."""

    def __init__(
        self,
        *,
        overlay: Any | None = None,
        capture: Any | None = None,
        camera_switcher: Any | None = None,
    ) -> None:
        self.overlay = overlay if overlay is not None else self._make_overlay()
        self.capture = capture if capture is not None else PreviewCapture(
            allow_viewport_fallback=False
        )
        self.camera_switcher = (
            camera_switcher
            if camera_switcher is not None
            else self._make_camera_switcher()
        )
        self.config: ButtonModeConfig = UsdMouseInteractConfig.default().button_mode
        self.state: ButtonModeState | None = None
        self.active = False
        self.preview_results: list[CaptureResult] = []
        self.preview_cameras: list[str] = []
        self._tour_task: Any | None = None
        self._layout_task: Any | None = None
        self._request_id = 0
        self._saved_tour_camera = ""
        self._last_run_overlay_size: tuple[int, int] | None = None
        self._last_preview_overlay_size: tuple[int, int] | None = None
        self._showing_final_preview = False
        self._showing_preview_matrix = False

    def configure(self, config: ButtonModeConfig) -> None:
        self.config = config
        self._last_run_overlay_size = None
        self._last_preview_overlay_size = None
        set_fallback = getattr(self.capture, "set_allow_viewport_fallback", None)
        if callable(set_fallback):
            try:
                set_fallback(False)
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{_SOURCE}] capture fallback configure failed: {exc!r}")
        if self.active and self.state is ButtonModeState.EXPLORING_READY:
            self.overlay.show_run_buttons(self.config, self._on_exploring_clicked)
        elif (
            self.active
            and self.state is ButtonModeState.EXPLORING_TOUR
            and self._showing_final_preview
        ):
            self.overlay.show_capture_matrix(
                self.preview_results,
                self.config,
                self._on_final_preview_back,
            )
        elif (
            self.active
            and self.state is ButtonModeState.EXPLORING_TOUR
            and self._showing_preview_matrix
        ):
            self.overlay.show_capture_matrix(self.preview_results, self.config)

    def activate(self) -> None:
        self.active = True
        self.state = ButtonModeState.EXPLORING_READY
        self.preview_results = []
        self.preview_cameras = []
        self._showing_final_preview = False
        self._showing_preview_matrix = False
        self._request_id += 1
        self._last_run_overlay_size = None
        self._last_preview_overlay_size = None
        self.overlay.show_run_buttons(self.config, self._on_exploring_clicked)
        self._cancel_task("_layout_task")
        self._layout_task = self._schedule(self._watch_overlay_layout(self._request_id))

    def deactivate(self) -> None:
        self.active = False
        self._request_id += 1
        self._cancel_task("_layout_task")
        self._cancel_task("_tour_task")
        self._restore_tour_camera()
        self._unhide_button_b_prims()
        self._unhide_button_a_prims()
        self.state = None
        self.preview_results = []
        self.preview_cameras = []
        self._showing_final_preview = False
        self._showing_preview_matrix = False
        self._last_run_overlay_size = None
        self._last_preview_overlay_size = None
        self.overlay.shutdown()

    def _on_exploring_clicked(self) -> None:
        if not self.active or self.state is ButtonModeState.EXPLORING_TOUR:
            return
        self._showing_final_preview = False
        self._showing_preview_matrix = False
        self._cancel_task("_layout_task")
        self._cancel_task("_tour_task")
        self._tour_task = self._schedule(self._run_exploring_tour(self._request_id))

    async def _run_exploring_tour(self, request_id: int) -> None:
        if not self.active:
            return
        self.state = ButtonModeState.EXPLORING_TOUR
        self.overlay.show_loading("Preparing...", self.config)
        tour_completed = False
        try:
            self._save_tour_camera()
            for key_index, key in enumerate(_TOUR_KEYS):
                if not self.active or request_id != self._request_id:
                    return
                if key == "a":
                    self._unhide_button_b_prims()
                results = await self._capture_for_key(key)
                results = await self._play_camera_sequence(str(key), results)
                if not self.active or request_id != self._request_id:
                    return
                if key == "a":
                    self._unhide_button_a_prims()
                if key_index == len(_TOUR_KEYS) - 1:
                    tour_completed = True
                    self.state = ButtonModeState.EXPLORING_TOUR
                    self.preview_results = list(results)
                    self.preview_cameras = [result.camera_path for result in results]
                    self._showing_final_preview = True
                    self._showing_preview_matrix = False
                    self._last_preview_overlay_size = self._current_overlay_size()
                    self.overlay.show_capture_matrix(
                        results,
                        self.config,
                        self._on_final_preview_back,
                    )
                    self._layout_task = self._schedule(
                        self._watch_overlay_layout(request_id)
                    )
                    return
                self._showing_final_preview = False
                self._showing_preview_matrix = True
                self.preview_results = list(results)
                self.preview_cameras = [result.camera_path for result in results]
                self._last_preview_overlay_size = self._current_overlay_size()
                self.overlay.show_capture_matrix(results, self.config)
                self._layout_task = self._schedule(self._watch_overlay_layout(request_id))
                await _wait_seconds(self.config.tour_matrix_hold_seconds)
                self._showing_preview_matrix = False
                self._cancel_task("_layout_task")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] exploring tour failed: {exc!r}")
        finally:
            if not (tour_completed and self.active and request_id == self._request_id):
                self._restore_tour_camera()
                self._unhide_button_b_prims()
                self._unhide_button_a_prims()
                if self.active and request_id == self._request_id:
                    self.state = ButtonModeState.EXPLORING_READY
                    self._showing_final_preview = False
                    self._showing_preview_matrix = False
                    self._last_run_overlay_size = None
                    self._last_preview_overlay_size = None
                    self.overlay.show_run_buttons(self.config, self._on_exploring_clicked)
                    self._cancel_task("_layout_task")
                    self._layout_task = self._schedule(
                        self._watch_overlay_layout(request_id)
                    )

    def _on_final_preview_back(self) -> None:
        if not self.active:
            return
        self._request_id += 1
        request_id = self._request_id
        self._cancel_task("_tour_task")
        self._cancel_task("_layout_task")
        self._restore_tour_camera()
        self._unhide_button_b_prims()
        self._unhide_button_a_prims()
        self.state = ButtonModeState.EXPLORING_READY
        self._showing_final_preview = False
        self._showing_preview_matrix = False
        self._last_run_overlay_size = None
        self._last_preview_overlay_size = None
        self.overlay.show_run_buttons(self.config, self._on_exploring_clicked)
        self._layout_task = self._schedule(self._watch_overlay_layout(request_id))

    async def _watch_overlay_layout(self, request_id: int) -> None:
        while self.active and request_id == self._request_id:
            if self.state is ButtonModeState.EXPLORING_READY:
                size = self._current_overlay_size()
                if size is not None and size != self._last_run_overlay_size:
                    self._last_run_overlay_size = size
                    self.overlay.show_run_buttons(self.config, self._on_exploring_clicked)
            elif self.state is ButtonModeState.EXPLORING_TOUR:
                size = self._current_overlay_size()
                if size is not None and size != self._last_preview_overlay_size:
                    self._last_preview_overlay_size = size
                    if self._showing_final_preview:
                        self.overlay.show_capture_matrix(
                            self.preview_results,
                            self.config,
                            self._on_final_preview_back,
                        )
                    elif self._showing_preview_matrix:
                        self.overlay.show_capture_matrix(self.preview_results, self.config)
            await _next_update()

    async def _capture_for_key(self, key: str) -> list[CaptureResult]:
        prepared = _prepare_camera_results(
            str(key),
            self.config.camera_sets.get(str(key), []),
            self.config.preview_width,
            self.config.preview_height,
        )
        valid_count = sum(1 for item in prepared if item.valid_camera_path)
        if valid_count:
            _log_warn(
                f"[{_SOURCE}] prepared {valid_count} camera(s) for {key}; "
                "captures will be taken from the active viewport during tour"
            )
        merged = _merge_capture_results(prepared, [])
        self.preview_results = merged
        self.preview_cameras = [result.camera_path for result in merged]
        return merged

    async def _play_camera_sequence(
        self,
        key: str,
        results: list[CaptureResult],
    ) -> list[CaptureResult]:
        clear_ui = getattr(self.overlay, "clear_current_state_ui", None)
        if callable(clear_ui):
            clear_ui()

        refreshed = list(results)
        playable: list[tuple[int, str]] = []
        for index, result in enumerate(refreshed):
            camera_path = _normalize_camera_path(result.camera_path)
            if camera_path is None:
                continue
            playable.append((index, camera_path))

        for playable_index, (result_index, camera_path) in enumerate(playable):
            is_last = playable_index == len(playable) - 1
            hold = (
                self.config.tour_final_hold_seconds
                if is_last
                else self.config.tour_camera_hold_seconds
            )
            try:
                self.camera_switcher.set_active_camera(camera_path)
            except Exception as exc:  # noqa: BLE001
                _log_warn(f"[{_SOURCE}] camera switch failed: {exc!r}")
                continue
            target_time = _monotonic() + max(0.0, float(hold))
            self._apply_camera_visibility_override(key, result_index)
            await _next_update()
            refreshed[result_index] = await self.capture.capture_active_viewport(
                camera_path,
                self.config.preview_width,
                self.config.preview_height,
            )
            if refreshed[result_index].error:
                _log_warn(
                    f"[{_SOURCE}] preview unavailable for {camera_path}: "
                    f"{refreshed[result_index].error}"
                )
            await _wait_seconds(max(0.0, target_time - _monotonic()))
        return refreshed

    def _apply_camera_visibility_override(self, key: str, result_index: int) -> None:
        clean_key = str(key).strip().lower()
        if clean_key == "a":
            if int(result_index) == 4:
                self._hide_button_a_prims()
            return
        if clean_key != "b":
            return
        if int(result_index) == 5:
            _set_prim_visibility(_RACKS_F_PRIM, visible=True)
        prim_path = _BUTTON_B_CAMERA_HIDE_PRIMS.get(int(result_index))
        if not prim_path:
            return
        _set_prim_visibility(prim_path, visible=False)

    def _unhide_button_b_prims(self) -> None:
        for prim_path in _BUTTON_B_CAMERA_HIDE_PRIMS.values():
            _set_prim_visibility(prim_path, visible=True)

    def _hide_button_a_prims(self) -> None:
        for prim_path in _BUTTON_A_CAMERA_5_HIDE_PRIMS:
            _set_prim_visibility(prim_path, visible=False)

    def _unhide_button_a_prims(self) -> None:
        for prim_path in _BUTTON_A_CAMERA_5_HIDE_PRIMS:
            _set_prim_visibility(prim_path, visible=True)

    def _save_tour_camera(self) -> None:
        if self._saved_tour_camera:
            return
        try:
            self._saved_tour_camera = self.camera_switcher.get_active_camera()
        except Exception as exc:  # noqa: BLE001
            self._saved_tour_camera = ""
            _log_warn(f"[{_SOURCE}] active camera save failed: {exc!r}")

    def _restore_tour_camera(self) -> None:
        if not self._saved_tour_camera:
            return
        camera_path = self._saved_tour_camera
        self._saved_tour_camera = ""
        try:
            self.camera_switcher.set_active_camera(camera_path)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] active camera restore failed: {exc!r}")

    def _cancel_task(self, attr_name: str) -> None:
        task = getattr(self, attr_name)
        setattr(self, attr_name, None)
        if task is None:
            return
        try:
            current_task = asyncio.current_task()
        except RuntimeError:
            current_task = None
        if task is current_task:
            return
        cancel = getattr(task, "cancel", None)
        done = getattr(task, "done", None)
        try:
            if callable(done) and done():
                return
            if callable(cancel):
                cancel()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] task cancel failed: {exc!r}")

    def _schedule(self, coro):
        try:
            import omni.kit.async_engine  # noqa: WPS433

            return omni.kit.async_engine.run_coroutine(coro)
        except Exception:
            return asyncio.ensure_future(coro)

    @staticmethod
    def _make_overlay():
        from .button_overlay import ButtonModeOverlayManager

        return ButtonModeOverlayManager()

    @staticmethod
    def _make_camera_switcher():
        from .viewport_camera import ViewportCameraSwitcher

        return ViewportCameraSwitcher()

    def _current_overlay_size(self) -> tuple[int, int] | None:
        size_fn = getattr(self.overlay, "current_viewport_size", None)
        if not callable(size_fn):
            return None
        try:
            width, height = size_fn()
            width_i = int(round(float(width)))
            height_i = int(round(float(height)))
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{_SOURCE}] viewport size read failed: {exc!r}")
            return None
        if width_i <= 0 or height_i <= 0:
            return None
        return width_i, height_i


class _PreparedCameraResult:
    __slots__ = ("fallback", "valid_camera_path")

    def __init__(
        self,
        fallback: CaptureResult,
        valid_camera_path: str | None,
    ) -> None:
        self.fallback = fallback
        self.valid_camera_path = valid_camera_path


def _prepare_camera_results(
    key: str,
    camera_paths: list[str],
    width: int,
    height: int,
) -> list[_PreparedCameraResult]:
    camera_count = camera_set_size_for_key(key)
    raw_paths = list(camera_paths[:camera_count])
    while len(raw_paths) < camera_count:
        raw_paths.append("")

    prepared: list[_PreparedCameraResult] = []
    for raw_path in raw_paths:
        display_path = str(raw_path).strip() if raw_path is not None else ""
        normalized_path = _normalize_camera_path(display_path)
        if normalized_path is None:
            error = "camera path is empty" if not display_path else (
                f"camera path is invalid: {display_path}"
            )
            _log_warn(f"[{_SOURCE}] {error}")
            prepared.append(
                _PreparedCameraResult(
                    CaptureResult(display_path, "", width, height, error),
                    None,
                )
            )
            continue
        prepared.append(
            _PreparedCameraResult(
                CaptureResult(normalized_path, "", width, height),
                normalized_path,
            )
        )
    return prepared


def _merge_capture_results(
    prepared: list[_PreparedCameraResult],
    captured_results: list[CaptureResult],
) -> list[CaptureResult]:
    captured_iter = iter(captured_results)
    merged: list[CaptureResult] = []
    for item in prepared:
        if item.valid_camera_path is None:
            merged.append(item.fallback)
            continue
        try:
            merged.append(next(captured_iter))
        except StopIteration:
            merged.append(
                CaptureResult(
                    item.valid_camera_path,
                    "",
                    item.fallback.width,
                    item.fallback.height,
                    "capture did not return result",
                )
            )
    return merged


def _normalize_camera_path(camera_path: str) -> str | None:
    try:
        from .viewport_camera import normalize_camera_path

        return normalize_camera_path(camera_path)
    except Exception:
        cleaned = str(camera_path).strip() if camera_path is not None else ""
        if cleaned.startswith("/") and "[" not in cleaned and " " not in cleaned:
            return cleaned
        return None


def _set_prim_visibility(prim_path: str, *, visible: bool) -> None:
    try:
        import omni.usd as omni_usd  # type: ignore[import-not-found] # noqa: WPS433
        from pxr import UsdGeom  # noqa: WPS433

        stage = omni_usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(str(prim_path)) if stage is not None else None
        if prim is None or not prim.IsValid():
            _log_warn(f"[{_SOURCE}] visibility prim not found: {prim_path}")
            return
        imageable = UsdGeom.Imageable(prim)
        if visible:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()
    except Exception as exc:  # noqa: BLE001
        _log_warn(
            f"[{_SOURCE}] visibility set failed for {prim_path} "
            f"visible={visible}: {exc!r}"
        )


async def _wait_seconds(seconds: float) -> None:
    seconds = max(0.0, float(seconds))
    if seconds <= 0:
        await _next_update()
        return
    end_time = _monotonic() + seconds
    while _monotonic() < end_time:
        await _next_update()


async def _next_update() -> None:
    try:
        import omni.kit.app  # noqa: WPS433

        await omni.kit.app.get_app().next_update_async()
    except Exception:
        await asyncio.sleep(0)


def _monotonic() -> float:
    try:
        import time

        return time.monotonic()
    except Exception:
        return 0.0
