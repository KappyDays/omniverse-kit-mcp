"""StageScanner — collects prim positions for the compass HUD.

Walks the active USD stage once per cache miss, computes a 2-D floor-plane
position per prim, and stamps a stable color per type. Heavy work is
amortized: stage-event subscriptions (open / layer reload) flag the cache
dirty and the next ``get_markers()`` rebuilds it. Camera position is read
fresh each frame elsewhere — only world prim layout is cached here.
"""
from __future__ import annotations

import dataclasses
from typing import Iterable

import carb


# Prim types we deliberately ignore — they have no spatial footprint or are
# noise on the radar (Materials/Shaders are referenced, not located; Scopes
# are organizational; Sequencer/Audio prims aren't visual).
SKIP_TYPES = frozenset({
    "",
    "Material",
    "Shader",
    "NodeGraph",
    "Scope",
    "Audio",
    "AudioSource",
    "AudioListener",
    "Skeleton",
    "SkelAnimation",
    "BlendShape",
    "Variant",
    "Collection",
    "GeomSubset",
    "PhysicsScene",
    "PhysicsMaterial",
    "PhysicsCollisionGroup",
    "RenderProduct",
    "RenderVar",
    "Backdrop",
    "TerminalsGraph",
})

# AARRGGBB color per prim type. Geometry = green family, lights = warm
# yellow, cameras = blue, characters = pink, articulation/robots = orange.
_TYPE_COLORS: dict[str, int] = {
    "Mesh":          0xFF60D080,
    "Cube":          0xFF60D080,
    "Sphere":        0xFF60D080,
    "Cylinder":      0xFF60D080,
    "Cone":          0xFF60D080,
    "Capsule":       0xFF60D080,
    "Plane":         0xFF40A060,
    "PointInstancer":0xFF40C0A0,
    "BasisCurves":   0xFF80E0C0,
    "Points":        0xFF80E0C0,
    "Camera":        0xFF60A8FF,
    "DistantLight":  0xFFFFD060,
    "DomeLight":     0xFFFFE0A0,
    "RectLight":     0xFFFFD060,
    "SphereLight":   0xFFFFD060,
    "DiskLight":     0xFFFFD060,
    "CylinderLight": 0xFFFFD060,
    "GeometryLight": 0xFFFFD060,
    "PortalLight":   0xFFFFD060,
    "Xform":         0xFFA0A0A0,
    "SkelRoot":      0xFFFF80C0,
    "NavMeshVolume": 0xFF80B0FF,
    "PhysicsJoint":  0xFFB060B0,
    "PhysxArticulationLink": 0xFFFFA040,
}
_DEFAULT_COLOR = 0xFFB0B0B0


@dataclasses.dataclass(slots=True, frozen=True)
class PrimMarker:
    """Single radar dot.

    ``floor_a`` / ``floor_b`` are the projected horizontal coordinates on
    the stage's floor plane; for a Y-up stage that's (X, Z), for Z-up
    that's (X, Y). ``height`` is the up-axis component, useful for layered
    rendering or label placement. ``size_px`` lets the HUD vary marker
    radius (e.g., camera/light gets a slightly bigger dot than mesh).
    """
    prim_path: str
    type_name: str
    floor_a: float
    floor_b: float
    height: float
    color_argb: int
    size_px: int = 4


@dataclasses.dataclass(slots=True, frozen=True)
class CameraPose:
    floor_a: float
    floor_b: float
    height: float
    heading_rad: float
    fov_deg: float = 60.0


def color_for_type(type_name: str) -> int:
    """Public lookup so the settings panel can show legend swatches."""
    return _TYPE_COLORS.get(type_name, _DEFAULT_COLOR)


def floor_axes(up_axis: str) -> tuple[int, int, int]:
    """Return (a_idx, b_idx, h_idx) into a Vec3 given a USD up-axis label.

    Y-up stages put the floor in the X/Z plane and elevation in Y. Z-up
    stages put the floor in X/Y. Returning indices keeps callers free of
    repeated conditional logic.
    """
    if up_axis == "Z":
        return 0, 1, 2
    return 0, 2, 1  # default Y-up


class StageScanner:
    """Caches a snapshot of the stage's prims for the radar to render.

    Cache is invalidated by ``mark_dirty()``; the extension wires this to
    USD stage events (open, asset reload). Lazily refreshes on next read.
    """

    MAX_PRIMS_PER_SCAN = 4000  # cap so a giant stage doesn't stall the UI

    def __init__(self) -> None:
        self._cache: list[PrimMarker] = []
        self._dirty: bool = True
        self._last_up_axis: str = "Y"
        self._last_world_extents: tuple[float, float, float, float] = (
            -10.0, -10.0, 10.0, 10.0,
        )
        self._allowed_types: frozenset[str] | None = None

    def mark_dirty(self) -> None:
        """Force a fresh traversal on the next ``get_markers`` call."""
        self._dirty = True

    def set_type_filter(self, types: Iterable[str] | None) -> None:
        """Restrict the next scan to a subset of prim types. None = all."""
        self._allowed_types = frozenset(types) if types is not None else None
        self._dirty = True

    @property
    def up_axis(self) -> str:
        return self._last_up_axis

    @property
    def world_extents(self) -> tuple[float, float, float, float]:
        """(min_a, min_b, max_a, max_b) of the floor-plane axis-aligned hull
        across all kept markers. Used by the panel "Frame All" button to
        pick a sensible radar zoom level.
        """
        return self._last_world_extents

    def get_markers(self, force_refresh: bool = False) -> list[PrimMarker]:
        if force_refresh or self._dirty:
            try:
                self._scan()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_compass] scan failed: {exc}")
                self._cache = []
            self._dirty = False
        return self._cache

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _scan(self) -> None:
        import omni.usd
        from pxr import UsdGeom, Usd, Gf

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._cache = []
            return

        try:
            up_axis = UsdGeom.GetStageUpAxis(stage)
        except Exception:
            up_axis = "Y"
        self._last_up_axis = up_axis
        a_idx, b_idx, h_idx = floor_axes(up_axis)

        bbox_cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(),
            includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.proxy],
            useExtentsHint=True,
        )
        markers: list[PrimMarker] = []
        scanned = 0
        min_a = min_b = float("inf")
        max_a = max_b = float("-inf")

        allow = self._allowed_types
        for prim in stage.Traverse():
            scanned += 1
            if scanned > self.MAX_PRIMS_PER_SCAN:
                carb.log_warn(
                    f"[stage_compass] scan capped at {self.MAX_PRIMS_PER_SCAN} prims"
                )
                break
            type_name = prim.GetTypeName()
            if type_name in SKIP_TYPES:
                continue
            if allow is not None and type_name not in allow:
                continue

            pos: Gf.Vec3d | None = None
            try:
                imageable = UsdGeom.Imageable(prim)
                if imageable:
                    bb = bbox_cache.ComputeWorldBound(prim)
                    if not bb.GetRange().IsEmpty():
                        pos = bb.ComputeAlignedBox().GetMidpoint()
            except Exception:
                pos = None
            if pos is None:
                # Fallback: read xformOp:translate directly (handles Lights,
                # Cameras, NavMeshVolumes that may report empty bbox).
                t_attr = prim.GetAttribute("xformOp:translate")
                if t_attr and t_attr.IsValid():
                    val = t_attr.Get()
                    if val is not None:
                        pos = Gf.Vec3d(float(val[0]), float(val[1]), float(val[2]))
            if pos is None:
                continue

            wa = float(pos[a_idx])
            wb = float(pos[b_idx])
            wh = float(pos[h_idx])
            color = color_for_type(type_name)
            size_px = 6 if type_name in ("Camera", "DistantLight", "DomeLight",
                                          "SphereLight", "RectLight",
                                          "DiskLight") else 4
            markers.append(PrimMarker(
                prim_path=prim.GetPath().pathString,
                type_name=type_name,
                floor_a=wa, floor_b=wb, height=wh,
                color_argb=color, size_px=size_px,
            ))
            if wa < min_a: min_a = wa
            if wa > max_a: max_a = wa
            if wb < min_b: min_b = wb
            if wb > max_b: max_b = wb

        self._cache = markers
        if markers:
            self._last_world_extents = (min_a, min_b, max_a, max_b)
        else:
            self._last_world_extents = (-10.0, -10.0, 10.0, 10.0)
