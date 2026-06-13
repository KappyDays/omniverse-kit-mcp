<!-- SoT: src/omniverse_kit_mcp/modules/process_module.py::ProcessModule.start + types/profile.py + .env -->
<!-- This document is a human-reproducible form of the actual commands spawned by the MCP `kit_app_start` tool. -->
<!-- If profile / .env changes, update this document as well. -->

# Kit Run Command — Isaac Sim & USD Composer

The actual commands issued by MCP `kit_app_start` to `subprocess.Popen` are organized in a form that can be reproduced by humans. Used for ProcessModule bypass debugging (direct startup without MCP server).

## Common conventions

| Item | value | Remarks |
|------|-----|------|
| `--ext-folder` | `<repo>/kkr-extensions` | All profiles are the same |
| `--enable` (REST bridge) | `omni.mycompany.validation_api` | Always primary enable |
| Extension REST port flag | `--/exts/omni.services.transport.server.http/port=<PORT>` | Forced binding for port range fallback blocking |
| `stdin` | **`DEVNULL` required** | Cold boot hang when inheriting MCP stdio. Direct PowerShell execution is also recommended by `< NUL` |
| `stdout` / `stderr` | `%TEMP%/omniverse_kit_mcp/kit_<epoch>.log` | OS pipe buffer saturation → prevent kit hang |

## Port matrix (instance_id → ext_port)

| Profile | Instance 1 | Instance 2 |
|---------|-----------|-----------|
| `isaac-sim` | 8111 | 8112 |
| `usd-composer` | 8114 | 8115 |

Health URL: `http://127.0.0.1:<PORT>/validation/v1/health`

---

## MCP-safe manual launchers

The recommended manual execution entry point is the file copied from the original repo `setup/launchers/*_mcp.*` to each app folder.

| App | Installed launcher | Ports |
|---|---|---|
| Isaac Sim | `<isaac-sim-root>/isaac-sim_mcp.bat` | 8111 → 8112 |
| USD Composer | `<usd-composer-root>/kkr_usd_composer_mcp.kit.bat` | 8114 → 8115 |

Both launchers support `--dry-run`, `--instance 1|2`, and `--port <PORT>`, and deliver the selected port to the kit as `--/exts/omni.services.transport.server.http/port=<PORT>` and `allow_port_range=false`.

```powershell
& "<usd-composer-root>/kkr_usd_composer_mcp.kit.bat" --dry-run
& "<usd-composer-root>/kkr_usd_composer_mcp.kit.bat" --instance 2
```

---

## Isaac Sim

### path

-`kit.exe`:`<isaac-sim-root>/kit/kit.exe`
-`.kit`:`<isaac-sim-root>/apps/isaacsim.exp.full.kit`

### Extension enable list

`ISAAC_SIM_EXTRA_EXT_IDS` of `.env` is applied (override profile default). Current `.env` values:

```
omni.anim.graph.bundle
omni.anim.navigation.bundle
isaacsim.replicator.agent.core
omni.kit.ui_test
isaacsim.sensors.rtx
omni.graph.action
omni.replicator.core
omni.mycompany.navmesh_playground
```

### ROS environment variables (required — prevent silent fail)

`isaac-sim.bat` + `setup_ros_env.bat` equivalent — If missing, ROS2 bridge dlopen dependent ext silently fails → kit event loop stops → /health does not respond.

| variable | value |
|------|-----|
| `ROS_DISTRO` | `humble` |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` |
| `PATH` | Original `PATH` + `;<isaac-sim-root>/exts/isaacsim.ros2.core/humble/lib` |

Isaac Sim 6.0.0 ships ROS 2 runtime libraries under `isaacsim.ros2.core`.
If a local build only contains the legacy bridge lib directory, use
`<isaac-sim-root>/exts/isaacsim.ros2.bridge/humble/lib` as a compatibility fallback.

### command (instance 1, port 8111)

PowerShell:

```powershell
$env:ROS_DISTRO = "humble"
$env:RMW_IMPLEMENTATION = "rmw_fastrtps_cpp"
$env:PATH = "$env:PATH;<isaac-sim-root>/exts/isaacsim.ros2.core/humble/lib"

& "<isaac-sim-root>/kit/kit.exe" `
  "<isaac-sim-root>/apps/isaacsim.exp.full.kit" `
  --ext-folder "<repo>/kkr-extensions" `
  --enable omni.mycompany.validation_api `
  --/exts/omni.services.transport.server.http/port=8111 `
  --enable omni.anim.graph.bundle `
  --enable omni.anim.navigation.bundle `
  --enable isaacsim.replicator.agent.core `
  --enable omni.kit.ui_test `
  --enable isaacsim.sensors.rtx `
  --enable omni.graph.action `
  --enable omni.replicator.core `
  --enable omni.mycompany.navmesh_playground `
  *> "$env:TEMP/omniverse_kit_mcp/kit_isaac_$(Get-Date -UFormat %s).log" `
  < $null
```

bash (Git Bash):

```bash
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export PATH="$PATH:<isaac-sim-root>/exts/isaacsim.ros2.core/humble/lib"

"<isaac-sim-root>/kit/kit.exe" \
  "<isaac-sim-root>/apps/isaacsim.exp.full.kit" \
  --ext-folder "<repo>/kkr-extensions" \
  --enable omni.mycompany.validation_api \
  --/exts/omni.services.transport.server.http/port=8111 \
  --enable omni.anim.graph.bundle \
  --enable omni.anim.navigation.bundle \
  --enable isaacsim.replicator.agent.core \
  --enable omni.kit.ui_test \
  --enable isaacsim.sensors.rtx \
  --enable omni.graph.action \
  --enable omni.replicator.core \
  --enable omni.mycompany.navmesh_playground \
  > /tmp/kit_isaac.log 2>&1 < /dev/null &
```

### Different instances

Only replace `port=8111` with `8112` (instance 2).

---

## USD Composer

### path

-`kit.exe`:`<usd-composer-root>/kit/kit.exe`
-`.kit`:`<usd-composer-root>/apps/kkr_usd_composer.kit`

### Extension enable list

The profile default value is empty (`extra_ext_ids=()`). Enable only `validation_api`. `ISAAC_SIM_EXTRA_EXT_IDS` does not apply to USD Composer (`config.py::_resolve_profile_and_derived_fields` allows env override only for isaac-sim profile — crashes due to dependency resolution failure when injecting Isaac-only ext).

### ROS environment variables

**Unnecessary**. `_prepare_launch_env` explicitly removes `ROS_DISTRO` / `RMW_IMPLEMENTATION` from env. If ROS env is set in the parent shell, unset and run it.

### command (instance 1, port 8114)

PowerShell:

```powershell
Remove-Item Env:ROS_DISTRO -ErrorAction SilentlyContinue
Remove-Item Env:RMW_IMPLEMENTATION -ErrorAction SilentlyContinue

& "<usd-composer-root>/kit/kit.exe" `
  "<usd-composer-root>/apps/kkr_usd_composer.kit" `
  --ext-folder "<repo>/kkr-extensions" `
  --enable omni.mycompany.validation_api `
  --/exts/omni.services.transport.server.http/port=8114 `
  *> "$env:TEMP/omniverse_kit_mcp/kit_usdcomposer_$(Get-Date -UFormat %s).log" `
  < $null
```

bash (Git Bash):

```bash
unset ROS_DISTRO
unset RMW_IMPLEMENTATION

"<usd-composer-root>/kit/kit.exe" \
  "<usd-composer-root>/apps/kkr_usd_composer.kit" \
  --ext-folder "<repo>/kkr-extensions" \
  --enable omni.mycompany.validation_api \
  --/exts/omni.services.transport.server.http/port=8114 \
  > /tmp/kit_usdcomposer.log 2>&1 < /dev/null &
```

### Different instances

Replace only `port=8114` with `8115` (instance 2).

---

## End / Cleanup

```powershell
# Only specific instances (identified by port — no effect on other instances)
$pid = Get-CimInstance Win32_Process -Filter "Name='kit.exe'" |
       Where-Object { $_.CommandLine -like "*port=8111*" } |
       Select-Object -First 1 -ExpandProperty ProcessId
taskkill /F /PID $pid /T

# After complete shutdown, clean up even the hub orphan (executes only when all kit.exe on the host is dead)
taskkill /F /IM hub.exe /T
Remove-Item "$env:TEMP/hub-*.lock", "$env:TEMP/hub-*.config.json" -ErrorAction SilentlyContinue
```

## Verification

Check health after startup:

```powershell
curl http://127.0.0.1:8111/validation/v1/health # Isaac Sim instance 1
curl http://127.0.0.1:8114/validation/v1/health # USD Composer instance 1
```

200 response = ready. Cold boot takes 13–30 seconds after stdin DEVNULL fix, 5–10 minutes after GPU shader cache rebuild.

## Related documents

- ProcessModule SoT: `src/omniverse_kit_mcp/modules/process_module.py`
- Profile SoT: `src/omniverse_kit_mcp/types/profile.py`
- Lifecycle invariants: `docs/invariants/process-lifecycle.md`
- Multi-app invariants: `docs/invariants/multi-app.md`
- stdin deadlock runbook: `docs/runbooks/kit-stdin-deadlock.md`
- Hub orphan runbook: `docs/runbooks/hub-orphan.md`

---

## Auto-attach setting (MCP attach possible when the user starts it directly)

By permanently placing dependency / ext-folder / port in the `.kit` file, **MCP can attach** even if the user launches it in the usual way (shortcut key, `isaac-sim.bat`, `repo.bat launch`). After this setting, `--enable` / `--ext-folder` / `--/exts/...port=N` CLI arguments are not required.

### Isaac Sim — `branch/isaac-sim-standalone-6.0.0-windows-x86_64/apps/isa acsim.exp.full.kit`- Add 9 to the end of `[dependencies]` (validation_api + 8 character/sensor/replicator/omnigraph dependencies)
  - `omni.mycompany.validation_api`, `omni.anim.graph.bundle`, `omni.anim.navigati on.bundle`, `isaacsim.replicator.agent.core`, `omni.kit.ui_test`, `isaacsim.sensors.rtx`, `omni.graph.action`, `omni.replicator.core`, `omni.mycompany.navmesh_playground`
- `[settings]` to `exts."omni.services.transport.server.http".port = 8111`
- Add `"<repo>/kkr-extensions"` to `[settings.app.exts.folders] '++'` array### USD Composer — `branch/kit-app-template/source/apps/kkr_usd_composer.kit` (automatic synchronization of build artifacts)

- Add only 1 `omni.mycompany.validation_api` to the end of `[dependencies]` (USD Composer supports only common tools)
- `[settings.exts]` to `"omni.services.transport.server.http".port = 8114` (collision avoidance with Isaac Sim)
- Add `"<repo>/kkr-extensions"` to `[settings.app.exts.folders] '++'` array

### Hypothesis verification — browser ext harmless (2026-04-25 automatic verification)

The “browser ext prohibited” item in the past `docs/invariants/usd-load.md` is a hypothesis as of 2026-04-20. Check for invalidity with automatic validation and remove it from invariants:

| Verification items | Results |
|---|---|
| `self._log_capture = None` of `extension.py:36` (carb log hook not registered) | Code verification OK — deadlock key condition not met |
| In USD Composer (`content_browser` default active) warehouse MDL-heavy load | **PASS** — 17.5s, no hang |
| Isaac Sim equal load (regression verification) | **PASS** — 54.8s (simultaneous instance + cold cache environment) |

→ The real cause of deadlock is **carb log hook registration + MDL resolver combination**. Now that the log hook is disabled, it doesn't matter whether browser ext is active or not. Lessons-learned: Preserve incident records.

### Verification

After modification, the user manually relaunches the two apps:

```powershell
curl http://127.0.0.1:8111/validation/v1/health   # Isaac Sim
curl http://127.0.0.1:8114/validation/v1/health   # USD Composer
```

Both responses are 200 → `status=ready` (idempotent attach) when calling MCP `kit_app_start` (instance_id=1, profile=isaac-sim / usd-composer).

### Caution

- **ext-folder is an absolute path** (`<repo>/kkr-extensions`) → If you move the project, `.kit` is also updated.
- **Isaac Sim `.kit` can be overwritten during NVIDIA release** — Reapply the above changes after major upgrade
- **Modified only for USD Composer source `.kit`**: Confirmed that `_build/.../apps/` output is also automatically synced. `repo.bat build` No need to rerun
- ROS env (`ROS_DISTRO=humble`, etc.) cannot be set in `.kit` → Isaac Sim will always be launched as `isaac-sim.bat` (automatically set). USD Composer does not require ROS