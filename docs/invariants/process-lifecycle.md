<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: kit_app_start / kit_app_stop / kit_app_restart Required knowledge before starting work -->
<!-- Multi-app context: “kit.exe” in this document applies equally to all app profiles.
For launch differences by profile, see `docs/invariants/multi-app.md`. -->
# Process Lifecycle — Invariants

All stage / viewport / character / robot / sensor / scenario tools on this MCP server are
It is meaningless until `kit.exe` is started and `GET /validation/v1/health` responds with 200.
Read this file before calling ProcessModule.

## Tool operation summary

| Tool | movement | normal time |
|------|------|----------|
| `kit_app_start` | Launch kit.exe (or attach alive process) + health polling (2 s interval, up to `startup_timeout`) | warm boot 15-30 s cold boot 13-30 s (after stdin DEVNULL fix) |
| `kit_app_stop` | `taskkill /F /IM kit.exe /T` + clean up orphan hub | ≤10 s |
| `kit_app_restart` | stop → `kkr-extensions/.../__pycache__` clear → start | stop + start sum |

## Restart minimization principle

The default entry point for live verification is `kit_app_start`. The kit for this MCP instance is already
If it is alive and its health is 200, it ends with attach/idempotent ready, and the user can
As with work, keep the process lifetime long. `kit_app_restart` is fresh stage or
This is not a general preparation step for repeated verification.

`kit_app_restart` acceptance conditions:
- crash/hang confirmed (`simulation_get_status` refused or start timeout repeated + log stuck)
- `omni.mycompany.validation_api` Reflects changes to own code
- Change extension.toml `[dependencies]`/native dll/app profile
- `extension_reload(ext_id)` or marker verification failed
- User explicitly requests fresh process

If you change user/demo Extension `.py` other than validation_api, you must first change `extension_reload(ext_id)`
Use and check whether it is reflected with marker response. Promotes to restart only in case of failure.

## ⚠️ stdin=subprocess.DEVNULL required (protected regression fact)

`subprocess.Popen(...)` of `src/omniverse_kit_mcp/modules/process_module.py::start` is
If `stdin=subprocess.DEVNULL` is not specified, the MCP server child kit.exe runs on the MCP host (Claude Code / Codex CLI).
Inherit MCP protocol stdin pipe → indefinite block when reading stdin during cold boot →
Full boot stop. **240s timeout, 13s ready verification (L17)**. The "extra_ext_ids race" diagnosis is
Void — stdin pipe is the actual cause.

Text / Reproduction / Recovery: `docs/runbooks/kit-stdin-deadlock.md`

## `kit_app_start` decision tree (2026-04-23 redesign)

```
process alive?
├─ NO  → spawn fresh + poll health (startup_timeout seconds)
└─ YES → health responding?
         ├─ YES → return status=ready (idempotent)
         └─ NO  → poll health WITHOUT respawn (startup_timeout seconds)
                  (may still be cold-booting; do not force-kill)
```

## Timeout response (when `startup_timeout` expires)- `process_alive=true` → `{status: "still_loading", log_tail: [...], pid}` —
Polling continues without spawn by recalling the caller
- `process_alive=false` → `{status: "crashed", log_tail: [...]}` —
Immediate diagnosis (commonly: ext missing / MDL deadlock / GPU driver)

Response branch / log_tail interpretation pattern: `docs/runbooks/cold-boot-timeout.md`

## stdout/stderr convention (no changes)

- `stdout` / `stderr` redirects to `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log`
- **`subprocess.DEVNULL` prohibited** (opposite of stdin) — When Windows OS pipe buffer is full
kit.exe initialization stop
- `start()` is automatically deleted as `_sweep_old_logs()` at every startup. `kit_*.log` 7 days old.
- `startup_log` + `log_tail` fields are used to determine the cause of failure.

## startup_timeout default

- Default 120 s (confirmed by user 2026-04-23). Intent: Return quick diagnostic information
- Even if cold boot (GPU shader cache rebuild) takes 5-10 minutes, after timeout `still_loading` +
Returns `process_alive=true` → When called again, Branch 2 polling continues.
- Cold boot after stdin fix is ​​usually 13-30 seconds — 5-10 minute cases are transient.
(hub orphan/pycache corruption) suspected

## ROS env automatic setup (prevents silent fail)

`src/omniverse_kit_mcp/modules/process_module.py::_prepare_launch_env` is in isaac-sim.bat
Reproduce ROS env setup in Python — If omitted, ROS2 bridge depends on ext silent fail →
kit.exe event loop stopped → `/health` unresponsive.

## OmniHub orphan warning

kit.exe separates `hub.exe` into `--mode=shared` daemon and spawn → `taskkill /T`
The hub does not reach the kit tree and port 14090 orphan remains. Accept loop after several hours
broken → next start `"Hub failed to launch: exit code 1"`.

Automatic processing: `ProcessModule._cleanup_orphan_hub()` is automatically processed on both sides of `stop/start`
execution. Manual recovery procedure: `docs/runbooks/hub-orphan.md`

## `.env` ↔ sub-config propagation (L14)

pydantic-settings v2 sets parent's `env_file` to `default_factory` sub-`BaseSettings`
Does not spread. All sub-configs (`IsaacSimConfig`, `IsaacSimProcessConfig`,
`LakehouseConfig`, `MCPServerConfig`, `ScenarioConfig`) is itself `env_file=".env"`
Required to have.

Verification command:
```bash
.venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout)"
```
→ Confirm that the `.env` value is reflected. In case of omission, silent failure.

Accident + Reoccurrence Prevention Checklist: `docs/runbooks/env-sub-config.md`

## External instance check (required before destructive operation)

`kit_app_stop` terminates **only the kit.exe spawned by this MCP server**. User GUI
Run standalone Isaac Sim, other MCP server (multi-instance / multi-app) is separate
Can survive as a process — Kit will set carb persistent settings (e.g.
`%LOCALAPPDATA%\ov\data\Kit\<app>\<ver>\user.config.json`) overwrite in memory
Therefore, **if you edit the config while the external instance is alive, the changes will be lost on shutdown**.

### Inspection procedure

Call `process_list_kit_instances` MCP tool before destructive operation:

```
process_list_kit_instances → instances[].is_this_mcp_instance == false row is
if present, it is an external instance — ask the user to close it before proceeding
```

### Destructive task definition (affected by external instances)

- Edit Kit `user.config.json` / `*.toml` (carb persistent settings)
- Delete `%LOCALAPPDATA%\ov\data\Kit\<app>` cache/extension data
- Force reload like `extension_activate(reload=True)` (no effect on other instances)
file conflicts possible)
- Omniverse common config editing such as `omniverse.toml` / `hub.toml`

### Impact-free (safe) operation

- Delete `__pycache__` (`kit_app_restart` is automatic — ext_folder only)
- `kit.exe stdout/stderr log sweep` (`_sweep_old_logs`, 7 days ago)
- `simulation_*` / `stage_*` / `viewport_*` (via Extension REST — another instance
REST and isolation)

## Hang Confirmation Indicator (Accurate Tool)

- **`kit_app_start` response** — It is `process_alive=true`, but it is not ready even if called repeatedly +
log_tail mtime stagnant for several minutes
- **PowerShell** `Get-Process -Name kit -ErrorAction SilentlyContinue` —
No row = death, alive if there is a row
- **MCP `simulation_get_status`** — response (duration_ms < 1000) = alive, refused = death
- **`curl http://127.0.0.1:8111/validation/v1/health`** — 200 = alive
- `netstat -ano | grep ":8111" | grep LISTENING` None = Endpoint not started

**Forbidden** (false negative — L7): `tasklist //FI "IMAGENAME eq kit.exe"` (git bash)
Due to a filter processing timing issue, the alive kit also returned an empty result.

## `.bat` wrapper PID ≠ kit.exe PID (avoiding false-positive EXITED)

When launching external kit `.bat` of `branch/` in the background in manual diagnosis (PowerShell):

```powershell
$proc = Start-Process -FilePath $bat `
    -RedirectStandardOutput $log -RedirectStandardError $err `
    -PassThru -WindowStyle Hidden
# $proc.Id is the .bat host cmd.exe or the .bat process PID — kit.exe not the kit.exe PID
```

`.bat` spawns a child kit.exe internally as `call "%~dp0kit\kit.exe" ...` and
atmosphere. The host wrapper follows the child's termination and terminates along with it, so as long as kit.exe is alive,
The wrapper PID is also alive — **but in some cases (cmd.exe wrapper will detach immediately,
Or, after kit.exe fastShutdown, only the wrapper remains and terminates immediately), the wrapper PID is
First it disappears and reports a false-positive `EXITED`**.

Recommended tools for life and death confirmation:```powershell
# check the child kit.exe itself (compare PID for a multi-instance host)
Get-Process -Name kit -ErrorAction SilentlyContinue

# child process tree of the parent wrapper PID
Get-CimInstance Win32_Process -Filter "ParentProcessId=<wrapperPID>" |
    Select-Object ProcessId, Name, CommandLine
```

(In multi-app / multi-instance, `Get-Process -Name kit` is all kit.exe on the host.
Matching — identified as `port=<N>`. Refer to §"Process Identification (name scope prohibited)" in main text —
[`multi-app.md`](multi-app.md))

## Related Boundaries

- Code location SoT (4 types of ProcessModule hang recovery traps): `src/omniverse_kit_mcp/modules/process-ops.md`
- Standalone test script: `scripts/run_process_module_standalone.py`
- Protected regression body (reproduction/recovery): `docs/runbooks/kit-stdin-deadlock.md`
- Cold boot timeout branch interpretation: `docs/runbooks/cold-boot-timeout.md`
- Hub orphan manual recovery: `docs/runbooks/hub-orphan.md`
- Env sub-config trap body: `docs/runbooks/env-sub-config.md`
