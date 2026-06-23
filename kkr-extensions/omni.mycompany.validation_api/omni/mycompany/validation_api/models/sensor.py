"""Pydantic models for Sensor REST endpoints (Phase E)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SensorAttachRtxCameraRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    robot_prim: str = Field(description="Parent robot prim path (sensor is parented beneath it).")
    mount_offset: list[float] = Field(
        description="Translation [x,y,z] in meters relative to robot_prim.",
        min_length=3, max_length=3,
    )
    mount_rotation: list[float] = Field(
        description="Euler rotation [rx,ry,rz] in degrees relative to robot_prim.",
        min_length=3, max_length=3,
    )
    resolution: list[int] = Field(default=[1280, 720], min_length=2, max_length=2)
    sensor_name: str = "RtxCamera"


class SensorAttachRtxLidarRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    robot_prim: str
    mount_offset: list[float] = Field(min_length=3, max_length=3)
    mount_rotation: list[float] = Field(min_length=3, max_length=3)
    config_preset: str = Field(
        default="Example_Rotary",
        description="Lidar profile preset (Example_Rotary / Velodyne_VLS128 / ...).",
    )
    sensor_name: str = "RtxLidar"


class SensorAttachRtxDepthCameraRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    robot_prim: str
    mount_offset: list[float] = Field(min_length=3, max_length=3)
    mount_rotation: list[float] = Field(min_length=3, max_length=3)
    resolution: list[int] = Field(default=[1280, 720], min_length=2, max_length=2)
    sensor_name: str = "RtxDepthCamera"


class SensorSetVisualizationRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_prim: str = Field(description="Sensor prim path previously returned by attach_*.")
    mode: Literal["on", "off"] = "on"


class SensorAttachContactRequestModel(BaseModel):
    """Physics contact sensor attachment (Phase G).

    Creates an ``isaacsim.sensors.experimental.physics.Contact`` child prim under
    *prim_path*. Provides contact force / event readout when the parent
    rigid body collides with other colliders.
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Parent rigid-body prim path")
    sensor_name: str = "ContactSensor"
    frequency: int = Field(default=60, ge=1, le=1000)
    translation: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        min_length=3, max_length=3,
    )
    radius: float = Field(
        default=-1.0,
        description="Sensor radius in meters; -1 uses Kit default",
    )


class SensorAttachImuRequestModel(BaseModel):
    """Physics IMU sensor attachment (Phase G).

    Creates an ``isaacsim.sensors.experimental.physics.IMU`` child prim. Emits
    linear acceleration / angular velocity / orientation readings at the
    configured frequency once simulation is playing.
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Parent rigid-body prim path")
    sensor_name: str = "IMUSensor"
    frequency: int = Field(default=200, ge=1, le=2000)
    mount_offset: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        min_length=3, max_length=3,
    )
    mount_orientation: list[float] = Field(
        default_factory=lambda: [1.0, 0.0, 0.0, 0.0],
        description="[qw, qx, qy, qz] scalar-first quaternion",
        min_length=4, max_length=4,
    )


class SensorLidarGetPointCloudRequestModel(BaseModel):
    """Read one frame of RTX Lidar point cloud data — symmetric readback for attach_rtx_lidar."""

    model_config = ConfigDict(extra="forbid")

    sensor_prim: str = Field(description="RTX Lidar prim path (from sensor_attach_rtx_lidar)")
    max_points: int = Field(
        default=1000, ge=1, le=100000,
        description="Truncate to first N points (response size cap)",
    )
    frames_to_wait: int = Field(
        default=2, ge=1, le=300,
        description="Kit ticks to await before reading annotator (lidar must spin)",
    )


class SensorSetAnnotatorRequestModel(BaseModel):
    """Configure replicator annotators on a sensor camera prim (Phase G).

    Annotators ⊂ {rgb, depth, semantic_segmentation, instance_segmentation,
    normals, motion_vectors, distance_to_camera, distance_to_image_plane}.
    Uses ``omni.replicator.core.AnnotatorRegistry`` to attach to a render
    product derived from the sensor prim. Missing annotator modules are
    skipped with a log warning rather than a hard failure.
    """

    model_config = ConfigDict(extra="forbid")

    sensor_prim: str = Field(description="Camera prim path (from sensor_attach_rtx_*)")
    annotators: list[str] = Field(
        default_factory=list,
        description=(
            "Annotator names — rgb|depth|semantic_segmentation|instance_segmentation|"
            "normals|motion_vectors|distance_to_camera|distance_to_image_plane"
        ),
    )
    resolution: list[int] = Field(
        default=[1280, 720], min_length=2, max_length=2,
        description="Render product resolution [w, h]",
    )
