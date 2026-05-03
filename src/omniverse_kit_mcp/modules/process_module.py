"""Isaac Sim process control — start / stop / restart via OS commands.

Launching Isaac Sim is the single most fundamental capability of this MCP server:
everything else (stage / viewport / character / robot / sensor tools) is a no-op
until kit.exe is up and ``/validation/v1/health`` responds. The start path has
to be bullet-proof on a cold boot (no residual env, no warm shader cache).

**Why we mirror isaac-sim.bat instead of exec'ing kit.exe directly.**
NVIDIA ships ``isaac-sim.bat`` as the canonical launcher. That script does two
things before calling kit.exe:

    1. ``setlocal`` so env changes do not leak into the calling shell.
    2. ``call setup_ros_env.bat`` which, when ``ROS_DISTRO`` is unset:
         - sets ``ROS_DISTRO=humble``
         - sets ``RMW_IMPLEMENTATION=rmw_fastrtps_cpp``
         - appends ``<ISAAC_SIM_ROOT>/exts/isaacsim.ros2.bridge/humble/lib`` to PATH

If we skip step (2), a number of Kit extensions that dlopen the ROS2 bridge
shared libraries fail silently during their ``startup`` hook and the Kit event
loop stalls. Externally the process looks alive (kit.exe stays resident around
60 MB) but no HTTP listener ever binds to port 8011 and the 240 s health poll
times out. See ``modules/CLAUDE.md`` (``ProcessModule hang recovery``).

``_prepare_launch_env()`` re-creates the minimum env that makes kit.exe behave
the same way the .bat does, so ``isaac_sim_start`` is reliable from a cold boot
without depending on the operator having sourced ROS beforehand.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from omniverse_kit_mcp.config import IsaacSimProcessConfig

logger = logging.getLogger(__name__)

# Redirect kit.exe stdout/stderr here so the OS pipe buffer never blocks startup.
_STARTUP_LOG_DIR = Path(tempfile.gettempdir()) / "omniverse_kit_mcp"
_STARTUP_LOG_TTL_SECONDS = 7 * 24 * 3600  # 7 days

# Mirrors isaac-sim.bat + setup_ros_env.bat (see module docstring).
_DEFAULT_ROS_DISTRO = "humble"
_DEFAULT_RMW_IMPLEMENTATION = "rmw_fastrtps_cpp"


class ProcessModule:
    """Manages the Isaac Sim kit.exe process lifecycle."""

    def __init__(self, config: IsaacSimProcessConfig) -> None:
        self._config = config
        self._process: subprocess.Popen | None = None
        self._stdout_log_path: Path | None = None
        self._stdout_handle = None

    async def start(self) -> dict[str, Any]:
        """Launch Isaac Sim (or attach to an in-progress one) and wait for health.

        Decision tree (2026-04-23 redesign):
          1. kit.exe alive AND health responding → ``ready`` (idempotent).
          2. kit.exe alive but no health yet → just poll for ``startup_timeout``
             seconds; do NOT respawn (would kill an in-progress cold boot).
          3. kit.exe dead → spawn fresh, then poll.

        On timeout, the response includes ``process_alive`` so the caller can
        distinguish "still loading slowly" (call again to keep polling) from
        "crashed" (read ``log_tail`` for cause). This avoids the prior failure
        mode where 240s timed out mid-cold-boot, kit.exe kept loading on its
        own, and the next ``isaac_sim_start`` call returned ``already_running``
        without verifying health (orphan masquerading as ready).
        """
        cfg = self._config

        # Branch 1: already healthy → idempotent success.
        if await self._is_process_alive() and await self._check_health():
            pid = self._process.pid if self._process is not None else await self._resolve_instance_pid()
            return {
                "ok": True,
                "status": "ready",
                "app_profile": cfg.app_profile.name,
                "instance_id": cfg.instance_id,
                "ext_port": cfg.ext_port,
                "pid": pid,
                "message": (
                    f"{cfg.app_profile.name} instance {cfg.instance_id} already "
                    f"running and healthy on port {cfg.ext_port} (pid={pid})"
                ),
            }

        spawned_now = False
        if await self._is_process_alive():
            # Branch 2: kit.exe alive but health not up. Could be cold boot
            # in progress, or an orphan from a previous failed startup. We
            # do NOT respawn — that would kill a slowly-starting kit.exe.
            # Caller can isaac_sim_stop + isaac_sim_start to force respawn.
            logger.info(
                "kit.exe alive but health not responding — polling without respawn "
                "(call isaac_sim_stop + isaac_sim_start to force respawn)."
            )
        else:
            # Branch 3: spawn fresh.
            await self._cleanup_orphan_hub()
            cmd = [
                cfg.effective_kit_exe,
                cfg.effective_kit_file,
                "--ext-folder", cfg.ext_folder,
                "--enable", cfg.ext_id,
                # Force Extension REST port — prevents allow_port_range
                # fallback (8000-8100 random) that would leave MCP client
                # talking to the wrong kit.exe instance.
                f"--/exts/omni.services.transport.server.http/port={cfg.ext_port}",
            ]
            for extra in cfg.extra_ext_ids:
                cmd.extend(["--enable", extra])
            env = _prepare_launch_env(cfg)

            _STARTUP_LOG_DIR.mkdir(parents=True, exist_ok=True)
            swept = _sweep_old_logs()
            if swept:
                logger.info("Swept %d old kit startup logs (> %d days)", swept, _STARTUP_LOG_TTL_SECONDS // 86400)
            self._stdout_log_path = _STARTUP_LOG_DIR / f"kit_{int(time.time())}.log"
            self._stdout_handle = self._stdout_log_path.open("w", encoding="utf-8")

            logger.info("Starting Isaac Sim: %s", " ".join(cmd))
            logger.info("kit.exe stdout/stderr → %s", self._stdout_log_path)
            logger.info(
                "ROS env: ROS_DISTRO=%s RMW_IMPLEMENTATION=%s",
                env.get("ROS_DISTRO"),
                env.get("RMW_IMPLEMENTATION"),
            )
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,  # CRITICAL: must NOT inherit parent stdin
                stdout=self._stdout_handle,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0,
            )
            # Why stdin=DEVNULL: when MCP server (omniverse-kit-mcp) is launched by
            # Claude Code via stdio, its stdin is the bidirectional MCP protocol
            # pipe. Without explicit DEVNULL, Popen inherits that pipe to the
            # kit.exe child. During cold boot some Kit init component (carb
            # plugin, GLFW, or one of the python modules) reads from stdin —
            # reading from the MCP stdio pipe blocks indefinitely (or worse,
            # consumes MCP protocol bytes intended for the parent server).
            # Symptom: kit.exe alive but internal log freezes at ~85-91ms (after
            # ext registration, before ext startup), CPU near 0, WS ~60MB.
            # Standalone scripts launched from a bash terminal don't hit this
            # because the inherited stdin is a TTY, which read() returns
            # immediately on EOF or never gets read because the boot path
            # checks isatty() first. 2026-04-24 reproduced + fixed.
            spawned_now = True

        # Poll health endpoint
        started_at = time.monotonic()
        timeout = cfg.startup_timeout
        while time.monotonic() - started_at < timeout:
            await asyncio.sleep(2.0)
            if await self._check_health():
                elapsed = round(time.monotonic() - started_at, 1)
                pid = self._process.pid if self._process is not None else await self._resolve_instance_pid()
                return {
                    "ok": True,
                    "status": "started" if spawned_now else "ready",
                    "app_profile": cfg.app_profile.name,
                    "instance_id": cfg.instance_id,
                    "ext_port": cfg.ext_port,
                    "pid": pid,
                    "elapsed_s": elapsed,
                    "startup_log": str(self._stdout_log_path) if self._stdout_log_path else None,
                    "message": (
                        f"{cfg.app_profile.name} instance {cfg.instance_id} ready in "
                        f"{elapsed}s on port {cfg.ext_port} "
                        f"({'newly spawned' if spawned_now else 'attached to existing process'})"
                    ),
                }

        # Timeout — diagnose process state for the caller.
        process_alive = await self._is_process_alive()
        log_tail = self._tail_log(20)
        elapsed = round(time.monotonic() - started_at, 1)
        if process_alive:
            return {
                "ok": False,
                "status": "still_loading",
                "app_profile": cfg.app_profile.name,
                "instance_id": cfg.instance_id,
                "ext_port": cfg.ext_port,
                "process_alive": True,
                "elapsed_s": elapsed,
                "startup_log": str(self._stdout_log_path) if self._stdout_log_path else None,
                "log_tail": log_tail,
                "message": (
                    f"{cfg.app_profile.name} instance {cfg.instance_id} kit.exe alive "
                    f"but health endpoint did not respond within {timeout}s. Cold boot "
                    f"(GPU shader cache rebuild) can take 5-10 min — call start again "
                    f"to keep polling, or stop to abort."
                ),
            }
        return {
            "ok": False,
            "status": "crashed",
            "app_profile": cfg.app_profile.name,
            "instance_id": cfg.instance_id,
            "ext_port": cfg.ext_port,
            "process_alive": False,
            "elapsed_s": elapsed,
            "startup_log": str(self._stdout_log_path) if self._stdout_log_path else None,
            "log_tail": log_tail,
            "message": (
                f"{cfg.app_profile.name} instance {cfg.instance_id} kit.exe died "
                f"within {timeout}s. Inspect log_tail / startup_log for the cause."
            ),
        }

    async def stop(self) -> dict[str, Any]:
        """Terminate THIS instance's kit.exe only. Does not affect other
        instances or other app profiles.

        Response fields:
          - instance_id, app_profile, ext_port, pid: identification
          - status: stopped / not_running / timeout / error
        """
        was_running = await self._is_process_alive()

        pid_to_kill: int | None = None
        if self._process is not None and self._process.pid is not None:
            pid_to_kill = self._process.pid
        else:
            pid_to_kill = await self._resolve_instance_pid()

        if was_running and pid_to_kill is not None:
            try:
                subprocess.run(
                    ["cmd", "/c", "taskkill", "/F", "/PID", str(pid_to_kill), "/T"],
                    capture_output=True, text=True, timeout=10,
                )
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "status": "error", "message": str(e)}

        await self._cleanup_orphan_hub()

        if not was_running:
            return {
                "ok": True,
                "status": "not_running",
                "app_profile": self._config.app_profile.name,
                "instance_id": self._config.instance_id,
                "ext_port": self._config.ext_port,
                "message": f"{self._config.app_profile.name} instance {self._config.instance_id} is not running",
            }

        try:
            for _ in range(10):
                await asyncio.sleep(1.0)
                if not await self._is_process_alive():
                    self._process = None
                    self._close_stdout_handle()
                    return {
                        "ok": True,
                        "status": "stopped",
                        "app_profile": self._config.app_profile.name,
                        "instance_id": self._config.instance_id,
                        "ext_port": self._config.ext_port,
                        "pid": pid_to_kill,
                        "message": (
                            f"{self._config.app_profile.name} instance "
                            f"{self._config.instance_id} terminated (pid={pid_to_kill})"
                        ),
                    }
            return {"ok": False, "status": "timeout", "message": "Process did not terminate in 10s"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "status": "error", "message": str(e)}

    async def list_kit_instances(self) -> dict[str, Any]:
        """Enumerate every running kit.exe on the host (read-only).

        Returns ALL ``kit.exe`` processes currently running — MCP-spawned,
        other MCP servers (multi-instance / multi-app), and user GUI
        launches alike. The response classifies each entry against THIS
        MCP server's config (``ext_port`` match) so the caller can tell
        which kit the current ``isaac_sim_*`` tools control vs. which
        live outside this server's reach.

        Use BEFORE destructive operations (Kit user.config.json edit,
        ``__pycache__`` outside ext_folder cleanup, settings reset,
        extension force-reload) — Kit instances persist their settings
        on shutdown, so any externally-launched kit.exe will overwrite
        your edits when it exits.

        Per-instance fields:
          - ``pid``: int
          - ``command_line``: str (full Win32 CommandLine)
          - ``start_time_utc``: ISO8601 string (CIM ``CreationDate``)
          - ``ext_port``: int | None — parsed from ``port=<N>`` substring
          - ``app_profile``: str | None — last ``apps/<name>.kit`` segment
          - ``is_this_mcp_instance``: bool — ``ext_port`` matches
            ``self._config.ext_port`` (the server processing this call)

        Windows-only (PowerShell + Win32_Process). On non-Windows hosts
        returns ``{ok: false, status: "unsupported_platform"}``.
        """
        import json as _json
        import re as _re

        if os.name != "nt":
            return {
                "ok": False,
                "status": "unsupported_platform",
                "message": "list_kit_instances requires Windows (PowerShell Win32_Process).",
                "instances": [],
            }

        try:
            ps_script = (
                "Get-CimInstance Win32_Process -Filter \"Name='kit.exe'\" "
                "| Select-Object ProcessId, CommandLine, "
                "@{N='StartTimeUtc';E={$_.CreationDate.ToUniversalTime().ToString('o')}} "
                "| ConvertTo-Json -Depth 2 -Compress"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "status": "timeout",
                    "message": "PowerShell Win32_Process query exceeded 10s",
                    "instances": []}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "status": "error", "message": str(e),
                    "instances": []}

        out = (result.stdout or "").strip()
        if not out:
            return {"ok": True, "status": "ok", "instances": []}

        try:
            raw = _json.loads(out)
        except _json.JSONDecodeError as e:
            return {"ok": False, "status": "parse_error",
                    "message": f"PowerShell JSON parse failed: {e}",
                    "instances": []}

        # Single-row result is a dict, multi-row is a list — normalize.
        rows = raw if isinstance(raw, list) else [raw]

        port_re = _re.compile(r"port=(\d+)")
        app_re = _re.compile(r"apps[\\/]([\w.\-]+)\.kit", _re.IGNORECASE)
        my_port = self._config.ext_port

        instances: list[dict[str, Any]] = []
        for row in rows:
            cmd = row.get("CommandLine") or ""
            port_m = port_re.search(cmd)
            app_m = app_re.search(cmd)
            ext_port = int(port_m.group(1)) if port_m else None
            app_profile = app_m.group(1) if app_m else None
            instances.append({
                "pid": int(row.get("ProcessId")) if row.get("ProcessId") is not None else None,
                "command_line": cmd,
                "start_time_utc": row.get("StartTimeUtc"),
                "ext_port": ext_port,
                "app_profile": app_profile,
                "is_this_mcp_instance": ext_port == my_port,
            })

        return {
            "ok": True,
            "status": "ok",
            "this_mcp_ext_port": my_port,
            "this_mcp_app_profile": self._config.app_profile.name,
            "instance_count": len(instances),
            "instances": instances,
        }

    async def restart(self) -> dict[str, Any]:
        """Stop Isaac Sim, clear caches, restart with fresh code."""
        # Stop
        stop_result = await self.stop()
        if not stop_result["ok"] and stop_result["status"] != "not_running":
            return {"ok": False, "status": "stop_failed", "message": stop_result["message"]}

        # Clear __pycache__
        ext_dir = Path(self._config.ext_folder)
        cleared = 0
        for cache_dir in ext_dir.rglob("__pycache__"):
            shutil.rmtree(cache_dir, ignore_errors=True)
            cleared += 1
        logger.info("Cleared %d __pycache__ directories", cleared)

        await asyncio.sleep(2.0)

        # Start
        start_result = await self.start()
        start_result["caches_cleared"] = cleared
        return start_result

    async def _resolve_instance_pid(self) -> int | None:
        """Locate the kit.exe PID for THIS instance by CommandLine match.

        Uses PowerShell CIM query filtered on the unique port=<N> substring
        injected during launch. Since each instance has a different port,
        this uniquely identifies our kit.exe even if MCP server restarted
        and lost self._process.pid.

        Returns None if no match (kit died or was never spawned for this
        profile/instance combo).
        """
        port_needle = f"port={self._config.ext_port}"
        try:
            ps_script = (
                "Get-CimInstance Win32_Process -Filter \"Name='kit.exe'\" "
                f"| Where-Object {{ $_.CommandLine -like '*{port_needle}*' }} "
                "| Select-Object -First 1 -ExpandProperty ProcessId"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=5,
            )
            out = result.stdout.strip()
            if not out:
                return None
            return int(out.splitlines()[0])
        except (ValueError, Exception):  # noqa: BLE001 — best-effort probe
            return None

    async def _is_process_alive(self) -> bool:
        """True iff THIS instance's kit.exe is running.

        Fast path: if self._process has a known PID, query that directly.
        Fallback: use CommandLine-based PID resolution (MCP server restart
        recovery — self._process is None but kit is still running).
        """
        if self._process is not None and self._process.pid is not None:
            try:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command",
                     f"Get-Process -Id {self._process.pid} -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.stdout.strip():
                    return True
            except Exception:  # noqa: BLE001
                pass
            self._process = None
        return (await self._resolve_instance_pid()) is not None

    async def _check_health(self) -> bool:
        """Check if the validation API health endpoint responds."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(self._config.health_url)
                return resp.status_code == 200
        except Exception:
            return False

    def _tail_log(self, n: int) -> list[str]:
        """Return the last n non-empty lines of the most recent kit.exe log.

        Used by ``start()`` to surface the cause of a startup failure without
        forcing the caller to open the file. Falls back to scanning
        ``_STARTUP_LOG_DIR`` if ``self._stdout_log_path`` is unset (e.g.
        attached to an externally-launched kit.exe).
        """
        path = self._stdout_log_path
        if path is None or not path.exists():
            try:
                if _STARTUP_LOG_DIR.exists():
                    candidates = sorted(
                        _STARTUP_LOG_DIR.glob("kit_*.log"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )
                    path = candidates[0] if candidates else None
            except Exception:
                path = None
        if path is None or not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                lines = [ln.rstrip() for ln in f.readlines() if ln.strip()]
            return lines[-n:]
        except Exception:
            return []

    def _close_stdout_handle(self) -> None:
        """Close the stdout log file handle (non-fatal if already closed)."""
        if self._stdout_handle is not None:
            try:
                self._stdout_handle.close()
            except Exception:
                pass
            self._stdout_handle = None

    async def _cleanup_orphan_hub(self) -> None:
        """Best-effort hub.exe cleanup. SKIPPED if any other kit.exe alive.

        hub.exe is a shared --mode=shared daemon (port 14090). All kit.exe
        instances on this host talk to the same hub. Killing it while any
        kit is still running breaks that kit's asset resolution. Therefore
        we only cleanup when no kit.exe is running anywhere on the host —
        meaning the whole Kit stack is being torn down.

        The "my own PID" is excluded from the alive count (we may still
        have it registered self._process.pid even though we just issued
        taskkill for it).
        """
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Get-Process -Name kit -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
                capture_output=True, text=True, timeout=5,
            )
            alive_pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            my_pid = self._process.pid if self._process is not None else None
            others = [p for p in alive_pids if my_pid is None or p != str(my_pid)]
            if others:
                logger.info(
                    "Skipping hub.exe cleanup — %d other kit.exe instance(s) alive: %s",
                    len(others), others,
                )
                return
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to enumerate kit.exe — proceeding with hub cleanup: %s", e)

        try:
            subprocess.run(
                ["cmd", "/c", "taskkill", "/F", "/IM", "hub.exe", "/T"],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:  # noqa: S110 — best-effort cleanup
            pass
        temp = Path(tempfile.gettempdir())
        for pattern in ("hub-*.lock", "hub-*.config.json"):
            for p in temp.glob(pattern):
                try:
                    p.unlink()
                except Exception:  # noqa: S110
                    pass


def _sweep_old_logs() -> int:
    """Delete kit startup logs older than ``_STARTUP_LOG_TTL_SECONDS``."""
    if not _STARTUP_LOG_DIR.exists():
        return 0
    cutoff = time.time() - _STARTUP_LOG_TTL_SECONDS
    swept = 0
    for log_file in _STARTUP_LOG_DIR.glob("kit_*.log"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                swept += 1
        except Exception:  # noqa: S110 — best-effort cleanup
            pass
    return swept


def _prepare_launch_env(cfg: IsaacSimProcessConfig) -> dict[str, str]:
    """Build env dict for Kit app launch — profile-aware.

    Isaac Sim needs isaac-sim.bat's env setup (ROS_DISTRO, RMW_IMPLEMENTATION,
    PATH with ros2.bridge lib) or ROS2-dependent extensions hang Kit init.
    USD Composer has no ROS dependency and explicit ROS env could confuse
    unrelated extensions (omni.services.*).

    Decision is driven by cfg.app_profile.ros_env_required.
    """
    env = os.environ.copy()

    if not cfg.app_profile.ros_env_required:
        for var in ("ROS_DISTRO", "RMW_IMPLEMENTATION"):
            env.pop(var, None)
        return env

    env.setdefault("ROS_DISTRO", _DEFAULT_ROS_DISTRO)
    env.setdefault("RMW_IMPLEMENTATION", _DEFAULT_RMW_IMPLEMENTATION)

    isaac_sim_root = Path(cfg.effective_kit_exe).parent.parent
    ros_lib = isaac_sim_root / "exts" / "isaacsim.ros2.bridge" / env["ROS_DISTRO"] / "lib"
    if ros_lib.is_dir():
        current_path = env.get("PATH", "")
        ros_lib_str = str(ros_lib)
        if ros_lib_str not in current_path.split(os.pathsep):
            env["PATH"] = (
                f"{current_path}{os.pathsep}{ros_lib_str}" if current_path else ros_lib_str
            )
    else:
        logger.warning(
            "ROS bridge lib dir not found under %s — Isaac extensions that dlopen"
            " the bridge DLLs may hang during startup",
            ros_lib,
        )
    return env
