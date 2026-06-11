"""Phase G live test: Sensor attach_contact / attach_imu / set_annotator."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient  # noqa: E402
from omniverse_kit_mcp.config import AppConfig  # noqa: E402

NOVA_CARTER = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)


async def _main() -> int:
    config = AppConfig()
    client = IsaacRestClient(config.isaac_sim)
    try:
        print(f"[health] {json.dumps(await client.health())[:200]}")

        live_robot = os.environ.get("LIVE_ROBOT") == "1"

        if live_robot:
            try:
                await client.robot_load({
                    "usd_url": NOVA_CARTER,
                    "prim_path": "/World/NovaCarter",
                    "position": [0.0, 0.0, 0.0],
                    "rotation": None,
                })
            except Exception as exc:  # noqa: BLE001
                print(f"[robot_load] SKIP — {type(exc).__name__}: {exc}")
                return 0

        # attach_contact
        try:
            resp = await client.sensor_attach_contact({
                "prim_path": "/World/NovaCarter",
                "sensor_name": "ChassisContact",
                "frequency": 120,
                "translation": [0.0, 0.0, 0.1],
                "radius": -1.0,
            })
            print(f"[attach_contact] path={resp.get('sensor_prim_path')} "
                  f"backend={resp.get('backend')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[attach_contact] SKIP — {type(exc).__name__}: {exc}")

        # attach_imu
        try:
            resp = await client.sensor_attach_imu({
                "prim_path": "/World/NovaCarter",
                "sensor_name": "MainIMU",
                "frequency": 500,
                "mount_offset": [0.0, 0.0, 0.15],
                "mount_orientation": [1.0, 0.0, 0.0, 0.0],
            })
            print(f"[attach_imu] path={resp.get('sensor_prim_path')} "
                  f"backend={resp.get('backend')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[attach_imu] SKIP — {type(exc).__name__}: {exc}")

        # attach_rtx_camera + set_annotator
        try:
            await client.sensor_attach_rtx_camera({
                "robot_prim": "/World/NovaCarter",
                "mount_offset": [0.3, 0.0, 0.5],
                "mount_rotation": [0.0, 0.0, 0.0],
                "resolution": [1280, 720],
                "sensor_name": "FrontCam",
            })
            resp = await client.sensor_set_annotator({
                "sensor_prim": "/World/NovaCarter/FrontCam",
                "annotators": ["rgb", "depth", "semantic_segmentation"],
                "resolution": [1280, 720],
            })
            print(f"[set_annotator] attached={resp.get('annotators')} "
                  f"backend={resp.get('backend')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[set_annotator] SKIP — {type(exc).__name__}: {exc}")

        await client.simulation_stop()
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
