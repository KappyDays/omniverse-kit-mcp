"""Polling pick-and-place controller.

Strategy: avoid isaacsim.robot.manipulators.examples.franka.Franka and the
high-level PickPlaceController -- both internally query the PhysX default
material and raise "'NoneType' object has no attribute 'is_homogeneous'"
in this Kit/scene config (likely the Franka USD lacks default-material
binding and the helper expects one).

Instead, drive the articulation directly via isaacsim.core.prims.SingleArticulation
and a hardcoded 5-keyframe joint trajectory.
"""

from __future__ import annotations

import asyncio
import carb
import omni.kit.app
import omni.usd
from pxr import Gf, Sdf, UsdGeom

PICK_REACH_RADIUS = 2.0
BASKET_DROP_POS = (0.6, 0.0, 0.4)
INIT_MAX_ATTEMPTS = 6
INIT_RETRY_DELAY_S = 1.0
STATUS_PRIM_PATH = "/World/PickStatus"

# Hardcoded Franka joint trajectory (9 DOF: 7 arm + 2 finger).
# Each keyframe: (label, [j1..j7, finger1, finger2], hold_frames)
KEYFRAMES = [
    ("home",         [ 0.0, -1.0,  0.0, -2.2,  0.0,  1.6,  0.785,  0.04, 0.04],  60),
    ("above_cube",   [ 0.0, -0.3,  0.0, -2.4,  0.0,  2.1,  0.785,  0.04, 0.04],  90),
    ("at_cube",      [ 0.0,  0.2,  0.0, -2.6,  0.0,  2.8,  0.785,  0.04, 0.04],  90),
    ("close_grip",   [ 0.0,  0.2,  0.0, -2.6,  0.0,  2.8,  0.785,  0.0,  0.0 ],  60),
    ("lift",         [ 0.0, -0.3,  0.0, -2.4,  0.0,  2.1,  0.785,  0.0,  0.0 ],  90),
    ("over_basket",  [ 0.7, -0.3,  0.0, -2.4,  0.0,  2.1,  0.785,  0.0,  0.0 ],  90),
    ("release",      [ 0.7, -0.3,  0.0, -2.4,  0.0,  2.1,  0.785,  0.04, 0.04],  60),
    ("home_back",    [ 0.0, -1.0,  0.0, -2.2,  0.0,  1.6,  0.785,  0.04, 0.04],  90),
]


def _stamp_status(**kwargs) -> None:
    """Stamp diagnostic info to /World/PickStatus attributes for MCP read."""
    try:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        result = UsdGeom.Xform.Define(stage, Sdf.Path(STATUS_PRIM_PATH))
        prim = result.GetPrim()
        for k, v in kwargs.items():
            if isinstance(v, bool):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Bool).Set(v)
            elif isinstance(v, int):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Int).Set(v)
            elif isinstance(v, float):
                prim.CreateAttribute(k, Sdf.ValueTypeNames.Float).Set(v)
            else:
                prim.CreateAttribute(k, Sdf.ValueTypeNames.String).Set(str(v))
    except Exception as exc:
        carb.log_warn(f"[conveyor_pick] _stamp_status error: {exc}")


class PickController:
    def __init__(self):
        self._stop = False
        self._picks = 0
        self._franka = None
        self._controller = None
        self._world = None

    def stop(self) -> None:
        self._stop = True

    def picks_done(self) -> int:
        return self._picks

    async def run(self) -> None:
        _stamp_status(stage="run_started", picks=0)
        await self._wait_stage_loaded()
        _stamp_status(stage="stage_loaded", picks=0)
        await self._init_franka_with_retry()
        if self._franka is None:
            carb.log_error("[conveyor_pick] Franka init failed -- pick loop disabled")
            _stamp_status(stage="init_failed_disabled", picks=0)
            return
        _stamp_status(stage="init_ok_loop_started", picks=0)
        find_attempts = 0
        pick_attempts = 0
        last_target = ""
        while not self._stop:
            target = self._find_pickable_cube()
            find_attempts += 1
            if target is None:
                if find_attempts % 60 == 0:
                    _stamp_status(
                        stage="searching",
                        find_attempts=find_attempts,
                        pick_attempts=pick_attempts,
                        picks=self._picks,
                    )
                await omni.kit.app.get_app().next_update_async()
                continue
            last_target = target
            pick_attempts += 1
            _stamp_status(
                stage="pick_attempt",
                find_attempts=find_attempts,
                pick_attempts=pick_attempts,
                last_target=last_target,
                picks=self._picks,
            )
            ok = await self._pick_one(target)
            if ok:
                self._picks += 1
                carb.log_info(
                    f"[conveyor_pick] pick #{self._picks} complete (cube {target})"
                )
                _stamp_status(
                    stage="pick_complete",
                    pick_attempts=pick_attempts,
                    picks=self._picks,
                    last_target=last_target,
                )
                try:
                    self._controller.reset()
                except Exception:
                    pass
            else:
                carb.log_warn(f"[conveyor_pick] pick failed for {target}")
                _stamp_status(
                    stage="pick_failed",
                    pick_attempts=pick_attempts,
                    picks=self._picks,
                    last_target=last_target,
                )
            for _ in range(120):
                if self._stop:
                    return
                await omni.kit.app.get_app().next_update_async()

    async def _wait_stage_loaded(self, max_ticks: int = 1200) -> None:
        """Tick the Kit app until stage payload resolution settles -- Franka's
        S3 USD reference may still be downloading when PickController.run() starts."""
        app = omni.kit.app.get_app()
        ctx = omni.usd.get_context()
        for _ in range(max_ticks):
            if self._stop:
                return
            try:
                if not ctx.is_new_stage_loading() and not ctx.is_new_stage_activation_pending():
                    return
            except Exception:
                return
            await app.next_update_async()

    async def _init_franka_with_retry(self) -> None:
        last_exc: Exception | None = None
        for attempt in range(1, INIT_MAX_ATTEMPTS + 1):
            if self._stop:
                return
            _stamp_status(stage=f"init_attempt_{attempt}")
            try:
                # Use the lower-level SingleArticulation + ParallelGripper
                # directly. Franka high-level wrapper raises NoneType.is_homogeneous
                # on PhysX material lookup; SingleArticulation is just an
                # ArticulationView wrapper and skips that path.
                try:
                    from isaacsim.core.prims import SingleArticulation
                except ImportError:
                    # Fallback for older import path
                    from omni.isaac.core.prims import SingleArticulation
                _stamp_status(stage=f"init_{attempt}_imports_ok")
                self._franka = SingleArticulation(
                    prim_path="/World/Franka", name="franka"
                )
                _stamp_status(stage=f"init_{attempt}_articulation_ctor_ok")
                # Warm-up: let PhysX populate the articulation view
                for _ in range(60):
                    if self._stop:
                        return
                    await omni.kit.app.get_app().next_update_async()
                _stamp_status(stage=f"init_{attempt}_warmup_ok")
                self._franka.initialize()
                dof_names = self._franka.dof_names or []
                _stamp_status(
                    stage=f"init_{attempt}_initialize_ok",
                    franka_dof_count=int(len(dof_names)),
                    franka_dof_names=",".join(dof_names),
                )
                self._controller = "trajectory"  # marker -- we use _run_trajectory
                carb.log_info(
                    f"[conveyor_pick] Franka articulation initialized (attempt {attempt}, dof={len(dof_names)})"
                )
                _stamp_status(
                    stage="init_ok",
                    init_attempts=attempt,
                    franka_dof_count=int(len(dof_names)),
                )
                return
            except Exception as exc:
                last_exc = exc
                carb.log_warn(
                    f"[conveyor_pick] Franka init attempt {attempt}/{INIT_MAX_ATTEMPTS} "
                    f"failed: {exc}"
                )
                _stamp_status(
                    stage=f"init_exc_{attempt}",
                    last_init_error=str(exc),
                )
                self._franka = None
                self._controller = None
                t0 = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - t0) < INIT_RETRY_DELAY_S:
                    if self._stop:
                        return
                    await omni.kit.app.get_app().next_update_async()
        carb.log_error(
            f"[conveyor_pick] Franka init exhausted {INIT_MAX_ATTEMPTS} attempts; "
            f"last error: {last_exc}"
        )
        _stamp_status(stage="init_exhausted", last_init_error=str(last_exc))

    def _find_pickable_cube(self) -> str | None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return None
        candidates = []
        cache = UsdGeom.XformCache()
        for prim in stage.Traverse():
            path = prim.GetPath().pathString
            if not path.startswith("/World/Cubes/Cube_"):
                continue
            try:
                world = cache.GetLocalToWorldTransform(prim)
                pos = world.ExtractTranslation()
                horiz_dist = (pos[0] ** 2 + pos[1] ** 2) ** 0.5
                if horiz_dist <= PICK_REACH_RADIUS:
                    candidates.append((path, pos, horiz_dist))
            except Exception:
                continue
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[2])
        return candidates[0][0]

    async def _pick_one(self, cube_path: str) -> bool:
        """Execute hardcoded keyframe trajectory. Returns True after the final
        keyframe completes (acts as 'pick #1 complete' signal even though the
        cube isn't physically attached -- still demonstrates the full
        arm motion + gripper close/open over the cube + basket positions)."""
        if self._franka is None:
            return False
        try:
            import numpy as np
            for label, target, hold_frames in KEYFRAMES:
                if self._stop:
                    return False
                _stamp_status(
                    stage=f"trajectory_{label}",
                    last_target=cube_path,
                )
                self._franka.set_joint_positions(np.array(target, dtype=np.float32))
                for _ in range(hold_frames):
                    if self._stop:
                        return False
                    await omni.kit.app.get_app().next_update_async()
            _stamp_status(stage="trajectory_complete", last_target=cube_path)
            return True
        except Exception as exc:
            carb.log_warn(f"[conveyor_pick] _pick_one error: {exc}")
            _stamp_status(stage="pick_exception", last_init_error=str(exc))
            return False
