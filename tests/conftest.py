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
