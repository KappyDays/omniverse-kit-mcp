<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Multi-app / multi-instance failure response — port conflict / USD Composer startup failure / cross infection -->
# Multi-App failure response

## Symptom 1 — `crashed` returns immediately when USD Composer instance starts

**Diagnosis**:
```bash
ls "/c/path/to/usd-composer-root/kit/kit.exe"
ls "/c/path/to/usd-composer-root/apps/kkr_usd_composer.kit"
```

Without either: broken USD Composer build.

**Recovery**:
```bash
cd /c/path/to/kit-app-template-root
./repo.bat build --release
```
Retry after build completion.

## Symptom 1b — USD Composer crashed + `Failed to resolve extension dependencies`

**Symptom**: `log_tail` to `No versions of isaacsim.replicator.agent.core that
satisfies` or similar Isaac-specific extension name.

**Cause**: `ISAAC_SIM_EXTRA_EXT_IDS` leaks in USD Composer profile. Config
Occurs when profile=isaac-sim check is missing in validator.

**Diagnosis**:
```bash
.venv/Scripts/python.exe -c "
from omniverse_kit_mcp.config import AppConfig
import os
os.environ['ISAAC_MCP_APP_PROFILE']='usd-composer'
ac = AppConfig()
print('extra_ext_ids:', ac.isaac_sim_process.extra_ext_ids)
"
```

Expected for usd-composer: `()` (empty). If Isaac-specific IDs appear →
"ISAAC_SIM_EXTRA_EXT_IDS is for Isaac-profile only" in `docs/invariants/multi-app.md`
Check the validator regression of section.

## Symptom 2 — `/robot/load` is 404 instead of 503 in USD Composer

**Cause**: validation_api extension is not loaded in USD Composer. kit lunch
The `--ext-folder` / `--enable omni.mycompany.validation_api` flag is in the command.
It is missing or the extension path is incorrect.

**Diagnosis**:
```bash
# check the CommandLine of the USD Composer instance just started
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='kit.exe'\" | Where-Object { \$_.CommandLine -like '*port=8114*' } | Select-Object -ExpandProperty CommandLine"
```

CommandLine: `--ext-folder` and `--enable omni.mycompany.validation_api`
Must have both. If not, `src/omniverse_kit_mcp/modules/process_module.py::ProcessModule` start cmd array build regression.

**Recovery**: Re-diagnosis after stop + start cycle. If the problem is still level C.

## Symptom 3 — `Address already in use` when starting Isaac instance 2

**Cause**: The previous kit is using port 8112, but `_is_process_alive` is detected.
Not possible (kit without `port=8112` in CommandLine — e.g. manual GUI launch kit).

**Diagnosis**:
```bash
netstat -ano | findstr ":8112"
```

Check PID → What is that PID:
```bash
powershell.exe -NoProfile -Command "Get-Process -Id <PID> | Select-Object Id, ProcessName, StartTime, Path"
```

**Recovery**:
- If it is an external kit that is not launched by our MCP → Manually stop or give up
- If ours is correct but identification fails → Manually run `taskkill /F /PID <PID>` and retry

## Symptom 4 — GPU OOM when Isaac + USD Composer are started simultaneously**Symptom**: Second start repeats `still_loading` + log_tail
`CUDA out of memory` / `Failed to allocate` / `Vulkan device lost`.

**Recovery**:
- Keep scene content empty (asset load prohibited)
- Only use one at a time (stop when Isaac is finished, then USD Composer)
- Long-term: Use GPU upgrade or streaming mode

## Symptom 5 — hub.exe cleanup breaks another instance

**Symptom**: Asset listing of instance 1 after stopping instance 2 (`/content/browse`)
This `ClientLibraryError` / connection refused.

**Cause**: “Skip if other kit alive” guard regression in `_cleanup_orphan_hub`.

**Diagnosis**:
```bash
Get-Process -Name hub -ErrorAction SilentlyContinue
netstat -ano | findstr :14090
```

If hub.exe disappears, regression is confirmed.

**Recovery**: Also restart Instance 1 — the hub is automatically regenerated. Code level fix is
`tests/unit/test_process_module_multi_app.py::test_hub_cleanup_skipped_when_other_kit_alive`
Verification.

## Symptom 6 — There is only one `omniverse-kit-mcp-*` entry in `~/.claude.json`

**Cause**: The setup script was run with an old version (before multi-app).

**Recovery**: From feature branch:
```bash
cmd //c "setup\\setup-omniverse-kit-mcp.bat"
```
Afterwards, verify `~/.claude.json` (refer to Phase 5.2 Step 2).

## Related Boundaries

- Invariants: `docs/invariants/multi-app.md`
-Code SoT:
  -`src/omniverse_kit_mcp/modules/process_module.py`
  -`kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
-Live smoke:
  -`scripts/verify_multi_instance.py`
  -`scripts/verify_multi_app.py`
- Existing faults: `docs/runbooks/kit-stdin-deadlock.md`, `cold-boot-timeout.md`,
  `hub-orphan.md`, `env-sub-config.md`