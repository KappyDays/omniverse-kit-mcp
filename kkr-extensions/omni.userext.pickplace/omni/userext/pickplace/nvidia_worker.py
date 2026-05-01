"""Per-Franka stop-and-grasp cycle worker (NVIDIA wiring).

매 physics step `tick(now)` 호출. 첫 호출에 ZoneSelector 로 cube 한 개
reserve → CubeFreezer.freeze → controller.reset → controller.forward 1 step.
이후 호출은 controller.forward 만 반복; controller.is_done() 시 thaw +
unreserve + target 해제 → 다음 cube 로 전환.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np


# NVIDIA PickPlaceController 가 요구하는 EE quaternion (downward, [w,x,y,z]).
DOWNWARD_QUAT = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

# NVIDIA PickPlaceController phase 매핑 — base_class PickPlaceController.events:
#   3 = PHASE_3_CLOSE_GRIPPER_AND_GRASP  → cube ↔ panda_hand FixedJoint attach
#   7 = PHASE_7_OPEN_GRIPPER             → FixedJoint detach
PHASE_GRASP_ATTACH = 3
PHASE_GRASP_DETACH = 7


class NVIDIAPickPlaceWorker:
    def __init__(
        self,
        *,
        robot_id: str,
        franka,
        controller,
        art_ctrl,
        zone_selector,
        freezer,
        phase_log,
        cube_attach,
        panda_hand_path: str,
        box_pos: np.ndarray,
        cube_pos_resolver: Callable[[str], np.ndarray],
    ) -> None:
        self.robot_id = robot_id
        self._franka = franka
        self._controller = controller
        self._art_ctrl = art_ctrl
        self._selector = zone_selector
        self._freezer = freezer
        self._log = phase_log
        self._attach = cube_attach
        self._panda_hand_path = panda_hand_path
        self._box_pos = np.asarray(box_pos, dtype=np.float32)
        self._cube_pos = cube_pos_resolver
        self.target_cube: Optional[str] = None
        self._attached: bool = False

    def tick(self, now: float) -> None:
        if self.target_cube is None:
            cube_path = self._selector.next_target(self.robot_id)
            if cube_path is None:
                return
            self.target_cube = cube_path
            self._attached = False
            self._freezer.freeze(cube_path)
            self._controller.reset()
            self._log.event(
                "cycle_start", t=now, robot_id=self.robot_id, cube_path=cube_path
            )

        cube_pos = self._cube_pos(self.target_cube)
        joint_pos = self._franka.get_joint_positions()
        action = self._controller.forward(
            picking_position=cube_pos,
            placing_position=self._box_pos,
            current_joint_positions=joint_pos,
            end_effector_orientation=DOWNWARD_QUAT,
        )
        self._art_ctrl.apply_action(action)
        phase = self._controller.get_current_event()
        self._log.event_phase(t=now, robot_id=self.robot_id, phase=phase)

        # Phase-driven attach/detach. Phase >= 3 means gripper has closed
        # around the cube → bind cube to panda_hand via FixedJoint so v4
        # actually carries the cube (ParallelGripper friction alone
        # insufficient — Task 9 finding). Phase >= 7 means gripper opens
        # → release at bin.
        if (
            not self._attached
            and self.target_cube is not None
            and phase >= PHASE_GRASP_ATTACH
            and phase < PHASE_GRASP_DETACH
        ):
            self._attach.attach(self.target_cube, self._panda_hand_path)
            self._attached = True
        elif (
            self._attached
            and self.target_cube is not None
            and phase >= PHASE_GRASP_DETACH
        ):
            self._attach.detach(self.target_cube)
            self._attached = False

        if self._controller.is_done():
            # Safety net: if cycle ends while still attached (e.g., is_done
            # fires before phase 7), force detach to prevent cube leaking
            # into next cycle.
            if self._attached and self.target_cube is not None:
                self._attach.detach(self.target_cube)
                self._attached = False
            self._freezer.thaw(self.target_cube)
            self._selector.unreserve(self.target_cube)
            self._log.event(
                "cycle_done",
                t=now,
                robot_id=self.robot_id,
                cube_path=self.target_cube,
            )
            self.target_cube = None

    def reset_state(self) -> None:
        """on_reset 시 호출 — target 해제. cube freeze/thaw + attach 정리는
        caller (extension._on_reset) 책임."""
        self.target_cube = None
        self._attached = False
        try:
            self._controller.reset()
        except Exception:
            pass
