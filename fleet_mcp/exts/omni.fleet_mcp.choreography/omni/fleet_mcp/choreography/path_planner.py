"""Pure formation + waypoint planning (NO omni / pxr). Unit-testable headless."""
from __future__ import annotations

from . import config


def formation_offsets(name: str) -> tuple[tuple[float, float], ...]:
    return config.FORMATIONS[name]


def leader_schedule() -> list[tuple[float, float, float]]:
    """Leader centroid waypoints as (x, y, cumulative_time)."""
    return [
        (x, y, i * config.WAYPOINT_DURATION)
        for i, (x, y) in enumerate(config.LEADER_WAYPOINTS)
    ]


def start_poses(formation: str) -> list[tuple[float, float]]:
    """(x, y) start pose per robot = first leader waypoint + formation offset."""
    x0, y0 = config.LEADER_WAYPOINTS[0]
    return [(x0 + dx, y0 + dy) for (dx, dy) in formation_offsets(formation)]


def robot_waypoints(formation: str) -> list[list[tuple[float, float, float]]]:
    """Per robot: list of (x, y, time) = leader schedule + that robot's offset."""
    sched = leader_schedule()
    out: list[list[tuple[float, float, float]]] = []
    for dx, dy in formation_offsets(formation):
        out.append([(x + dx, y + dy, t) for (x, y, t) in sched])
    return out
