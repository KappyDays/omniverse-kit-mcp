<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Required knowledge before starting code reflection work after modifying Extension .py -->
#ExtensionReload—Invariants

No matter what reload path is used after modifying Extension `.py`, `sys.modules` cleanup is not guaranteed.
When modifying the `kkr-extensions/` code, read this file.

## Key conclusions (updated 2026-05-26 — `extension_reload` newly created)

- **Reflect modifications to Demo/User Extension `.py`**: Use `extension_reload(ext_id)` MCP tool
(No need to restart Kit). This tool disable → **Purge ext_id tree in `sys.modules`** →
Perform `importlib.invalidate_caches()` → enable to make sure to remove the stale module/singleton.
- **If you still need to restart the Kit** (only two):
  1. `omni.mycompany.validation_api` Changing **your own** code — disabling the REST server
Self-reload is prohibited because `extension_reload` response is not possible (HTTP 400). Use `kit_app_restart`.
  2. Change extension.toml `[dependencies]` — Dependency graph resolving is not a hot path.
- The past conclusion ("restart is required for all `.py` modifications") was based on the time when there was no `sys.modules` purge.
Resolved with `extension_reload`. fswatcher auto reload still says `_reload_enabled=False`
Untrustworthy — call `extension_reload` explicitly. MCP `extension_activate(reload=True)` degrees
Toggle only, do not clean up sys.modules (purge is only for `extension_reload`).
- **Note module-level singleton**: Like `_window = WindowService()` / `_router = APIRouter()`
The import-time singleton is regenerated when the module is reimported after purge and is reload-safe, but `on_shutdown`
Without cleanup, zombies remain (see zombie cleanup pattern below).

## Verification pattern (check whether reload is successful)

Add a hard-coded marker to your code (e.g. add a temporary field to the response dict) → call the tool → marker
Make sure you see:
- Visible → reload success
- Not visible → reload failed → Kit process restart required

## ui.Window zombie cleanup pattern (L16)

When fswatcher automatically disable→enable, only `self._window.destroy()` of `on_shutdown`
`ui.Workspace` is not immediately unregistered from the registry (processed at the next update tick) →
Next, create a new `ui.Window` with the same name as `on_shutdown` → enter the same name in the registry
2 → walker returns stale OLD widget tree → widget path of MCP UI automation
The call is not fired.

Standard cleanup pattern (`on_shutdown` recommended for all new/existing extensions):

```python
# extension.py on_shutdown
if self._window is not None:
    self._window.visible = False  # deregister hint for Workspace
    self._window.destroy()
    self._window = None

# ui_panel.py build() start
existing = ui.Workspace.get_window("<name>")
if existing is not None:
    existing.visible = False
    existing.destroy()
self._window = ui.Window("<name>", ...)
```Both layers must be applied to be effective — if destroy is deferred, build() sweep is backup.
If you need a completely zero zombie, yield `next_update_async()` twice in build() and then sweep —
Currently, there is only 1 invisible orphan left, but walker is the first visible rule, so only normal NEW is picked.
So there is no user impact.

## Symptoms (if zombie remains)

- kit log: `[Warning] [omni.ui_query.query] found 2 windows named "<name>". Using first
  visible window found`
- `extension_get_ui_tree` reports two matches with `matched_windows: ["<name>", "<name>"]`
- Walker walks OLD (visible) → stale widget tree → calls MCP UI automation
callback unspoken
- If accumulated, memory leaks (until Kit restart)

## `branch/kit-app-template` source ↔ \_build hardlink

`branch/kit-app-template/source/apps/<app>.kit` and
`branch/kit-app-template/_build/windows-x86_64/release/apps/<app>.kit` is
hardlink created by premake (same inode). Even if you just edit the source, _build
It renews automatically, but after editing one side, if you try to edit another side in the same session,
**`Edit` tool fails with "File has been modified since read"** —
This is because the inodes are the same, so metadata is updated simultaneously.

Recommended pattern:
- **source/apps/ only Edit** — \_build side automatically syncs
- Verification: Inode comparison of `stat <source>.kit <build>.kit` (hardlink if identical)
- If you feel you need to modify the same .kit on both sides, check first whether it is a hardlink or not.

(This hardlink pattern is `branch/usd-composer-webrtc-streaming/kit-app-template/`
the same applies to)

## Related Boundaries

- L9 / L16 Incident Log: `kkr-extensions/docs/lessons-learned.md`
- Extension general rules (IExt / hot-reload / Korean UI prohibited): `kkr-extensions/docs/extension-basics.md`
- Window/UI automation sequence (panel race + dual-path drift): `docs/invariants/ui-invoke.md`
- MCP server import cache (separate process): `src/omniverse_kit_mcp/CLAUDE.md`
