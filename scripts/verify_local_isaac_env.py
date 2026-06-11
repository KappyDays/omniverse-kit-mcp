"""Verify local Codex/Isaac Sim environment before live MCP work.

This is intentionally local-machine oriented. It never writes secrets or paths;
it only reports whether the current worktree can launch and target the intended
Kit instance.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_ISAAC_PATH_KEYS = ("ISAAC_SIM_KIT_EXE", "ISAAC_SIM_KIT_FILE")
REQUIRED_ISAAC_VERSION_PREFIX = "6.0"
USER_LOCAL_ENV = Path.home() / ".config" / "omniverse-kit-mcp" / "local.env"


@dataclass(slots=True, frozen=True)
class CheckReport:
    profile: str
    instance: int
    base_url: str
    health_url: str | None
    kit_exe: str
    kit_file: str
    repo_env_exists: bool
    user_local_env_exists: bool
    expected_mcp_server: str
    mcp_list_checked: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE dotenv files without expanding values."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _expected_server_name(profile: str, instance: int) -> str:
    if profile == "isaac-sim":
        return f"isaacsim-mcp-{instance}"
    if profile == "usd-composer":
        return f"usdcomposer-mcp-{instance}"
    return f"{profile}-mcp-{instance}"


def _path_exists(path_text: str) -> bool:
    return bool(path_text) and Path(path_text).exists()


def _isaac_install_root(kit_exe: str) -> Path:
    return Path(kit_exe).parent.parent


def _has_any_source(key: str, repo_env: dict[str, str], user_env: dict[str, str]) -> bool:
    return key in os.environ or key in repo_env or key in user_env


def _check_codex_mcp_list(expected_server: str, cwd: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        command = ["cmd", "/c", "codex", "mcp", "list"] if os.name == "nt" else [
            "codex", "mcp", "list",
        ]
        proc = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        warnings.append("codex executable not found; skipped MCP list check")
        return errors, warnings
    except PermissionError as exc:
        warnings.append(f"codex mcp list could not be launched: {exc}")
        return errors, warnings
    except subprocess.TimeoutExpired:
        errors.append("codex mcp list timed out")
        return errors, warnings

    output = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        errors.append(f"codex mcp list failed with exit {proc.returncode}")
    elif expected_server not in output:
        errors.append(f"codex mcp list did not show {expected_server!r}")
    return errors, warnings


def build_report(
    *,
    profile: str,
    instance: int,
    check_codex_mcp_list: bool = False,
    repo_root: Path | None = None,
    mcp_cwd: Path | None = None,
) -> CheckReport:
    repo_root = repo_root or Path.cwd()
    mcp_cwd = mcp_cwd or Path.cwd()
    repo_env = read_env_file(repo_root / ".env")
    user_env = read_env_file(USER_LOCAL_ENV)

    os.environ["ISAAC_MCP_APP_PROFILE"] = profile
    os.environ["ISAAC_MCP_INSTANCE_ID"] = str(instance)

    from omniverse_kit_mcp.config import AppConfig

    cfg = AppConfig()
    expected_server = _expected_server_name(profile, instance)
    kit_exe = cfg.isaac_sim_process.effective_kit_exe
    kit_file = cfg.isaac_sim_process.effective_kit_file

    errors: list[str] = []
    warnings: list[str] = []

    if profile == "isaac-sim":
        for key in REQUIRED_ISAAC_PATH_KEYS:
            if not _has_any_source(key, repo_env, user_env):
                errors.append(
                    f"{key} is not set in OS env, .env, or {USER_LOCAL_ENV}"
                )
        if not _path_exists(kit_exe):
            errors.append(f"effective kit.exe does not exist: {kit_exe}")
        if not _path_exists(kit_file):
            errors.append(f"effective .kit file does not exist: {kit_file}")
        if _path_exists(kit_exe):
            install_root = _isaac_install_root(kit_exe)
            version_file = install_root / "VERSION"
            if version_file.exists():
                version = version_file.read_text(encoding="utf-8", errors="replace").strip()
                if not version.startswith(REQUIRED_ISAAC_VERSION_PREFIX):
                    errors.append(
                        "Isaac Sim install VERSION is not 6.0.x: "
                        f"{version_file} contains {version!r}"
                    )
            else:
                warnings.append(f"Isaac Sim VERSION file not found under {install_root}")

    if cfg.isaac_sim.base_url is None:
        errors.append("ISAAC_SIM_BASE_URL derivation failed")
    elif not cfg.isaac_sim.base_url.endswith(str(cfg.isaac_sim_process.ext_port)):
        warnings.append(
            "ISAAC_SIM_BASE_URL is explicit and does not end with derived "
            f"port {cfg.isaac_sim_process.ext_port}: {cfg.isaac_sim.base_url}"
        )

    if check_codex_mcp_list:
        mcp_errors, mcp_warnings = _check_codex_mcp_list(expected_server, mcp_cwd)
        errors.extend(mcp_errors)
        warnings.extend(mcp_warnings)

    return CheckReport(
        profile=profile,
        instance=instance,
        base_url=cfg.isaac_sim.base_url or "",
        health_url=cfg.isaac_sim_process.health_url,
        kit_exe=kit_exe,
        kit_file=kit_file,
        repo_env_exists=(repo_root / ".env").exists(),
        user_local_env_exists=USER_LOCAL_ENV.exists(),
        expected_mcp_server=expected_server,
        mcp_list_checked=check_codex_mcp_list,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _print_human(report: CheckReport) -> None:
    print("== local Isaac/Codex environment preflight ==")
    print(f"profile:             {report.profile}")
    print(f"instance:            {report.instance}")
    print(f"base_url:            {report.base_url}")
    print(f"health_url:          {report.health_url}")
    print(f"kit_exe:             {report.kit_exe}")
    print(f"kit_file:            {report.kit_file}")
    print(f"repo .env exists:    {report.repo_env_exists}")
    print(f"user local.env:      {USER_LOCAL_ENV}")
    print(f"user local.env exists: {report.user_local_env_exists}")
    print(f"expected MCP server: {report.expected_mcp_server}")
    if report.mcp_list_checked:
        print("codex mcp list:      checked")
    if report.warnings:
        print("\nWarnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  - {error}")
        print("\nCreate or copy a local .env before live MCP work.")
    else:
        print("\nOK: local environment is ready for this worktree.")


def _as_jsonable(report: CheckReport) -> dict[str, object]:
    return {
        "ok": report.ok,
        "profile": report.profile,
        "instance": report.instance,
        "base_url": report.base_url,
        "health_url": report.health_url,
        "kit_exe": report.kit_exe,
        "kit_file": report.kit_file,
        "repo_env_exists": report.repo_env_exists,
        "user_local_env": str(USER_LOCAL_ENV),
        "user_local_env_exists": report.user_local_env_exists,
        "expected_mcp_server": report.expected_mcp_server,
        "mcp_list_checked": report.mcp_list_checked,
        "warnings": list(report.warnings),
        "errors": list(report.errors),
    }


def _env_default_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default=os.environ.get("ISAAC_MCP_APP_PROFILE", "isaac-sim"),
        help="Kit app profile to validate.",
    )
    parser.add_argument(
        "--instance",
        type=int,
        default=_env_default_int("ISAAC_MCP_INSTANCE_ID", 1),
        help="Instance id to validate.",
    )
    parser.add_argument(
        "--check-codex-mcp-list",
        action="store_true",
        help="Run `codex mcp list` in the current directory and check the expected server name.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root whose .env should be loaded.",
    )
    parser.add_argument(
        "--mcp-cwd",
        type=Path,
        default=Path.cwd(),
        help="Directory where `codex mcp list` should run, usually workspaces/<app>/instance-N.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = build_report(
        profile=args.profile,
        instance=args.instance,
        check_codex_mcp_list=args.check_codex_mcp_list,
        repo_root=args.repo_root,
        mcp_cwd=args.mcp_cwd,
    )
    if args.json:
        print(json.dumps(_as_jsonable(report), indent=2))
    else:
        _print_human(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
