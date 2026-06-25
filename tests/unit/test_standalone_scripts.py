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
        "status": "passed",
        "passed_steps": 32,
        "failed_steps": 0,
        "skipped_steps": 0,
        "continued_steps": 0,
        "fatal_failed_steps": 0,
        "cleanup_failed_steps": 0,
        "failure_summary": [],
        "diagnostic_next_actions": [],
        "evidence_summary": [
            {"step_id": "capture_visible_result", "evidence_kind": "visual_capture"},
        ],
    }
    module_pass = {"ok": True, "status": "passed", "data": {"status": "ready"}}
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
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
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
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "=== scenario_validate live summary ===" in output
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
            "result": {"content": [{"type": "text", "text": json.dumps(module_pass)}]},
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
        "--scenario-validate-dry-run",
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
