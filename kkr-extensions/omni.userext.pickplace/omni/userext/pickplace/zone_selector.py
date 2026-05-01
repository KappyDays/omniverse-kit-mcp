"""ReachAssigner wrapper + cube state cache.

Worker 가 매 tick `next_target(robot_id)` 한 번 호출하면 zone-allowed +
미예약 cube 중 하나를 reserve 후 path 반환. 동시에 두 worker 가 호출해도
ReachAssigner.try_lock 의 mutual exclusion 으로 race 안전.
"""
from __future__ import annotations

from typing import Optional

from .reach_assignment import ReachAssigner, RobotZone


class ZoneSelector:
    def __init__(self, assigner: ReachAssigner) -> None:
        self._assigner = assigner
        self._cubes_cache: list[dict] = []

    def update(self, cubes: list[dict]) -> None:
        """매 tick `cube_spawner.list_cubes()` 결과를 갱신."""
        self._cubes_cache = list(cubes)

    def next_target(self, robot_id: str) -> Optional[str]:
        """robot_id 의 zone 에 속하면서 미예약 cube 한 개 reserve + path 반환."""
        target_zone = RobotZone.A if robot_id == "franka_A" else RobotZone.B
        for cube in self._cubes_cache:
            zone = self._assigner.zone_for(cube["pos"])
            if zone != target_zone:
                continue
            if self._assigner.locked_by(cube["path"]) is not None:
                continue
            if self._assigner.try_lock(robot_id, cube["path"]):
                return cube["path"]
        return None

    def unreserve(self, cube_path: str) -> None:
        """cycle 종료 시 호출 — locked_by 로 owner 자동 추론 후 release."""
        owner = self._assigner.locked_by(cube_path)
        if owner is not None:
            self._assigner.release(owner, cube_path)

    def reset(self) -> None:
        self._assigner.reset()
        self._cubes_cache.clear()
