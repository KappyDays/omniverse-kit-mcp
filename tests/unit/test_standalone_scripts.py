"""Standalone script cwd guards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.run_process_module_standalone as process_script
import scripts.run_scenario_standalone as scenario_script
from omniverse_kit_mcp.config import AppConfig, ScenarioConfig


class _CwdChecked(RuntimeError):
    pass


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


def test_scenario_standalone_rejects_non_object_input_overrides(capsys):
    exit_code = scenario_script.main([
        "--dry-run",
        "--input-overrides-json",
        "[1]",
        "smoke/dry.yaml",
    ])

    assert exit_code == 2
    assert "must decode to a JSON object" in capsys.readouterr().err
