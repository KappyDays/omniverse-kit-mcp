"""Phase event log — Worker cycle 진행을 timestamp 와 함께 기록.

Live test 에서 cycle 시간 / phase 분포 / 첫 cube grasp 까지 latency 를
사후 분석. v3 의 silent fallback (joint_positions 안 변하는 무한 루프) 같은
issue 가 entries 의 event 분포로 즉시 가시화.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhaseLog:
    """In-memory event list — extension 종료 시 JSON dump 가능."""

    _entries: list[dict[str, Any]] = field(default_factory=list)
    _last_phase: dict[str, int] = field(default_factory=dict)

    def event(self, event: str, *, t: float, robot_id: str, **kwargs: Any) -> None:
        """Generic event (`cycle_start` / `cycle_done` 등)."""
        entry = {"event": event, "t": t, "robot_id": robot_id}
        entry.update(kwargs)
        self._entries.append(entry)

    def event_phase(self, *, t: float, robot_id: str, phase: int) -> None:
        """Phase 변화 event — 동일 robot 의 직전 phase 와 같으면 dedup.

        Worker.tick 이 매 sim tick 호출되므로 phase 가 안 바뀐 동안 noise
        방지. robot_id 별로 last_phase 를 따로 추적 — 두 robot 이 동시에
        같은 phase 더라도 각자 한 번씩 기록.
        """
        last = self._last_phase.get(robot_id)
        if last == phase:
            return
        self._last_phase[robot_id] = phase
        self._entries.append({
            "event": "phase_change",
            "t": t,
            "robot_id": robot_id,
            "phase": phase,
        })

    def entries(self) -> list[dict[str, Any]]:
        return self._entries

    def to_json(self) -> str:
        return json.dumps(self._entries, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        self._entries.clear()
        self._last_phase.clear()
