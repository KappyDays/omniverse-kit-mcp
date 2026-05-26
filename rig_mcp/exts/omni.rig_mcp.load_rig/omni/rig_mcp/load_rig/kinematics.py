"""Pure lift/tilt drive schedule (NO omni / pxr). Unit-testable headless."""
from __future__ import annotations

from . import config


def lift_schedule() -> list[tuple[float, float, float]]:
    """(sim_time_s, lift_target_m, tilt_target_deg): settle -> raise -> tilt."""
    return [
        (0.0, 0.0, 0.0),
        (2.0, config.LIFT_HEIGHT, 0.0),
        (4.0, config.LIFT_HEIGHT, config.TILT_ANGLE),
    ]


def final_targets() -> tuple[float, float]:
    last = lift_schedule()[-1]
    return (last[1], last[2])
