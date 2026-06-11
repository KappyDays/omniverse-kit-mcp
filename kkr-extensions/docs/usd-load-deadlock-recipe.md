<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 독립 Extension 이 MDL-heavy S3 asset 을 로드할 때 복사해 쓰는 방어 코드 -->

# USD Load Deadlock Recipe

## 언제 필요한가

독립 Extension 이 S3 에서 **MDL-heavy asset** (office.usd, warehouse.usd, nova_carter.usd 등) 을 stage 에 로드해야 할 때. 그냥 `omni.kit.commands.execute("CreatePayloadCommand", ...)` 만 호출하면 학생 PC 에서 **kit.exe 가 92 초 freeze** 후 timeout — 증상:

- viewport 검은 화면
- UI 완전 무반응
- Kit Console 에 아무 에러 없음 (silent hang)

근본 원인: OmniUsdResolver 의 **MDL material 재조회 스레드** 가 `carb.logging` 콜백 스레드와 GIL 경합해 Kit 메인 이벤트 루프 정지. FastAPI handler / UI 콜백의 asyncio 루프도 동시 정지.

## 방어 3 요소

1. **`log_capture` 비활성화** — `carb.logging.acquire_logging().add_logger(cb)` 를 kit.exe 가동 중 켜두면 MDL resolver loop 이 carb thread 와 경합. Extension `on_startup` 에서는 `_log_capture = None` 유지 (request-scoped 로 켰다 끄는 구조로만 허용)
2. **`omni.kit.async_engine.run_coroutine` + `asyncio.wrap_future`** — FastAPI handler / UI 콜백의 event loop 와 Kit 메인 이벤트 루프는 분리되어 있음. 명령을 Kit 메인 루프에 명시 schedule 후, caller 는 `wrap_future` 로 await
3. **`CreatePayloadCommand`** — `CreateReferenceCommand` 대신 payload 방식. Isaac Sim GUI drag&drop 과 동등한 경로. Static payload 는 `instanceable=True`; robot/articulation payload 처럼 runtime traversal/write 가 필요한 outer payload 는 `instanceable=False`.
4. **MDL-payload 씬은 `stage_open`/`open_stage`(LoadAll) 로 열지 말 것** — nested office.usd MDL 을 동기 해소하다 92s deadlock (office 세션 실증). 반드시 **fresh stage + `CreatePayloadCommand` 경로**로만 로드.

## Copy-paste 레시피

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
    from pxr import Gf, UsdGeom

    usd_url = usd_url.replace("\\", "/")  # USD wants forward slashes

    async def _main_loop_impl():
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        # Parent must be a DEFINED prim. CreatePayloadCommand(path_to="/World/X")
        # auto-creates the parent "/World" as an `over` (no defining specifier);
        # an undefined ancestor prunes the whole subtree from the default-predicate
        # Traverse() AND from Hydra rendering (black viewport, tags unreachable).
        from pxr import Sdf
        parent_path = Sdf.Path(prim_path).GetParentPath()
        if not parent_path.isEmpty and parent_path != Sdf.Path.absoluteRootPath:
            UsdGeom.Xform.Define(stage, parent_path)

        # GUI drag&drop equivalent — Payload + instanceable.
        # instanceable=True locks the payload into an instance prototype:
        # great for STATIC heavy nested payloads (office.usd), but it makes
        # prims unreachable to stage.Traverse() and un-editable. If THIS load
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

        # 대형 asset loading 완료까지 대기 (main loop 에서 tick 진행 가능)
        await _wait_stage_loading()

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Prim not created at {prim_path}")

        # Position / rotation 적용
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

    # 핵심: Kit main loop 에 명시 schedule + wrap_future 로 await
    future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
    return await asyncio.wrap_future(future)


async def _wait_stage_loading(max_frames: int = 600) -> None:
    """Tick the Kit app until stage loading completes.

    Some Kit builds lack ``is_new_stage_loading`` /
    ``is_new_stage_activation_pending``. Prefer
    ``isaacsim.core.experimental.utils.stage.is_stage_loading`` when present,
    with ``get_stage_loading_status() -> (msg, files_loaded, total_files)`` as
    fallback.
    """
    import omni.kit.app  # lazy
    import omni.usd

    app = omni.kit.app.get_app()
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

## 사용 예 (독립 Extension 의 button 콜백)

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

## 함정 체크리스트

- [ ] Extension `on_startup` 에서 `carb.logging.add_logger()` 호출하지 않는가?
- [ ] USD url 은 forward slash (`/`) 인가? (backslash 는 MDL resolver 가 이상하게 해석)
- [ ] `log_capture` 를 request-scoped 외에 상시 활성화하지 않는가? Browser/content-browser presence 자체는 blocker 가 아니며 root cause 로 보지 않는다.
- [ ] `simulation.play` 중에 로드하려 하지 않는가? (timeline advance 가 추가 경합)
- [ ] 런타임에 편집/순회할 prim 이 있으면 outer 로드는 `instanceable=False` 인가? (True 면 instance prototype 에 갇혀 Traverse 미도달)
- [ ] payload 부모 prim 을 로드 전에 `UsdGeom.Xform.Define` 로 def 화했는가? (over 부모는 subtree prune)

## 근거

- `validation_api/services/stage_service.py::load_usd` 에 동일 코드 + docstring
- 2026-04-20 사용자 실증: isaac-sim.bat Kit (Extension 없음) + GUI drag&drop 은 `CreatePayloadCommand(instanceable=True)` 로 static asset load 성공. Extension 이 load 된 Kit 에서는 FastAPI handler 의 event loop 와 Kit 메인 이벤트 루프가 분리되어 command 가 main loop 에서 실행 안 됨 → `run_coroutine` 필수.
- 2026-06-10 Isaac Sim 6.0 robot live 실증: `robot_load` 는 같은 payload 패턴을 쓰되 `instanceable=False` + active job 거부 + timeline stop 이 필요. active navigation job 중 새 robot payload load 시 Kit/PhysX crash 재현.
