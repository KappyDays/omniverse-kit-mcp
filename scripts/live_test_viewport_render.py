"""Live test for Phase F Viewport render extension.

Exercises the 4 render-extension REST endpoints:

- POST /viewport/set_render_mode
- POST /viewport/set_render_quality
- POST /viewport/toggle_overlay
- POST /viewport/set_fov

Run:
    .venv/Scripts/python.exe scripts/live_test_viewport_render.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

BASE = (
    os.environ.get("ISAAC_SIM_BASE_URL", "http://127.0.0.1:8111").rstrip("/")
    + "/validation/v1"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "docs/artifacts/phase-f"


def _post(c, path, body):
    r = c.post(f"{BASE}{path}", json=body, timeout=60.0)
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
            _post(c, "/stage/new", None)
            _post(c, "/stage/create_prim", {
                "prim_path": "/World/Probe/Cube", "prim_type": "Cube",
                "position": [0, 0, 0.5],
            })
            _post(c, "/stage/create_prim", {
                "prim_path": "/World/Probe/Camera", "prim_type": "Camera",
                "position": [5.0, 5.0, 3.0],
            })
            _post(c, "/lighting/create_dome", {
                "prim_path": "/World/Probe/Dome", "intensity": 1000.0,
            })
            report["rt"] = _post(c, "/viewport/set_render_mode", {
                "viewport_name": "Viewport", "mode": "RealTime",
            })
            report["quality_low"] = _post(c, "/viewport/set_render_quality", {
                "samples": 1, "denoiser": "auto",
            })
            for overlay in ("gridlines", "axis", "stats"):
                report.setdefault("overlay", {})[overlay] = _post(
                    c, "/viewport/toggle_overlay",
                    {"viewport_name": "Viewport",
                     "overlay": overlay, "visible": True},
                )
            report["fov_wide"] = _post(c, "/viewport/set_fov", {
                "viewport_name": "Viewport", "fov_deg": 75.0,
            })
            report["pt"] = _post(c, "/viewport/set_render_mode", {
                "viewport_name": "Viewport", "mode": "PathTracing",
            })
            report["quality_high"] = _post(c, "/viewport/set_render_quality", {
                "samples": 16, "denoiser": "NRD",
            })
            # Reset to RealTime for the next test
            report["rt_restore"] = _post(c, "/viewport/set_render_mode", {
                "viewport_name": "Viewport", "mode": "RealTime",
            })
        _save("live_viewport_render_report.json", report)
        print(json.dumps(report, indent=2)[:2000])
        return 0
    except Exception as exc:  # noqa: BLE001
        _save("live_viewport_render_error.json", {"error": str(exc), "partial": report})
        print(f"live_test_viewport_render FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
