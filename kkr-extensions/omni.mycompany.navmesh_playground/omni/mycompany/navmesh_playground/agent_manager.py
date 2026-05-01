"""Agent record + list management."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


AgentKind = Literal["People", "Robot"]
AgentState = Literal[
    "Idle", "Walking", "Driving", "Sitting", "Stopped", "Error"
]


@dataclass
class AgentRecord:
    id: str                                  # e.g. "People-01"
    kind: AgentKind
    # Parent payload prim — for delete + Set Cur (xformOp:translate read).
    # People: /World/Characters/<name>. Robot: /World/<name>.
    prim_path: str
    # SkelRoot path under prim_path — for character_service.play_animation.
    # Robot: same as prim_path.
    skel_root_path: str = ""
    state: AgentState = "Idle"
    state_detail: str = ""
    start: tuple[float, float, float] = (0.0, 0.0, 0.0)
    goal: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # People-only:
    sit_variant: str = "SitIdle"
    # Robot-only:
    v_max: float = 1.0
    w_max: float = 1.2
    wheel_radius: float = 0.14
    wheel_base: float = 0.413
    arrival_tol: float = 0.3
    # Skin URL (People) / Robot asset URL
    asset_url: str = ""
    # Running async task handle; agent_manager does not own lifecycle
    task_ref: object = field(default=None)


class AgentManager:

    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._counter_by_kind: dict[str, int] = {"People": 0, "Robot": 0}

    def allocate_id(self, kind: AgentKind) -> str:
        self._counter_by_kind[kind] += 1
        return f"{kind}-{self._counter_by_kind[kind]:02d}"

    def add(self, record: AgentRecord) -> None:
        if record.id in self._agents:
            raise ValueError(f"Duplicate agent id: {record.id}")
        self._agents[record.id] = record

    def remove(self, agent_id: str) -> AgentRecord | None:
        return self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> AgentRecord | None:
        return self._agents.get(agent_id)

    def list(self) -> list[AgentRecord]:
        return list(self._agents.values())

    def sanitize_prim_name(self, base: str) -> str:
        """USD prim names: [A-Za-z0-9_], no leading digit."""
        s = re.sub(r"[^A-Za-z0-9_]", "_", base)
        if s and s[0].isdigit():
            s = f"a_{s}"
        return s or "agent"
