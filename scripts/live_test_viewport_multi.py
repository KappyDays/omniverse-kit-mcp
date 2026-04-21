"""Live test for Phase E multi-viewport — viewport_create / destroy against Kit.

Creates 2 aux viewports bound to camera prims (the default perspective + an
RTX Camera attached via Phase E sensor_attach_rtx_camera), captures from each,
then destroys them. Proves the Extension can materialize extra
``omni.kit.viewport.window`` instances and bind them to per-sensor cameras.

Artifacts saved to ``./docs/artifacts/phase-e/`` for later review.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8011/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_E_DIR = PROJECT_ROOT / "docs/artifacts/phase-e"

WAREHOUSE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Simple_Warehouse/warehouse.usd"
)
NOVA_CARTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)
JETBOT_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd"
)
WAREHOUSE_PRIM = "/World/Warehouse"

# Opt-in: LIVE_HEAVY_ENV=1 loads Simple_Warehouse.usd (>10 min on cold S3).
# Default minimal mode just adds a DomeLight + lightweight robot so
# viewport_multi can validate create/destroy without heavy assets.
USE_HEAVY_ENV = os.environ.get("LIVE_HEAVY_ENV") == "1"
_ROBOT_CHOICE = os.environ.get("LIVE_ROBOT", "jetbot").lower()
if _ROBOT_CHOICE == "nova_carter":
    ROBOT_USD_URL = NOVA_CARTER_URL
    ROBOT_PRIM = "/World/Robot/NovaCarter"
else:
    ROBOT_USD_URL = JETBOT_URL
    ROBOT_PRIM = "/World/Robot/Jetbot"


def _post(c: httpx.Client, path: str, *, json=None, timeout: float = 600.0):
    r = c.post(f"{BASE}{path}", json=json, timeout=timeout)
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
    client_timeout = httpx.Timeout(connect=15.0, read=600.0, write=60.0, pool=15.0)
    with httpx.Client(timeout=client_timeout) as c:
        _post(c, "/stage/new")
        if USE_HEAVY_ENV:
            _post(c, "/stage/load_usd", json={
                "usd_url": WAREHOUSE_URL, "prim_path": WAREHOUSE_PRIM,
                "position": None, "rotation": None,
            })
        else:
            _post(c, "/stage/create_prim", json={
                "prim_path": "/World/DomeLight",
                "prim_type": "DomeLight",
                "position": None,
            })
        _post(c, "/robot/load", json={
            "usd_url": ROBOT_USD_URL, "prim_path": ROBOT_PRIM,
            "position": [0.0, 0.0, 0.0], "rotation": None,
        })
        rgb = _post(c, "/sensor/attach_rtx_camera", json={
            "robot_prim": ROBOT_PRIM,
            "mount_offset": [0.3, 0.0, 0.8],
            "mount_rotation": [0.0, 0.0, 0.0],
            "resolution": [960, 540],
            "sensor_name": "FrontRGB",
        })
        report["rgb_sensor"] = rgb

        # Create 2 aux viewports
        vp_front = _post(c, "/viewport/create", json={
            "viewport_name": "Viewport_Front",
            "camera_path": rgb["sensor_prim_path"],
            "width": 960, "height": 540, "docked": False,
        })
        vp_persp = _post(c, "/viewport/create", json={
            "viewport_name": "Viewport_Persp",
            "camera_path": "/OmniverseKit_Persp",
            "width": 960, "height": 540, "docked": False,
        })
        report["viewport_front_create"] = vp_front
        report["viewport_persp_create"] = vp_persp

        # Idempotency: create again — expect existed=True
        vp_front_again = _post(c, "/viewport/create", json={
            "viewport_name": "Viewport_Front",
            "camera_path": rgb["sensor_prim_path"],
            "width": 960, "height": 540, "docked": False,
        })
        report["viewport_front_create_again"] = vp_front_again
        assert vp_front_again.get("existed") is True, "Second create must report existed=True"

        # Capture from each (camera_prim_path hint is accepted by viewport_capture)
        cap_front = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport_Front",
            "camera_prim_path": rgb["sensor_prim_path"],
            "renderer": "rtx", "width": 960, "height": 540,
            "samples_per_pixel": 64, "settle_frames": 5,
            "output_format": "png", "transparent_background": False,
        })
        cap_persp = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport_Persp",
            "camera_prim_path": "/OmniverseKit_Persp",
            "renderer": "rtx", "width": 960, "height": 540,
            "samples_per_pixel": 64, "settle_frames": 5,
            "output_format": "png", "transparent_background": False,
        })
        report["capture_front"] = {
            **cap_front,
            "local_path": _copy_capture(cap_front["path"], "viewport_front.png"),
        }
        report["capture_persp"] = {
            **cap_persp,
            "local_path": _copy_capture(cap_persp["path"], "viewport_persp.png"),
        }

        # Tear down
        report["destroy_front"] = _post(c, "/viewport/destroy", json={
            "viewport_name": "Viewport_Front",
        })
        report["destroy_persp"] = _post(c, "/viewport/destroy", json={
            "viewport_name": "Viewport_Persp",
        })
        # Destroy non-existent — must NOT raise
        report["destroy_missing"] = _post(c, "/viewport/destroy", json={
            "viewport_name": "Viewport_DoesNotExist",
        })

    path = _save_json("viewport_multi_live_report.json", report)
    print(f"[live_test_viewport_multi] Phase E report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
