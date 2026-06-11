"""Deadlock-safe USD loader for navmesh_playground (independent copy).

Source: kkr-extensions/docs/usd-load-deadlock-recipe.md + spec §8.4.
DO NOT import from omni.mycompany.validation_api — independent ext policy
(2026-04-22). Defensive 3 elements:
  1. Extension on_startup MUST keep `_log_capture = None`
  2. run_coroutine + wrap_future (Kit main loop schedule)
  3. CreatePayloadCommand(instanceable=True) for static playground payloads
     (GUI drag&drop equivalent). Robot/articulation loaders use a separate
     instanceable=False runtime-write exception.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any


DEFAULT_CHARACTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/6.0/Isaac/People/Characters/F_Business_02/F_Business_02.usd"
)


async def safe_load_usd(
    usd_url: str,
    prim_path: str,
    position: list[float] | None = None,
    rotation: list[float] | None = None,
) -> dict[str, Any]:
    """Deadlock-safe USD payload load. Spec §8.4.

    Use for any S3 MDL-heavy asset (warehouse, nova_carter, character skins, ...).
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
        from isaacsim.core.experimental.utils.stage import is_stage_loading
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

    Some Kit builds lack ``UsdContext.is_new_stage_loading()``. Prefer
    ``isaacsim.core.experimental.utils.stage.is_stage_loading`` or
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
        from isaacsim.core.experimental.utils.stage import is_stage_loading
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
_MOTION_LIBRARY_PATH = f"{_CHARS_ROOT}/HumanMotionLibrary"


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
    """Sync spawn with BehaviorAgent/IRA bind — UI thread direct.

    No validation_api dependency — pure Kit SDK + omni.kit.commands.
    Isaac Sim 6.0 Replicator Agent 1.x no longer ships the IRA 0.x
    IRA 0.x CharacterUtil path, so we mirror the 6.0 character loader:
    payload skin → SkelRoot → shared motion library → BehaviorAgent/IRA APIs.

    Returns dict with `prim_path` (parent payload, for delete + Set Cur),
    `skel_root_path` (for BehaviorAgent lookup), and an `anim_graph_bound`
    compatibility flag.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf, Sdf, Usd, UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage")

    # Ensure parent scope
    if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, Sdf.Path(_CHARS_ROOT))

    skin_path = f"{_CHARS_ROOT}/{char_name}"
    omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=omni.usd.get_context(),
        path_to=skin_path,
        asset_path=skin_url,
        prim_path=None,
        instanceable=False,
        select_prim=False,
    )
    _wait_stage_loaded_sync(max_wait_s=15.0)
    skin_prim = stage.GetPrimAtPath(skin_path)
    if not skin_prim.IsValid():
        raise RuntimeError(f"Skin payload failed at {skin_path}")

    xf = UsdGeom.Xformable(skin_prim)
    t_attr = skin_prim.GetAttribute("xformOp:translate")
    if not t_attr.IsValid():
        t_attr = xf.AddTranslateOp()
    pos = list(position or [0.0, 0.0, 0.0])
    t_attr.Set(Gf.Vec3d(float(pos[0]), float(pos[1]), float(pos[2])))
    r_attr = skin_prim.GetAttribute("xformOp:rotateXYZ")
    if not r_attr.IsValid():
        r_attr = xf.AddRotateXYZOp()
    r_attr.Set(Gf.Vec3f(0.0, 0.0, float(yaw)))

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

    motion_library_path = _ensure_motion_library_sync(stage)
    _apply_ira_character_apis_sync(stage, skel_root_path, motion_library_path)

    return {
        "ok": True,
        "prim_path": skin_path,
        "skel_root_path": skel_root_path,
        "anim_graph_bound": True,
        "runtime_backend": "isaacsim.replicator.agent.core.behavior_agent",
    }


async def safe_load_character(
    char_name: str,
    skin_url: str,
    position: list[float] | None = None,
    yaw: float = 0.0,
) -> dict[str, str]:
    """Load character skin and bind Isaac Sim 6.0 BehaviorAgent/IRA APIs.

    `char_name` 은 USD-safe identifier (sanitize 호출자 책임). 이 함수는
    항상 `/World/Characters/<char_name>` 에 배치.
    """
    async def _impl():
        import omni.kit.commands
        import omni.usd
        from pxr import Gf, UsdGeom

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
            UsdGeom.Xform.Define(stage, _CHARS_ROOT)

        sanitized_prim_path = f"{_CHARS_ROOT}/{char_name}"
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=omni.usd.get_context(),
            path_to=sanitized_prim_path,
            asset_path=skin_url,
            prim_path=None,
            instanceable=False,
            select_prim=False,
        )
        await _wait_stage_loading()

        skin_prim = stage.GetPrimAtPath(sanitized_prim_path)
        if not skin_prim.IsValid():
            raise RuntimeError(f"Skin payload failed at {sanitized_prim_path}")

        xf = UsdGeom.Xformable(skin_prim)
        t_attr = skin_prim.GetAttribute("xformOp:translate")
        if not t_attr.IsValid():
            t_attr = xf.AddTranslateOp()
        pos = list(position or [0.0, 0.0, 0.0])
        t_attr.Set(Gf.Vec3d(float(pos[0]), float(pos[1]), float(pos[2])))
        r_attr = skin_prim.GetAttribute("xformOp:rotateXYZ")
        if not r_attr.IsValid():
            r_attr = xf.AddRotateXYZOp()
        r_attr.Set(Gf.Vec3f(0.0, 0.0, float(yaw)))

        skel_root_path = _find_skel_root(stage, sanitized_prim_path)
        if skel_root_path is None:
            raise RuntimeError(f"SkelRoot not found under {sanitized_prim_path}")

        motion_library_path = await _ensure_motion_library(stage)
        await _apply_ira_character_apis(stage, skel_root_path, motion_library_path)

        return {
            "sanitized_prim_path": sanitized_prim_path,
            "skel_root_path": skel_root_path,
            "runtime_backend": "isaacsim.replicator.agent.core.behavior_agent",
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


def _resolve_human_motion_library_url() -> str:
    """Return Replicator Agent 1.x's default human motion library URL."""
    try:
        from omni.metropolis.utils.carb_util import get_value_by_key

        setting_value = get_value_by_key(
            "/exts/isaacsim.replicator.agent/default_human_motion_library_asset"
        )
        if setting_value:
            return str(setting_value)
    except Exception as exc:  # noqa: BLE001
        try:
            import carb
            carb.log_warn(f"[navmesh_playground] motion library setting lookup failed: {exc}")
        except Exception:
            pass

    from isaacsim.storage.native import get_assets_root_path

    assets_root = get_assets_root_path()
    if not assets_root:
        raise RuntimeError("Isaac Sim assets root unresolved.")
    return (
        f"{assets_root.rstrip('/')}/Isaac/People/MotionLibrary/"
        "HumanMotionLibrary.usd"
    )


def _ensure_motion_library_sync(stage) -> str:
    """Sync-create the shared human motion library payload."""
    import omni.kit.commands
    import omni.usd
    from pxr import UsdGeom

    if stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        return _MOTION_LIBRARY_PATH
    if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, _CHARS_ROOT)

    motion_library_url = _resolve_human_motion_library_url()
    omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=omni.usd.get_context(),
        path_to=_MOTION_LIBRARY_PATH,
        asset_path=motion_library_url,
        prim_path=None,
        instanceable=False,
        select_prim=False,
    )
    _wait_stage_loaded_sync(max_wait_s=15.0)
    if not stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        raise RuntimeError(f"Human motion library failed at {_MOTION_LIBRARY_PATH}")
    return _MOTION_LIBRARY_PATH


async def _ensure_motion_library(stage) -> str:
    """Async-create the shared human motion library payload."""
    import omni.kit.commands
    import omni.usd
    from pxr import UsdGeom

    if stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        return _MOTION_LIBRARY_PATH
    if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, _CHARS_ROOT)

    motion_library_url = _resolve_human_motion_library_url()
    omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=omni.usd.get_context(),
        path_to=_MOTION_LIBRARY_PATH,
        asset_path=motion_library_url,
        prim_path=None,
        instanceable=False,
        select_prim=False,
    )
    await _wait_stage_loading()
    if not stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        raise RuntimeError(f"Human motion library failed at {_MOTION_LIBRARY_PATH}")
    return _MOTION_LIBRARY_PATH


def _apply_ira_character_apis_sync(stage, skel_root_path: str, motion_library_path: str) -> None:
    """Apply BehaviorAgent + IRA APIs without advancing the UI update loop."""
    import omni.kit.commands

    skel_prim = stage.GetPrimAtPath(skel_root_path)
    if not skel_prim.IsValid():
        raise RuntimeError(f"Invalid SkelRoot: {skel_root_path}")
    omni.kit.commands.execute(
        "ApplyBehaviorAgentAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
        motion_library_prim_path=motion_library_path,
        motion_library_skeleton_rig="Human",
    )
    omni.kit.commands.execute(
        "ApplyIRACharacterAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
    )


async def _apply_ira_character_apis(stage, skel_root_path: str, motion_library_path: str) -> None:
    """Apply BehaviorAgent + IRA APIs and yield a frame for registration."""
    import omni.kit.app
    import omni.kit.commands

    skel_prim = stage.GetPrimAtPath(skel_root_path)
    if not skel_prim.IsValid():
        raise RuntimeError(f"Invalid SkelRoot: {skel_root_path}")
    omni.kit.commands.execute(
        "ApplyBehaviorAgentAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
        motion_library_prim_path=motion_library_path,
        motion_library_skeleton_rig="Human",
    )
    await omni.kit.app.get_app().next_update_async()
    omni.kit.commands.execute(
        "ApplyIRACharacterAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
    )
    await omni.kit.app.get_app().next_update_async()


async def safe_load_robot(
    prim_path: str,
    usd_url: str,
    position: list[float] | None = None,
) -> dict[str, Any]:
    """Load robot USD. Caller must subsequently:
       1) simulation_play → 1 tick → pause (articulation registry warm-up, T0.9)
       2) SingleArticulation(prim_path).initialize()
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
