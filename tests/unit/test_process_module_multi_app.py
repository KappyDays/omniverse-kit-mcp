"""ProcessModule multi-app isolation tests (subprocess mocked).

All launch / kill / alive probes are monkeypatched so these tests run
without live Isaac Sim or USD Composer. Live end-to-end smoke lives in
scripts/verify_multi_app.py (Phase 7).
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.modules.process_module import ProcessModule


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Isolate from project-level .env so profile defaults apply cleanly.

    Chdir to tmp_path so pydantic-settings env_file=".env" doesn't find the
    project's .env (which sets Isaac-specific ISAAC_SIM_EXTRA_EXT_IDS that
    would leak into usd-composer cmd).
    """
    monkeypatch.chdir(tmp_path)
    for key in (
        "ISAAC_SIM_EXTRA_EXT_IDS",
        "ISAAC_SIM_BASE_URL",
        "ISAAC_SIM_KIT_EXE",
        "ISAAC_SIM_KIT_FILE",
        "ISAAC_MCP_APP_PROFILE",
        "ISAAC_MCP_INSTANCE_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def _module_for(profile: str, instance: int) -> ProcessModule:
    os.environ["ISAAC_MCP_APP_PROFILE"] = profile
    os.environ["ISAAC_MCP_INSTANCE_ID"] = str(instance)
    try:
        cfg = AppConfig()
    finally:
        os.environ.pop("ISAAC_MCP_APP_PROFILE", None)
        os.environ.pop("ISAAC_MCP_INSTANCE_ID", None)
    return ProcessModule(cfg.isaac_sim_process)


async def _async_none():
    return None


async def _async_true():
    return True


async def _async_false():
    return False


# --- Port flag injection --------------------------------------------------

@pytest.mark.asyncio
async def test_isaac_instance_1_cmd_has_port_8011_and_ext_folder(monkeypatch):
    module = _module_for("isaac-sim", 1)
    captured: list[list[str]] = []

    def fake_popen(cmd, **kwargs):
        captured.append(cmd)
        fake = MagicMock()
        fake.pid = int("11111")
        return fake

    async def fake_alive(self):
        return False

    async def fake_health(self):
        return True

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", fake_alive)
    monkeypatch.setattr(ProcessModule, "_check_health", fake_health)
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    await module.start()

    cmd = captured[0]
    assert any("port=8011" in arg for arg in cmd), f"port flag missing: {cmd}"
    assert "--ext-folder" in cmd, f"--ext-folder missing: {cmd}"
    assert "omni.mycompany.validation_api" in cmd, f"--enable validation_api missing: {cmd}"


@pytest.mark.asyncio
async def test_usd_composer_instance_1_cmd_has_port_8014(monkeypatch):
    module = _module_for("usd-composer", 1)
    captured: list[list[str]] = []

    def fake_popen(cmd, **kwargs):
        captured.append(cmd)
        fake = MagicMock()
        fake.pid = int("22221")
        return fake

    async def fake_alive(self):
        return False

    async def fake_health(self):
        return True

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", fake_alive)
    monkeypatch.setattr(ProcessModule, "_check_health", fake_health)
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    await module.start()

    cmd = captured[0]
    assert any("port=8014" in arg for arg in cmd)
    assert any("kkr_usd_composer.kit" in arg for arg in cmd), \
        f"USD Composer kit file missing: {cmd}"
    assert not any("omni.anim.graph.bundle" in arg for arg in cmd), \
        f"Isaac anim.graph leaked into usd-composer cmd: {cmd}"


@pytest.mark.asyncio
async def test_usd_composer_instance_3_port_8016(monkeypatch):
    module = _module_for("usd-composer", 3)
    captured: list[list[str]] = []

    def fake_popen(cmd, **kwargs):
        captured.append(cmd)
        fake = MagicMock()
        fake.pid = int("22223")
        return fake

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", lambda self: _async_false())
    monkeypatch.setattr(ProcessModule, "_check_health", lambda self: _async_true())
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    await module.start()
    cmd = captured[0]
    assert any("port=8016" in arg for arg in cmd)


# --- ROS env only for isaac profile ---------------------------------------

@pytest.mark.asyncio
async def test_isaac_profile_sets_ros_env(monkeypatch):
    module = _module_for("isaac-sim", 1)
    captured_env: dict = {}

    def fake_popen(cmd, env=None, **kwargs):
        captured_env.update(env or {})
        fake = MagicMock()
        fake.pid = int("11112")
        return fake

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", lambda self: _async_false())
    monkeypatch.setattr(ProcessModule, "_check_health", lambda self: _async_true())
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    await module.start()
    assert captured_env.get("ROS_DISTRO") == "humble"
    assert captured_env.get("RMW_IMPLEMENTATION") == "rmw_fastrtps_cpp"


@pytest.mark.asyncio
async def test_usd_composer_profile_skips_ros_env(monkeypatch):
    monkeypatch.delenv("ROS_DISTRO", raising=False)
    monkeypatch.delenv("RMW_IMPLEMENTATION", raising=False)

    module = _module_for("usd-composer", 1)
    captured_env: dict = {}

    def fake_popen(cmd, env=None, **kwargs):
        captured_env.update(env or {})
        fake = MagicMock()
        fake.pid = int("22224")
        return fake

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", lambda self: _async_false())
    monkeypatch.setattr(ProcessModule, "_check_health", lambda self: _async_true())
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    await module.start()
    assert "ROS_DISTRO" not in captured_env, \
        f"usd-composer should not set ROS_DISTRO (got {captured_env.get('ROS_DISTRO')!r})"


# --- PID + CommandLine scoping -------------------------------------------

@pytest.mark.asyncio
async def test_resolve_instance_pid_matches_port_string(monkeypatch):
    module = _module_for("isaac-sim", 2)

    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.stdout = "33344\n"
        r.returncode = 0
        return r

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.run", fake_run)
    pid = await module._resolve_instance_pid()
    assert pid == 33344


@pytest.mark.asyncio
async def test_resolve_instance_pid_returns_none_when_empty(monkeypatch):
    module = _module_for("isaac-sim", 2)

    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.stdout = ""
        r.returncode = 0
        return r

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.run", fake_run)
    pid = await module._resolve_instance_pid()
    assert pid is None


@pytest.mark.asyncio
async def test_stop_uses_pid_not_imagename(monkeypatch):
    module = _module_for("isaac-sim", 2)
    module._process = MagicMock()
    module._process.pid = int("55512")
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        r = MagicMock()
        r.stdout = ""
        r.returncode = 0
        return r

    call_count = {"alive": 0}

    async def fake_alive(self):
        call_count["alive"] += 1
        return call_count["alive"] == 1

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.run", fake_run)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", fake_alive)
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    result = await module.stop()
    assert result["ok"] is True
    assert result.get("pid") == 55512

    pid_kills = [c for c in captured if "/PID" in c and "55512" in c]
    assert pid_kills, f"expected taskkill /PID 55512; got {captured}"

    image_kills = [c for c in captured if "/IM" in c and "kit.exe" in c]
    assert not image_kills, (
        f"must not taskkill /IM kit.exe (would kill other instances); got {captured}"
    )


# --- hub cleanup skip when other kit alive -------------------------------

@pytest.mark.asyncio
async def test_hub_cleanup_skipped_when_other_kit_alive(monkeypatch):
    module = _module_for("isaac-sim", 1)
    module._process = None
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        r = MagicMock()
        r.returncode = 0
        joined = " ".join(cmd)
        if "Get-Process" in joined and "kit" in joined:
            r.stdout = "99999\n"
        else:
            r.stdout = ""
        return r

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.run", fake_run)

    await module._cleanup_orphan_hub()
    hub_kills = [c for c in captured if "/IM" in c and "hub.exe" in c]
    assert not hub_kills, f"hub cleanup must skip while other kit alive; got {captured}"


@pytest.mark.asyncio
async def test_hub_cleanup_runs_when_no_kit_alive(monkeypatch):
    module = _module_for("usd-composer", 1)
    module._process = None
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        return r

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.run", fake_run)
    await module._cleanup_orphan_hub()
    hub_kills = [c for c in captured if "/IM" in c and "hub.exe" in c]
    assert hub_kills, f"hub cleanup must run when no kit.exe alive; got {captured}"


# --- Response payload includes profile + instance identifiers ------------

@pytest.mark.asyncio
async def test_start_response_includes_profile_and_instance(monkeypatch):
    module = _module_for("usd-composer", 2)

    def fake_popen(cmd, **kwargs):
        fake = MagicMock()
        fake.pid = int("77777")
        return fake

    monkeypatch.setattr("omniverse_kit_mcp.modules.process_module.subprocess.Popen", fake_popen)
    monkeypatch.setattr(ProcessModule, "_is_process_alive", lambda self: _async_false())
    monkeypatch.setattr(ProcessModule, "_check_health", lambda self: _async_true())
    monkeypatch.setattr(ProcessModule, "_cleanup_orphan_hub", lambda self: _async_none())

    result = await module.start()
    assert result["ok"] is True
    assert result["app_profile"] == "usd-composer"
    assert result["instance_id"] == 2
    assert result["ext_port"] == 8015
    assert result["pid"] == 77777
