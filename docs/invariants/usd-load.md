<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: stage_load_usd / stage_open / robot_load / character_load Required knowledge before starting work -->
# USD Load — Invariants

This file before calling `stage_load_usd` / `stage_open` / `robot_load` / `character_load`
Read. If any condition is broken, Kit to MDL resolver + carb log callback deadlock
Event loop stop → 92 s timeout for all MCP tools (actual baseline after resolution of hang on 2026-04-20).

## 4 Condition (no changes — if broken, hang recurs)

### 1. S3 URL required

Allowed prefix:
-`https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/...`
-`https://omniverse-content-staging.s3.us-west-2.amazonaws.com/Assets/simready_content/...`
-`https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/{ArchVis,DigitalTwin,Vegetation}/...`

`file:///` Local cache **prohibited** (stale cache causes silent miss when re-querying S3).

Catalog SoT: `docs/assets/isaac/asset_inventory.md` entry point + `docs/assets/isaac/assets/*.md`.

**Defense recipe when developing extension**: When loading S3 MDL-heavy asset (office / warehouse / nova_carter / 6.0 character skins) from extension, not MCP server, **copy** and use the log_capture disable + `run_coroutine` + `CreatePayloadCommand` 3-element pattern. The general static payload is `instanceable=True`; The robot/articulation payload follows the exceptions below. Details: `kkr-extensions/docs/usd-load-deadlock-recipe.md`.

**Robot/articulation exception (Isaac Sim 6.0 live verification)**: For `robot_load`, use `CreatePayloadCommand`, but it must be `instanceable=False`. Since the articulation runtime performs child prim traversal/write, instanceable payload may break subsequent control. Additionally, `robot_load` must have no pending/running async jobs before stage mutation, and if the timeline is playing, it must be stopped first. When Franka load is attempted during NovaCarter `navigate_path` job, Kit/PhysX crash occurs.

### 2. `log_capture.start()` Always prohibited from calling

- Maintain `self._log_capture = None` in Extension `on_startup`
- Verified symptom that MDL loader loop caused carb thread and GIL contention
- Right before live verification, open the request-scoped capture window with `extension_clear_logs`,
  Only patterns that close immediately after failure with `extension_capture_logs(..., stop_after_capture=True)` are allowed.

### 3. Zombie recovery only works with `cmd //c "taskkill /F /IM kit.exe /T"`

- `powershell Stop-Process` is confirmed to be Access Denied
- Convenience script: `scripts/kill_kit_zombie.sh`

## `stage_open` vs `stage_load_usd`

- `stage_open(url)` — Entire root stage replacement (scene conversion)
- `stage_load_usd(url, prim_path)` — `/World/<name>` Payload added to existing stage
  (multi-asset composition)
- **play-guard (2026-05-26)**: `stage_new`/`stage_open`/`stage_load_usd` is MCP
  If `is_playing` is entered at the `SimulationModule` entry, it automatically precedes `simulation_stop` (stage during play)
  Replacement → prevent 92s hang). The caller does not need to call stop separately.

## Root cause (for relapse diagnosis)

With the carb log callback of `LogCaptureService` registered, historical Kit 107
/ Isaac Sim 5.1 MDL resolver opens Materials.usd of S3 asset
`"Disabling base URL to resolve MDL identifier
'OmniPBR.mdl'"` repetition → Python callback GIL contention in carb thread → Kit main event
loop deadlock → all MCP tools 92 s timeout.

## Solved 3 elements (baseline — hang recurrence when changed)

1. Extension `on_startup` to `self._log_capture = None`
   (NOT `get_log_capture_service().start()`). If you need console log evidence
   Capture briefly only with the request-scoped MCP tool.
2.`kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/stage_service.py::load_usd`
   is `omni.kit.async_engine.run_coroutine(_main_loop_impl())`+
   `asyncio.wrap_future(future)` — Since FastAPI event loop ≠ Kit main event loop
   Explicit schedule in kit main loop
3. `omni.kit.commands.execute("CreatePayloadCommand", ...)` —
   Equivalent path to GUI drag&drop scene_drop_delegate. `stage_load_usd` /
   static asset payload is `instanceable=True`; `robot_load` is runtime
   `instanceable=False` for articulation write.

Code recipe (defense code to copy when loading S3 MDL-heavy asset from independent extension):
`kkr-extensions/docs/usd-load-deadlock-recipe.md`

## Actual measurement (after hang resolution on 2026-04-20)

- Simple_Warehouse 2.4 s
-NovaCarter 3.1s
- F_Business_02 character skin 2.6 s
-SimReady cold 10~57 s
- Multi-asset composition OK

## Diagnosis order in case of recurrence

1. Kit log `%USERPROFILE%\.nvidia-omniverse\logs\Kit\Isaac-Sim Full\6.0\kit_*.log`
   After the last entry repeats `"Disabling base URL to resolve MDL identifier"`, silent =
   deadlock confirmed
2. `simulation_get_status` blocks 92 s timeout → Kit main loop
3. `cmd //c "taskkill /F /IM kit.exe /T"` (PowerShell `Stop-Process` is Access Denied)
4. To `.venv/Scripts/python.exe scripts/run_process_module_standalone.py start`
   fresh restart

## Do not (trigger relapse)

- `log_capture.start()` always reactivated
- `file:///` local cache
- **skip/fallback/placeholder** when S3 load fails — all prohibited. Be sure to succeed after analyzing the root cause

> The past “browser ext prohibited” item (diagnosed on 2026-04-20) is invalidated by automatic verification on 2026-04-25. With USD Composer `.kit` default, warehouse MDL-heavy load succeeded in 17.5s with `omni.kit.window.content_browser` active. The cause of deadlock is carb log hook registration (currently disabled in `extension.py:36`), and the browser ext itself is harmless. Preserve lessons-learned.

## Related Boundaries- Low-level code location (Stage / USD load protocol): `src/omniverse_kit_mcp/modules/integration-facts.md`
- Asset URL catalog entry point: `docs/assets/isaac/asset_inventory.md`
- Independent Extension Defense Recipe: `kkr-extensions/docs/usd-load-deadlock-recipe.md`
- LogCapture Inactive Decision Incident: `kkr-extensions/docs/lessons-learned.md`