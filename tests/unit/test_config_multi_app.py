"""Multi-app config derivation tests.

Isolates from project-level .env via monkeypatch.chdir(tmp_path) so the
pydantic-settings env_file=".env" does not interfere.
"""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in (
        "ISAAC_MCP_INSTANCE_ID",
        "ISAAC_MCP_APP_PROFILE",
        "ISAAC_SIM_EXT_BASE_PORT",
        "ISAAC_SIM_BASE_URL",
        "ISAAC_SIM_HEALTH_URL",
        "ISAAC_SIM_KIT_EXE",
        "ISAAC_SIM_KIT_FILE",
        "USD_COMPOSER_KIT_EXE",
        "USD_COMPOSER_KIT_FILE",
        "MCP_SERVER_TOOL_PROFILE",
        "MCP_SERVER_TOOL_INCLUDE",
        "MCP_SERVER_TOOL_EXCLUDE",
    ):
        monkeypatch.delenv(key, raising=False)


# --- Default profile (isaac-sim, instance 1) ------------------------------

def test_default_profile_is_isaac_sim():
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.name == "isaac-sim"
    assert cfg.isaac_sim_process.instance_id == 1
    assert cfg.isaac_sim_process.ext_port == 8111
    assert cfg.isaac_sim_process.health_url == "http://127.0.0.1:8111/validation/v1/health"
    assert cfg.isaac_sim.base_url == "http://127.0.0.1:8111"
    assert cfg.mcp_server.tool_profile == "full"


def test_mcp_tool_profile_env_accepts_core(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_TOOL_PROFILE", "core")
    cfg = AppConfig()
    assert cfg.mcp_server.tool_profile == "core"


def test_mcp_tool_profile_rejects_unknown(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_TOOL_PROFILE", "tiny")
    with pytest.raises(Exception, match="Unknown MCP tool profile"):
        AppConfig()


def test_isaac_instance_2_port_8112(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "2")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8112
    assert cfg.isaac_sim.base_url == "http://127.0.0.1:8112"


def test_isaac_instance_3_rejected(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "3")
    with pytest.raises(Exception):
        AppConfig()


# --- USD Composer profile (isolated port range) --------------------------

def test_usd_composer_profile_instance_1_port_8114(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "1")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.name == "usd-composer"
    assert cfg.isaac_sim_process.ext_port == 8114
    assert cfg.isaac_sim.base_url == "http://127.0.0.1:8114"


def test_usd_composer_instance_2_port_8115(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "2")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8115


def test_usd_composer_instance_3_rejected(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "3")
    with pytest.raises(Exception):
        AppConfig()


# --- Profile-specific kit binary paths -----------------------------------

def test_isaac_profile_uses_isaac_kit_exe():
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.kit_exe == "C:/IsaacSim/kit/kit.exe"
    assert cfg.isaac_sim_process.app_profile.kit_file == (
        "C:/IsaacSim/apps/isaacsim.exp.full.kit"
    )
    assert cfg.isaac_sim_process.app_profile.kit_exe.endswith("/kit/kit.exe") or \
           cfg.isaac_sim_process.app_profile.kit_exe.endswith("\\kit\\kit.exe")


def test_usd_composer_profile_uses_composer_kit_exe(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.kit_exe == "C:/USDComposer/kit/kit.exe"
    assert "kkr_usd_composer.kit" in cfg.isaac_sim_process.app_profile.kit_file


def test_usd_composer_ignores_legacy_isaac_kit_overrides(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_SIM_KIT_EXE", "C:/IsaacSim/kit/kit.exe")
    monkeypatch.setenv("ISAAC_SIM_KIT_FILE", "C:/IsaacSim/apps/isaacsim.exp.full.kit")

    cfg = AppConfig()

    assert cfg.isaac_sim_process.effective_kit_exe == "C:/USDComposer/kit/kit.exe"
    assert cfg.isaac_sim_process.effective_kit_file == (
        "C:/USDComposer/apps/kkr_usd_composer.kit"
    )


def test_usd_composer_uses_composer_specific_kit_overrides(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("USD_COMPOSER_KIT_EXE", "D:/Composer/kit/kit.exe")
    monkeypatch.setenv("USD_COMPOSER_KIT_FILE", "D:/Composer/apps/kkr_usd_composer.kit")

    cfg = AppConfig()

    assert cfg.isaac_sim_process.effective_kit_exe == "D:/Composer/kit/kit.exe"
    assert cfg.isaac_sim_process.effective_kit_file == (
        "D:/Composer/apps/kkr_usd_composer.kit"
    )


# --- ROS env requirement differs per profile -----------------------------

def test_isaac_profile_requires_ros_env():
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.ros_env_required is True


def test_usd_composer_profile_no_ros_env(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.ros_env_required is False


# --- Supported module groups differ per profile --------------------------

def test_isaac_profile_supports_all_module_groups():
    cfg = AppConfig()
    supported = cfg.isaac_sim_process.app_profile.supported_module_groups
    for g in ("common", "robot", "character", "navigation", "sensor", "replicator"):
        assert g in supported, f"isaac-sim must support {g}"


def test_usd_composer_profile_supports_only_common(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    cfg = AppConfig()
    supported = cfg.isaac_sim_process.app_profile.supported_module_groups
    assert "common" in supported
    for g in ("robot", "character", "navigation", "sensor", "replicator"):
        assert g not in supported, f"usd-composer must NOT claim to support {g}"


# --- Override resilience --------------------------------------------------

def test_explicit_base_url_overrides_derivation(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "2")
    monkeypatch.setenv("ISAAC_SIM_BASE_URL", "http://remote-host:9911")
    cfg = AppConfig()
    assert cfg.isaac_sim.base_url == "http://remote-host:9911"


def test_unknown_profile_rejects(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "kaolin")  # not supported yet
    with pytest.raises(Exception):
        AppConfig()


def test_invalid_instance_id_rejects(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "0")
    with pytest.raises(Exception):
        AppConfig()


# --- Profile module smoke tests ------------------------------------------

def test_profile_module_exports_isaac_and_usd_composer():
    from omniverse_kit_mcp.types.profile import get_profile, list_profile_names
    assert set(list_profile_names()) == {"isaac-sim", "usd-composer"}
    assert get_profile("isaac-sim").default_ext_port == 8111
    assert get_profile("usd-composer").default_ext_port == 8114


def test_isaac_profile_enables_isaac_6_extensions():
    cfg = AppConfig()
    extra = cfg.isaac_sim_process.app_profile.extra_ext_ids
    assert "isaacsim.sensors.experimental.rtx" in extra
    assert "isaacsim.sensors.experimental.physics" in extra
    assert "isaacsim.ros2.bridge" in extra
    assert "isaacsim.sensors.rtx" not in extra


def test_get_profile_raises_on_unknown():
    from omniverse_kit_mcp.types.profile import get_profile
    with pytest.raises(ValueError, match="Unknown app profile"):
        get_profile("kaolin")


def test_profile_is_frozen_dataclass():
    from omniverse_kit_mcp.types.profile import ISAAC_SIM_PROFILE
    with pytest.raises(Exception):  # FrozenInstanceError
        ISAAC_SIM_PROFILE.name = "mutated"
