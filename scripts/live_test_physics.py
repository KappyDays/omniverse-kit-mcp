"""Live test for Phase F Physics module.

Exercises the 6 physics REST endpoints against a running Isaac Sim:

- POST /physics/set_scene
- POST /physics/apply_rigid_body
- POST /physics/apply_collider
- POST /physics/apply_material
- POST /physics/create_joint
- POST /physics/visualize

Run:
    .venv/Scripts/python.exe scripts/live_test_physics.py

Requires a running Isaac Sim (``ProcessModule.start()``) and a permissive
``/validation/v1`` router. Writes JSON results to ``./docs/artifacts/phase-f/live_physics_*.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8111/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "docs/artifacts/phase-f"
BOX_PRIM = "/World/PhaseF/Box"
GROUND_PRIM = "/World/PhaseF/Ground"
CUBE_A = "/World/PhaseF/JointA"
CUBE_B = "/World/PhaseF/JointB"


def _post(c: httpx.Client, path: str, *, json_body=None, params=None, timeout: float = 60.0):
    r = c.post(f"{BASE}{path}", json=json_body, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _save(name: str, payload) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
    )


def main() -> int:
    report: dict[str, object] = {}
    try:
        with httpx.Client() as c:
            _post(c, "/stage/new")
            scene = _post(c, "/physics/set_scene", json_body={"gravity": [0, 0, -9.81]})
            report["set_scene"] = scene

            for prim, pos in ((GROUND_PRIM, [0, 0, -0.5]), (BOX_PRIM, [0, 0, 2.0])):
                _post(c, "/stage/create_prim", json_body={
                    "prim_path": prim, "prim_type": "Cube", "position": pos,
                })

            rb = _post(c, "/physics/apply_rigid_body", json_body={
                "prim_path": BOX_PRIM, "mass": 1.0, "dynamic": True,
            })
            report["apply_rigid_body"] = rb

            collider = _post(c, "/physics/apply_collider", json_body={
                "prim_path": BOX_PRIM, "approximation": "box",
            })
            report["apply_collider"] = collider

            phys_mat = _post(c, "/physics/apply_material", json_body={
                "prim_path": BOX_PRIM, "friction": 0.7,
                "restitution": 0.2, "density": 800.0,
            })
            report["apply_material"] = phys_mat

            # Joint exercise — two cubes + a revolute
            for p, pos in ((CUBE_A, [3, 0, 1]), (CUBE_B, [4, 0, 1])):
                _post(c, "/stage/create_prim", json_body={
                    "prim_path": p, "prim_type": "Cube", "position": pos,
                })
            for p, dyn in ((CUBE_A, False), (CUBE_B, True)):
                _post(c, "/physics/apply_rigid_body", json_body={
                    "prim_path": p, "dynamic": dyn,
                })
            joint = _post(c, "/physics/create_joint", json_body={
                "joint_type": "Revolute",
                "body_a": CUBE_A,
                "body_b": CUBE_B,
                "anchor": [0.5, 0.0, 0.0],
                "axis": [0.0, 0.0, 1.0],
            })
            report["create_joint"] = joint

            for mode in ("collision", "joint", "mass", "off"):
                resp = _post(c, "/physics/visualize", json_body={"mode": mode})
                report.setdefault("visualize", {})[mode] = resp

        _save("live_physics_report.json", report)
        print(json.dumps(report, indent=2)[:2000])
        return 0
    except Exception as exc:  # noqa: BLE001
        _save("live_physics_error.json", {"error": str(exc), "partial": report})
        print(f"live_test_physics FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
