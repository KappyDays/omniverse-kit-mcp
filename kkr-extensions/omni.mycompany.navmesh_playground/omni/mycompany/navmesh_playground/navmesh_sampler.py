"""Area-weighted random point sampler on baked NavMesh (independent copy).

Spec §8.1. Mirrors validation_api.navigation_service.sample_walkable_points
algorithmically (independent ext policy, 2026-04-22). Falls back to bbox-
rejection + reachability when triangle iteration API is absent.
"""
from __future__ import annotations

import math
import random
from bisect import bisect_left
from itertools import accumulate
from typing import Sequence


def query_shortest_path(
    mesh,
    start: Sequence[float],
    goal: Sequence[float],
    *,
    agent_radius: float,
    agent_height: float,
    straighten: bool = True,
):
    """Compatibility wrapper for Kit 107/Isaac Sim 6.0 NavMesh queries."""
    import carb  # lazy

    start_pos = carb.Float3(*start)
    goal_pos = carb.Float3(*goal)
    agent = _make_nav_agent_desc(agent_radius, agent_height)
    if agent is not None:
        try:
            import numpy as np  # lazy
            return mesh.query_shortest_path(
                start_pos, goal_pos, agent, np.array([], dtype=np.float32),
                bool(straighten),
            )
        except TypeError:
            pass

    return mesh.query_shortest_path(
        start_pos, goal_pos,
        agent_radius=float(agent_radius),
        agent_height=float(agent_height),
        straighten=bool(straighten),
    )


def _make_nav_agent_desc(agent_radius: float, agent_height: float):
    try:
        import omni.anim.navigation.core as nav  # lazy
        desc = nav.NavAgentDesc()
    except Exception:  # noqa: BLE001
        return None
    if hasattr(desc, "radius"):
        desc.radius = float(agent_radius)
    if hasattr(desc, "height"):
        desc.height = float(agent_height)
    return desc


def sample_walkable_points_sync(
    count: int,
    bounds_min: Sequence[float] | None = None,
    bounds_max: Sequence[float] | None = None,
    seed: int | None = None,
) -> list[tuple[float, float, float]]:
    """Sync wrapper — UI thread direct (no Kit main loop yield).

    Use from omni.ui callback. Trades responsiveness (UI freezes briefly
    during many query_shortest_path attempts) for correctness — the async
    variant's run_coroutine schedule path conflicts with character mesh
    Hydra processing in the same Kit main loop slot.
    """
    return _sample_impl(count, bounds_min, bounds_max, seed)


async def sample_walkable_points(
    count: int,
    bounds_min: Sequence[float] | None = None,
    bounds_max: Sequence[float] | None = None,
    seed: int | None = None,
) -> list[tuple[float, float, float]]:
    """Async wrapper — kept for legacy callers; identical to sync."""
    return _sample_impl(count, bounds_min, bounds_max, seed)


def _sample_impl(
    count: int,
    bounds_min,
    bounds_max,
    seed,
) -> list[tuple[float, float, float]]:
    import omni.anim.navigation.core as nav  # lazy

    if not (1 <= count <= 1000):
        raise ValueError(f"count out of range [1, 1000]: {count}")

    iface = nav.acquire_interface()
    mesh = iface.get_navmesh()
    if mesh is None:
        raise RuntimeError("NavMesh not baked. Bake first.")

    rng = random.Random(seed)

    # ---- Path A: area-weighted triangle iteration ----
    tri_count_fn = getattr(mesh, "get_triangle_count", None)
    tri_get_fn = getattr(mesh, "get_triangle", None)
    if tri_count_fn is not None and tri_get_fn is not None:
        try:
            n = int(tri_count_fn())
            if n > 0:
                tris: list[tuple[tuple[float, float, float],
                                  tuple[float, float, float],
                                  tuple[float, float, float]]] = []
                areas: list[float] = []
                for i in range(n):
                    raw = tri_get_fn(i)
                    v0, v1, v2 = _normalize(raw)
                    if bounds_min is not None and bounds_max is not None:
                        cx = (v0[0] + v1[0] + v2[0]) / 3.0
                        cy = (v0[1] + v1[1] + v2[1]) / 3.0
                        cz = (v0[2] + v1[2] + v2[2]) / 3.0
                        if not (
                            bounds_min[0] <= cx <= bounds_max[0]
                            and bounds_min[1] <= cy <= bounds_max[1]
                            and bounds_min[2] <= cz <= bounds_max[2]
                        ):
                            continue
                    e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
                    e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
                    area = 0.5 * _cross_mag(e1, e2)
                    if area <= 0.0:
                        continue
                    tris.append((v0, v1, v2))
                    areas.append(area)

                if tris:
                    cum = list(accumulate(areas))
                    total = cum[-1]
                    out: list[tuple[float, float, float]] = []
                    for _ in range(count):
                        idx = bisect_left(cum, rng.random() * total)
                        v0, v1, v2 = tris[idx]
                        r1 = rng.random()
                        r2 = rng.random()
                        if r1 + r2 > 1.0:
                            r1, r2 = 1.0 - r1, 1.0 - r2
                        x = v0[0] + r1 * (v1[0] - v0[0]) + r2 * (v2[0] - v0[0])
                        y = v0[1] + r1 * (v1[1] - v0[1]) + r2 * (v2[1] - v0[1])
                        z = v0[2] + r1 * (v1[2] - v0[2]) + r2 * (v2[2] - v0[2])
                        out.append((x, y, z))
                    return out
        except Exception:  # noqa: BLE001 — fall through to fallback
            pass

    # ---- Path B: bbox-rejection fallback ----
    return _sample_via_reachability(mesh, count, bounds_min, bounds_max, rng)


def _sample_via_reachability(
    mesh,
    count: int,
    bounds_min: Sequence[float] | None,
    bounds_max: Sequence[float] | None,
    rng: random.Random,
) -> list[tuple[float, float, float]]:
    """Fallback sampler — random bbox point + query_shortest_path reachability."""
    import omni.usd

    if bounds_min is None or bounds_max is None:
        # Discover from NavMeshVolume in stage
        stage = omni.usd.get_context().get_stage()
        center = (0.0, 0.0, 0.0)
        scale = (20.0, 20.0, 20.0)
        for prim in stage.Traverse():
            if prim.GetTypeName() != "NavMeshVolume":
                continue
            t = prim.GetAttribute("xformOp:translate")
            s = prim.GetAttribute("xformOp:scale")
            if t.IsValid():
                v = t.Get()
                center = (float(v[0]), float(v[1]), float(v[2]))
            if s.IsValid():
                v = s.Get()
                scale = (float(v[0]), float(v[1]), float(v[2]))
            break
        bounds_min = (
            center[0] - scale[0] / 2.0,
            center[1] - scale[1] / 2.0,
            center[2] - scale[2] / 2.0,
        )
        bounds_max = (
            center[0] + scale[0] / 2.0,
            center[1] + scale[1] / 2.0,
            center[2] + scale[2] / 2.0,
        )

    seed_origin = (
        (bounds_min[0] + bounds_max[0]) / 2.0,
        (bounds_min[1] + bounds_max[1]) / 2.0,
        0.0,
    )
    out: list[tuple[float, float, float]] = []
    max_attempts = count * 50
    attempts = 0
    while len(out) < count and attempts < max_attempts:
        attempts += 1
        x = rng.uniform(bounds_min[0], bounds_max[0])
        y = rng.uniform(bounds_min[1], bounds_max[1])
        try:
            path = query_shortest_path(
                mesh, seed_origin, (x, y, 0.0),
                agent_radius=0.25, agent_height=1.0, straighten=True,
            )
        except Exception:  # noqa: BLE001
            path = None
        if path is not None:
            pts = path.get_points() or []
            if pts:
                last = pts[-1]
                out.append((float(last.x), float(last.y), float(last.z)))
    if not out:
        raise RuntimeError(
            f"bbox-reachability sampling produced 0 points after {attempts} attempts."
        )
    return out


def _normalize(tri):
    """Coerce triangle representation to ((x,y,z), (x,y,z), (x,y,z)) tuples."""
    if hasattr(tri, "__len__") and len(tri) == 3:
        v0, v1, v2 = tri
        return (
            (float(v0[0]), float(v0[1]), float(v0[2])),
            (float(v1[0]), float(v1[1]), float(v1[2])),
            (float(v2[0]), float(v2[1]), float(v2[2])),
        )
    if hasattr(tri, "__len__") and len(tri) == 9:
        f = list(tri)
        return (
            (float(f[0]), float(f[1]), float(f[2])),
            (float(f[3]), float(f[4]), float(f[5])),
            (float(f[6]), float(f[7]), float(f[8])),
        )
    raise NotImplementedError(f"Unsupported triangle shape: {type(tri)}")


def _cross_mag(a, b) -> float:
    cx = a[1] * b[2] - a[2] * b[1]
    cy = a[2] * b[0] - a[0] * b[2]
    cz = a[0] * b[1] - a[1] * b[0]
    return math.sqrt(cx * cx + cy * cy + cz * cz)
