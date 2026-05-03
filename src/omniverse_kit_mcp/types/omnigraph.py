"""OmniGraph types — node / connect / execute + ROS2 publisher macro (Phase H)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class OmnigraphCreateNodeRequest:
    graph_path: str
    node_type: str
    node_name: str | None = None


@dataclass(slots=True, frozen=True)
class OmnigraphCreateNodeResult:
    ok: bool
    graph_path: str
    graph_existed: bool
    node_type: str
    node_name: str
    node_path: str
    backend: str = ""


@dataclass(slots=True, frozen=True)
class OmnigraphConnectRequest:
    src_attr: str
    dst_attr: str


@dataclass(slots=True, frozen=True)
class OmnigraphConnectResult:
    ok: bool
    src_attr: str
    dst_attr: str
    backend: str = ""


@dataclass(slots=True, frozen=True)
class OmnigraphExecuteRequest:
    graph_path: str


@dataclass(slots=True, frozen=True)
class OmnigraphExecuteResult:
    ok: bool
    graph_path: str
    evaluated: bool
    backend: str = ""


@dataclass(slots=True, frozen=True)
class OmnigraphCreateRos2PublisherRequest:
    graph_path: str
    topic: str
    source_prim: str
    msg_type: str = "sensor_msgs/msg/Image"


@dataclass(slots=True, frozen=True)
class OmnigraphNodeRef:
    name: str
    type: str
    path: str


@dataclass(slots=True, frozen=True)
class OmnigraphEdgeRef:
    src: str
    dst: str


@dataclass(slots=True, frozen=True)
class OmnigraphCreateRos2PublisherResult:
    ok: bool
    graph_path: str
    topic: str
    source_prim: str
    msg_type: str
    ros2_available: bool
    nodes_created: tuple[OmnigraphNodeRef, ...] = field(default_factory=tuple)
    edges_created: tuple[OmnigraphEdgeRef, ...] = field(default_factory=tuple)
    backend: str = ""
