# Stage Annotator

Prim-anchored sticky-note review system for Isaac Sim 5.1 / USD
Composer 2026.x. Drop threaded review notes on any prim, track them
through a status workflow, and visualize them in-scene with colour-coded
3D pin spheres.

## What it does

A floating panel (`Stage Annotator` window) on the left side hosts the
note board:

* List of all notes with **filter combos** (status, author) and a free-
  text search field
* **Stats line** showing per-status counts
* Each note card surfaces title, prim path, author, relative timestamp,
  reply count, and quick **Open / Go** buttons
* Selected note card expands a **detail editor** with editable title,
  body, status combo (Open → In Progress → Resolved → Won't Fix),
  threaded **replies** with delete buttons, and a **Delete Note**
  button (last in the layout to make accidental clicks unlikely)

In the 3D viewport, every note is mirrored as a small colour-coded
sphere under `/Annotations/<note_id>/Pin`:

| Status      | Pin colour   |
|-------------|--------------|
| Open        | Red          |
| In Progress | Amber        |
| Resolved    | Green        |
| Won't Fix   | Grey         |

The pin is positioned just above the host prim's bounding box (size
auto-scaled to the host bbox diagonal so a note on a small prop and on
a warehouse both render at sensible sizes).

## Compatibility

| Host                                  | Status |
|---------------------------------------|--------|
| Isaac Sim 5.1 (`isaacsim.exp.full`)   | Verified — CRUD / pin sync / JSON export green via self-test |
| USD Composer 2026.x / Kit 110.x       | Verified — primary live target during development |
| Kit 107.x SDK                         | Source-compatible (USD APIs + `omni.ui` 2.x only) |

Python: 3.11 (Kit 107) or 3.12 (Kit 110). No third-party PyPI packages.

## Dependencies

Declared in `config/extension.toml` (every entry is part of stock Kit —
**no external pip / conda / Nucleus dependencies**):

| Module                       | Used for                                                |
|------------------------------|---------------------------------------------------------|
| `omni.kit.uiapp`             | Window / widget host                                    |
| `omni.usd`                   | Stage access, selection, customData read/write          |
| `omni.ui`                    | Notes panel + detail editor + thread layout             |
| `omni.kit.viewport.utility`  | "Frame Prim" / "Select Prim" camera helpers             |
| `omni.kit.viewport.window`   | Viewport widget interop (kept for parity)               |

Standard library only: `dataclasses · json · time · uuid · getpass · os`.

Project policy: extension is **independent** — no `omni.mycompany.validation_api`
import. Drop-in usable in any Kit 107 / 110 host.

## Installation / activation

Pick the path that matches your workflow.

### 1. Drop the folder under an `--ext-folder`

```cmd
kit.exe ^
  --ext-folder C:/path/to/your/extensions ^
  --enable omni.mycompany.stage_annotator
```

The folder layout under that path must be `omni.mycompany.stage_annotator/`
(see "Layout" below).

### 2. Add to the project's `.env`

Append the id to `ISAAC_SIM_EXTRA_EXT_IDS` so
`setup-isaacsim-mcp.bat` forwards it as `--enable …` on next boot:

```env
ISAAC_SIM_EXTRA_EXT_IDS=[..., "omni.mycompany.stage_annotator"]
```

### 3. Window → Extensions UI (interactive)

`Window → Extensions`, search "Stage Annotator", flip the toggle. The
"Stage Annotator" window appears immediately.

### 4. MCP `extension_activate` (headless / scripted)

```python
extension_activate(ext_id="omni.mycompany.stage_annotator")
# returns {"enabled": true}, the Notes window appears
```

For a code reload during development:
```python
extension_activate(ext_id="omni.mycompany.stage_annotator", reload=True)
```

## How to use

1. Activate via `Window → Extensions → Stage Annotator`.
2. Pick a prim in the **Stage** panel or viewport.
3. In the Annotator window: click **+ New for Selection**.
   A new card appears, status `Open`, anchored to the prim. A red
   sphere pin appears in the viewport at the prim's bbox top.
4. Click the new card → the detail editor expands. Edit title / body
   inline; changes save on focus loss.
5. Cycle the status combo to push the workflow forward. Pin colour
   updates instantly.
6. Add replies in the **Replies** thread. Each reply records author
   (your OS username) and timestamp.
7. **Frame Prim** (camera) / **Select Prim** (stage panel) buttons let
   reviewers jump back to the host prim.
8. **Export JSON** writes all notes to
   `~/.stage_annotator_exports/notes_<timestamp>.json` for sharing
   outside Kit.

## Persistence

Notes are stored as a JSON blob in the stage's root-layer
`customLayerData` under the key `stage_annotator:notes`. Saving the USD
captures the notes; opening it on another machine restores them.

## Layout

```
omni.mycompany.stage_annotator/
├── config/extension.toml
└── omni/mycompany/stage_annotator/
    ├── __init__.py
    ├── extension.py       # IExt entry, hooks, self-test
    ├── note_store.py      # Data model + JSON persistence
    ├── pin_renderer.py    # 3D Sphere markers (re-syncs on store change)
    └── notes_panel.py     # ui.Window — list / filter / detail editor
```

## Self-test

`on_startup` runs three round-trip checks and stamps the results on
`/Annotator/SelfTestResult`:

* `crud_ok`   — add / update-status / add-reply / remove
* `pin_ok`    — store add → renderer creates `/Annotations/<id>/Pin`
* `export_ok` — `export_json()` returns parseable schema

```
stage_assert_property(
    /Annotator/SelfTestResult.crud_ok,   equals true
)
stage_assert_property(
    /Annotator/SelfTestResult.pin_ok,    equals true
)
stage_assert_property(
    /Annotator/SelfTestResult.export_ok, equals true
)
```

## Limits

| Constraint | Value |
|-----------:|:------|
| Max notes per stage | 256 |
| Max replies per note | 64 |
| Title / body length | unbounded (clipped only in card preview) |

These keep customLayerData under a comfortable size; raising them is
straightforward in `note_store.py`.

## Known limitations

* The author-filter combo is populated at panel build time. Adding a
  brand-new author after build doesn't dynamically extend the combo
  (Kit's `omni.ui.ComboBox` lacks an `add_item` API in 107.x). Use
  `Refresh` to rebuild after seeding test data.
* Pin position uses `UsdGeom.BBoxCache` — invisible / proxy-only prims
  fall back to `xformOp:translate` or the stage origin.
