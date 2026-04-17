"""Live test for Phase B+ GUI-equivalent endpoints.

Covers new tools: stage_new / stage_create_prim(Camera, DistantLight) /
stage_set_selection / stage_get_selection / viewport_set_active_camera /
stage_save / stage_open. Requires Isaac Sim Extension running at 8011.

Usage: .venv/Scripts/python.exe scripts/live_test_gui_equiv.py
"""

from __future__ import annotations

import os
import sys
import tempfile

import httpx

BASE = "http://localhost:8011/validation/v1"


def _post(c: httpx.Client, path: str, *, json=None, params=None):
    url = f"{BASE}{path}"
    r = c.post(url, json=json, params=params)
    r.raise_for_status()
    return r.json()


def _get(c: httpx.Client, path: str, *, params=None):
    url = f"{BASE}{path}"
    r = c.get(url, params=params)
    r.raise_for_status()
    return r.json()


def main() -> int:
    save_path = os.path.join(tempfile.gettempdir(), "isaacsim_mcp_phase_b_test.usd").replace("\\", "/")
    report: dict[str, object] = {}

    with httpx.Client(timeout=60) as c:
        # 1. New empty stage
        report["stage_new"] = _post(c, "/stage/new")

        # 2. Create Xform + Cube + Camera + DistantLight (GUI Create menu)
        report["create_world"] = _post(c, "/stage/create_prim", json={
            "prim_path": "/World", "prim_type": "Xform",
        })
        report["create_cube"] = _post(c, "/stage/create_prim", json={
            "prim_path": "/World/Cube", "prim_type": "Cube", "position": [0, 0, 0.5],
        })
        report["create_camera"] = _post(c, "/stage/create_prim", json={
            "prim_path": "/World/Cam1", "prim_type": "Camera", "position": [3.0, 3.0, 2.0],
        })
        report["create_light"] = _post(c, "/stage/create_prim", json={
            "prim_path": "/World/Sun", "prim_type": "DistantLight",
        })

        # 3. Selection round-trip
        report["set_selection"] = _post(c, "/stage/selection", json={
            "prim_paths": ["/World/Cube", "/World/Cam1"],
            "expand_in_stage": True,
        })
        report["get_selection"] = _get(c, "/stage/selection")

        # 4. Active camera switch
        report["active_camera"] = _post(c, "/viewport/active_camera", json={
            "camera_path": "/World/Cam1",
            "viewport_name": "Viewport",
        })

        # 5. Capture viewport through the new camera
        report["capture"] = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport",
            "width": 800,
            "height": 600,
            "output_format": "png",
        })

        # 6. Save stage
        report["save"] = _post(c, "/stage/save", params={"path": save_path})

        # 7. Clear and open back
        report["new_again"] = _post(c, "/stage/new")
        report["open"] = _post(c, "/stage/open", params={"url": save_path})

        # 8. Verify the cube we saved is back
        report["verify_cube"] = _post(c, "/stage/assert/prim-exists", json={
            "prim_path": "/World/Cube", "should_exist": True,
        })
        report["verify_camera"] = _post(c, "/stage/assert/prim-exists", json={
            "prim_path": "/World/Cam1", "should_exist": True,
        })
        report["verify_light"] = _post(c, "/stage/assert/prim-exists", json={
            "prim_path": "/World/Sun", "should_exist": True,
        })

    import json
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    # Success requires every step ok/passed
    for name, res in report.items():
        if isinstance(res, dict):
            if res.get("ok") is False:
                print(f"FAIL: {name} ok=false", file=sys.stderr)
                return 1
            if "passed" in res and res["passed"] is False:
                print(f"FAIL: {name} passed=false", file=sys.stderr)
                return 1
    print(f"SAVE_PATH={save_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
