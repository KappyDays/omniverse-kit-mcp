"""Self-contained USD load with deadlock protection.

Copied (not imported) from ``kkr-extensions/docs/usd-load-deadlock-recipe.md``
per the independent-extension policy. Loading the office_datacenter scene
transitively composes ``office.usd`` (MDL-heavy), which freezes kit.exe for ~92s
unless the three defenses are in place:

1. ``on_startup`` never calls ``carb.logging.add_logger()`` (the extension keeps
   ``_log_capture = None``).
2. ``omni.kit.async_engine.run_coroutine`` + ``asyncio.wrap_future`` — schedule
   the command on the Kit main event loop (a UI callback's asyncio loop is a
   different loop).
3. ``CreatePayloadCommand(instanceable=True)`` — the GUI drag&drop path —
   followed by a ``_wait_stage_loading`` tick loop.

USD URLs/paths must use forward slashes; loading is never done while the
timeline is playing.
"""

from __future__ import annotations

import asyncio
from typing import Any


async def safe_load_usd(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation: list[float] | None = None,
    instanceable: bool = True,
) -> dict[str, Any]:
    """Load a USD reference into the stage with deadlock protection.

    Safe for S3 MDL-heavy assets. Call from any async context (UI callback,
    scenario step).

    ``instanceable`` defaults to True (the GUI drag&drop equivalent). The
    office_datacenter scene is loaded with ``instanceable=False`` so its tagged
    demo prims stay traversable + editable (emissive animation); the nested
    office.usd payload carries its own ``instanceable=True`` for the static,
    MDL-heavy building.
    """
    import omni.kit.async_engine
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, UsdGeom

    usd_url = usd_url.replace("\\", "/")  # USD wants forward slashes

    async def _main_loop_impl():
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        # GUI drag&drop equivalent — Payload + instanceable=True
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=ctx,
            path_to=prim_path,
            asset_path=usd_url,
            instanceable=instanceable,
        )

        # Wait for the (potentially large) payload to finish composing — the
        # Kit main loop keeps ticking here so MDL resolution can complete.
        await _wait_stage_loading()

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not created at {prim_path}")

        xformable = UsdGeom.Xformable(prim)
        if position is not None:
            t_attr = prim.GetAttribute("xformOp:translate")
            if not t_attr.IsValid():
                t_attr = xformable.AddTranslateOp()
            t_attr.Set(Gf.Vec3d(position[0], position[1], position[2]))
        if rotation is not None:
            r_attr = prim.GetAttribute("xformOp:rotateXYZ")
            if not r_attr.IsValid():
                r_attr = xformable.AddRotateXYZOp()
            r_attr.Set(Gf.Vec3f(rotation[0], rotation[1], rotation[2]))

        return {
            "ok": True,
            "prim_path": prim_path,
            "usd_url": usd_url,
            "type_name": str(prim.GetTypeName()),
        }

    # Core: schedule on the Kit main loop + await via wrap_future.
    future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
    return await asyncio.wrap_future(future)


async def _wait_stage_loading(max_ticks: int = 2400) -> None:
    """Tick the Kit app until stage loading (payload/MDL resolution) completes.

    Isaac Sim 5.1's ``UsdContext`` has no ``is_new_stage_loading`` (the recipe's
    original method); the live API is ``get_stage_loading_status() -> (msg,
    loaded, total)`` where ``total == 0`` means nothing is pending. We warm up a
    few frames so loading can kick off, then wait for several consecutive idle
    ticks so we don't exit before the office payload's MDL has started resolving.
    """
    import omni.kit.app
    import omni.usd

    app = omni.kit.app.get_app()
    ctx = omni.usd.get_context()
    for _ in range(5):
        await app.next_update_async()
    idle = 0
    for _ in range(max_ticks):
        try:
            _msg, _loaded, total = ctx.get_stage_loading_status()
        except Exception:  # noqa: BLE001 — be tolerant of API drift
            return
        if total == 0:
            idle += 1
            if idle >= 3:
                return
        else:
            idle = 0
        await app.next_update_async()
