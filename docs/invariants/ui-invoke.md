<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: extension_ui_invoke / window_ui_show Required knowledge before starting work -->
# UI Invoke — Invariants

`extension_ui_invoke` has two pitfalls: panel layout race + controller code path separation
There is. Read this file before working on UI automation.

## panel layout race (L15)

`omni.kit.ui_test.input.emulate_mouse:49` calls `pos.x / window_width`.
Immediately after `window_width = ui.Workspace.get_main_window_width()` creates the panel
(or immediately after `extension_activate(reload=True)`) Returns 0 for 1 to 10 frames →
`ZeroDivisionError`. The OS window itself is normal (3864×2100, `window_list` confirmed).

## Safety call sequence

```
extension_activate(ext_id, reload=True)
  → window_ui_show(panel_name, focus=true, settle_frames=10)  # handled automatically
  → extension_ui_invoke(widget_path)
```

## Auto-defense (currently applied)

`kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::ui_invoke`
A:
1. The window part of widget_path
   `kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::_auto_show_window`
   Automatically called with (settle_frames=10)
2.`kkr-extensions/omni.mycompany.validation_api/omni/mycompany/validation_api/services/ui_service.py::_install_ui_test_dimensions_patch`
   monkey-patch `omni.kit.ui_test.input.emulate_mouse` — workspace dimensions=0
   Replaced by OS app-window dimensions

Apply both layers — just one side can fix it, but if applied together, it can be affected by future timing changes.
robust.

## L8 invalidation (re-diagnosis result)

Previous “ext_ui_invoke binding stale → only stable user mouse direct click” diagnosis is invalid —
The actual cause is layout race. **Claude can also be clicked using the above sequence**.

## ⚠️ Direct MCP call ≠ UI button validation (L13)

Directly call MCP to verify the operation of Extension UI buttons (e.g. `character_load`,
`character_play_animation_variant`) will eliminate the bug in the controller code path.
Noise. When the user clicks a UI button:
- `_on_spawn_random` → `safe_spawn_character_sync` (self-implementation) → `_walk_then_sit`
  (controller code) — use a different path

Separate verification results:
- MCP verification PASS, UI click fail — dual-path drift of controller possible

**Extension UI button behavior must be measured by button clicking like the user**.
The MCP equivalent call only checks the possibility of operation, not verification.

## Controller dual-path drift prevention

If controller / usd_loader uses validation_api singleton:
- Directly match the method name + signature + response dict key with the service code SoT
- Example: `vr._job.get_status` (sync) vs `vr._job.status` (X)
- Follow `_ANIM_GRAPH_SUFFIX` character_service.py SoTIf there are two types of path (parent payload vs SkelRoot) like AgentRecord:
- Separated into separate fields (`prim_path` + `skel_root_path`)
- Reuse of a single field causes delete vs animation API conflict

## Related Boundaries

- L13 / L15 accident record: `kkr-extensions/docs/lessons-learned.md`
- Window / Extension domain separation: `src/omniverse_kit_mcp/modules/integration-facts.md`
- Extension reload (UI panel zombie-like layer): `docs/invariants/ext-reload.md`
- Extension implementation policy: `kkr-extensions/CLAUDE.md` (reuse of validation_api service import prohibited)