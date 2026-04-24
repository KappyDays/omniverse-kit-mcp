"""Multi-app config derivation tests.

Isolates from project-level .env via monkeypatch.chdir(tmp_path) so the
pydantic-settings env_file=".env" does not interfere.
"""

from __future__ import annotations

import pytest

from isaacsim_mcp.config import AppConfig


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
    ):
        monkeypatch.delenv(key, raising=False)


# --- Default profile (isaac-sim, instance 1) ------------------------------

def test_default_profile_is_isaac_sim():
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.name == "isaac-sim"
    assert cfg.isaac_sim_process.instance_id == 1
    assert cfg.isaac_sim_process.ext_port == 8011
    assert cfg.isaac_sim_process.health_url == "http://localhost:8011/validation/v1/health"
    assert cfg.isaac_sim.base_url == "http://localhost:8011"


def test_isaac_instance_2_port_8012(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "2")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8012
    assert cfg.isaac_sim.base_url == "http://localhost:8012"


def test_isaac_instance_3_port_8013(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "3")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8013


# --- USD Composer profile (isolated port range) --------------------------

def test_usd_composer_profile_instance_1_port_8014(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "1")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.app_profile.name == "usd-composer"
    assert cfg.isaac_sim_process.ext_port == 8014
    assert cfg.isaac_sim.base_url == "http://localhost:8014"


def test_usd_composer_instance_2_port_8015(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "2")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8015


def test_usd_composer_instance_3_port_8016(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    monkeypatch.setenv("ISAAC_MCP_INSTANCE_ID", "3")
    cfg = AppConfig()
    assert cfg.isaac_sim_process.ext_port == 8016


# --- Profile-specific kit binary paths -----------------------------------

def test_isaac_profile_uses_isaac_kit_exe():
    cfg = AppConfig()
    assert "isaac-sim-standalone" in cfg.isaac_sim_process.app_profile.kit_exe
    assert cfg.isaac_sim_process.app_profile.kit_exe.endswith("/kit/kit.exe") or \
           cfg.isaac_sim_process.app_profile.kit_exe.endswith("\\kit\\kit.exe")


def test_usd_composer_profile_uses_composer_kit_exe(monkeypatch):
    monkeypatch.setenv("ISAAC_MCP_APP_PROFILE", "usd-composer")
    cfg = AppConfig()
    assert "kit-app-template" in cfg.isaac_sim_process.app_profile.kit_exe
    assert "kkr_usd_composer.kit" in cfg.isaac_sim_process.app_profile.kit_file


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
    from isaacsim_mcp.types.profile import get_profile, list_profile_names
    assert set(list_profile_names()) == {"isaac-sim", "usd-composer"}
    assert get_profile("isaac-sim").default_ext_port == 8011
    assert get_profile("usd-composer").default_ext_port == 8014


def test_get_profile_raises_on_unknown():
    from isaacsim_mcp.types.profile import get_profile
    with pytest.raises(ValueError, match="Unknown app profile"):
        get_profile("kaolin")


def test_profile_is_frozen_dataclass():
    from isaacsim_mcp.types.profile import ISAAC_SIM_PROFILE
    with pytest.raises(Exception):  # FrozenInstanceError
        ISAAC_SIM_PROFILE.name = "mutated"
