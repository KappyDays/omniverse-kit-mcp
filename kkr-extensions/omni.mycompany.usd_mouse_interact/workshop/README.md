# usd-mouse-interact (v0.2.1)

Kit Extension verified against the locally-built **KKR USD Composer 0.1.1**
(`apps/kkr_usd_composer.kit`, kit-app-template build, Kit
`110.1.0+main.0.c98fc5cb.local`). Turns the active viewport into an FPS-style
whitelist-picker while the timeline is playing:

- **Mouse-look** — moving the mouse rotates the active camera (yaw + pitch).
  Direct call of Win32 `user32.GetCursorPos` / `SetCursorPos` to ctypes → Isaac Sim
  Works with both USD Composer and USD Composer (regardless of whether the cursor API is exposed in Kit appwindow or not).
  Linux/macOS builds are in the following order: carb.windowing → appwindow API → 0-delta guard
  fallback.
- **WASD + Q/E** — translates the camera (forward / straight / vertical).
- **Circular crosshair** — a small white `omni.ui.Circle` (10 px) pinned to the
  viewport center.
- **Whitelist pick highlight** — Only the prim in `customLayerData["usdMouseInteract"]
  .allowed_prims` is displayed as USD selection when hovered.
- **Top-left info panel** — `customLayerData["usdMouseInteract"].descriptions`
  If the user text takes precedence, prim metadata falls back (kind/displayName).
- **Timeline play / stop** — toggles the whole feature on and off.
- **ESC** — soft-disengage (mouse + key capture stop) without stopping the
  timeline. Re-engage by stopping and replaying the timeline.

This folder holds the **workshop / verification material** (design notes,
tests, helper scripts) for the parent Kit Extension at
`kkr-extensions/omni.mycompany.usd_mouse_interact/`.

## Folder layout

```
kkr-extensions/omni.mycompany.usd_mouse_interact/
├── config/                         — Kit extension manifest
├── omni/mycompany/usd_mouse_interact/
│                                   — extension source
└── workshop/                       — workshop material
    ├── README.md                   — this file
    ├── docs/
    │   ├── design.md               — architecture, components, decisions
    │   └── verification-report.md  — live + unit-test verification results
    ├── tests/
    │   ├── conftest.py
    │   ├── test_camera_math.py
    │   ├── test_input_state.py
    │   ├── test_interaction_state_machine.py
    │   └── test_metadata_store.py
    └── scripts/
        └── save_capture_pair.py    — split window_capture into local app + viewport captures
```

## Install / enable inside USD Composer

The extension already lives under `kkr-extensions/`, which is passed as a Kit
`--ext-folder` by the default workspace launchers in this repo.

After USD Composer is running you can:

```python
# via MCP (this repo's tools)
extension_activate(ext_id="omni.mycompany.usd_mouse_interact")
```

or, in the Kit UI, **Window → Extensions → Third Party →
omni.mycompany.usd_mouse_interact** → toggle on.

## Quickstart

1. **Launch Dev panel** — `Window → USD Mouse Interact` after activating extension
   (If not present, toggle on `Window → Extensions`). Once the panel pops up, you can dock it.
2. **Create Whitelist** — Select prim from Stage panel → dev panel **Add** →
   **Save** (see Chapter 3 *Whitelist Editing*).
3. **Play** — Timeline ▶ When pressed, a white crosshair is output in the center of the viewport + camera capture
   Start. From this point, mouse movement → yaw/pitch, **W/A/S/D** → forward/strafe,
   **E/Q** → up/down.
4. **Hover** — When the crosshair touches the whitelisted prim (a) USD selection
   Displayed in + (b) InfoOverlay (title + description) output at the top left of the viewport.
5. **Off** — **Stop** (▪) or **Esc**. ▪ When pressed, the camera moves to the position just before Play.
   It is automatically restored, and if you just press **Esc**, only the input capture is released and the camera moves to the current position.
   Hold (to re-lock ▪ → ▶).

## Camera controls (only active during Play)

| input | Action |
|------|------|
| Mouse Move | yaw + pitch (return to screen center every frame with Win32 `SetCursorPos`) |
| `W` / `S` | forward / backward |
| `A` / `D` | straight left / right |
| `E` / `Q` | up / down (based on world up-axis) |
| `Esc` | Turn off input capture only (maintain camera position) |
| Stop (▪) | Uncapture + restore camera position + remove crosshair/InfoOverlay |

Movement speed and mouse sensitivity can be adjusted in real time in the **Tuning** section of the dev panel.

> **Known limitations — text input during fly mode**
> During Fly mode active, the `W A S D Q E R` key toggles the viewport gizmo shortcut key.
> *consume* to prevent (W=Translate, E=Rotate, R=Scale, Q=Select).
> As a side effect, the Edit description modal of the dev panel / Stage panel search box /
> Even if the focus is on another widget such as a property field, these keys are used by typing.
> Not delivered. If text input is required, press **Stop** (▪) or **Esc**.
> Turn off fly mode first. ESC itself is host modal dialog (Save confirm
> etc.) is propagated to avoid conflict with .

## Edit Whitelist (Add / Remove / Clear / Save)

Whitelist determines *which prim is the target of highlight + InfoOverlay when hovered*
A set of prim paths to determine. Manage with the 4 buttons at the top of the dev panel:| button | Action | Impact |
|------|------|------|
| **Add** | Merge *currently selected* prims in Stage to whitelist | in-memory immediately + Stage immediately reflected (call controller `reload_metadata`) |
| **Remove** | Exclude selected prims from the whitelist + also delete the prim's description | Same |
| **Clear** | Empty all whitelist and description | Same |
| **Save** | Write the current in-memory state to layer customLayerData again | (Usually for explicit synchronization since Add/Remove automatically saves) |

### Standard flow for registering a new prim as target

1. Click target prim on the **Stage panel** (left). Multiple selection (Ctrl/Shift) support.
2. Click **Add** in **dev panel**. The status label in the middle of the panel is
   It is updated as `1 prim(s) -- 0 described`, and the prim path is displayed in the scroll area below.
   Row added.
3. *(Optional)* Write a description using the **Edit** button in that row (next section).
4. To permanently save to the USD file itself, select **File → Save** (Ctrl+S) in USD Composer.
   The whitelist is serialized together within `customLayerData` of the layer, so it is exported separately.
   Not necessary. (**Save** button on dev panel is only layer in-memory synchronization — disk
   Saving is handled by Kit’s File Save.)

### Automatic matching of descendant prim

Whitelist entries follow the *ancestor matching* rule. For example
Even if you only register `/World/Robot`, hover over `/World/Robot/Joint1/Mesh` below it.
If you do this, it will be treated as a hit as `/World/Robot` (longest-ancestor priority). Therefore, large groups
It is efficient to register only one group prim.

## Edit Description (InfoOverlay text at top left)

The `desc` area of InfoOverlay is determined by the following priorities:

1. **User description** — `customLayerData["usdMouseInteract"]
   .descriptions[<hit_path>]` (exact/longest ancestor matching).
2. **prim metadata fallback** — If the above field is empty
   `f"{typeName} — under {parent_path}"` (e.g. `Cube — under /World`).
3. **invalid prim** — `(unknown prim)`.

### Editing description in dev panel

1. There is one line per prim in the **Whitelist + Descriptions** section of the dev panel.
   (`/World/TestCube` `Test cu...efault...` `Edit`).
2. Click the **Edit** button → Separate modal window (`Edit description -- /<path>`)
   Stopping.
3. Enter text in the center multiline `StringField`. Latin (ASCII) + ASCII
   Only punctuation is rendered normally (known limitation of Kit 110 omni.ui — Korean/CJK
   is displayed in the `?` box, so it is recommended to write in English).
4. When you press **OK**, it is immediately reflected in in-memory and layer customLayerData. **Cancel**
   Change is obsolete.
5. Hover again → `desc` in InfoOverlay is immediately updated with new text.

### When you want to show only prim’s own metadata

If you leave description empty (or OK with an empty string after entering it), the fallback rule will run.
Activated. In this case, an automatic label such as `Cube — under /World` is output. an empty string
Saving will remove that key from the `descriptions` dict (saving storage).

### Edit USD directly

It is also possible to write customLayerData by hand in the editor. layer root to:

```usda
customLayerData = {
    dictionary usdMouseInteract = {
        string[] allowed_prims = ["/World/TestCube", "/World/Robot"]
        dictionary descriptions = {
            string "/World/TestCube" = "Test target cube."
            string "/World/Robot"    = "Franka arm group."
        }
    }
}
```

After saving, reactivate **extension** (deactivate → activate) in the dev panel or
Restarting USD Composer reloads the panel with new data.

## Tuning (Speed / Sensitivity)

Instantly adjust camera response with two sliders in the **Tuning** section at the bottom of the dev panel:

| Slider | range | Unit/Meaning | default |
|----------|-----|-------------|-------|
| **Speed** | 50 ~ 5000 | Translation speed (units/sec, based on USD up-axis) | 500 |
| **Sensitivity** | 1 to 100 | Mouse rotation scale (internally `× 0.0001` → radians/pixel) | 25 |

Value changes are applied starting from the next frame — No Stop/Play cycle required. Meta Rule: USD
Composer / Isaac Sim Both viewports are 1 unit = 1 cm (`metersPerUnit = 0.01`)
In the scene, the speed is felt as 500 ≈ 5 m/s, and for demonstration of a distant environment, it is 1500 ~
3000, for close detailed inspection, 200 to 500 is acceptable.

> Sliders are *in-session* values. Since it is not stored in the USD file, the next session will
> Restart with defaults (500 / 25).

## Data storage location

All whitelist + descriptions are in the **root layer** of the current active stage.
Saved in `customLayerData["usdMouseInteract"]`:

```
customLayerData
└── usdMouseInteract
    ├── allowed_prims  : Vt.StringArray  (sorted path list)
    └── descriptions   : dict[str, str]  (path → user text)
```

Core rules:

- **Stage-specific dependency** — When you open another USD file, only the customLayerData of that file is
  Read. There is no separate extension global repository.
- **Ignore Sublayer / reference** — Only the root layer is seen. in the sublayer
  customLayerData is ignored, so be careful when working with sublayers.
- **Save == File Save** — **Save** in dev panel is for updating in-memory layer.
  Actual disk saving can be done using USD Composer's **File → Save** (Ctrl+S) or
  Taken by **Save As**. If you quit without saving, you lose.

## Development

### Run unit tests

```powershell
.venv/Scripts/python.exe -m pytest kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/tests -v
```

### Reload after editing

`.py` changes are picked up by Kit's fswatcher within a few seconds. If a
reload doesn't take effect (Python sys.modules cache), call
`extension_activate(ext_id="omni.mycompany.usd_mouse_interact", reload=True)`.

### Why `omni.mycompany.*`?USD Composer (Kit-app-template build) only mounts already-registered top-level
namespaces; `omni.kappy.*` and bare `kappy_*` were silently ignored even when
the manifest was found. This is documented in the verification report.