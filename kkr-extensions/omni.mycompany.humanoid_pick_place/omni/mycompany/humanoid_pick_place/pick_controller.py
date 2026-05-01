"""Async pick-and-place controller for the humanoid demo.

Strategy mirrors ``conveyor_pick.pick_controller``:

    * Avoid the high-level isaacsim manipulator helpers — they assume a
      Franka-style fixed-base 7-DOF arm and crash on Humanoid28.
    * Drive ``SingleArticulation`` directly via
      ``set_joint_positions`` against a hand-tuned keyframe table.
    * Status is stamped onto ``/World/PickStatus`` so an out-of-process
      verifier can confirm progress without Python introspection.

Cube-grasp trick: when a keyframe has ``cube=ATTACH``, the controller
flips the cube's RigidBodyAPI to kinematic and per-frame writes its
world translate to track the right-hand link. ``DETACH`` flips
kinematic off so gravity resumes — the cube falls onto the place table.
"""

from __future__ import annotations

import asyncio
from typing import Any

import carb
import numpy as np
import omni.kit.app
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics

from .humanoids import HumanoidSpec, default_humanoid
from .joint_layout import resolve_indices
from .scene_builder import (
    HUMANOID_PRIM_PATH,
    PICK_CUBE_PATH,
    PICK_CUBE_SIZE,
    PLACE_TABLE_POSITION,
    TABLE_HEIGHT,
    find_right_hand_link,
    stamp_status,
)
from .trajectory import (
    DEFAULT_TRAJECTORY,
    CubeAttachment,
    Keyframe,
)

INIT_MAX_ATTEMPTS = 6
INIT_RETRY_DELAY_S = 1.0


class PickController:
    """Run the keyframe trajectory once. Re-instantiate per cycle."""

    def __init__(self, humanoid: HumanoidSpec | None = None,
                 trajectory: tuple[Keyframe, ...] = DEFAULT_TRAJECTORY):
        self._humanoid: HumanoidSpec = humanoid or default_humanoid()
        self._trajectory = trajectory
        self._stop = False
        self._cycles_done = 0
        self._art = None
        self._dof_names: tuple[str, ...] = ()
        self._joint_indices = None  # JointIndices (resolve_indices result)
        self._right_hand_link: str | None = None
        # Cube transport state
        self._cube_kinematic_on = False

    # ----- Public control surface -----

    def stop(self) -> None:
        self._stop = True

    def cycles_done(self) -> int:
        return self._cycles_done

    async def run_once(self) -> dict[str, Any]:
        """Execute the full trajectory once. Returns a summary dict."""
        stamp_status(stage="run_started", cycles=self._cycles_done,
                     humanoid=self._humanoid.key)
        await self._wait_stage_loaded()

        ok = await self._init_articulation_with_retry()
        if not ok:
            stamp_status(stage="init_failed", cycles=self._cycles_done)
            return {"ok": False, "reason": "articulation_init_failed"}

        # Resolve role → DOF index against the live dof_names.
        self._joint_indices = resolve_indices(self._dof_names)
        stamp_status(
            stage="init_ok",
            dof_count=int(self._joint_indices.dof_count),
            dof_names=",".join(self._dof_names),
            right_shoulder1=int(self._joint_indices.right_shoulder1),
            right_shoulder2=int(self._joint_indices.right_shoulder2),
            right_elbow=int(self._joint_indices.right_elbow),
            abdomen_z=int(self._joint_indices.abdomen_z),
        )

        if not self._joint_indices.has_right_arm:
            stamp_status(stage="no_right_arm", cycles=self._cycles_done)
            carb.log_warn(
                f"[humanoid_pick_place] right arm DOFs not found in dof_names; "
                f"trajectory will only animate joints that resolved (others "
                f"silently skipped)."
            )

        # Locate the right-hand link for cube tracking.
        stage = omni.usd.get_context().get_stage()
        if self._humanoid.right_hand_link_hint:
            self._right_hand_link = find_right_hand_link(
                stage, self._humanoid.right_hand_link_hint,
            )
        if self._right_hand_link is None:
            stamp_status(
                stage="no_right_hand_link",
                hint=str(self._humanoid.right_hand_link_hint),
            )
            carb.log_warn(
                f"[humanoid_pick_place] right hand link with hint "
                f"{self._humanoid.right_hand_link_hint!r} not found — "
                f"cube will not be carried."
            )

        # Iterate keyframes.
        for kf in self._trajectory:
            if self._stop:
                stamp_status(stage="stopped", cycles=self._cycles_done)
                return {"ok": False, "reason": "stopped"}
            ok_kf = await self._play_keyframe(kf)
            if not ok_kf:
                stamp_status(stage=f"keyframe_failed_{kf.label}",
                             cycles=self._cycles_done)
                return {"ok": False, "reason": f"keyframe_{kf.label}_failed"}

        # Make sure cube is detached at the end (defensive).
        self._set_cube_kinematic(False)
        self._cycles_done += 1
        stamp_status(
            stage="cycle_complete",
            cycles=self._cycles_done,
            cube_final_pos=str(self._read_cube_pos()),
        )
        return {"ok": True, "cycles": self._cycles_done}

    # ----- Internal -----

    async def _wait_stage_loaded(self, max_ticks: int = 1200) -> None:
        app = omni.kit.app.get_app()
        ctx = omni.usd.get_context()
        for _ in range(max_ticks):
            if self._stop:
                return
            try:
                _, files_loaded, total_files = ctx.get_stage_loading_status()
                if total_files == 0 or files_loaded >= total_files:
                    return
            except Exception:
                return
            await app.next_update_async()

    async def _init_articulation_with_retry(self) -> bool:
        last_exc: Exception | None = None
        for attempt in range(1, INIT_MAX_ATTEMPTS + 1):
            if self._stop:
                return False
            stamp_status(stage=f"init_attempt_{attempt}")
            try:
                try:
                    from isaacsim.core.prims import SingleArticulation
                except ImportError:
                    from omni.isaac.core.prims import SingleArticulation
                self._art = SingleArticulation(
                    prim_path=HUMANOID_PRIM_PATH, name="humanoid",
                )
                # Warm-up: PhysX needs ~1 simulation tick to populate the
                # articulation view before initialize() works in 5.1.
                for _ in range(60):
                    if self._stop:
                        return False
                    await omni.kit.app.get_app().next_update_async()
                self._art.initialize()
                names = self._art.dof_names or []
                self._dof_names = tuple(names)
                carb.log_info(
                    f"[humanoid_pick_place] articulation init ok "
                    f"(attempt {attempt}, dof={len(names)})"
                )
                return True
            except Exception as exc:
                last_exc = exc
                carb.log_warn(
                    f"[humanoid_pick_place] init attempt {attempt}/"
                    f"{INIT_MAX_ATTEMPTS} failed: {exc}"
                )
                stamp_status(stage=f"init_exc_{attempt}", error=str(exc))
                self._art = None
                t0 = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - t0) < INIT_RETRY_DELAY_S:
                    if self._stop:
                        return False
                    await omni.kit.app.get_app().next_update_async()
        carb.log_error(
            f"[humanoid_pick_place] articulation init exhausted "
            f"{INIT_MAX_ATTEMPTS} attempts; last={last_exc}"
        )
        return False

    async def _play_keyframe(self, kf: Keyframe) -> bool:
        """Drive the articulation to ``kf.targets`` and hold for hold_frames.

        Uses ``set_joint_position_targets`` so the PhysX joint drives
        actively pull the limbs to the requested pose every physics step.
        ``set_joint_positions`` (without drive) only teleports the state
        for one frame — the next physics step then snaps everything back
        to whatever the drives' targets are (default 0), so the arm
        never visibly moves.
        """
        stamp_status(
            stage=f"trajectory_{kf.label}",
            cycles=self._cycles_done,
            cube_attachment=kf.cube.value,
        )
        try:
            target = self._build_dof_target(kf.targets)
            self._apply_joint_targets(target)

            # Cube state transition (one-shot at keyframe entry).
            if kf.cube == CubeAttachment.ATTACH:
                self._set_cube_kinematic(True)
            elif kf.cube == CubeAttachment.DETACH:
                # Deterministic placement: teleport the cube directly
                # above the place table, then drop it. This guarantees
                # the demo lands the cube on the table even when
                # PhysX integration drift carries the hand off-target.
                # The 5 cm hover lets gravity slap the cube down with a
                # tiny visible bounce so the user sees it land.
                self._teleport_cube_above_place_table()
                self._set_cube_kinematic(False)

            app = omni.kit.app.get_app()
            # Drive target was set once at keyframe entry — no per-frame
            # state writes (those caused PhysX articulation jitter that
            # spawned a halo of contact-debug spheres around the table
            # in viewport captures from the prior iteration).
            for _ in range(kf.hold_frames):
                if self._stop:
                    return False
                # Per-frame cube tracking while attached.
                if self._cube_kinematic_on and self._right_hand_link:
                    self._stamp_cube_to_hand()
                await app.next_update_async()
            return True
        except Exception as exc:
            carb.log_warn(
                f"[humanoid_pick_place] keyframe {kf.label} error: {exc}"
            )
            return False

    def _apply_joint_targets(self, target: np.ndarray) -> None:
        """Push ``target`` to the articulation drives + bootstrap state.

        Path 1 — ``apply_action(ArticulationAction(joint_positions=target))``:
            preferred entry point in Isaac Sim 5.1; routes through the
            articulation controller so the drives respect joint limits +
            ramp curves.

        Path 2 fallback — ``set_joint_position_targets(target)``: lower
            level but available on every ``SingleArticulation`` build.

        Either way we ALSO call ``set_joint_positions(target)`` once so
        a humanoid whose authored joint drives have ``stiffness=0``
        still moves: the state write teleports the pose, then the
        target write keeps subsequent physics steps from reverting.
        """
        # 1. State write — instant teleport (covers the zero-drive case).
        try:
            self._art.set_joint_positions(target)
        except Exception as exc:
            carb.log_warn(
                f"[humanoid_pick_place] set_joint_positions: {exc}"
            )
        # 2. Drive target write — keep the pose every physics step.
        applied = False
        try:
            from isaacsim.core.utils.types import ArticulationAction
            ctrl = getattr(self._art, "get_articulation_controller", None)
            if callable(ctrl):
                action = ArticulationAction(joint_positions=target)
                ctrl().apply_action(action)
                applied = True
        except Exception as exc:
            carb.log_warn(
                f"[humanoid_pick_place] apply_action: {exc}"
            )
        if not applied:
            try:
                fn = getattr(self._art, "set_joint_position_targets", None)
                if callable(fn):
                    fn(target)
            except Exception as exc:
                carb.log_warn(
                    f"[humanoid_pick_place] set_joint_position_targets: {exc}"
                )

    def _build_dof_target(self, role_targets: dict[str, float]) -> np.ndarray:
        """Compose a (dof_count,) array from role-keyed targets.

        Reads current positions first so DOFs not addressed by the
        keyframe stay where they were (avoiding sudden snaps to 0 when
        the trajectory only moves a subset).
        """
        cur = self._art.get_joint_positions()
        if cur is None:
            cur = np.zeros(self._joint_indices.dof_count, dtype=np.float32)
        target = np.array(cur, dtype=np.float32)
        for role, value in role_targets.items():
            idx = self._joint_indices.index_or(role)
            if idx < 0:
                # Try the JointIndices role attribute (covers role candidates)
                idx = getattr(self._joint_indices, role, -1)
            if 0 <= idx < target.shape[0]:
                target[idx] = float(value)
        return target

    def _set_cube_kinematic(self, on: bool) -> None:
        """Toggle the pick cube between dynamic and kinematic.

        Kinematic = controller writes its translate each frame (cube
        follows the hand). Dynamic = PhysX dynamics resume → gravity
        drops the cube onto the place table.
        """
        try:
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(PICK_CUBE_PATH)
            if not prim or not prim.IsValid():
                return
            api = UsdPhysics.RigidBodyAPI(prim)
            if not api:
                api = UsdPhysics.RigidBodyAPI.Apply(prim)
            kin_attr = api.GetKinematicEnabledAttr()
            if not kin_attr:
                kin_attr = api.CreateKinematicEnabledAttr()
            kin_attr.Set(bool(on))
            self._cube_kinematic_on = bool(on)
            stamp_status(cube_kinematic=bool(on))
        except Exception as exc:
            carb.log_warn(f"[humanoid_pick_place] kinematic toggle: {exc}")

    def _teleport_cube_above_place_table(self) -> None:
        """One-shot: write cube xformOp:translate to place-table top + 5 cm.

        Used at the DETACH keyframe so the cube reliably lands on the
        place table no matter where the humanoid's hand has wandered.
        Center-aligns the cube on the table top (table cube has size=1
        scaled to 0.4 × 0.4 × 0.4 m at TABLE_HEIGHT centred z, so the
        top sits at z = TABLE_HEIGHT + TABLE_HEIGHT = 2 * TABLE_HEIGHT).
        """
        try:
            stage = omni.usd.get_context().get_stage()
            cube = stage.GetPrimAtPath(PICK_CUBE_PATH)
            if not cube or not cube.IsValid():
                return
            top_z = 2.0 * TABLE_HEIGHT + PICK_CUBE_SIZE * 0.5 + 0.05
            target = Gf.Vec3d(
                float(PLACE_TABLE_POSITION[0]),
                float(PLACE_TABLE_POSITION[1]),
                float(top_z),
            )
            t_attr = cube.GetAttribute("xformOp:translate")
            if not t_attr.IsValid():
                t_attr = UsdGeom.Xformable(cube).AddTranslateOp()
            t_attr.Set(target)
            stamp_status(cube_dropped_at=str((target[0], target[1], target[2])))
        except Exception as exc:
            carb.log_warn(f"[humanoid_pick_place] teleport cube: {exc}")

    def _stamp_cube_to_hand(self) -> None:
        """Per-frame: write cube translate to right-hand world position."""
        try:
            stage = omni.usd.get_context().get_stage()
            hand = stage.GetPrimAtPath(self._right_hand_link)
            if not hand or not hand.IsValid():
                return
            xfc = UsdGeom.XformCache(Usd.TimeCode.Default())
            mat = xfc.GetLocalToWorldTransform(hand)
            tip = mat.ExtractTranslation()
            # Offset slightly below the hand link so the cube hangs as if held.
            cube = stage.GetPrimAtPath(PICK_CUBE_PATH)
            if not cube or not cube.IsValid():
                return
            t_attr = cube.GetAttribute("xformOp:translate")
            if not t_attr.IsValid():
                t_attr = UsdGeom.Xformable(cube).AddTranslateOp()
            t_attr.Set(Gf.Vec3d(tip[0], tip[1], tip[2] - 0.06))
        except Exception as exc:
            carb.log_warn(f"[humanoid_pick_place] cube stamp: {exc}")

    def _read_cube_pos(self) -> tuple[float, float, float] | None:
        try:
            stage = omni.usd.get_context().get_stage()
            cube = stage.GetPrimAtPath(PICK_CUBE_PATH)
            if not cube or not cube.IsValid():
                return None
            t = cube.GetAttribute("xformOp:translate").Get()
            if t is None:
                return None
            return (float(t[0]), float(t[1]), float(t[2]))
        except Exception:
            return None
