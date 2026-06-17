<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Immutable rules of multi-app / multi-instance architecture — Must read when adding a new profile -->
# Multi-App × Multi-Instance — Invariants

This MCP server simultaneously controls **multiple Kit-based app instances** on one host.
Currently supported: **isaac-sim**, **usd-composer**. Read this document before adding apps/editing profile.

## Port allocation (contiguous per-profile window)

| Profile | Instance 1 | Instance 2 |
|---------|-----------|-----------|
| `isaac-sim` | 8111 | 8112 |
| `usd-composer` | 8114 | 8115 |

Derived formula: `port = profile.default_ext_port + (instance_id - 1)`.

Port conflict prevention rules:
- When adding a new profile, set `default_ext_port` to the range and 3-port of the existing profile.
Allocation at intervals (kaolin → 8017, etc.)
- Instance Limit 2 — `instance_id` Field in `src/omniverse_kit_mcp/config.py`
In the `ge=1, le=2` guard. Permanent limit (no extension procedure) by user decision (2026-05-23)

## Process Identification (name scope prohibited)

**Prohibited**: `taskkill /IM kit.exe`, `Get-Process -Name kit` — all of host
instance matched.

**Required**: PID based (`taskkill /F /PID <self._process.pid> /T`) or
CommandLine filter (`ProcessModule._resolve_instance_pid` is identified by
both `port=<N>` and the expected profile `.kit` file name). `port=<N>` is
`--/exts/...port=N` at kit launch; the `.kit` match prevents a USD Composer
workspace from attaching to an Isaac Sim process that accidentally owns a
Composer port, and vice versa.

## Hub.exe shared daemon

`hub.exe` (port 14090) is shared by all kit.exe. `_cleanup_orphan_hub` is
**Perform cleanup only when there are 0 kit.exes on the host**. If you don't skip the conditional
When you stop an instance, the asset resolution of other instances is interrupted.

## Extension REST Bridge Neutrality

`omni.mycompany.validation_api` is **app-agnostic**. Isaac / USD Composer
Loaded from both. Isaac-specific route activates Kit ext required for request-time
Probe to see if it exists, and if not, returns HTTP 503.

Guard function is `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
`require_*_stack()` — When adding a new Isaac-specific route, register the guard here as well.

## ISAAC_SIM_EXTRA_EXT_IDS is for Isaac-profile only

`ISAAC_SIM_EXTRA_EXT_IDS` of `.env` is an Isaac-specific extension id only.
Includes (isaacsim.sensors.experimental.rtx/isaacsim.sensors.experimental.physics/
isaacsim.ros2.bridge / isaacsim.replicator.agent.core).
When injected into USD Composer, “Failed to resolve extension” appears when booting the kit.
crash with "dependencies". Config validator (`src/omniverse_kit_mcp/config.py::IsaacSimProcessConfig`)
Apply env value only to profile=isaac-sim, others are curated by profile
Use extra_ext_ids.

## Procedure for adding a new App Profile (kaolin, etc.)

1. Add `KitAppProfile` to `src/omniverse_kit_mcp/types/profile.py` + `_PROFILES`
register dict
2. `supported_module_groups` includes only groups that the app actually supports.
For groups that are not supported, the guard of `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py` on the extension side is automatically activated.
503 handling → No additional code changes required
3. Add entry to `$Profiles` array of `setup/setup_omniverse_kit_mcp.ps1`
4. Port / supported by profile in `tests/unit/test_config_multi_app.py`
Add group/kit_exe verification test
5. Extend `scripts/verify_multi_app.py` (optional — new profile smoke)

## MCP Tool Surface Invariance

Even if the profile increases, the `EXPECTED_MODULE_TOOLS` frozenset does not change.
- Common tools are registered regardless of profile
- For capabilities that are not supported, the tool is set to `CAPABILITY_NOT_SUPPORTED` at runtime.
Return error_code (graceful in UI)
- Tool name-based profile branching (e.g. `isaacsim_robot_load`) is prohibited —
Frozenset management burden + client needs to know different tool names for each profile

## `.kit` ext folder absolute path — required update when repo / directory rename

External Kit app build of `branch/` (`isaac-sim-standalone-*.bat`,
`branch/kit-app-template/_build/.../release/*.kit.bat`,
`branch/usd-composer-webrtc-streaming/.../release/*.kit.bat`) is a self-layout
To absorb the external `omniverse-kit-mcp/kkr-extensions/` into the ext folder
Add **absolute path** to the `[settings.app.exts.folders]` `'++'` list in the `.kit` file.
Hard code it. (Relative paths have different depths for each .kit location, so layout-fragile).

When working directory rename / repo move, if this absolute path becomes stale, `omni.mycompany.*`
The extension is not visible in the ext folder and the dependency solver fails immediately —
`.bat` runs directly and ends in 3 seconds. Diagnosis/Repair: `docs/runbooks/kit-dep-solver-fail.md`.

### Detection procedure (required immediately after rename/move)

```bash
# 1) grep .kit files across the current tree for ext folder absolute paths
grep -rn '"<workspace>/' --include='*.kit' <workspace>/

# 2) check that every matched path exists and is non-empty
#    (after a rename, the old path often remains as an empty folder)
```

### Target file list (as of 2026-05-04)

-`branch/isaac-sim-standalone-6.0.0-windows-x86_64/apps/isaacsim.exp.full.kit`
-`branch/kit-app-template/source/apps/kkr_usd_composer.kit`
(`_build/windows-x86_64/release/apps/kkr_usd_composer.kit` and hardlink — both updates just by modifying the source)
-`branch/usd-composer-webrtc-streaming/kit-app-template/source/apps/kkr_usd_composer.kit`
(same hardlink pattern)

In all three files, `[settings.app.exts.folders]` and `'++'` are the last items in the list.
It must be unified as `"<repo>/kkr-extensions"`.

## Related Boundaries- Code SoT: `src/omniverse_kit_mcp/types/profile.py` (KitAppProfile + _PROFILES)
- ProcessModule launch: `src/omniverse_kit_mcp/modules/process_module.py::start`
- Extension guards: `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/_app_features.py`
- Setup registration: `setup/setup_omniverse_kit_mcp.ps1`
- Dependency solver fail diagnosis: `docs/runbooks/kit-dep-solver-fail.md`
- Fault response: `docs/runbooks/multi-app.md`
