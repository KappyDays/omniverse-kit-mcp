"""Live test for Phase F Lighting module.

Exercises all 6 lighting REST endpoints:

- POST /lighting/create_{dome,distant,disk,rect,sphere}
- POST /lighting/set_exposure

Run:
    .venv/Scripts/python.exe scripts/live_test_lighting.py
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


def _post(c, path, body=None):
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
            _post(c, "/stage/new")
            report["dome"] = _post(c, "/lighting/create_dome", {
                "prim_path": "/World/Lights/Dome", "intensity": 800.0,
            })
            report["distant"] = _post(c, "/lighting/create_distant", {
                "prim_path": "/World/Lights/Sun",
                "intensity": 1500.0, "angle_deg": 0.53,
            })
            report["disk"] = _post(c, "/lighting/create_disk", {
                "prim_path": "/World/Lights/Disk",
                "intensity": 500.0, "radius": 0.6,
            })
            report["rect"] = _post(c, "/lighting/create_rect", {
                "prim_path": "/World/Lights/Window",
                "intensity": 700.0, "width": 2.0, "height": 1.0,
            })
            report["sphere"] = _post(c, "/lighting/create_sphere", {
                "prim_path": "/World/Lights/Bulb",
                "intensity": 400.0, "radius": 0.1,
            })
            for exp in (-1.0, 0.0, 1.5, 0.0):
                report.setdefault("exposure", {})[str(exp)] = _post(
                    c, "/lighting/set_exposure", {"exposure": exp},
                )
        _save("live_lighting_report.json", report)
        print(json.dumps(report, indent=2)[:2000])
        return 0
    except Exception as exc:  # noqa: BLE001
        _save("live_lighting_error.json", {"error": str(exc), "partial": report})
        print(f"live_test_lighting FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
