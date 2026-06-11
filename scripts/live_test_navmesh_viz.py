"""Live test for Phase E navigation_set_visualization.

Runs the canonical 3-candidate research: bakes the NavMesh on Simple_Warehouse
and cycles the overlay through {walkable → obstacles → off}, capturing the
viewport after each toggle so callers can visually confirm the backend
(carb_settings vs prim_visibility fallback) produces distinct output.

Artifacts saved to ``./docs/artifacts/phase-e/`` as:
- navmesh_walkable.png
- navmesh_obstacles.png
- navmesh_off.png
- navmesh_viz_live_report.json
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import httpx

BASE = (
    os.environ.get("ISAAC_SIM_BASE_URL", "http://127.0.0.1:8111").rstrip("/")
    + "/validation/v1"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_E_DIR = PROJECT_ROOT / "docs/artifacts/phase-e"

WAREHOUSE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Simple_Warehouse/warehouse.usd"
)
WAREHOUSE_PRIM = "/World/Warehouse"

# Opt-in: LIVE_HEAVY_ENV=1 loads Simple_Warehouse.usd (>10 min cold fetch).
# Default minimal mode builds a DomeLight + ground Plane + a few Cube
# obstacles so NavMesh bake has something non-trivial to walk on.
USE_HEAVY_ENV = os.environ.get("LIVE_HEAVY_ENV") == "1"


def _post(c: httpx.Client, path: str, *, json=None, params=None, timeout: float = 600.0):
    r = c.post(f"{BASE}{path}", json=json, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _copy_capture(src_path: str, dest_name: str) -> str:
    PHASE_E_DIR.mkdir(parents=True, exist_ok=True)
    dest = PHASE_E_DIR / dest_name
    shutil.copy2(src_path, dest)
    return str(dest)


def _save_json(name: str, data) -> str:
    PHASE_E_DIR.mkdir(parents=True, exist_ok=True)
    p = PHASE_E_DIR / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(p)


def _capture(c: httpx.Client, tag: str) -> dict:
    raw = _post(c, "/viewport/capture", json={
        "viewport_name": "Viewport",
        "camera_prim_path": None,
        "renderer": "rtx",
        "width": 1280, "height": 720,
        "samples_per_pixel": 64, "settle_frames": 5,
        "output_format": "png", "transparent_background": False,
    })
    local = _copy_capture(raw["path"], f"navmesh_{tag}.png")
    raw["local_path"] = local
    return raw


def main() -> int:
    report: dict = {}
    client_timeout = httpx.Timeout(connect=15.0, read=600.0, write=60.0, pool=15.0)
    with httpx.Client(timeout=client_timeout) as c:
        # Arrange
        _post(c, "/stage/new")
        if USE_HEAVY_ENV:
            _post(c, "/stage/load_usd", json={
                "usd_url": WAREHOUSE_URL, "prim_path": WAREHOUSE_PRIM,
                "position": None, "rotation": None,
            })
        else:
            # Minimal walkable scene: DomeLight + ground Plane + 3 obstacle
            # Cubes spread around. NavMesh bake covers the plane's walkable
            # area; the cubes give the overlay something to highlight.
            _post(c, "/stage/create_prim", json={
                "prim_path": "/World/DomeLight",
                "prim_type": "DomeLight", "position": None,
            })
            _post(c, "/stage/create_prim", json={
                "prim_path": "/World/Ground",
                "prim_type": "Plane", "position": None,
            })
            # Scale ground to be large enough for NavMesh to have area
            _post(c, "/stage/set_property", json={
                "prim_path": "/World/Ground",
                "property_name": "xformOp:scale",
                "value": [20.0, 20.0, 1.0],
                "type_hint": "Vec3d",
            })
            for i, (x, y) in enumerate([(3.0, 2.0), (-4.0, 1.5), (2.0, -3.0)]):
                _post(c, "/stage/create_prim", json={
                    "prim_path": f"/World/Obstacle{i}",
                    "prim_type": "Cube",
                    "position": [x, y, 0.5],
                })
        # R1a — bake requires timeline stopped
        _post(c, "/simulation/stop")

        bake = _post(c, "/navigation/bake", params={
            "volume_scale": 40.0, "timeout_s": 300.0,
        })
        report["bake"] = bake

        # Cycle overlay modes
        report["viz_walkable"] = _post(c, "/navigation/set_visualization", json={
            "mode": "walkable",
        })
        report["capture_walkable"] = _capture(c, "walkable")

        report["viz_obstacles"] = _post(c, "/navigation/set_visualization", json={
            "mode": "obstacles",
        })
        report["capture_obstacles"] = _capture(c, "obstacles")

        report["viz_off"] = _post(c, "/navigation/set_visualization", json={
            "mode": "off",
        })
        report["capture_off"] = _capture(c, "off")

    path = _save_json("navmesh_viz_live_report.json", report)
    print(f"[live_test_navmesh_viz] Phase E report: {path}")
    backends = {k: report[k].get("backend") for k in ("viz_walkable", "viz_obstacles", "viz_off")}
    print(f"[live_test_navmesh_viz] backends: {backends}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
