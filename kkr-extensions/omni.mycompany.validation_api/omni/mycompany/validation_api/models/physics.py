"""Pydantic models for Physics REST endpoints (Phase F)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PhysicsApplyRigidBodyRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Target prim for rigid body + mass API.")
    mass: float = Field(default=1.0, ge=0.0)
    dynamic: bool = Field(default=True, description="False = kinematic / static.")


class PhysicsApplyColliderRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    approximation: Literal[
        "convexHull", "triangleMesh", "sdf", "box", "sphere", "none"
    ] = "convexHull"


class PhysicsApplyMaterialRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str = Field(description="Prim to bind the physics material to.")
    friction: float = Field(default=0.5, ge=0.0)
    restitution: float = Field(default=0.0, ge=0.0, le=1.0)
    density: float = Field(default=1000.0, ge=0.0)
    material_name: str | None = None


class PhysicsCreateJointRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    joint_type: Literal["Fixed", "Revolute", "Prismatic", "Spherical"]
    body_a: str
    body_b: str
    anchor: list[float] = Field(default=[0.0, 0.0, 0.0], min_length=3, max_length=3)
    axis: list[float] = Field(default=[0.0, 0.0, 1.0], min_length=3, max_length=3)
    joint_prim_path: str | None = None


class PhysicsSetJointDriveRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    joint_prim_path: str = Field(description="Existing joint prim to drive.")
    drive_type: Literal["linear", "angular"] = "angular"
    target_position: float = 0.0
    target_velocity: float = 0.0
    stiffness: float = Field(default=0.0, ge=0.0)
    damping: float = Field(default=0.0, ge=0.0)
    max_force: float | None = Field(default=None, ge=0.0)


class PhysicsSetSceneRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gravity: list[float] = Field(
        default=[0.0, 0.0, -9.81], min_length=3, max_length=3,
    )
    timestep: float = Field(default=1.0 / 60.0, gt=0.0, le=1.0)
    solver_iter_pos: int = Field(default=4, ge=1, le=255)
    solver_iter_vel: int = Field(default=1, ge=0, le=255)
    scene_prim_path: str = "/World/PhysicsScene"


class PhysicsVisualizeRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["collision", "joint", "mass", "off"]
