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
3. **`CreatePayloadCommand(instanceable=True)`** — `CreateReferenceCommand` 대신 payload 방식. Isaac Sim 5.1 GUI drag&drop 과 동등한 경로

## Copy-paste 레시피

```python
"""Self-contained USD load with deadlock protection.

Drop this helper into any independent Extension that needs to load MDL-heavy
S3 assets (office.usd, warehouse.usd, nova_carter.usd, Biped_Setup.usd, ...).
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
) -> dict[str, Any]:
    """Load a USD reference into the stage with deadlock protection.

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

        # GUI drag&drop 동등 — Payload + instanceable=True
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=ctx,
            path_to=prim_path,
            asset_path=usd_url,
            instanceable=True,
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


async def _wait_stage_loading(max_ticks: int = 1200) -> None:
    """Tick the Kit app until stage loading completes."""
    import omni.kit.app
    import omni.usd

    app = omni.kit.app.get_app()
    ctx = omni.usd.get_context()
    for _ in range(max_ticks):
        if not ctx.is_new_stage_loading() and not ctx.is_new_stage_activation_pending():
            return
        await app.next_update_async()
```

## 사용 예 (독립 Extension 의 button 콜백)

```python
import asyncio
from .safe_load import safe_load_usd

OFFICE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Office/office.usd"
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
- [ ] `.env` `ISAAC_SIM_EXTRA_EXT_IDS` 에 `isaacsim.asset.browser` / `omni.kit.window.content_browser` 가 **없는가**? (S3 crawl thread 경합 방지)
- [ ] `simulation.play` 중에 로드하려 하지 않는가? (timeline advance 가 추가 경합)

## 근거

- `validation_api/services/stage_service.py::load_usd` 에 동일 코드 + docstring
- 2026-04-20 사용자 실증: isaac-sim.bat Kit (Extension 없음) + GUI drag&drop 은 `CreatePayloadCommand(instanceable=True)` 로 성공. Extension 이 load 된 Kit 에서는 FastAPI handler 의 event loop 와 Kit 메인 이벤트 루프가 분리되어 command 가 main loop 에서 실행 안 됨 → `run_coroutine` 필수.
