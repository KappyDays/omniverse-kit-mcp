"""Viewport render service — RTX mode / quality / overlay / fov (Phase F).

Extends ``ViewportService`` with settings-driven controls:
- render mode: ``/rtx/rendermode`` ∈ {RaytracedLighting, PathTracing}
- quality: ``/rtx/pathtracing/spp`` + ``/rtx/post/aa/op``
- overlays: ``/persistent/app/viewport/*`` toggles
- fov: camera ``focalLength`` derived from desired horizontal FOV
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


_RENDER_MODE_MAP = {
    "RealTime": "RaytracedLighting",
    "PathTracing": "PathTracing",
}

_DENOISER_OP_MAP = {"auto": 3, "DLSS": 4, "NRD": 5, "off": 0}

# Overlay → carb.settings key. ``axis`` intentionally avoids
# ``/persistent/app/viewport/displayOptions`` — Kit 5.1 ``legacy.py:226``
# reads that parent key as an integer bitmask; writing a child boolean
# turns the parent into a dict and triggers
# ``TypeError: unsupported operand type(s) for &: 'dict' and 'int'``
# on every subsequent Kit startup (baked into user.config.json until
# manually removed). We therefore target the per-viewport guide path
# Kit actually uses to track axis-gizmo visibility.
_OVERLAY_KEY_GRIDLINES = "/persistent/app/viewport/grid/enabled"
_OVERLAY_KEY_STATS = "/rtx/stats/enable"


def _axis_key_for_viewport(viewport_name: str) -> str:
    """Axis gizmo visibility is stored per-viewport under ``guide/axis/visible``."""
    safe = viewport_name or "Viewport"
    return f"/persistent/app/viewport/{safe}/Viewport0/guide/axis/visible"


class ViewportRenderService:
    """Settings-driven render pipeline controls layered on the main viewport."""

    async def set_render_mode(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings

        viewport_name = request.get("viewport_name", "Viewport")
        mode = request["mode"]
        if mode not in _RENDER_MODE_MAP:
            raise ValueError("mode must be RealTime | PathTracing")
        carb.settings.get_settings().set("/rtx/rendermode", _RENDER_MODE_MAP[mode])
        return {
            "ok": True,
            "viewport_name": viewport_name,
            "mode": mode,
            "setting_value": _RENDER_MODE_MAP[mode],
        }

    async def set_render_quality(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings

        samples = int(request.get("samples", 1))
        denoiser = request.get("denoiser", "auto")
        if denoiser not in _DENOISER_OP_MAP:
            raise ValueError("denoiser must be auto | DLSS | NRD | off")
        settings = carb.settings.get_settings()
        settings.set("/rtx/pathtracing/spp", samples)
        aa_op = _DENOISER_OP_MAP[denoiser]
        settings.set("/rtx/post/aa/op", aa_op)
        return {
            "ok": True,
            "samples": samples,
            "denoiser": denoiser,
            "aa_op": aa_op,
        }

    async def toggle_overlay(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings

        viewport_name = request.get("viewport_name", "Viewport")
        overlay = request["overlay"]
        visible = bool(request.get("visible", True))
        if overlay == "gridlines":
            key = _OVERLAY_KEY_GRIDLINES
        elif overlay == "stats":
            key = _OVERLAY_KEY_STATS
        elif overlay == "axis":
            key = _axis_key_for_viewport(viewport_name)
        else:
            raise ValueError("overlay must be gridlines | axis | stats")
        carb.settings.get_settings().set(key, visible)
        return {
            "ok": True,
            "viewport_name": viewport_name,
            "overlay": overlay,
            "visible": visible,
            "setting_path": key,
        }

    async def set_fov(self, request: dict[str, Any]) -> dict[str, Any]:
        """Convert a desired horizontal FOV (degrees) to focalLength on the camera.

        Walks a short candidate list (viewport-reported camera → default
        Perspective → first Camera prim on stage) so the call succeeds
        against freshly-opened stages where `/OmniverseKit_Persp` may live
        in the session layer and not yet be resolvable by GetPrimAtPath.
        """
        import omni.usd

        viewport_name = request.get("viewport_name", "Viewport")
        fov_deg = float(request["fov_deg"])
        if fov_deg <= 0 or fov_deg >= 180:
            raise ValueError("fov_deg must be in (0, 180)")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        candidates = _candidate_camera_paths(viewport_name, stage)
        camera_prim = None
        camera_path: str | None = None
        for candidate in candidates:
            prim = stage.GetPrimAtPath(candidate)
            if prim.IsValid():
                camera_prim = prim
                camera_path = candidate
                break
        if camera_prim is None:
            raise ValueError(
                f"No camera prim found (tried {candidates}). Create a camera or "
                f"open a stage with the default perspective camera first."
            )

        horiz_aperture_attr = camera_prim.GetAttribute("horizontalAperture")
        horiz_aperture = (
            float(horiz_aperture_attr.Get()) if horiz_aperture_attr.IsValid() else 20.955
        )
        focal_length = (horiz_aperture / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
        focal_attr = camera_prim.GetAttribute("focalLength")
        if focal_attr.IsValid():
            focal_attr.Set(focal_length)
        return {
            "ok": True,
            "viewport_name": viewport_name,
            "camera_path": camera_path,
            "fov_deg": fov_deg,
            "focal_length": focal_length,
            "horizontal_aperture": horiz_aperture,
        }

    async def set_camera_lookat(self, request: dict[str, Any]) -> dict[str, Any]:
        """Author a camera's world transform from eye/target/up (deadlock-safe).

        Runs on the REST handler path and writes only ``xformOp:transform`` —
        same proven-safe class as ``set_fov``'s focalLength write. NOT the
        ``kit_python_run`` main-thread path that deadlocked in the office session.
        Default target is the viewport's active camera (Perspective included);
        pass ``camera_path`` to author a specific (e.g. authored) camera.
        """
        import omni.kit.app
        import omni.usd
        from pxr import Gf, UsdGeom

        viewport_name = request.get("viewport_name", "Viewport")
        eye = [float(v) for v in request["eye"]]
        target = [float(v) for v in request["target"]]
        up = [float(v) for v in request.get("up", [0.0, 0.0, 1.0])]
        explicit = request.get("camera_path")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        candidates = [explicit] if explicit else _candidate_camera_paths(viewport_name, stage)
        camera_prim = None
        camera_path: str | None = None
        for candidate in candidates:
            if not candidate:
                continue
            prim = stage.GetPrimAtPath(candidate)
            if prim.IsValid():
                camera_prim = prim
                camera_path = candidate
                break
        if camera_prim is None:
            raise ValueError(f"No camera prim found (tried {candidates}).")

        # view = world->camera; camera local-to-world = its inverse.
        view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(*up))
        cam_to_world = view.GetInverse()

        xform = UsdGeom.Xformable(camera_prim)
        xform.ClearXformOpOrder()  # reset to a single transform op (op-order safe)
        xform.AddTransformOp().Set(cam_to_world)

        # Let the viewport pick up the new transform for a subsequent capture.
        app = omni.kit.app.get_app()
        for _ in range(2):
            await app.next_update_async()

        return {
            "ok": True,
            "viewport_name": viewport_name,
            "camera_path": camera_path,
            "eye": eye,
            "target": target,
            "up": up,
        }


def _resolve_camera_path(viewport_name: str) -> str:
    """Look up the active camera for *viewport_name* with a safe fallback."""
    try:
        from omni.kit.viewport.utility import get_viewport_from_window_name

        viewport = get_viewport_from_window_name(viewport_name)
        if viewport is not None and getattr(viewport, "camera_path", None):
            return str(viewport.camera_path)
    except Exception:  # noqa: BLE001
        logger.debug("get_viewport_from_window_name failed", exc_info=True)
    return "/OmniverseKit_Persp"


def _candidate_camera_paths(viewport_name: str, stage: Any) -> list[str]:
    """Return an ordered list of candidate camera paths to probe."""
    from pxr import UsdGeom

    candidates: list[str] = []
    # 1. The viewport's active camera, if discoverable.
    try:
        from omni.kit.viewport.utility import get_viewport_from_window_name

        viewport = get_viewport_from_window_name(viewport_name)
        if viewport is not None and getattr(viewport, "camera_path", None):
            candidates.append(str(viewport.camera_path))
    except Exception:  # noqa: BLE001
        logger.debug("get_viewport_from_window_name failed", exc_info=True)

    # 2. Kit's built-in cameras.
    for default in (
        "/OmniverseKit_Persp",
        "/OmniverseKit_Top",
        "/OmniverseKit_Front",
        "/OmniverseKit_Right",
    ):
        if default not in candidates:
            candidates.append(default)

    # 3. First Camera prim on the stage (authored content).
    try:
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Camera):
                candidates.append(str(prim.GetPath()))
                break
    except Exception:  # noqa: BLE001
        logger.debug("stage traverse for camera failed", exc_info=True)
    return candidates
