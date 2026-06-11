"""Phase G live test: Character load_crowd + play_animation_variant."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient  # noqa: E402
from omniverse_kit_mcp.config import AppConfig  # noqa: E402

CHARACTER_USD = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/People/Characters/F_Business_02/F_Business_02.usd"
)


async def _main() -> int:
    config = AppConfig()
    client = IsaacRestClient(config.isaac_sim)
    try:
        print(f"[health] {json.dumps(await client.health())[:200]}")

        # Crowd load (grid layout, 4 members)
        try:
            resp = await client.character_load_crowd({
                "count": 4,
                "layout": "grid",
                "spacing": 2.5,
                "base_name": "Crowd",
                "center": [0.0, 0.0, 0.0],
                "usd_url": CHARACTER_USD,
            })
            print(f"[load_crowd] success={resp.get('success_count')}/"
                  f"{resp.get('count')} layout={resp.get('layout')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[load_crowd] SKIP — {type(exc).__name__}: {exc}")

        # Play animation variant on Crowd_00
        try:
            await client.simulation_play()
            await client.simulation_pause()
            resp = await client.character_play_animation_variant({
                "prim_path": "/World/Characters/Crowd_00",
                "variant": "SitReading",
                "speed": 1.0,
                "target_position": None,
            })
            print(f"[play_animation_variant] base={resp.get('base_action')} "
                  f"variables_set={list((resp.get('variables_set') or {}).keys())}")
        except Exception as exc:  # noqa: BLE001
            print(f"[play_animation_variant] SKIP — {type(exc).__name__}: {exc}")

        await client.simulation_stop()
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
