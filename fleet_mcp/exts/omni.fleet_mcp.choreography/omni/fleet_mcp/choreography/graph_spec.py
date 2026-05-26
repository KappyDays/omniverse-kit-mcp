"""Pure declarative spec of the OmniGraph ActionGraph to author live (NO omni)."""
from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class FleetGraphSpec:
    graph_path: str
    robot_paths: tuple[str, ...]
    wheel_radius: float
    wheel_base: float
    tick_node_type: str


def build_spec(robot_paths) -> FleetGraphSpec:
    return FleetGraphSpec(
        graph_path=config.GRAPH_PATH,
        robot_paths=tuple(robot_paths),
        wheel_radius=config.WHEEL_RADIUS,
        wheel_base=config.WHEEL_BASE,
        tick_node_type="omni.graph.action.OnPlaybackTick",
    )
