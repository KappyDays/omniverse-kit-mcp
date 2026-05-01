"""Per-cube FixedJoint attach — explicit grasp hold during pick-place cycle.

v4 Task 9 라이브 검증 결과 ParallelGripper.close() 만으로는 5cm cube 에 대해
충분한 contact friction 을 만들지 못해 cube 가 실제로 들리지 않음 (rate=0%).
v3 SurfaceGripper 가 사용한 ``UsdPhysics.FixedJoint`` 를 grasp phase 동안만
명시적으로 만들어 cube 를 panda_hand 에 묶고, release phase 에서 떼어냄.

NVIDIA PickPlaceController phase mapping:
    3 = PHASE_3_CLOSE_GRIPPER_AND_GRASP  → attach
    7 = PHASE_7_OPEN_GRIPPER             → detach
"""
from __future__ import annotations

import carb


_SOURCE = "omni.userext.pickplace"


class CubeAttach:
    """Stage handle 받아서 cube ↔ panda_hand FixedJoint 를 동적으로 생성/삭제.

    내부 dict 로 cube_path → joint_path 매핑 유지 → idempotent attach 보장
    + detach 시 joint_path 자동 회수.
    """

    def __init__(self, stage) -> None:
        self._stage = stage
        self._joints: dict[str, str] = {}

    def attach(self, cube_path: str, panda_hand_path: str) -> None:
        """cube ↔ panda_hand FixedJoint 생성. 이미 attach 됐으면 noop."""
        from pxr import Sdf, UsdPhysics

        if cube_path in self._joints:
            return
        cube_prim = self._stage.GetPrimAtPath(Sdf.Path(cube_path))
        hand_prim = self._stage.GetPrimAtPath(Sdf.Path(panda_hand_path))
        if not cube_prim.IsValid() or not hand_prim.IsValid():
            carb.log_warn(
                f"[{_SOURCE}] attach skipped — invalid prim: cube={cube_path} hand={panda_hand_path}"
            )
            return
        joint_name = cube_path.replace("/", "_").lstrip("_") + "_GraspJoint"
        joint_path = f"{panda_hand_path}/{joint_name}"
        joint = UsdPhysics.FixedJoint.Define(self._stage, Sdf.Path(joint_path))
        joint.CreateBody0Rel().SetTargets([panda_hand_path])
        joint.CreateBody1Rel().SetTargets([cube_path])
        self._joints[cube_path] = joint_path
        carb.log_warn(f"[{_SOURCE}] attach {cube_path} ↔ {panda_hand_path} via {joint_path}")

    def detach(self, cube_path: str) -> None:
        """cube 의 FixedJoint 삭제. attach 이력 없으면 noop."""
        joint_path = self._joints.pop(cube_path, None)
        if joint_path is None:
            return
        try:
            import omni.kit.commands
            omni.kit.commands.execute("DeletePrims", paths=[joint_path])
            carb.log_warn(f"[{_SOURCE}] detach {cube_path} ({joint_path})")
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] detach failed for {cube_path}: {exc!r}")

    def reset(self) -> None:
        """모든 joint 삭제 (extension reset 시)."""
        for cube_path in list(self._joints.keys()):
            self.detach(cube_path)
