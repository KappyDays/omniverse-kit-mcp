"""Standalone script cwd guards."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.run_process_module_standalone as process_script
import scripts.run_scenario_standalone as scenario_script


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
