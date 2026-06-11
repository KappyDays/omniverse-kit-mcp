"""Live test — Phase H Content (browse / preview / resolve).

Usage:
    .venv/Scripts/python.exe scripts/live_test_content.py

Exercises:
  - POST /content/browse   (S3 Isaac Sim asset root — categories)
  - POST /content/resolve  (file:/// local path)
  - POST /content/preview  (single USD stat)
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
PHASE_H_DIR = PROJECT_ROOT / "docs/artifacts/phase-h"

S3_ASSETS_ROOT = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac"
)
WAREHOUSE_USD = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Simple_Warehouse/warehouse.usd"
)
LOCAL_PROBE = str(PROJECT_ROOT / "README.md")


def main() -> int:
    PHASE_H_DIR.mkdir(exist_ok=True)

    with httpx.Client(timeout=120.0) as c:
        health = c.get(f"{BASE}/health")
        if health.status_code != 200:
            print(f"FAIL — /health returned {health.status_code}: {health.text}")
            return 2

        responses: dict[str, object] = {}
        try:
            print("-- browse S3 Isaac root")
            r = c.post(f"{BASE}/content/browse", json={
                "url": S3_ASSETS_ROOT, "recursive": False, "max_depth": 1,
                "max_entries": 50,
            })
            r.raise_for_status()
            responses["browse_s3"] = r.json()
            print(f"entries={r.json().get('entry_count')}")

            print("-- resolve local path")
            r = c.post(f"{BASE}/content/resolve", json={"url": f"file:///{LOCAL_PROBE.replace(chr(92), '/')}"})
            r.raise_for_status()
            responses["resolve_local"] = r.json()
            print(r.json())

            print("-- preview warehouse.usd")
            r = c.post(f"{BASE}/content/preview", json={"url": WAREHOUSE_USD})
            r.raise_for_status()
            responses["preview_warehouse"] = r.json()
            print(r.json())
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} — {exc.response.text[:300]}")
            responses["error"] = {
                "status": exc.response.status_code, "body": exc.response.text,
            }

        (PHASE_H_DIR / "content_live_report.json").write_text(
            json.dumps(responses, indent=2), encoding="utf-8",
        )
        print(f"Saved report to {PHASE_H_DIR / 'content_live_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
