"""Deadlock-safe USD loader for navmesh_playground (independent copy).

Source: kkr-extensions/docs/usd-load-deadlock-recipe.md + spec §8.4.
DO NOT import from omni.mycompany.validation_api — independent ext policy
(2026-04-22). Defensive 3 elements:
  1. Extension on_startup MUST keep `_log_capture = None`
  2. run_coroutine + wrap_future (Kit main loop schedule)
  3. CreatePayloadCommand(instanceable=True) (GUI drag&drop equivalent)
"""
from __future__ import annotations

import asyncio
import math
from typing import Any


BIPED_SETUP_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/People/Characters/Biped_Setup.usd"
)


async def safe_load_usd(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation: list[float] | None = None,
) -> dict[str, Any]:
    """Deadlock-safe USD payload load. Spec §8.4.

    Use for any S3 MDL-heavy asset (warehouse, nova_carter, Biped_Setup, ...).
    """
    import omni.kit.async_engine
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, UsdGeom

    usd_url = usd_url.replace("\\", "/")  # USD expects forward slashes

    async def _impl():
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=ctx,
            path_to=prim_path,
            asset_path=usd_url,
            instanceable=True,
        )
        await _wait_stage_loading()

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not created at {prim_path}")

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
            "type_name": str(prim.GetTypeName()),
        }

    future = omni.kit.async_engine.run_coroutine(_impl())
    return await asyncio.wrap_future(future)


def safe_load_usd_sync(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation: list[float] | None = None,
) -> dict[str, Any]:
    """Sync USD payload load — CreatePayloadCommand only (no wait).

    DECISION (2026-04-23): button callback 이 sync polling 으로 main thread 를
    오래 점유하면 omni.kit.ui_test.click 의 await 가 진행 못 함 + Kit ui
    event loop starvation → OS "non-responsive" kill. 따라서 callback 자체는
    CreatePayloadCommand 호출만 하고 즉시 return. 호출자가 별도로
    `wait_stage_loaded_async` (async, run_coroutine 으로 schedule) 호출하여
    children mesh fully load 까지 yield.

    Use ONLY from omni.ui callback (sync 짧음).
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, UsdGeom

    usd_url = usd_url.replace("\\", "/")
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    # Ensure parent Xform exists (CreatePayloadCommand silent-fails otherwise
    # for nested paths like /World/People/People_01 when /World/People absent).
    _ensure_parent_xform(stage, prim_path)

    cmd_result = omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=ctx,
        path_to=prim_path,
        asset_path=usd_url,
        instanceable=True,
    )

    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(
            f"Prim not created at {prim_path} (CreatePayloadCommand returned "
            f"{cmd_result!r}, asset_path={usd_url})"
        )
    # Validity may be true for empty placeholder — verify TypeName is set.
    type_name = str(prim.GetTypeName())
    if not type_name:
        raise RuntimeError(
            f"CreatePayloadCommand returned empty type at {prim_path} "
            f"(cmd_result={cmd_result!r}, asset_path={usd_url}). "
            "Likely silent fail — payload reference may need explicit add."
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
        "type_name": str(prim.GetTypeName()),
    }


async def wait_stage_loaded_async(max_ticks: int = 600) -> None:
    """Async wait — yield Kit main loop until stage stops loading.

    Use after `safe_load_usd_sync` to let payload children fully populate
    without freezing the UI.
    """
    import omni.kit.app
    app = omni.kit.app.get_app()
    for _ in range(max_ticks):
        if not _is_stage_loading_sync():
            return
        await app.next_update_async()


def _ensure_parent_xform(stage, prim_path: str) -> None:
    """Walk down the prim_path and Define an Xform for any missing intermediate.

    Required because `CreatePayloadCommand(path_to=...)` silently fails when
    the immediate parent is undefined (root '/' is OK; nested levels are not).
    """
    from pxr import Sdf, UsdGeom
    parts = [p for p in prim_path.split("/") if p]
    if not parts:
        return
    cur = ""
    for part in parts[:-1]:  # everything except the leaf
        cur = f"{cur}/{part}"
        if not stage.GetPrimAtPath(cur).IsValid():
            UsdGeom.Xform.Define(stage, Sdf.Path(cur))


def _is_stage_loading_sync() -> bool:
    """Sync check — true while USD payload children still loading."""
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


async def _wait_stage_loading(max_ticks: int = 1200) -> None:
    """Tick the Kit app until stage loading completes.

    Kit 5.1: ``UsdContext.is_new_stage_loading()`` 는 부재. 대신
    ``isaacsim.core.utils.stage.is_stage_loading`` 또는
    ``UsdContext.get_stage_loading_status()`` 사용 (character_service 패턴 일치).
    """
    import omni.kit.app

    app = omni.kit.app.get_app()
    for _ in range(max_ticks):
        await app.next_update_async()
        if not _is_stage_loading():
            return


def _is_stage_loading() -> bool:
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


_CHARS_ROOT = "/World/Characters"
_BIPED_PATH = f"{_CHARS_ROOT}/Biped_Setup"
# AnimationGraph prim is one level deeper than CharacterAnimation —
# matches services/character_service.py SoT (live-verified).
# Wrong suffix → "Animation graph not assigned a valid skeleton" warning
# + Action/Walk/PathPoints type-mismatch errors on set_variable.
_ANIM_GRAPH_SUFFIX = "/CharacterAnimation/AnimationGraph"


# NOTE on the "Mismatched units found on drag and drop" warning:
# Biped_Setup.usd is authored in centimetres (metersPerUnit=0.01) while
# Simple_Warehouse loads with metersPerUnit=1.0. USD detects this and
# silently inserts a `xformOp:scale:unitsResolve` of (100,100,100) on
# the imported prim so it renders at the correct physical size — the
# warning is purely informational. We deliberately do NOT mutate the
# stage's metersPerUnit to suppress the warning: doing so AFTER the
# warehouse is loaded retroactively rescales the warehouse / camera /
# everything else into a broken coordinate system, and AnimGraph world
# coordinates stop matching xformOp positions (live-discovered
# 2026-04-23). Treat the warning as cosmetic noise.


def _wait_stage_loaded_sync(max_wait_s: float = 10.0, poll_s: float = 0.05) -> bool:
    """Sync poll until the USD payload children finish populating.

    Used after CreatePayloadCommand so SkelRoot etc. exist before we try
    to find them. Returns True if loading finished, False on timeout.
    Safe for UI thread because the wait is short and Kit USD streaming
    runs on a background thread.
    """
    import time
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        if not _is_stage_loading_sync():
            return True
        time.sleep(poll_s)
    return False


def safe_spawn_character_sync(char_name: str, skin_url: str,
                              position: list[float], yaw: float = 0.0) -> dict:
    """Sync spawn with AnimGraph bind — UI thread direct, fully standalone.

    No validation_api dependency — pure Kit SDK + omni.kit.commands.
    Resolves two live-discovered issues:

    1. **AnimGraph bind path** — uses
       `/World/Characters/Biped_Setup/CharacterAnimation/AnimationGraph`
       (NOT `/CharacterAnimation` alone, which silently no-ops).
    2. **SkelRoot timing** — payload children populate asynchronously;
       we poll `is_stage_loading()` synchronously before recursing.

    Returns dict with `prim_path` (parent payload, for delete + Set Cur),
    `skel_root_path` (for AnimGraph variable manipulation), and a
    `anim_graph_bound` flag.

    Note: the "Mismatched units found on drag and drop" carb.log_warn is
    expected when the host stage is not in centimetres — see the
    module-level comment for why we accept the warning rather than
    rewrite stage units.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Sdf, UsdGeom, Usd, Gf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage")

    # Ensure parent scope
    if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(_CHARS_ROOT))

    # 1. Biped_Setup (shared, invisible). Holds the AnimationGraph that
    # every skin binds to. Use add_reference_to_stage instead of
    # CreatePayloadCommand so the rig is registered with
    # ``omni.anim.graph.core`` correctly (verified via character_service
    # parity — CreatePayloadCommand alone does not trigger AnimGraph
    # character registration, leaving `ag.get_character()` returning
    # None forever and the Walk variables silently no-op).
    from isaacsim.core.utils.stage import add_reference_to_stage  # lazy
    biped_loaded_now = False
    if not stage.GetPrimAtPath(_BIPED_PATH).IsValid():
        add_reference_to_stage(BIPED_SETUP_URL, _BIPED_PATH)
        biped_loaded_now = True
        # Wait for payload + then hide the rig so it does not render.
        _wait_stage_loaded_sync(max_wait_s=15.0)
        biped_prim = stage.GetPrimAtPath(_BIPED_PATH)
        if biped_prim.IsValid():
            vis = biped_prim.GetAttribute("visibility")
            if vis and vis.IsValid():
                vis.Set("invisible")

    # 2. Skin via CharacterUtil — the official Isaac Sim path that
    # registers the new character with ``omni.anim.graph.core`` so
    # ``get_character()`` will return a valid handle on the next tick.
    # ``CharacterUtil.load_character_usd_to_stage(url, position, yaw, name)``
    # places the character at ``/World/Characters/{name}``.
    from isaacsim.replicator.agent.core.stage_util import CharacterUtil  # lazy
    CharacterUtil.load_character_usd_to_stage(
        skin_url, list(position or [0.0, 0.0, 0.0]), float(yaw), char_name,
    )
    skin_path = f"{_CHARS_ROOT}/{char_name}"

    # 3. Wait for payload children (SkelRoot etc.) to populate.
    _wait_stage_loaded_sync(max_wait_s=15.0)
    skin_prim = stage.GetPrimAtPath(skin_path)
    if not skin_prim.IsValid():
        raise RuntimeError(f"Skin payload failed at {skin_path}")

    # 4. Find SkelRoot recursively (DH characters nest under DHGen).
    skel_root_path = None
    root = stage.GetPrimAtPath(skin_path)
    for prim in Usd.PrimRange(root):
        if prim.GetTypeName() == "SkelRoot":
            skel_root_path = prim.GetPath().pathString
            break
    if skel_root_path is None:
        raise RuntimeError(
            f"SkelRoot not found under {skin_path} after stage settle. "
            "Skin USD may be malformed or the S3 reference 404'd silently."
        )

    # 5. Bind AnimationGraph. The exact prim path is critical — wrong
    # suffix → silent no-op + "Animation graph not assigned a valid
    # skeleton" warning at first set_variable.
    anim_graph_path = _BIPED_PATH + _ANIM_GRAPH_SUFFIX
    anim_graph_bound = False
    ag_prim = stage.GetPrimAtPath(anim_graph_path)
    if ag_prim.IsValid():
        omni.kit.commands.execute(
            "ApplyAnimationGraphAPICommand",
            paths=[Sdf.Path(skel_root_path)],
            animation_graph_path=Sdf.Path(anim_graph_path),
        )
        anim_graph_bound = True

    # NOTE: AnimGraph plugin character registration warm-up is handled
    # async in `people_controller._walk_then_sit` after the Go button.
    # We deliberately do NOT call `kit_app.update()` here — calling
    # `app.update()` from a sync UI button callback (already inside a
    # Kit update tick) deadlocks Kit (verified 2026-04-23, hang +
    # taskkill required). The async warm-up uses `await
    # app.next_update_async()` which is safe.

    return {
        "ok": True,
        "prim_path": skin_path,
        "skel_root_path": skel_root_path,
        "anim_graph_bound": anim_graph_bound,
        "biped_loaded_now": biped_loaded_now,
    }


async def safe_load_character(
    char_name: str,
    skin_url: str,
    position: list[float] | None = None,
    yaw: float = 0.0,
) -> dict[str, str]:
    """Load Biped_Setup rig + overlay skin asset + bind AnimationGraph.

    Mirrors validation_api.character_service.load (검증된 CharacterUtil 패턴).
    `char_name` 은 USD-safe identifier (sanitize 호출자 책임). 반환 dict 에
    `sanitized_prim_path` 가 후속 호출용 SkelRoot path.

    Spec §8.4 의 prim_path-based shape 와는 다름 — character_service.load
    의 validated path. 이 함수는 항상 `/World/Characters/<char_name>` 에 배치.
    """
    async def _impl():
        import omni.kit.commands
        import omni.usd
        from isaacsim.replicator.agent.core.stage_util import CharacterUtil
        from isaacsim.storage.native import get_assets_root_path
        from pxr import Sdf, UsdGeom

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        assets_root = (get_assets_root_path() or "").rstrip("/")
        if not assets_root:
            raise RuntimeError("Isaac Sim assets root unresolved.")

        # 1. Ensure shared Biped rig (invisible)
        if not stage.GetPrimAtPath(_BIPED_PATH).IsValid():
            from isaacsim.core.utils.stage import add_reference_to_stage
            if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
                UsdGeom.Xform.Define(stage, _CHARS_ROOT)
            biped_url = f"{assets_root}/Isaac/People/Characters/Biped_Setup.usd"
            add_reference_to_stage(biped_url, _BIPED_PATH)
            await _wait_stage_loading()
            biped_prim = stage.GetPrimAtPath(_BIPED_PATH)
            if not biped_prim.IsValid():
                raise RuntimeError(f"Biped_Setup failed to resolve at {_BIPED_PATH}")
            vis = biped_prim.GetAttribute("visibility")
            if vis and vis.IsValid():
                vis.Set("invisible")

        # 2. Load skin via CharacterUtil
        CharacterUtil.load_character_usd_to_stage(
            skin_url, list(position or [0.0, 0.0, 0.0]), float(yaw), char_name,
        )
        await _wait_stage_loading()

        sanitized_prim_path = f"{_CHARS_ROOT}/{char_name}"

        # 3. Find SkelRoot
        skel_root_path = _find_skel_root(stage, sanitized_prim_path)
        if skel_root_path is None:
            raise RuntimeError(f"SkelRoot not found under {sanitized_prim_path}")

        # 4. Bind AnimationGraph
        anim_graph_path = _BIPED_PATH + _ANIM_GRAPH_SUFFIX
        if not stage.GetPrimAtPath(anim_graph_path).IsValid():
            raise RuntimeError(f"AnimationGraph missing at {anim_graph_path}")
        omni.kit.commands.execute(
            "ApplyAnimationGraphAPICommand",
            paths=[Sdf.Path(skel_root_path)],
            animation_graph_path=Sdf.Path(anim_graph_path),
        )

        return {
            "sanitized_prim_path": sanitized_prim_path,
            "skel_root_path": skel_root_path,
        }

    import omni.kit.async_engine
    return await asyncio.wrap_future(omni.kit.async_engine.run_coroutine(_impl()))


def _find_skel_root(stage, prim_path: str) -> str | None:
    """Recursively find first SkelRoot prim under prim_path."""
    from pxr import Usd
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        return None
    for prim in Usd.PrimRange(root):
        if prim.GetTypeName() == "SkelRoot":
            return prim.GetPath().pathString
    return None


async def safe_load_robot(
    prim_path: str,
    usd_url: str,
    position: list[float] | None = None,
) -> dict[str, Any]:
    """Load robot USD. Caller must subsequently:
       1) simulation_play → 1 tick → pause (articulation registry warm-up, T0.9)
       2) SingleArticulation(prim_path).initialize()  (5.1 required)
    """
    return await safe_load_usd(usd_url, prim_path, position=position)


def _set_yaw(prim_path: str, yaw: float) -> None:
    import omni.usd
    from pxr import Gf, UsdGeom
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    xf = UsdGeom.Xformable(prim)
    r_attr = prim.GetAttribute("xformOp:rotateXYZ")
    if not r_attr.IsValid():
        r_attr = xf.AddRotateXYZOp()
    r_attr.Set(Gf.Vec3f(0.0, 0.0, math.degrees(yaw)))
