"""Live test for Phase E Sensor module — RTX Camera / Lidar / Depth Camera attach.

Exercises the 4 sensor REST endpoints against a running Isaac Sim:

- POST /sensor/attach_rtx_camera        (sensor_attach_rtx_camera tool)
- POST /sensor/attach_rtx_lidar         (sensor_attach_rtx_lidar tool)
- POST /sensor/attach_rtx_depth_camera  (sensor_attach_rtx_depth_camera tool)
- POST /sensor/set_visualization        (sensor_set_visualization tool)

Artifacts written to ``./docs/artifacts/phase-e/`` so they can be reviewed from a regular
terminal (the Extension writes original PNGs to ``%TEMP%/validation_api_captures/``).

Usage:
    .venv/Scripts/python.exe scripts/live_test_sensor.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8111/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_E_DIR = PROJECT_ROOT / "docs/artifacts/phase-e"

WAREHOUSE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Simple_Warehouse/warehouse.usd"
)
NOVA_CARTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)
JETBOT_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"
)
WAREHOUSE_PRIM = "/World/Warehouse"

# Opt-in flag: set LIVE_HEAVY_ENV=1 to load Simple_Warehouse.usd as the scene
# backdrop. Default mode skips the warehouse — S3 cold-fetch of warehouse.usd
# can exceed 10 minutes on first run and blocks the entire Kit HTTP router
# while Kit resolves every referenced prim. Phase E endpoint validation
# doesn't need the warehouse, so omit it by default and re-enable for the
# Twin 1 PPTX session where warehouse assets are already cached.
USE_HEAVY_ENV = os.environ.get("LIVE_HEAVY_ENV") == "1"

# Robot asset selector: "jetbot" (lightweight, default) or "nova_carter"
# (larger — first-cold fetch can take 10+ minutes serialized S3 reference
# resolution; use only when the asset cache is already warm).
_ROBOT_CHOICE = os.environ.get("LIVE_ROBOT", "jetbot").lower()
if _ROBOT_CHOICE == "nova_carter":
    ROBOT_USD_URL = NOVA_CARTER_URL
    ROBOT_PRIM = "/World/Robot/NovaCarter"
else:
    ROBOT_USD_URL = JETBOT_URL
    ROBOT_PRIM = "/World/Robot/Jetbot"


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


def main() -> int:
    report: dict = {}
    # httpx default (no timeout arg) applies a 5 s connect + 5 s read — far too
    # short for the first-cold S3 fetch of Simple_Warehouse.usd. Tighten later
    # once warehouse assets are cached.
    client_timeout = httpx.Timeout(connect=15.0, read=600.0, write=60.0, pool=15.0)
    with httpx.Client(timeout=client_timeout) as c:
        # Reset + optional warehouse + robot
        _post(c, "/stage/new")
        if USE_HEAVY_ENV:
            _post(c, "/stage/load_usd", json={
                "usd_url": WAREHOUSE_URL, "prim_path": WAREHOUSE_PRIM,
                "position": None, "rotation": None,
            })
        else:
            # Minimal scene — DomeLight so viewport_capture has lighting, skip
            # heavy warehouse fetch. Phase E sensor attach doesn't depend on
            # warehouse geometry.
            _post(c, "/stage/create_prim", json={
                "prim_path": "/World/DomeLight",
                "prim_type": "DomeLight",
                "position": None,
            })
        _post(c, "/robot/load", json={
            "usd_url": ROBOT_USD_URL,
            "prim_path": ROBOT_PRIM,
            "position": [0.0, 0.0, 0.0],
            "rotation": None,
        })

        # 1) RTX Camera
        rgb_resp = _post(c, "/sensor/attach_rtx_camera", json={
            "robot_prim": ROBOT_PRIM,
            "mount_offset": [0.3, 0.0, 0.8],
            "mount_rotation": [0.0, 0.0, 0.0],
            "resolution": [1280, 720],
            "sensor_name": "FrontRGB",
        })
        report["rgb"] = rgb_resp

        # 2) RTX Lidar
        lidar_resp = _post(c, "/sensor/attach_rtx_lidar", json={
            "robot_prim": ROBOT_PRIM,
            "mount_offset": [0.0, 0.0, 1.2],
            "mount_rotation": [0.0, 0.0, 0.0],
            "config_preset": "Example_Rotary",
            "sensor_name": "TopLidar",
        })
        report["lidar"] = lidar_resp

        # 3) RTX Depth Camera
        depth_resp = _post(c, "/sensor/attach_rtx_depth_camera", json={
            "robot_prim": ROBOT_PRIM,
            "mount_offset": [0.0, 0.3, 0.7],
            "mount_rotation": [0.0, 0.0, 90.0],
            "resolution": [1280, 720],
            "sensor_name": "DepthSide",
        })
        report["depth"] = depth_resp

        # 4) Toggle Lidar Debug Draw on + capture
        viz_on_resp = _post(c, "/sensor/set_visualization", json={
            "sensor_prim": lidar_resp["sensor_prim_path"],
            "mode": "on",
        })
        report["lidar_viz_on"] = viz_on_resp

        capture_on = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport",
            "camera_prim_path": None,
            "renderer": "rtx",
            "width": 1280, "height": 720,
            "samples_per_pixel": 64, "settle_frames": 5,
            "output_format": "png", "transparent_background": False,
        })
        report["viewport_after_viz_on"] = capture_on
        report["viewport_after_viz_on"]["local_path"] = _copy_capture(
            capture_on["path"], "sensor_viz_on.png",
        )

        viz_off_resp = _post(c, "/sensor/set_visualization", json={
            "sensor_prim": lidar_resp["sensor_prim_path"],
            "mode": "off",
        })
        report["lidar_viz_off"] = viz_off_resp

        # Stage snapshot containing the 3 sensor prims
        snap = _post(c, "/stage/snapshot", json={
            "include_prim_patterns": [f"{ROBOT_PRIM}/*"],
            "exclude_prim_patterns": [],
            "include_properties": False,
            "include_metadata": False,
            "max_prim_count": 50,
        })
        report["stage_snapshot_sensor_children"] = snap

    path = _save_json("sensor_live_report.json", report)
    print(f"[live_test_sensor] Phase E report: {path}")
    print(json.dumps({k: report[k].get("ok", "?") for k in report if isinstance(report[k], dict)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
