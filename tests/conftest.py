"""Shared test fixtures and mock clients."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

# Add kkr-extensions directory to sys.path so `omni.mycompany.validation_api`
# is importable via Python namespace packages (PEP 420). MUST come before any
# submodule stubbing — otherwise standalone `omni` ModuleType blocks the namespace.
_ext_root = Path(__file__).parent.parent / "kkr-extensions" / "omni.mycompany.validation_api"
if str(_ext_root) not in sys.path:
    sys.path.insert(0, str(_ext_root))

# Stub Kit-only leaf modules (carb, omni.ext, etc.) that the Extension imports
# at top level. Tests mock these further as needed.
import types as _types


def _stub(name: str, **attrs):
    if name in sys.modules:
        mod = sys.modules[name]
    else:
        mod = _types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        setattr(mod, k, v)
    # Ensure parent namespace package is imported so setattr binds correctly
    if "." in name:
        parent_name, leaf = name.rsplit(".", 1)
        if parent_name not in sys.modules:
            __import__(parent_name)  # triggers implicit namespace package creation
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, leaf, mod)
    return mod


class _IExtStub:  # minimal base so `class X(omni.ext.IExt)` works at import time
    def on_startup(self, ext_id): ...
    def on_shutdown(self): ...


_stub("carb", log_warn=lambda *a, **k: None, log_info=lambda *a, **k: None,
      log_error=lambda *a, **k: None)
_stub("carb.settings", get_settings=lambda: _types.SimpleNamespace(
    set=lambda *a, **k: None, get=lambda *a, **k: None))
_stub("omni.ext", IExt=_IExtStub)
_stub("omni.ui")
_stub("omni.usd", get_context=lambda: None)
_stub("omni.timeline", get_timeline_interface=lambda: None)
_stub("omni.kit")
_stub("omni.kit.app", get_app=lambda: None)
_stub("omni.kit.commands", execute=lambda *a, **k: None)
_stub("omni.kit.notification_manager",
      post_notification=lambda *a, **k: None,
      NotificationStatus=_types.SimpleNamespace(WARNING="warning", INFO="info"))
_stub("omni.services")
_stub("omni.services.core")
_stub("omni.graph")
_stub("omni.graph.core")
_stub("omni.graph.action")
_stub("pxr")
_stub("pxr.UsdGeom", Imageable=lambda prim: _types.SimpleNamespace(
    MakeInvisible=lambda: None, MakeVisible=lambda: None))
_stub("pxr.Gf")
_stub("pxr.Usd")
_stub("pxr.Sdf")
_stub("isaacsim")
_stub("isaacsim.core")
_stub("isaacsim.core.nodes")
_stub("isaacsim.wheeled_robots")
_stub("isaacsim.wheeled_robots.controllers")

from omniverse_kit_mcp.types.common import ModuleName, OperationMeta
from omniverse_kit_mcp.types.extension import ExtensionState
from omniverse_kit_mcp.types.lakehouse import LakehouseQueryResult, LakehouseRow
from omniverse_kit_mcp.types.stage import StageSnapshot, UsdPropertyValue
from omniverse_kit_mcp.types.viewport import ImageArtifact, SSIMComparisonResult

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def snapshot_before_raw() -> dict:
    return json.loads((FIXTURES / "stage" / "snapshot_before.json").read_text(encoding="utf-8"))


@pytest.fixture
def snapshot_after_raw() -> dict:
    return json.loads((FIXTURES / "stage" / "snapshot_after_add_cube.json").read_text(encoding="utf-8"))


@pytest.fixture
def lakehouse_query_result_raw() -> dict:
    return json.loads((FIXTURES / "lakehouse" / "query_result_single_row.json").read_text(encoding="utf-8"))


@pytest.fixture
def sync_add_cube_scenario_raw() -> dict:
    return yaml.safe_load((FIXTURES / "scenarios" / "valid" / "sync_add_cube.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def operation_meta() -> OperationMeta:
    return OperationMeta(
        request_id="test-req-001",
        module=ModuleName.STAGE,
        started_at_epoch_ms=1000000,
    )


# --- Mock Clients ---


@dataclass
class MockIsaacRestClient:
    """Mock Isaac REST client for unit tests."""

    responses: dict[str, Any] = field(default_factory=dict)
    calls: list[tuple[str, dict]] = field(default_factory=list)

    async def health(self) -> dict:
        return self.responses.get("health", {"ok": True})

    async def stage_snapshot(self, capture_filter: dict) -> dict:
        self.calls.append(("stage_snapshot", capture_filter))
        return self.responses.get("stage_snapshot", {"prims": {}, "root_layer_identifier": "", "stage_identifier": ""})

    async def stage_assert_prim_exists(self, assertion: dict) -> dict:
        self.calls.append(("stage_assert_prim_exists", assertion))
        return self.responses.get("stage_assert_prim_exists", {"passed": True, "failures": [], "checked_count": 1})

    async def stage_assert_property(self, assertion: dict) -> dict:
        self.calls.append(("stage_assert_property", assertion))
        return self.responses.get("stage_assert_property", {"passed": True, "failures": [], "checked_count": 1})

    async def stage_compute_world_bbox(self, request: dict) -> dict:
        self.calls.append(("stage_compute_world_bbox", request))
        sequence = self.responses.get("stage_compute_world_bbox_sequence")
        if sequence:
            return sequence.pop(0)
        return self.responses.get("stage_compute_world_bbox", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "min": [0.0, 0.0, 0.0],
            "max": [1.0, 1.0, 1.0],
            "center": [0.5, 0.5, 0.5],
            "size": [1.0, 1.0, 1.0],
            "world_translate": [0.0, 0.0, 0.0],
            "world_orient_wxyz": [1.0, 0.0, 0.0, 0.0],
            "is_empty": False,
        })

    async def viewport_capture(self, request: dict) -> dict:
        self.calls.append(("viewport_capture", request))
        return self.responses.get("viewport_capture", {"artifact_id": "test_img", "path": "/tmp/test.png", "width": 1280, "height": 720, "sha256": "abc", "created_at_epoch_ms": 0})

    async def viewport_compare_ssim(self, request: dict) -> dict:
        self.calls.append(("viewport_compare_ssim", request))
        return self.responses.get("viewport_compare_ssim", {"score": 0.99, "passed": True})

    async def extension_state(self) -> dict:
        self.calls.append(("extension_state", {}))
        return self.responses.get("extension_state", {"enabled": True, "busy": False, "last_operation": None, "last_error": None, "reset_token": None, "state_version": 0})

    async def extension_trigger(self, request: dict) -> dict:
        self.calls.append(("extension_trigger", request))
        return self.responses.get("extension_trigger", {"enabled": True, "busy": False, "last_operation": request.get("operation"), "last_error": None, "reset_token": None, "state_version": 1})

    async def extension_reset(self, request: dict) -> dict:
        self.calls.append(("extension_reset", request))
        return self.responses.get("extension_reset", {"enabled": True, "busy": False, "last_operation": None, "last_error": None, "reset_token": None, "state_version": 0})

    # Stage WRITE operations (backed by SimulationModule in production)

    async def stage_load_usd(self, request: dict) -> dict:
        self.calls.append(("stage_load_usd", request))
        return self.responses.get(
            "stage_load_usd",
            {"ok": True, "prim_path": request.get("prim_path", ""), "type_name": "Xform", "has_children": True},
        )

    async def stage_set_property(self, request: dict) -> dict:
        self.calls.append(("stage_set_property", request))
        return self.responses.get(
            "stage_set_property",
            {"ok": True, "prim_path": request.get("prim_path", ""), "property_name": request.get("property_name", ""), "value": request.get("value")},
        )

    async def stage_set_semantic_label(self, request: dict) -> dict:
        self.calls.append(("stage_set_semantic_label", request))
        return self.responses.get(
            "stage_set_semantic_label",
            {"ok": True, "prim_path": request.get("prim_path", ""), "label_type": request.get("label_type", "class"), "label_class": request.get("label_class", ""), "applied_schemas": ["SemanticsLabelsAPI:class"]},
        )

    async def stage_create_prim(self, request: dict) -> dict:
        self.calls.append(("stage_create_prim", request))
        return self.responses.get(
            "stage_create_prim",
            {"ok": True, "prim_path": request.get("prim_path", ""), "prim_type": request.get("prim_type", "Xform")},
        )

    async def stage_delete_prim(self, prim_path: str) -> dict:
        self.calls.append(("stage_delete_prim", {"prim_path": prim_path}))
        return self.responses.get("stage_delete_prim", {"ok": True, "prim_path": prim_path})

    # Simulation timeline

    async def simulation_play(self) -> dict:
        self.calls.append(("simulation_play", {}))
        return self.responses.get(
            "simulation_play",
            {"is_playing": True, "is_stopped": False, "current_time": 0.0, "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0},
        )

    async def simulation_pause(self) -> dict:
        self.calls.append(("simulation_pause", {}))
        return self.responses.get(
            "simulation_pause",
            {"is_playing": False, "is_stopped": False, "current_time": 1.0, "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0},
        )

    async def simulation_stop(self) -> dict:
        self.calls.append(("simulation_stop", {}))
        return self.responses.get(
            "simulation_stop",
            {"is_playing": False, "is_stopped": True, "current_time": 0.0, "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0},
        )

    async def simulation_status(self) -> dict:
        self.calls.append(("simulation_status", {}))
        return self.responses.get(
            "simulation_status",
            {"is_playing": False, "is_stopped": True, "current_time": 0.0, "start_time": 0.0, "end_time": 10.0, "time_codes_per_second": 24.0},
        )

    # Simulation (Phase G)

    async def simulation_step(self, request: dict) -> dict:
        self.calls.append(("simulation_step", request))
        frames = int(request.get("frames", 1))
        return self.responses.get("simulation_step", {
            "ok": True,
            "is_playing": False,
            "is_stopped": False,
            "current_time": frames / 60.0,
            "start_time": 0.0,
            "end_time": 10.0,
            "time_codes_per_second": 60.0,
            "frames": frames,
            "advance_mode": "forward_one_frame",
            "was_playing": False,
        })

    async def simulation_step_observe(self, request: dict) -> dict:
        self.calls.append(("simulation_step_observe", request))
        frames = int(request.get("frames", 1))
        return self.responses.get("simulation_step_observe", {
            "ok": True,
            "is_playing": False,
            "is_stopped": False,
            "current_time": frames / 60.0,
            "start_time": 0.0,
            "end_time": 10.0,
            "time_codes_per_second": 60.0,
            "frames": frames,
            "advance_mode": "forward_one_frame",
            "was_playing": False,
            "prim_states": [
                {
                    "prim_path": path,
                    "position": [0.1, 0.2, 0.3],
                    "orientation": [1.0, 0.0, 0.0, 0.0],
                    "linear_velocity": [0.0, 0.0, 0.0],
                    "angular_velocity": [0.0, 0.0, 0.0],
                    "has_rigid_body": True,
                    "source": "mock",
                    "error": None,
                }
                for path in request.get("observe_prims", [])
            ],
            "joint_states": [
                {
                    "prim_path": path,
                    "positions": [0.0] * 7,
                    "dof_names": [f"panda_joint{i + 1}" for i in range(7)],
                    "source": "mock",
                    "error": None,
                }
                for path in request.get("observe_joints", [])
            ],
            "ee_states": [
                {
                    "prim_path": item.get("prim_path", ""),
                    "end_effector_frame": item.get("end_effector_frame") or "panda_hand",
                    "position": [0.5, 0.0, 0.4],
                    "orientation": [1.0, 0.0, 0.0, 0.0],
                    "source": "mock",
                    "error": None,
                }
                for item in request.get("observe_ee", [])
            ],
        })

    async def simulation_wait_until(self, request: dict) -> dict:
        self.calls.append(("simulation_wait_until", request))
        until = float(request.get("until_time", 0.0))
        return self.responses.get("simulation_wait_until", {
            "ok": True,
            "is_playing": True,
            "is_stopped": False,
            "current_time": until,
            "start_time": 0.0,
            "end_time": 100.0,
            "time_codes_per_second": 60.0,
            "until_time": until,
            "reached": True,
            "timed_out": False,
            "elapsed_s": until,
            "frames_waited": int(until * 60),
        })

    async def simulation_set_time(self, request: dict) -> dict:
        self.calls.append(("simulation_set_time", request))
        target = float(request.get("time_seconds", 0.0))
        return self.responses.get("simulation_set_time", {
            "ok": True,
            "is_playing": False,
            "is_stopped": False,
            "current_time": target,
            "start_time": 0.0,
            "end_time": 10.0,
            "time_codes_per_second": 60.0,
            "requested_time": target,
            "previous_time": 0.0,
        })

    # Robot (Phase B)

    async def robot_load(self, request: dict) -> dict:
        self.calls.append(("robot_load", request))
        return self.responses.get(
            "robot_load",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "usd_url": request.get("usd_url", ""),
                "type_name": "Xform",
                "has_articulation": True,
            },
        )

    async def robot_get_joint_positions(self, prim_path: str) -> dict:
        self.calls.append(("robot_get_joint_positions", {"prim_path": prim_path}))
        return self.responses.get(
            "robot_get_joint_positions",
            {"ok": True, "prim_path": prim_path, "positions": [0.0] * 7},
        )

    async def robot_get_joint_config(self, prim_path: str) -> dict:
        self.calls.append(("robot_get_joint_config", {"prim_path": prim_path}))
        return self.responses.get(
            "robot_get_joint_config",
            {
                "ok": True,
                "prim_path": prim_path,
                "source": "dof_properties",
                "dof_count": 7,
                "dof_names": [f"panda_joint{i + 1}" for i in range(7)],
                "joint_types": ["RevoluteJoint"] * 7,
                "stiffness": [400.0] * 7,
                "damping": [40.0] * 7,
                "max_force": [87.0] * 7,
                "lower_limits": [-2.9, -1.8, -2.9, -3.0, -2.9, -0.1, -2.9],
                "upper_limits": [2.9, 1.8, 2.9, 0.0, 2.9, 3.7, 2.9],
                "max_velocity": [2.0] * 7,
            },
        )

    async def robot_set_joint_positions(self, request: dict) -> dict:
        self.calls.append(("robot_set_joint_positions", request))
        return self.responses.get(
            "robot_set_joint_positions",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "positions_count": len(request.get("positions", [])),
            },
        )

    async def robot_navigate(self, request: dict) -> dict:
        self.calls.append(("robot_navigate", request))
        return self.responses.get(
            "robot_navigate",
            {
                "ok": True,
                "job_id": "job_test_0001",
                "prim_path": request.get("prim_path", ""),
                "target": request.get("target", [0.0, 0.0, 0.0]),
            },
        )

    # Robot (Phase G)

    async def robot_navigate_path(self, request: dict) -> dict:
        self.calls.append(("robot_navigate_path", request))
        points = request.get("points") or []
        return self.responses.get(
            "robot_navigate_path",
            {
                "ok": True,
                "job_id": "job_test_path_0001",
                "prim_path": request.get("prim_path", ""),
                "num_waypoints": len(points),
                "duration_s": float(request.get("duration_s", 5.0)),
            },
        )

    async def robot_gripper_control(self, request: dict) -> dict:
        self.calls.append(("robot_gripper_control", request))
        action = request.get("action", "open")
        target = request.get("target")
        if action == "open":
            value = 0.04
        elif action == "close":
            value = 0.0
        else:
            value = float(target) if target is not None else 0.0
        return self.responses.get(
            "robot_gripper_control",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "action": action,
                "target_value": value,
                "gripper_joint_names": ["panda_finger_joint1", "panda_finger_joint2"],
                "gripper_joint_indices": [7, 8],
                "dof_count": 9,
            },
        )

    async def robot_set_ee_target(self, request: dict) -> dict:
        self.calls.append(("robot_set_ee_target", request))
        pose = request.get("target_pose") or [0.0] * 7
        return self.responses.get(
            "robot_set_ee_target",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "target_pose": list(pose),
                "robot_description": request.get("robot_description", "Franka"),
                "end_effector_frame": request.get("end_effector_frame") or "right_gripper",
                "lula_import_path": "isaacsim.robot_motion",
                "ik_success": True,
                "solution": [0.0, -0.5, 0.0, -2.0, 0.0, 1.5, 0.8],
            },
        )

    async def robot_get_ee_pose(
        self,
        prim_path: str,
        end_effector_frame: str | None = None,
    ) -> dict:
        self.calls.append((
            "robot_get_ee_pose",
            {"prim_path": prim_path, "end_effector_frame": end_effector_frame},
        ))
        return self.responses.get(
            "robot_get_ee_pose",
            {
                "ok": True,
                "prim_path": prim_path,
                "end_effector_frame": end_effector_frame or "panda_hand",
                "position": [0.5, 0.0, 0.4],
                "orientation": [1.0, 0.0, 0.0, 0.0],
                "source": "mock",
            },
        )

    # Jobs (Phase B)

    async def job_status(self, job_id: str) -> dict:
        self.calls.append(("job_status", {"job_id": job_id}))
        default = {
            "job_id": job_id,
            "status": "done",
            "progress": 1.0,
            "result": {"final_position": [1.0, 0.0, 0.0], "steps": 60, "elapsed_s": 1.0},
            "error": None,
            "created_at_epoch_ms": 1000,
            "updated_at_epoch_ms": 2000,
        }
        return self.responses.get("job_status", default)

    async def job_cancel(self, job_id: str) -> dict:
        self.calls.append(("job_cancel", {"job_id": job_id}))
        default = {
            "job_id": job_id,
            "status": "canceled",
            "progress": 0.5,
            "result": None,
            "error": "Job canceled by user",
            "created_at_epoch_ms": 1000,
            "updated_at_epoch_ms": 2000,
        }
        return self.responses.get("job_cancel", default)

    # Character (Phase C)

    async def character_load(self, request: dict) -> dict:
        self.calls.append(("character_load", request))
        return self.responses.get(
            "character_load",
            {
                "ok": True,
                "prim_path": request.get("prim_path") or "/World/Characters/Biped_Setup",
                "skel_root_path": "/World/Characters/Biped_Setup/SkelRoot",
                "sanitized_prim_path": request.get("prim_path") or "/World/Characters/Biped_Setup",
                "has_skeleton": True,
                "anim_graph_bound": True,
            },
        )

    async def character_play_animation(self, request: dict) -> dict:
        self.calls.append(("character_play_animation", request))
        return self.responses.get(
            "character_play_animation",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "action": request.get("animation_name", "Idle"),
                "speed": float(request.get("speed", 1.0)),
                "bound_graph": request.get("prim_path", "") + "/SkelRoot",
            },
        )

    async def character_set_position(self, request: dict) -> dict:
        self.calls.append(("character_set_position", request))
        return self.responses.get(
            "character_set_position",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "position": request.get("position", [0.0, 0.0, 0.0]),
                "orientation": request.get("orientation") or [1.0, 0.0, 0.0, 0.0],
            },
        )

    async def character_stop_animation(self, request: dict) -> dict:
        self.calls.append(("character_stop_animation", request))
        return self.responses.get(
            "character_stop_animation",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "action": "Idle",
                "speed": 0.0,
            },
        )

    async def character_navigate(self, request: dict) -> dict:
        self.calls.append(("character_navigate", request))
        return self.responses.get(
            "character_navigate",
            {
                "ok": True,
                "job_id": "job_char_0001",
                "prim_path": request.get("prim_path", ""),
                "target": request.get("target", [0.0, 0.0, 0.0]),
            },
        )

    async def character_get_state(self, prim_path: str) -> dict:
        self.calls.append(("character_get_state", {"prim_path": prim_path}))
        return self.responses.get(
            "character_get_state",
            {
                "ok": True,
                "prim_path": prim_path,
                "position": [0.0, 0.0, 0.0],
                "rotation": [1.0, 0.0, 0.0, 0.0],
                "action": "Idle",
                "is_navigating": False,
            },
        )

    # Character (Phase G)

    async def character_play_animation_variant(self, request: dict) -> dict:
        self.calls.append(("character_play_animation_variant", request))
        variant = request.get("variant", "Idle")
        # Derive the base action from the variant prefix (same logic as Extension)
        for base in ("Sit", "Walk", "Run", "Idle"):
            if variant == base or variant.startswith(base):
                base_action = base
                tail = variant[len(base):].lower() or ""
                break
        else:
            base_action = variant
            tail = ""
        variables_set: dict = {"Action": base_action}
        if tail:
            variables_set[f"{base_action.lower()}_style"] = tail
        if base_action in ("Walk", "Run"):
            variables_set["Walk"] = float(request.get("speed", 1.0))
        return self.responses.get(
            "character_play_animation_variant",
            {
                "ok": True,
                "prim_path": request.get("prim_path", ""),
                "variant": variant,
                "base_action": base_action,
                "speed": float(request.get("speed", 1.0)),
                "variables_set": variables_set,
                "bound_graph": request.get("prim_path", "") + "/SkelRoot",
            },
        )

    async def character_load_crowd(self, request: dict) -> dict:
        self.calls.append(("character_load_crowd", request))
        count = int(request.get("count", 0))
        base = request.get("base_name", "Crowd")
        spacing = float(request.get("spacing", 2.0))
        center = request.get("center") or [0.0, 0.0, 0.0]
        layout = request.get("layout", "grid")
        loaded = []
        import math
        cols = max(1, int(math.ceil(math.sqrt(count)))) if layout == "grid" else count
        for i in range(count):
            if layout == "grid":
                row = i // cols
                col = i % cols
                x = center[0] + (col - (cols - 1) / 2.0) * spacing
                y = center[1] + (row - (cols - 1) / 2.0) * spacing
            elif layout == "line":
                x = center[0] + (i - (count - 1) / 2.0) * spacing
                y = center[1]
            else:
                x = center[0]
                y = center[1]
            loaded.append({
                "index": i,
                "prim_path": f"/World/Characters/{base}_{i:02d}",
                "position": [x, y, center[2]],
            })
        return self.responses.get(
            "character_load_crowd",
            {
                "ok": count > 0,
                "count": count,
                "success_count": count,
                "layout": layout,
                "spacing": spacing,
                "base_name": base,
                "center": list(center),
                "usd_url": request.get("usd_url") or "https://example/Biped_Setup.usd",
                "loaded": loaded,
            },
        )

    # File / Selection / Camera (Phase B+)

    async def stage_save(self, path: str | None = None) -> dict:
        self.calls.append(("stage_save", {"path": path}))
        return self.responses.get("stage_save", {"ok": True, "path": path or "inline", "mode": "save_as" if path else "save"})

    async def stage_open(self, url: str) -> dict:
        self.calls.append(("stage_open", {"url": url}))
        return self.responses.get("stage_open", {"ok": True, "url": url, "root_layer": url})

    async def stage_new(self) -> dict:
        self.calls.append(("stage_new", {}))
        return self.responses.get("stage_new", {"ok": True, "root_layer": "anon:new"})

    async def stage_get_selection(self) -> dict:
        self.calls.append(("stage_get_selection", {}))
        return self.responses.get("stage_get_selection", {"ok": True, "selected_prim_paths": [], "count": 0})

    async def stage_set_selection(self, prim_paths: list, expand_in_stage: bool = True) -> dict:
        self.calls.append(("stage_set_selection", {"prim_paths": prim_paths, "expand_in_stage": expand_in_stage}))
        return self.responses.get("stage_set_selection", {"ok": True, "selected_prim_paths": prim_paths, "count": len(prim_paths)})

    async def viewport_set_active_camera(self, camera_path: str, viewport_name: str = "Viewport") -> dict:
        self.calls.append(("viewport_set_active_camera", {"camera_path": camera_path, "viewport_name": viewport_name}))
        return self.responses.get("viewport_set_active_camera", {"ok": True, "camera_path": camera_path, "viewport_name": viewport_name})

    # Assets (Phase B+)

    # Phase D — Extension UI automation + carb log capture

    async def extension_activate(self, ext_id: str, reload: bool = False) -> dict:
        self.calls.append(("extension_activate", {"ext_id": ext_id, "reload": reload}))
        return self.responses.get(
            "extension_activate",
            {
                "ok": True,
                "ext_id": ext_id,
                "was_enabled": False,
                "enabled": True,
                "reloaded": reload,
            },
        )

    async def extension_ui_tree(
        self,
        ext_id: str | None = None,
        window: str | None = None,
        widget_types: list[str] | None = None,
    ) -> dict:
        self.calls.append(("extension_ui_tree", {
            "ext_id": ext_id, "window": window, "widget_types": widget_types,
        }))
        return self.responses.get(
            "extension_ui_tree",
            {
                "ok": True,
                "ext_id": ext_id,
                "window": window,
                "matched_windows": [window] if window else [],
                "windows": [
                    {"title": "UI Demo", "visible": True, "docked": False},
                ],
                "widgets": [
                    {
                        "path": "UI Demo//Frame/VStack/Button[0]",
                        "label": "Trigger",
                        "type": "Button",
                        "enabled": True,
                        "visible": True,
                        "value": None,
                    },
                    {
                        "path": "UI Demo//Frame/VStack/StringField[0]",
                        "label": "",
                        "type": "StringField",
                        "enabled": True,
                        "visible": True,
                        "value": "",
                    },
                ],
                "widget_count": 2,
                "walk_errors": [],
            },
        )

    async def extension_ui_invoke(
        self, widget_path: str, action: str, value=None,
    ) -> dict:
        self.calls.append(
            ("extension_ui_invoke", {"widget_path": widget_path, "action": action, "value": value})
        )
        return self.responses.get(
            "extension_ui_invoke",
            {
                "ok": True,
                "widget_path": widget_path,
                "action_performed": action,
                "value": value,
                "post_state": {
                    "path": widget_path,
                    "label": "Clicked 1 times",
                    "type": "Button",
                    "enabled": True,
                    "visible": True,
                    "value": None,
                },
            },
        )

    async def extension_clear_logs(self) -> dict:
        self.calls.append(("extension_clear_logs", {}))
        return self.responses.get("extension_clear_logs", {"ok": True, "removed": 42})

    async def window_capture(self, request: dict) -> dict:
        self.calls.append(("window_capture", request))
        default = {
            "ok": True,
            "artifact_id": "win_abc",
            "path": "/tmp/window_abc.png",
            "width": 1920,
            "height": 1080,
            "hwnd": 123456,
            "title": "Isaac Sim Full",
            "class_name": "GLFW30",
            "mode": request.get("mode", "kit"),
            "used_printwindow": True,
            "used_bitblt_fallback": False,
            "sha256": "deadbeef",
            "wait_stable": request.get("wait_stable", False),
            "created_at_epoch_ms": 1,
        }
        return self.responses.get("window_capture", default)

    async def window_list(self) -> dict:
        self.calls.append(("window_list", {}))
        return self.responses.get("window_list", {
            "ok": True, "pid": 1234, "count": 1,
            "windows": [
                {"hwnd": 1, "title": "Isaac Sim Full", "class_name": "GLFW30",
                 "width": 1920, "height": 1080},
            ],
        })

    async def window_ui_list(self, name_filter: str | None = None) -> dict:
        self.calls.append(("window_ui_list", {"name_filter": name_filter}))
        return self.responses.get("window_ui_list", {
            "ok": True, "count": 2, "filter": name_filter,
            "windows": [
                {"title": "Viewport", "visible": True, "docked": False,
                 "dock_id": 0, "width": 800, "height": 600},
                {"title": "Stage", "visible": True, "docked": True,
                 "dock_id": 42, "width": 300, "height": 600},
            ],
        })

    async def window_ui_show(
        self, name: str, visible: bool = True, focus: bool = True, settle_frames: int = 5,
    ) -> dict:
        self.calls.append(("window_ui_show", {
            "name": name, "visible": visible, "focus": focus, "settle_frames": settle_frames,
        }))
        return self.responses.get("window_ui_show", {
            "ok": True, "name": name, "resolved_name": name, "resolved_via": "exact",
            "requested_visible": visible, "found": True, "focused": focus,
            "visible_after": visible, "docked": False, "dock_id": 0,
        })

    async def window_menu_list(self, menu_path: str | None = None) -> dict:
        self.calls.append(("window_menu_list", {"menu_path": menu_path}))
        return self.responses.get("window_menu_list", {
            "ok": True, "count": 1, "menu_path": menu_path,
            "items": [
                {"path": "Window/Viewport", "name": "Viewport", "has_submenu": False,
                 "enabled": True, "onclick_action": ["omni.kit.viewport", "Viewport"],
                 "action_prefix": "omni.kit.viewport"},
            ],
            "diag": {},
        })

    async def window_menu_trigger(self, menu_path: str) -> dict:
        self.calls.append(("window_menu_trigger", {"menu_path": menu_path}))
        return self.responses.get("window_menu_trigger", {
            "ok": True, "menu_path": menu_path,
            "action": ["omni.kit.x", "X"], "created_prims": [],
        })

    async def navigation_bake(
        self, volume_scale: float = 40.0, timeout_s: float = 300.0,
    ) -> dict:
        self.calls.append((
            "navigation_bake",
            {"volume_scale": volume_scale, "timeout_s": timeout_s},
        ))
        return self.responses.get("navigation_bake", {
            "ok": True, "agent_max_radius": 0.25, "area_count": 1,
            "mesh_signature": "abc", "volume_prim_path": "/World/NavMeshVolume",
            "volume_created": True, "volume_scale": volume_scale,
        })

    async def navigation_query_path(self, request: dict) -> dict:
        self.calls.append(("navigation_query_path", request))
        return self.responses.get("navigation_query_path", {
            "ok": True,
            "points": [request["start"], request["end"]],
            "length": 5.0,
            "straight": request.get("straighten", True),
            "auto_baked": False,
            "agent_radius": request.get("agent_radius", 0.25),
            "agent_height": request.get("agent_height", 1.8),
        })

    async def navigation_add_exclude_volume(
        self, prim_path: str | None = None, padding: float = 0.1,
    ) -> dict:
        self.calls.append((
            "navigation_add_exclude_volume",
            {"prim_path": prim_path, "padding": padding},
        ))
        return self.responses.get("navigation_add_exclude_volume", {
            "ok": True, "volume_prim_path": "/World/NavMeshExclude_1",
            "bbox_min": [-0.5, -0.5, 0.0], "bbox_max": [0.5, 0.5, 1.0],
            "padding": padding, "source_prim_path": prim_path,
        })

    async def navigation_set_visualization(self, request: dict) -> dict:
        self.calls.append(("navigation_set_visualization", request))
        return self.responses.get("navigation_set_visualization", {
            "ok": True,
            "mode": request.get("mode", "walkable"),
            "backend": "carb_settings",
            "setting_path": "/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh",
        })

    # Phase J — NavMesh Playground

    async def navigation_sample_walkable_points(self, request: dict) -> dict:
        self.calls.append(("navigation_sample_walkable_points", request))
        count = int(request.get("count", 1))
        return self.responses.get("navigation_sample_walkable_points", {
            "ok": True,
            "points": [[float(i), float(i), 0.0] for i in range(count)],
            "triangle_count": 100,
            "total_area_m2": 50.0,
            "seed": request.get("seed"),
            "method": "area_weighted",
        })

    async def robot_drive_physics(self, request: dict) -> dict:
        self.calls.append(("robot_drive_physics", request))
        return self.responses.get("robot_drive_physics", {
            "ok": True,
            "job_id": "drive_test_0001",
            "prim_path": request.get("prim_path", "/World/Robot"),
        })

    # Sensor (Phase E) — RTX Camera / Lidar / Depth + viz

    async def sensor_attach_rtx_camera(self, request: dict) -> dict:
        self.calls.append(("sensor_attach_rtx_camera", request))
        parent = request.get("robot_prim", "/World/Robot")
        name = request.get("sensor_name", "RtxCamera")
        return self.responses.get("sensor_attach_rtx_camera", {
            "ok": True,
            "sensor_prim_path": f"{parent}/{name}",
            "parent_prim": parent,
            "sensor_type": "rtx_camera",
            "resolution": request.get("resolution", [1280, 720]),
        })

    async def sensor_attach_rtx_lidar(self, request: dict) -> dict:
        self.calls.append(("sensor_attach_rtx_lidar", request))
        parent = request.get("robot_prim", "/World/Robot")
        name = request.get("sensor_name", "RtxLidar")
        return self.responses.get("sensor_attach_rtx_lidar", {
            "ok": True,
            "sensor_prim_path": f"{parent}/{name}",
            "parent_prim": parent,
            "sensor_type": "rtx_lidar",
            "config_preset": request.get("config_preset", "Example_Rotary"),
            "annotator": "RtxSensorCpuIsaacCreateRTXLidarScanBuffer",
        })

    async def sensor_attach_rtx_depth_camera(self, request: dict) -> dict:
        self.calls.append(("sensor_attach_rtx_depth_camera", request))
        parent = request.get("robot_prim", "/World/Robot")
        name = request.get("sensor_name", "RtxDepthCamera")
        return self.responses.get("sensor_attach_rtx_depth_camera", {
            "ok": True,
            "sensor_prim_path": f"{parent}/{name}",
            "parent_prim": parent,
            "sensor_type": "rtx_depth_camera",
            "resolution": request.get("resolution", [1280, 720]),
            "annotator": "distance_to_camera",
        })

    async def sensor_set_visualization(self, request: dict) -> dict:
        self.calls.append(("sensor_set_visualization", request))
        return self.responses.get("sensor_set_visualization", {
            "ok": True,
            "sensor_prim": request.get("sensor_prim", ""),
            "mode": request.get("mode", "on"),
            "sensor_type": "rtx_lidar",
        })

    # Sensor (Phase G)

    async def sensor_attach_contact(self, request: dict) -> dict:
        self.calls.append(("sensor_attach_contact", request))
        parent = request.get("prim_path", "/World/Robot")
        name = request.get("sensor_name", "ContactSensor")
        return self.responses.get("sensor_attach_contact", {
            "ok": True,
            "sensor_prim_path": f"{parent}/{name}",
            "parent_prim": parent,
            "sensor_type": "contact",
            "frequency": int(request.get("frequency", 60)),
            "translation": request.get("translation", [0.0, 0.0, 0.0]),
            "radius": float(request.get("radius", -1.0)),
            "backend": "isaacsim.sensors.physics",
        })

    async def sensor_attach_imu(self, request: dict) -> dict:
        self.calls.append(("sensor_attach_imu", request))
        parent = request.get("prim_path", "/World/Robot")
        name = request.get("sensor_name", "IMUSensor")
        return self.responses.get("sensor_attach_imu", {
            "ok": True,
            "sensor_prim_path": f"{parent}/{name}",
            "parent_prim": parent,
            "sensor_type": "imu",
            "frequency": int(request.get("frequency", 200)),
            "mount_offset": request.get("mount_offset", [0.0, 0.0, 0.0]),
            "mount_orientation": request.get("mount_orientation", [1.0, 0.0, 0.0, 0.0]),
            "backend": "isaacsim.sensors.physics",
        })

    async def sensor_set_annotator(self, request: dict) -> dict:
        self.calls.append(("sensor_set_annotator", request))
        annotators = request.get("annotators") or []
        resolution = request.get("resolution") or [1280, 720]
        return self.responses.get("sensor_set_annotator", {
            "ok": True,
            "sensor_prim": request.get("sensor_prim", ""),
            "annotators": list(annotators),
            "skipped": {},
            "resolution": [int(resolution[0]), int(resolution[1])],
            "backend": "omni.replicator.core",
            "render_product": "/Render/RenderProduct_Mock_0",
        })

    async def sensor_lidar_get_point_cloud(self, request: dict) -> dict:
        self.calls.append(("sensor_lidar_get_point_cloud", request))
        max_points = int(request.get("max_points", 1000))
        n = min(3, max_points)
        return self.responses.get("sensor_lidar_get_point_cloud", {
            "ok": True,
            "sensor_prim": request.get("sensor_prim", ""),
            "annotator": "RtxSensorCpuIsaacCreateRTXLidarScanBuffer",
            "backend": "omni.replicator.core",
            "num_points": n,
            "points": [[float(i), 0.0, 0.0] for i in range(n)],
            "intensities": [1.0] * n,
            "truncated": False,
            "frames_waited": int(request.get("frames_to_wait", 2)),
            "raw_keys": ["azimuth", "data", "distance", "elevation", "intensity"],
            "warning": None,
        })

    # Physics (Phase F) — rigid body / collider / material / joint / scene / viz

    async def physics_apply_rigid_body(self, request: dict) -> dict:
        self.calls.append(("physics_apply_rigid_body", request))
        return self.responses.get("physics_apply_rigid_body", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "mass": request.get("mass", 1.0),
            "dynamic": request.get("dynamic", True),
            "applied_apis": ["PhysicsRigidBodyAPI", "PhysicsMassAPI"],
        })

    async def physics_get_rigid_body_state(self, prim_path: str) -> dict:
        self.calls.append(("physics_get_rigid_body_state", {"prim_path": prim_path}))
        return self.responses.get("physics_get_rigid_body_state", {
            "ok": True,
            "prim_path": prim_path,
            "source": "physx_runtime",
            "linear_velocity": [0.0, 0.0, -2.5],
            "angular_velocity": [0.0, 0.0, 0.0],
            "mass": 1.0,
            "center_of_mass": [0.0, 0.0, 0.0],
            "is_kinematic": False,
            "is_enabled": True,
        })

    async def physics_apply_collider(self, request: dict) -> dict:
        self.calls.append(("physics_apply_collider", request))
        return self.responses.get("physics_apply_collider", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "approximation": request.get("approximation", "convexHull"),
            "applied_apis": ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"],
        })

    async def physics_apply_material(self, request: dict) -> dict:
        self.calls.append(("physics_apply_material", request))
        return self.responses.get("physics_apply_material", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "material_prim_path": "/World/PhysicsMaterials/M_mock",
            "friction": request.get("friction", 0.5),
            "restitution": request.get("restitution", 0.0),
            "density": request.get("density", 1000.0),
        })

    async def physics_create_joint(self, request: dict) -> dict:
        self.calls.append(("physics_create_joint", request))
        return self.responses.get("physics_create_joint", {
            "ok": True,
            "joint_prim_path": request.get("joint_prim_path")
                or f"/World/PhysicsJoints/{request.get('joint_type', 'Joint')}_mock",
            "joint_type": request.get("joint_type", "Fixed"),
            "body_a": request.get("body_a", ""),
            "body_b": request.get("body_b", ""),
        })

    async def physics_set_joint_drive(self, request: dict) -> dict:
        self.calls.append(("physics_set_joint_drive", request))
        return self.responses.get("physics_set_joint_drive", {
            "ok": True,
            "joint_prim_path": request.get("joint_prim_path", ""),
            "drive_type": request.get("drive_type", "angular"),
            "target_position": request.get("target_position", 0.0),
            "target_velocity": request.get("target_velocity", 0.0),
            "stiffness": request.get("stiffness", 0.0),
            "damping": request.get("damping", 0.0),
            "max_force": request.get("max_force"),
        })

    async def physics_set_scene(self, request: dict) -> dict:
        self.calls.append(("physics_set_scene", request))
        gravity = request.get("gravity") or [0.0, 0.0, -9.81]
        timestep = request.get("timestep", 1.0 / 60.0)
        return self.responses.get("physics_set_scene", {
            "ok": True,
            "scene_prim_path": request.get("scene_prim_path", "/World/PhysicsScene"),
            "gravity": list(gravity),
            "gravity_magnitude": 9.81,
            "timestep": timestep,
            "time_steps_per_second": int(round(1.0 / timestep)) if timestep > 0 else 60,
            "solver_iter_pos": request.get("solver_iter_pos", 4),
            "solver_iter_vel": request.get("solver_iter_vel", 1),
        })

    async def physics_visualize(self, request: dict) -> dict:
        self.calls.append(("physics_visualize", request))
        mode = request.get("mode", "off")
        active = [] if mode == "off" else [f"/physics/visualization_{mode}"]
        return self.responses.get("physics_visualize", {
            "ok": True,
            "mode": mode,
            "active_settings": active,
        })

    # Lighting (Phase F) — UsdLux creators + exposure

    async def lighting_create(self, kind: str, request: dict) -> dict:
        self.calls.append((f"lighting_create_{kind}", request))
        type_map = {
            "dome": "DomeLight",
            "distant": "DistantLight",
            "disk": "DiskLight",
            "rect": "RectLight",
            "sphere": "SphereLight",
        }
        extra: dict = {}
        if kind == "dome":
            extra["texture"] = request.get("texture")
        elif kind == "distant":
            extra["angle_deg"] = request.get("angle_deg", 0.53)
        elif kind == "disk":
            extra["radius"] = request.get("radius", 1.0)
        elif kind == "rect":
            extra["width"] = request.get("width", 1.0)
            extra["height"] = request.get("height", 1.0)
        elif kind == "sphere":
            extra["radius"] = request.get("radius", 1.0)
        return self.responses.get(f"lighting_create_{kind}", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "light_type": type_map.get(kind, "DomeLight"),
            "intensity": request.get("intensity", 1000.0),
            "extra": extra,
        })

    async def lighting_set_exposure(self, request: dict) -> dict:
        self.calls.append(("lighting_set_exposure", request))
        return self.responses.get("lighting_set_exposure", {
            "ok": True,
            "exposure": request.get("exposure", 0.0),
            "setting_path": "/rtx/post/tonemap/exposure",
        })

    # Material (Phase F) — MDL list / assign / bound

    async def material_list_mdl(self, library: str = "default") -> dict:
        self.calls.append(("material_list_mdl", {"library": library}))
        return self.responses.get("material_list_mdl", {
            "ok": True,
            "library": library,
            "count": 3,
            "entries": [
                {"name": "OmniPBR", "url": "/mock/OmniPBR.mdl", "library": library},
                {"name": "OmniGlass", "url": "/mock/OmniGlass.mdl", "library": library},
                {"name": "OmniSurface", "url": "/mock/OmniSurface.mdl", "library": library},
            ],
        })

    async def material_assign_mdl(self, request: dict) -> dict:
        self.calls.append(("material_assign_mdl", request))
        return self.responses.get("material_assign_mdl", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "material_prim_path": f"/World/Materials/{request.get('material_name', 'M')}",
            "mdl_url": request.get("mdl_url", ""),
            "material_name": request.get("material_name", ""),
        })

    async def material_get_bound(self, prim_path: str) -> dict:
        self.calls.append(("material_get_bound", {"prim_path": prim_path}))
        return self.responses.get("material_get_bound", {
            "ok": True,
            "prim_path": prim_path,
            "material_path": "/World/Materials/OmniPBR",
            "binding_strength": "strongerThanDescendants",
        })

    # Viewport render (Phase F) — mode / quality / overlay / fov

    async def viewport_set_render_mode(self, request: dict) -> dict:
        self.calls.append(("viewport_set_render_mode", request))
        mode = request.get("mode", "RealTime")
        return self.responses.get("viewport_set_render_mode", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "mode": mode,
            "setting_value": "PathTracing" if mode == "PathTracing" else "RaytracedLighting",
        })

    async def viewport_set_render_quality(self, request: dict) -> dict:
        self.calls.append(("viewport_set_render_quality", request))
        op_map = {"auto": 3, "DLSS": 4, "NRD": 5, "off": 0}
        return self.responses.get("viewport_set_render_quality", {
            "ok": True,
            "samples": request.get("samples", 1),
            "denoiser": request.get("denoiser", "auto"),
            "aa_op": op_map.get(request.get("denoiser", "auto"), 3),
        })

    async def viewport_toggle_overlay(self, request: dict) -> dict:
        self.calls.append(("viewport_toggle_overlay", request))
        overlay = request.get("overlay", "gridlines")
        path_map = {
            "gridlines": "/persistent/app/viewport/grid/enabled",
            "axis": "/persistent/app/viewport/displayOptions/axis",
            "stats": "/rtx/stats/enable",
        }
        return self.responses.get("viewport_toggle_overlay", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "overlay": overlay,
            "visible": request.get("visible", True),
            "setting_path": path_map.get(overlay, ""),
        })

    async def viewport_set_fov(self, request: dict) -> dict:
        self.calls.append(("viewport_set_fov", request))
        return self.responses.get("viewport_set_fov", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "camera_path": "/OmniverseKit_Persp",
            "fov_deg": request.get("fov_deg", 60.0),
            "focal_length": 18.1466,
            "horizontal_aperture": 20.955,
        })

    async def viewport_set_camera_lookat(self, request: dict) -> dict:
        self.calls.append(("viewport_set_camera_lookat", request))
        return self.responses.get("viewport_set_camera_lookat", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "camera_path": request.get("camera_path") or "/OmniverseKit_Persp",
            "eye": request.get("eye", [0.0, 0.0, 0.0]),
            "target": request.get("target", [0.0, 0.0, 0.0]),
            "up": request.get("up", [0.0, 0.0, 1.0]),
        })

    async def viewport_focus_prim(self, request: dict) -> dict:
        self.calls.append(("viewport_focus_prim", request))
        return self.responses.get("viewport_focus_prim", {
            "ok": True,
            "prim_path": request.get("prim_path", ""),
            "viewport_name": request.get("viewport_name", "Viewport"),
            "camera_path": request.get("camera_path") or "/OmniverseKit_Persp",
            "method": "frame_viewport_prims",
            "target": [0.0, 0.0, 0.0],
            "eye": None,
            "bbox_min": [-0.5, -0.5, -0.5],
            "bbox_max": [0.5, 0.5, 0.5],
            "radius": 0.8660254,
            "selected": bool(request.get("select", True)),
        })

    async def viewport_project_points(self, request: dict) -> dict:
        self.calls.append(("viewport_project_points", request))
        width = int(request.get("width", 1280))
        height = int(request.get("height", 720))
        points = [
            {
                "world": point,
                "ndc_xy": [0.5, 0.5],
                "pixel_xy": [width / 2.0, height / 2.0],
                "depth": 1.0,
                "in_front": True,
                "in_frame": True,
            }
            for point in request.get("points", [])
        ]
        return self.responses.get("viewport_project_points", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "camera_path": request.get("camera_path") or "/OmniverseKit_Persp",
            "width": width,
            "height": height,
            "points": points,
        })

    async def viewport_frame_prims(self, request: dict) -> dict:
        self.calls.append(("viewport_frame_prims", request))
        target = [0.5, 0.5, 0.5]
        eye = [2.0, -1.0, 1.5]
        return self.responses.get("viewport_frame_prims", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport"),
            "camera_path": request.get("camera_path") or "/OmniverseKit_Persp",
            "prim_paths": request.get("prim_paths", []),
            "eye": eye,
            "target": target,
            "up": request.get("up", [0.0, 0.0, 1.0]),
            "fov_deg": request.get("fov_deg", 60.0),
            "distance": 2.0,
            "combined_bbox": {
                "min": [0.0, 0.0, 0.0],
                "max": [1.0, 1.0, 1.0],
                "center": target,
                "size": [1.0, 1.0, 1.0],
                "is_empty": False,
            },
            "prim_bboxes": [],
        })

    # Viewport multi (Phase E) — create / destroy

    async def viewport_create(self, request: dict) -> dict:
        self.calls.append(("viewport_create", request))
        return self.responses.get("viewport_create", {
            "ok": True,
            "viewport_name": request.get("viewport_name", "Viewport_Aux"),
            "existed": False,
            "camera_path": request.get("camera_path"),
            "width": request.get("width", 1280),
            "height": request.get("height", 720),
            "docked": request.get("docked", False),
        })

    async def viewport_destroy(self, request: dict) -> dict:
        self.calls.append(("viewport_destroy", request))
        return self.responses.get("viewport_destroy", {
            "ok": True,
            "viewport_name": request.get("viewport_name", ""),
            "destroyed": True,
        })

    async def extension_logs(
        self,
        ext_id: str | None = None,
        since_ms: int | None = None,
        level: str = "INFO",
        limit: int = 1000,
    ) -> dict:
        self.calls.append(
            (
                "extension_logs",
                {
                    "ext_id": ext_id,
                    "since_ms": since_ms,
                    "level": level,
                    "limit": limit,
                },
            )
        )
        return self.responses.get(
            "extension_logs",
            {
                "ok": True,
                "entries": [
                    {
                        "ts_ms": 1700000000000,
                        "level": "INFO",
                        "level_int": -1,
                        "source": "omni.mycompany.ui_demo",
                        "filename": "extension.py",
                        "line": 42,
                        "msg": "hello",
                    },
                ],
                "count": 1,
                "truncated": False,
                "level_filter": level,
                "since_ms": since_ms,
                "source_filter": ext_id,
            },
        )

    async def asset_list(
        self,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> dict:
        self.calls.append(
            ("asset_list", {
                "category": category,
                "subpath": subpath,
                "recursive": recursive,
                "max_depth": max_depth,
                "max_entries": max_entries,
            })
        )
        if category is None:
            return self.responses.get("asset_list_categories", {
                "ok": True,
                "assets_root": "https://example/Isaac/5.1",
                "categories": [
                    {"name": "robots", "url": "https://example/Isaac/5.1/Isaac/Robots"},
                ],
            })
        return self.responses.get("asset_list", {
            "ok": True,
            "category": category,
            "subpath": subpath,
            "base_url": f"https://example/Isaac/5.1/Isaac/{category.capitalize()}",
            "target_url": f"https://example/Isaac/5.1/Isaac/{category.capitalize()}/{subpath}".rstrip("/"),
            "items": [
                {"name": "Franka", "url": "https://example/.../Franka", "is_folder": True, "size": None},
                {"name": "franka.usd", "url": "https://example/.../franka.usd", "is_folder": False, "size": 1024},
            ],
            "count": 2,
        })

    # --- Phase H — Replicator ---

    async def replicator_create_writer(self, request: dict) -> dict:
        self.calls.append(("replicator_create_writer", request))
        return self.responses.get("replicator_create_writer", {
            "ok": True,
            "writer_id": "writer_mock01",
            "writer_type": request.get("writer_type", "BasicWriter"),
            "output_dir": request.get("output_dir", ""),
            "channels": {
                "rgb": bool(request.get("rgb", True)),
                "depth": bool(request.get("depth", False)),
                "semantic_segmentation": bool(
                    request.get("semantic_segmentation", False),
                ),
            },
            "backend": "omni.replicator.core",
        })

    async def replicator_register_randomizer(self, request: dict) -> dict:
        self.calls.append(("replicator_register_randomizer", request))
        return self.responses.get("replicator_register_randomizer", {
            "ok": True,
            "randomizer_id": "rand_mock01",
            "type": request.get("type", "position"),
            "target": request.get("target", "/World/Boxes/*"),
            "config": dict(request.get("config") or {}),
            "backend": "omni.replicator.core",
        })

    async def replicator_trigger_once(self, request: dict) -> dict:
        self.calls.append(("replicator_trigger_once", request))
        frames = int(request.get("num_frames", 1))
        return self.responses.get("replicator_trigger_once", {
            "ok": True,
            "num_frames": frames,
            "frames_ran": frames,
            "writer_count": 1,
            "randomizer_count": 1,
            "backend": "omni.replicator.core",
        })

    async def replicator_trigger_on_time(self, request: dict) -> dict:
        self.calls.append(("replicator_trigger_on_time", request))
        return self.responses.get("replicator_trigger_on_time", {
            "ok": True,
            "trigger_id": "trig_mock01",
            "interval_s": float(request.get("interval_s", 0.5)),
            "backend": "omni.replicator.core",
        })

    # --- Phase H — OmniGraph ---

    async def omnigraph_create_node(self, request: dict) -> dict:
        self.calls.append(("omnigraph_create_node", request))
        node_type = request.get("node_type", "")
        node_name = request.get("node_name") or node_type.rsplit(".", 1)[-1]
        return self.responses.get("omnigraph_create_node", {
            "ok": True,
            "graph_path": request.get("graph_path", "/ActionGraph"),
            "graph_existed": False,
            "node_type": node_type,
            "node_name": node_name,
            "node_path": f"{request.get('graph_path', '/ActionGraph')}/{node_name}",
            "backend": "omni.graph.core",
        })

    async def omnigraph_connect(self, request: dict) -> dict:
        self.calls.append(("omnigraph_connect", request))
        return self.responses.get("omnigraph_connect", {
            "ok": True,
            "src_attr": request.get("src_attr", ""),
            "dst_attr": request.get("dst_attr", ""),
            "backend": "omni.graph.core",
        })

    async def omnigraph_execute(self, request: dict) -> dict:
        self.calls.append(("omnigraph_execute", request))
        return self.responses.get("omnigraph_execute", {
            "ok": True,
            "graph_path": request.get("graph_path", "/ActionGraph"),
            "evaluated": True,
            "backend": "omni.graph.core",
        })

    async def omnigraph_create_ros2_publisher(self, request: dict) -> dict:
        self.calls.append(("omnigraph_create_ros2_publisher", request))
        graph = request.get("graph_path", "/ActionGraph")
        return self.responses.get("omnigraph_create_ros2_publisher", {
            "ok": True,
            "graph_path": graph,
            "topic": request.get("topic", "/camera/image_raw"),
            "source_prim": request.get("source_prim", "/World/Camera"),
            "msg_type": request.get("msg_type", "sensor_msgs/msg/Image"),
            "ros2_available": False,
            "nodes_created": [
                {"name": "OnTick", "type": "omni.graph.action.OnTick", "path": f"{graph}/OnTick"},
                {"name": "RenderProduct", "type": "isaacsim.core.nodes.IsaacCreateRenderProduct", "path": f"{graph}/RenderProduct"},
                {"name": "PublishImage", "type": "isaacsim.ros2.bridge.ROS2PublishImage", "path": f"{graph}/PublishImage"},
            ],
            "edges_created": [
                {"src": f"{graph}/OnTick.outputs:tick", "dst": f"{graph}/RenderProduct.inputs:execIn"},
                {"src": f"{graph}/RenderProduct.outputs:execOut", "dst": f"{graph}/PublishImage.inputs:execIn"},
            ],
            "backend": "omni.graph.core",
        })

    async def omnigraph_create_script_controller(self, request: dict) -> dict:
        self.calls.append(("omnigraph_create_script_controller", request))
        graph = request.get("graph_path", "/ActionGraph")
        node_name = request.get("node_name", "ScriptNode")
        tick_name = request.get("tick_node_name", "OnPlaybackTick")
        return self.responses.get("omnigraph_create_script_controller", {
            "ok": True,
            "graph_path": graph,
            "script_path": request.get("script_path", ""),
            "node_path": f"{graph}/{node_name}",
            "tick_node_path": f"{graph}/{tick_name}",
            "nodes_created": [
                {"name": tick_name, "type": "omni.graph.action.OnPlaybackTick", "path": f"{graph}/{tick_name}"},
                {"name": node_name, "type": "omni.graph.scriptnode.ScriptNode", "path": f"{graph}/{node_name}"},
            ],
            "edges_created": [
                {"src": f"{graph}/{tick_name}.outputs:tick", "dst": f"{graph}/{node_name}.inputs:execIn"},
            ],
            "backend": "omni.graph.core",
            "reset_state": bool(request.get("reset_state", True)),
        })

    # --- Phase H — Content browser ---

    async def content_browse(self, request: dict) -> dict:
        self.calls.append(("content_browse", request))
        url = request.get("url", "")
        return self.responses.get("content_browse", {
            "ok": True,
            "url": url,
            "recursive": bool(request.get("recursive", False)),
            "entries": [
                {"url": f"{url}/folderA", "name": "folderA", "is_folder": True, "size": None, "modified_time_ns": 0, "flags": 16},
                {"url": f"{url}/file.usd", "name": "file.usd", "is_folder": False, "size": 1024, "modified_time_ns": 0, "flags": 0},
            ],
            "entry_count": 2,
            "truncated": False,
            "backend": "omni.client",
        })

    async def content_preview(self, request: dict) -> dict:
        self.calls.append(("content_preview", request))
        url = request.get("url", "")
        return self.responses.get("content_preview", {
            "ok": True,
            "url": url,
            "info": {
                "url": url,
                "name": url.rsplit("/", 1)[-1],
                "is_folder": False,
                "size": 2048,
                "modified_time_ns": 0,
                "flags": 0,
            },
            "backend": "omni.client",
        })

    async def content_inspect(self, request: dict) -> dict:
        self.calls.append(("content_inspect", request))
        url = request.get("url", "")
        return self.responses.get("content_inspect", {
            "ok": True,
            "url": url,
            "default_prim": "/World",
            "bbox_min": [-1.0, -1.0, 0.0],
            "bbox_max": [1.0, 1.0, 2.0],
            "meters_per_unit": 0.01,
            "up_axis": "Z",
            "prim_count": 42,
            "backend": "usd",
        })

    async def content_resolve(self, request: dict) -> dict:
        self.calls.append(("content_resolve", request))
        url = request.get("url", "")
        return self.responses.get("content_resolve", {
            "ok": True,
            "url": url,
            "resolved": url,
            "backend": "omni.client",
        })

    # --- Phase H — Extension management extensions ---

    async def extension_deactivate(self, ext_id: str) -> dict:
        self.calls.append(("extension_deactivate", {"ext_id": ext_id}))
        return self.responses.get("extension_deactivate", {
            "ok": True,
            "ext_id": ext_id,
            "was_enabled": True,
            "enabled": False,
        })

    async def extension_list_all(self, enabled_only: bool = False) -> dict:
        self.calls.append(("extension_list_all", {"enabled_only": enabled_only}))
        return self.responses.get("extension_list_all", {
            "ok": True,
            "enabled_only": enabled_only,
            "count": 2,
            "extensions": [
                {
                    "id": "omni.kit.menu.utils",
                    "full_id": "omni.kit.menu.utils-1.2.3",
                    "name": "omni.kit.menu.utils",
                    "version": "1.2.3",
                    "enabled": True,
                    "path": "C:/Kit/ext/omni.kit.menu.utils",
                    "title": "Menu Utils",
                },
                {
                    "id": "omni.mycompany.ui_demo",
                    "full_id": "omni.mycompany.ui_demo-0.1.0",
                    "name": "omni.mycompany.ui_demo",
                    "version": "0.1.0",
                    "enabled": False,
                    "path": "C:/Kit/ext/omni.mycompany.ui_demo",
                    "title": "UI Demo",
                },
            ],
        })

    async def extension_get_info(self, ext_id: str) -> dict:
        self.calls.append(("extension_get_info", {"ext_id": ext_id}))
        return self.responses.get("extension_get_info", {
            "ok": True,
            "ext_id": ext_id,
            "info": {
                "id": ext_id,
                "full_id": f"{ext_id}-1.0.0",
                "name": ext_id,
                "version": "1.0.0",
                "enabled": True,
                "path": f"C:/Kit/ext/{ext_id}",
                "title": ext_id,
                "dependencies": ["omni.kit.app"],
            },
        })

    async def extension_reload_clean(self, ext_id: str) -> dict:
        self.calls.append(("extension_reload_clean", {"ext_id": ext_id}))
        return self.responses.get("extension_reload_clean", {
            "ok": True,
            "ext_id": ext_id,
            "was_enabled": True,
            "enabled": True,
            "reloaded": True,
            "modules_purged": 3,
        })

    async def kit_command_execute(
        self,
        name: str,
        payload: dict | None = None,
        expect_undo: bool = False,
    ) -> dict:
        self.calls.append(("kit_command_execute", {"name": name, "payload": payload, "expect_undo": expect_undo}))
        return self.responses.get("kit_command_execute", {
            "ok": True, "name": name, "succeeded": True, "result": None,
        })

    async def kit_python_run(
        self,
        code: str,
        return_keys: list[str] | None = None,
    ) -> dict:
        self.calls.append(("kit_python_run", {"code": code, "return_keys": list(return_keys or [])}))
        return self.responses.get("kit_python_run", {
            "ok": True, "stdout": "", "stderr": "",
            "error": None, "traceback": None, "returned": {},
        })

    async def close(self) -> None:
        pass


@dataclass
class MockLakehouseClient:
    """Mock Lakehouse client for unit tests."""

    responses: dict[str, Any] = field(default_factory=dict)
    calls: list[dict] = field(default_factory=list)

    async def query(self, params: dict) -> dict:
        self.calls.append(params)
        return self.responses.get("query", {"row_count": 0, "rows": [], "schema": {}})

    async def close(self) -> None:
        pass
