"""Navigation service — NavMesh bake + shortest-path query.

Wraps ``omni.anim.navigation.core.acquire_interface()`` so callers can
programmatically bake the NavMesh for the current Stage and query
obstacle-aware paths. Used by :func:`robot_service.navigate_path` to drive
robots over NavMesh waypoints (Character nav already uses NavMesh internally
via AnimationGraph).

**Non-blocking bake**: we call the async ``start_navmesh_baking()`` and
poll ``is_navmesh_baking()`` with ``app.next_update_async()`` yields.
The blocking variant ``start_navmesh_baking_and_wait()`` holds Kit's
single-thread Python event loop, which starves the HTTP router for every
subsequent call in the same session and makes validation scripts hang.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NavigationService:
    """Bake NavMesh + query shortest path (world-space waypoints)."""

    def _nav(self):
        import omni.anim.navigation.core as nav  # lazy
        return nav.acquire_interface()

    async def add_exclude_volume(self, request: dict[str, Any]) -> dict[str, Any]:
        """Add a NavMeshVolume(type=Exclude) covering a given prim's bbox so
        NavMesh bake treats that region as non-walkable (prevents step-up onto
        chairs, tables, etc.). Caller should rebake after adding volumes.

        If `prim_path` is given, computes world bbox for sizing. Otherwise
        `center` + `size` must be provided explicitly.
        """
        import omni.kit.commands
        import omni.usd
        from pxr import Gf

        center = request.get("center")
        size = request.get("size")
        prim_path = request.get("prim_path")
        padding = float(request.get("padding", 0.1))

        if prim_path and (center is None or size is None):
            # Compute bbox via stage service logic inline (avoid tight coupling)
            from .stage_service import StageService
            bb = await StageService().compute_world_bbox(prim_path)
            center = bb["center"]; size = bb["size"]

        if center is None or size is None:
            raise ValueError("Provide either prim_path OR (center + size)")

        omni.kit.commands.execute("CreateNavMeshVolumeCommand", volume_type=1)  # 1 = Exclude

        stage = omni.usd.get_context().get_stage()
        created_path: str | None = None
        for prim in stage.Traverse():
            if prim.GetTypeName() != "NavMeshVolume":
                continue
            # look for a newly created Exclude (has translate at 0)
            t = prim.GetAttribute("xformOp:translate")
            if t.IsValid() and tuple(t.Get() or (0, 0, 0)) == (0, 0, 0):
                # Need to also verify volumeType == Exclude
                vt = prim.GetAttribute("nav:volumeType") or prim.GetAttribute("navVolumeType")
                if vt is None or vt.Get() == "Exclude":
                    created_path = prim.GetPath().pathString
                    break
        if created_path is None:
            # fallback: pick most recent NavMeshVolume
            for prim in stage.Traverse():
                if prim.GetTypeName() == "NavMeshVolume":
                    created_path = prim.GetPath().pathString
        if created_path is None:
            raise RuntimeError("Exclude NavMeshVolume creation failed")

        # Position + scale
        pad_x, pad_y, pad_z = padding, padding, padding
        scale = [size[0] + 2 * pad_x, size[1] + 2 * pad_y, size[2] + 2 * pad_z]
        vprim = stage.GetPrimAtPath(created_path)
        tattr = vprim.GetAttribute("xformOp:translate")
        if tattr.IsValid():
            tattr.Set(Gf.Vec3d(*center))
        sattr = vprim.GetAttribute("xformOp:scale")
        if sattr.IsValid():
            sattr.Set(Gf.Vec3d(*scale))
        return {
            "ok": True,
            "volume_path": created_path,
            "type": "Exclude",
            "center": list(center),
            "scale": scale,
            "padding": padding,
        }

    def _ensure_navmesh_volume(self, scale: float = 40.0) -> str:
        """Ensure at least one NavMeshVolume (Include) prim exists in the stage.

        NavMesh bake requires at least one Include volume; without it the bake
        no-ops and ``get_navmesh()`` returns None. Creates a default volume
        centered at origin with the given world-space scale (covers typical
        Simple_Warehouse / Office environments at default 40 m box)."""
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Sdf, UsdGeom

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        # Check existing NavMeshVolume prims
        existing: list[str] = []
        for prim in stage.Traverse():
            if prim.GetTypeName() == "NavMeshVolume":
                existing.append(prim.GetPath().pathString)
        if existing:
            return existing[0]

        # Create default volume — the registered command name is
        # "CreateNavMeshVolumeCommand" (omni.anim.navigation.core.scripts.command).
        omni.kit.commands.execute("CreateNavMeshVolumeCommand",
                                    volume_type=0)  # 0 = Include

        # Command assigns a name like /NavMeshVolume; find it
        created: str | None = None
        for prim in stage.Traverse():
            if prim.GetTypeName() == "NavMeshVolume":
                created = prim.GetPath().pathString
                break
        if created is None:
            raise RuntimeError("NavMeshVolume creation failed")

        # Rescale to cover target environment (default command scale=10m is
        # often too small for warehouses)
        prim = stage.GetPrimAtPath(created)
        scale_attr = prim.GetAttribute("xformOp:scale")
        if scale_attr.IsValid():
            from pxr import Gf
            scale_attr.Set(Gf.Vec3d(scale, scale, scale))
        return created

    async def bake(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        """Bake the NavMesh for the current stage, cooperatively.

        Kicks the async `start_navmesh_baking()` then yields via
        `app.next_update_async()` until `is_navmesh_baking()` returns False
        (or `timeout_s` elapses). **Never** calls
        `start_navmesh_baking_and_wait()` — that helper blocks Kit's Python
        thread and poisons the whole HTTP router for the duration.

        Auto-creates a NavMeshVolume(Include, 40 m scale) if the stage has none.
        Returns metadata about the baked mesh so the caller can confirm
        area_count / agent_max_radius etc. are non-trivial.
        """
        import omni.kit.app  # lazy

        request = request or {}
        volume_scale = float(request.get("volume_scale", 40.0))
        timeout_s = float(request.get("timeout_s", 300.0))
        volume_path = self._ensure_navmesh_volume(scale=volume_scale)

        # Let USD settle after volume creation — without this, the navigation
        # interface occasionally sees the stage mid-mutation and the bake
        # returns a stale/empty navmesh.
        app = omni.kit.app.get_app()
        for _ in range(10):
            await app.next_update_async()

        iface = self._nav()
        kicked = bool(iface.start_navmesh_baking())
        if not kicked:
            return {
                "ok": False, "baked": False,
                "reason": "start_navmesh_baking returned False "
                          "(no volume / navmesh cache locked / disabled in settings)",
                "volume_path": volume_path,
            }

        deadline = time.monotonic() + max(1.0, timeout_s)
        elapsed_ticks = 0
        while True:
            try:
                in_progress = bool(iface.is_navmesh_baking())
            except Exception:  # noqa: BLE001 — defensive; API surfaces changed across Kit versions
                in_progress = False
            if not in_progress:
                break
            if time.monotonic() >= deadline:
                return {
                    "ok": False, "baked": False,
                    "reason": f"bake still in progress after {timeout_s:.0f}s timeout",
                    "volume_path": volume_path,
                    "elapsed_ticks": elapsed_ticks,
                }
            await app.next_update_async()
            elapsed_ticks += 1

        # Ref exposure after baking finishes — mesh object may need a few ticks
        mesh = None
        for _ in range(30):
            mesh = iface.get_navmesh()
            if mesh is not None:
                break
            await app.next_update_async()
        if mesh is None:
            return {
                "ok": False, "baked": True,
                "reason": "bake finished but get_navmesh() stayed None",
                "volume_path": volume_path,
            }
        return {
            "ok": True,
            "baked": True,
            "volume_path": volume_path,
            "elapsed_ticks": elapsed_ticks,
            "agent_max_radius": float(mesh.get_agent_max_radius()),
            "agent_min_radius": float(mesh.get_agent_min_radius()),
            "agent_min_height": float(mesh.get_agent_min_height()),
            "agent_max_slope": float(mesh.get_agent_max_slope()),
            "agent_max_step_height": float(mesh.get_agent_max_step_height()),
            "area_count": int(mesh.get_area_count()),
            "mesh_signature": int(mesh.get_mesh_signature()),
        }

    async def _bake_if_needed(self) -> None:
        """Cooperative auto-bake used by query_path when the mesh is missing.

        Mirrors `bake()` but without the volume-creation path decision — caller
        has already verified the stage is in a usable state.
        """
        import omni.kit.app  # lazy

        iface = self._nav()
        iface.start_navmesh_baking()
        app = omni.kit.app.get_app()
        # Reasonable polling cap — query_path callers don't want to wait forever
        for _ in range(4000):
            try:
                in_progress = bool(iface.is_navmesh_baking())
            except Exception:  # noqa: BLE001
                in_progress = False
            if not in_progress:
                break
            await app.next_update_async()

    async def set_visualization(self, request: dict[str, Any]) -> dict[str, Any]:
        """Toggle NavMesh walkable-area overlay in the viewport (Phase E).

        Backends attempted in order (first success wins, reported in
        ``response.backend``):

        1. ``carb.settings`` ``/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh``
           — Isaac Sim 5.x supports this top-level toggle (True shows walkable).
        2. ``prim_visibility`` — fall back to flipping every ``NavMeshVolume``
           prim's visibility token. Coarser (doesn't distinguish walkable
           vs obstacles) but always available.
        """
        import carb.settings

        mode = request.get("mode")
        if mode not in ("walkable", "obstacles", "off"):
            raise ValueError("mode must be 'walkable' | 'obstacles' | 'off'")

        settings = carb.settings.get_settings()
        setting_path = "/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh"
        obstacles_setting = "/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMeshObstacles"

        applied_setting: str | None = None
        try:
            # Walkable overlay
            settings.set(setting_path, mode == "walkable")
            applied_setting = setting_path
            # Obstacles overlay — only toggled if the key exists on this Kit build
            try:
                settings.set(obstacles_setting, mode == "obstacles")
            except Exception:  # noqa: BLE001 — harmless if the key is missing
                pass
            backend = "carb_settings"
        except Exception as exc:  # noqa: BLE001 — fall back to prim visibility
            logger.warning(
                "carb.settings toggle failed (%s); falling back to prim visibility", exc,
            )
            backend = "prim_visibility"
            applied_setting = None
            await self._fallback_set_volume_visibility(visible=(mode != "off"))
        else:
            # Also toggle volume visibility so the change is obvious when the
            # backend setting is honored but the viewport draws nothing (DomeLight
            # baseline). Idempotent.
            try:
                await self._fallback_set_volume_visibility(visible=(mode != "off"))
            except Exception:
                pass

        return {
            "ok": True,
            "mode": mode,
            "backend": backend,
            "setting_path": applied_setting,
        }

    async def _fallback_set_volume_visibility(self, *, visible: bool) -> None:
        """Toggle NavMeshVolume prim visibility as a coarse viz fallback."""
        import omni.usd

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        token = "inherited" if visible else "invisible"
        for prim in stage.Traverse():
            if prim.GetTypeName() != "NavMeshVolume":
                continue
            vis = prim.GetAttribute("visibility")
            if vis.IsValid():
                vis.Set(token)

    async def sample_walkable_points(self, request: dict[str, Any]) -> dict[str, Any]:
        """Sample N random walkable points on the baked NavMesh.

        Spec §8.1 algorithm: area-weighted triangle selection +
        barycentric interior sample. Falls back to bbox-rejection
        (random point in NavMeshVolume bbox, accepted if reachable
        from a baked seed via ``query_shortest_path``) when this Kit
        build does not expose the public triangle iteration API.

        Returns ``method`` field: ``"area_weighted"`` (preferred) or
        ``"bbox_reachability"`` (fallback).
        """
        import math
        import random
        from bisect import bisect_left
        from itertools import accumulate

        import carb  # lazy
        import omni.kit.app
        import omni.usd
        from pxr import Gf

        request = request or {}
        count = int(request["count"])
        if not (1 <= count <= 1000):
            raise ValueError(f"count out of range [1, 1000]: {count}")
        bounds_min = request.get("bounds_min")
        bounds_max = request.get("bounds_max")
        if (bounds_min is None) != (bounds_max is None):
            raise ValueError("bounds_min and bounds_max must both be set or both None")
        seed = request.get("seed")

        iface = self._nav()
        mesh = iface.get_navmesh()
        if mesh is None:
            raise RuntimeError(
                "NavMesh not baked. Call /navigation/bake first (timeline must be stopped)."
            )

        rng = random.Random(seed)

        # ---- Path A: area-weighted triangle iteration (spec §8.1) ----
        try:
            tri_count_fn = getattr(mesh, "get_triangle_count", None)
            tri_get_fn = getattr(mesh, "get_triangle", None)
            if tri_count_fn is None or tri_get_fn is None:
                raise AttributeError("triangle iteration API not exposed")
            n = int(tri_count_fn())
            if n <= 0:
                raise RuntimeError("get_triangle_count() returned 0")

            tris: list[tuple[Gf.Vec3d, Gf.Vec3d, Gf.Vec3d]] = []
            areas: list[float] = []
            for i in range(n):
                tri = tri_get_fn(i)
                # Tri shape varies — try (Vec3, Vec3, Vec3) | flat 9-tuple | list
                v0, v1, v2 = _normalize_triangle(tri)
                if bounds_min is not None and bounds_max is not None:
                    c = (v0 + v1 + v2) / 3.0
                    if not (
                        bounds_min[0] <= c[0] <= bounds_max[0]
                        and bounds_min[1] <= c[1] <= bounds_max[1]
                        and bounds_min[2] <= c[2] <= bounds_max[2]
                    ):
                        continue
                e1 = v1 - v0
                e2 = v2 - v0
                area = 0.5 * _cross_mag(e1, e2)
                if area <= 0.0:
                    continue
                tris.append((v0, v1, v2))
                areas.append(area)

            if not tris:
                raise RuntimeError("No walkable triangles within bounds.")

            cum = list(accumulate(areas))
            total = cum[-1]
            points: list[list[float]] = []
            for _ in range(count):
                idx = bisect_left(cum, rng.random() * total)
                v0, v1, v2 = tris[idx]
                r1, r2 = rng.random(), rng.random()
                if r1 + r2 > 1.0:
                    r1, r2 = 1.0 - r1, 1.0 - r2
                p = v0 + r1 * (v1 - v0) + r2 * (v2 - v0)
                points.append([float(p[0]), float(p[1]), float(p[2])])

            return {
                "ok": True,
                "points": points,
                "triangle_count": len(tris),
                "total_area_m2": float(total),
                "seed": seed,
                "method": "area_weighted",
            }
        except (AttributeError, NotImplementedError, RuntimeError) as exc:
            # Fall through to bbox-reachability path
            carb.log_warn(
                f"[navigation_service.sample_walkable_points] triangle iteration "
                f"unavailable ({exc}); falling back to bbox-reachability."
            )

        # ---- Path B: bbox-rejection fallback ----
        # Find NavMeshVolume bbox if user did not provide one.
        if bounds_min is None or bounds_max is None:
            stage = omni.usd.get_context().get_stage()
            volume_centers: list[Gf.Vec3d] = []
            volume_scales: list[Gf.Vec3d] = []
            for prim in stage.Traverse():
                if prim.GetTypeName() != "NavMeshVolume":
                    continue
                t_attr = prim.GetAttribute("xformOp:translate")
                s_attr = prim.GetAttribute("xformOp:scale")
                if t_attr.IsValid():
                    v = t_attr.Get()
                    volume_centers.append(Gf.Vec3d(v[0], v[1], v[2]))
                if s_attr.IsValid():
                    v = s_attr.Get()
                    volume_scales.append(Gf.Vec3d(v[0], v[1], v[2]))
            if not volume_centers:
                raise RuntimeError("No NavMeshVolume in stage; cannot derive bounds.")
            c0 = volume_centers[0]
            s0 = volume_scales[0] if volume_scales else Gf.Vec3d(20.0, 20.0, 20.0)
            bounds_min = [c0[0] - s0[0] / 2.0, c0[1] - s0[1] / 2.0, c0[2] - s0[2] / 2.0]
            bounds_max = [c0[0] + s0[0] / 2.0, c0[1] + s0[1] / 2.0, c0[2] + s0[2] / 2.0]

        # Seed origin: use bbox center, project to navmesh by Z=0 floor
        seed_origin = [
            (bounds_min[0] + bounds_max[0]) / 2.0,
            (bounds_min[1] + bounds_max[1]) / 2.0,
            0.0,
        ]
        out: list[list[float]] = []
        max_attempts = count * 50
        attempts = 0
        while len(out) < count and attempts < max_attempts:
            attempts += 1
            x = rng.uniform(bounds_min[0], bounds_max[0])
            y = rng.uniform(bounds_min[1], bounds_max[1])
            z = 0.0  # floor
            try:
                path = mesh.query_shortest_path(
                    carb.Float3(*seed_origin), carb.Float3(x, y, z),
                    agent_radius=0.25, agent_height=1.0, straighten=True,
                )
            except Exception:  # noqa: BLE001 — defensive
                path = None
            if path is None:
                continue
            pts = path.get_points() or []
            if not pts:
                continue
            last = pts[-1]
            # Snap to actual reachable end (not raw bbox sample)
            out.append([float(last.x), float(last.y), float(last.z)])

        if not out:
            raise RuntimeError(
                f"bbox-reachability sampling produced 0 points after {attempts} attempts."
            )

        return {
            "ok": True,
            "points": out[:count],
            "triangle_count": 0,
            "total_area_m2": 0.0,
            "seed": seed,
            "method": "bbox_reachability",
            "attempts": attempts,
        }

    async def query_path(self, request: dict[str, Any]) -> dict[str, Any]:
        """Query shortest path between two world positions. If NavMesh isn't
        baked yet, auto-bake once (caller doesn't need to remember)."""
        import carb  # lazy

        start = list(request["start"])
        end = list(request["end"])
        if len(start) != 3 or len(end) != 3:
            raise ValueError("start / end must be [x, y, z]")
        agent_radius = float(request.get("agent_radius", 0.0))
        agent_height = float(request.get("agent_height", 0.0))
        straighten = bool(request.get("straighten", True))

        import omni.kit.app  # lazy
        app = omni.kit.app.get_app()
        iface = self._nav()
        mesh = iface.get_navmesh()
        auto_baked = False
        if mesh is None:
            self._ensure_navmesh_volume()
            for _ in range(10):
                await app.next_update_async()
            await self._bake_if_needed()
            for _ in range(30):
                mesh = iface.get_navmesh()
                if mesh is not None:
                    break
                await app.next_update_async()
            auto_baked = True
            if mesh is None:
                return {"ok": False, "reason": "navmesh bake failed",
                        "auto_baked": auto_baked}

        path = mesh.query_shortest_path(
            carb.Float3(*start), carb.Float3(*end),
            agent_radius=agent_radius, agent_height=agent_height,
            straighten=straighten,
        )
        if path is None:
            return {"ok": False, "reason": "no path found",
                    "auto_baked": auto_baked, "start": start, "end": end}

        raw_points = path.get_points() or []
        points = [[float(p.x), float(p.y), float(p.z)] for p in raw_points]
        return {
            "ok": True,
            "auto_baked": auto_baked,
            "start": start, "end": end,
            "num_points": len(points),
            "points": points,
            "length": float(path.length()),
            "straighten": straighten,
        }


def _normalize_triangle(tri):
    """Coerce triangle representation into (Vec3d, Vec3d, Vec3d).

    Kit NavMesh build versions return triangles as either
    (Vec3, Vec3, Vec3), flat 9-tuple, or list-of-3 sub-lists.
    """
    from pxr import Gf
    if hasattr(tri, "__len__") and len(tri) == 3:
        # (Vec3, Vec3, Vec3) or [3-tuple, 3-tuple, 3-tuple]
        v0, v1, v2 = tri
        return (
            Gf.Vec3d(float(v0[0]), float(v0[1]), float(v0[2])),
            Gf.Vec3d(float(v1[0]), float(v1[1]), float(v1[2])),
            Gf.Vec3d(float(v2[0]), float(v2[1]), float(v2[2])),
        )
    if hasattr(tri, "__len__") and len(tri) == 9:
        # flat 9-tuple
        f = list(tri)
        return (
            Gf.Vec3d(f[0], f[1], f[2]),
            Gf.Vec3d(f[3], f[4], f[5]),
            Gf.Vec3d(f[6], f[7], f[8]),
        )
    raise NotImplementedError(f"Unsupported triangle shape: {type(tri)} len={len(tri) if hasattr(tri, '__len__') else '?'}")


def _cross_mag(a, b) -> float:
    import math
    cx = a[1] * b[2] - a[2] * b[1]
    cy = a[2] * b[0] - a[0] * b[2]
    cz = a[0] * b[1] - a[1] * b[0]
    return math.sqrt(cx * cx + cy * cy + cz * cz)
