"""Environment setup actions — scale, camera speed, hide toggle, WASD spawn, reset.

Pure functions operating on omni.usd.get_context()'s stage + selection.
scale_selected / reset_scale_selected use omni.kit.commands so Ctrl+Z works.
All returned strings are English only (Kit 107 omni.ui font atlas lacks CJK).
"""
from __future__ import annotations

import carb
import carb.settings
import omni.kit.commands
import omni.usd
from pxr import UsdGeom


_CAMERA_SPEED_KEY = "/persistent/app/viewport/camMoveVelocity"

# Substring keywords (case-insensitive) matched against prim.GetName() to decide
# which prims to hide via the Hide toggle button (B#3).
HIDE_KEYWORDS: tuple[str, ...] = ("ceiling", "ventilation", "cube")


# ---------------------- B#1: scale ----------------------

def _get_current_scale(stage, prim_path: str) -> tuple[float, float, float]:
    prim = stage.GetPrimAtPath(prim_path)
    attr = prim.GetAttribute("xformOp:scale")
    if attr and attr.IsValid():
        val = attr.Get()
        if val is not None:
            return (float(val[0]), float(val[1]), float(val[2]))
    return (1.0, 1.0, 1.0)


def scale_selected(factor: float) -> str:
    ctx = omni.usd.get_context()
    selected = ctx.get_selection().get_selected_prim_paths()
    if not selected:
        raise ValueError(
            "No prim selected. Select a prim in the Stage panel first."
        )
    stage = ctx.get_stage()
    for path in selected:
        cur = _get_current_scale(stage, path)
        new_scale = tuple(c * factor for c in cur)
        omni.kit.commands.execute(
            "TransformPrimSRTCommand",
            path=path,
            new_scale=new_scale,
        )
    return f"Scaled {len(selected)} prim(s) by {factor}x"


def reset_scale_selected() -> str:
    ctx = omni.usd.get_context()
    selected = ctx.get_selection().get_selected_prim_paths()
    if not selected:
        raise ValueError("No prim selected.")
    for path in selected:
        omni.kit.commands.execute(
            "TransformPrimSRTCommand",
            path=path,
            new_scale=(1.0, 1.0, 1.0),
        )
    return f"Reset scale to 1.0 for {len(selected)} prim(s)"


# ---------------------- B#2: camera speed ----------------------

def set_camera_speed(speed: float) -> str:
    if speed <= 0 or speed > 10.0:
        raise ValueError(f"camera speed out of range: {speed}")
    settings = carb.settings.get_settings()
    settings.set(_CAMERA_SPEED_KEY, float(speed))
    return f"Camera speed = {speed}"


# ---------------------- B#3: hide toggle ----------------------

def toggle_hidden_prims(state) -> str:
    """Case-insensitive substring match against HIDE_KEYWORDS + toggle + cache.

    Hides any prim whose name contains 'ceiling', 'ventilation', or 'cube'
    (case-insensitive). Second invocation restores the cached prims.
    The matched prim paths are stored in state.ceiling_cache regardless of
    keyword (the field name is historical — it now holds any hidden prim).
    """
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if not state.ceiling_hidden:
        matched: list[str] = []
        for prim in stage.Traverse():
            name_lower = prim.GetName().lower()
            if any(kw in name_lower for kw in HIDE_KEYWORDS):
                matched.append(str(prim.GetPath()))
        for path in matched:
            imageable = UsdGeom.Imageable(stage.GetPrimAtPath(path))
            if imageable:
                imageable.MakeInvisible()
        state.ceiling_cache = matched
        state.ceiling_hidden = True
        return f"Hid {len(matched)} prim(s) matching {list(HIDE_KEYWORDS)}"
    else:
        count = len(state.ceiling_cache)
        for path in state.ceiling_cache:
            prim = stage.GetPrimAtPath(path)
            if prim.IsValid():
                imageable = UsdGeom.Imageable(prim)
                if imageable:
                    imageable.MakeVisible()
        state.ceiling_cache = []
        state.ceiling_hidden = False
        return f"Restored {count} prim(s)"


# Backwards-compat alias — the old name is still used in tests and panel wiring
# until fully renamed. Prefer toggle_hidden_prims for new code.
toggle_ceiling_visibility = toggle_hidden_prims


# ---------------------- B#4: WASD Nova Carter spawn ----------------------

async def spawn_wasd_nova_carter(services, state) -> str:
    """Load Nova Carter (if not already) + build WASD ActionGraph on it."""
    from .step_actions import NOVA_CARTER_URL
    if not state.nova_carter_loaded:
        # StageLoadUsdRequestModel — {usd_url, prim_path, position?, rotation?}
        await services.stage.load_usd({
            "usd_url": NOVA_CARTER_URL,
            "prim_path": "/World/nova_carter",
            "position": [0.0, 0.0, 0.0],
        })
        state.nova_carter_loaded = True

    from ..bindings.graph_builder import build_wasd_graph
    graph_path = build_wasd_graph(
        graph_path="/World/nova_carter/WASDGraph",
        robot_prim="/World/nova_carter",
    )
    state.wasd_graph_path = graph_path
    return (
        f"WASD Nova Carter ready. Press Play + use W/A/S/D to drive, "
        f"Space to brake. Graph: {graph_path}"
    )


# ---------------------- Reset all ----------------------

async def reset_all(services, state) -> str:
    """Discard stage + reset all state flags to defaults."""
    await services.stage.new_stage()

    from .state import TutorialState
    default = TutorialState()
    for fld in default.__dataclass_fields__:
        setattr(state, fld, getattr(default, fld))

    return "All state reset (new stage loaded)"
