<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Kit Extension Development Root — Navigation Hub -->

# kkr-extensions — Kit Extension Development

A root containing Kit Extensions that run inside the Isaac Sim GUI (`kit.exe`). This file contains a **topic document (`docs/`) and a nav hub** that guides you to each Extension folder.

## ⚠️ Must read before work (invariants)

- Modify Extension `.py` / reload (fswatcher + zombie cleanup): [`../docs/invariants/ext-reload.md`](../docs/invariants/ext-reload.md)
- USD load 4 condition (MDL deadlock defense): [`../docs/invariants/usd-load.md`](../docs/invariants/usd-load.md)
- UI automation sequence (`extension_ui_invoke`): [`../docs/invariants/ui-invoke.md`](../docs/invariants/ui-invoke.md)

## Extension list

| directory | Role |
|---------|------|
| `omni.mycompany.validation_api/` | **REST bridge Extension** — FastAPI router (`localhost:8111/validation/v1/**`) that allows the MCP server to remotely operate the Kit SDK. All MCP tools in this project depend on this REST |
| `omni.mycompany.navmesh_playground/` | Phase J Extension — Place People/Robot on `full_warehouse.usd` as random walkable and move along NavMesh path. People = BehaviorAgent/IRA Walk→Sit FSM, Robot = DifferentialController based physics wheel. **Standalone** (no validation_api dependency). Copy deadlock-recipe. |
| `omni.mycompany.usd_mouse_interact/` | Composer Extension v0.2 — FPS fly-camera + whitelist prim picker + info overlay (timeline-driven). OS-level input bypass verification using the manual inject button (yaw / WASD / Force pick) on the dev panel. **Independent structure** — Separate docs / tests / helper scripts in `workshop/` |
| `omni.mycompany.usd_mouse_interact_demo/` | Composer input/streaming demo working copy — button overlay + multi-mode mouse interaction experimental use |

## Core policies

### 🛑 Extension is **independent structure** (confirmed on 2026-04-22)

- Kit SDK (`omni.kit.commands` / `omni.usd` / `pxr.*`, etc.) **Direct call**
- Depends on `validation_api` **Prohibited**
- When necessary to load S3 MDL-heavy assets (office / warehouse / nova_carter / 6.0 character skins, etc.), **copy** the defense code of `docs/usd-load-deadlock-recipe.md` (not import)
- Do not reuse `validation_api` internal service import — Extension calls Kit SDK directly

### Common rules (docs/extension-basics.md for details)

- `IExt` subclass must be imported into `__init__.py` (if not present, `on_startup` will not be called)
- Logging is only for `carb.log_warn / log_info / log_error` — Python `logging` / `print` is not visible in the Kit Console.
- Reflection of code modifications: **hot-reload for local development** / Kit complete restart for `[dependencies]` changes
- **UI strings are English only (hard rule — no exceptions)** — `omni.ui` CJK rendering restrictions are also observed in Isaac Sim 6.0 / Kit 110 series. DevPanel label / Button text / hint label / Window title / status text all in English author
- Viewport overlay UI uses a single root `ui.ZStack` under `viewport_window.get_frame()` — Details: `docs/kit-sdk-pitfalls.md` "Viewport-owned overlay UI"
- User-facing color/transparency setting UI always uses `omni.ui.ColorWidget(r, g, b, a)` — Details: `docs/kit-sdk-pitfalls.md` "Color changing UI uses `ColorWidget`"
- When a new viewport/UI pitfall is found, the `docs/kit-sdk-pitfalls.md` body + `docs/extension-basics.md` checklist pointer are updated together.

## Topic document (`docs/`)

| document | When to read |
|------|----------|
| [`docs/extension-basics.md`](docs/extension-basics.md) | **When starting a new extension** — IExt / toml / hot-reload / independent skeleton copy-paste template |
| [`docs/kit-sdk-pitfalls.md`](docs/kit-sdk-pitfalls.md) | When you get stuck while using a specific Kit API (USD load / articulation / character / NavMesh / sensor / viewport / UI automation), search for ground truth pitfalls by domain |
| [`docs/usd-load-deadlock-recipe.md`](docs/usd-load-deadlock-recipe.md) | Defense code to copy when loading S3 MDL-heavy asset from independent extension (log_capture disable + run_coroutine + CreatePayloadCommand instanceable 3-element) |
| [`docs/lessons-learned.md`](docs/lessons-learned.md) | Cumulative log of past implementation mistakes + lessons learned. Avoid the same mistakes by scanning before starting a new task |

## Individual documents for each extension

The common content is in `docs/`, and only the unique contents of each Extension are in the Extension folder:

- Extension-specific QA documents are placed in the relevant Extension folder.

## Related Boundaries

- How the MCP server calls `validation_api`: [`../src/omniverse_kit_mcp/CLAUDE.md`](../src/omniverse_kit_mcp/CLAUDE.md) + [`../src/omniverse_kit_mcp/modules/CLAUDE.md`](../src/omniverse_kit_mcp/modules/CLAUDE.md)
- `validation_api` REST endpoint full list SoT: [`omni.mycompany.validation_api/omni/mycompany/validation_api/rest_router.py`](omni.mycompany.validation_api/omni/mycompany/validation_api/rest_router.py) (code is SoT)
- Extension activation installation procedure: [`../setup/CLAUDE.md`](../setup/CLAUDE.md)
- Automatically manipulate Extension UI in Scenario YAML: [`../scenarios/CLAUDE.md`](../scenarios/CLAUDE.md)