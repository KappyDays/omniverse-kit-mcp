<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: OmniHub orphan port 14090 residual diagnosis / recovery -->
# OmniHub orphan port 14090 (manual recovery)

When the next kit is started, the `hub.exe` daemon spawned by `omni.client` remains orphaned.
Enter when `"Hub failed to launch: child exited with exit code: 1"` occurs.

## Symptoms

- Repeat `"Hub failed to launch: child exited with exit
  code: 1"` in startup_log of `kit_app_start`
- The result is `netstat -ano | findstr :14090` LISTENING, but the new connection is `10061
  refused`
- `Get-Process -Name hub -ErrorAction SilentlyContinue` returns row even after kit.exe is terminated
- `%TEMP%/hub-*.lock` / `hub-*.config.json` files remain

## Root cause

`omni.client` spawns `hub.exe` as `--mode=shared` — separated from the kit process tree
daemon. Even if the kit is terminated, port 14090 orphan remains. When time passes, accept loop broken →
New connection refuse → OmniHub init of the next kit fails.

## Automatic recovery (currently applied)

`src/omniverse_kit_mcp/modules/process_module.py::_cleanup_orphan_hub`
Automatically performs on both `stop` / `start`:
-`taskkill /F /IM hub.exe /T`
- Remove `%TEMP%/hub-*.lock` / `hub-*.config.json` files

## Manual recovery (in case of automatic fail)

1. **Force termination of Hub process**:
   ```bash
   cmd //c "taskkill /F /IM hub.exe /T"
   ```
   (PowerShell `Stop-Process` is Access Denied)

2. **Clean up Lock / config file**:
   ```bash
   rm -f /c/Users/$USER/AppData/Local/Temp/hub-*.lock /c/Users/$USER/AppData/Local/Temp/hub-*.config.json
   ```

3. **Restart the kit**:
   ```bash
   .venv/Scripts/python.exe scripts/run_process_module_standalone.py start
   ```

## Diagnostic tools

- `Get-Process -Name hub -ErrorAction SilentlyContinue` (PowerShell) — confirmed alive
- `netstat -ano | findstr :14090` — LISTENING OK
- `ls /c/Users/$USER/AppData/Local/Temp/hub-*` — Check lock/config file

## Related Boundaries

- Auto-recovery code: `src/omniverse_kit_mcp/modules/process_module.py::_cleanup_orphan_hub`
- ProcessModule hang recovery 4 types of pitfalls #4: `src/omniverse_kit_mcp/modules/process-ops.md`
- Process life cycle invariants: `docs/invariants/process-lifecycle.md`
- Cold boot timeout branch: `docs/runbooks/cold-boot-timeout.md`