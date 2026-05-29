"""Programmatic self-test — verifies the full transmission contract against
the currently loaded stage and stamps ``/OfficeMcp/SelfTestResult`` customData.

Mirrors the robot_lidar / stage_annotator self-test pattern. Run from a live
Kit after Load Scene::

    kit_python_run(code="import omni.office_mcp.network_demo.selftest as st; st.run()")
    # then read /OfficeMcp/SelfTestResult customData once it has been stamped

IMPORTANT — async by design: when office.usd is loaded, driving shader emissive
in a *tight synchronous loop* starves the Kit main loop of the ticks that the
MDL resolver / Hydra need, which deadlocks kit.exe (~92 s). So the test runs as
a coroutine that ``await``s ``next_update_async()`` between emissive writes —
the same naturally tick-separated pattern the extension's per-frame update uses.
``run()`` schedules it and returns immediately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from . import scene_tags
from .transmission import STATUS_DELIVERED, TransmissionController, WaveModel


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def run() -> dict[str, Any]:
    """Schedule the async self-test on the Kit main loop. Returns immediately."""
    import omni.kit.async_engine

    omni.kit.async_engine.run_coroutine(_run_async())
    return {"scheduled": True}


async def _run_async() -> dict[str, Any]:
    import carb
    import omni.kit.app
    import omni.usd

    app = omni.kit.app.get_app()
    checks: list[CheckResult] = []
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return _stamp(None, [CheckResult("stage_present", False, "no stage")])

    # 1. Tag discovery (read-only, safe).
    tags = scene_tags.discover(stage)
    checks.append(CheckResult(
        "tags_discovered", tags.ok,
        detail=(
            f"trigger={tags.trigger} switch={tags.switch} "
            f"cables={len(tags.cables)} servers={len(tags.server_leds)} "
            f"missing={tags.missing()}"
        ),
    ))

    # 2. Emissive inputs bind (one _apply -> yield a tick).
    ctrl = TransmissionController()
    bound = False
    try:
        bound = ctrl.bind(stage, tags)
        await app.next_update_async()
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("bind_emissive_inputs", False, str(exc)))
    checks.append(CheckResult("bind_emissive_inputs", bool(bound)))

    # 3. Pure wave model: sequential LED order + delivered transition.
    try:
        model = WaveModel(len(tags.cables), tags.server_led_orders, duration=1.0)
        model.start()
        seq: list[int] = []
        for _ in range(20):
            seq.append(model.lit_count())
            model.advance(0.1)
        monotonic = all(b >= a for a, b in zip(seq, seq[1:]))
        checks.append(CheckResult("wave_sequential_monotonic", monotonic, detail=f"seq={seq}"))
        checks.append(CheckResult(
            "wave_delivered_all_servers",
            model.status == STATUS_DELIVERED and model.lit_count() == len(tags.server_leds),
            detail=f"status={model.status} lit={model.lit_count()}/{len(tags.server_leds)}",
        ))
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("wave_model", False, str(exc)))

    # 4. Drive the *real* controller through delivered, yielding a tick between
    #    each emissive write, then read back a cable's emissiveColor.
    try:
        if ctrl.model is not None:
            ctrl.start()
            await app.next_update_async()
            for _ in range(12):
                ctrl.on_update(0.3)
                await app.next_update_async()
            cable_glow = _max_cable_emissive(stage, tags)
            checks.append(CheckResult(
                "cable_emissive_authored", cable_glow > 0.01,
                detail=f"max cable emissive={cable_glow:.3f}",
            ))
        else:
            checks.append(CheckResult("cable_emissive_authored", False, "controller not bound"))
    except Exception as exc:  # noqa: BLE001
        checks.append(CheckResult("cable_emissive_authored", False, str(exc)))

    # Leave the cables off again so the stamp doesn't leave the scene lit.
    try:
        ctrl.reset_visuals()
        await app.next_update_async()
    except Exception:  # noqa: BLE001
        pass

    summary = _stamp(stage, checks)
    carb.log_warn(f"[office_mcp.selftest] {summary['passed']}/{summary['total']} passed")
    return summary


def _max_cable_emissive(stage, tags) -> float:
    from pxr import UsdShade

    best = 0.0
    for cable in tags.cables:
        prim = stage.GetPrimAtPath(cable.path)
        if not prim or not prim.IsValid():
            continue
        mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if not mat:
            continue
        shader = mat.ComputeSurfaceSource()[0]
        if not shader:
            continue
        inp = shader.GetInput("emissiveColor")
        if not inp:
            continue
        val = inp.Get()
        if val is not None:
            best = max(best, float(max(val[0], val[1], val[2])))
    return best


def _stamp(stage, checks: list[CheckResult]) -> dict[str, Any]:
    summary = {
        "ok": all(c.ok for c in checks),
        "total": len(checks),
        "passed": sum(1 for c in checks if c.ok),
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
    }
    if stage is None:
        return summary
    import omni.kit.commands

    path = "/OfficeMcp/SelfTestResult"
    if not stage.GetPrimAtPath(path).IsValid():
        omni.kit.commands.execute(
            "CreatePrimWithDefaultXformCommand", prim_type="Xform", prim_path=path,
        )
    prim = stage.GetPrimAtPath(path)
    prim.SetCustomDataByKey("selftest_ok", bool(summary["ok"]))
    prim.SetCustomDataByKey("selftest_total", int(summary["total"]))
    prim.SetCustomDataByKey("selftest_passed", int(summary["passed"]))
    prim.SetCustomDataByKey("selftest_json", json.dumps(summary))
    for c in checks:
        prim.SetCustomDataByKey(f"check_{c.name}_ok", bool(c.ok))
        if c.detail:
            prim.SetCustomDataByKey(f"check_{c.name}_detail", c.detail)
    return summary
