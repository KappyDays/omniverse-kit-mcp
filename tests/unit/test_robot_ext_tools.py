"""Unit tests for robot_navigate_path / robot_gripper_control / robot_set_ee_target (Phase G)."""

from __future__ import annotations

import inspect

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
    RobotService,
    _assert_franka_family_pick_place_robot,
    _build_franka_pick_place_diagnostics,
    _create_franka_parallel_gripper,
    _create_franka_pick_place_controller,
    _ensure_initialized,
    _evaluate_pick_object_fit,
    _franka_pick_place_default_events_dt,
    _franka_parallel_gripper_spec,
    _tick_franka_pick_place_demo,
    _resolve_official_franka_pick_place_classes,
    _resolve_franka_pick_place_hover_height,
    _resolve_lula_config,
)
from omni.mycompany.validation_api.models.robot import (
    RobotFrankaPickPlaceDemoInstallRequestModel,
    RobotFrankaPickPlaceRequestModel,
)
from omni.mycompany.validation_api.services.job_service import JobService


def _meta() -> OperationMeta:
    return OperationMeta(request_id="t", module=ModuleName.ROBOT, started_at_epoch_ms=0)


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_robot_ext_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    assert "robot_list_arm_profiles" in names
    assert "robot_navigate_path" in names
    assert "robot_gripper_control" in names
    assert "robot_set_ee_target" in names
    assert "robot_get_ee_pose" in names
    assert "robot_run_franka_pick_place" in names
    assert "robot_install_franka_pick_place_playback_demo" in names
    assert "robot_install_pick_place_playback_demo" in names
    assert "robot_reset_pick_place_demo" in names
    assert "robot_get_pick_place_demo_status" in names


def test_robot_service_load_uses_payload_command():
    source = inspect.getsource(RobotService.load)

    assert "CreatePayloadCommand" in source
    assert "CreateReferenceCommand" not in source
    assert "instanceable=False" in source
    assert "_active_job_ids" in source
    assert "_stop_timeline_if_playing" in source


def test_job_service_active_job_ids_filters_non_terminal_jobs():
    service = JobService()
    service._jobs = {
        "pending-job": {"status": "pending"},
        "running-job": {"status": "running"},
        "done-job": {"status": "done"},
        "error-job": {"status": "error"},
        "canceled-job": {"status": "canceled"},
    }

    assert service.active_job_ids() == ("pending-job", "running-job")


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


def test_franka_family_pick_place_guard_accepts_franka_and_fr3_only():
    _assert_franka_family_pick_place_robot("Franka", endpoint="robot/franka_pick_place")
    _assert_franka_family_pick_place_robot("FR3", endpoint="franka_pick_place_demo")
    _assert_franka_family_pick_place_robot("fr3", endpoint="franka_pick_place_demo")

    with pytest.raises(ValueError, match=r"Franka', 'FR3"):
        _assert_franka_family_pick_place_robot("UR10", endpoint="franka_pick_place_demo")


def test_franka_parallel_gripper_spec_switches_for_fr3():
    panda = _franka_parallel_gripper_spec("Franka")
    assert panda.end_effector_prim_name == "panda_rightfinger"
    assert panda.joint_prim_names == ("panda_finger_joint1", "panda_finger_joint2")

    fr3 = _franka_parallel_gripper_spec("FR3")
    assert fr3.end_effector_prim_name == "fr3_rightfinger"
    assert fr3.joint_prim_names == ("fr3_finger_joint1", "fr3_finger_joint2")


def test_fr3_parallel_gripper_uses_absolute_open_close_targets():
    seen: list[dict[str, object]] = []

    class FakeGripper:
        def __init__(self, **kwargs):
            seen.append(kwargs)

        def initialize(self, **kwargs):
            seen.append({"initialize": kwargs})

    class FakeClasses:
        parallel_gripper = FakeGripper

    class FakeRobot:
        dof_names = ("fr3_finger_joint1", "fr3_finger_joint2")

        def apply_action(self, action):
            return action

        def get_joint_positions(self):
            return [0.05, 0.05]

        def set_joint_positions(self, *args, **kwargs):
            return None

    _create_franka_parallel_gripper(
        FakeClasses,
        FakeRobot(),
        "/World/FR3",
        robot_description="FR3",
    )

    assert seen[0]["joint_prim_names"] == ["fr3_finger_joint1", "fr3_finger_joint2"]
    assert seen[0]["action_deltas"] is None


def test_panda_parallel_gripper_keeps_delta_open_close_targets():
    seen: list[dict[str, object]] = []

    class FakeGripper:
        def __init__(self, **kwargs):
            seen.append(kwargs)

        def initialize(self, **kwargs):
            seen.append({"initialize": kwargs})

    class FakeClasses:
        parallel_gripper = FakeGripper

    class FakeRobot:
        dof_names = ("panda_finger_joint1", "panda_finger_joint2")

        def apply_action(self, action):
            return action

        def get_joint_positions(self):
            return [0.05, 0.05]

        def set_joint_positions(self, *args, **kwargs):
            return None

    _create_franka_parallel_gripper(
        FakeClasses,
        FakeRobot(),
        "/World/Franka",
        robot_description="Franka",
    )

    assert seen[0]["joint_prim_names"] == ["panda_finger_joint1", "panda_finger_joint2"]
    assert seen[0]["action_deltas"] is not None


def test_franka_pick_place_controller_uses_official_controller_for_panda():
    calls: list[dict[str, object]] = []

    class FakeClasses:
        @staticmethod
        def pick_place_controller(**kwargs):
            calls.append(kwargs)
            return {"controller": "official", **kwargs}

    result = _create_franka_pick_place_controller(
        classes=FakeClasses,
        robot=object(),
        gripper=object(),
        hover_height=0.4,
        events_dt=[0.1],
        robot_description="Franka",
    )

    assert result["controller"] == "official"
    assert calls[0]["end_effector_initial_height"] == pytest.approx(0.4)


def test_franka_pick_place_controller_routes_fr3_to_profile_aware_factory(monkeypatch):
    seen: dict[str, object] = {}

    def fake_fr3_factory(**kwargs):
        seen.update(kwargs)
        return {"controller": "fr3"}

    monkeypatch.setattr(
        "omni.mycompany.validation_api.services.robot_service._create_fr3_pick_place_controller",
        fake_fr3_factory,
    )

    result = _create_franka_pick_place_controller(
        classes=object(),
        robot="robot",
        gripper="gripper",
        hover_height=0.5,
        events_dt=None,
        robot_description="FR3",
    )

    assert result == {"controller": "fr3"}
    assert seen["robot"] == "robot"
    assert seen["gripper"] == "gripper"
    assert seen["robot_description"] == "FR3"


def test_franka_pick_place_default_events_dt_completes_within_playback_budget():
    events_dt = _franka_pick_place_default_events_dt()
    expected_ticks = sum(int((1.0 + dt - 1e-9) // dt) for dt in events_dt)

    assert events_dt == [0.008, 0.005, 1.0, 0.1, 0.05, 0.05, 0.0025, 1.0, 0.008, 0.08]
    assert expected_ticks < 1800


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


def test_franka_pick_place_demo_install_model_defaults_are_replay_safe():
    model = RobotFrankaPickPlaceDemoInstallRequestModel()

    assert model.robot_prim_path == "/World/Franka"
    assert model.object_prim_path == "/World/PickCube"
    assert model.create_demo_scene is True
    assert model.reset_on_play is True
    assert model.object_size == pytest.approx(0.04)
    assert model.max_grasp_width_m == pytest.approx(0.08)
    assert model.fit_clearance_m == pytest.approx(0.005)


def test_franka_pick_place_object_fit_accepts_default_cube():
    fit = _evaluate_pick_object_fit(
        [0.04, 0.04, 0.04],
        max_grasp_width_m=0.08,
        fit_clearance_m=0.005,
    )

    assert fit["ok"] is True
    assert fit["axis"] == "x"
    assert fit["limit_m"] == pytest.approx(0.075)
    assert fit["measured_m"] == pytest.approx(0.04)


def test_franka_pick_place_object_fit_rejects_oversized_catalog_box():
    fit = _evaluate_pick_object_fit(
        [0.198, 0.297, 0.146],
        max_grasp_width_m=0.08,
        fit_clearance_m=0.005,
    )

    assert fit["ok"] is False
    assert "exceeds gripper opening" in fit["reason"]
    assert fit["axis"] == "y"
    assert fit["limit_m"] == pytest.approx(0.075)
    assert fit["measured_m"] == pytest.approx(0.297)


def test_franka_pick_place_demo_scene_defaults_to_native_fit_cube():
    from omni.mycompany.validation_api.services.robot_service import (
        _ensure_franka_pick_place_demo_scene,
    )

    source = inspect.getsource(_ensure_franka_pick_place_demo_scene)

    assert "_define_pick_place_demo_cube" in source
    assert "AddReference(str(object_asset_url))" in source
    assert "object_asset_url is required" not in source


def test_franka_pick_place_demo_timeout_refreshes_bbox_metrics():
    source = inspect.getsource(_tick_franka_pick_place_demo)

    assert "if state.steps >= state.max_steps" in source
    assert "_refresh_franka_pick_place_demo_metrics(state)" in source


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
