"""Live test — Phase H Replicator (writer / randomizer / trigger).

Usage:
    .venv/Scripts/python.exe scripts/live_test_replicator.py

Prerequisites:
  - Isaac Sim running with validation extension (isaac_sim_start)
  - `omni.replicator.core` enabled via ISAAC_SIM_EXTRA_EXT_IDS
  - Writable ``_temp_sdg/replicator_live`` under the project root

Exercises:
  - POST /replicator/create_writer      (BasicWriter)
  - POST /replicator/register_randomizer (position + lighting)
  - POST /replicator/trigger_once       (5 frames)
  - POST /replicator/trigger_on_time    (0.5 s)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = "http://localhost:8011/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_temp_sdg" / "replicator_live"
PHASE_H_DIR = PROJECT_ROOT / "docs/artifacts/phase-h"


def main() -> int:
    PHASE_H_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=120.0) as c:
        health = c.get(f"{BASE}/health")
        if health.status_code != 200:
            print(f"FAIL — /health returned {health.status_code}: {health.text}")
            return 2

        responses: dict[str, object] = {}
        try:
            print("-- create_writer (BasicWriter rgb+depth)")
            r = c.post(f"{BASE}/replicator/create_writer", json={
                "writer_type": "BasicWriter",
                "output_dir": str(OUTPUT_DIR),
                "rgb": True,
                "depth": True,
                "semantic_segmentation": False,
            })
            r.raise_for_status()
            responses["create_writer"] = r.json()
            print(r.json())

            print("-- register_randomizer (position)")
            r = c.post(f"{BASE}/replicator/register_randomizer", json={
                "type": "position",
                "target": "/World/*",
                "config": {"volume": [[-1, -1, 0], [1, 1, 0]]},
            })
            r.raise_for_status()
            responses["randomizer_position"] = r.json()
            print(r.json())

            print("-- register_randomizer (lighting)")
            r = c.post(f"{BASE}/replicator/register_randomizer", json={
                "type": "lighting",
                "target": "/World/*",
                "config": {"min_int": 800, "max_int": 2200},
            })
            r.raise_for_status()
            responses["randomizer_lighting"] = r.json()
            print(r.json())

            print("-- trigger_once (5 frames)")
            r = c.post(f"{BASE}/replicator/trigger_once", json={"num_frames": 5})
            r.raise_for_status()
            responses["trigger_once"] = r.json()
            print(r.json())

            print("-- trigger_on_time (0.5 s)")
            r = c.post(f"{BASE}/replicator/trigger_on_time", json={"interval_s": 0.5})
            r.raise_for_status()
            responses["trigger_on_time"] = r.json()
            print(r.json())
        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} — {exc.response.text[:300]}")
            responses["error"] = {
                "status": exc.response.status_code, "body": exc.response.text,
            }
            (PHASE_H_DIR / "replicator_live_report.json").write_text(
                json.dumps(responses, indent=2), encoding="utf-8",
            )
            return 1

        (PHASE_H_DIR / "replicator_live_report.json").write_text(
            json.dumps(responses, indent=2), encoding="utf-8",
        )
        print(f"Saved report to {PHASE_H_DIR / 'replicator_live_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
