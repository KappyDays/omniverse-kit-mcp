"""Live test — Phase H OmniGraph (node / connect / execute + ROS2 publisher).

Usage:
    .venv/Scripts/python.exe scripts/live_test_omnigraph.py

Exercises:
  - POST /omnigraph/create_node          (OnTick + Counter)
  - POST /omnigraph/connect              (OnTick.outputs:tick → Counter.inputs:execIn)
  - POST /omnigraph/execute              (one-shot evaluate)
  - POST /omnigraph/create_ros2_publisher
    (graph structure assembled regardless of rclpy availability — response reports ros2_available)
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


def main() -> int:
    PHASE_H_DIR.mkdir(exist_ok=True)

    with httpx.Client(timeout=120.0) as c:
        health = c.get(f"{BASE}/health")
        if health.status_code != 200:
            print(f"FAIL — /health returned {health.status_code}: {health.text}")
            return 2

        responses: dict[str, object] = {}
        try:
            # Ensure a Camera for the ROS2 publisher test
            r = c.post(f"{BASE}/stage/create_prim", json={
                "prim_path": "/World/PublisherCamera", "prim_type": "Camera",
            })
            r.raise_for_status()

            print("-- create_node OnTick")
            r = c.post(f"{BASE}/omnigraph/create_node", json={
                "graph_path": "/World/LiveActionGraph",
                "node_type": "omni.graph.action.OnTick",
                "node_name": "OnTick",
            })
            r.raise_for_status()
            responses["create_node_on_tick"] = r.json()
            print(r.json())

            print("-- create_node Counter")
            r = c.post(f"{BASE}/omnigraph/create_node", json={
                "graph_path": "/World/LiveActionGraph",
                "node_type": "omni.graph.nodes.Counter",
                "node_name": "Counter",
            })
            r.raise_for_status()
            responses["create_node_counter"] = r.json()
            print(r.json())

            print("-- connect OnTick.tick → Counter.execIn")
            r = c.post(f"{BASE}/omnigraph/connect", json={
                "src_attr": "/World/LiveActionGraph/OnTick.outputs:tick",
                "dst_attr": "/World/LiveActionGraph/Counter.inputs:execIn",
            })
            r.raise_for_status()
            responses["connect"] = r.json()
            print(r.json())

            print("-- execute graph")
            r = c.post(f"{BASE}/omnigraph/execute", json={
                "graph_path": "/World/LiveActionGraph",
            })
            r.raise_for_status()
            responses["execute"] = r.json()
            print(r.json())

            print("-- create_ros2_publisher (graph structure)")
            r = c.post(f"{BASE}/omnigraph/create_ros2_publisher", json={
                "graph_path": "/World/RosPubLive",
                "topic": "/validation/image",
                "source_prim": "/World/PublisherCamera",
                "msg_type": "sensor_msgs/msg/Image",
            })
            r.raise_for_status()
            responses["create_ros2_publisher"] = r.json()
            print(r.json())

        except httpx.HTTPStatusError as exc:
            print(f"HTTP error: {exc.response.status_code} — {exc.response.text[:300]}")
            responses["error"] = {
                "status": exc.response.status_code, "body": exc.response.text,
            }

        (PHASE_H_DIR / "omnigraph_live_report.json").write_text(
            json.dumps(responses, indent=2), encoding="utf-8",
        )
        print(f"Saved report to {PHASE_H_DIR / 'omnigraph_live_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
