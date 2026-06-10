"""Guards for MCP-friendly manual Kit launchers.

The launcher source of truth lives in-repo. Setup copies these files into the
out-of-repo Kit install/build folders so reinstalling those folders does not
silently lose the MCP-safe manual launch path.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCHERS = REPO / "setup" / "launchers"
SETUP_PS1 = REPO / "setup" / "setup_omniverse_kit_mcp.ps1"


def _read_launcher(name: str) -> str:
    path = LAUNCHERS / name
    assert path.exists(), f"missing launcher template: {path}"
    return path.read_text(encoding="utf-8")


def test_launcher_templates_exist_for_manual_mcp_launches():
    expected = {
        "isaac-sim_mcp.bat",
        "isaac-sim_mcp.ps1",
        "kkr_usd_composer_mcp.kit.bat",
        "kkr_usd_composer_mcp.kit.ps1",
    }
    assert {p.name for p in LAUNCHERS.glob("*_mcp.*")} == expected


def test_bat_launchers_use_portable_pushd_and_relative_ps1():
    for name in ("isaac-sim_mcp.bat", "kkr_usd_composer_mcp.kit.bat"):
        text = _read_launcher(name)
        assert 'pushd "%~dp0"' in text
        assert '-File ".\\' in text
        assert "%%~dp0" not in text
        assert "C:/Users/" not in text
        assert "C:\\Users\\" not in text


def test_ps1_launchers_use_expected_ports_and_disable_port_range():
    expectations = {
        "isaac-sim_mcp.ps1": ("8111", "8112", "apps/isaacsim.exp.full.kit"),
        "kkr_usd_composer_mcp.kit.ps1": ("8114", "8115", "apps/kkr_usd_composer.kit"),
    }
    for name, (port1, port2, kit_file) in expectations.items():
        text = _read_launcher(name)
        assert f"1 = {port1}" in text
        assert f"2 = {port2}" in text
        assert kit_file in text
        assert "allow_port_range=false" in text
        assert "Test-PortAvailable" in text
        assert "Global\\" in text
        assert "C:/Users/" not in text
        assert "C:\\Users\\" not in text


def test_setup_installs_launcher_templates_to_known_kit_folders():
    text = SETUP_PS1.read_text(encoding="utf-8")
    assert "Install-McpLauncher" in text
    assert "setup\\launchers" in text
    assert "isaac-sim_mcp.bat" in text
    assert "isaac-sim_mcp.ps1" in text
    assert "kkr_usd_composer_mcp.kit.bat" in text
    assert "kkr_usd_composer_mcp.kit.ps1" in text
    assert "isaac-sim-standalone-5.1.0-windows-x86_64" in text
    assert "kit-app-template\\_build\\windows-x86_64\\release" in text
