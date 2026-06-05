"""Viewport camera validation and switching helpers."""

from __future__ import annotations

import logging
from typing import Optional

from pxr import Sdf, Usd, UsdGeom

PERSPECTIVE_CAMERA_PATH = "/OmniverseKit_Persp"


def _log_warn(message: str) -> None:
    try:
        import carb  # noqa: WPS433

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning(message)


def normalize_camera_path(camera_path: str) -> str | None:
    """Return a clean absolute prim path, or ``None`` when invalid."""
    normalized = str(camera_path).strip() if camera_path is not None else ""
    if not normalized:
        return None

    try:
        valid_result = Sdf.Path.IsValidPathString(normalized)
    except Exception:  # noqa: BLE001
        return None

    is_valid = valid_result[0] if isinstance(valid_result, tuple) else bool(valid_result)
    if not is_valid:
        return None

    try:
        path = Sdf.Path(normalized)
    except Exception:  # noqa: BLE001
        return None

    if not path.IsAbsolutePath() or not path.IsPrimPath():
        return None
    return str(path)


def validate_camera_path(stage: Usd.Stage, camera_path: str) -> str | None:
    """Return an error string when ``camera_path`` is not a valid camera."""
    stripped_path = str(camera_path).strip() if camera_path is not None else ""
    normalized_path = normalize_camera_path(camera_path)
    if normalized_path is None:
        if not stripped_path:
            return "camera path is empty"
        return f"camera path is invalid: {stripped_path}"

    try:
        prim = stage.GetPrimAtPath(normalized_path) if stage is not None else None
    except Exception:  # noqa: BLE001
        prim = None

    if not prim or not prim.IsValid():
        return f"camera path is invalid: {normalized_path}"
    if not prim.IsA(UsdGeom.Camera):
        return f"path is not a camera: {normalized_path}"
    return None


class ViewportCameraSwitcher:
    """Small wrapper around the active Kit viewport camera selection."""

    def __init__(self) -> None:
        self._saved_camera_path: Optional[str] = None

    def get_active_camera(self) -> str:
        try:
            viewport = self._get_active_viewport()
            if viewport is None:
                _log_warn("usd_mouse_interact_demo: no active viewport")
                return ""
            camera_path = viewport.get_active_camera()
            return str(camera_path) if camera_path else ""
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"usd_mouse_interact_demo: get active camera failed: {exc}")
            return ""

    def set_active_camera(self, camera_path: str, stage: Usd.Stage | None = None) -> bool:
        normalized_path = normalize_camera_path(camera_path)
        if normalized_path is None:
            _log_warn(f"usd_mouse_interact_demo: invalid camera path: {camera_path}")
            return False
        if stage is not None:
            validation_error = validate_camera_path(stage, normalized_path)
            if validation_error is not None:
                _log_warn(f"usd_mouse_interact_demo: {validation_error}")
                return False

        try:
            viewport = self._get_active_viewport()
            if viewport is None:
                _log_warn("usd_mouse_interact_demo: no active viewport")
                return False

            try:
                viewport.camera_path = normalized_path
            except Exception as property_exc:  # noqa: BLE001
                set_active_camera = getattr(viewport, "set_active_camera", None)
                if set_active_camera is None:
                    _log_warn(
                        "usd_mouse_interact_demo: viewport camera_path assignment failed "
                        f"and no set_active_camera fallback exists: {property_exc}"
                    )
                    return False
                set_active_camera(normalized_path)

            get_active_camera = getattr(viewport, "get_active_camera", None)
            if callable(get_active_camera):
                active_camera = normalize_camera_path(get_active_camera())
                if active_camera != normalized_path:
                    _log_warn(
                        "usd_mouse_interact_demo: viewport rejected active camera "
                        f"{normalized_path}"
                    )
                    return False
            return True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"usd_mouse_interact_demo: set active camera failed: {exc}")
            return False

    def save_current(self) -> None:
        try:
            self._saved_camera_path = self.get_active_camera()
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"usd_mouse_interact_demo: save active camera failed: {exc}")

    def restore_saved(self) -> None:
        try:
            saved_camera_path = self._saved_camera_path
            self._saved_camera_path = None
            if saved_camera_path:
                self.set_active_camera(saved_camera_path)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"usd_mouse_interact_demo: restore active camera failed: {exc}")

    def set_perspective_camera(self) -> bool:
        """Switch the active viewport back to Kit's default Perspective camera."""
        try:
            viewport = self._get_active_viewport()
            if viewport is None:
                _log_warn("usd_mouse_interact_demo: no active viewport")
                return False
            try:
                viewport.camera_path = PERSPECTIVE_CAMERA_PATH
            except Exception as property_exc:  # noqa: BLE001
                set_active_camera = getattr(viewport, "set_active_camera", None)
                if not callable(set_active_camera):
                    _log_warn(
                        "usd_mouse_interact_demo: perspective camera assignment failed "
                        f"and no set_active_camera fallback exists: {property_exc}"
                    )
                    return False
                set_active_camera(PERSPECTIVE_CAMERA_PATH)
            return True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"usd_mouse_interact_demo: set perspective camera failed: {exc}")
            return False

    def _get_active_viewport(self):
        import omni.kit.viewport.utility as viewport_utility  # noqa: WPS433

        return viewport_utility.get_active_viewport()
