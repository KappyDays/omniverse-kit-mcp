"""503 + *_stack_unavailable → CAPABILITY_NOT_SUPPORTED error_code.

Isolates the client-layer mapping from Extension HTTP response to the
typed error returned by module methods. Used when USD Composer profile
serves a request for an Isaac-only route.
"""

from __future__ import annotations

import httpx
import pytest

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.config import IsaacSimConfig
from omniverse_kit_mcp.exceptions import CapabilityNotSupportedError, RemoteServiceError


@pytest.mark.asyncio
async def test_503_robot_stack_unavailable_maps_to_capability_error():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            503,
            json={"detail": {
                "error": "robot_stack_unavailable",
                "message": "Robot operations require isaacsim.robot.manipulators",
                "required_extensions": ["isaacsim.robot.manipulators", "isaacsim.core.nodes"],
            }},
        )
    )
    cfg = IsaacSimConfig(base_url="http://localhost:8014")
    client = IsaacRestClient(cfg)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="http://localhost:8014",
        transport=transport,
    )

    with pytest.raises(CapabilityNotSupportedError) as exc_info:
        await client.robot_load({"prim_path": "/World/Robot", "usd_url": "x"})

    assert exc_info.value.capability == "robot_stack_unavailable"
    assert "isaacsim.robot.manipulators" in exc_info.value.required_extensions

    await client._client.aclose()


@pytest.mark.asyncio
async def test_non_stack_503_falls_back_to_remote_service_error():
    """503 without *_stack_unavailable is treated as generic transient error,
    not CapabilityNotSupportedError."""
    transport = httpx.MockTransport(
        lambda req: httpx.Response(503, json={"detail": "Service temporarily unavailable"})
    )
    cfg = IsaacSimConfig(base_url="http://localhost:8014", max_retries=1)
    client = IsaacRestClient(cfg)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="http://localhost:8014",
        transport=transport,
    )

    with pytest.raises(RemoteServiceError) as exc_info:
        await client.robot_load({"prim_path": "/World/Robot", "usd_url": "x"})
    assert not isinstance(exc_info.value, CapabilityNotSupportedError)

    await client._client.aclose()


@pytest.mark.asyncio
async def test_robot_module_returns_capability_not_supported_error_code():
    from unittest.mock import AsyncMock, MagicMock
    from omniverse_kit_mcp.modules.robot_module import RobotModule
    from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
    from omniverse_kit_mcp.types.robot import RobotLoadRequest

    mock_client = MagicMock()
    mock_client.robot_load = AsyncMock(side_effect=CapabilityNotSupportedError({
        "error": "robot_stack_unavailable",
        "message": "nope",
        "required_extensions": ["isaacsim.robot.manipulators"],
    }))

    module = RobotModule(mock_client)
    meta = OperationMeta(request_id="t1", module=ModuleName.ROBOT, started_at_epoch_ms=1)
    result = await module.load(meta, RobotLoadRequest(prim_path="/World/R", usd_url="x"))

    assert result.ok is False
    assert result.error_code == "CAPABILITY_NOT_SUPPORTED"
    assert result.data is not None
    assert result.data.diagnostics["reason"] == "robot_load_error"
    assert result.data.diagnostics["upstream_error_code"] == "CAPABILITY_NOT_SUPPORTED"
