<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Defense code copied when the independent extension loads the MDL-heavy S3 asset -->

# USD Load Deadlock Recipe

## When is it needed?

When an independent extension needs to load **MDL-heavy asset** (office.usd, warehouse.usd, nova_carter.usd, etc.) from S3 to the stage. If you just call `omni.kit.commands.execute("CreatePayloadCommand", ...)`, on the student PC, **kit.exe freezes** for 92 seconds and then times out — Symptoms:

-viewport black screen
- UI completely unresponsive
- No error in Kit Console (silent hang)

Root cause: OmniUSDResolver's **MDL material retrieval thread** is in GIL contention with `carb.logging` callback thread, causing Kit main event loop to hang. The asyncio loop of the FastAPI handler/UI callback also stops simultaneously.

## Defense 3 Elements

1. **Disable `log_capture`** — If `carb.logging.acquire_logging().add_logger(cb)` is turned on while kit.exe is running, the MDL resolver loop will compete with the carb thread. Extension `on_startup` maintains `_log_capture = None` (allowed only by turning it on and off with request-scoped)
2. **`omni.kit.async_engine.run_coroutine` + `asyncio.wrap_future`** — The event loop of the FastAPI handler / UI callback and the Kit main event loop are separated. After specifying schedule command in Kit main loop, caller awaits with `wrap_future`
3. **`CreatePayloadCommand`** — payload method instead of `CreateReferenceCommand`. Path equivalent to Isaac Sim GUI drag&drop. Static payload is `instanceable=True`; Like the robot/articulation payload, the outer payload that requires runtime traversal/write is `instanceable=False`.
4. **Do not open MDL-payload scene with `stage_open`/`open_stage`(LoadAll)** — Desynchronize nested office.usd MDL 92s deadlock (office session verification). Be sure to load only **fresh stage + `CreatePayloadCommand` path**.

## Copy-paste recipe

```python
"""Self-contained USD load with deadlock protection.

Drop this helper into any independent Extension that needs to load MDL-heavy
S3 assets (office.usd, warehouse.usd, nova_carter.usd, F_Business_02.usd, ...).
No dependency on validation_api.
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
    """Load a USD payload into the stage with deadlock protection.

    Safe for S3 MDL-heavy assets. Call from any async context (UI callback,
    FastAPI handler, scenario step).
    """
    import omni.kit.async_engine
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, USDGeom

    usd_url = usd_url.replace("\\", "/")  # USD wants forward slashes

    async def _main_loop_impl():
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")# Parent must be a DEFINED prim. CreatePayloadCommand(path_to="/World/X")
        # auto-creates the parent "/World" as an `over` (no defining specifier);
        # an undefined ancestor prunes the whole subtree from the default-predicate
        # Traverse() AND from Hydra rendering (black viewport, tags unreachable).
        from pxr import Sdf
        parent_path = Sdf.Path(prim_path).GetParentPath()
        if not parent_path.isEmpty and parent_path != Sdf.Path.absoluteRootPath:
            USDGeom.Xform.Define(stage, parent_path)

        # GUI drag&drop equivalent — Payload + instanceable.
        # instanceable=True locks the payload into an instance prototype:
        # great for STATIC heavy nested payloads (office.usd), but it makes
        #prims unreachable to stage.Traverse() and un-editable. If THIS load
        # has runtime-edited/traversed content (emissive cables, customData
        # tags), pass instanceable=False for the OUTER load (nested static
        # payloads keep True).
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=ctx,
            path_to=prim_path,
            asset_path=usd_url,
            instanceable=instanceable,
        )

        # Wait until large asset loading is completed (tick can be performed in main loop)
        await_wait_stage_loading()

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not created at {prim_path}")

        # Apply position/rotation
        xformable = USDGeom.Xformable(prim)
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
            "prim_path":prim_path,
            "usd_url": usd_url,
            "type_name": str(prim.GetTypeName()),
        }

    # Core: Kit main loop specified schedule + await with wrap_future
    future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
    return await asyncio. wrap_future(future)


async def _wait_stage_loading(max_frames: int = 600) -> None:
    """Tick the Kit app until stage loading completes.

    Some Kit builds lack ``is_new_stage_loading`` /
    ``is_new_stage_activation_pending``. Prefer
    ``isaacsim.core.experimental.utils.stage.is_stage_loading`` when present,
    with ``get_stage_loading_status() -> (msg, files_loaded, total_files)`` as
    fallback.
    """
    import omni.kit.app # lazy
    import omni. usd    app = omni.kit.app.get_app()
    ctx = omni.usd.get_context()
    for _ in range(max_frames):
        await app.next_update_async()
        try:
            from isaacsim.core.experimental.utils.stage import is_stage_loading
            if not is_stage_loading():
                return
        except ImportError:
            _, files_loaded, total_files = ctx.get_stage_loading_status()
            if not (total_files > 0 and files_loaded < total_files):
                return
```

## Example of use (button callback of independent extension)

```python
import asyncio
from .safe_load import safe_load_usd

OFFICE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/Environments/Office/office.usd"
)


def on_load_office_clicked() -> None:
    async def _run():
        result = await safe_load_usd(
            OFFICE_URL,
            prim_path="/World/office",
            position=[0.0, 0.0, 0.0],
        )
        print(f"[my_ext] loaded: {result}")

    asyncio.ensure_future(_run())
```

## Trap Checklist

- [ ] Doesn’t Extension `on_startup` call `carb.logging.add_logger()`?
- [ ] Is the USD url a forward slash (`/`)? (backslash is interpreted strangely by the MDL resolver)
- [ ] Isn’t `log_capture` always activated other than request-scoped? Browser/content-browser presence itself is not a blocker and is not considered a root cause.
- [ ] Are you trying to load `simulation.play`? (timeline advance is additional contention)
- [ ] If there is a prim to edit/traverse at runtime, is the outer load `instanceable=False`? (If True, Traverse is stuck in instance prototype and not reached)
- [ ] Did you def the payload parent prim to `USDGeom.Xform.Define` before loading? (over parent subtree prune)

## Grounds

- Same code + docstring in `validation_api/services/stage_service.py::load_usd`
- 2026-04-20 User verification: isaac-sim.bat Kit (no extension) + GUI drag&drop successfully loaded static asset with `CreatePayloadCommand(instanceable=True)`. In a kit with an extension loaded, the event loop of the FastAPI handler and the main event loop of the kit are separated, so the command is not executed in the main loop → `run_coroutine` is required.
- 2026-06-10 Isaac Sim 6.0 robot live verification: `robot_load` uses the same payload pattern, but requires `instanceable=False` + active job rejection + timeline stop. Kit/PhysX crash reproduced when loading new robot payload during active navigation job.