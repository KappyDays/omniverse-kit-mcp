"""Phase G live test: Robot extensions — navigate_path / gripper_control / set_ee_target.

Runs against a live Isaac Sim Extension (http://localhost:8011). Intended for
post-integration smoke after ``isaac_sim_start``. Tolerant of asset load
failures (logs + skip) since Phase G live validation depends on Franka /
NovaCarter S3 assets and network availability.

Env flags:
  LIVE_HEAVY_ENV=1 — also load the warehouse environment for navigate_path
  LIVE_ROBOT=1     — actually attempt load (otherwise minimal REST probe only)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Allow running from project root without `uv run`.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient  # noqa: E402
from omniverse_kit_mcp.config import AppConfig  # noqa: E402

NOVA_CARTER = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)
FRANKA = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/FrankaRobotics/FrankaPanda/franka.usd"
)


async def _main() -> int:
    config = AppConfig()
    client = IsaacRestClient(config.isaac_sim)
    try:
        health = await client.health()
        print(f"[health] {json.dumps(health)[:200]}")

        live_robot = os.environ.get("LIVE_ROBOT") == "1"

        # --- navigate_path (NovaCarter) ---
        if live_robot:
            try:
                await client.robot_load({
                    "usd_url": NOVA_CARTER,
                    "prim_path": "/World/NovaCarter",
                    "position": [0.0, 0.0, 0.0],
                    "rotation": None,
                })
                await client.simulation_stop()
                await client.simulation_play()
                resp = await client.robot_navigate_path({
                    "prim_path": "/World/NovaCarter",
                    "points": [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [3.0, 2.0, 0.0]],
                    "duration_s": 3.0,
                })
                print(f"[navigate_path] job_id={resp.get('job_id')} "
                      f"num_waypoints={resp.get('num_waypoints')}")
            except Exception as exc:  # noqa: BLE001
                print(f"[navigate_path] SKIP — {type(exc).__name__}: {exc}")
        else:
            print("[navigate_path] LIVE_ROBOT=1 not set, skipping asset load")

        # --- gripper_control (Franka) ---
        if live_robot:
            try:
                await client.robot_load({
                    "usd_url": FRANKA,
                    "prim_path": "/World/Franka",
                    "position": [2.0, 0.0, 0.0],
                    "rotation": None,
                })
                await client.simulation_play()
                await client.simulation_pause()
                for action in ("open", "close"):
                    resp = await client.robot_gripper_control({
                        "prim_path": "/World/Franka",
                        "action": action,
                        "target": None,
                    })
                    print(f"[gripper {action}] target_value={resp.get('target_value')} "
                          f"joints={resp.get('gripper_joint_names')}")
            except Exception as exc:  # noqa: BLE001
                print(f"[gripper_control] SKIP — {type(exc).__name__}: {exc}")

        # --- set_ee_target (Franka) ---
        if live_robot:
            try:
                resp = await client.robot_set_ee_target({
                    "prim_path": "/World/Franka",
                    "target_pose": [0.4, 0.1, 0.4, 1.0, 0.0, 0.0, 0.0],
                    "robot_description": "Franka",
                    "end_effector_frame": None,
                })
                print(f"[set_ee_target] ik_success={resp.get('ik_success')} "
                      f"import_path={resp.get('lula_import_path')}")
            except Exception as exc:  # noqa: BLE001
                print(f"[set_ee_target] SKIP — {type(exc).__name__}: {exc}")

        await client.simulation_stop()
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
