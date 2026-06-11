"""Guards for Codex worktree bootstrap helpers."""

from __future__ import annotations

from pathlib import Path

from scripts import verify_local_isaac_env
from scripts.verify_local_isaac_env import build_report, read_env_file


def test_read_env_file_handles_comments_and_quotes(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
        # local only
        ISAAC_SIM_KIT_EXE="C:/Isaac/kit/kit.exe"
        ISAAC_SIM_KIT_FILE='C:/Isaac/apps/isaacsim.exp.full.kit'
        INVALID_LINE
        """,
        encoding="utf-8",
    )

    values = read_env_file(env_file)

    assert values["ISAAC_SIM_KIT_EXE"] == "C:/Isaac/kit/kit.exe"
    assert values["ISAAC_SIM_KIT_FILE"] == "C:/Isaac/apps/isaacsim.exp.full.kit"
    assert "INVALID_LINE" not in values


def test_build_report_accepts_fake_isaac_paths(monkeypatch, tmp_path):
    kit_exe = tmp_path / "kit" / "kit.exe"
    kit_file = tmp_path / "apps" / "isaacsim.exp.full.kit"
    kit_exe.parent.mkdir()
    kit_file.parent.mkdir()
    kit_exe.write_text("", encoding="utf-8")
    kit_file.write_text("", encoding="utf-8")
    (tmp_path / "VERSION").write_text("6.0.0-test\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        verify_local_isaac_env,
        "USER_LOCAL_ENV",
        tmp_path / "missing-local.env",
    )
    monkeypatch.setenv("ISAAC_SIM_KIT_EXE", kit_exe.as_posix())
    monkeypatch.setenv("ISAAC_SIM_KIT_FILE", kit_file.as_posix())
    monkeypatch.delenv("ISAAC_SIM_BASE_URL", raising=False)

    report = build_report(
        profile="isaac-sim",
        instance=2,
        check_codex_mcp_list=False,
        repo_root=Path.cwd(),
        mcp_cwd=Path.cwd(),
    )

    assert report.ok
    assert report.base_url == "http://127.0.0.1:8112"
    assert report.health_url == "http://127.0.0.1:8112/validation/v1/health"
    assert report.expected_mcp_server == "isaacsim-mcp-2"


def test_build_report_rejects_isaac_51_install(monkeypatch, tmp_path):
    kit_exe = tmp_path / "kit" / "kit.exe"
    kit_file = tmp_path / "apps" / "isaacsim.exp.full.kit"
    kit_exe.parent.mkdir()
    kit_file.parent.mkdir()
    kit_exe.write_text("", encoding="utf-8")
    kit_file.write_text("", encoding="utf-8")
    (tmp_path / "VERSION").write_text("5.1.0\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        verify_local_isaac_env,
        "USER_LOCAL_ENV",
        tmp_path / "missing-local.env",
    )
    monkeypatch.setenv("ISAAC_SIM_KIT_EXE", kit_exe.as_posix())
    monkeypatch.setenv("ISAAC_SIM_KIT_FILE", kit_file.as_posix())
    monkeypatch.delenv("ISAAC_SIM_BASE_URL", raising=False)

    report = build_report(
        profile="isaac-sim",
        instance=1,
        check_codex_mcp_list=False,
        repo_root=Path.cwd(),
        mcp_cwd=Path.cwd(),
    )

    assert not report.ok
    assert any("VERSION is not 6.0.x" in error for error in report.errors)


def test_build_report_fails_without_isaac_paths(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        verify_local_isaac_env,
        "USER_LOCAL_ENV",
        tmp_path / "missing-local.env",
    )
    for key in ("ISAAC_SIM_KIT_EXE", "ISAAC_SIM_KIT_FILE", "ISAAC_SIM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)

    report = build_report(
        profile="isaac-sim",
        instance=1,
        check_codex_mcp_list=False,
        repo_root=Path.cwd(),
        mcp_cwd=Path.cwd(),
    )

    assert not report.ok
    assert any("ISAAC_SIM_KIT_EXE" in error for error in report.errors)
    assert any("ISAAC_SIM_KIT_FILE" in error for error in report.errors)
