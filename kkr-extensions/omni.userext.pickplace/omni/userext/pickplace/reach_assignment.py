"""Franka 좌표 기반 거리 분담 + reservation lock.

v5 — ㅁ rounded loop 으로 변경되면서 v4 의 좌우-x 분리 로직 (x<0→A, x>0→B)
이 깨짐 (ConveyorBuilder anchor chain origin 기준이라 4 STRAIGHT 모두 비대칭
좌표 가능). 거리 기반: 각 robot 의 (x,y) 좌표에서 cube 까지 horizontal
distance 가 reach_radius 이내인 robot 이 zone 소유. 둘 다 안 닿으면 None.

Construction: ``ReachAssigner(franka_a_pos, franka_b_pos, reach_radius=1.0)``
where positions are ``(x,y,z)`` tuples (z 무시). Default reach 1.0 m =
Franka Panda spec 1.27 m 의 안전 마진.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Tuple


class RobotZone(Enum):
    A = "franka_A"
    B = "franka_B"


class ReachAssigner:
    def __init__(
        self,
        franka_a_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        franka_b_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        reach_radius: float = 1.0,
    ) -> None:
        self.franka_a_xy = (float(franka_a_pos[0]), float(franka_a_pos[1]))
        self.franka_b_xy = (float(franka_b_pos[0]), float(franka_b_pos[1]))
        self.reach_radius_sq = float(reach_radius) ** 2
        self._locks: Dict[str, str] = {}

    def zone_for(self, cube_pos: Tuple[float, float, float]) -> Optional[RobotZone]:
        cx, cy = float(cube_pos[0]), float(cube_pos[1])
        dax = cx - self.franka_a_xy[0]
        day = cy - self.franka_a_xy[1]
        dbx = cx - self.franka_b_xy[0]
        dby = cy - self.franka_b_xy[1]
        da_sq = dax * dax + day * day
        db_sq = dbx * dbx + dby * dby
        # 둘 다 reach 밖 → 어느 robot 도 못 잡음 (cube 그대로 흘러감)
        if da_sq > self.reach_radius_sq and db_sq > self.reach_radius_sq:
            return None
        # 가장 가까운 robot 에게 할당
        return RobotZone.A if da_sq <= db_sq else RobotZone.B

    def try_lock(self, robot_id: str, cube_path: str) -> bool:
        existing = self._locks.get(cube_path)
        if existing is not None and existing != robot_id:
            return False
        self._locks[cube_path] = robot_id
        return True

    def release(self, robot_id: str, cube_path: str) -> None:
        if self._locks.get(cube_path) == robot_id:
            del self._locks[cube_path]

    def locked_by(self, cube_path: str) -> Optional[str]:
        return self._locks.get(cube_path)

    def reset(self) -> None:
        self._locks.clear()
