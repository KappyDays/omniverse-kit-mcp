<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Common basic knowledge of Kit Extension creation / modification / debugging -->

#ExtensionBasics

Common information you need to know when creating a new Kit Extension or modifying an existing one.

## IExt inheritance 3 elements (required)

1. Declare `config/extension.toml` to `[[python.module]]`
2. `omni/<vendor>/<name>/__init__.py` to `IExt` subclass **import** — if not present, Kit will not call `on_startup`
3. **Directly** inherit `omni.ext.IExt` (no dynamic variables or metaclass tricks)

## Reflection of code modifications

| Situation | Reflection method |
|------|----------|
| Local development (non-streaming) | **Hot-reload** — Automatically reloads just by saving the file. If necessary, force reload by toggling inactive → active in Extension Manager. `__pycache__` is automatically processed |
| Streaming / Remote Environment | Recommended to delete `__pycache__` + complete restart of Kit (empirically safe) |
| Change `[dependencies]` in `extension.toml` | **Kit complete restart required** — Dependency graph not updated with hot-reload |

## Logging

- Only `carb.log_info / log_warn / log_error` is visible in Kit Console
- Python standard `logging` and `print` are not recorded in the Kit Console (beware of confusion when debugging)

## Extension API call priority

1. `omni.kit.commands.execute(...)` — USD operation standard, **undo/redo automatic support**
2. `omni.usd.get_context().get_stage()` — When direct access to the stage is required
3. `omni.timeline.get_timeline_interface()` — Simulation Control
4. `pxr.*` (USDGeom, Gf, Sdf, USDSkel, etc.) — Low-level USD manipulation

The prim created with `omni.kit.commands.CreatePrimWithDefaultXformCommand` already includes `xformOp` → Use `prim.GetAttribute("xformOp:translate").Set(...)` instead of `AddTranslateOp()`.

## omni.ui constraints (must read before UI planning)

- **Actual measurement of `omni.ui` CJK rendering constraints even in Isaac Sim 6.0 / Kit 110 series**, UI strings are written focusing on ASCII / Latin
- **Do not include Korean/CJK characters in UI** — Broken by mojibake or missing glyph. Label, tooltip, status all in English
- `omni.ui` cannot verify widget behavior in the pytest environment (stub level) — Actual UI QA uses **live Kit + QA_CHECKLIST manual** method
- Viewport overlay UI places a single root `ui.ZStack` under `viewport_window.get_frame()` and places multiple `ui.Placer` within it. Details: "Viewport-owned overlay UI" of `kit-sdk-pitfalls.md`
- Image tile click UI is prohibited for `with ui.Button` / `with button`. `ui.ZStack` + image + transparent mouse-event rectangle pattern used. Details: "`omni.ui.Button` is not a context manager" in `kit-sdk-pitfalls.md`
- The Viewport overlay button is made with the actual `ui.Button(opaque_for_mouse_events=True)` within `ui.ZStack(..., content_clipping=True)`. `Rectangle + Label + transparent Rectangle` composite buttons are at risk of losing Prim selection penetration/hover. Details: "Viewport overlay button of `kit-sdk-pitfalls.md` is `content_clipping=True` + `ui.Button`"
- Viewport point hover/pick is prohibited from relying solely on `ViewportAPI.request_query`. In fixed camera mode, camera-ray fallback is enabled. Details: "Viewport point picking must not depend solely on `request_query`" of `kit-sdk-pitfalls.md`
- Items where the user changes the color/transparency value in the Extension UI are always set to `omni.ui.ColorWidget(r, g, b, a)`. The combination of hex `StringField` + alpha `IntDrag` is prohibited unless it is a temporary debug UI. Details: "Color change UI uses `ColorWidget`" of `kit-sdk-pitfalls.md`

## Kit Python environment (based on Isaac Sim 6.0 / Kit 110 series)

- Isaac Sim 6.0 bundled Kit Python is Python 3.12 series
- FastAPI / Pydantic is used only in `validation_api` REST boundary. The exact package version can be checked using the local extension catalog or the `pip show` result of Kit install.
- `omni.services.core` is a FastAPI-based router registration route. The version may vary depending on Kit install, so do not hard-code it.

## New independent Extension skeleton (copy-paste)

> ⚠️ In accordance with the **"new extension is an independent structure"** policy of the root `CLAUDE.md`, the new extension does not depend on `validation_api` but uses the Kit SDK directly.

```
kkr-extensions/omni.mycompany.<my_ext>/
├── config/
│   └── extension.toml
└── omni/mycompany/<my_ext>/
    ├── __init__.py
    └── extension.py
```

**`config/extension.toml`**:
```toml
[package]
version="0.1.0"
title = "My Extension"
description = "Short description of what this does."
category = "Tools" # or Tutorial / Validation / ...
keywords = ["..."]

[dependencies]
"omni.kit.uiapp" = {}
"omni.ui" = {}
# ⚠️ New extensions are prohibited from relying on validation_api
# "omni.mycompany.validation_api" = {} ← Do not use[[python.module]]
name = "omni.mycompany.<my_ext>"
```

**`__init__.py`**:
```python
from .extension import MyExtension # noqa: F401 — Kit navigation to this IExt subclass
```

**`extension.py`**:
```python
from __future__ import annotations

import carb
import omni.ext


_SOURCE = "omni.mycompany.<my_ext>"


class MyExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        # TODO: Implement UI window/scene behavior

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        # TODO: Clean up the UI / release the listener
```

If you need to load the MDL-heavy S3 asset directly, copy the defense code of `docs/usd-load-deadlock-recipe.md` and use it.

## Extension activation path

| path | When to use |
|------|----------|
| `kit.exe --enable <ext_id>` | Process level (one-time execution) |
| `ISAAC_SIM_EXTRA_EXT_IDS` JSON array of `.env` | Automatically starts the MCP server with `setup-omniverse-kit-mcp.bat` (recommended when distributing student PCs) |
| Extension Manager UI Toggle | Manual during local development |

To automatically activate for student/new PC, adopt **`.env`** method + reflected in `setup/setup_omniverse_kit_mcp.ps1`.