"""Unit tests for robot_navigate_path / robot_gripper_control / robot_set_ee_target (Phase G)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.scenario.action_registry import build_request
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.robot import (
    RobotEEPose,
    RobotFrankaPickPlaceRequest,
    RobotGripperControlRequest,
    RobotGripperControlResult,
    RobotNavigatePathRequest,
    RobotNavigatePathResult,
    RobotSetEETargetRequest,
    RobotSetEETargetResult,
)
from omni.mycompany.validation_api.services.robot_service import (
    _build_franka_pick_place_diagnostics,
    _ensure_initialized,
    _resolve_official_franka_pick_place_classes,
    _resolve_franka_pick_place_hover_height,
    _resolve_lula_config,
)
from omni.mycompany.validation_api.models.robot import RobotFrankaPickPlaceRequestModel


def _meta() -> OperationMeta:
    return OperationMeta(request_id="t", module=ModuleName.ROBOT, started_at_epoch_ms=0)


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_robot_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "robot_navigate_path" in names
    assert "robot_gripper_control" in names
    assert "robot_set_ee_target" in names
    assert "robot_get_ee_pose" in names
    assert "robot_run_franka_pick_place" in names


@pytest.mark.asyncio
async def test_navigate_path_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotNavigatePathRequest(
        prim_path="/World/Robot",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 1.0, 0.0)),
        duration_s=6.0,
    )
    result = await module.navigate_path(_meta(), request)
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, RobotNavigatePathResult)
    assert result.data.job_id.startswith("job_test_path")
    assert result.data.num_waypoints == 3
    assert result.data.duration_s == pytest.approx(6.0)
    # Client received the correctly-serialised points list
    call_name, call_args = client.calls[-1]
    assert call_name == "robot_navigate_path"
    assert call_args["points"] == [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 1.0, 0.0]]


@pytest.mark.asyncio
async def test_gripper_control_open_close_set():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    r_open = await module.gripper_control(
        _meta(), RobotGripperControlRequest(prim_path="/W/F", action="open"),
    )
    assert r_open.status is ExecutionStatus.PASSED
    assert isinstance(r_open.data, RobotGripperControlResult)
    assert r_open.data.action == "open"
    assert r_open.data.target_value == pytest.approx(0.04)
    assert "panda_finger_joint1" in r_open.data.gripper_joint_names

    r_close = await module.gripper_control(
        _meta(), RobotGripperControlRequest(prim_path="/W/F", action="close"),
    )
    assert r_close.data.target_value == pytest.approx(0.0)

    r_set = await module.gripper_control(
        _meta(), RobotGripperControlRequest(prim_path="/W/F", action="set", target=0.025),
    )
    assert r_set.data.action == "set"
    assert r_set.data.target_value == pytest.approx(0.025)


@pytest.mark.asyncio
async def test_set_ee_target_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    result = await module.set_ee_target(
        _meta(),
        RobotSetEETargetRequest(
            prim_path="/World/Franka",
            target_pose=(0.5, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0),
        ),
    )
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, RobotSetEETargetResult)
    assert result.data.ik_success is True
    assert len(result.data.solution) == 7


def test_resolve_lula_config_prefers_isaac_sim_51_loader_api():
    class Loader51:
        def __init__(self) -> None:
            self.calls: list[tuple[str, tuple[str, ...]]] = []

        def load_supported_motion_policy_config(self, robot_description, policy):
            self.calls.append(("motion_policy", (robot_description, policy)))
            return {
                "robot_description_path": "/configs/fr3/rmpflow.yaml",
                "urdf_path": "/configs/fr3/fr3.urdf",
                "end_effector_frame_name": "fr3_hand_tcp",
            }

    loader = Loader51()

    cfg = _resolve_lula_config(loader, "FR3")

    assert loader.calls == [("motion_policy", ("FR3", "RMPflow"))]
    assert cfg["robot_description_path"] == "/configs/fr3/rmpflow.yaml"
    assert cfg["urdf_path"] == "/configs/fr3/fr3.urdf"
    assert cfg["end_effector_frame_name"] == "fr3_hand_tcp"


def test_ensure_initialized_surfaces_not_ready_articulation():
    class NotReadyArticulation:
        prim_path = "/World/Franka"

        def initialize(self) -> None:
            raise AttributeError("'NoneType' object has no attribute 'link_names'")

    with pytest.raises(ValueError, match="articulation.*not ready"):
        _ensure_initialized(NotReadyArticulation())


@pytest.mark.asyncio
async def test_get_ee_pose_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    result = await module.get_ee_pose(_meta(), "/World/Franka", "panda_hand")
    assert result.status is ExecutionStatus.PASSED
    assert isinstance(result.data, RobotEEPose)
    assert result.data.prim_path == "/World/Franka"
    assert result.data.end_effector_frame == "panda_hand"
    assert result.data.position == pytest.approx((0.5, 0.0, 0.4))
    assert result.data.orientation == pytest.approx((1.0, 0.0, 0.0, 0.0))


def test_action_registry_phase_g_robot_builders():
    # navigate_path
    req = build_request(
        ModuleName.ROBOT,
        "navigate_path",
        {"prim_path": "/World/R", "waypoints": [[0, 0, 0], [1, 0, 0]]},
    )
    assert isinstance(req, RobotNavigatePathRequest)
    assert req.duration_s == 5.0
    # gripper_control
    req2 = build_request(
        ModuleName.ROBOT,
        "gripper_control",
        {"prim_path": "/World/R", "action": "open"},
    )
    assert isinstance(req2, RobotGripperControlRequest)
    # set_ee_target
    req3 = build_request(
        ModuleName.ROBOT,
        "set_ee_target",
        {
            "prim_path": "/World/R",
            "target_pose": [0.5, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0],
        },
    )
    assert isinstance(req3, RobotSetEETargetRequest)
    assert req3.robot_description == "Franka"

    req4 = build_request(
        ModuleName.ROBOT,
        "run_franka_pick_place",
        {
            "robot_prim_path": "/World/Franka",
            "object_prim_path": "/World/Cube",
            "target_position": [0.45, -0.35, 0.72],
        },
    )
    assert isinstance(req4, RobotFrankaPickPlaceRequest)
    assert req4.max_steps == 1800
    assert req4.position_tolerance == 0.05


def test_action_registry_robot_errors():
    with pytest.raises(ValueError, match="waypoints"):
        build_request(ModuleName.ROBOT, "navigate_path", {"prim_path": "/x", "waypoints": []})
    with pytest.raises(ValueError, match="open|close|set"):
        build_request(ModuleName.ROBOT, "gripper_control", {"prim_path": "/x", "action": "wiggle"})
    with pytest.raises(ValueError, match="requires target"):
        build_request(ModuleName.ROBOT, "gripper_control", {"prim_path": "/x", "action": "set"})
    with pytest.raises(ValueError, match="qw,qx,qy,qz"):
        build_request(
            ModuleName.ROBOT, "set_ee_target",
            {"prim_path": "/x", "target_pose": [0, 0, 0]},
        )
    with pytest.raises(ValueError, match="target_position"):
        build_request(
            ModuleName.ROBOT,
            "run_franka_pick_place",
            {
                "robot_prim_path": "/World/Franka",
                "object_prim_path": "/World/Cube",
                "target_position": [0, 0],
            },
        )


def test_franka_pick_place_request_model_defaults_are_official_controller_safe():
    model = RobotFrankaPickPlaceRequestModel(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/Cube",
        target_position=[0.45, -0.35, 0.72],
    )

    assert model.robot_description == "Franka"
    assert model.max_steps == 1800
    assert model.position_tolerance == pytest.approx(0.05)
    assert model.lift_height_tolerance == pytest.approx(0.03)
    assert model.events_dt is None


def test_franka_pick_place_request_model_accepts_explicit_grasp_pose():
    model = RobotFrankaPickPlaceRequestModel(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/Cube",
        target_position=[0.45, -0.35, 0.72],
        picking_position=[0.3, 0.2, 0.51],
        end_effector_orientation=[0.0, 0.0, 1.0, 0.0],
    )

    assert model.picking_position == [0.3, 0.2, 0.51]
    assert model.end_effector_orientation == [0.0, 0.0, 1.0, 0.0]


def test_franka_pick_place_diagnostics_reference_official_block_geometry():
    diagnostics = _build_franka_pick_place_diagnostics(
        bbox_size=[0.163, 0.029, 0.013],
        picking_position_source="bbox_center",
    )

    assert diagnostics["official_reference"] == "Isaac Sim Franka Cortex Block Stacking"
    assert diagnostics["official_block_size_m"] == pytest.approx(0.0515)
    assert any("flatter" in warning for warning in diagnostics["warnings"])
    assert any("picking_position" in hint for hint in diagnostics["hints"])


def test_franka_pick_place_hover_height_is_absolute_world_z_for_tables():
    assert _resolve_franka_pick_place_hover_height(
        explicit_height=None,
        picking_z=0.46875,
        target_z=0.46875,
    ) == pytest.approx(0.71875)
    assert _resolve_franka_pick_place_hover_height(
        explicit_height=None,
        picking_z=0.02575,
        target_z=0.02575,
    ) == pytest.approx(0.3)
    assert _resolve_franka_pick_place_hover_height(
        explicit_height=0.8,
        picking_z=0.46875,
        target_z=0.46875,
    ) == pytest.approx(0.8)


def test_official_pick_place_classes_resolve_from_isaac_sim_namespace(monkeypatch):
    class FakePickPlaceController:
        pass

    class FakeParallelGripper:
        pass

    class FakeSingleArticulation:
        pass

    class FakeModule:
        PickPlaceController = FakePickPlaceController
        ParallelGripper = FakeParallelGripper
        SingleArticulation = FakeSingleArticulation

    def fake_import(name):
        if name == "isaacsim.robot.manipulators.examples.franka.controllers.pick_place_controller":
            return FakeModule
        if name == "isaacsim.robot.manipulators.grippers.parallel_gripper":
            return FakeModule
        if name == "isaacsim.core.prims":
            return FakeModule
        raise ImportError(name)

    monkeypatch.setattr("importlib.import_module", fake_import)

    classes = _resolve_official_franka_pick_place_classes()

    assert classes.pick_place_controller is FakePickPlaceController
    assert classes.parallel_gripper is FakeParallelGripper
    assert classes.single_articulation is FakeSingleArticulation
