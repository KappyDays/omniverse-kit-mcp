<!-- Parent: CLAUDE.md -->
<!-- Scope: ProcessModule Operation Manual — Refer to when starting up or setting up the environment -->

# ProcessModule — Operations Manual

Operating data related to kit.exe startup/shutdown. No need to read during normal development flow.
For reference only in the following situations:
- When `kit_app_start` returns `still_loading` / `crashed`
- When kit.exe hang / zombie is suspected
- When `.env` environment variable is not reflected

Required knowledge before work: `../../../docs/invariants/process-lifecycle.md`. Diagnosis by disability
Procedure: `../../../docs/runbooks/` (kit-stdin-deadlock / cold-boot-timeout /
hub-orphan/env-sub-config).

## ProcessModule stdin/stdout/stderr convention (no modification)

- **`stdin=subprocess.DEVNULL` required** (root cause confirmed on 2026-04-24 — `../../../docs/runbooks/kit-stdin-deadlock.md` must be read). MCP server is the stdio child of MCP host (Claude Code / Codex CLI) → its stdin is MCP protocol pipe. If the ProcessModule does not specify `subprocess.Popen` or `stdin`, the child kit.exe inherits the pipe → blocks when reading stdin during cold boot → complete boot stop (at ~85 ms, immediately after ext registration). Standalone execution in bash is safe because TTY stdin — Because of this difference, standalone passes / MCP causes a false negative of hang.
- `stdout` / `stderr` redirects to **`%TEMP%/omniverse_kit_mcp/kit_<epoch>.log`**. **Prohibit `subprocess.DEVNULL` on stdout/stderr** — Stop initializing kit.exe when Windows OS pipe buffer is full (opposite of stdin)
- `startup_timeout` default 120 s (confirmed by user 2026-04-23). Intent: **Return diagnostic information quickly rather than waiting until the end of cold boot**. Even if cold boot (GPU shader cache rebuild) takes 5-10 minutes, `status=still_loading` + `process_alive=true` is returned after timeout → If the caller calls `kit_app_start` again, polling continues without spawn (Branch 2). **Cold boot after stdin fix usually takes 13-30 seconds** — 5-10 minute case is suspected to be transient (hub orphan/pycache corruption)
- `ProcessModule.start()` returns `startup_log` + `log_tail` fields of dict to determine the cause of failure
- `start()` is automatically deleted 7 days ago as `_sweep_old_logs()` at every startup.

## ProcessModule.start() decision tree (2026-04-23 redesign)

```
process alive?
├─ NO  → spawn fresh + poll health (startup_timeout seconds)
└─ YES → health responding?
         ├─ YES → return status=ready (idempotent)
         └─ NO  → poll health WITHOUT respawn (startup_timeout seconds)
                  (may still be cold-booting; do not force-kill)
```

Timeout response (when `startup_timeout` is reached):
- `process_alive=true` → `{status: "still_loading", log_tail: [...], pid}` — Branch 2 polling continues by recalling the caller
- `process_alive=false` → `{status: "crashed", log_tail: [...]}` — Immediate diagnosis (commonly: ext missing / MDL deadlock / GPU driver)If forced recovery of orphan kit.exe is required, explicitly call `kit_app_stop` + `kit_app_start` (safe replacement for the old "auto force-kill"). Log tail analysis procedure: `../../../docs/runbooks/cold-boot-timeout.md`.

## ProcessModule hang recovery (restart failed after GUI X-close)

**Symptom**: `kit_app_start` response repeats as `still_loading` (process_alive=true but health remains unresponsive forever) — orphan or real hang.

**Causes (Quadruple, in order of frequency of occurrence)**:
1. **stdin pipe inheritance** (Confirmed on 2026-04-24, most common and dangerous): MCP server (`omniverse-kit-mcp`) is the stdio child of MCP host (Claude Code / Codex CLI) → If `stdin` is not specified in `subprocess.Popen(...)`, child kit.exe inherits MCP protocol pipe as stdin → Blocks when attempting to read stdin during cold boot → Full boot Stop. Symptoms: alive + CPU ~0 + WS ~60MB + internal log mtime ~85ms. **`subprocess.Popen(stdin=subprocess.DEVNULL, ...)` must be specified** (Currently ProcessModule applied). If you run a standalone script in bash, it is safe because stdin=TTY — this difference is a common cause of false negatives (“It works in standalone, but hangs in MCP” → suspected of missing stdin DEVNULL)
2. **ROS env missing**: If `ProcessModule` and `subprocess.Popen(env=)` are not specified, `ROS_DISTRO` / `RMW_IMPLEMENTATION` / `PATH` (`ros2.bridge/humble/lib`) are missing → Kit extension dependent on ROS2 bridge silently fails at the startup hook → kit.exe event loop stops. **Automatically avoided with the introduction of `_prepare_launch_env()` on 2026-04-19** (`../../../docs/invariants/process-lifecycle.md`). In case of recurrence, check the ROS env line in startup_log
3. **MDL resolver deadlock**: `LogCaptureService` is active + when loading S3 MDL-heavy asset, carb log callback stops main loop due to GIL contention. log_tail is silent after the last iteration of `"Disabling base URL to resolve MDL identifier"`. Avoidance: Maintain the three-factor baseline of `../../../docs/invariants/usd-load.md`
4. **Hub orphan**: `omni.client` spawns `hub.exe` as `--mode=shared` → daemon separated from the kit process tree → Even if the kit is terminated, port 14090 orphan remains. As time passes, the accept loop is broken and `netstat` is LISTENING, but the new connection is `10061 refused` → OmniHub init of the next kit fails, and `"Hub failed to launch: child exited with exit code: 1"` is repeated in startup_log. `ProcessModule._cleanup_orphan_hub()` automatically removes `taskkill /F /IM hub.exe /T` + `%TEMP%/hub-*.{lock,config.json}` from both sides of `stop/start`. Manual recovery: `../../../docs/runbooks/hub-orphan.md`**Recovery Procedure**:
1. Check `log_tail` in `kit_app_start` response → Check MDL deadlock signature or ext load failure
2. If it is determined to be a true hang, force termination: `cmd //c "taskkill /F /IM kit.exe /T"` (Actual measurement: only successful. PowerShell `Stop-Process` / `taskkill /F /PID <pid>` is "Access is denied"). Convenience script: `../../../scripts/kill_kit_zombie.sh`
3. Minimal ext direct launch (quick health check by bypassing cold boot):
   ```bash
   nohup "C:/.../kit/kit.exe" "C:/.../apps/isaacsim.exp.full.kit" \
     --ext-folder "C:/.../omniverse-kit-mcp/kkr-extensions" \
     --enable omni.mycompany.validation_api \
     > "$LOG" 2>&1 &
   ```
Afterwards, MCP `kit_app_start` detects alive + responds ready by polling health
4. When Character / Navigation / UI automation is required: After checking the minimal endpoint, restart `.env` full ext-list with `kit_app_restart`

**Hang Confirmation Indicator** (Accurate Tool):
- **`kit_app_start` response** — It is `process_alive=true`, but it is not ready even after repeated calls + log_tail mtime has been stagnant for several minutes
- **PowerShell `Get-Process -Name kit -ErrorAction SilentlyContinue`** — No row = dead, alive if row exists (suspicious of hang if CPU freezes + WorkingSet congestion)
- **MCP `simulation_get_status`** — response (duration_ms < 1000) = alive, connection refused = dead
- **`curl http://127.0.0.1:8111/validation/v1/health`** — 200 response = alive
- No `netstat -ano | grep ":8111" | grep LISTENING` = Endpoint not started
- `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log` mtime has been stagnant for several minutes

**Prohibited** (results in a false negative): `tasklist //FI "IMAGENAME eq kit.exe"` (calls git bash). Due to a filter processing timing issue, the alive kit also returned an empty result. This is the result of user verification on 2026-04-23, and the current rules are stored in `../../../docs/invariants/process-lifecycle.md`.

## `.env` ↔ sub-config trap (discovered 2026-04-23)

pydantic-settings v2 does not propagate the parent's `env_file` to sub-`BaseSettings` instances created with `default_factory`. Every sub-config (`IsaacSimConfig`, `IsaacSimProcessConfig`, `LakehouseConfig`, `MCPServerConfig`, `ScenarioConfig`) must have its own `model_config = SettingsConfigDict(env_prefix=..., env_file=".env", extra="ignore")`. If missing, refer only to OS environment variables → `.env` silently ignored.

**Symptoms (actual measurements)**:
- Ignore `ISAAC_SIM_STARTUP_TIMEOUT=120.0` of `.env` → Always use default 240.0
- `.env` ignores `ISAAC_SIM_EXTRA_EXT_IDS=[7 entries]` → Only default 4 are always active → `omni.mycompany.navmesh_playground`, etc. are not registered

**Verification**:
```bash
.venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout, len(ac.isaac_sim_process.extra_ext_ids))"
```
→ `.env` value must be reflected. Incident Record + Recurrence Prevention Checklist: `../../../docs/runbooks/env-sub-config.md`.

## Isaac Sim Standalone path (ProcessModule default)

```
<isaac-sim-root>\
  ├── kit\kit.exe
  └── apps\isaacsim.exp.full.kit
```

Other users override `.env` to `ISAAC_SIM_KIT_EXE` + `ISAAC_SIM_KIT_FILE` (see README §"Isaac Sim Setup").

## Related Boundaries- Code SoT: `process_module.py::start` / `process_module.py::_cleanup_orphan_hub`
- Process lifecycle invariants (required before work): `../../../docs/invariants/process-lifecycle.md`
- stdin pipe deadlock (L17): `../../../docs/runbooks/kit-stdin-deadlock.md`
- Cold boot timeout branch: `../../../docs/runbooks/cold-boot-timeout.md`
- Hub orphan recovery: `../../../docs/runbooks/hub-orphan.md`
- Env sub-config trap (L14): `../../../docs/runbooks/env-sub-config.md`
- Module Responsibility Matrix + Character Constraints: `CLAUDE.md` (sibling)
- Integration Facts (15 domains): `integration-facts.md` (sibling)
- Standalone test script: `../../../scripts/run_process_module_standalone.py`