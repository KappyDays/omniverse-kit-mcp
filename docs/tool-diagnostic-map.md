<!-- Parent: ../CLAUDE.md -->
<!-- Scope: When an error/failure occurs, verify the hypothesis with a read-only MCP tool before modifying the code — Debugging first read -->
# Tool Diagnostic Map

When an error/unexpected operation occurs **Modify → Before the trial cycle** Read this document.
If the code modification + attempt with the same hypothesis fails twice → Hypothesis reexamination is forced (repeated attempts are prohibited).

## Diagnostic workflow (5 second cycle vs 10 minute cycle)

1. **Grep error message**: project source + Kit source (`C:/workspace/isaac-sim-standalone-*/exts/`) — Identify line of occurrence, narrow down hypothesis
2. **Call MCP read-only diagnostic tool** (~5 seconds each) — Verify hypothesis using the table below
3. **When environmental dependency is suspected**: `extension_search/activate` (lazy install) + `content_browse` (URL verification) + filesystem directly
4. Attempt to modify the code **only after confirming the hypothesis**. Same hypothesis fails twice = hypothesis discarded

## Question → MCP tool reverse index

| question | 1st MCP tool | Response field / validation method |
|------|---------------|---------------------|
| Is this prim this articulation? | `robot_load(usd_url, prim_path)` | `has_articulation` |
| Robot load failed? | `simulation_get_status` → `stage_capture_snapshot` → `official_asset_search` / `asset_search` → `robot_load` → `extension_capture_logs` | For `ROBOT_LOAD_ERROR` or `CAPABILITY_NOT_SUPPORTED`, inspect `diagnostics.reason=robot_load_error`, `diagnostics.usd_url`, `diagnostics.prim_path`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` |
| Is this USD URL real? | `content_browse(parent_dir)` | Items in `entries[]` (S3 catalog) |
| Ext registration? | `extension_search(keyword)` | result count > 0 |
| Enable Ext? | `extension_get_info(ext_id)` | `info.enabled` / `info.path` |
| Ext lazy install + activation? | `extension_activate(ext_id)` | `was_enabled` / `enabled` |
| Widget click effect? | `extension_ui_invoke` post-state + `extension_get_ui_tree` label change |
| Prim being? | `stage_assert_prim_exists(prim_path)` | `passed` |
| Prim attribute value? | `stage_assert_property(prim_path, property_name)` (expected omitted) | `actual.value` |
| Stage full prim? | `stage_capture_snapshot` → `data.prims` dict (larger response — Bash + jq/python recommended) |
| Timeline state? | `simulation_get_status` | `is_playing` / `current_time` |
| Window exists? | `window_list` | `windows[].class_name=GLFW30` |
| Window UI tree? | `extension_get_ui_tree(window=)` | `widgets[]` (USD Composer does not have `omni.kit.ui_test` → 0 widgets + walk_error) |
| Visual status? | `viewport_capture` / `window_capture` + `Read` tool | PNG (R3) |
| Viewport framing failed? | `stage_capture_snapshot` → `simulation_get_status` → `viewport_frame_prims` → `extension_capture_logs` | For `VIEWPORT_FRAME_PRIMS_ERROR`, inspect `diagnostics.reason=viewport_frame_prims_error`, requested `diagnostics.prim_paths`, `diagnostics.upstream_error_code`, and `diagnostics.fallback_tool_order` before changing camera code |
| Kit menu item? | `window_menu_list` / `window_menu_trigger` | `items[]` |
| Script Editor localhost REST timeout? | `simulation_get_status` from outside Script Editor | Same Kit process blocking on itself; do not call Kit REST synchronously from Script Editor |
| MDL deadlock? | `simulation_get_status` 92s timeout | → `runbooks/kit-stdin-deadlock.md` |

## Extension internal progress stamping pattern

Inside ext in an environment where `extension_capture_logs` is no-op (`invariants/usd-load.md`)
For external polling of progress, USD attribute stamp:

```python
# extension code (at each progress step)
from pxr import Sdf, USDGeom
prim = USDGeom.Xform.Define(stage, Sdf.Path("/World/MyExtStatus")).GetPrim()
prim.CreateAttribute("stage", Sdf.ValueTypeNames.String).Set("step_5_done")
prim.CreateAttribute("last_error", Sdf.ValueTypeNames.String).Set(str(exc))
```

```python
# MCP polling (external)
stage_assert_property(prim_path="/World/MyExtStatus", property_name="stage")
# response.actual.value to read the current step
```

## Self-test pattern (environment without UI automation)

USD Composer, etc. `omni.kit.ui_test` absent → `extension_ui_invoke` widget click not possible
(Externalized as `extension_get_ui_tree` widgets=0 + walk_error).

Alternative: self-test coroutine schedule, results in extension `on_startup`
stamp with `/World/<Ext>SelfTestResult` prim attribute → MCP `stage_assert_property`
read. Immediately after stamping to avoid side-effects (e.g. restore after highlight) and verification race.
Separate verification state (reset to highlighted_path = None, etc.).

## Comparison of hypothesis testing costs

| Action | time |
|------|------|
| 1 MCP read-only call | ~5 s |
| Grep (project/kit source) | ~5 s |
| Standalone python verification (`scripts/run_*_standalone.py`) | ~10 s |
| Kit restart + build + play + start cycle | ~10 min |

→ One cycle saved with one read-only verification before code modification. Accumulated 1 hour vs 25 s for 4-5 attempts.

## Related Boundaries

- Full MCP tool signature: `tool-catalog.md` (auto-generated, signature-oriented)
- Process lifecycle / hang: `invariants/process-lifecycle.md` + `runbooks/cold-boot-timeout.md`
- USD load trap (S3 URL / MDL deadlock): `invariants/usd-load.md`
- Ext reload (sys.modules cleanup limit): `invariants/ext-reload.md`
- Multi-app port / profile: `invariants/multi-app.md`
- Kit SDK domain trap: `../kkr-extensions/docs/kit-sdk-pitfalls.md`
