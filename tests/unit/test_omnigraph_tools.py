"""Unit tests for omnigraph_* MCP tools (Phase H)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.omnigraph import (
    OmnigraphConnectRequest,
    OmnigraphConnectResult,
    OmnigraphCreateNodeRequest,
    OmnigraphCreateNodeResult,
    OmnigraphCreateRos2PublisherRequest,
    OmnigraphCreateRos2PublisherResult,
    OmnigraphCreateScriptControllerRequest,
    OmnigraphCreateScriptControllerResult,
    OmnigraphExecuteRequest,
    OmnigraphExecuteResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="t", module=ModuleName.OMNIGRAPH, started_at_epoch_ms=0,
    )


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_omnigraph_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "omnigraph_create_node" in names
    assert "omnigraph_connect" in names
    assert "omnigraph_execute" in names
    assert "omnigraph_create_ros2_publisher" in names
    assert "omnigraph_create_script_controller" in names


@pytest.mark.asyncio
async def test_create_node_returns_path():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = OmnigraphModule(client)
    result = await module.create_node(
        _meta(),
        OmnigraphCreateNodeRequest(
            graph_path="/ActionGraph",
            node_type="omni.graph.action.OnTick",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, OmnigraphCreateNodeResult)
    assert result.data.graph_path == "/ActionGraph"
    assert result.data.node_name == "OnTick"
    assert result.data.node_path.endswith("/OnTick")


@pytest.mark.asyncio
async def test_connect_returns_edge_echo():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = OmnigraphModule(client)
    result = await module.connect(
        _meta(),
        OmnigraphConnectRequest(
            src_attr="/ActionGraph/OnTick.outputs:tick",
            dst_attr="/ActionGraph/Pub.inputs:execIn",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, OmnigraphConnectResult)
    assert "OnTick.outputs:tick" in result.data.src_attr
    assert "Pub.inputs:execIn" in result.data.dst_attr


@pytest.mark.asyncio
async def test_execute_reports_evaluated_flag():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = OmnigraphModule(client)
    result = await module.execute(
        _meta(),
        OmnigraphExecuteRequest(graph_path="/ActionGraph"),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, OmnigraphExecuteResult)
    assert result.data.evaluated is True


@pytest.mark.asyncio
async def test_create_ros2_publisher_reports_ros2_available():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = OmnigraphModule(client)
    result = await module.create_ros2_publisher(
        _meta(),
        OmnigraphCreateRos2PublisherRequest(
            graph_path="/ActionGraph",
            topic="/camera/image_raw",
            source_prim="/World/Camera",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, OmnigraphCreateRos2PublisherResult)
    assert result.data.topic == "/camera/image_raw"
    assert len(result.data.nodes_created) >= 1
    assert result.data.ros2_available in (True, False)


@pytest.mark.asyncio
async def test_create_script_controller_wires_tick_to_script_node():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = OmnigraphModule(client)
    result = await module.create_script_controller(
        _meta(),
        OmnigraphCreateScriptControllerRequest(
            graph_path="/World/ActionGraph",
            script_path="C:/tmp/franka_pick_place_controller.py",
            node_name="PickPlaceController",
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, OmnigraphCreateScriptControllerResult)
    assert result.data.node_path == "/World/ActionGraph/PickPlaceController"
    assert result.data.tick_node_path == "/World/ActionGraph/OnPlaybackTick"
    assert result.data.edges_created[0].dst.endswith("PickPlaceController.inputs:execIn")
    assert result.data.reset_state is True


def test_action_registry_phase_h_omnigraph_builders():
    req = build_request(
        ModuleName.OMNIGRAPH, "create_node",
        {"graph_path": "/G", "node_type": "omni.graph.nodes.ConstantFloat"},
    )
    assert isinstance(req, OmnigraphCreateNodeRequest)

    req2 = build_request(
        ModuleName.OMNIGRAPH, "connect",
        {"src_attr": "/G/A.outputs:x", "dst_attr": "/G/B.inputs:y"},
    )
    assert isinstance(req2, OmnigraphConnectRequest)

    req3 = build_request(ModuleName.OMNIGRAPH, "execute", {"graph_path": "/G"})
    assert isinstance(req3, OmnigraphExecuteRequest)

    req4 = build_request(
        ModuleName.OMNIGRAPH, "create_ros2_publisher",
        {"graph_path": "/G", "topic": "/t", "source_prim": "/W/C"},
    )
    assert isinstance(req4, OmnigraphCreateRos2PublisherRequest)


def test_action_registry_omnigraph_errors():
    with pytest.raises(ValueError, match="graph_path and node_type"):
        build_request(
            ModuleName.OMNIGRAPH, "create_node",
            {"graph_path": "/G"},
        )
    with pytest.raises(ValueError, match="src_attr and dst_attr"):
        build_request(ModuleName.OMNIGRAPH, "connect", {"src_attr": "/G/A.x"})
    with pytest.raises(ValueError, match="graph_path"):
        build_request(ModuleName.OMNIGRAPH, "execute", {})
    with pytest.raises(ValueError, match="source_prim"):
        build_request(
            ModuleName.OMNIGRAPH, "create_ros2_publisher",
            {"graph_path": "/G", "topic": "/t"},
        )
