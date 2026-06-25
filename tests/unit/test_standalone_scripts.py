"""Standalone script cwd guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.probe_mcp_surface as mcp_probe
import scripts.run_process_module_standalone as process_script
import scripts.run_scenario_standalone as scenario_script
from omniverse_kit_mcp.config import AppConfig, ScenarioConfig
from omniverse_kit_mcp.types.common import ExecutionStatus
from omniverse_kit_mcp.types.scenario import ScenarioRunSummary, StepResult


class _CwdChecked(RuntimeError):
    pass


def _write_standalone_minimal_scenario(scenarios: Path) -> None:
    scenario_path = scenarios / "smoke" / "dry.yaml"
    scenario_path.parent.mkdir(parents=True)
    scenario_path.write_text(
        """
apiVersion: isaacsim.validation/v1
kind: Scenario
metadata:
  id: standalone_dry_run
  name: Standalone dry run
spec:
  variables:
    lidar_min_points: 1
  assert:
    - id: read_lidar
      module: sensor
      action: lidar_get_point_cloud
      idempotent: true
      retries:
        maxAttempts: 2
        initialBackoffSeconds: 0
        maxBackoffSeconds: 0
      args:
        sensor_prim: /World/Robot/Lidar
        frames_to_wait: 12
        min_points: ${variables.lidar_min_points}
        max_points: 16
""".strip(),
        encoding="utf-8",
    )


def _host_local_capture_path() -> str:
    return (
        "C:"
        + "/Users/"
        + "localuser"
        + "/AppData/Local/Temp/validation_api_captures/capture_script.png"
    )


def _log_capture_pass() -> dict:
    return {
        "ok": True,
        "status": "passed",
        "data": {
            "status": "ready",
            "capture_running": False,
            "capture_stop_requested": True,
            "capture_stop_completed": True,
            "capture_stop_timed_out": False,
            "capture_stop_timeout_s": 1.0,
        },
    }


def _standalone_summary(scenario_id: str = "standalone_dry_run") -> ScenarioRunSummary:
    capture_path = _host_local_capture_path()
    return ScenarioRunSummary(
        scenario_id=scenario_id,
        status=ExecutionStatus.PASSED,
        passed_steps=1,
        failed_steps=0,
        skipped_steps=0,
        started_at_epoch_ms=1000,
        ended_at_epoch_ms=1100,
        step_results=(
            StepResult(
                step_id="capture",
                phase="assert",
                status=ExecutionStatus.PASSED,
                message=f"capture saved at {capture_path}",
                data_summary={
                    "artifact": {
                        "path": capture_path,
                        "sha256": "abc123",
                        "width": 320,
                        "height": 180,
                    },
                },
            ),
        ),
        artifact_paths=(capture_path,),
    )


class _FakeStandaloneClient:
    def __init__(self, config):
        self.config = config
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _install_fake_mcp_stdio(
    monkeypatch,
    *,
    responses: list[dict],
    sent_messages: list[dict],
) -> None:
    class FakeStdin:
        def write(self, data: bytes) -> None:
            sent_messages.append(json.loads(data.decode("utf-8")))

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeStdout:
        def __init__(self, payloads: list[dict]):
            self._lines = [
                (json.dumps(payload) + "\n").encode("utf-8")
                for payload in payloads
            ]

        async def readline(self) -> bytes:
            if not self._lines:
                return b""
            return self._lines.pop(0)

    class FakeProcess:
        def __init__(self, payloads: list[dict]):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout(payloads)

        async def wait(self) -> int:
            return 0

        def kill(self) -> None:
            pass

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess(responses)

    monkeypatch.setattr(
        mcp_probe.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )


@pytest.mark.asyncio
async def test_process_standalone_chdirs_to_project_root_before_config(
    monkeypatch, tmp_path,
):
    monkeypatch.chdir(tmp_path)

    def fake_app_config():
        assert Path.cwd() == process_script.PROJECT_ROOT
        raise _CwdChecked

    monkeypatch.setattr(process_script, "AppConfig", fake_app_config)

    with pytest.raises(_CwdChecked):
        await process_script.run("start", "isaac-sim", 1)


@pytest.mark.asyncio
async def test_scenario_standalone_chdirs_to_project_root_before_config(
    monkeypatch, tmp_path,
):
    monkeypatch.chdir(tmp_path)

    def fake_app_config():
        assert Path.cwd() == scenario_script.PROJECT_ROOT
        raise _CwdChecked

    monkeypatch.setattr(scenario_script, "AppConfig", fake_app_config)

    with pytest.raises(_CwdChecked):
        await scenario_script.run("smoke/robot_rtx_sensor_golden_workflow.yaml")


@pytest.mark.asyncio
async def test_scenario_standalone_dry_run_prints_plan_without_rest_clients(
    monkeypatch, tmp_path, capsys,
):
    scenarios = tmp_path / "scenarios"
    _write_standalone_minimal_scenario(scenarios)
    config = AppConfig(scenario=ScenarioConfig(SCENARIOS_DIR=str(scenarios)))
    monkeypatch.setattr(scenario_script, "AppConfig", lambda: config)

    def fail_client(*args, **kwargs):
        raise AssertionError("dry-run must not create REST clients")

    monkeypatch.setattr(scenario_script, "IsaacRestClient", fail_client)
    monkeypatch.chdir(tmp_path)

    exit_code = await scenario_script.run(
        "smoke/dry.yaml",
        dry_run=True,
        input_overrides={"lidar_min_points": 4},
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output.split("===== DRY RUN PLAN =====", 1)[1])
    assert payload["dry_run"] is True
    assert payload["compiled"] is True
    assert payload["steps"] == payload["total_steps"] == 2
    assert payload["variables"]["lidar_min_points"] == 4
    assert payload["evidence_steps"][0]["key_args"]["min_points"] == 4
    assert payload["retry_steps"][0]["key_args"]["frames_to_wait"] == 12
    assert payload["retry_steps"][0]["retries"]["maxAttempts"] == 2


@pytest.mark.asyncio
async def test_scenario_standalone_normal_run_can_emit_public_safe_markdown(
    monkeypatch, tmp_path, capsys,
):
    scenarios = tmp_path / "scenarios"
    _write_standalone_minimal_scenario(scenarios)
    config = AppConfig(scenario=ScenarioConfig(SCENARIOS_DIR=str(scenarios)))
    monkeypatch.setattr(scenario_script, "AppConfig", lambda: config)

    created_isaac_clients: list[_FakeStandaloneClient] = []
    created_lakehouse_clients: list[_FakeStandaloneClient] = []

    def fake_isaac_client(config):
        client = _FakeStandaloneClient(config)
        created_isaac_clients.append(client)
        return client

    def fake_lakehouse_client(config):
        client = _FakeStandaloneClient(config)
        created_lakehouse_clients.append(client)
        return client

    class FakeScenarioRunner:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, scenario):
            return _standalone_summary(scenario.scenario_id)

    monkeypatch.setattr(scenario_script, "IsaacRestClient", fake_isaac_client)
    monkeypatch.setattr(scenario_script, "LakehouseClient", fake_lakehouse_client)
    monkeypatch.setattr(scenario_script, "ScenarioRunner", FakeScenarioRunner)

    exit_code = await scenario_script.run(
        "smoke/dry.yaml",
        report_format="markdown",
        redact_local_paths=True,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "===== JSON REPORT =====" not in output
    assert "===== MARKDOWN REPORT =====" in output
    assert _host_local_capture_path() not in output
    assert "<validation-api-capture>/capture_script.png" in output
    assert created_isaac_clients[0].closed is True
    assert created_lakehouse_clients[0].closed is True


@pytest.mark.asyncio
async def test_scenario_standalone_normal_run_defaults_to_both_raw_reports(
    monkeypatch, tmp_path, capsys,
):
    scenarios = tmp_path / "scenarios"
    _write_standalone_minimal_scenario(scenarios)
    config = AppConfig(scenario=ScenarioConfig(SCENARIOS_DIR=str(scenarios)))
    monkeypatch.setattr(scenario_script, "AppConfig", lambda: config)

    class FakeScenarioRunner:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self, scenario):
            return _standalone_summary(scenario.scenario_id)

    monkeypatch.setattr(scenario_script, "IsaacRestClient", _FakeStandaloneClient)
    monkeypatch.setattr(scenario_script, "LakehouseClient", _FakeStandaloneClient)
    monkeypatch.setattr(scenario_script, "ScenarioRunner", FakeScenarioRunner)

    exit_code = await scenario_script.run("smoke/dry.yaml")

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "===== JSON REPORT =====" in output
    assert "===== MARKDOWN REPORT =====" in output
    assert _host_local_capture_path() in output


def test_scenario_standalone_rejects_non_object_input_overrides(capsys):
    exit_code = scenario_script.main([
        "--dry-run",
        "--input-overrides-json",
        "[1]",
        "smoke/dry.yaml",
    ])

    assert exit_code == 2
    assert "must decode to a JSON object" in capsys.readouterr().err


def test_mcp_probe_loads_workspace_stdio_entry(tmp_path):
    workspace = tmp_path / "workspaces" / "isaac" / "instance-1"
    workspace.mkdir(parents=True)
    (workspace / ".mcp.json").write_text(
        json.dumps({
            "mcpServers": {
                "isaacsim-mcp-1": {
                    "type": "stdio",
                    "command": "cmd",
                    "args": [
                        "/c",
                        "uv",
                        "--directory",
                        "../../..",
                        "run",
                        "--no-sync",
                        "omniverse-kit-mcp",
                    ],
                    "env": {
                        "ISAAC_MCP_APP_PROFILE": "isaac-sim",
                        "ISAAC_MCP_INSTANCE_ID": "1",
                    },
                },
            },
        }),
        encoding="utf-8",
    )

    command, cwd, env = mcp_probe._load_workspace_stdio_entry(workspace)

    assert command == [
        "cmd",
        "/c",
        "uv",
        "--directory",
        "../../..",
        "run",
        "--no-sync",
        "omniverse-kit-mcp",
    ]
    assert cwd == workspace
    assert env == {
        "ISAAC_MCP_APP_PROFILE": "isaac-sim",
        "ISAAC_MCP_INSTANCE_ID": "1",
    }


def test_mcp_probe_summarizes_scenario_plan_shape():
    summary = mcp_probe._scenario_plan_probe_summary({
        "scenario_id": "robot_rtx_sensor_golden_workflow",
        "total_steps": 23,
        "preflight_requirements": {
            "runtime_info": {
                "checks": [
                    "tool_profile",
                    "robot_probe_unknown_profile_fallback_tool_order",
                ],
            },
            "scratch_stage": {"required": True},
            "simulation_play_gate": {
                "missing_before_required_step_count": 0,
            },
        },
        "simulation_state_summary": {
            "play_state_missing_count": 0,
            "requires_play_count": 2,
        },
        "simulation_state_steps": [{"id": "attach_top_lidar"}],
        "timeline_control_steps": [{"id": "play_for_sensor_data"}],
        "phases": {
            "cleanup": [
                {
                    "id": "__fallback_cleanup_reset",
                    "action": "reset",
                    "timeoutSeconds": 30.0,
                    "automatic": True,
                }
            ],
        },
        "retry_steps": [
            {
                "id": "read_lidar_point_cloud",
                "phase": "assert",
                "action": "sensor.lidar_get_point_cloud",
                "retries": {"maxAttempts": 3},
                "key_args": {"min_points": 513, "frames_to_wait": 180},
            }
        ],
        "live_validation_checklist": {
            "scratch_stage_required": True,
            "log_capture_recommended": True,
            "steps": [
                {"tool": "mcp_runtime_info"},
                {"tool": "kit_app_start"},
                {"tool": "scenario_validate"},
            ]
        },
    })

    assert summary == {
        "scenario_id": "robot_rtx_sensor_golden_workflow",
        "total_steps": 23,
        "required_fields_present": {
            "preflight_requirements": True,
            "simulation_state_summary": True,
            "simulation_state_steps": True,
            "timeline_control_steps": True,
            "live_validation_checklist": True,
        },
        "preflight_requirement_keys": [
            "runtime_info",
            "scratch_stage",
            "simulation_play_gate",
        ],
        "preflight_runtime_info_checks": [
            "tool_profile",
            "robot_probe_unknown_profile_fallback_tool_order",
        ],
        "play_state_missing_count": 0,
        "requires_play_count": 2,
        "simulation_state_step_count": 1,
        "timeline_control_step_count": 1,
        "automatic_cleanup_steps": [
            {
                "step_id": "__fallback_cleanup_reset",
                "action": "reset",
                "timeoutSeconds": 30.0,
            }
        ],
        "retry_step_count": 1,
        "retry_steps": [
            {
                "step_id": "read_lidar_point_cloud",
                "phase": "assert",
                "action": "sensor.lidar_get_point_cloud",
                "max_attempts": 3,
                "key_args": {"min_points": 513, "frames_to_wait": 180},
            }
        ],
        "live_validation_step_count": 3,
        "live_validation_tools": [
            "mcp_runtime_info",
            "kit_app_start",
            "scenario_validate",
        ],
        "scratch_stage_required": True,
        "log_capture_recommended": True,
    }


@pytest.mark.asyncio
async def test_mcp_probe_calls_scenario_validate_dry_run_with_plan_args(
    monkeypatch,
    capsys,
):
    sent_messages: list[dict] = []

    plan_payload = {
        "scenario_id": "official_asset_verify_live",
        "total_steps": 5,
        "diagnostic_steps": [],
        "evidence_steps": [{"id": "verify_pallet_asset"}],
        "stage_mutation_steps": [{"id": "verify_pallet_asset"}],
        "preflight_requirements": {
            "runtime_info": {
                "checks": ["tool_profile"],
            },
        },
        "live_validation_checklist": {
            "scratch_stage_required": True,
            "log_capture_recommended": True,
            "steps": [
                {"tool": "mcp_runtime_info"},
                {"tool": "scenario_validate"},
            ],
        },
    }
    dry_run_payload = {
        **plan_payload,
        "dry_run": True,
        "compiled": True,
        "steps": 5,
    }
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "fake-mcp", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "mcp_runtime_info"},
                    {"name": "scenario_plan"},
                    {"name": "scenario_validate"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "resources": [
                    {"uri": "isaacsim://scenario-schema"},
                    {"uri": "isaacsim://scenarios"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(plan_payload)},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {
                "content": [
                    {"type": "text", "text": json.dumps(dry_run_payload)},
                ],
            },
        },
    ]

    class FakeStdin:
        def write(self, data: bytes) -> None:
            sent_messages.append(json.loads(data.decode("utf-8")))

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeStdout:
        def __init__(self, payloads: list[dict]):
            self._lines = [
                (json.dumps(payload) + "\n").encode("utf-8")
                for payload in payloads
            ]

        async def readline(self) -> bytes:
            if not self._lines:
                return b""
            return self._lines.pop(0)

    class FakeProcess:
        def __init__(self, payloads: list[dict]):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout(payloads)

        async def wait(self) -> int:
            return 0

        def kill(self) -> None:
            pass

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess(responses)

    monkeypatch.setattr(
        mcp_probe.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    exit_code = await mcp_probe.probe(
        scenario_plan="smoke/official_asset_verify_live.yaml",
        scenario_validate_dry_run=True,
        input_overrides={"asset_name": "pallet"},
        required_plan_fields=(
            "diagnostic_steps",
            "evidence_steps",
            "stage_mutation_steps",
        ),
        required_live_validation_tools=(
            "mcp_runtime_info",
            "scenario_validate",
        ),
        expected_preflight_runtime_checks=("tool_profile",),
        expect_scratch_stage_required=True,
        expect_log_capture_recommended=True,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "=== scenario_validate dry-run smoke ===" in output
    assert "snapshot: tmp_mcp_surface.json" in output
    assert str(mcp_probe.REPO_ROOT) not in output
    tool_calls = [
        message
        for message in sent_messages
        if message.get("method") == "tools/call"
    ]
    assert [call["params"]["name"] for call in tool_calls] == [
        "scenario_plan",
        "scenario_validate",
    ]
    assert tool_calls[0]["params"]["arguments"] == {
        "scenario_path": "smoke/official_asset_verify_live.yaml",
        "input_overrides": {"asset_name": "pallet"},
    }
    assert tool_calls[1]["params"]["arguments"] == {
        "scenario_path": "smoke/official_asset_verify_live.yaml",
        "dry_run": True,
        "input_overrides": {"asset_name": "pallet"},
    }


@pytest.mark.asyncio
async def test_mcp_probe_live_scenario_uses_canonical_wrapper_order(
    monkeypatch,
    capsys,
):
    sent_messages: list[dict] = []
    runtime_payload = {
        "tool_profile": "full",
        "app_profile": "isaac-sim",
        "tool_count": 152,
        "source_newer_than_import": False,
        "restart_required_for_latest_mcp_code": False,
    }
    plan_payload = {
        "scenario_id": "robot_rtx_sensor_golden_workflow",
        "total_steps": 32,
        "preflight_requirements": {
            "runtime_info": {
                "checks": [
                    "robot_probe_unknown_profile_fallback_tool_order",
                ],
            },
        },
        "simulation_state_summary": {
            "play_state_missing_count": 0,
            "requires_play_count": 2,
        },
        "simulation_state_steps": [],
        "timeline_control_steps": [],
        "phases": {
            "cleanup": [
                {
                    "id": "__fallback_cleanup_reset",
                    "module": "extension",
                    "action": "reset",
                    "args": {},
                    "timeoutSeconds": 30.0,
                    "automatic": True,
                }
            ],
        },
        "retry_steps": [],
        "live_validation_checklist": {
            "scratch_stage_required": True,
            "log_capture_recommended": True,
            "steps": [
                {"tool": "mcp_runtime_info"},
                {"tool": "kit_app_start"},
                {"tool": "simulation_get_status"},
                {"tool": "scenario_plan"},
                {"tool": "scenario_validate"},
                {"tool": "extension_clear_logs"},
                {"tool": "scenario_validate"},
                {"tool": "scenario_last_report"},
                {"tool": "extension_capture_logs"},
            ],
        },
    }
    dry_run_payload = {
        **plan_payload,
        "dry_run": True,
        "compiled": True,
        "steps": 32,
    }
    live_report_payload = {
        "scenario_id": "robot_rtx_sensor_golden_workflow",
        "status": "failed",
        "passed_steps": 31,
        "failed_steps": 1,
        "skipped_steps": 0,
        "continued_steps": 0,
        "fatal_failed_steps": 1,
        "cleanup_failed_steps": 0,
        "failure_summary": [
            {
                "step_id": "read_lidar_point_cloud",
                "status": "failed",
                "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            }
        ],
        "diagnostic_next_actions": [
            {
                "step_id": "read_lidar_point_cloud",
                "status": "failed",
                "diagnostics.reason": "point_count_below_minimum",
                "diagnostics.num_points": 512,
                "diagnostics.min_points": 513,
            },
        ],
        "evidence_summary": [
            {
                "step_id": "capture_visible_result",
                "evidence_kind": "visual_capture",
                "status": "passed",
                "attempts": 1,
                "passed": True,
            },
        ],
    }
    module_pass = {"ok": True, "status": "passed", "data": {"status": "ready"}}
    log_capture_pass = _log_capture_pass()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "fake-mcp", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "mcp_runtime_info"},
                    {"name": "kit_app_start"},
                    {"name": "simulation_get_status"},
                    {"name": "scenario_plan"},
                    {"name": "scenario_validate"},
                    {"name": "extension_clear_logs"},
                    {"name": "scenario_last_report"},
                    {"name": "extension_capture_logs"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "resources": [
                    {"uri": "isaacsim://scenario-schema"},
                    {"uri": "isaacsim://scenarios"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"content": [{"type": "text", "text": json.dumps(runtime_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 6,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "result": {"content": [{"type": "text", "text": json.dumps(plan_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 8,
            "result": {"content": [{"type": "text", "text": json.dumps(dry_run_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 9,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 10,
            "result": {
                "content": [{"type": "text", "text": json.dumps(live_report_payload)}]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 11,
            "result": {
                "content": [{"type": "text", "text": "# Scenario Report: redacted"}]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 12,
            "result": {
                "content": [{"type": "text", "text": json.dumps(log_capture_pass)}]
            },
        },
    ]

    class FakeStdin:
        def write(self, data: bytes) -> None:
            sent_messages.append(json.loads(data.decode("utf-8")))

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeStdout:
        def __init__(self, payloads: list[dict]):
            self._lines = [
                (json.dumps(payload) + "\n").encode("utf-8")
                for payload in payloads
            ]

        async def readline(self) -> bytes:
            if not self._lines:
                return b""
            return self._lines.pop(0)

    class FakeProcess:
        def __init__(self, payloads: list[dict]):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout(payloads)

        async def wait(self) -> int:
            return 0

        def kill(self) -> None:
            pass

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess(responses)

    monkeypatch.setattr(
        mcp_probe.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    exit_code = await mcp_probe.probe(
        workspace=Path("workspaces/isaac/instance-1"),
        runtime_info=True,
        scenario_plan="smoke/robot_rtx_sensor_golden_workflow.yaml",
        scenario_validate_dry_run=True,
        scenario_validate_live=True,
        required_plan_fields=("preflight_requirements",),
        expected_preflight_runtime_checks=(
            "robot_probe_unknown_profile_fallback_tool_order",
        ),
        expect_scratch_stage_required=True,
        expect_log_capture_recommended=True,
        expected_automatic_cleanup_timeouts=(
            ("__fallback_cleanup_reset", 30.0),
        ),
        expect_live_status="failed",
        expected_live_evidence_kinds=("visual_capture",),
        expected_live_evidence_fields=(
            ("visual_capture", "status", "passed"),
            ("capture_visible_result", "attempts", 1),
            ("capture_visible_result", "passed", True),
        ),
        expected_live_evidence_field_minimums=(
            ("capture_visible_result", "attempts", 1.0),
        ),
        expect_live_cleanup_failures=0,
        expected_live_failure_step_errors=(
            (
                "read_lidar_point_cloud",
                "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            ),
        ),
        expect_live_diagnostic_next_actions_min=1,
        expected_live_diagnostic_fields=(
            (
                "read_lidar_point_cloud",
                "diagnostics.reason",
                "point_count_below_minimum",
            ),
        ),
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"automatic_cleanup_steps": [' in output
    assert '"timeoutSeconds": 30.0' in output
    assert "=== scenario_validate live summary ===" in output
    assert '"failure_steps": [' in output
    assert '"evidence_kinds": [' in output
    assert '"evidence": [' in output
    assert '"cleanup_failed_steps": 0' in output
    assert '"diagnostic_next_action_count": 1' in output
    assert "# Scenario Report: redacted" in output
    tool_calls = [
        message
        for message in sent_messages
        if message.get("method") == "tools/call"
    ]
    assert [call["params"]["name"] for call in tool_calls] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "scenario_plan",
        "scenario_validate",
        "extension_clear_logs",
        "scenario_validate",
        "scenario_last_report",
        "extension_capture_logs",
    ]
    assert tool_calls[6]["params"]["arguments"] == {
        "scenario_path": "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "report_format": "json",
        "redact_local_paths": True,
    }
    assert tool_calls[7]["params"]["arguments"] == {
        "report_format": "markdown",
        "redact_local_paths": True,
    }
    assert tool_calls[8]["params"]["arguments"] == {
        "level": "WARN",
        "stop_after_capture": True,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "evidence_rows",
        "cleanup_failed_steps",
        "expected_live_evidence_fields",
        "expected_message",
        "absent_message",
    ),
    (
        (
            [{"step_id": "evidence_0", "evidence_kind": "visual_capture"}],
            0,
            (),
            "live evidence kind 'official_asset_verify' was not found",
            "scenario_validate live cleanup expectation mismatch:",
        ),
        (
            [
                {
                    "step_id": "verify_pallet_asset",
                    "evidence_kind": "official_asset_verify",
                    "verification_status": "load_verified",
                },
            ],
            1,
            (),
            "cleanup_failed_steps expected 0, got 1",
            "scenario_validate live evidence expectation mismatch:",
        ),
        (
            [
                {
                    "step_id": "verify_pallet_asset",
                    "evidence_kind": "official_asset_verify",
                    "verification_status": "discovered",
                },
            ],
            0,
            (("official_asset_verify", "verification_status", "load_verified"),),
            (
                "live evidence row 'official_asset_verify' field "
                "'verification_status' expected 'load_verified', got ['discovered']"
            ),
            "scenario_validate live evidence expectation mismatch:",
        ),
    ),
)
async def test_mcp_probe_live_expectation_mismatches_set_nonzero_exit(
    monkeypatch,
    capsys,
    evidence_rows,
    cleanup_failed_steps,
    expected_live_evidence_fields,
    expected_message,
    absent_message,
):
    sent_messages: list[dict] = []
    plan_payload = {
        "scenario_id": "official_asset_verify_live",
        "total_steps": 5,
        "simulation_state_summary": {},
        "simulation_state_steps": [],
        "timeline_control_steps": [],
    }
    dry_run_payload = {
        **plan_payload,
        "dry_run": True,
        "compiled": True,
        "steps": 5,
    }
    live_report_payload = {
        "scenario_id": "official_asset_verify_live",
        "status": "passed",
        "passed_steps": 5,
        "failed_steps": 0,
        "skipped_steps": 0,
        "continued_steps": 0,
        "fatal_failed_steps": 0,
        "cleanup_failed_steps": cleanup_failed_steps,
        "failure_summary": [],
        "diagnostic_next_actions": [],
        "evidence_summary": evidence_rows,
    }
    module_pass = {"ok": True, "status": "passed", "data": {"status": "ready"}}
    log_capture_pass = _log_capture_pass()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "fake-mcp", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "mcp_runtime_info"},
                    {"name": "kit_app_start"},
                    {"name": "simulation_get_status"},
                    {"name": "scenario_plan"},
                    {"name": "scenario_validate"},
                    {"name": "extension_clear_logs"},
                    {"name": "scenario_last_report"},
                    {"name": "extension_capture_logs"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "resources": [
                    {"uri": "isaacsim://scenario-schema"},
                    {"uri": "isaacsim://scenarios"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"content": [{"type": "text", "text": "{}"}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 6,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "result": {"content": [{"type": "text", "text": json.dumps(plan_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 8,
            "result": {"content": [{"type": "text", "text": json.dumps(dry_run_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 9,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 10,
            "result": {
                "content": [{"type": "text", "text": json.dumps(live_report_payload)}]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 11,
            "result": {
                "content": [{"type": "text", "text": "# Scenario Report: redacted"}]
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 12,
            "result": {
                "content": [{"type": "text", "text": json.dumps(log_capture_pass)}]
            },
        },
    ]
    _install_fake_mcp_stdio(
        monkeypatch,
        responses=responses,
        sent_messages=sent_messages,
    )

    exit_code = await mcp_probe.probe(
        workspace=Path("workspaces/isaac/instance-1"),
        scenario_plan="smoke/official_asset_verify_live.yaml",
        scenario_validate_dry_run=True,
        scenario_validate_live=True,
        expected_live_evidence_kinds=("official_asset_verify",),
        expected_live_evidence_fields=expected_live_evidence_fields,
        expect_live_cleanup_failures=0,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert expected_message in output
    assert absent_message not in output
    assert "# Scenario Report: redacted" in output


@pytest.mark.asyncio
async def test_mcp_probe_live_preflight_only_skips_scenario_calls(
    monkeypatch,
    capsys,
):
    sent_messages: list[dict] = []
    runtime_payload = {
        "tool_profile": "full",
        "app_profile": "isaac-sim",
        "tool_count": 152,
        "source_newer_than_import": False,
        "restart_required_for_latest_mcp_code": False,
    }
    module_pass = {"ok": True, "status": "passed", "data": {"status": "ready"}}
    log_capture_pass = _log_capture_pass()
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "fake-mcp", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "mcp_runtime_info"},
                    {"name": "kit_app_start"},
                    {"name": "simulation_get_status"},
                    {"name": "extension_clear_logs"},
                    {"name": "extension_capture_logs"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "resources": [
                    {"uri": "isaacsim://scenario-schema"},
                    {"uri": "isaacsim://scenarios"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"content": [{"type": "text", "text": json.dumps(runtime_payload)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 6,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 8,
            "result": {
                "content": [{"type": "text", "text": json.dumps(log_capture_pass)}]
            },
        },
    ]

    class FakeStdin:
        def write(self, data: bytes) -> None:
            sent_messages.append(json.loads(data.decode("utf-8")))

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    class FakeStdout:
        def __init__(self, payloads: list[dict]):
            self._lines = [
                (json.dumps(payload) + "\n").encode("utf-8")
                for payload in payloads
            ]

        async def readline(self) -> bytes:
            if not self._lines:
                return b""
            return self._lines.pop(0)

    class FakeProcess:
        def __init__(self, payloads: list[dict]):
            self.stdin = FakeStdin()
            self.stdout = FakeStdout(payloads)

        async def wait(self) -> int:
            return 0

        def kill(self) -> None:
            pass

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess(responses)

    monkeypatch.setattr(
        mcp_probe.asyncio,
        "create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    exit_code = await mcp_probe.probe(
        workspace=Path("workspaces/isaac/instance-1"),
        live_preflight=True,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "=== extension_capture_logs WARN+ preflight ===" in output
    tool_calls = [
        message
        for message in sent_messages
        if message.get("method") == "tools/call"
    ]
    assert [call["params"]["name"] for call in tool_calls] == [
        "mcp_runtime_info",
        "kit_app_start",
        "simulation_get_status",
        "extension_clear_logs",
        "extension_capture_logs",
    ]
    assert tool_calls[-1]["params"]["arguments"] == {
        "level": "WARN",
        "stop_after_capture": True,
    }


@pytest.mark.asyncio
async def test_mcp_probe_live_preflight_fails_when_log_capture_does_not_close(
    monkeypatch,
    capsys,
):
    sent_messages: list[dict] = []
    module_pass = {"ok": True, "status": "passed", "data": {"status": "ready"}}
    log_capture_open = {
        "ok": True,
        "status": "passed",
        "data": {
            "capture_running": True,
            "capture_stop_requested": True,
            "capture_stop_completed": False,
            "capture_stop_timed_out": True,
            "capture_stop_timeout_s": 1.0,
        },
    }
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "serverInfo": {"name": "fake-mcp", "version": "0"},
                "capabilities": {"tools": {}, "resources": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "mcp_runtime_info"},
                    {"name": "kit_app_start"},
                    {"name": "simulation_get_status"},
                    {"name": "extension_clear_logs"},
                    {"name": "extension_capture_logs"},
                ],
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"resources": []},
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"content": [{"type": "text", "text": "{}"}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 6,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
        },
        {
            "jsonrpc": "2.0",
            "id": 8,
            "result": {
                "content": [{"type": "text", "text": json.dumps(log_capture_open)}]
            },
        },
    ]
    _install_fake_mcp_stdio(
        monkeypatch,
        responses=responses,
        sent_messages=sent_messages,
    )

    exit_code = await mcp_probe.probe(
        workspace=Path("workspaces/isaac/instance-1"),
        live_preflight=True,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "extension_capture_logs close expectation mismatch:" in output
    assert "data.capture_stop_completed expected True, got False" in output
    assert "data.capture_stop_timed_out expected False, got True" in output


def test_mcp_probe_parses_required_live_validation_tools():
    assert mcp_probe._parse_required_tool_sequence(
        "mcp_runtime_info, kit_app_start,, scenario_plan ",
    ) == (
        "mcp_runtime_info",
        "kit_app_start",
        "scenario_plan",
    )


def test_mcp_probe_live_validation_tool_mismatches_are_empty_for_exact_order():
    summary = {
        "live_validation_tools": [
            "mcp_runtime_info",
            "kit_app_start",
            "scenario_plan",
        ],
    }

    assert mcp_probe._live_validation_tool_mismatches(
        summary,
        (
            "mcp_runtime_info",
            "kit_app_start",
            "scenario_plan",
        ),
    ) == []


def test_mcp_probe_live_validation_tool_mismatches_report_order_drift():
    summary = {
        "live_validation_tools": [
            "kit_app_start",
            "mcp_runtime_info",
        ],
    }

    assert mcp_probe._live_validation_tool_mismatches(
        summary,
        (
            "mcp_runtime_info",
            "kit_app_start",
        ),
    ) == [
        "live_validation_tools expected "
        "['mcp_runtime_info', 'kit_app_start'], got "
        "['kit_app_start', 'mcp_runtime_info']",
    ]


def test_mcp_probe_parses_expected_retry_key_args():
    assert mcp_probe._parse_expected_retry_key_args([
        "read_lidar_point_cloud:min_points=513",
        "read_lidar_point_cloud:fail_on_warning=true",
        'read_lidar_point_cloud:mode="controlled"',
    ]) == (
        ("read_lidar_point_cloud", "min_points", 513),
        ("read_lidar_point_cloud", "fail_on_warning", True),
        ("read_lidar_point_cloud", "mode", "controlled"),
    )


def test_mcp_probe_rejects_malformed_retry_key_arg_expectation():
    with pytest.raises(ValueError, match="step_id:key=value"):
        mcp_probe._parse_expected_retry_key_args(["read_lidar_point_cloud"])


def test_mcp_probe_parses_expected_automatic_cleanup_timeouts():
    assert mcp_probe._parse_expected_automatic_cleanup_timeouts([
        "__fallback_cleanup_reset=30",
    ]) == (("__fallback_cleanup_reset", 30.0),)


def test_mcp_probe_rejects_malformed_automatic_cleanup_timeout():
    with pytest.raises(ValueError, match="step_id=seconds"):
        mcp_probe._parse_expected_automatic_cleanup_timeouts([
            "__fallback_cleanup_reset",
        ])
    with pytest.raises(ValueError, match="seconds must be numeric"):
        mcp_probe._parse_expected_automatic_cleanup_timeouts([
            "__fallback_cleanup_reset=soon",
        ])


def test_mcp_probe_retry_key_arg_mismatches_are_empty_for_expected_value():
    summary = {
        "retry_steps": [
            {
                "step_id": "read_lidar_point_cloud",
                "key_args": {"min_points": 513},
            },
        ],
    }

    assert mcp_probe._retry_key_arg_mismatches(
        summary,
        (("read_lidar_point_cloud", "min_points", 513),),
    ) == []


def test_mcp_probe_retry_key_arg_mismatches_report_drift():
    summary = {
        "retry_steps": [
            {
                "step_id": "read_lidar_point_cloud",
                "key_args": {"min_points": 512},
            },
        ],
    }

    assert mcp_probe._retry_key_arg_mismatches(
        summary,
        (("read_lidar_point_cloud", "min_points", 513),),
    ) == [
        "retry step 'read_lidar_point_cloud' key_args['min_points'] "
        "expected 513, got 512",
    ]
    assert mcp_probe._retry_key_arg_mismatches(
        summary,
        (("read_lidar_point_cloud", "frames_to_wait", 180),),
    ) == [
        "retry step 'read_lidar_point_cloud' "
        "key_args['frames_to_wait'] was not found",
    ]
    assert mcp_probe._retry_key_arg_mismatches(
        summary,
        (("missing_step", "min_points", 513),),
    ) == ["retry step 'missing_step' was not found"]


def test_mcp_probe_automatic_cleanup_timeout_mismatches_are_empty_for_expected_value():
    summary = {
        "automatic_cleanup_steps": [
            {
                "step_id": "__fallback_cleanup_reset",
                "timeoutSeconds": 30.0,
            },
        ],
    }

    assert mcp_probe._automatic_cleanup_timeout_mismatches(
        summary,
        (("__fallback_cleanup_reset", 30.0),),
    ) == []


def test_mcp_probe_automatic_cleanup_timeout_mismatches_report_drift():
    summary = {
        "automatic_cleanup_steps": [
            {
                "step_id": "__fallback_cleanup_reset",
                "timeoutSeconds": 60.0,
            },
        ],
    }

    assert mcp_probe._automatic_cleanup_timeout_mismatches(
        summary,
        (("__fallback_cleanup_reset", 30.0),),
    ) == [
        "automatic cleanup step '__fallback_cleanup_reset' timeoutSeconds "
        "expected 30.0, got 60.0",
    ]
    assert mcp_probe._automatic_cleanup_timeout_mismatches(
        summary,
        (("missing_cleanup", 30.0),),
    ) == ["automatic cleanup step 'missing_cleanup' was not found"]


def test_mcp_probe_live_evidence_kind_mismatches_are_empty_for_expected_kind():
    summary = {
        "evidence_kinds": [
            "rtx_lidar_point_cloud",
            "viewport_framing",
            "visual_capture",
        ],
    }

    assert mcp_probe._live_evidence_kind_mismatches(
        summary,
        ("rtx_lidar_point_cloud", "visual_capture"),
    ) == []


def test_mcp_probe_live_evidence_kind_mismatches_report_missing_kind():
    assert mcp_probe._live_evidence_kind_mismatches(
        {"evidence_kinds": ["visual_capture"]},
        ("rtx_lidar_point_cloud",),
    ) == ["live evidence kind 'rtx_lidar_point_cloud' was not found"]
    assert mcp_probe._live_evidence_kind_mismatches(
        {},
        ("visual_capture",),
    ) == ["evidence_kinds summary is missing or malformed"]


def test_mcp_probe_parses_expected_live_evidence_fields():
    assert mcp_probe._parse_expected_live_evidence_fields([
        "official_asset_verify:verification_status=load_verified",
        "verify_pallet_asset:attempt=2",
        "official_asset_verify:stale=false",
        'official_asset_verify:name="aluminumpallet_a01.usd"',
    ]) == (
        ("official_asset_verify", "verification_status", "load_verified"),
        ("verify_pallet_asset", "attempt", 2),
        ("official_asset_verify", "stale", False),
        ("official_asset_verify", "name", "aluminumpallet_a01.usd"),
    )


def test_mcp_probe_rejects_malformed_live_evidence_field_expectation():
    with pytest.raises(ValueError, match="selector:key=value"):
        mcp_probe._parse_expected_live_evidence_fields([
            "official_asset_verify",
        ])
    with pytest.raises(ValueError, match="selector:key=value"):
        mcp_probe._parse_expected_live_evidence_fields([
            "official_asset_verify:verification_status",
        ])
    with pytest.raises(ValueError, match="non-empty"):
        mcp_probe._parse_expected_live_evidence_fields([
            "official_asset_verify:=load_verified",
        ])


def test_mcp_probe_parses_expected_live_evidence_field_minimums():
    assert mcp_probe._parse_expected_live_evidence_field_minimums([
        "read_lidar_point_cloud:num_points=1",
        "capture_visible_result:pixel_variance_average=0.5",
    ]) == (
        ("read_lidar_point_cloud", "num_points", 1.0),
        ("capture_visible_result", "pixel_variance_average", 0.5),
    )


def test_mcp_probe_rejects_malformed_live_evidence_field_minimum():
    with pytest.raises(ValueError, match="selector:key=minimum"):
        mcp_probe._parse_expected_live_evidence_field_minimums([
            "read_lidar_point_cloud",
        ])
    with pytest.raises(ValueError, match="selector:key=minimum"):
        mcp_probe._parse_expected_live_evidence_field_minimums([
            "read_lidar_point_cloud:num_points",
        ])
    with pytest.raises(ValueError, match="non-empty"):
        mcp_probe._parse_expected_live_evidence_field_minimums([
            "read_lidar_point_cloud:=1",
        ])
    with pytest.raises(ValueError, match="minimum must be numeric"):
        mcp_probe._parse_expected_live_evidence_field_minimums([
            "read_lidar_point_cloud:num_points=many",
        ])


def test_mcp_probe_live_summary_keeps_public_robot_rtx_evidence_fields():
    summary = mcp_probe._scenario_live_report_summary({
        "evidence_summary": [
            {
                "step_id": "read_lidar_point_cloud",
                "evidence_kind": "rtx_lidar_point_cloud",
                "num_points": 512,
                "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
                "frames_waited": 180,
                "warning": None,
                "truncated": False,
            },
            {
                "step_id": "frame_robot_and_sensors",
                "evidence_kind": "viewport_framing",
                "prim_count": 4,
                "bbox_empty": False,
                "camera_path": "/OmniverseKit_Persp",
            },
            {
                "step_id": "capture_visible_result",
                "evidence_kind": "visual_capture",
                "capture_path": "<local-capture>/capture.png",
                "sha256": "abc123",
                "width": 1280,
                "height": 720,
                "passed": True,
            },
        ],
    })

    evidence = {
        row["step_id"]: row
        for row in summary["evidence"]
    }
    assert evidence["read_lidar_point_cloud"] == {
        "step_id": "read_lidar_point_cloud",
        "evidence_kind": "rtx_lidar_point_cloud",
        "num_points": 512,
        "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
        "frames_waited": 180,
        "warning": None,
        "truncated": False,
    }
    assert evidence["frame_robot_and_sensors"] == {
        "step_id": "frame_robot_and_sensors",
        "evidence_kind": "viewport_framing",
        "prim_count": 4,
        "bbox_empty": False,
    }
    assert evidence["capture_visible_result"] == {
        "step_id": "capture_visible_result",
        "evidence_kind": "visual_capture",
        "sha256": "abc123",
        "width": 1280,
        "height": 720,
        "passed": True,
    }


def test_mcp_probe_live_summary_keeps_public_official_asset_evidence_fields():
    summary = mcp_probe._scenario_live_report_summary({
        "evidence_summary": [
            {
                "step_id": "verify_pallet_asset",
                "evidence_kind": "official_asset_verify",
                "kind": "asset",
                "name": "aluminumpallet_a01.usd",
                "app_profile": "isaac-sim",
                "verification_status": "load_verified",
                "load_quality": "content_verified_no_bbox",
                "attempt": 1,
                "timeout_s": 180.0,
                "retry_count": 1,
                "canonical_url": "https://example.invalid/asset.usd",
            },
        ],
    })

    assert summary["evidence"] == [
        {
            "step_id": "verify_pallet_asset",
            "evidence_kind": "official_asset_verify",
            "kind": "asset",
            "name": "aluminumpallet_a01.usd",
            "app_profile": "isaac-sim",
            "verification_status": "load_verified",
            "load_quality": "content_verified_no_bbox",
            "attempt": 1,
            "timeout_s": 180.0,
            "retry_count": 1,
        },
    ]


def test_mcp_probe_live_evidence_field_minimum_mismatches_are_empty():
    summary = {
        "evidence": [
            {
                "step_id": "read_lidar_point_cloud",
                "evidence_kind": "rtx_lidar_point_cloud",
                "num_points": 512,
            },
            {
                "step_id": "capture_visible_result",
                "evidence_kind": "visual_capture",
                "pixel_variance_average": 1107.7,
            },
        ],
    }

    assert mcp_probe._live_evidence_field_minimum_mismatches(
        summary,
        (
            ("read_lidar_point_cloud", "num_points", 1.0),
            ("visual_capture", "pixel_variance_average", 1.0),
        ),
    ) == []


def test_mcp_probe_live_evidence_field_minimum_mismatches_report_drift():
    summary = {
        "evidence": [
            {
                "step_id": "read_lidar_point_cloud",
                "evidence_kind": "rtx_lidar_point_cloud",
                "num_points": 0,
                "frames_waited": "many",
            },
        ],
    }

    assert mcp_probe._live_evidence_field_minimum_mismatches(
        summary,
        (("read_lidar_point_cloud", "num_points", 1.0),),
    ) == [
        "live evidence row 'read_lidar_point_cloud' field 'num_points' "
        "expected at least 1.0, got [0]",
    ]
    assert mcp_probe._live_evidence_field_minimum_mismatches(
        summary,
        (("read_lidar_point_cloud", "frames_waited", 1.0),),
    ) == [
        "live evidence row 'read_lidar_point_cloud' field 'frames_waited' "
        "expected at least 1.0, got ['many']",
    ]
    assert mcp_probe._live_evidence_field_minimum_mismatches(
        summary,
        (("read_lidar_point_cloud", "pixel_variance_average", 1.0),),
    ) == [
        "live evidence row 'read_lidar_point_cloud' field "
        "'pixel_variance_average' was not found",
    ]
    assert mcp_probe._live_evidence_field_minimum_mismatches(
        summary,
        (("visual_capture", "pixel_variance_average", 1.0),),
    ) == ["live evidence row 'visual_capture' was not found"]
    assert mcp_probe._live_evidence_field_minimum_mismatches(
        {},
        (("read_lidar_point_cloud", "num_points", 1.0),),
    ) == ["evidence summary is missing or malformed"]


def test_mcp_probe_live_evidence_field_mismatches_are_empty_for_expected_value():
    summary = {
        "evidence": [
            {
                "step_id": "verify_pallet_asset",
                "evidence_kind": "official_asset_verify",
                "verification_status": "load_verified",
                "kind": "asset",
                "app_profile": "isaac-sim",
            },
        ],
    }

    assert mcp_probe._live_evidence_field_mismatches(
        summary,
        (
            ("official_asset_verify", "verification_status", "load_verified"),
            ("verify_pallet_asset", "app_profile", "isaac-sim"),
        ),
    ) == []


def test_mcp_probe_live_evidence_field_mismatches_report_drift():
    summary = {
        "evidence": [
            {
                "step_id": "verify_pallet_asset",
                "evidence_kind": "official_asset_verify",
                "verification_status": "discovered",
                "kind": "asset",
            },
        ],
    }

    assert mcp_probe._live_evidence_field_mismatches(
        summary,
        (("official_asset_verify", "verification_status", "load_verified"),),
    ) == [
        "live evidence row 'official_asset_verify' field 'verification_status' "
        "expected 'load_verified', got ['discovered']",
    ]
    assert mcp_probe._live_evidence_field_mismatches(
        summary,
        (("official_asset_verify", "app_profile", "isaac-sim"),),
    ) == [
        "live evidence row 'official_asset_verify' field 'app_profile' "
        "was not found",
    ]
    assert mcp_probe._live_evidence_field_mismatches(
        summary,
        (("visual_capture", "status", "passed"),),
    ) == ["live evidence row 'visual_capture' was not found"]
    assert mcp_probe._live_evidence_field_mismatches(
        {},
        (("official_asset_verify", "verification_status", "load_verified"),),
    ) == ["evidence summary is missing or malformed"]


def test_mcp_probe_live_cleanup_failure_mismatches_are_empty_for_expected_count():
    assert mcp_probe._live_cleanup_failure_mismatches(
        {"cleanup_failed_steps": 0},
        0,
    ) == []


def test_mcp_probe_live_cleanup_failure_mismatches_report_drift():
    assert mcp_probe._live_cleanup_failure_mismatches(
        {"cleanup_failed_steps": 1},
        0,
    ) == ["cleanup_failed_steps expected 0, got 1"]
    assert mcp_probe._live_cleanup_failure_mismatches(
        {},
        0,
    ) == ["cleanup_failed_steps expected 0, got None"]


def test_mcp_probe_parses_expected_live_failure_step_errors():
    assert mcp_probe._parse_expected_live_failure_step_errors([
        "read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
    ]) == (
        (
            "read_lidar_point_cloud",
            "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
        ),
    )


def test_mcp_probe_rejects_malformed_live_failure_step_error_expectation():
    with pytest.raises(ValueError, match="step_id=ERROR_CODE"):
        mcp_probe._parse_expected_live_failure_step_errors([
            "read_lidar_point_cloud",
        ])
    with pytest.raises(ValueError, match="non-empty"):
        mcp_probe._parse_expected_live_failure_step_errors(["=ERROR_CODE"])


def test_mcp_probe_live_failure_step_error_mismatches_are_empty_for_expected_code():
    summary = {
        "failure_steps": [
            {
                "step_id": "read_lidar_point_cloud",
                "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            },
        ],
    }

    assert mcp_probe._live_failure_step_error_mismatches(
        summary,
        (
            (
                "read_lidar_point_cloud",
                "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            ),
        ),
    ) == []


def test_mcp_probe_live_failure_step_error_mismatches_report_drift():
    summary = {
        "failure_steps": [
            {
                "step_id": "read_lidar_point_cloud",
                "error_code": "SENSOR_LIDAR_TIMEOUT",
            },
        ],
    }

    assert mcp_probe._live_failure_step_error_mismatches(
        summary,
        (
            (
                "read_lidar_point_cloud",
                "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            ),
        ),
    ) == [
        "live failure step 'read_lidar_point_cloud' error_code expected "
        "'SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS', got 'SENSOR_LIDAR_TIMEOUT'",
    ]
    assert mcp_probe._live_failure_step_error_mismatches(
        summary,
        (("missing_step", "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"),),
    ) == ["live failure step 'missing_step' was not found"]
    assert mcp_probe._live_failure_step_error_mismatches(
        {},
        (("read_lidar_point_cloud", "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS"),),
    ) == ["failure_steps summary is missing or malformed"]


def test_mcp_probe_live_diagnostic_next_action_mismatches_are_empty_for_minimum():
    assert mcp_probe._live_diagnostic_next_action_mismatches(
        {"diagnostic_next_action_count": 4},
        1,
    ) == []


def test_mcp_probe_live_diagnostic_next_action_mismatches_report_drift():
    assert mcp_probe._live_diagnostic_next_action_mismatches(
        {"diagnostic_next_action_count": 0},
        1,
    ) == ["diagnostic_next_action_count expected at least 1, got 0"]
    assert mcp_probe._live_diagnostic_next_action_mismatches(
        {},
        1,
    ) == ["diagnostic_next_action_count expected at least 1, got None"]


def test_mcp_probe_parses_expected_live_diagnostic_fields():
    assert mcp_probe._parse_expected_live_diagnostic_fields([
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum",
        "read_lidar_point_cloud:diagnostics.num_points=512",
        'read_lidar_point_cloud:source="step"',
    ]) == (
        (
            "read_lidar_point_cloud",
            "diagnostics.reason",
            "point_count_below_minimum",
        ),
        ("read_lidar_point_cloud", "diagnostics.num_points", 512),
        ("read_lidar_point_cloud", "source", "step"),
    )


def test_mcp_probe_rejects_malformed_live_diagnostic_field():
    with pytest.raises(ValueError, match="step_id:key=value"):
        mcp_probe._parse_expected_live_diagnostic_fields([
            "read_lidar_point_cloud",
        ])
    with pytest.raises(ValueError, match="step_id:key=value"):
        mcp_probe._parse_expected_live_diagnostic_fields([
            "read_lidar_point_cloud:diagnostics.reason",
        ])
    with pytest.raises(ValueError, match="non-empty"):
        mcp_probe._parse_expected_live_diagnostic_fields([
            "read_lidar_point_cloud:=point_count_below_minimum",
        ])


def test_mcp_probe_live_summary_keeps_public_diagnostic_fields():
    summary = mcp_probe._scenario_live_report_summary({
        "diagnostic_next_actions": [
            {
                "step_id": "read_lidar_point_cloud",
                "phase": "act",
                "source": "step",
                "status": "failed",
                "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
                "diagnostics.reason": "point_count_below_minimum",
                "diagnostics.num_points": 512,
                "diagnostics.min_points": 513,
                "diagnostics.fallback_tool_order": [
                    "simulation_step",
                    "sensor_lidar_get_point_cloud",
                    "extension_capture_logs",
                ],
                "diagnostics.cached_lidar_instance": True,
                "diagnostics.raw_local_path": "<local-log>/log.txt",
            },
            {
                "step_id": "verify_pallet_asset",
                "phase": "assert",
                "source": "step",
                "status": "failed",
                "error_code": "OFFICIAL_ASSET_VERIFY_ERROR",
                "diagnostics.reason": "asset_load_quality_failed",
                "diagnostics.target_status": "load_verified",
                "diagnostics.current_catalog_status": "url_validated",
                "diagnostics.error_type": "TimeoutError",
                "diagnostics.failure_codes": ["ASSET_BBOX_EMPTY"],
                "diagnostics.upstream_error_code": "OFFICIAL_ASSET_VERIFY_ERROR",
                "diagnostics.timeout_s": 180.0,
                "diagnostics.asset_checks": {
                    "load_quality": "empty_content",
                    "content_has_bbox": False,
                },
                "diagnostics.material_checks": {
                    "created_test_prim": False,
                    "binding_verified": False,
                },
            },
        ],
    })

    assert summary["diagnostic_next_actions"] == [
        {
            "step_id": "read_lidar_point_cloud",
            "phase": "act",
            "source": "step",
            "status": "failed",
            "error_code": "SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
            "diagnostics.reason": "point_count_below_minimum",
            "diagnostics.num_points": 512,
            "diagnostics.min_points": 513,
            "diagnostics.fallback_tool_order": [
                "simulation_step",
                "sensor_lidar_get_point_cloud",
                "extension_capture_logs",
            ],
            "diagnostics.cached_lidar_instance": True,
        },
        {
            "step_id": "verify_pallet_asset",
            "phase": "assert",
            "source": "step",
            "status": "failed",
            "error_code": "OFFICIAL_ASSET_VERIFY_ERROR",
            "diagnostics.reason": "asset_load_quality_failed",
            "diagnostics.target_status": "load_verified",
            "diagnostics.current_catalog_status": "url_validated",
            "diagnostics.error_type": "TimeoutError",
            "diagnostics.failure_codes": ["ASSET_BBOX_EMPTY"],
            "diagnostics.upstream_error_code": "OFFICIAL_ASSET_VERIFY_ERROR",
            "diagnostics.timeout_s": 180.0,
            "diagnostics.asset_checks": {
                "load_quality": "empty_content",
                "content_has_bbox": False,
            },
            "diagnostics.material_checks": {
                "created_test_prim": False,
                "binding_verified": False,
            },
        },
    ]


def test_mcp_probe_live_diagnostic_field_mismatches_are_empty_for_expected_value():
    summary = {
        "diagnostic_next_actions": [
            {
                "step_id": "read_lidar_point_cloud",
                "diagnostics.reason": "point_count_below_minimum",
                "diagnostics.num_points": 512,
            },
            {
                "step_id": "verify_pallet_asset",
                "diagnostics.reason": "asset_load_quality_failed",
                "diagnostics.asset_checks": {"load_quality": "empty_content"},
            },
        ],
    }

    assert mcp_probe._live_diagnostic_field_mismatches(
        summary,
        (
            (
                "read_lidar_point_cloud",
                "diagnostics.reason",
                "point_count_below_minimum",
            ),
            ("read_lidar_point_cloud", "diagnostics.num_points", 512),
            (
                "verify_pallet_asset",
                "diagnostics.asset_checks",
                {"load_quality": "empty_content"},
            ),
        ),
    ) == []


def test_mcp_probe_live_diagnostic_field_mismatches_report_drift():
    summary = {
        "diagnostic_next_actions": [
            {
                "step_id": "read_lidar_point_cloud",
                "diagnostics.reason": "empty_scan_buffer",
            },
        ],
    }

    assert mcp_probe._live_diagnostic_field_mismatches(
        summary,
        (
            (
                "read_lidar_point_cloud",
                "diagnostics.reason",
                "point_count_below_minimum",
            ),
        ),
    ) == [
        "live diagnostic row 'read_lidar_point_cloud' field "
        "'diagnostics.reason' expected 'point_count_below_minimum', "
        "got ['empty_scan_buffer']",
    ]
    assert mcp_probe._live_diagnostic_field_mismatches(
        summary,
        (("read_lidar_point_cloud", "diagnostics.num_points", 512),),
    ) == [
        "live diagnostic row 'read_lidar_point_cloud' field "
        "'diagnostics.num_points' was not found",
    ]
    assert mcp_probe._live_diagnostic_field_mismatches(
        summary,
        (("missing_step", "diagnostics.reason", "point_count_below_minimum"),),
    ) == ["live diagnostic row 'missing_step' was not found"]
    assert mcp_probe._live_diagnostic_field_mismatches(
        {},
        (
            (
                "read_lidar_point_cloud",
                "diagnostics.reason",
                "point_count_below_minimum",
            ),
        ),
    ) == ["diagnostic_next_actions summary is missing or malformed"]


def test_mcp_probe_preflight_runtime_check_mismatches_are_empty_for_expected_values():
    summary = {
        "preflight_runtime_info_checks": [
            "tool_profile",
            "robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE",
        ],
    }

    assert mcp_probe._preflight_runtime_check_mismatches(
        summary,
        (
            "tool_profile",
            "robot_probe_unknown_profile_error_code=ROBOT_PROBE_UNKNOWN_PROFILE",
        ),
    ) == []


def test_mcp_probe_preflight_runtime_check_mismatches_report_drift():
    assert mcp_probe._preflight_runtime_check_mismatches(
        {
            "preflight_runtime_info_checks": [
                "tool_profile",
            ],
        },
        ("robot_probe_unknown_profile_fallback_tool_order",),
    ) == [
        (
            "preflight runtime check "
            "'robot_probe_unknown_profile_fallback_tool_order' was not found"
        ),
    ]
    assert mcp_probe._preflight_runtime_check_mismatches(
        {},
        ("tool_profile",),
    ) == [
        "preflight_runtime_info_checks summary is missing or malformed",
    ]


def test_mcp_probe_scenario_validate_dry_run_mismatches_are_empty_for_plan():
    assert mcp_probe._scenario_validate_dry_run_mismatches({
        "dry_run": True,
        "compiled": True,
        "steps": 32,
        "total_steps": 32,
    }) == []


def test_mcp_probe_scenario_validate_dry_run_mismatches_report_drift():
    assert mcp_probe._scenario_validate_dry_run_mismatches({
        "dry_run": False,
        "compiled": False,
        "steps": 31,
        "total_steps": 32,
    }) == [
        "dry_run expected True, got False",
        "compiled expected True, got False",
        "steps expected total_steps 32, got 31",
    ]


def test_mcp_probe_plan_flag_mismatches_report_drift():
    summary = {
        "scratch_stage_required": False,
        "log_capture_recommended": True,
    }

    assert mcp_probe._plan_flag_mismatches(
        summary,
        expect_scratch_stage_required=True,
        expect_log_capture_recommended=False,
    ) == [
        "scratch_stage_required expected True, got False",
        "log_capture_recommended expected False, got True",
    ]


def test_mcp_probe_rejects_plan_expectations_without_scenario_plan():
    assert mcp_probe.main([
        "--require-live-validation-tools",
        "mcp_runtime_info,kit_app_start",
    ]) == 2
    assert mcp_probe.main([
        "--expect-scratch-stage-required",
        "true",
    ]) == 2
    assert mcp_probe.main([
        "--expect-log-capture-recommended",
        "false",
    ]) == 2
    assert mcp_probe.main([
        "--expect-preflight-runtime-check",
        "robot_probe_unknown_profile_fallback_tool_order",
    ]) == 2
    assert mcp_probe.main([
        "--expect-retry-key-arg",
        "read_lidar_point_cloud:min_points=513",
    ]) == 2
    assert mcp_probe.main([
        "--expect-automatic-cleanup-timeout",
        "__fallback_cleanup_reset=30",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-dry-run",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-status",
        "failed",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-evidence-kind",
        "visual_capture",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-evidence-field",
        "official_asset_verify:verification_status=load_verified",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-evidence-field-min",
        "read_lidar_point_cloud:num_points=1",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-cleanup-failures",
        "0",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-failure-step-error",
        "read_lidar_point_cloud=SENSOR_LIDAR_POINT_CLOUD_TOO_FEW_POINTS",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-diagnostic-next-actions-min",
        "1",
    ]) == 2
    assert mcp_probe.main([
        "--expect-live-diagnostic-field",
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-live",
        "--workspace",
        "workspaces/isaac/instance-1",
        "--scenario-plan",
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "--scenario-validate-dry-run",
        "--expect-live-cleanup-failures",
        "-1",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-live",
        "--workspace",
        "workspaces/isaac/instance-1",
        "--scenario-plan",
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "--scenario-validate-dry-run",
        "--expect-live-diagnostic-next-actions-min",
        "-1",
    ]) == 2
    assert mcp_probe.main([
        "--live-preflight",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-live",
        "--scenario-plan",
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "--scenario-validate-dry-run",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-live",
        "--workspace",
        "workspaces/isaac/instance-1",
        "--scenario-validate-dry-run",
    ]) == 2
    assert mcp_probe.main([
        "--scenario-validate-live",
        "--workspace",
        "workspaces/isaac/instance-1",
        "--scenario-plan",
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
    ]) == 2


def test_mcp_probe_help_names_log_capture_stop_boundary(capsys):
    with pytest.raises(SystemExit) as exc_info:
        mcp_probe.main(["--help"])

    assert exc_info.value.code == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "extension_capture_logs(level=WARN, stop_after_capture=true)" in output
    assert "extension_capture_logs(stop_after_capture=true)" in output
    assert "--expect-live-evidence-field" in output
    assert "selector:key=value" in output
    assert "Value is JSON-decoded when possible" in output
    assert "--expect-live-evidence-field-min" in output
    assert "selector:key=minimum" in output
    assert "--expect-live-diagnostic-field" in output


def test_mcp_probe_main_wires_live_assertion_options(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_probe(**kwargs):
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(mcp_probe, "probe", fake_probe)

    exit_code = mcp_probe.main([
        "--workspace",
        "workspaces/isaac/instance-1",
        "--scenario-plan",
        "smoke/robot_rtx_sensor_golden_workflow.yaml",
        "--scenario-validate-dry-run",
        "--scenario-validate-live",
        "--input-overrides-json",
        '{"lidar_min_points":513}',
        "--expect-live-status",
        "failed",
        "--expect-live-evidence-kind",
        "rtx_lidar_point_cloud",
        "--expect-live-evidence-field",
        "read_lidar_point_cloud:status=passed",
        "--expect-live-evidence-field-min",
        "read_lidar_point_cloud:num_points=1",
        "--expect-live-diagnostic-field",
        "read_lidar_point_cloud:diagnostics.reason=point_count_below_minimum",
    ])

    assert exit_code == 0
    assert captured["workspace"] == Path("workspaces/isaac/instance-1")
    assert captured["runtime_info"] is True
    assert captured["scenario_plan"] == "smoke/robot_rtx_sensor_golden_workflow.yaml"
    assert captured["scenario_validate_dry_run"] is True
    assert captured["scenario_validate_live"] is True
    assert captured["input_overrides"] == {"lidar_min_points": 513}
    assert captured["expect_live_status"] == "failed"
    assert captured["expected_live_evidence_kinds"] == ("rtx_lidar_point_cloud",)
    assert captured["expected_live_evidence_fields"] == (
        ("read_lidar_point_cloud", "status", "passed"),
    )
    assert captured["expected_live_evidence_field_minimums"] == (
        ("read_lidar_point_cloud", "num_points", 1.0),
    )
    assert captured["expected_live_diagnostic_fields"] == (
        (
            "read_lidar_point_cloud",
            "diagnostics.reason",
            "point_count_below_minimum",
        ),
    )


def test_mcp_probe_summarizes_runtime_info_shape():
    summary = mcp_probe._runtime_info_probe_summary({
        "tool_profile": "full",
        "app_profile": "isaac-sim",
        "tool_count": 152,
        "registered_tool_count": 152,
        "omitted_tool_count": 0,
        "included_groups": {"Scenario": 3, "Robot": 8},
        "omitted_tools": [],
        "custom_include_tokens": [],
        "custom_exclude_tokens": [],
        "source_newer_than_import": False,
        "restart_required_for_latest_mcp_code": False,
        "has_mcp_runtime_info_tool": True,
        "robot_probe_result_has_checks": True,
        "robot_probe_unknown_profile_error_code": "ROBOT_PROBE_UNKNOWN_PROFILE",
        "robot_probe_unknown_profile_error_data_path": (
            "data.checks.probe.evidence"
        ),
        "robot_probe_unknown_profile_fallback_tool_order": [
            "robot_list_arm_profiles",
            "robot_probe_arm_profiles",
            "official_asset_search",
            "asset_search",
            "robot_load",
        ],
    })

    assert summary == {
        "tool_profile": "full",
        "app_profile": "isaac-sim",
        "tool_count": 152,
        "registered_tool_count": 152,
        "omitted_tool_count": 0,
        "included_group_count": 2,
        "omitted_tool_list_count": 0,
        "custom_include_tokens": [],
        "custom_exclude_tokens": [],
        "source_newer_than_import": False,
        "restart_required_for_latest_mcp_code": False,
        "has_mcp_runtime_info_tool": True,
        "robot_probe_result_has_checks": True,
        "robot_probe_unknown_profile_error_code": "ROBOT_PROBE_UNKNOWN_PROFILE",
        "robot_probe_unknown_profile_error_data_path": (
            "data.checks.probe.evidence"
        ),
        "robot_probe_unknown_profile_fallback_tool_order": [
            "robot_list_arm_profiles",
            "robot_probe_arm_profiles",
            "official_asset_search",
            "asset_search",
            "robot_load",
        ],
    }


def test_mcp_probe_module_result_summary_includes_error_diagnostics():
    summary = mcp_probe._module_result_probe_summary({
        "ok": False,
        "status": "error",
        "message": "RemoteTimeoutError",
        "error_code": "EXTENSION_LOGS_ERROR",
        "duration_ms": 91_757,
        "data": {
            "capture_running": True,
            "capture_stop_requested": True,
            "capture_stop_completed": False,
            "capture_stop_timed_out": True,
            "capture_stop_timeout_s": 1.0,
            "diagnostics": {
                "reason": "extension_logs_error",
                "error_type": "RemoteTimeoutError",
                "retryable": True,
                "fallback_tool_order": [
                    "extension_clear_logs",
                    "extension_capture_logs",
                    "process_list_kit_instances",
                    "kit_app_restart",
                ],
            },
        },
    })

    assert summary == {
        "ok": False,
        "status": "error",
        "message": "RemoteTimeoutError",
        "error_code": "EXTENSION_LOGS_ERROR",
        "duration_ms": 91_757,
        "data.capture_running": True,
        "data.capture_stop_requested": True,
        "data.capture_stop_completed": False,
        "data.capture_stop_timed_out": True,
        "data.capture_stop_timeout_s": 1.0,
        "data.diagnostics.reason": "extension_logs_error",
        "data.diagnostics.error_type": "RemoteTimeoutError",
        "data.diagnostics.retryable": True,
        "data.diagnostics.fallback_tool_order": [
            "extension_clear_logs",
            "extension_capture_logs",
            "process_list_kit_instances",
            "kit_app_restart",
        ],
    }


def test_mcp_probe_log_capture_close_mismatches_are_empty_for_closed_capture():
    summary = mcp_probe._module_result_probe_summary(_log_capture_pass())

    assert mcp_probe._log_capture_close_mismatches(summary) == []


def test_mcp_probe_log_capture_close_mismatches_report_open_capture():
    summary = {
        "data.capture_running": True,
        "data.capture_stop_requested": True,
        "data.capture_stop_completed": False,
        "data.capture_stop_timed_out": True,
    }

    assert mcp_probe._log_capture_close_mismatches(summary) == [
        "data.capture_stop_completed expected True, got False",
        "data.capture_stop_timed_out expected False, got True",
        "data.capture_running expected False, got True",
    ]


def test_mcp_probe_runtime_info_mismatches_are_empty_for_expected_shape():
    summary = {
        "tool_profile": "full",
        "app_profile": "isaac-sim",
        "tool_count": 152,
        "source_newer_than_import": False,
        "restart_required_for_latest_mcp_code": False,
        "robot_probe_result_has_checks": True,
        "robot_probe_unknown_profile_error_code": "ROBOT_PROBE_UNKNOWN_PROFILE",
        "robot_probe_unknown_profile_error_data_path": (
            "data.checks.probe.evidence"
        ),
        "robot_probe_unknown_profile_fallback_tool_order": [
            "robot_list_arm_profiles",
            "robot_probe_arm_profiles",
            "official_asset_search",
            "asset_search",
            "robot_load",
        ],
    }

    assert mcp_probe._runtime_info_mismatches(
        summary,
        expect_tool_profile="full",
        expect_app_profile="isaac-sim",
        expect_tool_count=152,
        require_runtime_fresh=True,
        require_robot_probe_error_contract=True,
    ) == []


def test_mcp_probe_runtime_info_mismatches_report_profile_count_staleness_and_robot_contract():
    summary = {
        "tool_profile": "app",
        "app_profile": "usd-composer",
        "tool_count": 148,
        "source_newer_than_import": True,
        "restart_required_for_latest_mcp_code": True,
        "robot_probe_result_has_checks": False,
        "robot_probe_unknown_profile_error_code": "OLD_CODE",
        "robot_probe_unknown_profile_error_data_path": "data",
        "robot_probe_unknown_profile_fallback_tool_order": [
            "robot_list_arm_profiles",
        ],
    }

    assert mcp_probe._runtime_info_mismatches(
        summary,
        expect_tool_profile="full",
        expect_app_profile="isaac-sim",
        expect_tool_count=152,
        require_runtime_fresh=True,
        require_robot_probe_error_contract=True,
    ) == [
        "tool_profile expected 'full', got 'app'",
        "app_profile expected 'isaac-sim', got 'usd-composer'",
        "tool_count expected 152, got 148",
        "source_newer_than_import is true",
        "restart_required_for_latest_mcp_code is true",
        "robot_probe_result_has_checks is not true",
        (
            "robot_probe_unknown_profile_error_code expected "
            "'ROBOT_PROBE_UNKNOWN_PROFILE', got 'OLD_CODE'"
        ),
        (
            "robot_probe_unknown_profile_error_data_path expected "
            "'data.checks.probe.evidence', got 'data'"
        ),
        (
            "robot_probe_unknown_profile_fallback_tool_order expected "
            "['robot_list_arm_profiles', 'robot_probe_arm_profiles', "
            "'official_asset_search', 'asset_search', 'robot_load'], got "
            "['robot_list_arm_profiles']"
        ),
    ]


def test_mcp_probe_summarizes_custom_plan_fields():
    summary = mcp_probe._scenario_plan_probe_summary(
        {
            "scenario_id": "official_asset_verify_live",
            "diagnostic_steps": [],
            "evidence_steps": [{"id": "verify_stage_probe"}],
        },
        ("diagnostic_steps", "evidence_steps", "stage_mutation_steps"),
    )

    assert summary["required_fields_present"] == {
        "diagnostic_steps": True,
        "evidence_steps": True,
        "stage_mutation_steps": False,
    }


def test_mcp_probe_merges_default_and_custom_required_plan_fields():
    assert mcp_probe._merge_required_plan_fields(
        True,
        ["evidence_steps", "simulation_state_summary", ""],
    ) == (
        "preflight_requirements",
        "simulation_state_summary",
        "simulation_state_steps",
        "timeline_control_steps",
        "live_validation_checklist",
        "evidence_steps",
    )


def test_mcp_probe_rejects_non_object_input_overrides():
    with pytest.raises(ValueError, match="must decode to a JSON object"):
        mcp_probe._parse_json_object("[1]", label="--input-overrides-json")
