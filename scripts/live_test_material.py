"""Live test for Phase F Material module.

Exercises the 3 material REST endpoints:

- GET  /material/list_mdl
- POST /material/assign_mdl
- GET  /material/get_bound

Run:
    .venv/Scripts/python.exe scripts/live_test_material.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8111/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "docs/artifacts/phase-f"


def _save(name: str, payload) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
    )


def main() -> int:
    report: dict[str, object] = {}
    try:
        with httpx.Client() as c:
            c.post(f"{BASE}/stage/new", timeout=60.0)
            c.post(
                f"{BASE}/stage/create_prim",
                json={"prim_path": "/World/MaterialCube", "prim_type": "Cube"},
                timeout=60.0,
            ).raise_for_status()

            r = c.get(f"{BASE}/material/list_mdl", params={"library": "default"}, timeout=60.0)
            r.raise_for_status()
            listing = r.json()
            report["list_mdl"] = {
                "count": listing.get("count"),
                "first_10": (listing.get("entries") or [])[:10],
            }

            assign = c.post(
                f"{BASE}/material/assign_mdl",
                json={
                    "prim_path": "/World/MaterialCube",
                    "mdl_url": "OmniPBR.mdl",
                    "material_name": "OmniPBR_Live",
                },
                timeout=60.0,
            )
            assign.raise_for_status()
            report["assign_mdl"] = assign.json()

            r = c.get(
                f"{BASE}/material/get_bound",
                params={"prim_path": "/World/MaterialCube"},
                timeout=60.0,
            )
            r.raise_for_status()
            report["get_bound"] = r.json()

        _save("live_material_report.json", report)
        print(json.dumps(report, indent=2)[:2000])
        return 0
    except Exception as exc:  # noqa: BLE001
        _save("live_material_error.json", {"error": str(exc), "partial": report})
        print(f"live_test_material FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
