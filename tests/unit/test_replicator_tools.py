"""Unit tests for replicator_* MCP tools (Phase H)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.replicator import (
    ReplicatorCreateWriterRequest,
    ReplicatorCreateWriterResult,
    ReplicatorRegisterRandomizerRequest,
    ReplicatorRegisterRandomizerResult,
    ReplicatorTriggerOnceRequest,
    ReplicatorTriggerOnceResult,
    ReplicatorTriggerOnTimeRequest,
    ReplicatorTriggerOnTimeResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.REPLICATOR, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_replicator_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "replicator_create_writer" in names
    assert "replicator_register_randomizer" in names
    assert "replicator_trigger_once" in names
    assert "replicator_trigger_on_time" in names


@pytest.mark.asyncio
async def test_create_writer_reports_channels():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ReplicatorModule(client)
    result = await module.create_writer(
        _meta(),
        ReplicatorCreateWriterRequest(
            writer_type="BasicWriter",
            output_dir="C:/tmp/sdg_out",
            rgb=True,
            depth=True,
            semantic_segmentation=False,
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ReplicatorCreateWriterResult)
    assert result.data.writer_type == "BasicWriter"
    assert result.data.output_dir == "C:/tmp/sdg_out"
    assert result.data.channels["rgb"] is True
    assert result.data.channels["depth"] is True


@pytest.mark.asyncio
async def test_register_randomizer_position():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ReplicatorModule(client)
    result = await module.register_randomizer(
        _meta(),
        ReplicatorRegisterRandomizerRequest(
            type="position",
            target="/World/Boxes/*",
            config={"volume": [[-1, -1, 0], [1, 1, 0]]},
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ReplicatorRegisterRandomizerResult)
    assert result.data.type == "position"
    assert result.data.target == "/World/Boxes/*"
    assert result.data.randomizer_id


@pytest.mark.asyncio
async def test_trigger_once_runs_frames():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ReplicatorModule(client)
    result = await module.trigger_once(
        _meta(),
        ReplicatorTriggerOnceRequest(num_frames=5),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ReplicatorTriggerOnceResult)
    assert result.data.num_frames == 5
    assert result.data.frames_ran == 5


@pytest.mark.asyncio
async def test_trigger_on_time_reports_interval():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = ReplicatorModule(client)
    result = await module.trigger_on_time(
        _meta(),
        ReplicatorTriggerOnTimeRequest(interval_s=0.25),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, ReplicatorTriggerOnTimeResult)
    assert result.data.interval_s == 0.25
    assert result.data.trigger_id


def test_action_registry_phase_h_replicator_builders():
    req = build_request(
        ModuleName.REPLICATOR, "create_writer",
        {"writer_type": "BasicWriter", "output_dir": "C:/tmp/sdg"},
    )
    assert isinstance(req, ReplicatorCreateWriterRequest)

    req2 = build_request(
        ModuleName.REPLICATOR, "register_randomizer",
        {"type": "rotation", "target": "/W/*", "config": {}},
    )
    assert isinstance(req2, ReplicatorRegisterRandomizerRequest)

    req3 = build_request(
        ModuleName.REPLICATOR, "trigger_once", {"num_frames": 10},
    )
    assert isinstance(req3, ReplicatorTriggerOnceRequest)

    req4 = build_request(
        ModuleName.REPLICATOR, "trigger_on_time", {"interval_s": 1.0},
    )
    assert isinstance(req4, ReplicatorTriggerOnTimeRequest)


def test_action_registry_replicator_errors():
    with pytest.raises(ValueError, match="writer_type"):
        build_request(
            ModuleName.REPLICATOR, "create_writer",
            {"writer_type": "Unknown", "output_dir": "x"},
        )
    with pytest.raises(ValueError, match="output_dir"):
        build_request(
            ModuleName.REPLICATOR, "create_writer",
            {"writer_type": "BasicWriter"},
        )
    with pytest.raises(ValueError, match="type"):
        build_request(
            ModuleName.REPLICATOR, "register_randomizer",
            {"type": "mass", "target": "/W"},
        )
    with pytest.raises(ValueError, match="num_frames"):
        build_request(
            ModuleName.REPLICATOR, "trigger_once", {"num_frames": 0},
        )
    with pytest.raises(ValueError, match="interval_s"):
        build_request(
            ModuleName.REPLICATOR, "trigger_on_time", {"interval_s": 0},
        )
