"""Unit tests for RobotModule — load / joint positions / navigate (Phase B)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.robot import (
    JointConfig,
    JointPositions,
    JointPositionsSetRequest,
    JointPositionsSetResult,
    RobotArmProfilesResult,
    RobotDrivePhysicsRequest,
    RobotDrivePhysicsResult,
    RobotFrankaPickPlaceRequest,
    RobotFrankaPickPlaceResult,
    RobotFrankaPickPlaceDemoRequest,
    RobotFrankaPickPlaceDemoStatus,
    RobotLoadRequest,
    RobotLoadResult,
    RobotNavigateRequest,
    RobotNavigateResult,
    RobotPickPlaceDemoRequest,
)


def _meta() -> OperationMeta:
    return OperationMeta(request_id="test", module=ModuleName.ROBOT, started_at_epoch_ms=0)


@pytest.mark.asyncio
async def test_robot_list_arm_profiles_returns_curated_support_matrix():
    from tests.conftest import MockIsaacRestClient

    module = RobotModule(MockIsaacRestClient())

    result = await module.list_arm_profiles(_meta())

    assert result.ok
    assert isinstance(result.data, RobotArmProfilesResult)
    assert result.data.count == 41
    assert "franka_panda" in result.data.validated_pick_place_profiles
    assert "ur10" in result.data.candidate_pick_place_profiles
    assert "kawasaki_rs080n" in result.data.candidate_pick_place_profiles
    assert "ur20" in result.data.profile_only_profiles
    franka = next(p for p in result.data.profiles if p.profile_name == "franka_panda")
    assert franka.asset_url.endswith("/Robots/FrankaRobotics/FrankaPanda/franka.usd")


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
    assert all(v == 0.0 for v in result.data.stiffness)


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
    assert result.error_code == "ROBOT_GET_JOINT_CONFIG_ERROR"
    assert "articulation" in (result.message or "").lower()


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
    assert result.error_code == "ROBOT_SET_JOINTS_ERROR"
    assert "articulation" in (result.message or "").lower()


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
    nav_calls = [c for c in client.calls if c[0] == "robot_navigate"]
    assert nav_calls[0][1]["duration_s"] == 2.0


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
    drive_calls = [c for c in client.calls if c[0] == "robot_drive_physics"]
    assert len(drive_calls) == 1
    assert drive_calls[0][1]["waypoints"] == [list(p) for p in waypoints]
    assert drive_calls[0][1]["wheel_radius"] == 0.14


@pytest.mark.asyncio
async def test_robot_drive_physics_server_error_maps():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["robot_drive_physics"] = {"ok": False, "reason": "wheel DOF unresolvable"}
    module = RobotModule(client)
    request = RobotDrivePhysicsRequest(
        prim_path="/World/X",
        waypoints=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
    )
    result = await module.drive_physics(_meta(), request)

    assert not result.ok
    assert result.error_code == "ROBOT_DRIVE_PHYSICS_ERROR"
    assert "DOF" in (result.message or "")


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
    calls = [c for c in client.calls if c[0] == "robot_install_franka_pick_place_playback_demo"]
    assert len(calls) == 1
    assert calls[0][1]["object_initial_position"] == [0.3, 0.35, 0.02575]
    assert calls[0][1]["object_asset_url"].endswith("/Props/KLT_Bin/small_KLT.usd")
    assert calls[0][1]["grid_asset_url"].endswith("/Environments/Grid/default_environment.usd")
    assert calls[0][1]["end_effector_orientation"] == [0.0, 0.0, 1.0, 0.0]


@pytest.mark.asyncio
async def test_robot_install_profile_pick_place_demo_routes_franka_panda():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = RobotModule(client)

    result = await module.install_pick_place_playback_demo(
        _meta(),
        RobotPickPlaceDemoRequest(profile_name="franka_panda"),
    )

    assert result.ok
    assert result.data.profile_name == "franka_panda"
    assert result.data.support_status == "validated_pick_place"
    assert client.calls[-1][0] == "robot_install_franka_pick_place_playback_demo"


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
