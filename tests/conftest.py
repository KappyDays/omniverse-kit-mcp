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
