"""Self-contained USD load with deadlock protection.

Drop-in helper for loading MDL-heavy S3 assets (Franka, warehouse, ...). Uses
`run_coroutine` + `CreatePayloadCommand(instanceable=True)` 3-element recipe.

Reference: docs/invariants/usd-load.md, kkr-extensions/docs/usd-load-deadlock-recipe.md
"""
from __future__ import annotations

import asyncio
from typing import Any


async def safe_load_usd(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation_xyz: list[float] | None = None,
    expected_child: str | None = None,
) -> dict[str, Any]:
    """Load a USD reference into the stage with deadlock protection."""
    import omni.kit.async_engine
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, Sdf, UsdGeom

    usd_url = usd_url.replace("\\", "/")

    async def _main_loop_impl() -> dict[str, Any]:
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        sdf_path = Sdf.Path(prim_path)

        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=ctx,
            path_to=sdf_path,
            asset_path=usd_url,
            instanceable=True,
        )

        await _wait_payload_loaded(prim_path, expected_child=expected_child)

        prim = stage.GetPrimAtPath(sdf_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not created at {prim_path}")

        xformable = UsdGeom.Xformable(prim)
        if position is not None:
            t_attr = prim.GetAttribute("xformOp:translate")
            if not t_attr.IsValid():
                t_attr = xformable.AddTranslateOp().GetAttr()
            t_attr.Set(Gf.Vec3d(position[0], position[1], position[2]))
        if rotation_xyz is not None:
            r_attr = prim.GetAttribute("xformOp:rotateXYZ")
            if not r_attr.IsValid():
                r_attr = xformable.AddRotateXYZOp().GetAttr()
            r_attr.Set(Gf.Vec3f(rotation_xyz[0], rotation_xyz[1], rotation_xyz[2]))

        return {
            "ok": True,
            "prim_path": prim_path,
            "usd_url": usd_url,
            "type_name": str(prim.GetTypeName()),
        }

    future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
    return await asyncio.wrap_future(future)


async def _wait_payload_loaded(
    prim_path: str,
    expected_child: str | None = None,
    max_ticks: int = 1200,
    min_ticks: int = 30,
) -> None:
    """Tick the Kit app until a referenced/payloaded prim's sub-tree is populated."""
    import omni.kit.app
    import omni.usd
    from pxr import Sdf

    app = omni.kit.app.get_app()
    ctx = omni.usd.get_context()

    sdf_root = Sdf.Path(prim_path)
    sdf_target = Sdf.Path(f"{prim_path}/{expected_child}") if expected_child else None

    for _ in range(min_ticks):
        await app.next_update_async()

    for _ in range(max_ticks - min_ticks):
        stage = ctx.get_stage()
        if stage is not None:
            prim = stage.GetPrimAtPath(sdf_root)
            if prim.IsValid():
                if sdf_target is not None:
                    target = stage.GetPrimAtPath(sdf_target)
                    if target.IsValid():
                        for _ in range(5):
                            await app.next_update_async()
                        return
                else:
                    children = list(prim.GetAllChildren())
                    if len(children) > 0:
                        for _ in range(5):
                            await app.next_update_async()
                        return
        await app.next_update_async()
