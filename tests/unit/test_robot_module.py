"""Unit tests for RobotModule — load / joint positions / navigate (Phase B)."""

from __future__ import annotations

import asyncio

import pytest

import omniverse_kit_mcp.modules.robot_module as robot_module
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.types.common import (
    ExecutionStatus,
    ModuleName,
    ModuleResult,
    OperationMeta,
)
from omniverse_kit_mcp.types.robot import (
    JointConfig,
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
    RobotArmProfileProbeRequest,
    RobotArmProfilesProbeRequest,
    RobotArmProfileProbeResult,
    RobotArmProfilesProbeResult,
    RobotArmProfilesResult,
    RobotDrivePhysicsRequest,
    RobotDrivePhysicsResult,
    RobotFrankaPickPlaceRequest,
    RobotFrankaPickPlaceResult,
    RobotFrankaPickPlaceDemoRequest,
    RobotFrankaPickPlaceDemoStatus,
    RobotGripperControlRequest,
    RobotGripperControlResult,
    RobotLoadRequest,
    RobotLoadResult,
    RobotEEPose,
    RobotNavigatePathRequest,
    RobotNavigatePathResult,
    RobotNavigateRequest,
    RobotNavigateResult,
    RobotPickPlaceDemoRequest,
    RobotSetEETargetRequest,
    RobotSetEETargetResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.ROBOT, started_at_epoch_ms=0)


def test_robot_probe_arm_profile_request_defaults_to_bounded_timeout():
    request = RobotArmProfileProbeRequest(profile_name="franka_panda")

    assert request.timeout_s == pytest.approx(90.0)


@pytest.mark.asyncio
async def test_robot_list_arm_profiles_returns_curated_support_matrix():
    from tests.conftest import MockIsaacRestClient

    module = RobotModule(MockIsaacRestClient())

    result = await module.list_arm_profiles(_meta())

    assert result.ok
    assert isinstance(result.data, RobotArmProfilesResult)
    assert result.data.count == 41
    assert "franka_panda" not in result.data.validated_pick_place_profiles
    assert "franka_fr3" in result.data.validated_pick_place_profiles
    assert "franka_panda" in result.data.candidate_pick_place_profiles
    assert "ur10" in result.data.candidate_pick_place_profiles
    assert "kawasaki_rs080n" in result.data.candidate_pick_place_profiles
    assert "ur20" in result.data.profile_only_profiles
    assert set(result.data.known_dynamic_timeout_profiles) == {
        "dofbot",
        "lite6",
        "lite6_gripper",
        "openarm_bimanual",
        "openarm_unimanual",
        "so101_new_calib",
        "uf850",
        "ur3",
        "ur5",
        "ur20",
        "xarm6",
        "xarm7",
    }
    assert "warmup_step" in result.data.known_dynamic_timeout_profile_reasons["dofbot"]
    assert "dynamic IK-only probe timed out" in (
        result.data.known_dynamic_timeout_profile_reasons["ur3"]
    )
    profiles_by_name = {profile.profile_name: profile for profile in result.data.profiles}
    profile_names = set(profiles_by_name)
    assert set(result.data.known_dynamic_timeout_profiles) <= profile_names
    assert result.data.static_only_probe_recommended_profiles == (
        result.data.known_dynamic_timeout_profiles
    )
    assert set(result.data.dynamic_probe_recommended_profiles).isdisjoint(
        result.data.static_only_probe_recommended_profiles
    )
    assert set(result.data.dynamic_probe_recommended_profiles) | set(
        result.data.static_only_probe_recommended_profiles
    ) == profile_names
    assert set(result.data.recommended_probe_mode_by_profile) == profile_names
    assert set(result.data.recommended_probe_mode_reasons) == profile_names
    assert result.data.recommended_probe_mode_by_profile["ur20"] == (
        "static_only_known_dynamic_timeout"
    )
    assert result.data.recommended_probe_mode_by_profile["ur30"] == (
        "dynamic_with_bounded_timeouts"
    )
    assert "timed out" in result.data.recommended_probe_mode_reasons["ur20"]
    assert "No durable live dynamic-timeout evidence" in (
        result.data.recommended_probe_mode_reasons["ur30"]
    )
    assert "ur30" in result.data.dynamic_probe_recommended_profiles
    assert "ur20" in result.data.static_only_probe_recommended_profiles
    assert result.data.known_pick_place_blocker_profiles == (
        "franka_panda",
        "factory_franka",
    )
    assert "insufficient lift" in (
        result.data.known_pick_place_blocker_profile_reasons["franka_panda"]
    )
    assert "deeper combined-Z offset trial" in (
        result.data.known_pick_place_blocker_profile_reasons["factory_franka"]
    )
    assert set(result.data.known_pick_place_blocker_profiles) <= profile_names
    validated_profiles = set(result.data.validated_pick_place_profiles)
    assert not validated_profiles & set(result.data.known_pick_place_blocker_profiles)
    assert not validated_profiles & set(result.data.known_dynamic_timeout_profiles)
    for profile_name in result.data.known_pick_place_blocker_profiles:
        assert profiles_by_name[profile_name].support_status != "validated_pick_place"
    franka = next(p for p in result.data.profiles if p.profile_name == "franka_panda")
    assert franka.asset_url.endswith("/Robots/FrankaRobotics/FrankaPanda/franka.usd")
    assert franka.max_grasp_width_m == pytest.approx(0.08)
    assert franka.fit_clearance_m == pytest.approx(0.005)
    fr3 = next(p for p in result.data.profiles if p.profile_name == "franka_fr3")
    assert fr3.max_grasp_width_m == pytest.approx(0.08)
    assert fr3.fit_clearance_m == pytest.approx(0.005)
    ur10 = next(p for p in result.data.profiles if p.profile_name == "ur10")
    assert ur10.end_effector_frame_candidates == ("tool0", "ee_link", "wrist_3_link")
    ridgeback_ur5 = next(
        p for p in result.data.profiles if p.profile_name == "ridgeback_ur5"
    )
    assert ridgeback_ur5.end_effector_frame_candidates == (
        "tool0",
        "ee_link",
        "wrist_3_link",
        "ur_arm_tool0",
        "ur_arm_ee_link",
        "ur_arm_wrist_3_link",
    )
    for profile_name in (
        "kawasaki_rs007l",
        "kawasaki_rs007n",
        "kawasaki_rs013n",
        "kawasaki_rs025n",
        "kawasaki_rs080n",
    ):
        kawasaki = next(p for p in result.data.profiles if p.profile_name == profile_name)
        assert kawasaki.end_effector_frame_candidates == (
            "onrobot_rg2_base_link",
            "tool0",
            "ee_link",
            "right_gripper",
        )
    for profile_name in ("cobotta_pro_900", "cobotta_pro_1300"):
        denso = next(p for p in result.data.profiles if p.profile_name == profile_name)
        assert denso.end_effector_frame_candidates == (
            "onrobot_rg6_base_link",
            "J6",
            "joint_6",
        )


@pytest.mark.asyncio
async def test_robot_load_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotLoadRequest(
        usd_url="file:///tmp/franka.usd",
        prim_path="/World/Franka",
        position=(1.0, 2.0, 3.0),
    )
    result = await module.load(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, RobotLoadResult)
    assert result.data.prim_path == "/World/Franka"
    assert result.data.has_articulation is True
    assert result.data.diagnostics == {}
    load_calls = [c for c in client.calls if c[0] == "robot_load"]
    assert len(load_calls) == 1
    assert load_calls[0][1]["position"] == [1.0, 2.0, 3.0]


@pytest.mark.asyncio
async def test_robot_get_joint_positions():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_positions"] = {
        "ok": True,
        "prim_path": "/World/Franka",
        "positions": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
    }
    module = RobotModule(client)
    result = await module.get_joint_positions(_meta(), "/World/Franka")

    assert result.ok
    assert isinstance(result.data, JointPositions)
    assert result.data.positions == (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
    assert result.data.diagnostics == {}


@pytest.mark.asyncio
async def test_robot_get_joint_positions_error_returns_typed_diagnostics():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_get_joint_positions(self, prim_path):  # type: ignore[override]
            raise ValueError("Prim at /X has no PhysX articulation API")

    module = RobotModule(FailingClient())
    result = await module.get_joint_positions(_meta(), "/X")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_GET_JOINTS_ERROR"
    assert isinstance(result.data, JointPositions)
    assert result.data.prim_path == "/X"
    assert result.data.positions == ()
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_get_joint_positions_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_GET_JOINTS_ERROR"
    assert diagnostics["prim_path"] == "/X"
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_get_joint_positions",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_get_joint_config_default_franka():
    """Default mock returns Franka 7-DOF config from dof_properties source."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    result = await module.get_joint_config(_meta(), "/World/Franka")

    assert result.ok
    assert isinstance(result.data, JointConfig)
    assert result.data.dof_count == 7
    assert result.data.source == "dof_properties"
    assert result.data.diagnostics == {}
    assert len(result.data.stiffness) == 7
    assert result.data.stiffness[0] == 400.0
    assert result.data.upper_limits[5] == 3.7
    cfg_calls = [c for c in client.calls if c[0] == "robot_get_joint_config"]
    assert len(cfg_calls) == 1
    assert cfg_calls[0][1]["prim_path"] == "/World/Franka"


@pytest.mark.asyncio
async def test_robot_get_joint_config_usd_fallback_source():
    """Custom mock simulates UsdPhysics.DriveAPI fallback path."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_config"] = {
        "ok": True,
        "prim_path": "/World/UR10",
        "source": "usd_drive_api",
        "dof_count": 6,
        "dof_names": [f"j{i}" for i in range(6)],
        "joint_types": ["RevoluteJoint"] * 6,
        "stiffness": [0.0] * 6,
        "damping": [0.0] * 6,
        "max_force": [0.0] * 6,
        "lower_limits": [-3.14] * 6,
        "upper_limits": [3.14] * 6,
        "max_velocity": [0.0] * 6,
    }
    module = RobotModule(client)
    result = await module.get_joint_config(_meta(), "/World/UR10")

    assert result.ok
    assert result.data.source == "usd_drive_api"
    assert result.data.dof_count == 6
    assert result.data.diagnostics == {}
    assert all(v == 0.0 for v in result.data.stiffness)


@pytest.mark.asyncio
async def test_robot_get_joint_config_static_marks_diagnostic_order():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    result = await module.get_joint_config_static(_meta(), "/World/Franka")

    assert result.ok
    assert result.data.source == "usd_joint_prims_static"
    assert result.data.static_only is True
    assert result.data.order_reliable is False
    assert result.data.dof_count == 7
    assert result.data.diagnostics == {}
    cfg_calls = [c for c in client.calls if c[0] == "robot_get_joint_config_static"]
    assert len(cfg_calls) == 1
    assert cfg_calls[0][1]["prim_path"] == "/World/Franka"


@pytest.mark.asyncio
async def test_robot_get_joint_config_static_coerces_missing_numeric_attrs():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_config_static"] = {
        "ok": True,
        "prim_path": "/World/Sparse",
        "source": "usd_joint_prims_static",
        "static_only": True,
        "order_reliable": False,
        "dof_count": 2,
        "dof_names": ["joint_a", "joint_b"],
        "joint_types": ["PhysicsRevoluteJoint", "PhysicsPrismaticJoint"],
        "stiffness": [None, 10.0],
        "damping": [None, "bad-value"],
        "max_force": [1.0, None],
        "lower_limits": [None, -1.0],
        "upper_limits": [1.0, None],
        "max_velocity": [None, 2.0],
    }
    module = RobotModule(client)

    result = await module.get_joint_config_static(_meta(), "/World/Sparse")

    assert result.ok
    assert result.data.stiffness == (0.0, 10.0)
    assert result.data.damping == (0.0, 0.0)
    assert result.data.max_force == (1.0, 0.0)
    assert result.data.lower_limits == (0.0, -1.0)
    assert result.data.upper_limits == (1.0, 0.0)
    assert result.data.max_velocity == (0.0, 2.0)


@pytest.mark.asyncio
async def test_robot_get_joint_config_propagates_400():
    """Extension raises ValueError when prim has no articulation → wrapped error."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_get_joint_config(self, prim_path):  # type: ignore[override]
            raise ValueError("Prim at /X has no PhysX articulation API")

    module = RobotModule(FailingClient())
    result = await module.get_joint_config(_meta(), "/X")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_GET_JOINT_CONFIG_ERROR"
    assert "articulation" in (result.message or "").lower()
    assert isinstance(result.data, JointConfig)
    assert result.data.prim_path == "/X"
    assert result.data.dof_count == 0
    assert result.data.order_reliable is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_get_joint_config_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_GET_JOINT_CONFIG_ERROR"
    assert diagnostics["prim_path"] == "/X"
    assert diagnostics["static"] is False
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_get_joint_config",
        "extension_capture_logs",
    ]
    assert any("dynamic readback fails" in item for item in diagnostics["suggested_next"])


@pytest.mark.asyncio
async def test_robot_get_joint_config_static_error_returns_typed_diagnostics():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_get_joint_config_static(self, prim_path):  # type: ignore[override]
            raise ValueError("No joints discovered under /X")

    module = RobotModule(FailingClient())
    result = await module.get_joint_config_static(_meta(), "/X")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_GET_STATIC_JOINT_CONFIG_ERROR"
    assert isinstance(result.data, JointConfig)
    assert result.data.prim_path == "/X"
    assert result.data.static_only is True
    assert result.data.order_reliable is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_get_static_joint_config_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_GET_STATIC_JOINT_CONFIG_ERROR"
    assert diagnostics["prim_path"] == "/X"
    assert diagnostics["static"] is True
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "extension_capture_logs",
    ]
    assert any("USD joint prims" in item for item in diagnostics["suggested_next"])
    assert not any(
        "dynamic readback fails" in item for item in diagnostics["suggested_next"]
    )


@pytest.mark.asyncio
async def test_robot_set_joint_positions():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    positions = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    request = JointPositionsSetRequest(
        prim_path="/World/Franka",
        positions=tuple(positions),
    )
    result = await module.set_joint_positions(_meta(), request)

    assert result.ok
    assert isinstance(result.data, JointPositionsSetResult)
    assert result.data.positions_count == 7
    assert result.data.diagnostics == {}
    set_calls = [c for c in client.calls if c[0] == "robot_set_joint_positions"]
    assert len(set_calls) == 1
    assert set_calls[0][1]["positions"] == positions


@pytest.mark.asyncio
async def test_robot_set_joint_positions_surfaces_http_400():
    """Extension raises ValueError on missing articulation → HTTP 400 →
    RemoteServiceError propagates as ROBOT_SET_JOINTS_ERROR."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_set_joint_positions(self, request):  # type: ignore[override]
            raise ValueError("Prim at /X has no PhysX articulation API")

    module = RobotModule(FailingClient())
    request = JointPositionsSetRequest(prim_path="/X", positions=(0.0,))
    result = await module.set_joint_positions(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_SET_JOINTS_ERROR"
    assert "articulation" in (result.message or "").lower()
    assert isinstance(result.data, JointPositionsSetResult)
    assert result.data.prim_path == "/X"
    assert result.data.positions_count == 1
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_set_joint_positions_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_SET_JOINTS_ERROR"
    assert diagnostics["prim_path"] == "/X"
    assert diagnostics["positions_count"] == 1
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_set_joint_positions",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_navigate_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotNavigateRequest(
        prim_path="/World/Franka",
        target=(5.0, 0.0, 0.0),
        duration_s=2.0,
    )
    result = await module.navigate_to(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotNavigateResult)
    assert result.data.job_id == "job_test_0001"
    assert result.data.diagnostics == {}
    nav_calls = [c for c in client.calls if c[0] == "robot_navigate"]
    assert nav_calls[0][1]["duration_s"] == 2.0


@pytest.mark.asyncio
async def test_robot_navigate_to_error_returns_typed_diagnostics():
    class FailingClient:
        async def robot_navigate(self, request):
            raise RuntimeError("timeline is not playing")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotNavigateRequest(
        prim_path="/World/Robot",
        target=(1.0, 2.0, 3.0),
        duration_s=2.5,
    )
    result = await module.navigate_to(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_NAVIGATE_ERROR"
    assert isinstance(result.data, RobotNavigateResult)
    assert result.data.job_id == ""
    assert result.data.prim_path == "/World/Robot"
    assert result.data.target == (1.0, 2.0, 3.0)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_navigate_to_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_NAVIGATE_ERROR"
    assert diagnostics["upstream_message"] == "timeline is not playing"
    assert diagnostics["target"] == [1.0, 2.0, 3.0]
    assert diagnostics["duration_s"] == 2.5
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_navigate_to",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_navigate_path_error_returns_typed_diagnostics():
    class FailingClient:
        async def robot_navigate_path(self, request):
            raise RuntimeError("path planner unavailable")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotNavigatePathRequest(
        prim_path="/World/Robot",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        duration_s=4.0,
    )
    result = await module.navigate_path(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_NAVIGATE_PATH_ERROR"
    assert isinstance(result.data, RobotNavigatePathResult)
    assert result.data.job_id == ""
    assert result.data.prim_path == "/World/Robot"
    assert result.data.num_waypoints == 2
    assert result.data.duration_s == 4.0
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_navigate_path_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_NAVIGATE_PATH_ERROR"
    assert diagnostics["upstream_message"] == "path planner unavailable"
    assert diagnostics["waypoint_count"] == 2
    assert diagnostics["duration_s"] == 4.0
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_navigate_path",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_load_propagates_error():
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def robot_load(self, request):  # type: ignore[override]
            raise RuntimeError("CreatePayloadCommand failed")

    module = RobotModule(FailingClient())
    request = RobotLoadRequest(usd_url="bogus", prim_path="/World/X")
    result = await module.load(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_LOAD_ERROR"
    assert "CreatePayloadCommand failed" in (result.message or "")
    assert isinstance(result.data, RobotLoadResult)
    assert result.data.ok is False
    assert result.data.prim_path == "/World/X"
    assert result.data.usd_url == "bogus"
    assert result.data.has_articulation is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_load_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_LOAD_ERROR"
    assert diagnostics["upstream_message"] == "CreatePayloadCommand failed"
    assert diagnostics["usd_url"] == "bogus"
    assert diagnostics["prim_path"] == "/World/X"
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "official_asset_search",
        "asset_search",
        "robot_load",
        "extension_capture_logs",
    ]
    assert any("simulation_get_status" in item for item in diagnostics["suggested_next"])


@pytest.mark.asyncio
async def test_robot_gripper_control_error_returns_typed_diagnostics():
    class FailingClient:
        async def robot_gripper_control(self, request):
            raise RuntimeError("No gripper joints found")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotGripperControlRequest(
        prim_path="/World/Robot",
        action="set",
        target=0.2,
    )
    result = await module.gripper_control(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_GRIPPER_CONTROL_ERROR"
    assert isinstance(result.data, RobotGripperControlResult)
    assert result.data.prim_path == "/World/Robot"
    assert result.data.action == "set"
    assert result.data.target_value == pytest.approx(0.2)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_gripper_control_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_GRIPPER_CONTROL_ERROR"
    assert diagnostics["upstream_message"] == "No gripper joints found"
    assert diagnostics["prim_path"] == "/World/Robot"
    assert diagnostics["action"] == "set"
    assert diagnostics["target"] == 0.2
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_gripper_control",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_set_ee_target_error_returns_typed_diagnostics():
    class FailingClient:
        async def robot_set_ee_target(self, request):
            raise RuntimeError("IK failed to initialize")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotSetEETargetRequest(
        prim_path="/World/Robot",
        target_pose=(0.3, 0.1, 0.4, 1.0, 0.0, 0.0, 0.0),
        robot_description="Franka",
        end_effector_frame="panda_hand",
    )
    result = await module.set_ee_target(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_SET_EE_TARGET_ERROR"
    assert isinstance(result.data, RobotSetEETargetResult)
    assert result.data.prim_path == "/World/Robot"
    assert result.data.ik_success is False
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_set_ee_target_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_SET_EE_TARGET_ERROR"
    assert diagnostics["upstream_message"] == "IK failed to initialize"
    assert diagnostics["prim_path"] == "/World/Robot"
    assert diagnostics["target_pose"] == [0.3, 0.1, 0.4, 1.0, 0.0, 0.0, 0.0]
    assert diagnostics["robot_description"] == "Franka"
    assert diagnostics["end_effector_frame"] == "panda_hand"
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_set_ee_target",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_get_ee_pose_error_returns_typed_diagnostics():
    class FailingClient:
        async def robot_get_ee_pose(
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            raise RuntimeError("end-effector frame not found")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    result = await module.get_ee_pose(_meta(), "/World/Robot", "tool0")

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_GET_EE_POSE_ERROR"
    assert isinstance(result.data, RobotEEPose)
    assert result.data.prim_path == "/World/Robot"
    assert result.data.end_effector_frame == "tool0"
    assert result.data.position == (0.0, 0.0, 0.0)
    assert result.data.orientation == (1.0, 0.0, 0.0, 0.0)
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_get_ee_pose_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_GET_EE_POSE_ERROR"
    assert diagnostics["upstream_message"] == "end-effector frame not found"
    assert diagnostics["prim_path"] == "/World/Robot"
    assert diagnostics["end_effector_frame"] == "tool0"
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_get_ee_pose",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_happy_path_safe_nudge():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    prim_path = "/World/MCPProbe/franka_panda"
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 7},
        {"ok": True, "prim_path": prim_path, "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
        ),
    )

    assert result.ok
    assert isinstance(result.data, RobotArmProfileProbeResult)
    assert result.data.overall_ok is True
    assert result.data.mcp_controllability == "dynamic_joint_control"
    assert "safe joint nudge succeeded" in result.data.mcp_controllability_reason
    assert result.data.probe_capability_level == 5
    assert result.data.probe_capability_level_name == "ik_or_ee_telemetry"
    assert "not pick/place validation" in result.data.probe_capability_level_reason
    assert result.data.probe_proves_pick_place is False
    assert result.data.pick_place_validation_status == "known_pick_place_blocker"
    assert "Known pick/place playback blocker" in result.data.pick_place_validation_reason
    assert result.data.recommended_next_status == "candidate_pick_place"
    assert result.data.checks["load"].ok is True
    assert result.data.checks["safe_nudge"].ok is True
    assert result.data.checks["gripper"].ok is True
    assert result.data.checks["ik"].ok is True
    set_calls = [c for c in client.calls if c[0] == "robot_set_joint_positions"]
    assert len(set_calls) == 2
    assert set_calls[0][1]["positions"][0] == pytest.approx(0.01)
    assert set_calls[1][1]["positions"] == [0.0] * 7
    assert ("stage_delete_prim", {"prim_path": prim_path}) in client.calls


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_stops_timeline_before_stage_reset():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    prim_path = "/World/MCPProbe/franka_panda"
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 7},
        {"ok": True, "prim_path": prim_path, "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
        ),
    )

    assert result.ok
    assert result.data.checks["stage_reset_stop"].ok is True
    assert [name for name, _ in client.calls[:2]] == ["simulation_stop", "stage_new"]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_safe_nudge_accepts_partial_progress():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    prim_path = "/World/MCPProbe/franka_panda"
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 7},
        {"ok": True, "prim_path": prim_path, "positions": [0.004, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
        ),
    )

    evidence = result.data.checks["safe_nudge"].evidence
    assert result.ok
    assert result.data.overall_ok is True
    assert result.data.checks["safe_nudge"].ok is True
    assert evidence["readback_ok"] is False
    assert evidence["moved_toward_target"] is True
    assert evidence["progress_ratio"] == pytest.approx(0.4)
    assert evidence["target_error"] == pytest.approx(-0.006)


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_safe_nudge_skips_mobile_base_joint():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    prim_path = "/World/MCPProbe/ridgeback_franka"
    client.responses["robot_get_joint_config"] = {
        "ok": True,
        "prim_path": prim_path,
        "source": "dof_properties",
        "dof_count": 4,
        "dof_names": [
            "dummy_base_prismatic_x_joint",
            "panda_joint1",
            "panda_joint2",
            "panda_finger_joint1",
        ],
        "joint_types": ["PrismaticJoint", "RevoluteJoint", "RevoluteJoint", "PrismaticJoint"],
        "stiffness": [0.0, 400.0, 400.0, 100.0],
        "damping": [0.0, 40.0, 40.0, 10.0],
        "max_force": [0.0, 87.0, 87.0, 20.0],
        "lower_limits": [-1.0, -2.9, -1.8, 0.0],
        "upper_limits": [1.0, 2.9, 1.8, 0.04],
        "max_velocity": [1.0, 2.0, 2.0, 0.2],
    }
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0, 0.0, 0.0, 0.0]},
        {"ok": True, "prim_path": prim_path, "positions": [0.0, 0.01, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="ridgeback_franka",
            prim_path=prim_path,
        ),
    )

    evidence = result.data.checks["safe_nudge"].evidence
    set_calls = [c for c in client.calls if c[0] == "robot_set_joint_positions"]
    assert result.ok
    assert result.data.checks["safe_nudge"].ok is True
    assert evidence["joint_index"] == 1
    assert evidence["joint_name"] == "panda_joint1"
    assert set_calls[0][1]["positions"] == [0.0, 0.01, 0.0, 0.0]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_no_gripper_is_not_overall_failure():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    prim_path = "/World/MCPProbe/ur3"
    client.responses["robot_get_joint_config"] = {
        "ok": True,
        "prim_path": prim_path,
        "source": "dof_properties",
        "dof_count": 6,
        "dof_names": [f"ur_joint{i}" for i in range(6)],
        "joint_types": ["RevoluteJoint"] * 6,
        "stiffness": [100.0] * 6,
        "damping": [10.0] * 6,
        "max_force": [50.0] * 6,
        "lower_limits": [-3.14] * 6,
        "upper_limits": [3.14] * 6,
        "max_velocity": [2.0] * 6,
    }
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 6},
        {"ok": True, "prim_path": prim_path, "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(profile_name="ur3", prim_path=prim_path),
    )

    assert result.ok
    assert result.data.overall_ok is True
    assert result.data.checks["gripper"].skipped is True
    assert result.data.checks["gripper"].ok is True
    assert result.data.mcp_controllability == "dynamic_joint_control"
    assert result.data.probe_capability_level == 5
    assert result.data.probe_capability_level_name == "ik_or_ee_telemetry"
    assert result.data.recommended_next_status == "ik_only"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_uses_profile_ik_frame_for_ee_pose():
    from tests.conftest import MockIsaacRestClient

    class Tool0OnlyClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or [0.0] * 7
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "UR3e"),
                "end_effector_frame": "tool0",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame != "tool0":
                raise ValueError(f"End-effector frame {end_effector_frame} not found")
            return {
                "ok": True,
                "prim_path": prim_path,
                "end_effector_frame": "tool0",
                "position": [0.5, 0.0, 0.4],
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "source": "dynamic_control",
            }

    client = Tool0OnlyClient()
    prim_path = "/World/MCPProbe/ur3e"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="ur3e",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ee_pose = result.data.checks["ee_pose"]
    assert ee_pose.ok is True
    assert ee_pose.skipped is False
    assert ee_pose.evidence["end_effector_frame"] == "tool0"
    assert ee_pose.evidence["requested_frame"] == "tool0"
    assert ee_pose.evidence["attempted_frames"] == ["tool0"]
    ee_pose_calls = [c for c in client.calls if c[0] == "robot_get_ee_pose"]
    assert ee_pose_calls == [
        ("robot_get_ee_pose", {"prim_path": prim_path, "end_effector_frame": "tool0"})
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_ur_tries_live_usd_wrist_frame_candidate():
    from tests.conftest import MockIsaacRestClient

    class URWristFrameClient(MockIsaacRestClient):
        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame == "wrist_3_link":
                return {
                    "ok": True,
                    "prim_path": prim_path,
                    "end_effector_frame": "wrist_3_link",
                    "position": [0.4, 0.0, 0.4],
                    "orientation": [1.0, 0.0, 0.0, 0.0],
                    "source": "usd_world_transform",
                }
            raise ValueError(f"End-effector frame {end_effector_frame!r} not found")

    client = URWristFrameClient()
    prim_path = "/World/MCPProbe/ur3e"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="ur3e",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ee_pose = result.data.checks["ee_pose"]
    assert ee_pose.ok is True
    assert ee_pose.evidence["requested_frame"] == "wrist_3_link"
    assert ee_pose.evidence["end_effector_frame"] == "wrist_3_link"
    assert ee_pose.evidence["attempted_frames"] == [
        "tool0",
        "ee_link",
        "wrist_3_link",
    ]
    assert result.data.mcp_controllability == "dynamic_joint_read_only"
    assert result.data.probe_capability_level == 2
    assert result.data.probe_capability_level_name == "dynamic_joint_read"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_missing_lula_config_is_reported_not_thrown():
    from tests.conftest import MockIsaacRestClient

    class NoIkClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            raise ValueError("No Lula motion policy config for robot_description='UR3'")

    client = NoIkClient()
    prim_path = "/World/MCPProbe/ur3"
    client.responses["robot_get_joint_config"] = {
        "ok": True,
        "prim_path": prim_path,
        "source": "dof_properties",
        "dof_count": 6,
        "dof_names": [f"ur_joint{i}" for i in range(6)],
        "joint_types": ["RevoluteJoint"] * 6,
        "stiffness": [100.0] * 6,
        "damping": [10.0] * 6,
        "max_force": [50.0] * 6,
        "lower_limits": [-3.14] * 6,
        "upper_limits": [3.14] * 6,
        "max_velocity": [2.0] * 6,
    }
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 6},
        {"ok": True, "prim_path": prim_path, "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(profile_name="ur3", prim_path=prim_path),
    )

    assert result.ok
    assert result.data.overall_ok is True
    assert result.data.checks["ik"].ok is False
    assert result.data.checks["ik"].skipped is True
    assert result.data.checks["ik"].error_code == "ROBOT_SET_EE_TARGET_ERROR"
    assert "Lula" in result.data.checks["ik"].message
    assert result.data.mcp_controllability == "dynamic_joint_control"
    assert result.data.recommended_next_status == "profile_only"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_candidate_keeps_candidate_recommendation_when_ik_unsupported():
    from tests.conftest import MockIsaacRestClient

    class NoIkClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            raise ValueError("No Lula motion policy config for robot_description='RS007L'")

    client = NoIkClient()
    prim_path = "/World/MCPProbe/kawasaki_rs007l"
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": prim_path, "positions": [0.0] * 7},
        {"ok": True, "prim_path": prim_path, "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(profile_name="kawasaki_rs007l", prim_path=prim_path),
    )

    assert result.ok
    assert result.data.overall_ok is True
    assert result.data.support_status == "candidate_pick_place"
    assert result.data.checks["ik"].ok is False
    assert result.data.checks["ik"].skipped is True
    assert result.data.mcp_controllability == "dynamic_joint_control"
    assert result.data.recommended_next_status == "candidate_pick_place"
    assert result.data.probe_proves_pick_place is False
    assert result.data.pick_place_validation_status == "not_validated_by_probe"
    assert "Durable live grasp" in result.data.pick_place_validation_reason


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_ik_preserves_non_unsupported_failure():
    from tests.conftest import MockIsaacRestClient

    class IkSolverFailureClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            raise RuntimeError("Lula IK solve raised: synthetic solver failure")

    client = IkSolverFailureClient()
    prim_path = "/World/MCPProbe/franka_panda"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ik = result.data.checks["ik"]
    assert ik.ok is False
    assert ik.skipped is False
    assert ik.error_code == "ROBOT_SET_EE_TARGET_ERROR"
    assert "synthetic solver failure" in ik.message
    assert "unsupported" not in ik.evidence
    assert ik.evidence["attempted_targets"][0]["ok"] is False
    assert result.data.mcp_controllability == "dynamic_joint_read_only"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_kawasaki_tries_relaxed_ik_orientation():
    from tests.conftest import MockIsaacRestClient

    class KawasakiIkTargetClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or []
            if pose == [0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0]:
                raise ValueError("Lula IK did not converge for target pose")
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "RS007L"),
                "end_effector_frame": "gripper_center",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

    client = KawasakiIkTargetClient()
    prim_path = "/World/MCPProbe/kawasaki_rs007l"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="kawasaki_rs007l",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ik = result.data.checks["ik"]
    assert ik.ok is True
    assert ik.skipped is False
    assert ik.evidence["selected_target_label"] == "kawasaki_relaxed_orientation"
    assert ik.evidence["solution_count"] == 6
    assert ik.evidence["attempted_targets"][0]["ok"] is False
    assert ik.evidence["attempted_targets"][0]["label"] == "default"
    assert ik.evidence["attempted_targets"][1]["ok"] is True
    assert ik.evidence["attempted_targets"][1]["label"] == "kawasaki_relaxed_orientation"
    target_calls = [c for c in client.calls if c[0] == "robot_set_ee_target"]
    assert [c[1]["target_pose"] for c in target_calls] == [
        [0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0],
        [0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0],
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_kawasaki_rs080n_tries_forward_ik_target():
    from tests.conftest import MockIsaacRestClient

    class KawasakiRs080nTargetClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or []
            if pose != [0.7, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0]:
                raise ValueError("Lula IK did not converge for target pose")
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "RS080N"),
                "end_effector_frame": "gripper_center",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

    client = KawasakiRs080nTargetClient()
    prim_path = "/World/MCPProbe/kawasaki_rs080n"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="kawasaki_rs080n",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ik = result.data.checks["ik"]
    assert ik.ok is True
    assert ik.skipped is False
    assert ik.evidence["selected_target_label"] == "kawasaki_rs080n_relaxed_forward"
    assert ik.evidence["solution_count"] == 6
    assert [attempt["label"] for attempt in ik.evidence["attempted_targets"]] == [
        "default",
        "kawasaki_relaxed_orientation",
        "kawasaki_rs080n_relaxed_forward",
    ]
    assert [attempt["ok"] for attempt in ik.evidence["attempted_targets"]] == [
        False,
        False,
        True,
    ]
    target_calls = [c for c in client.calls if c[0] == "robot_set_ee_target"]
    assert [c[1]["target_pose"] for c in target_calls] == [
        [0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0],
        [0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0],
        [0.7, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0],
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_kuka_tries_live_proven_forward_ik_target():
    from tests.conftest import MockIsaacRestClient

    class KukaIkTargetClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or []
            if pose != [1.5, 0.0, 1.2, 1.0, 0.0, 0.0, 0.0]:
                raise ValueError("Lula IK did not converge for target pose")
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "Kuka_KR210"),
                "end_effector_frame": "tool0",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

    client = KukaIkTargetClient()
    prim_path = "/World/MCPProbe/kuka_kr210_l150"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="kuka_kr210_l150",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ik = result.data.checks["ik"]
    assert ik.ok is True
    assert ik.skipped is False
    assert ik.evidence["selected_target_label"] == "kuka_forward_high_identity"
    assert ik.evidence["solution_count"] == 6
    assert ik.evidence["attempted_targets"][0]["ok"] is False
    assert ik.evidence["attempted_targets"][0]["label"] == "default"
    assert ik.evidence["attempted_targets"][1]["ok"] is False
    assert ik.evidence["attempted_targets"][1]["label"] == "relaxed_orientation"
    assert ik.evidence["attempted_targets"][2]["ok"] is True
    assert ik.evidence["attempted_targets"][2]["label"] == "kuka_forward_high_identity"
    target_calls = [c for c in client.calls if c[0] == "robot_set_ee_target"]
    assert [c[1]["target_pose"] for c in target_calls] == [
        [0.4, 0.0, 0.4, 1.0, 0.0, 0.0, 0.0],
        [0.4, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0],
        [1.5, 0.0, 1.2, 1.0, 0.0, 0.0, 0.0],
    ]


@pytest.mark.parametrize("profile_name", ("cobotta_pro_900", "cobotta_pro_1300"))
@pytest.mark.asyncio
async def test_robot_probe_arm_profile_denso_uses_live_usd_ee_frame_candidate(
    profile_name: str,
):
    from tests.conftest import MockIsaacRestClient

    class DensoEEPoseClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or []
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "Cobotta_Pro_900"),
                "end_effector_frame": "gripper_center",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame != "onrobot_rg6_base_link":
                raise ValueError(f"End-effector frame {end_effector_frame} not found")
            return {
                "ok": True,
                "prim_path": prim_path,
                "end_effector_frame": "onrobot_rg6_base_link",
                "position": [0.4, 0.0, 0.4],
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "source": "usd_world_transform",
            }

    client = DensoEEPoseClient()
    prim_path = f"/World/MCPProbe/{profile_name}"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name=profile_name,
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ee_pose = result.data.checks["ee_pose"]
    assert ee_pose.ok is True
    assert ee_pose.evidence["requested_frame"] == "onrobot_rg6_base_link"
    assert ee_pose.evidence["end_effector_frame"] == "onrobot_rg6_base_link"
    assert ee_pose.evidence["attempted_frames"] == ["onrobot_rg6_base_link"]
    assert result.data.mcp_controllability == "dynamic_joint_read_only"
    assert result.data.probe_capability_level == 2
    assert result.data.probe_capability_level_name == "dynamic_joint_read"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_kawasaki_uses_live_usd_ee_frame_candidate():
    from tests.conftest import MockIsaacRestClient

    class KawasakiEEPoseClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            pose = request.get("target_pose") or []
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "RS007L"),
                "end_effector_frame": "right_gripper",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0] * 6,
            }

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame != "onrobot_rg2_base_link":
                raise ValueError(f"End-effector frame {end_effector_frame} not found")
            return {
                "ok": True,
                "prim_path": prim_path,
                "end_effector_frame": "onrobot_rg2_base_link",
                "position": [0.4, 0.0, 0.4],
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "source": "usd_world_transform",
            }

    client = KawasakiEEPoseClient()
    prim_path = "/World/MCPProbe/kawasaki_rs007l"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="kawasaki_rs007l",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    ee_pose = result.data.checks["ee_pose"]
    assert ee_pose.ok is True
    assert ee_pose.evidence["requested_frame"] == "onrobot_rg2_base_link"
    assert ee_pose.evidence["end_effector_frame"] == "onrobot_rg2_base_link"
    assert ee_pose.evidence["attempted_frames"] == ["onrobot_rg2_base_link"]
    assert result.data.mcp_controllability == "dynamic_joint_read_only"
    assert result.data.probe_capability_level == 2
    assert result.data.probe_capability_level_name == "dynamic_joint_read"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_marks_unsupported_capabilities_skipped():
    from tests.conftest import MockIsaacRestClient

    class UnsupportedCapabilityClient(MockIsaacRestClient):
        async def robot_gripper_control(self, request):  # type: ignore[override]
            self.calls.append(("robot_gripper_control", request))
            raise ValueError("No gripper joints found")

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            raise ValueError("End-effector frame panda_hand not found")

    client = UnsupportedCapabilityClient()
    prim_path = "/World/MCPProbe/franka_panda"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    assert result.ok
    assert result.data.checks["gripper"].skipped is True
    assert result.data.checks["gripper"].evidence["unsupported"] is True
    assert result.data.checks["ee_pose"].skipped is True
    assert result.data.checks["ee_pose"].evidence["unsupported"] is True
    assert result.data.checks["ee_pose"].evidence["attempted_frames"] == [
        "panda_rightfinger",
        "panda_hand",
        "right_gripper",
        None,
    ]
    assert len(result.data.checks["ee_pose"].evidence["attempts"]) == 4


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_summarizes_unsupported_capability_profiles():
    from tests.conftest import MockIsaacRestClient

    class UnsupportedCapabilityClient(MockIsaacRestClient):
        async def robot_gripper_control(self, request):  # type: ignore[override]
            self.calls.append(("robot_gripper_control", request))
            raise ValueError("No gripper joints found")

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            raise ValueError("End-effector frame panda_hand not found")

    client = UnsupportedCapabilityClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=1,
            safe_nudge=False,
        ),
    )

    assert result.ok
    assert result.data.unsupported_capability_profiles == ("franka_panda",)
    assert result.data.unsupported_capability_counts == {
        "gripper": 1,
        "ee_pose": 1,
    }
    assert result.data.blocked_profiles == ()
    assert result.data.hard_failure_profiles == ()
    assert result.data.lifecycle_recovery_profiles == ()
    assert result.data.mcp_controllability_counts == {"dynamic_joint_read_only": 1}
    assert result.data.probe_capability_level_name_counts == {"dynamic_joint_read": 1}


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_summarizes_ik_target_failure_profiles():
    from tests.conftest import MockIsaacRestClient

    class KukaIkFailureClient(MockIsaacRestClient):
        async def robot_set_ee_target(self, request):  # type: ignore[override]
            self.calls.append(("robot_set_ee_target", request))
            raise ValueError("Lula IK did not converge for target pose")

        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            raise ValueError("End-effector frame not found")

    client = KukaIkFailureClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("ik_only",),
            family_filter=("kuka",),
            safe_nudge=False,
        ),
    )

    assert result.ok
    assert result.data.count == 1
    row = result.data.results[0]
    assert row.profile_name == "kuka_kr210_l150"
    assert row.mcp_controllability == "dynamic_joint_read_only"
    assert row.checks["ik"].ok is False
    assert row.checks["ik"].skipped is False
    assert row.checks["ik"].error_code == "ROBOT_SET_EE_TARGET_ERROR"
    assert "unsupported" not in row.checks["ik"].evidence
    assert [attempt["label"] for attempt in row.checks["ik"].evidence["attempted_targets"]] == [
        "default",
        "relaxed_orientation",
        "kuka_forward_high_identity",
    ]
    assert [attempt["ok"] for attempt in row.checks["ik"].evidence["attempted_targets"]] == [
        False,
        False,
        False,
    ]
    assert result.data.ik_target_failure_profiles == ("kuka_kr210_l150",)
    assert result.data.unsupported_capability_profiles == ("kuka_kr210_l150",)
    assert result.data.unsupported_capability_counts == {
        "gripper": 1,
        "ee_pose": 1,
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_marks_profile_declared_unsupported_skips():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="kinova_gen3",
            safe_nudge=False,
        ),
    )

    assert result.ok
    gripper = result.data.checks["gripper"]
    assert gripper.ok is True
    assert gripper.skipped is True
    assert gripper.evidence["unsupported"] is True
    assert gripper.evidence["capability"] == "gripper"
    assert gripper.evidence["built_in_gripper"] is False
    ik = result.data.checks["ik"]
    assert ik.ok is True
    assert ik.skipped is True
    assert ik.evidence["unsupported"] is True
    assert ik.evidence["capability"] == "ik"
    assert ik.evidence["robot_description"] is None


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_summarizes_profile_declared_unsupported_skips():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("kinova",),
            limit=1,
            safe_nudge=False,
        ),
    )

    assert result.ok
    assert result.data.results[0].profile_name == "kinova_gen3"
    assert result.data.unsupported_capability_profiles == ("kinova_gen3",)
    assert result.data.unsupported_capability_counts == {
        "gripper": 1,
        "ik": 1,
    }
    assert result.data.blocked_profiles == ()
    assert result.data.hard_failure_profiles == ()


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_ee_pose_preserves_non_unsupported_failure():
    from tests.conftest import MockIsaacRestClient

    class MixedEEPoseFailureClient(MockIsaacRestClient):
        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame == "panda_rightfinger":
                raise RuntimeError("pose solver exploded")
            raise ValueError("End-effector frame not found")

    client = MixedEEPoseFailureClient()
    prim_path = "/World/MCPProbe/franka_panda"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    ee_pose = result.data.checks["ee_pose"]
    assert result.ok
    assert ee_pose.ok is False
    assert ee_pose.skipped is False
    assert ee_pose.error_code == "ROBOT_GET_EE_POSE_ERROR"
    assert "pose solver exploded" in ee_pose.message
    assert ee_pose.evidence["attempted_frames"] == [
        "panda_rightfinger",
        "panda_hand",
        "right_gripper",
        None,
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_ridgeback_ur5_attempts_mobile_ur_ee_frames():
    from tests.conftest import MockIsaacRestClient

    class MobileURPoseClient(MockIsaacRestClient):
        async def robot_get_ee_pose(  # type: ignore[override]
            self,
            prim_path: str,
            end_effector_frame: str | None = None,
        ):
            self.calls.append((
                "robot_get_ee_pose",
                {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
            ))
            if end_effector_frame == "ur_arm_wrist_3_link":
                return {
                    "ok": True,
                    "prim_path": prim_path,
                    "end_effector_frame": "ur_arm_wrist_3_link",
                    "position": [0.4, 0.0, 0.4],
                    "orientation": [1.0, 0.0, 0.0, 0.0],
                    "source": "mock",
                }
            raise ValueError(f"End-effector frame {end_effector_frame!r} not found")

    client = MobileURPoseClient()
    prim_path = "/World/MCPProbe/ridgeback_ur5"
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="ridgeback_ur5",
            prim_path=prim_path,
            safe_nudge=False,
        ),
    )

    ee_pose = result.data.checks["ee_pose"]
    assert result.ok
    assert ee_pose.ok is True
    assert ee_pose.evidence["end_effector_frame"] == "ur_arm_wrist_3_link"
    assert ee_pose.evidence["requested_frame"] == "ur_arm_wrist_3_link"
    assert ee_pose.evidence["attempted_frames"] == [
        "tool0",
        "ee_link",
        "wrist_3_link",
        "ur_arm_tool0",
        "ur_arm_ee_link",
        "ur_arm_wrist_3_link",
    ]
    assert result.data.mcp_controllability == "dynamic_joint_read_only"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_dynamic_checks_disabled_reads_static_metadata():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="dofbot",
            dynamic_checks=False,
        ),
    )

    assert result.ok
    assert result.data.overall_ok is False
    assert result.data.checks["load"].ok is True
    assert result.data.checks["articulation"].ok is True
    assert result.data.mcp_controllability == "static_load_articulation_metadata"
    assert "static USD joint metadata" in result.data.mcp_controllability_reason
    assert result.data.probe_capability_level == 1
    assert result.data.probe_capability_level_name == "load_articulation_static_metadata"
    assert "dynamic joint read/write was intentionally skipped" in (
        result.data.probe_capability_level_reason
    )
    static = result.data.checks["static_joint_config"]
    assert static.ok is True
    assert static.skipped is False
    assert static.evidence["source"] == "usd_joint_prims_static"
    assert static.evidence["static_only"] is True
    assert static.evidence["order_reliable"] is False
    for name in (
        "simulation_play",
        "warmup_step",
        "joint_config",
        "joint_read",
        "safe_nudge",
        "gripper",
        "ik",
        "ee_pose",
    ):
        check = result.data.checks[name]
        assert check.skipped is True
        assert check.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        assert check.evidence["dynamic_checks"] is False
    assert result.data.checks["cleanup"].ok is True
    assert [name for name, _ in client.calls if name == "simulation_play"] == []
    assert [name for name, _ in client.calls if name == "simulation_step"] == []
    assert [name for name, _ in client.calls if name == "robot_get_joint_config"] == []
    static_calls = [name for name, _ in client.calls if name == "robot_get_joint_config_static"]
    assert static_calls == ["robot_get_joint_config_static"]
    assert ("stage_delete_prim", {"prim_path": "/World/MCPProbe/dofbot"}) in client.calls


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_can_route_known_dynamic_timeout_static_only():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="ur3",
            static_only_for_known_dynamic_timeouts=True,
        ),
    )

    assert result.ok
    assert result.data.profile_name == "ur3"
    assert result.data.overall_ok is False
    assert result.data.mcp_controllability == "static_load_articulation_metadata"
    assert result.data.probe_capability_level_name == "load_articulation_static_metadata"
    policy = result.data.checks["dynamic_probe_policy"]
    assert policy.skipped is True
    assert policy.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
    assert policy.evidence["profile_name"] == "ur3"
    assert policy.evidence["dynamic_checks_requested"] is True
    assert policy.evidence["dynamic_checks_effective"] is False
    assert result.data.checks["static_joint_config"].ok is True
    assert result.data.checks["joint_config"].error_code == (
        "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
    )
    assert [name for name, _ in client.calls if name == "simulation_play"] == []
    assert [name for name, _ in client.calls if name == "robot_get_joint_config"] == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_dynamic_checks_disabled_skips_static_config_unavailable():
    from tests.conftest import MockIsaacRestClient

    class MissingStaticConfigClient(MockIsaacRestClient):
        async def robot_get_joint_config_static(self, prim_path: str) -> dict:  # type: ignore[override]
            self.calls.append(("robot_get_joint_config_static", {"prim_path": prim_path}))
            raise RuntimeError("404 Not Found")

    client = MissingStaticConfigClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="dofbot",
            dynamic_checks=False,
        ),
    )

    assert result.ok
    static = result.data.checks["static_joint_config"]
    assert static.ok is True
    assert static.skipped is True
    assert static.error_code == "ROBOT_PROBE_STATIC_JOINT_CONFIG_UNAVAILABLE"
    assert static.evidence["upstream_error_code"] == "ROBOT_GET_STATIC_JOINT_CONFIG_ERROR"
    assert result.data.mcp_controllability == "load_articulation_only"
    assert result.data.probe_capability_level == 1
    assert result.data.probe_capability_level_name == "load_articulation_only"
    assert [name for name, _ in client.calls if name == "robot_get_joint_config"] == []
    assert ("stage_delete_prim", {"prim_path": "/World/MCPProbe/dofbot"}) in client.calls


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_filters_status_family_and_limit():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": "/World/MCPProbe/franka_panda", "positions": [0.0] * 7},
        {"ok": True, "prim_path": "/World/MCPProbe/franka_panda", "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("candidate_pick_place",),
            family_filter=("franka",),
            limit=1,
        ),
    )

    assert result.ok
    assert isinstance(result.data, RobotArmProfilesProbeResult)
    assert result.data.count == 1
    assert result.data.results[0].profile_name == "franka_panda"
    assert result.data.mcp_controllability_counts == {"dynamic_joint_control": 1}
    assert result.data.mcp_controllability_profiles == {
        "dynamic_joint_control": ("franka_panda",)
    }
    assert result.data.probe_capability_level_name_counts == {"ik_or_ee_telemetry": 1}
    assert result.data.probe_capability_level_name_profiles == {
        "ik_or_ee_telemetry": ("franka_panda",)
    }
    assert result.data.pick_place_validation_status_counts == {
        "known_pick_place_blocker": 1
    }
    assert result.data.pick_place_validation_status_profiles == {
        "known_pick_place_blocker": ("franka_panda",)
    }
    assert result.data.dynamic_joint_control_profiles == ("franka_panda",)
    assert result.data.blocked_profiles == ()
    assert result.data.results[0].probe_proves_pick_place is False
    assert result.data.results[0].pick_place_validation_status == (
        "known_pick_place_blocker"
    )


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_filters_explicit_profile_names_in_order():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            profile_names=("ur10", "not_a_builtin_arm", "franka_fr3"),
            safe_nudge=False,
            cleanup=False,
        ),
    )

    assert result.ok
    assert result.data.profile_names == (
        "ur10",
        "not_a_builtin_arm",
        "franka_fr3",
    )
    assert result.data.requested_count == 3
    assert [row.profile_name for row in result.data.results] == [
        "ur10",
        "not_a_builtin_arm",
        "franka_fr3",
    ]
    assert result.data.mcp_controllability_profiles == {
        "dynamic_joint_read_only": ("ur10", "franka_fr3"),
        "blocked_profile_error": ("not_a_builtin_arm",),
    }
    assert result.data.blocked_profiles == ("not_a_builtin_arm",)
    assert result.data.hard_failure_profiles == ("not_a_builtin_arm",)
    unknown = result.data.results[1]
    assert unknown.support_status == "unknown"
    assert unknown.checks["probe"].error_code == "ROBOT_PROBE_UNKNOWN_PROFILE"
    assert unknown.checks["probe"].evidence["hard_failure"] is True
    assert [name for name, _ in client.calls if name == "stage_delete_prim"] == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_empty_profile_names_selects_no_profiles():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            profile_names=(),
            safe_nudge=False,
            cleanup=False,
        ),
    )

    assert result.ok
    assert result.data.profile_names == ()
    assert result.data.requested_count == 0
    assert result.data.count == 0
    assert result.data.results == ()
    assert result.data.mcp_controllability_counts == {}
    assert result.data.blocked_profiles == ()
    assert client.calls == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_profile_names_can_intersect_status_filter():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            profile_names=("franka_fr3", "ur10", "not_a_builtin_arm"),
            status_filter=("candidate_pick_place",),
            safe_nudge=False,
            cleanup=False,
        ),
    )

    assert result.ok
    assert result.data.profile_names == (
        "franka_fr3",
        "ur10",
        "not_a_builtin_arm",
    )
    assert [row.profile_name for row in result.data.results] == [
        "ur10",
        "not_a_builtin_arm",
    ]
    assert result.data.requested_count == 2
    assert result.data.blocked_profiles == ("not_a_builtin_arm",)


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_passes_dynamic_checks_disabled():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("yahboom",),
            limit=1,
            dynamic_checks=False,
        ),
    )

    assert result.ok
    assert result.data.count == 1
    row = result.data.results[0]
    assert row.profile_name == "dofbot"
    assert row.overall_ok is False
    assert row.checks["load"].ok is True
    assert row.checks["static_joint_config"].ok is True
    assert row.checks["joint_config"].error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
    assert result.data.known_dynamic_timeout_routed_profiles == ()
    assert result.data.lifecycle_recovery_profiles == ()
    assert [name for name, _ in client.calls if name == "simulation_play"] == []
    assert [name for name, _ in client.calls if name == "simulation_step"] == []
    assert [name for name, _ in client.calls if name == "robot_get_joint_config"] == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_can_route_known_dynamic_timeouts_static_only():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("ik_only",),
            family_filter=("ur",),
            limit=2,
            static_only_for_known_dynamic_timeouts=True,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    hazardous = result.data.results[0]
    dynamic = result.data.results[1]
    assert hazardous.profile_name == "ur3"
    assert hazardous.overall_ok is False
    assert hazardous.mcp_controllability == "static_load_articulation_metadata"
    assert hazardous.probe_capability_level == 1
    assert hazardous.probe_capability_level_name == "load_articulation_static_metadata"
    policy = hazardous.checks["dynamic_probe_policy"]
    assert policy.skipped is True
    assert policy.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
    assert policy.evidence["profile_name"] == "ur3"
    assert policy.evidence["dynamic_checks_requested"] is True
    assert hazardous.checks["static_joint_config"].ok is True
    assert hazardous.checks["joint_config"].error_code == (
        "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
    )
    assert dynamic.profile_name == "ur3e"
    assert dynamic.mcp_controllability == "dynamic_joint_read_only"
    assert "dynamic_probe_policy" not in dynamic.checks
    assert dynamic.checks["joint_config"].ok is True
    assert result.data.mcp_controllability_counts == {
        "static_load_articulation_metadata": 1,
        "dynamic_joint_read_only": 1,
    }
    assert result.data.mcp_controllability_profiles == {
        "static_load_articulation_metadata": ("ur3",),
        "dynamic_joint_read_only": ("ur3e",),
    }
    assert result.data.probe_capability_level_name_counts == {
        "load_articulation_static_metadata": 1,
        "dynamic_joint_read": 1,
    }
    assert result.data.probe_capability_level_name_profiles == {
        "load_articulation_static_metadata": ("ur3",),
        "dynamic_joint_read": ("ur3e",),
    }
    assert result.data.static_metadata_profiles == ("ur3",)
    assert result.data.known_dynamic_timeout_routed_profiles == ("ur3",)
    assert result.data.lifecycle_recovery_profiles == ()
    assert result.data.timed_out_profiles == ()
    assert [name for name, _ in client.calls if name == "simulation_play"] == [
        "simulation_play"
    ]


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_routes_openarm_timeouts_static_only():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("profile_only",),
            family_filter=("openarm",),
            static_only_for_known_dynamic_timeouts=True,
        ),
    )

    assert result.ok
    rows = {row.profile_name: row for row in result.data.results}

    for profile_name in ("openarm_unimanual", "openarm_bimanual"):
        hazardous = rows[profile_name]
        assert hazardous.overall_ok is False
        assert hazardous.mcp_controllability == "static_load_articulation_metadata"
        assert hazardous.probe_capability_level == 1
        assert hazardous.probe_capability_level_name == "load_articulation_static_metadata"
        policy = hazardous.checks["dynamic_probe_policy"]
        assert policy.skipped is True
        assert policy.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
        assert policy.evidence["profile_name"] == profile_name
        assert policy.evidence["dynamic_checks_requested"] is True
        assert hazardous.checks["static_joint_config"].ok is True
        assert hazardous.checks["joint_config"].error_code == (
            "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        )


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_routes_ufactory_timeouts_static_only():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("profile_only",),
            family_filter=("ufactory",),
            static_only_for_known_dynamic_timeouts=True,
        ),
    )

    assert result.ok
    rows = {row.profile_name: row for row in result.data.results}

    for profile_name in ("lite6", "lite6_gripper", "uf850", "xarm6", "xarm7"):
        hazardous = rows[profile_name]
        assert hazardous.overall_ok is False
        assert hazardous.mcp_controllability == "static_load_articulation_metadata"
        assert hazardous.probe_capability_level == 1
        assert hazardous.probe_capability_level_name == "load_articulation_static_metadata"
        policy = hazardous.checks["dynamic_probe_policy"]
        assert policy.skipped is True
        assert policy.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
        assert policy.evidence["profile_name"] == profile_name
        assert policy.evidence["dynamic_checks_requested"] is True
        assert hazardous.checks["static_joint_config"].ok is True
        assert hazardous.checks["joint_config"].error_code == (
            "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family_filter", "static_profiles", "dynamic_profiles"),
    [
        (("robotstudio",), ("so101_new_calib",), ("so100",)),
        (("yahboom",), ("dofbot",), ()),
        (("ur",), ("ur20",), ("ur30",)),
    ],
)
async def test_robot_probe_arm_profiles_routes_remaining_known_timeout_families_static_only(
    family_filter,
    static_profiles,
    dynamic_profiles,
):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("profile_only",),
            family_filter=family_filter,
            static_only_for_known_dynamic_timeouts=True,
        ),
    )

    assert result.ok
    rows = {row.profile_name: row for row in result.data.results}
    assert set(static_profiles) | set(dynamic_profiles) <= set(rows)

    for profile_name in static_profiles:
        hazardous = rows[profile_name]
        assert hazardous.overall_ok is False
        assert hazardous.mcp_controllability == "static_load_articulation_metadata"
        assert hazardous.probe_capability_level == 1
        assert hazardous.probe_capability_level_name == "load_articulation_static_metadata"
        policy = hazardous.checks["dynamic_probe_policy"]
        assert policy.skipped is True
        assert policy.error_code == "ROBOT_PROBE_DYNAMIC_CHECKS_KNOWN_HAZARD"
        assert policy.evidence["profile_name"] == profile_name
        assert policy.evidence["dynamic_checks_requested"] is True
        assert policy.evidence["dynamic_checks_effective"] is False
        assert hazardous.checks["static_joint_config"].ok is True
        assert hazardous.checks["joint_config"].error_code == (
            "ROBOT_PROBE_DYNAMIC_CHECKS_DISABLED"
        )

    for profile_name in dynamic_profiles:
        dynamic = rows[profile_name]
        assert "dynamic_probe_policy" not in dynamic.checks
        assert dynamic.checks["joint_config"].ok is True

    if not dynamic_profiles:
        assert [name for name, _ in client.calls if name == "simulation_play"] == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_records_timeout_and_continues():
    from tests.conftest import MockIsaacRestClient

    class SlowFirstLoadClient(MockIsaacRestClient):
        load_count = 0

        async def robot_load(self, request):  # type: ignore[override]
            self.load_count += 1
            if self.load_count == 1:
                await asyncio.sleep(0.05)
            return await super().robot_load(request)

    client = SlowFirstLoadClient()
    client.responses["robot_get_joint_positions_sequence"] = [
        {"ok": True, "prim_path": "/World/MCPProbe/franka_fr3", "positions": [0.0] * 7},
        {"ok": True, "prim_path": "/World/MCPProbe/franka_fr3", "positions": [0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
            per_profile_timeout_s=0.02,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    timeout_result = result.data.results[0]
    assert timeout_result.profile_name == "franka_panda"
    assert timeout_result.overall_ok is False
    assert timeout_result.mcp_controllability == "blocked_timeout"
    assert timeout_result.probe_capability_level == 0
    assert timeout_result.probe_capability_level_name == "blocked_timeout"
    assert timeout_result.checks["probe_timeout"].error_code == "ROBOT_PROBE_PROFILE_TIMEOUT"
    assert timeout_result.checks["probe_timeout"].evidence["timeout_kind"] == "batch_per_profile"
    assert timeout_result.checks["probe_timeout"].evidence["batch_profile"] == "franka_panda"
    assert timeout_result.checks["probe_timeout"].evidence["last_phase"] == "load"
    assert timeout_result.checks["probe_timeout"].evidence["completed_checks"] == [
        "stage_reset_stop",
        "stage_reset",
    ]
    assert result.data.results[1].profile_name == "franka_fr3"
    assert result.data.results[1].checks["load"].ok is True
    assert result.data.timed_out_profiles == ("franka_panda",)
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ()
    assert result.data.blocked_profiles == ("franka_panda",)
    assert result.data.hard_failure_profiles == ()
    assert result.data.mcp_controllability_counts == {
        "blocked_timeout": 1,
        "dynamic_joint_control": 1,
    }
    assert result.data.mcp_controllability_profiles == {
        "blocked_timeout": ("franka_panda",),
        "dynamic_joint_control": ("franka_fr3",),
    }
    assert result.data.probe_capability_level_name_counts == {
        "blocked_timeout": 1,
        "ik_or_ee_telemetry": 1,
    }
    assert result.data.probe_capability_level_name_profiles == {
        "blocked_timeout": ("franka_panda",),
        "ik_or_ee_telemetry": ("franka_fr3",),
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_records_hard_error_and_continues():
    from tests.conftest import MockIsaacRestClient

    class FirstProfileErrorRobotModule(RobotModule):
        async def probe_arm_profile(self, meta, request):  # type: ignore[override]
            if request.profile_name == "franka_panda":
                raise RuntimeError("synthetic profile failure")
            return await super().probe_arm_profile(meta, request)

    client = MockIsaacRestClient()
    module = FirstProfileErrorRobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    error_result = result.data.results[0]
    assert error_result.profile_name == "franka_panda"
    assert error_result.overall_ok is False
    assert error_result.mcp_controllability == "blocked_profile_error"
    assert "synthetic profile failure" in error_result.mcp_controllability_reason
    assert error_result.probe_capability_level == 0
    assert error_result.probe_capability_level_name == "blocked_profile_error"
    assert "synthetic profile failure" in error_result.probe_capability_level_reason
    probe = error_result.checks["probe"]
    assert probe.error_code == "ROBOT_PROBE_PROFILE_ERROR"
    assert probe.evidence["exception_type"] == "RuntimeError"
    assert probe.evidence["batch_profile"] == "franka_panda"
    assert probe.evidence["hard_failure"] is True
    assert result.data.results[1].profile_name == "franka_fr3"
    assert result.data.results[1].checks["load"].ok is True
    assert result.data.blocked_profiles == ("franka_panda",)
    assert result.data.hard_failure_profiles == ("franka_panda",)
    assert result.data.timed_out_profiles == ()
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ()
    assert result.data.mcp_controllability_counts == {
        "blocked_profile_error": 1,
        "dynamic_joint_read_only": 1,
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_records_returned_error_as_hard_failure():
    from tests.conftest import MockIsaacRestClient

    class FirstProfileReturnedErrorRobotModule(RobotModule):
        async def probe_arm_profile(self, meta, request):  # type: ignore[override]
            if request.profile_name == "franka_panda":
                return ModuleResult(
                    ok=False,
                    status=ExecutionStatus.ERROR,
                    data=None,
                    message="synthetic returned profile failure",
                    error_code="ROBOT_PROBE_RETURNED_ERROR",
                )
            return await super().probe_arm_profile(meta, request)

    client = MockIsaacRestClient()
    module = FirstProfileReturnedErrorRobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    error_result = result.data.results[0]
    assert error_result.profile_name == "franka_panda"
    assert error_result.overall_ok is False
    assert error_result.mcp_controllability == "blocked_profile_error"
    assert "synthetic returned profile failure" in error_result.mcp_controllability_reason
    assert error_result.probe_capability_level == 0
    assert error_result.probe_capability_level_name == "blocked_profile_error"
    probe = error_result.checks["probe"]
    assert probe.error_code == "ROBOT_PROBE_RETURNED_ERROR"
    assert probe.message == "synthetic returned profile failure"
    assert probe.evidence["batch_profile"] == "franka_panda"
    assert probe.evidence["hard_failure"] is True
    assert probe.evidence["returned_status"] == "error"
    assert result.data.results[1].profile_name == "franka_fr3"
    assert result.data.results[1].checks["load"].ok is True
    assert result.data.blocked_profiles == ("franka_panda",)
    assert result.data.hard_failure_profiles == ("franka_panda",)
    assert result.data.timed_out_profiles == ()
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ()
    assert result.data.mcp_controllability_counts == {
        "blocked_profile_error": 1,
        "dynamic_joint_read_only": 1,
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_records_empty_success_result_and_continues():
    from tests.conftest import MockIsaacRestClient

    class FirstProfileEmptyResultRobotModule(RobotModule):
        async def probe_arm_profile(self, meta, request):  # type: ignore[override]
            if request.profile_name == "franka_panda":
                return ModuleResult(
                    ok=True,
                    status=ExecutionStatus.PASSED,
                    data=None,
                )
            return await super().probe_arm_profile(meta, request)

    client = MockIsaacRestClient()
    module = FirstProfileEmptyResultRobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    error_result = result.data.results[0]
    assert error_result.profile_name == "franka_panda"
    assert error_result.overall_ok is False
    assert error_result.mcp_controllability == "blocked_profile_error"
    assert error_result.probe_capability_level == 0
    assert error_result.probe_capability_level_name == "blocked_profile_error"
    probe = error_result.checks["probe"]
    assert probe.error_code == "ROBOT_PROBE_PROFILE_EMPTY_RESULT"
    assert probe.evidence["batch_profile"] == "franka_panda"
    assert probe.evidence["hard_failure"] is True
    assert probe.evidence["contract_violation"] == "ok_without_data"
    assert result.data.results[1].profile_name == "franka_fr3"
    assert result.data.results[1].checks["load"].ok is True
    assert result.data.blocked_profiles == ("franka_panda",)
    assert result.data.hard_failure_profiles == ("franka_panda",)
    assert result.data.timed_out_profiles == ()
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ()
    assert result.data.mcp_controllability_counts == {
        "blocked_profile_error": 1,
        "dynamic_joint_read_only": 1,
    }


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_records_phase_exception_as_hard_failure():
    from tests.conftest import MockIsaacRestClient

    class LoadRaisesClient(MockIsaacRestClient):
        async def robot_load(self, request):  # type: ignore[override]
            self.calls.append(("robot_load", request))
            raise RuntimeError("synthetic Kit load failure")

    client = LoadRaisesClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(profile_name="franka_panda"),
    )

    assert result.ok
    assert result.data.overall_ok is False
    assert result.data.mcp_controllability == "blocked_load_or_articulation"
    load = result.data.checks["load"]
    assert load.error_code == "ROBOT_PROBE_LOAD_ERROR"
    assert load.message == "synthetic Kit load failure"
    assert load.evidence["exception_type"] == "RuntimeError"
    assert load.evidence["hard_failure"] is True
    assert result.data.checks["articulation"].skipped is True
    assert result.data.checks["articulation"].error_code == "ROBOT_PROBE_LOAD_MISSING"


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_preserves_status_recommendation_for_blocked_rows():
    from tests.conftest import MockIsaacRestClient

    class CandidateProfileErrorRobotModule(RobotModule):
        async def probe_arm_profile(self, meta, request):  # type: ignore[override]
            if request.profile_name == "franka_panda":
                raise RuntimeError("synthetic candidate failure")
            return await super().probe_arm_profile(meta, request)

    timeout_result = await RobotModule(MockIsaacRestClient()).probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("candidate_pick_place",),
            family_filter=("franka",),
            limit=1,
            batch_timeout_s=0.001,
        ),
    )
    assert timeout_result.ok
    timeout_row = timeout_result.data.results[0]
    assert timeout_row.profile_name == "franka_panda"
    assert timeout_row.mcp_controllability == "blocked_batch_timeout"
    assert timeout_row.recommended_next_status == "candidate_pick_place"

    error_result = await CandidateProfileErrorRobotModule(
        MockIsaacRestClient()
    ).probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            status_filter=("candidate_pick_place",),
            family_filter=("franka",),
            limit=1,
        ),
    )
    assert error_result.ok
    error_row = error_result.data.results[0]
    assert error_row.profile_name == "franka_panda"
    assert error_row.mcp_controllability == "blocked_profile_error"
    assert error_row.recommended_next_status == "candidate_pick_place"


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_warmup_timeout_stops_downstream_and_defers_cleanup(
    monkeypatch: pytest.MonkeyPatch,
):
    from tests.conftest import MockIsaacRestClient

    monkeypatch.setattr(robot_module, "_PROBE_PHASE_OPERATION_TIMEOUT_S", 0.001)

    class SlowWarmupClient(MockIsaacRestClient):
        async def simulation_step(self, request):  # type: ignore[override]
            self.calls.append(("simulation_step", request))
            await asyncio.sleep(0.05)
            return await super().simulation_step(request)

    client = SlowWarmupClient()
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="franka_panda",
            timeout_s=1.0,
        ),
    )

    assert result.ok
    assert result.data.overall_ok is False
    assert result.data.mcp_controllability == "blocked_timeout"
    assert "warmup_step" in result.data.mcp_controllability_reason
    assert result.data.probe_capability_level == 0
    assert result.data.probe_capability_level_name == "blocked_timeout"
    assert "warmup_step" in result.data.probe_capability_level_reason
    warmup = result.data.checks["warmup_step"]
    assert warmup.error_code == "ROBOT_PROBE_WARMUP_STEP_TIMEOUT"
    assert warmup.evidence["timeout_kind"] == "phase_operation"
    assert "joint_config" not in result.data.checks
    assert "joint_read" not in result.data.checks
    assert "safe_nudge" not in result.data.checks
    assert "gripper" not in result.data.checks
    assert result.data.checks["simulation_stop"].error_code == (
        "ROBOT_PROBE_SIMULATION_STOP_DEFERRED"
    )
    assert result.data.checks["cleanup"].error_code == "ROBOT_PROBE_CLEANUP_DEFERRED"
    assert result.data.checks["cleanup"].evidence["requires_lifecycle_recovery"] is True
    assert [name for name, _ in client.calls if name == "simulation_stop"] == [
        "simulation_stop"
    ]
    assert [name for name, _ in client.calls if name == "stage_delete_prim"] == []
    assert [name for name, _ in client.calls if name == "robot_get_joint_config"] == []


@pytest.mark.asyncio
async def test_robot_probe_arm_profile_simulation_play_failure_is_blocked_phase_error():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["simulation_play"] = {
        "ok": False,
        "error": "play refused",
    }
    module = RobotModule(client)

    result = await module.probe_arm_profile(
        _meta(),
        RobotArmProfileProbeRequest(
            profile_name="factory_franka",
            timeout_s=1.0,
        ),
    )

    assert result.ok
    assert result.data.overall_ok is False
    assert result.data.recommended_next_status == "candidate_pick_place"
    assert result.data.mcp_controllability == "blocked_phase_error"
    assert "simulation_play" in result.data.mcp_controllability_reason
    assert result.data.probe_capability_level == 0
    assert result.data.probe_capability_level_name == "blocked_phase_error"
    assert "simulation_play" in result.data.probe_capability_level_reason
    play = result.data.checks["simulation_play"]
    assert play.error_code == "ROBOT_PROBE_SIMULATION_PLAY_FAILED"
    assert "joint_config" not in result.data.checks
    assert "joint_read" not in result.data.checks
    assert "safe_nudge" not in result.data.checks


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_aborts_after_phase_timeout_cleanup_deferred(
    monkeypatch: pytest.MonkeyPatch,
):
    from tests.conftest import MockIsaacRestClient

    monkeypatch.setattr(robot_module, "_PROBE_PHASE_OPERATION_TIMEOUT_S", 0.001)
    class SlowWarmupClient(MockIsaacRestClient):
        async def simulation_step(self, request):  # type: ignore[override]
            self.calls.append(("simulation_step", request))
            await asyncio.sleep(0.05)
            return await super().simulation_step(request)

    client = SlowWarmupClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
            per_profile_timeout_s=1.0,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    timeout_result = result.data.results[0]
    aborted_result = result.data.results[1]
    assert timeout_result.mcp_controllability == "blocked_timeout"
    assert "warmup_step" in timeout_result.mcp_controllability_reason
    assert timeout_result.probe_capability_level == 0
    assert timeout_result.probe_capability_level_name == "blocked_timeout"
    assert "warmup_step" in timeout_result.probe_capability_level_reason
    assert timeout_result.checks["warmup_step"].error_code == "ROBOT_PROBE_WARMUP_STEP_TIMEOUT"
    assert timeout_result.checks["simulation_stop"].error_code == (
        "ROBOT_PROBE_SIMULATION_STOP_DEFERRED"
    )
    assert timeout_result.checks["cleanup"].error_code == "ROBOT_PROBE_CLEANUP_DEFERRED"
    assert aborted_result.profile_name == "franka_fr3"
    assert aborted_result.checks["probe_batch_aborted"].error_code == "ROBOT_PROBE_BATCH_ABORTED"
    assert aborted_result.checks["probe_batch_aborted"].evidence["blocked_by_profile"] == "franka_panda"
    assert aborted_result.checks["probe_batch_aborted"].evidence["reason"] == (
        "profile_timeout_cleanup_deferred"
    )
    assert aborted_result.probe_capability_level == 0
    assert aborted_result.probe_capability_level_name == "blocked_batch_abort"
    assert result.data.lifecycle_recovery_profiles == ("franka_panda",)
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ("franka_fr3",)


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_aborts_remaining_when_timeout_cleanup_times_out(
    monkeypatch: pytest.MonkeyPatch,
):
    from tests.conftest import MockIsaacRestClient

    monkeypatch.setattr(robot_module, "_PROBE_TIMEOUT_CLEANUP_TIMEOUT_S", 0.001)

    class SlowLoadUnhealthyCleanupClient(MockIsaacRestClient):
        cleanup_unhealthy = False

        async def robot_load(self, request):  # type: ignore[override]
            self.calls.append(("robot_load", request))
            try:
                await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                self.cleanup_unhealthy = True
                raise
            return {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "usd_url": request.get("usd_url", ""),
                "type_name": "Xform",
                "has_articulation": True,
            }

        async def simulation_stop(self):  # type: ignore[override]
            self.calls.append(("simulation_stop", {}))
            if self.cleanup_unhealthy:
                await asyncio.sleep(0.05)
            return {
                "is_playing": False,
                "is_stopped": True,
                "current_time": 0.0,
                "start_time": 0.0,
                "end_time": 10.0,
                "time_codes_per_second": 24.0,
            }

    client = SlowLoadUnhealthyCleanupClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
            per_profile_timeout_s=0.01,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    timeout_result = result.data.results[0]
    aborted_result = result.data.results[1]
    assert timeout_result.profile_name == "franka_panda"
    assert timeout_result.checks["probe_timeout"].error_code == "ROBOT_PROBE_PROFILE_TIMEOUT"
    assert timeout_result.checks["probe_timeout"].evidence["last_phase"] == "load"
    assert timeout_result.checks["simulation_stop"].error_code == "ROBOT_PROBE_SIMULATION_STOP_TIMEOUT"
    assert aborted_result.profile_name == "franka_fr3"
    aborted_check = aborted_result.checks["probe_batch_aborted"]
    assert aborted_result.overall_ok is False
    assert aborted_result.mcp_controllability == "blocked_batch_abort"
    assert aborted_result.probe_capability_level == 0
    assert aborted_result.probe_capability_level_name == "blocked_batch_abort"
    assert aborted_check.error_code == "ROBOT_PROBE_BATCH_ABORTED"
    assert aborted_check.evidence["blocked_by_profile"] == "franka_panda"
    assert aborted_check.evidence["reason"] == "profile_timeout_cleanup_failed"
    assert [call for call in client.calls if call[0] == "robot_load"] == [
        (
            "robot_load",
            {
                "usd_url": result.data.results[0].asset_url,
                "prim_path": "/World/MCPProbe/franka_panda",
                "position": None,
                "rotation": None,
            },
        )
    ]
    assert result.data.lifecycle_recovery_profiles == ("franka_panda",)
    assert result.data.batch_timeout_profiles == ()
    assert result.data.batch_aborted_profiles == ("franka_fr3",)


@pytest.mark.asyncio
async def test_robot_probe_arm_profiles_records_batch_timeout_before_next_profile():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.probe_arm_profiles(
        _meta(),
        RobotArmProfilesProbeRequest(
            family_filter=("franka",),
            limit=2,
            batch_timeout_s=0.001,
        ),
    )

    assert result.ok
    assert result.data.count == 2
    assert result.data.requested_count == 2
    for profile_result in result.data.results:
        assert profile_result.overall_ok is False
        assert profile_result.mcp_controllability == "blocked_batch_timeout"
        assert profile_result.probe_capability_level == 0
        assert profile_result.probe_capability_level_name == "blocked_batch_timeout"
        check = profile_result.checks["probe_batch_timeout"]
        assert check.skipped is True
        assert check.error_code == "ROBOT_PROBE_BATCH_TIMEOUT"
        assert check.evidence["timeout_kind"] == "batch_total"
    assert not [call for call in client.calls if call[0] == "robot_load"]
    assert result.data.timed_out_profiles == ("franka_panda", "franka_fr3")
    assert result.data.batch_timeout_profiles == ("franka_panda", "franka_fr3")
    assert result.data.batch_aborted_profiles == ()
    assert result.data.blocked_profiles == ("franka_panda", "franka_fr3")
    assert result.data.lifecycle_recovery_profiles == ()
    assert result.data.mcp_controllability_counts == {"blocked_batch_timeout": 2}
    assert result.data.mcp_controllability_profiles == {
        "blocked_batch_timeout": ("franka_panda", "franka_fr3")
    }
    assert result.data.probe_capability_level_name_counts == {
        "blocked_batch_timeout": 2,
    }
    assert result.data.probe_capability_level_name_profiles == {
        "blocked_batch_timeout": ("franka_panda", "franka_fr3")
    }


# Phase J — drive_physics


@pytest.mark.asyncio
async def test_robot_drive_physics_returns_job_id():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    waypoints = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 2.0, 0.0))
    request = RobotDrivePhysicsRequest(
        prim_path="/World/Robot",
        waypoints=waypoints,
        wheel_radius=0.14, wheel_base=0.413,
    )
    result = await module.drive_physics(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotDrivePhysicsResult)
    assert result.data.job_id == "drive_test_0001"
    assert result.data.diagnostics == {}
    drive_calls = [c for c in client.calls if c[0] == "robot_drive_physics"]
    assert len(drive_calls) == 1
    assert drive_calls[0][1]["waypoints"] == [list(p) for p in waypoints]
    assert drive_calls[0][1]["wheel_radius"] == 0.14


@pytest.mark.asyncio
async def test_robot_drive_physics_server_error_maps():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_drive_physics"] = {
        "ok": False,
        "reason": "wheel DOF unresolvable",
        "diagnostics": {"reason": "wheel_dof_unresolvable"},
    }
    module = RobotModule(client)
    request = RobotDrivePhysicsRequest(
        prim_path="/World/X",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
    )
    result = await module.drive_physics(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_DRIVE_PHYSICS_ERROR"
    assert "DOF" in (result.message or "")
    assert isinstance(result.data, RobotDrivePhysicsResult)
    assert result.data.ok is False
    assert result.data.job_id == ""
    assert result.data.prim_path == "/World/X"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_drive_physics_error"
    assert diagnostics["raw_reason"] == "wheel_dof_unresolvable"
    assert diagnostics["upstream_error_code"] == "ROBOT_DRIVE_PHYSICS_ERROR"
    assert diagnostics["upstream_message"] == "wheel DOF unresolvable"
    assert diagnostics["prim_path"] == "/World/X"
    assert diagnostics["waypoint_count"] == 2
    assert diagnostics["wheel_radius"] == 0.14
    assert diagnostics["wheel_base"] == 0.413
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_get_joint_config_static",
        "robot_drive_physics",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_drive_physics_exception_returns_typed_diagnostics():
    class FailingClient:
        async def robot_drive_physics(self, request):
            raise RuntimeError("physics drive service unavailable")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotDrivePhysicsRequest(
        prim_path="/World/MobileBase",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        max_linear=0.5,
        max_angular=0.75,
        wheel_radius=0.2,
        wheel_base=0.6,
        arrival_tolerance=0.1,
        timeout_s=12.0,
        lookahead=0.4,
    )
    result = await module.drive_physics(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_DRIVE_PHYSICS_ERROR"
    assert isinstance(result.data, RobotDrivePhysicsResult)
    assert result.data.ok is False
    assert result.data.prim_path == "/World/MobileBase"
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_drive_physics_error"
    assert diagnostics["upstream_message"] == "physics drive service unavailable"
    assert diagnostics["max_linear"] == 0.5
    assert diagnostics["max_angular"] == 0.75
    assert diagnostics["wheel_radius"] == 0.2
    assert diagnostics["wheel_base"] == 0.6
    assert diagnostics["arrival_tolerance"] == 0.1
    assert diagnostics["timeout_s"] == 12.0
    assert diagnostics["lookahead"] == 0.4


@pytest.mark.asyncio
async def test_robot_run_franka_pick_place_uses_official_controller_payload():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotFrankaPickPlaceRequest(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/KLT",
        target_position=(0.45, -0.35, 0.72),
        max_steps=1200,
        position_tolerance=0.04,
        lift_height_tolerance=0.025,
    )

    result = await module.run_franka_pick_place(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotFrankaPickPlaceResult)
    assert result.data.controller == "isaacsim.robot.manipulators.examples.franka.controllers.PickPlaceController"
    assert result.data.uses_kinematic_carry is False
    assert result.data.placed is True
    calls = [c for c in client.calls if c[0] == "robot_run_franka_pick_place"]
    assert len(calls) == 1
    assert calls[0][1]["robot_prim_path"] == "/World/Franka"
    assert calls[0][1]["object_prim_path"] == "/World/KLT"
    assert calls[0][1]["target_position"] == [0.45, -0.35, 0.72]
    assert calls[0][1]["max_steps"] == 1200


@pytest.mark.asyncio
async def test_robot_run_franka_pick_place_forwards_explicit_grasp_pose():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotFrankaPickPlaceRequest(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/Cube",
        target_position=(0.45, -0.35, 0.72),
        picking_position=(0.3, 0.2, 0.51),
        end_effector_orientation=(0.0, 0.0, 1.0, 0.0),
    )

    result = await module.run_franka_pick_place(_meta(), request)

    assert result.ok
    calls = [c for c in client.calls if c[0] == "robot_run_franka_pick_place"]
    assert calls[0][1]["picking_position"] == [0.3, 0.2, 0.51]
    assert calls[0][1]["end_effector_orientation"] == [0.0, 0.0, 1.0, 0.0]


@pytest.mark.asyncio
async def test_robot_run_franka_pick_place_failed_physical_validation_is_not_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_run_franka_pick_place"] = {
        "ok": False,
        "robot_prim_path": "/World/Franka",
        "object_prim_path": "/World/KLT",
        "target_position": [0.45, -0.35, 0.72],
        "controller": "isaacsim.robot.manipulators.examples.franka.controllers.PickPlaceController",
        "gripper": "ParallelGripper",
        "uses_kinematic_carry": False,
        "steps": 300,
        "done": False,
        "placed": False,
        "lifted": False,
        "final_object_position": [0.2, 0.35, 0.72],
        "final_distance": 0.72,
        "max_lift_delta": 0.0,
        "reason": "Object was not lifted by the gripper",
    }
    module = RobotModule(client)

    result = await module.run_franka_pick_place(
        _meta(),
        RobotFrankaPickPlaceRequest(
            robot_prim_path="/World/Franka",
            object_prim_path="/World/KLT",
            target_position=(0.45, -0.35, 0.72),
        ),
    )

    assert not result.ok
    assert result.error_code == "ROBOT_FRANKA_PICK_PLACE_FAILED"
    assert isinstance(result.data, RobotFrankaPickPlaceResult)
    assert result.data.uses_kinematic_carry is False
    assert "not lifted" in (result.message or "")


@pytest.mark.asyncio
async def test_robot_run_franka_pick_place_exception_returns_typed_diagnostics():
    class FailingClient:
        async def robot_run_franka_pick_place(self, request):
            raise RuntimeError("PickPlaceController unavailable")

    module = RobotModule(FailingClient())  # type: ignore[arg-type]
    request = RobotFrankaPickPlaceRequest(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/Cube",
        target_position=(0.45, -0.35, 0.72),
        picking_position=(0.3, 0.2, 0.51),
        end_effector_initial_height=0.2,
        max_steps=900,
        position_tolerance=0.04,
        lift_height_tolerance=0.02,
    )

    result = await module.run_franka_pick_place(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_FRANKA_PICK_PLACE_ERROR"
    assert isinstance(result.data, RobotFrankaPickPlaceResult)
    assert result.data.ok is False
    assert result.data.robot_prim_path == "/World/Franka"
    assert result.data.object_prim_path == "/World/Cube"
    assert result.data.target_position == (0.45, -0.35, 0.72)
    assert result.data.picking_position == (0.3, 0.2, 0.51)
    assert result.data.end_effector_initial_height == 0.2
    diagnostics = result.data.diagnostics
    assert diagnostics["reason"] == "robot_franka_pick_place_error"
    assert diagnostics["upstream_error_code"] == "ROBOT_FRANKA_PICK_PLACE_ERROR"
    assert diagnostics["upstream_message"] == "PickPlaceController unavailable"
    assert diagnostics["robot_prim_path"] == "/World/Franka"
    assert diagnostics["object_prim_path"] == "/World/Cube"
    assert diagnostics["target_position"] == [0.45, -0.35, 0.72]
    assert diagnostics["picking_position"] == [0.3, 0.2, 0.51]
    assert diagnostics["max_steps"] == 900
    assert diagnostics["position_tolerance"] == 0.04
    assert diagnostics["lift_height_tolerance"] == 0.02
    assert diagnostics["fallback_tool_order"] == [
        "mcp_runtime_info",
        "simulation_get_status",
        "stage_capture_snapshot",
        "robot_run_franka_pick_place",
        "extension_capture_logs",
    ]


@pytest.mark.asyncio
async def test_robot_install_pick_place_playback_demo_forwards_payload():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotFrankaPickPlaceDemoRequest(
        robot_prim_path="/World/Franka",
        object_prim_path="/World/PickCube",
        target_position=(0.45, -0.35, 0.02575),
        object_initial_position=(0.3, 0.35, 0.02575),
        end_effector_orientation=(0.0, 0.0, 1.0, 0.0),
    )

    result = await module.install_franka_pick_place_playback_demo(_meta(), request)

    assert result.ok
    assert isinstance(result.data, RobotFrankaPickPlaceDemoStatus)
    assert result.data.status == "idle"
    assert result.data.uses_kinematic_carry is False
    assert result.data.object_fit_ok is True
    assert result.data.object_fit_limit_m == pytest.approx(0.075)
    assert result.data.object_fit_measured_m == pytest.approx(0.04)
    calls = [c for c in client.calls if c[0] == "robot_install_franka_pick_place_playback_demo"]
    assert len(calls) == 1
    assert calls[0][1]["object_initial_position"] == [0.3, 0.35, 0.02575]
    assert calls[0][1]["object_asset_url"] is None
    assert calls[0][1]["grid_asset_url"].endswith("/Environments/Grid/default_environment.usd")
    assert calls[0][1]["end_effector_orientation"] == [0.0, 0.0, 1.0, 0.0]
    assert calls[0][1]["max_grasp_width_m"] == pytest.approx(0.08)
    assert calls[0][1]["fit_clearance_m"] == pytest.approx(0.005)
    assert calls[0][1]["robot_description"] == "Franka"


@pytest.mark.asyncio
async def test_robot_install_pick_place_playback_demo_forwards_explicit_object_asset_url():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)
    request = RobotFrankaPickPlaceDemoRequest(
        object_asset_url="https://example.invalid/object.usd",
    )

    result = await module.install_franka_pick_place_playback_demo(_meta(), request)

    assert result.ok
    calls = [c for c in client.calls if c[0] == "robot_install_franka_pick_place_playback_demo"]
    assert len(calls) == 1
    assert calls[0][1]["object_asset_url"] == "https://example.invalid/object.usd"
    assert calls[0][1]["max_grasp_width_m"] == pytest.approx(0.08)
    assert calls[0][1]["fit_clearance_m"] == pytest.approx(0.005)


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_blocks_franka_panda_until_durable_proof():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(profile_name="franka_panda"),
    )

    assert result.ok
    assert result.data.ok is False
    assert result.data.status == "unsupported"
    assert result.data.profile_name == "franka_panda"
    assert result.data.support_status == "candidate_pick_place"
    assert result.data.diagnostics["reason"] == "pick_place_profile_unsupported"
    assert result.data.diagnostics["target_status"] == "validated_pick_place"
    assert result.data.diagnostics["known_pick_place_blocker"] is True
    assert "insufficient lift" in (
        result.data.diagnostics["known_pick_place_blocker_reason"]
    )
    assert result.data.diagnostics["fallback_tool_order"] == [
        "robot_list_arm_profiles",
        "robot_probe_arm_profile",
        "robot_install_pick_place_playback_demo",
    ]
    assert any(
        "probe success is not pick/place validation" in item
        for item in result.data.diagnostics["suggested_next"]
    )
    assert client.calls == []


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_routes_validated_franka_fr3():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(profile_name="franka_fr3", robot_prim_path="/World/FR3"),
    )

    assert result.ok
    assert result.data.profile_name == "franka_fr3"
    assert result.data.support_status == "validated_pick_place"
    assert result.data.controller_strategy == "same_family_franka_candidate"
    assert client.calls[-2][0] == "robot_load"
    assert client.calls[-2][1]["prim_path"] == "/World/FR3"
    assert client.calls[-2][1]["usd_url"].endswith("/Robots/FrankaRobotics/FrankaFR3/fr3.usd")
    assert client.calls[-1][0] == "robot_install_franka_pick_place_playback_demo"
    assert client.calls[-1][1]["robot_prim_path"] == "/World/FR3"
    assert client.calls[-1][1]["robot_description"] == "FR3"
    assert client.calls[-1][1]["max_grasp_width_m"] == pytest.approx(0.08)
    assert client.calls[-1][1]["fit_clearance_m"] == pytest.approx(0.005)


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_blocks_factory_franka_candidate_playback():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(
            profile_name="factory_franka",
            robot_prim_path="/World/FactoryFranka",
        ),
    )

    assert result.ok
    assert result.data.ok is False
    assert result.data.status == "unsupported"
    assert result.data.profile_name == "factory_franka"
    assert result.data.support_status == "candidate_pick_place"
    assert result.data.controller_strategy == "same_family_franka_candidate"
    assert result.data.uses_kinematic_carry is False
    assert result.data.diagnostics["unsupported"] is True
    assert result.data.diagnostics["reason"] == "pick_place_profile_unsupported"
    assert result.data.diagnostics["support_status"] == "candidate_pick_place"
    assert result.data.diagnostics["playback_route"] == "blocked_unvalidated_profile"
    assert result.data.diagnostics["adapter_ready"] is False
    assert result.data.diagnostics["known_pick_place_blocker"] is True
    assert "deeper combined-Z offset trial" in (
        result.data.diagnostics["known_pick_place_blocker_reason"]
    )
    assert result.data.diagnostics["required_support_status"] == "validated_pick_place"
    assert (
        result.data.diagnostics["validated_pick_place_requires"]
        == "durable_live_pick_place_proof"
    )
    assert result.data.diagnostics["target_status"] == "validated_pick_place"
    assert result.data.diagnostics["fallback_tool_order"] == [
        "robot_list_arm_profiles",
        "robot_probe_arm_profile",
        "robot_install_pick_place_playback_demo",
    ]
    assert result.data.diagnostics["probe_success_is_pick_place_validation"] is False
    assert (
        result.data.diagnostics["mcp_controllability_is_pick_place_validation"]
        is False
    )
    assert result.data.diagnostics["profile_family"] == "franka"
    assert result.data.diagnostics["built_in_gripper"] is True
    assert client.calls == []


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_reports_candidate_unsupported():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(profile_name="ur10"),
    )

    assert result.ok
    assert result.data.ok is False
    assert result.data.status == "unsupported"
    assert result.data.profile_name == "ur10"
    assert result.data.support_status == "candidate_pick_place"
    assert result.data.uses_kinematic_carry is False
    assert result.data.object_fit_ok is False
    assert result.data.diagnostics["reason"] == "pick_place_profile_unsupported"
    assert result.data.diagnostics["playback_route"] == "blocked_unvalidated_profile"
    assert result.data.diagnostics["adapter_ready"] is False
    assert result.data.diagnostics["known_pick_place_blocker"] is False
    assert result.data.diagnostics["known_pick_place_blocker_reason"] is None
    assert result.data.diagnostics["required_support_status"] == "validated_pick_place"
    assert (
        result.data.diagnostics["validated_pick_place_requires"]
        == "durable_live_pick_place_proof"
    )
    assert result.data.diagnostics["target_status"] == "validated_pick_place"
    assert result.data.diagnostics["fallback_tool_order"] == [
        "robot_list_arm_profiles",
        "robot_probe_arm_profile",
        "robot_install_pick_place_playback_demo",
    ]
    assert any(
        "support_status=validated_pick_place" in item
        for item in result.data.diagnostics["suggested_next"]
    )
    assert result.data.diagnostics["probe_success_is_pick_place_validation"] is False
    assert result.data.diagnostics["profile_family"] == "ur"
    assert result.data.diagnostics["built_in_gripper"] is False
    assert client.calls == []


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_reports_unknown_profile():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(profile_name="not_a_builtin_arm"),
    )

    assert result.ok
    assert result.data.ok is False
    assert result.data.status == "unsupported"
    assert result.data.profile_name == "not_a_builtin_arm"
    assert result.data.support_status == "unsupported"
    assert result.data.diagnostics["reason"] == "pick_place_profile_unsupported"
    assert result.data.diagnostics["playback_route"] == "unknown_profile"
    assert result.data.diagnostics["adapter_ready"] is False
    assert result.data.diagnostics["known_pick_place_blocker"] is False
    assert result.data.diagnostics["known_pick_place_blocker_reason"] is None
    assert result.data.diagnostics["target_status"] == "validated_pick_place"
    assert result.data.diagnostics["required_support_status"] == "validated_pick_place"
    assert result.data.diagnostics["fallback_tool_order"] == [
        "robot_list_arm_profiles",
        "robot_probe_arm_profile",
        "robot_install_pick_place_playback_demo",
    ]
    assert result.data.diagnostics["probe_success_is_pick_place_validation"] is False
    assert "profile_family" not in result.data.diagnostics
    assert client.calls == []


@pytest.mark.asyncio
async def test_robot_get_pick_place_demo_status_reports_done_metrics():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.get_pick_place_demo_status(_meta())

    assert result.ok
    assert isinstance(result.data, RobotFrankaPickPlaceDemoStatus)
    assert result.data.status == "done"
    assert result.data.done is True
    assert result.data.placed is True
    assert result.data.lifted is True
    assert result.data.final_distance == pytest.approx(0.01)
    assert result.data.object_bbox_size == pytest.approx((0.04, 0.04, 0.04))
    assert result.data.object_fit_ok is True
    assert result.data.object_fit_axis == "x"
    assert result.data.object_fit_limit_m == pytest.approx(0.075)
    assert result.data.object_fit_measured_m == pytest.approx(0.04)
    progress = result.data.diagnostics["playback_progress"]
    assert progress["current_event"] == 9
    assert progress["current_event_ticks"] == 12
    assert progress["event_tick_counts"]["9"] == 12
    assert progress["samples"][-1]["step"] == 620
    assert progress["samples"][-1]["distance_to_target"] == pytest.approx(0.01)


@pytest.mark.asyncio
async def test_robot_get_pick_place_demo_status_records_timeout_without_waiting_for_rest_timeout():
    from tests.conftest import MockIsaacRestClient

    class SlowStatusClient(MockIsaacRestClient):
        async def robot_get_pick_place_demo_status(self) -> dict:
            self.calls.append(("robot_get_pick_place_demo_status", {}))
            await asyncio.sleep(60)
            return self.responses["robot_get_pick_place_demo_status"]

    client = SlowStatusClient()
    module = RobotModule(client)

    result = await module.get_pick_place_demo_status(_meta(), timeout_s=0.01)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert isinstance(result.data, RobotFrankaPickPlaceDemoStatus)
    assert result.error_code == "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT"
    assert "timed out after 0.01s" in (result.message or "")
    assert result.data.ok is False
    assert result.data.status == "timeout"
    assert result.data.last_error == result.message
    assert result.data.diagnostics["reason"] == "pick_place_demo_status_timeout"
    assert result.data.diagnostics["upstream_error_code"] == (
        "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_TIMEOUT"
    )
    assert result.data.diagnostics["timeout_s"] == pytest.approx(0.01)
    assert result.data.diagnostics["fallback_tool_order"] == [
        "simulation_get_status",
        "robot_get_pick_place_demo_status",
        "extension_capture_logs",
    ]
    assert any(
        "simulation_get_status" in item
        for item in result.data.diagnostics["suggested_next"]
    )
    assert result.duration_ms is not None
    assert result.duration_ms < 1000
    assert client.calls == [("robot_get_pick_place_demo_status", {})]


@pytest.mark.asyncio
async def test_robot_get_pick_place_demo_status_surfaces_rest_error_diagnostics():
    from tests.conftest import MockIsaacRestClient

    class FailingStatusClient(MockIsaacRestClient):
        async def robot_get_pick_place_demo_status(self) -> dict:
            self.calls.append(("robot_get_pick_place_demo_status", {}))
            raise RuntimeError("status endpoint unavailable")

    client = FailingStatusClient()
    module = RobotModule(client)

    result = await module.get_pick_place_demo_status(_meta(), timeout_s=0.5)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_ERROR"
    assert isinstance(result.data, RobotFrankaPickPlaceDemoStatus)
    assert result.data.status == "error"
    assert result.data.last_error == "status endpoint unavailable"
    assert result.data.diagnostics["reason"] == "pick_place_demo_status_error"
    assert result.data.diagnostics["upstream_error_code"] == (
        "ROBOT_FRANKA_PICK_PLACE_DEMO_STATUS_ERROR"
    )
    assert result.data.diagnostics["timeout_s"] == pytest.approx(0.5)
    assert result.data.diagnostics["fallback_tool_order"] == [
        "simulation_get_status",
        "robot_get_pick_place_demo_status",
        "extension_capture_logs",
    ]
    assert client.calls == [("robot_get_pick_place_demo_status", {})]


@pytest.mark.asyncio
async def test_robot_get_pick_place_demo_status_reports_oversized_object_fit_failure():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_get_pick_place_demo_status"] = {
        "ok": True,
        "status": "idle",
        "robot_prim_path": "/World/Franka",
        "object_prim_path": "/World/KLT",
        "target_position": [0.45, -0.35, 0.02575],
        "controller": "isaacsim.robot.manipulators.examples.franka.controllers.PickPlaceController",
        "gripper": "ParallelGripper",
        "uses_kinematic_carry": False,
        "steps": 0,
        "max_steps": 1800,
        "done": False,
        "placed": False,
        "lifted": False,
        "final_distance": 0.0,
        "max_lift_delta": 0.0,
        "object_bbox_center": [0.3, 0.35, 0.073],
        "object_bbox_size": [0.198, 0.297, 0.146],
        "diagnostics": {
            "object_fit": {
                "ok": False,
                "reason": "Object bbox exceeds gripper opening.",
                "axis": "y",
                "limit_m": 0.075,
                "measured_m": 0.297,
            }
        },
    }
    module = RobotModule(client)

    result = await module.get_pick_place_demo_status(_meta())

    assert result.ok
    assert result.data.object_fit_ok is False
    assert result.data.object_fit_reason == "Object bbox exceeds gripper opening."
    assert result.data.object_fit_axis == "y"
    assert result.data.object_fit_limit_m == pytest.approx(0.075)
    assert result.data.object_fit_measured_m == pytest.approx(0.297)


@pytest.mark.asyncio
async def test_robot_reset_pick_place_demo_resets_to_idle():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.reset_pick_place_demo(_meta())

    assert result.ok
    assert result.data.status == "idle"
    assert result.data.steps == 0
    assert client.calls[-1][0] == "robot_reset_pick_place_demo"
