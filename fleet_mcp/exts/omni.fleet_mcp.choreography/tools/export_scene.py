"""Headless build + export of the fleet scene (usd-core; no Kit runtime).

Run: .venv/Scripts/python.exe fleet_mcp/exts/omni.fleet_mcp.choreography/tools/export_scene.py
"""
from __future__ import annotations

import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))
sys.dont_write_bytecode = True

from pxr import Usd, UsdGeom  # noqa: E402

from omni.fleet_mcp.choreography import config, scene_builder  # noqa: E402


def _prim_paths(stage) -> set[str]:
    return {p.GetPath().pathString for p in stage.Traverse()}


def main() -> int:
    stage = Usd.Stage.CreateInMemory()
    info = scene_builder.build(stage)

    before = _prim_paths(stage)
    scene_builder.build(stage)
    after = _prim_paths(stage)
    assert before == after, f"not idempotent; diff={before ^ after}"

    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert stage.GetPrimAtPath(config.ENV_PRIM).GetReferences()

    robots, waypoints = info["robots"], info["waypoints"]
    assert len(robots) == len(config.ROBOT_NAMES), robots
    assert len(waypoints) == len(config.LEADER_WAYPOINTS), waypoints
    for rp in robots:
        model = stage.GetPrimAtPath(rp + "/Model")
        assert model and model.GetReferences(), f"missing /Model reference under {rp}"
    for wp in waypoints:
        assert stage.GetPrimAtPath(wp).GetTypeName() == "Sphere", wp

    out = _EXT_ROOT.parents[1] / "scenes" / "fleet_scene.usd"
    out.parent.mkdir(parents=True, exist_ok=True)
    stage.GetRootLayer().Export(str(out))
    print(f"OK: env + {len(robots)} robots + {len(waypoints)} waypoints, idempotent -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
