"""Shared test fixtures and mock clients."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import yaml

from isaacsim_mcp.types.common import ModuleName, OperationMeta
from isaacsim_mcp.types.extension import ExtensionState
from isaacsim_mcp.types.lakehouse import LakehouseQueryResult, LakehouseRow
from isaacsim_mcp.types.stage import StageSnapshot, UsdPropertyValue
from isaacsim_mcp.types.viewport import ImageArtifact, SSIMComparisonResult

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
            "ok": True, "pid": "<process-id>", "count": 1,
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
