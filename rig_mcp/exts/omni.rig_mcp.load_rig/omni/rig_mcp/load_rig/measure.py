"""Pure reduction of a measurement series (NO omni / pxr).

The live extension samples (sim_time, contact_force_N, joint_effort) during the lift;
this reduces the series to a summary for reporting.
"""
from __future__ import annotations


def summarize(series: list[tuple[float, float, float]]) -> dict:
    if not series:
        return {"samples": 0, "max_force": 0.0, "final_force": 0.0, "max_effort": 0.0}
    forces = [f for (_t, f, _e) in series]
    efforts = [e for (_t, _f, e) in series]
    return {
        "samples": len(series),
        "max_force": max(forces),
        "final_force": forces[-1],
        "max_effort": max(efforts, key=abs),
    }
