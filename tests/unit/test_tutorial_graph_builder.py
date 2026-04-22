"""Tests for WASD Action Graph builder."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def graph_builder_with_mocked_og():
    """Set up mocked omni.graph.core.Controller and import graph_builder."""
    # Get the already-stubbed omni.graph.core module from conftest
    og_mod = sys.modules.get("omni.graph.core")
    if og_mod is None:
        raise RuntimeError("omni.graph.core not stubbed by conftest")

    # Create mock Controller
    controller = MagicMock()
    controller.edit = MagicMock(return_value=(MagicMock(), [], [], []))
    keys = types.SimpleNamespace(
        CREATE_NODES="create_nodes",
        SET_VALUES="set_values",
        CONNECT="connect",
    )
    controller.Keys = keys

    # Attach to the stubbed module
    og_mod.Controller = controller

    # Delete cached graph_builder imports to force fresh import
    keys_to_delete = [k for k in sys.modules.keys() if "graph_builder" in k.lower()]
    for key in keys_to_delete:
        del sys.modules[key]

    # Return the controller so tests can verify it was called
    return controller


def test_build_wasd_graph_returns_path(graph_builder_with_mocked_og):
    # Import AFTER fixture sets up mock
    from omni.mycompany.isaac_tutorial.bindings.graph_builder import (
        build_wasd_graph,
    )

    path = build_wasd_graph(
        graph_path="/World/nova_carter/WASDGraph",
        robot_prim="/World/nova_carter",
    )
    assert path == "/World/nova_carter/WASDGraph"


def test_build_wasd_graph_creates_required_nodes(graph_builder_with_mocked_og):
    # Import AFTER fixture sets up mock
    from omni.mycompany.isaac_tutorial.bindings.graph_builder import (
        build_wasd_graph,
    )

    build_wasd_graph(
        graph_path="/World/nova_carter/WASDGraph",
        robot_prim="/World/nova_carter",
    )

    assert graph_builder_with_mocked_og.edit.called
    call = graph_builder_with_mocked_og.edit.call_args
    # payload dict keyed by CREATE_NODES/SET_VALUES/CONNECT strings
    payload = call.args[1]
    create_nodes = payload["create_nodes"]
    node_types = [t for _, t in create_nodes]

    # OnTick(1) + Key(5) + Write(5) + Read(2) + DiffCtrl(1) + ArtCtrl(1) = 15 nodes
    assert len(create_nodes) == 15
    # Check specific node types are created
    assert "omni.graph.action.OnPlaybackTick" in node_types
    assert "omni.graph.action.OnKeyboardInput" in node_types
    assert "omni.graph.core.WriteVariable" in node_types
    assert "omni.graph.core.ReadVariable" in node_types
    assert "isaacsim.wheeled_robots.DifferentialController" in node_types
    assert "isaacsim.core.nodes.IsaacArticulationController" in node_types


def test_build_wasd_graph_space_is_brake(graph_builder_with_mocked_og):
    # Import AFTER fixture sets up mock
    from omni.mycompany.isaac_tutorial.bindings.graph_builder import (
        build_wasd_graph,
    )

    build_wasd_graph(
        graph_path="/World/nova_carter/WASDGraph",
        robot_prim="/World/nova_carter",
    )

    call = graph_builder_with_mocked_og.edit.call_args
    payload = call.args[1]
    set_values = payload["set_values"]

    # SPACE key maps to [0.0, 0.0] (emergency brake)
    space_value = None
    for key, val in set_values:
        if key == "Write_SPACE.inputs:value":
            space_value = val
    assert space_value == [0.0, 0.0]
