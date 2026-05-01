"""TutorialState dataclass + stage-based recovery."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TutorialState:
    office_loaded: bool = False
    nova_carter_loaded: bool = False
    navigated: bool = False
    people_loaded: bool = False
    ceiling_hidden: bool = False
    ceiling_cache: list[str] = field(default_factory=list)
    wasd_graph_path: str | None = None
    active_job_ids: dict[str, str] = field(default_factory=dict)
    sensor_writer_id: str | None = None
    sensor_output_dir: str | None = None
    navmesh_viz_mode: str = "off"
    camera_speed: float = 0.1
    chair_anchor_path: str | None = None


def recover_state_from_stage(stage) -> TutorialState:
    """Extension on_startup 시 기존 stage 내용으로 state 를 유추."""
    s = TutorialState()
    s.office_loaded = stage.GetPrimAtPath("/World/office").IsValid()
    s.nova_carter_loaded = stage.GetPrimAtPath("/World/nova_carter").IsValid()
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        if path.startswith("/World/Characters/"):
            s.people_loaded = True
            break
    return s
