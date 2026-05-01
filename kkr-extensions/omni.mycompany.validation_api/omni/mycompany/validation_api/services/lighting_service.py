"""Lighting service — UsdLux Dome/Distant/Disk/Rect/Sphere + exposure (Phase F).

Each ``create_*`` path defines a UsdLux prim (creating the parent scope if
needed), writes core attributes via the `inputs:*` prefix (USD 2023+ schema),
and returns a normalised response consumed by ``LightingModule``.
``set_exposure`` toggles ``carb.settings`` ``/rtx/post/tonemap/exposure``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

EXPOSURE_SETTING = "/rtx/post/tonemap/exposure"


class LightingService:
    """Create UsdLux lights + control RTX tonemap exposure."""

    # ------------------------------------------------------------------
    # Creators
    # ------------------------------------------------------------------

    async def create_dome(self, request: dict[str, Any]) -> dict[str, Any]:
        prim_path = request["prim_path"]
        intensity = float(request.get("intensity", 1000.0))
        texture = request.get("texture")
        prim = _define_light(prim_path, "DomeLight")
        _set_input_float(prim, "intensity", intensity)
        if texture is not None:
            _set_input_asset(prim, "texture:file", texture)
        return {
            "ok": True,
            "prim_path": prim_path,
            "light_type": "DomeLight",
            "intensity": intensity,
            "extra": {"texture": texture},
        }

    async def create_distant(self, request: dict[str, Any]) -> dict[str, Any]:
        prim_path = request["prim_path"]
        intensity = float(request.get("intensity", 1000.0))
        angle_deg = float(request.get("angle_deg", 0.53))
        prim = _define_light(prim_path, "DistantLight")
        _set_input_float(prim, "intensity", intensity)
        _set_input_float(prim, "angle", angle_deg)
        return {
            "ok": True,
            "prim_path": prim_path,
            "light_type": "DistantLight",
            "intensity": intensity,
            "extra": {"angle_deg": angle_deg},
        }

    async def create_disk(self, request: dict[str, Any]) -> dict[str, Any]:
        prim_path = request["prim_path"]
        intensity = float(request.get("intensity", 1000.0))
        radius = float(request.get("radius", 1.0))
        prim = _define_light(prim_path, "DiskLight")
        _set_input_float(prim, "intensity", intensity)
        _set_input_float(prim, "radius", radius)
        return {
            "ok": True,
            "prim_path": prim_path,
            "light_type": "DiskLight",
            "intensity": intensity,
            "extra": {"radius": radius},
        }

    async def create_rect(self, request: dict[str, Any]) -> dict[str, Any]:
        prim_path = request["prim_path"]
        intensity = float(request.get("intensity", 1000.0))
        width = float(request.get("width", 1.0))
        height = float(request.get("height", 1.0))
        prim = _define_light(prim_path, "RectLight")
        _set_input_float(prim, "intensity", intensity)
        _set_input_float(prim, "width", width)
        _set_input_float(prim, "height", height)
        return {
            "ok": True,
            "prim_path": prim_path,
            "light_type": "RectLight",
            "intensity": intensity,
            "extra": {"width": width, "height": height},
        }

    async def create_sphere(self, request: dict[str, Any]) -> dict[str, Any]:
        prim_path = request["prim_path"]
        intensity = float(request.get("intensity", 1000.0))
        radius = float(request.get("radius", 1.0))
        prim = _define_light(prim_path, "SphereLight")
        _set_input_float(prim, "intensity", intensity)
        _set_input_float(prim, "radius", radius)
        return {
            "ok": True,
            "prim_path": prim_path,
            "light_type": "SphereLight",
            "intensity": intensity,
            "extra": {"radius": radius},
        }

    # ------------------------------------------------------------------
    # Exposure
    # ------------------------------------------------------------------

    async def set_exposure(self, request: dict[str, Any]) -> dict[str, Any]:
        import carb.settings

        exposure = float(request["exposure"])
        carb.settings.get_settings().set(EXPOSURE_SETTING, exposure)
        return {
            "ok": True,
            "exposure": exposure,
            "setting_path": EXPOSURE_SETTING,
        }


# ---------------------------------------------------------------------------
# Helpers — lazy imports keep module import safe when Kit is not loaded (tests).
# ---------------------------------------------------------------------------


def _define_light(prim_path: str, light_type: str) -> Any:
    import omni.usd
    from pxr import Sdf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    _ensure_parent_scope(stage, prim_path)
    prim = stage.DefinePrim(Sdf.Path(prim_path), light_type)
    if not prim.IsValid():
        raise RuntimeError(f"Failed to create {light_type} at {prim_path}")
    return prim


def _ensure_parent_scope(stage: Any, prim_path: str) -> None:
    from pxr import Sdf

    parts = prim_path.strip("/").split("/")
    if len(parts) <= 1:
        return
    parent = "/" + "/".join(parts[:-1])
    existing = stage.GetPrimAtPath(Sdf.Path(parent))
    if not existing.IsValid():
        stage.DefinePrim(Sdf.Path(parent), "Xform")


def _set_input_float(prim: Any, name: str, value: float) -> None:
    from pxr import Sdf

    attr_name = f"inputs:{name}"
    attr = prim.GetAttribute(attr_name)
    if not attr.IsValid():
        attr = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float)
    attr.Set(float(value))


def _set_input_asset(prim: Any, name: str, value: str) -> None:
    from pxr import Sdf

    attr_name = f"inputs:{name}"
    attr = prim.GetAttribute(attr_name)
    if not attr.IsValid():
        attr = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Asset)
    attr.Set(Sdf.AssetPath(value))
