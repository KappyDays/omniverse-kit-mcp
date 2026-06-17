"""Unit tests for robot_navigate_path / robot_gripper_control / robot_set_ee_target (Phase G)."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

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
    _ee_pose_frame_candidate_names,
    _franka_pick_place_default_events_dt,
    _franka_pick_place_demo_gripper_progress,
    _franka_pick_place_demo_joint_progress,
    _franka_parallel_gripper_spec,
    _franka_pick_place_offset_recommendation,
    _franka_pick_place_strategy_diagnostics,
    _franka_pick_place_demo_status,
    _franka_pick_place_demo_progress_diagnostics,
    _ensure_franka_pick_place_demo_gripper_ready,
    _initialize_franka_parallel_gripper,
    _lula_solver_joint_names,
    _select_lula_articulation_joint_indices,
    _tick_franka_pick_place_demo,
    _record_franka_pick_place_demo_progress,
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


def test_lula_solver_joint_names_uses_solver_reported_order():
    class Solver:
        def get_joint_names(self):
            return ("joint_a", "joint_b")

    assert _lula_solver_joint_names(Solver()) == ("joint_a", "joint_b")


def test_lula_joint_indices_map_mobile_ur_arm_after_base_joints():
    indices = _select_lula_articulation_joint_indices(
        dof_names=(
            "dummy_base_prismatic_x_joint",
            "dummy_base_prismatic_y_joint",
            "dummy_base_revolute_z_joint",
            "ur_arm_shoulder_pan_joint",
            "ur_arm_shoulder_lift_joint",
            "ur_arm_elbow_joint",
            "ur_arm_wrist_1_joint",
            "ur_arm_wrist_2_joint",
            "ur_arm_wrist_3_joint",
        ),
        solver_joint_names=(
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint",
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint",
        ),
        robot_description="UR5",
        warm_count=9,
    )

    assert indices == (3, 4, 5, 6, 7, 8)


def test_lula_joint_indices_skip_kawasaki_gripper_dofs():
    indices = _select_lula_articulation_joint_indices(
        dof_names=(
            "joint1",
            "joint2",
            "joint3",
            "joint4",
            "joint5",
            "joint6",
            "left_inner_finger_joint",
            "right_inner_finger_joint",
        ),
        solver_joint_names=(),
        robot_description="RS007L",
        warm_count=8,
    )

    assert indices == (0, 1, 2, 3, 4, 5)


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


def test_franka_pick_place_demo_reinitializes_gripper_indices_after_reset():
    class FakeGripper:
        _joint_dof_indicies = None

        def initialize(self, **kwargs):
            self.initialize_kwargs = kwargs
            self._joint_dof_indicies = [7, 8]

    class FakeRobot:
        dof_names = (
            "panda_joint1",
            "panda_joint2",
            "panda_joint3",
            "panda_joint4",
            "panda_joint5",
            "panda_joint6",
            "panda_joint7",
            "panda_finger_joint1",
            "panda_finger_joint2",
        )

        def apply_action(self, action):
            return action

        def get_joint_positions(self):
            return [0.0] * len(self.dof_names)

        def set_joint_positions(self, *_args, **_kwargs):
            return None

    gripper = FakeGripper()
    state = SimpleNamespace(
        robot=FakeRobot(),
        gripper=gripper,
        diagnostics={},
        playback_wrapper_refresh_count=0,
    )

    refreshed = _ensure_franka_pick_place_demo_gripper_ready(state)

    assert refreshed is True
    assert gripper._joint_dof_indicies == [7, 8]
    assert gripper.initialize_kwargs["dof_names"][-2:] == [
        "panda_finger_joint1",
        "panda_finger_joint2",
    ]
    assert state.playback_wrapper_refresh_count == 1
    assert state.diagnostics["playback_wrapper_refresh_count"] == 1


def test_franka_parallel_gripper_joint_position_callback_uses_last_known_cache():
    class FakeGripper:
        def initialize(self, **kwargs):
            self.get_joint_positions_func = kwargs["get_joint_positions_func"]

    class FakeRobot:
        dof_names = ("panda_finger_joint1", "panda_finger_joint2")

        def __init__(self):
            self.positions = [[0.04, 0.04], None]

        def apply_action(self, action):
            return action

        def get_joint_positions(self):
            return self.positions.pop(0) if self.positions else None

        def set_joint_positions(self, *_args, **_kwargs):
            return None

    gripper = FakeGripper()

    _initialize_franka_parallel_gripper(gripper, FakeRobot())

    assert gripper.get_joint_positions_func() == [0.04, 0.04]
    assert gripper.get_joint_positions_func() == [0.04, 0.04]


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


def test_ee_pose_frame_candidates_include_ur_and_kawasaki_aliases():
    assert _ee_pose_frame_candidate_names("tool0") == (
        "tool0",
        "ee_link",
        "wrist_3_link",
        "ur_arm_tool0",
        "ur_arm_ee_link",
        "ur_arm_wrist_3_link",
        "onrobot_rg2_base_link",
        "link5",
        "panda_hand",
        "right_gripper",
    )
    assert _ee_pose_frame_candidate_names("ur_arm_tool0") == (
        "ur_arm_tool0",
        "ur_arm_ee_link",
        "ur_arm_wrist_3_link",
        "tool0",
        "ee_link",
        "wrist_3_link",
        "panda_hand",
        "right_gripper",
    )
    assert _ee_pose_frame_candidate_names("right_gripper") == (
        "right_gripper",
        "panda_rightfinger",
        "fr3_rightfinger",
        "onrobot_rg2_base_link",
        "panda_hand",
        "tool0",
        "ee_link",
    )


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


def test_franka_pick_place_demo_status_uses_cached_bbox_metrics():
    source = inspect.getsource(_franka_pick_place_demo_status)

    assert "_compute_world_bbox" not in source
    assert "state.object_bbox_size" in source
    assert "state.last_object_bbox_center" in source


def test_franka_pick_place_demo_progress_diagnostics_are_bounded():
    state = SimpleNamespace(
        controller_event=0,
        event_tick_counts={},
        event_first_steps={},
        event_last_steps={},
        progress_samples=[],
        initial_object_position=[0.0, 0.0, 0.0],
        object_initial_position=[0.0, 0.0, 0.0],
        object_bbox_size=[0.04, 0.02, 0.04],
        target_position=[0.5, 0.0, 0.0],
        lift_height_tolerance=0.03,
        status="picking",
    )

    _record_franka_pick_place_demo_progress(
        state,
        event=0,
        step=1,
        timeline_time=0.01,
        object_center=[0.0, 0.0, 0.02],
        gripper_progress={
            "gripper_joint_indices": [7, 8],
            "gripper_joint_names": ["panda_finger_joint1", "panda_finger_joint2"],
            "gripper_joint_positions": [0.04, 0.04],
            "gripper_aperture_m": 0.08,
            "action_gripper_joint_positions": [0.02, 0.02],
            "action_gripper_aperture_m": 0.04,
        },
        current_pick=[0.0, 0.0, 0.02],
        end_effector_position=[0.6, 0.0, 0.0],
        joint_progress={
            "joint_delta_from_initial_max_abs": 0.0,
            "action_joint_positions_present": True,
            "action_joint_position_delta_max_abs": 0.10,
            "action_joint_position_count": 7,
        },
    )
    _record_franka_pick_place_demo_progress(
        state,
        event=0,
        step=2,
        timeline_time=0.02,
        object_center=[0.01, 0.0, 0.02],
    )
    state.controller_event = 1
    state.status = "placing"
    _record_franka_pick_place_demo_progress(
        state,
        event=1,
        step=3,
        timeline_time=0.03,
        object_center=[0.1, 0.0, 0.05],
        gripper_progress={
            "gripper_joint_indices": [7, 8],
            "gripper_joint_names": ["panda_finger_joint1", "panda_finger_joint2"],
            "gripper_joint_positions": [0.01, 0.01],
            "gripper_aperture_m": 0.02,
            "action_gripper_joint_positions": [0.0, 0.0],
            "action_gripper_aperture_m": 0.0,
        },
        current_pick=[0.1, 0.0, 0.05],
        end_effector_position=[0.12, 0.0, 0.05],
        joint_progress={
            "joint_delta_from_initial_max_abs": 0.02,
            "joint_delta_from_initial_l2": 0.03,
            "action_joint_positions_present": True,
            "action_joint_position_delta_max_abs": 0.04,
            "action_joint_position_delta_l2": 0.05,
            "action_joint_position_count": 7,
        },
    )

    progress = _franka_pick_place_demo_progress_diagnostics(state)

    assert progress["current_event"] == 1
    assert progress["current_event_ticks"] == 1
    assert progress["event_tick_counts"] == {"0": 2, "1": 1}
    assert progress["event_first_steps"] == {"0": 1, "1": 3}
    assert progress["event_last_steps"] == {"0": 2, "1": 3}
    assert progress["max_joint_delta_from_initial"] == pytest.approx(0.02)
    assert progress["max_action_joint_position_delta"] == pytest.approx(0.10)
    assert progress["action_joint_positions_seen"] is True
    assert progress["end_effector_pose_seen"] is True
    assert progress["min_end_effector_distance_to_pick"] == pytest.approx(0.02)
    assert progress["min_end_effector_distance_to_target"] == pytest.approx(0.10)
    assert progress["min_end_effector_distance_to_object"] == pytest.approx(0.02)
    assert progress["min_end_effector_xy_distance_to_object"] == pytest.approx(0.02)
    assert progress["min_abs_end_effector_z_distance_to_object"] == pytest.approx(0.0)
    assert progress[
        "signed_end_effector_z_distance_at_min_abs_to_object"
    ] == pytest.approx(0.0)
    assert progress["end_effector_object_delta_at_min_distance"] == pytest.approx(
        [0.02, 0.0, 0.0]
    )
    assert progress["end_effector_object_delta_at_min_xy_distance"] == pytest.approx(
        [0.02, 0.0, 0.0]
    )
    assert progress["end_effector_object_delta_at_min_abs_z"] == pytest.approx(
        [0.02, 0.0, 0.0]
    )
    assert progress["approach_window"]["classification"] == (
        "approach_window_inside_bbox_sphere"
    )
    assert progress["approach_window"]["axis_hint"] == "inside_object_bbox_sphere"
    assert progress["approach_window"]["diagnostic_end_effector_offset_delta_m"] is None
    assert progress["approach_window"]["diagnostic_end_effector_offset_delta_source"] is None
    assert progress["approach_window"]["xy_aligned_during_approach"] is True
    assert progress["approach_window"]["z_aligned_during_approach"] is True
    assert (
        progress["approach_window"]["inside_object_bbox_sphere_during_approach"]
        is True
    )
    assert progress["approach_window"]["far_from_object_during_approach"] is False
    assert progress["approach_window"][
        "end_effector_object_delta_at_min_distance"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress["gripper_closed_on_object_width_seen"] is True
    assert progress[
        "min_end_effector_distance_to_object_during_closed_gripper"
    ] == pytest.approx(0.02)
    assert progress[
        "min_end_effector_xy_distance_to_object_during_closed_gripper"
    ] == pytest.approx(0.02)
    assert progress[
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper"
    ] == pytest.approx(0.0)
    assert progress[
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper"
    ] == pytest.approx(0.0)
    assert progress[
        "end_effector_object_delta_at_min_distance_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress[
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress[
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress["max_object_lift_delta_during_closed_gripper"] == pytest.approx(
        0.05
    )
    assert progress["max_object_xy_motion_during_closed_gripper"] == pytest.approx(0.1)
    assert progress["gripper_aperture_seen"] is True
    assert progress["action_gripper_aperture_seen"] is True
    assert progress["min_gripper_aperture_m"] == pytest.approx(0.02)
    assert progress["max_gripper_aperture_m"] == pytest.approx(0.08)
    assert progress["min_action_gripper_aperture_m"] == pytest.approx(0.0)
    assert progress["max_action_gripper_aperture_m"] == pytest.approx(0.04)
    assert progress["min_gripper_object_width_margin_m"] == pytest.approx(-0.02)
    assert progress["min_action_gripper_object_width_margin_m"] == pytest.approx(-0.04)
    assert progress["contact_window"]["classification"] == (
        "closed_gripper_width_window_inside_bbox_sphere"
    )
    assert progress["contact_window"]["axis_hint"] == "inside_object_bbox_sphere"
    assert progress["contact_window"]["diagnostic_end_effector_offset_delta_m"] is None
    assert progress["contact_window"]["diagnostic_end_effector_offset_delta_source"] is None
    assert progress["contact_window"]["object_grasp_width_m"] == pytest.approx(0.04)
    assert progress["contact_window"]["object_half_height_m"] == pytest.approx(0.02)
    assert progress["contact_window"]["object_bbox_half_diagonal_m"] == pytest.approx(
        0.03
    )
    assert progress["contact_window"]["xy_aligned_during_closed_gripper"] is True
    assert progress["contact_window"]["z_aligned_during_closed_gripper"] is True
    assert (
        progress["contact_window"]["inside_object_bbox_sphere_during_closed_gripper"]
        is True
    )
    assert progress["contact_window"]["far_from_object_during_closed_gripper"] is False
    assert progress["contact_window"][
        "closed_gripper_far_distance_threshold_m"
    ] == pytest.approx(0.07)
    assert progress["contact_window"][
        "closed_gripper_distance_over_far_threshold_m"
    ] == pytest.approx(-0.05)
    assert progress["contact_window"][
        "closed_gripper_xy_margin_to_object_half_width_m"
    ] == pytest.approx(0.0)
    assert progress["contact_window"][
        "closed_gripper_distance_margin_to_object_bbox_sphere_m"
    ] == pytest.approx(-0.01)
    assert progress["contact_window"][
        "closed_gripper_z_margin_to_object_half_height_m"
    ] == pytest.approx(-0.02)
    assert progress["contact_window"][
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper"
    ] == pytest.approx(0.0)
    assert progress["contact_window"][
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper"
    ] == pytest.approx(0.0)
    assert progress["contact_window"][
        "end_effector_object_delta_at_min_distance_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress["contact_window"][
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress["contact_window"][
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper"
    ] == pytest.approx([0.02, 0.0, 0.0])
    assert progress["contact_window"][
        "max_object_lift_delta_during_closed_gripper"
    ] == pytest.approx(0.05)
    assert progress["contact_window"][
        "max_object_xy_motion_during_closed_gripper"
    ] == pytest.approx(0.1)
    assert progress["contact_window"]["lift_height_tolerance_m"] == pytest.approx(0.03)
    assert progress["contact_window"][
        "lift_threshold_met_during_closed_gripper"
    ] is True
    assert progress["samples"][0]["controller_event"] == 0
    assert progress["samples"][1]["controller_event"] == 1
    assert progress["samples"][1]["lift_delta"] == pytest.approx(0.05)
    assert progress["samples"][1]["end_effector_position"] == [0.12, 0.0, 0.05]
    assert progress["samples"][1]["end_effector_distance_to_pick"] == pytest.approx(0.02)
    assert progress["samples"][1]["end_effector_distance_to_target"] == pytest.approx(
        (0.38**2 + 0.05**2) ** 0.5
    )
    assert progress["samples"][1]["end_effector_distance_to_object"] == pytest.approx(
        0.02
    )
    assert progress["samples"][1]["end_effector_object_delta"] == pytest.approx(
        [0.02, 0.0, 0.0]
    )
    assert progress["samples"][1]["end_effector_xy_distance_to_object"] == pytest.approx(
        0.02
    )
    assert progress["samples"][1]["end_effector_z_delta_to_object"] == pytest.approx(
        0.0
    )
    assert progress["samples"][1]["end_effector_abs_z_distance_to_object"] == pytest.approx(
        0.0
    )
    assert progress["samples"][1]["gripper_joint_indices"] == [7, 8]
    assert progress["samples"][1]["gripper_aperture_m"] == pytest.approx(0.02)
    assert progress["samples"][1]["action_gripper_aperture_m"] == pytest.approx(0.0)
    assert progress["samples"][1]["gripper_object_width_m"] == pytest.approx(0.04)
    assert progress["samples"][1]["gripper_object_width_margin_m"] == pytest.approx(-0.02)
    assert progress["samples"][1]["gripper_closed_on_object_width"] is True
    assert progress["samples"][1]["action_gripper_object_width_margin_m"] == pytest.approx(
        -0.04
    )
    assert progress["samples"][1]["joint_delta_from_initial_l2"] == pytest.approx(0.03)
    assert progress["samples"][1]["action_joint_position_delta_l2"] == pytest.approx(0.05)
    assert progress["samples"][1]["action_joint_position_count"] == 7
    assert len(progress["samples"]) <= progress["sample_limit"]


def test_franka_pick_place_contact_window_classifies_xy_aligned_without_envelope_contact():
    min_distance = 0.058858394036590496
    min_xy_distance = 0.006803149706765672
    min_abs_z_distance = (min_distance**2 - min_xy_distance**2) ** 0.5
    state = SimpleNamespace(
        controller_event=1,
        event_tick_counts={1: 120},
        event_first_steps={1: 1},
        event_last_steps={1: 120},
        progress_samples=[],
        object_bbox_size=[0.04, 0.04, 0.04],
        max_joint_delta_from_initial=0.0,
        max_action_joint_position_delta=0.0,
        action_joint_positions_seen=False,
        end_effector_pose_seen=True,
        min_end_effector_distance_to_pick=None,
        min_end_effector_distance_to_target=None,
        min_end_effector_distance_to_object=0.041107170889927866,
        gripper_closed_on_object_width_seen=True,
        min_end_effector_distance_to_object_during_closed_gripper=min_distance,
        min_end_effector_xy_distance_to_object_during_closed_gripper=min_xy_distance,
        min_abs_end_effector_z_distance_to_object_during_closed_gripper=min_abs_z_distance,
        signed_end_effector_z_distance_at_min_abs_during_closed_gripper=min_abs_z_distance,
        end_effector_object_delta_at_min_distance_during_closed_gripper=[
            min_xy_distance,
            0.0,
            min_abs_z_distance,
        ],
        end_effector_object_delta_at_min_xy_distance_during_closed_gripper=[
            min_xy_distance,
            0.0,
            min_abs_z_distance,
        ],
        end_effector_object_delta_at_min_abs_z_during_closed_gripper=[
            min_xy_distance,
            0.0,
            min_abs_z_distance,
        ],
        max_object_lift_delta_during_closed_gripper=0.0,
        max_object_xy_motion_during_closed_gripper=0.0,
        lift_height_tolerance=0.02,
        gripper_aperture_seen=True,
        action_gripper_aperture_seen=False,
        min_gripper_aperture_m=0.0,
        max_gripper_aperture_m=0.08,
        min_action_gripper_aperture_m=None,
        max_action_gripper_aperture_m=None,
        min_gripper_object_width_margin_m=-0.04,
        min_action_gripper_object_width_margin_m=None,
    )

    progress = _franka_pick_place_demo_progress_diagnostics(state)

    contact = progress["contact_window"]
    assert contact["classification"] == (
        "closed_gripper_width_window_xy_aligned_outside_bbox_sphere"
    )
    assert contact["axis_hint"] == "z_offset_outside_object_height"
    assert contact["diagnostic_end_effector_offset_delta_m"] == pytest.approx(
        [0.0, 0.0, -(min_abs_z_distance - 0.02)]
    )
    assert (
        contact["diagnostic_end_effector_offset_delta_source"]
        == "z_margin_to_object_half_height"
    )
    assert contact["diagnostic_end_effector_offset_base_m"] == pytest.approx(
        [0.0, 0.0, 0.0]
    )
    assert contact[
        "diagnostic_end_effector_offset_applied_delta_m"
    ] == pytest.approx([0.0, 0.0, -(min_abs_z_distance - 0.02)])
    assert contact["diagnostic_end_effector_offset_next_m"] == pytest.approx(
        [0.0, 0.0, -(min_abs_z_distance - 0.02)]
    )
    assert contact["diagnostic_end_effector_offset_delta_limited"] is False
    assert contact["diagnostic_end_effector_offset_delta_limit_m"] == pytest.approx(
        0.05
    )
    assert contact["object_grasp_width_m"] == pytest.approx(0.04)
    assert contact["object_half_height_m"] == pytest.approx(0.02)
    assert contact["object_bbox_half_diagonal_m"] == pytest.approx(
        (0.04**2 + 0.04**2 + 0.04**2) ** 0.5 / 2.0
    )
    assert contact["xy_aligned_during_closed_gripper"] is True
    assert contact["z_aligned_during_closed_gripper"] is False
    assert contact["inside_object_bbox_sphere_during_closed_gripper"] is False
    assert contact["far_from_object_during_closed_gripper"] is False
    assert contact["closed_gripper_far_distance_threshold_m"] == pytest.approx(
        ((0.04**2 + 0.04**2 + 0.04**2) ** 0.5 / 2.0) + 0.04
    )
    assert contact[
        "closed_gripper_distance_over_far_threshold_m"
    ] == pytest.approx(min_distance - contact["closed_gripper_far_distance_threshold_m"])
    assert contact["closed_gripper_xy_margin_to_object_half_width_m"] == pytest.approx(
        -0.013196850293234328
    )
    assert contact[
        "min_abs_end_effector_z_distance_to_object_during_closed_gripper"
    ] == pytest.approx(min_abs_z_distance)
    assert contact[
        "signed_end_effector_z_distance_at_min_abs_during_closed_gripper"
    ] == pytest.approx(min_abs_z_distance)
    assert contact[
        "closed_gripper_z_margin_to_object_half_height_m"
    ] == pytest.approx(min_abs_z_distance - 0.02)
    assert contact[
        "end_effector_object_delta_at_min_distance_during_closed_gripper"
    ] == pytest.approx([min_xy_distance, 0.0, min_abs_z_distance])
    assert contact[
        "end_effector_object_delta_at_min_xy_distance_during_closed_gripper"
    ] == pytest.approx([min_xy_distance, 0.0, min_abs_z_distance])
    assert contact[
        "end_effector_object_delta_at_min_abs_z_during_closed_gripper"
    ] == pytest.approx([min_xy_distance, 0.0, min_abs_z_distance])
    assert contact[
        "closed_gripper_distance_margin_to_object_bbox_sphere_m"
    ] == pytest.approx(0.024217377874675377)
    assert contact["max_object_lift_delta_during_closed_gripper"] == pytest.approx(0.0)
    assert contact["max_object_xy_motion_during_closed_gripper"] == pytest.approx(0.0)
    assert contact["lift_height_tolerance_m"] == pytest.approx(0.02)
    assert contact["lift_threshold_met_during_closed_gripper"] is False


def test_franka_pick_place_contact_window_classifies_far_closure_axis():
    delta = [-0.16773882508277893, -0.3364330865442753, 0.862981878221035]
    min_distance = sum(value * value for value in delta) ** 0.5
    min_xy_distance = (delta[0] ** 2 + delta[1] ** 2) ** 0.5
    state = SimpleNamespace(
        controller_event=1,
        event_tick_counts={1: 1},
        event_first_steps={1: 1},
        event_last_steps={1: 1},
        progress_samples=[],
        object_bbox_size=[0.04, 0.04, 0.04],
        max_joint_delta_from_initial=0.0,
        max_action_joint_position_delta=0.0,
        action_joint_positions_seen=False,
        end_effector_pose_seen=True,
        min_end_effector_distance_to_pick=None,
        min_end_effector_distance_to_target=None,
        min_end_effector_distance_to_object=min_distance,
        gripper_closed_on_object_width_seen=True,
        min_end_effector_distance_to_object_during_closed_gripper=min_distance,
        min_end_effector_xy_distance_to_object_during_closed_gripper=min_xy_distance,
        min_abs_end_effector_z_distance_to_object_during_closed_gripper=abs(delta[2]),
        signed_end_effector_z_distance_at_min_abs_during_closed_gripper=delta[2],
        end_effector_object_delta_at_min_distance_during_closed_gripper=delta,
        end_effector_object_delta_at_min_xy_distance_during_closed_gripper=delta,
        end_effector_object_delta_at_min_abs_z_during_closed_gripper=delta,
        max_object_lift_delta_during_closed_gripper=0.0,
        max_object_xy_motion_during_closed_gripper=0.0,
        lift_height_tolerance=0.03,
        gripper_aperture_seen=True,
        action_gripper_aperture_seen=False,
        min_gripper_aperture_m=0.0,
        max_gripper_aperture_m=0.08,
        min_action_gripper_aperture_m=None,
        max_action_gripper_aperture_m=None,
        min_gripper_object_width_margin_m=-0.04,
        min_action_gripper_object_width_margin_m=None,
    )

    contact = _franka_pick_place_demo_progress_diagnostics(state)["contact_window"]

    assert contact["classification"] == "closed_gripper_width_window_far_from_object"
    assert contact["axis_hint"] == "z_offset_far_from_object"
    assert contact["diagnostic_end_effector_offset_delta_m"] == pytest.approx(
        [0.0, 0.0, -(abs(delta[2]) - 0.02)]
    )
    assert (
        contact["diagnostic_end_effector_offset_delta_source"]
        == "z_margin_to_object_half_height"
    )
    assert contact["diagnostic_end_effector_offset_base_m"] == pytest.approx(
        [0.0, 0.0, 0.0]
    )
    assert contact[
        "diagnostic_end_effector_offset_applied_delta_m"
    ] == pytest.approx([0.0, 0.0, -0.05])
    assert contact["diagnostic_end_effector_offset_next_m"] == pytest.approx(
        [0.0, 0.0, -0.05]
    )
    assert contact["diagnostic_end_effector_offset_delta_limited"] is True
    assert contact["diagnostic_end_effector_offset_delta_limit_m"] == pytest.approx(
        0.05
    )
    assert contact["xy_aligned_during_closed_gripper"] is False
    assert contact["z_aligned_during_closed_gripper"] is False
    assert contact["inside_object_bbox_sphere_during_closed_gripper"] is False
    assert contact["far_from_object_during_closed_gripper"] is True
    assert contact["closed_gripper_far_distance_threshold_m"] == pytest.approx(
        ((0.04**2 + 0.04**2 + 0.04**2) ** 0.5 / 2.0) + 0.04
    )
    assert contact[
        "closed_gripper_distance_over_far_threshold_m"
    ] == pytest.approx(min_distance - contact["closed_gripper_far_distance_threshold_m"])
    assert contact[
        "end_effector_object_delta_at_min_distance_during_closed_gripper"
    ] == pytest.approx(delta)


def test_franka_pick_place_offset_recommendation_omits_non_finite_delta():
    recommendation = _franka_pick_place_offset_recommendation(
        base_offset=[0.1, 0.2, 0.3],
        delta=[float("nan"), 0.0, -0.02],
    )

    assert recommendation["diagnostic_end_effector_offset_base_m"] == pytest.approx(
        [0.1, 0.2, 0.3]
    )
    assert recommendation["diagnostic_end_effector_offset_applied_delta_m"] is None
    assert recommendation["diagnostic_end_effector_offset_next_m"] is None
    assert recommendation["diagnostic_end_effector_offset_delta_limited"] is False
    assert recommendation["diagnostic_end_effector_offset_delta_limit_m"] == pytest.approx(
        0.05
    )


def test_franka_pick_place_offset_recommendation_ignores_non_finite_base():
    recommendation = _franka_pick_place_offset_recommendation(
        base_offset=[0.1, float("inf"), 0.3],
        delta=[0.0, 0.0, -0.02],
    )

    assert recommendation["diagnostic_end_effector_offset_base_m"] == pytest.approx(
        [0.0, 0.0, 0.0]
    )
    assert recommendation[
        "diagnostic_end_effector_offset_applied_delta_m"
    ] == pytest.approx([0.0, 0.0, -0.02])
    assert recommendation["diagnostic_end_effector_offset_next_m"] == pytest.approx(
        [0.0, 0.0, -0.02]
    )
    assert recommendation["diagnostic_end_effector_offset_delta_limited"] is False
    assert recommendation["diagnostic_end_effector_offset_delta_limit_m"] == pytest.approx(
        0.05
    )


def test_franka_pick_place_demo_joint_progress_summarizes_controller_actions():
    action = SimpleNamespace(
        joint_positions=[0.1, 0.0, 0.4],
        joint_indices=[0, 2, 4],
    )

    progress = _franka_pick_place_demo_joint_progress(
        current_joint_positions=[0.0, 0.0, 0.1, 0.0, 0.2],
        initial_joint_positions=[0.0, 0.0, 0.0, 0.0, 0.0],
        actions=action,
    )

    assert progress["joint_delta_from_initial_max_abs"] == pytest.approx(0.2)
    assert progress["joint_delta_from_initial_l2"] == pytest.approx((0.01 + 0.04) ** 0.5)
    assert progress["action_joint_positions_present"] is True
    assert progress["action_joint_position_count"] == 3
    assert progress["action_joint_indices_present"] is True
    assert progress["action_joint_position_delta_max_abs"] == pytest.approx(0.2)
    assert progress["action_joint_position_delta_l2"] == pytest.approx(
        (0.01 + 0.01 + 0.04) ** 0.5
    )


def test_franka_pick_place_demo_joint_progress_flattens_nested_controller_actions():
    action = SimpleNamespace(
        joint_positions=[[0.1, 0.0, 0.4]],
        joint_indices=[[0, 2, 4]],
    )

    progress = _franka_pick_place_demo_joint_progress(
        current_joint_positions=[0.0, 0.0, 0.1, 0.0, 0.2],
        initial_joint_positions=[[0.0, 0.0, 0.0, 0.0, 0.0]],
        actions=action,
    )

    assert progress["joint_delta_from_initial_max_abs"] == pytest.approx(0.2)
    assert progress["action_joint_positions_present"] is True
    assert progress["action_joint_position_count"] == 3
    assert progress["action_joint_indices_present"] is True
    assert progress["action_joint_position_delta_max_abs"] == pytest.approx(0.2)
    assert progress["action_joint_position_delta_l2"] == pytest.approx(
        (0.01 + 0.01 + 0.04) ** 0.5
    )


def test_franka_pick_place_demo_gripper_progress_tracks_aperture_targets():
    robot = SimpleNamespace(
        dof_names=[
            "panda_joint1",
            "panda_joint2",
            "panda_joint3",
            "panda_joint4",
            "panda_joint5",
            "panda_joint6",
            "panda_joint7",
            "panda_finger_joint1",
            "panda_finger_joint2",
        ]
    )
    action = SimpleNamespace(
        joint_positions=[[0.005, 0.006]],
        joint_indices=[[7, 8]],
    )

    progress = _franka_pick_place_demo_gripper_progress(
        robot=robot,
        current_joint_positions=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.04, 0.035],
        actions=action,
        robot_description="Franka",
    )

    assert progress["gripper_joint_indices"] == [7, 8]
    assert progress["gripper_joint_names"] == [
        "panda_finger_joint1",
        "panda_finger_joint2",
    ]
    assert progress["gripper_joint_index_source"] == "spec_dof_name"
    assert progress["gripper_joint_positions"] == [0.04, 0.035]
    assert progress["gripper_aperture_m"] == pytest.approx(0.075)
    assert progress["action_gripper_joint_positions"] == [0.005, 0.006]
    assert progress["action_gripper_aperture_m"] == pytest.approx(0.011)


def test_franka_pick_place_diagnostics_reference_official_block_geometry():
    diagnostics = _build_franka_pick_place_diagnostics(
        bbox_size=[0.163, 0.029, 0.013],
        picking_position_source="bbox_center",
    )

    assert diagnostics["official_reference"] == "Isaac Sim Franka Cortex Block Stacking"
    assert diagnostics["official_block_size_m"] == pytest.approx(0.0515)
    assert any("flatter" in warning for warning in diagnostics["warnings"])
    assert any("picking_position" in hint for hint in diagnostics["hints"])


def test_franka_pick_place_strategy_diagnostics_records_requested_geometry():
    diagnostics = _franka_pick_place_strategy_diagnostics(
        picking_position_source="explicit",
        picking_position=(0.3, 0.35, 0.02),
        object_initial_position=(0.3, 0.35, 0.02575),
        target_position=(0.45, -0.35, 0.02575),
        end_effector_initial_height=0.3,
        end_effector_initial_height_source="official_default",
        end_effector_offset=(0.0, 0.0, -0.02),
        end_effector_orientation=(0.0, 1.0, 0.0, 0.0),
        events_dt=(0.008, 0.005),
        max_steps=1000,
        reset_on_play=True,
    )

    assert diagnostics == {
        "picking_position_source": "explicit",
        "picking_position": [0.3, 0.35, 0.02],
        "object_initial_position": [0.3, 0.35, 0.02575],
        "target_position": [0.45, -0.35, 0.02575],
        "end_effector_initial_height": 0.3,
        "end_effector_initial_height_source": "official_default",
        "end_effector_offset": [0.0, 0.0, -0.02],
        "end_effector_orientation": [0.0, 1.0, 0.0, 0.0],
        "events_dt": [0.008, 0.005],
        "max_steps": 1000,
        "reset_on_play": True,
    }


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
