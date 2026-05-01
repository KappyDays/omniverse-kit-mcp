"""In-process reuse of validation_api's singleton service instances.

Rather than constructing fresh service instances (which would require knowing
every constructor's dependency graph — RobotService needs JobService, etc.),
we import the already-constructed singletons from validation_api.rest_router.
This preserves single-source-of-truth for job state, sensor writers, etc. —
the same instances MCP REST calls use.
"""
from __future__ import annotations

from types import SimpleNamespace


_cached: SimpleNamespace | None = None


def get_services() -> SimpleNamespace:
    global _cached
    if _cached is not None:
        return _cached
    try:
        from omni.mycompany.validation_api import rest_router as vr
    except ImportError as exc:
        raise RuntimeError(
            "validation_api Extension is not active. "
            "Enable omni.mycompany.validation_api via the Extension Manager first."
        ) from exc

    _cached = SimpleNamespace(
        stage=vr._stage,
        robot=vr._robot,
        character=vr._character,
        navigation=vr._navigation,
        sensor=vr._sensor,
        replicator=vr._replicator,
        simulation=vr._simulation,
        jobs=vr._job,
    )
    return _cached


def reset_cache() -> None:
    """Force re-import on next get_services() — used by tests / Extension reload."""
    global _cached
    _cached = None
