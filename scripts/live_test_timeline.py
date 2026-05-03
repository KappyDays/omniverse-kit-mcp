"""Phase G live test: Simulation timeline extensions — step / set_time."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient  # noqa: E402
from omniverse_kit_mcp.config import AppConfig  # noqa: E402


async def _main() -> int:
    config = AppConfig()
    client = IsaacRestClient(config.isaac_sim)
    try:
        print(f"[health] {json.dumps(await client.health())[:200]}")

        # Stop first (deterministic starting point)
        await client.simulation_stop()
        status = await client.simulation_status()
        print(f"[start] current_time={status.get('current_time')}")

        # simulation_step
        try:
            resp = await client.simulation_step({"frames": 30})
            print(f"[step] frames=30 mode={resp.get('advance_mode')} "
                  f"was_playing={resp.get('was_playing')} "
                  f"current_time={resp.get('current_time')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[step] SKIP — {type(exc).__name__}: {exc}")

        # simulation_set_time
        try:
            resp = await client.simulation_set_time({"time_seconds": 3.5})
            print(f"[set_time] requested={resp.get('requested_time')} "
                  f"previous={resp.get('previous_time')} "
                  f"current_time={resp.get('current_time')}")
        except Exception as exc:  # noqa: BLE001
            print(f"[set_time] SKIP — {type(exc).__name__}: {exc}")

        # Final status
        final = await client.simulation_status()
        print(f"[final] current_time={final.get('current_time')} "
              f"is_playing={final.get('is_playing')}")

        await client.simulation_stop()
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
