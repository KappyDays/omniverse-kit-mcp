"""Live test — Phase H extension management (deactivate / list_all / get_info).

Usage:
    .venv/Scripts/python.exe scripts/live_test_extension_ext.py

Exercises:
  - POST /extension/list_all
  - POST /extension/get_info
  - POST /extension/deactivate
  - POST /extension/activate (re-enable)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8111/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_H_DIR = PROJECT_ROOT / "docs/artifacts/phase-h"

PROBE_EXT = "omni.kit.menu.utils"  # safe, widely-available core ext for get_info probe
DEMO_EXT = "omni.mycompany.ui_demo"  # safe to toggle — dev-local extension


def main() -> int:
    PHASE_H_DIR.mkdir(exist_ok=True)

    with httpx.Client(timeout=120.0) as c:
        health = c.get(f"{BASE}/health")
        if health.status_code != 200:
            print(f"FAIL — /health returned {health.status_code}: {health.text}")
            return 2

        responses: dict[str, object] = {}
        try:
            print("-- list_all (all)")
            r = c.post(f"{BASE}/extension/list_all", json={"enabled_only": False})
            r.raise_for_status()
            responses["list_all"] = {"count": r.json().get("count")}
            print(f"count={r.json().get('count')}")

            print("-- list_all (enabled_only)")
            r = c.post(f"{BASE}/extension/list_all", json={"enabled_only": True})
            r.raise_for_status()
            responses["list_enabled_only"] = {"count": r.json().get("count")}
            print(f"enabled_count={r.json().get('count')}")

            print(f"-- get_info {PROBE_EXT}")
            r = c.post(f"{BASE}/extension/get_info", json={"ext_id": PROBE_EXT})
            r.raise_for_status()
            responses["get_info_core"] = r.json()
            print(r.json())

            print(f"-- deactivate {DEMO_EXT} (tolerant)")
            r = c.post(f"{BASE}/extension/deactivate", json={"ext_id": DEMO_EXT})
            if r.status_code == 200:
                responses["deactivate_demo"] = r.json()
                print(r.json())
                print(f"-- reactivate {DEMO_EXT} reload=True")
                r = c.post(f"{BASE}/extension/activate", json={"ext_id": DEMO_EXT, "reload": True})
                r.raise_for_status()
                responses["reactivate_demo"] = r.json()
                print(r.json())
            else:
                print(f"deactivate skipped — HTTP {r.status_code}: {r.text[:200]}")
                responses["deactivate_demo_skip"] = {
                    "status": r.status_code, "body": r.text[:200],
                }
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} — {exc.response.text[:300]}")
            responses["error"] = {
                "status": exc.response.status_code, "body": exc.response.text,
            }

        (PHASE_H_DIR / "extension_ext_live_report.json").write_text(
            json.dumps(responses, indent=2), encoding="utf-8",
        )
        print(f"Saved report to {PHASE_H_DIR / 'extension_ext_live_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
