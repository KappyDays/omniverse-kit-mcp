"""Deadlock-safe USD loader for humanoid_pick_place (independent ext copy).

Mirrors ``kkr-extensions/docs/usd-load-deadlock-recipe.md`` defensive
3 elements:
    1. Extension on_startup keeps ``_log_capture = None`` (handled by
       ``HumanoidPickPlaceExtension.on_startup``)
    2. ``CreatePayloadCommand(instanceable=True)`` for MDL-heavy assets
    3. Stage-loading wait via ``isaacsim.core.utils.stage.is_stage_loading``
       (Kit 5.1 has no ``UsdContext.is_new_stage_loading``)

We deliberately do NOT import from ``omni.mycompany.validation_api`` —
independent extension policy (2026-04-22).
"""

from __future__ import annotations

import time
from typing import Any


def safe_load_usd_sync(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation: list[float] | None = None,
    instanceable: bool = False,
) -> dict[str, Any]:
    """Sync UsdContext + CreatePayloadCommand load.

    Used inside button callbacks where awaiting the full payload would
    block the Kit UI thread. The caller is expected to follow up with
    :func:`wait_stage_loaded_sync` before reading the loaded prims.

    ``instanceable=False`` for the humanoid root (the articulation is
    authored such that PhysX needs unique payload prims to track DOFs);
    set ``True`` for cosmetic assets (tables, props) where instanceable
    saves memory.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, Sdf, UsdGeom

    usd_url = usd_url.replace("\\", "/")
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    _ensure_parent_xform(stage, prim_path)

    cmd_result = omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=ctx,
        path_to=prim_path,
        asset_path=usd_url,
        instanceable=instanceable,
    )

    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(
            f"Prim not created at {prim_path} (CreatePayloadCommand result "
            f"{cmd_result!r}, asset {usd_url})"
        )

    type_name = str(prim.GetTypeName())
    if not type_name:
        raise RuntimeError(
            f"CreatePayloadCommand returned empty type at {prim_path} "
            f"(asset {usd_url}). Likely silent fail."
        )

    xf = UsdGeom.Xformable(prim)
    if position is not None:
        t_attr = prim.GetAttribute("xformOp:translate")
        if not t_attr.IsValid():
            t_attr = xf.AddTranslateOp()
        t_attr.Set(Gf.Vec3d(position[0], position[1], position[2]))
    if rotation is not None:
        r_attr = prim.GetAttribute("xformOp:rotateXYZ")
        if not r_attr.IsValid():
            r_attr = xf.AddRotateXYZOp()
        r_attr.Set(Gf.Vec3f(rotation[0], rotation[1], rotation[2]))

    return {
        "ok": True,
        "prim_path": prim_path,
        "usd_url": usd_url,
        "type_name": type_name,
    }


def wait_stage_loaded_sync(max_wait_s: float = 15.0, poll_s: float = 0.05) -> bool:
    """Sync poll of ``is_stage_loading`` until payload children populate.

    Returns ``True`` when loading completes within ``max_wait_s``,
    ``False`` on timeout. Safe to call from a UI callback for short
    waits (Kit USD streaming runs on a background thread).
    """
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        if not _is_stage_loading_sync():
            return True
        time.sleep(poll_s)
    return False


def _is_stage_loading_sync() -> bool:
    try:
        from isaacsim.core.utils.stage import is_stage_loading
        return is_stage_loading()
    except ImportError:
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            _, files_loaded, total_files = ctx.get_stage_loading_status()
            return total_files > 0 and files_loaded < total_files
        except Exception:
            return False


def _ensure_parent_xform(stage, prim_path: str) -> None:
    """Define an Xform for any missing intermediate path component.

    ``CreatePayloadCommand`` silently fails when an intermediate parent
    is undefined (e.g. ``/World/Demo/Humanoid`` when ``/World/Demo`` is
    absent).
    """
    from pxr import Sdf, UsdGeom
    parts = [p for p in prim_path.split("/") if p]
    if not parts:
        return
    cur = ""
    for part in parts[:-1]:
        cur = f"{cur}/{part}"
        if not stage.GetPrimAtPath(cur).IsValid():
            UsdGeom.Xform.Define(stage, Sdf.Path(cur))
