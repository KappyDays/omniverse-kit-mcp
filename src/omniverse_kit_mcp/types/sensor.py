"""Sensor types — RTX Camera / Lidar / Depth Camera attachment + visualization (Phase E)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True, frozen=True)
class SensorAttachRtxCameraRequest:
    robot_prim: str
    mount_offset: tuple[float, float, float]
    mount_rotation: tuple[float, float, float]
    resolution: tuple[int, int] = (1280, 720)
    sensor_name: str = "RtxCamera"


@dataclass(slots=True, frozen=True)
class SensorAttachRtxCameraResult:
    ok: bool
    sensor_prim_path: str
    parent_prim: str
    sensor_type: str
    resolution: tuple[int, int]


@dataclass(slots=True, frozen=True)
class SensorAttachRtxLidarRequest:
    robot_prim: str
    mount_offset: tuple[float, float, float]
    mount_rotation: tuple[float, float, float]
    config_preset: str = "Example_Rotary"
    sensor_name: str = "RtxLidar"


@dataclass(slots=True, frozen=True)
class SensorAttachRtxLidarResult:
    ok: bool
    sensor_prim_path: str
    parent_prim: str
    sensor_type: str
    config_preset: str
    annotator: str | None
    backend: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SensorAttachRtxDepthCameraRequest:
    robot_prim: str
    mount_offset: tuple[float, float, float]
    mount_rotation: tuple[float, float, float]
    resolution: tuple[int, int] = (1280, 720)
    sensor_name: str = "RtxDepthCamera"


@dataclass(slots=True, frozen=True)
class SensorAttachRtxDepthCameraResult:
    ok: bool
    sensor_prim_path: str
    parent_prim: str
    sensor_type: str
    resolution: tuple[int, int]
    annotator: str | None


@dataclass(slots=True, frozen=True)
class SensorSetVisualizationRequest:
    sensor_prim: str
    mode: Literal["on", "off"] = "on"


@dataclass(slots=True, frozen=True)
class SensorSetVisualizationResult:
    ok: bool
    sensor_prim: str
    mode: str
    sensor_type: str | None


# --- Phase G ---


@dataclass(slots=True, frozen=True)
class SensorAttachContactRequest:
    prim_path: str
    sensor_name: str = "ContactSensor"
    frequency: int = 60
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = -1.0


@dataclass(slots=True, frozen=True)
class SensorAttachContactResult:
    ok: bool
    sensor_prim_path: str
    parent_prim: str
    sensor_type: str
    frequency: int
    translation: tuple[float, float, float]
    radius: float
    backend: str


@dataclass(slots=True, frozen=True)
class SensorAttachImuRequest:
    prim_path: str
    sensor_name: str = "IMUSensor"
    frequency: int = 200
    mount_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mount_orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)


@dataclass(slots=True, frozen=True)
class SensorAttachImuResult:
    ok: bool
    sensor_prim_path: str
    parent_prim: str
    sensor_type: str
    frequency: int
    mount_offset: tuple[float, float, float]
    mount_orientation: tuple[float, float, float, float]
    backend: str


@dataclass(slots=True, frozen=True)
class SensorSetAnnotatorRequest:
    sensor_prim: str
    annotators: tuple[str, ...]
    resolution: tuple[int, int] = (1280, 720)


@dataclass(slots=True, frozen=True)
class SensorSetAnnotatorResult:
    ok: bool
    sensor_prim: str
    annotators: tuple[str, ...]
    skipped: tuple[str, ...]
    resolution: tuple[int, int]
    backend: str
    render_product: str | None


@dataclass(slots=True, frozen=True)
class SensorLidarGetPointCloudRequest:
    sensor_prim: str
    max_points: int = 1000
    frames_to_wait: int = 2
    min_points: int = 0
    fail_on_warning: bool = False


@dataclass(slots=True, frozen=True)
class SensorLidarGetPointCloudResult:
    ok: bool
    sensor_prim: str
    annotator: str
    backend: str
    num_points: int
    points: tuple[tuple[float, float, float], ...]
    intensities: tuple[float, ...]
    truncated: bool
    frames_waited: int
    raw_keys: tuple[str, ...]
    warning: str | None
    empty_reason: str | None
    diagnostics: dict[str, Any]
