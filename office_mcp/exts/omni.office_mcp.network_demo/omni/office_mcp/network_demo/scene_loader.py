"""Load Scene flow: fresh stage -> deadlock-safe reference -> tag discovery.

``office_datacenter.usd`` is referenced (as a payload, via ``safe_load_usd``)
under ``/World/OfficeDemo``. The scene's own nested ``office.usd`` payload
composes transitively, resolving its MDL materials inside the deadlock-safe
tick loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import scene_tags
from .safe_load import safe_load_usd

DEMO_ROOT = "/World/OfficeDemo"


def default_scene_url() -> str:
    """Absolute forward-slash path to ``office_mcp/scenes/office_datacenter.usd``.

    Resolved relative to this file so it works regardless of repo location:
    ``.../office_mcp/exts/omni.office_mcp.network_demo/omni/office_mcp/network_demo/scene_loader.py``
    -> ``office_mcp`` is ``parents[5]``.
    """
    office_mcp_root = Path(__file__).resolve().parents[5]
    scene = office_mcp_root / "scenes" / "office_datacenter.usd"
    return str(scene).replace("\\", "/")


async def load_scene(scene_url: str | None = None, prim_path: str = DEMO_ROOT) -> dict[str, Any]:
    """Open a clean stage and reference the demo scene; discover its tags.

    Returns ``{ok, prim_path, usd_url, tags, missing, error}``. Idempotent —
    each call starts from a fresh stage (SPEC §8).
    """
    import carb
    import omni.timeline
    import omni.usd

    url = (scene_url or default_scene_url()).replace("\\", "/")

    # Deadlock guard: never load while the timeline is playing.
    try:
        omni.timeline.get_timeline_interface().stop()
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[scene_loader] timeline stop soft-fail: {exc!r}")

    ctx = omni.usd.get_context()

    # Fresh stage so repeated Load Scene clicks are idempotent.
    try:
        await ctx.new_stage_async()
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[scene_loader] new_stage_async soft-fail, trying new_stage: {exc!r}")
        try:
            ctx.new_stage()
        except Exception as exc2:  # noqa: BLE001
            return {"ok": False, "error": f"new_stage failed: {exc2!r}"}

    # CreatePayloadCommand at /World/OfficeDemo would otherwise auto-create the
    # parent /World as an *over* (no defining specifier). An undefined ancestor
    # prunes the whole subtree from the default traversal predicate AND from
    # Hydra rendering. Define /World as a real Xform first so the loaded scene
    # is both discoverable and renderable.
    try:
        from pxr import UsdGeom
        UsdGeom.Xform.Define(ctx.get_stage(), "/World")
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[scene_loader] define /World soft-fail: {exc!r}")

    try:
        # instanceable=False so the tagged demo prims stay traversable + the
        # cable/LED emissive stays editable; the nested office.usd payload keeps
        # its own instanceable=True (authored in build_scene).
        result = await safe_load_usd(url, prim_path=prim_path, instanceable=False)
    except Exception as exc:  # noqa: BLE001
        carb.log_error(f"[scene_loader] safe_load_usd failed: {exc!r}")
        return {"ok": False, "usd_url": url, "error": f"load failed: {exc!r}"}

    stage = ctx.get_stage()
    tags = scene_tags.discover(stage)
    result["tags"] = tags
    result["missing"] = tags.missing()
    if not tags.ok:
        result["ok"] = False
        result["error"] = "Scene tags not found - rebuild scene"
    return result
