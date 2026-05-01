"""Per-cube velocity freezer — NVIDIA stop-and-grasp 핵심.

Robot 이 cube 를 grasp 시도할 때 belt SurfaceVelocity 영향만 cube_path 단위로
차단. freeze() 가 호출된 cube 만 정적; 다른 cube 와 belt 자체는 영향 없음.
thaw() 후 cube 가 belt 위에 있으면 다음 PhysX tick 에 SurfaceVelocity 가 다시
자동 적용 (PhysX surface velocity 동작).
"""
from __future__ import annotations

import carb


_SOURCE = "omni.userext.pickplace"


class CubeFreezer:
    """Stage handle 받아서 cube velocity 를 직접 set / reset.

    Stage 는 omni.usd.get_context().get_stage() 결과; ``__init__`` 에서 받아
    저장. freeze / thaw 모두 동일 stage 사용.
    """

    def __init__(self, stage) -> None:
        self._stage = stage

    def _set_velocities_zero(self, cube_path: str) -> None:
        from pxr import Sdf, UsdPhysics

        prim = self._stage.GetPrimAtPath(Sdf.Path(cube_path))
        if not prim.IsValid():
            carb.log_warn(f"[{_SOURCE}] freezer: prim not found at {cube_path}")
            return
        rb = UsdPhysics.RigidBodyAPI(prim)
        if not rb:
            carb.log_warn(f"[{_SOURCE}] freezer: RigidBodyAPI missing on {cube_path}")
            return
        rb.GetVelocityAttr().Set((0.0, 0.0, 0.0))
        rb.GetAngularVelocityAttr().Set((0.0, 0.0, 0.0))

    def freeze(self, cube_path: str) -> None:
        """grasp 시작: cube velocity 0 — belt 영향 차단."""
        self._set_velocities_zero(cube_path)

    def thaw(self, cube_path: str) -> None:
        """grasp 종료: 명시 reset (box 안 0 유지 / belt 위 PhysX 자동 회복)."""
        self._set_velocities_zero(cube_path)
