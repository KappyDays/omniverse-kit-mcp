"""Physics types — rigid body / collider / material / joint / scene / viz (Phase F)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True)
class PhysicsApplyRigidBodyRequest:
    prim_path: str
    mass: float = 1.0
    dynamic: bool = True


@dataclass(slots=True, frozen=True)
class PhysicsApplyRigidBodyResult:
    ok: bool
    prim_path: str
    mass: float
    dynamic: bool
    applied_apis: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PhysicsRigidBodyState:
    """Rigid body runtime state — vel / mass / COM + kinematic flags.

    ``source`` reports which backend filled the readout:
      * ``"physx_runtime"`` — live PhysX state via SingleRigidPrim
        (requires simulation.play to have ticked at least once).
      * ``"usd_initial"`` — USD authored values (velocities reflect
        whatever was set on the prim before play; mass/COM are always
        accurate from MassAPI).
    """

    prim_path: str
    source: str
    linear_velocity: tuple[float, float, float]
    angular_velocity: tuple[float, float, float]
    mass: float
    center_of_mass: tuple[float, float, float]
    is_kinematic: bool
    is_enabled: bool


@dataclass(slots=True, frozen=True)
class PhysicsApplyColliderRequest:
    prim_path: str
    approximation: Literal[
        "convexHull", "triangleMesh", "sdf", "box", "sphere", "none"
    ] = "convexHull"


@dataclass(slots=True, frozen=True)
class PhysicsApplyColliderResult:
    ok: bool
    prim_path: str
    approximation: str
    applied_apis: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PhysicsApplyMaterialRequest:
    prim_path: str
    friction: float = 0.5
    restitution: float = 0.0
    density: float = 1000.0
    material_name: str | None = None


@dataclass(slots=True, frozen=True)
class PhysicsApplyMaterialResult:
    ok: bool
    prim_path: str
    material_prim_path: str
    friction: float
    restitution: float
    density: float


@dataclass(slots=True, frozen=True)
class PhysicsCreateJointRequest:
    joint_type: Literal["Fixed", "Revolute", "Prismatic", "Spherical"]
    body_a: str
    body_b: str
    anchor: tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    joint_prim_path: str | None = None


@dataclass(slots=True, frozen=True)
class PhysicsCreateJointResult:
    ok: bool
    joint_prim_path: str
    joint_type: str
    body_a: str
    body_b: str


@dataclass(slots=True, frozen=True)
class PhysicsSetSceneRequest:
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)
    timestep: float = 1.0 / 60.0
    solver_iter_pos: int = 4
    solver_iter_vel: int = 1
    scene_prim_path: str = "/World/PhysicsScene"


@dataclass(slots=True, frozen=True)
class PhysicsSetSceneResult:
    ok: bool
    scene_prim_path: str
    gravity: tuple[float, float, float]
    gravity_magnitude: float
    timestep: float
    time_steps_per_second: int
    solver_iter_pos: int
    solver_iter_vel: int


@dataclass(slots=True, frozen=True)
class PhysicsVisualizeRequest:
    mode: Literal["collision", "joint", "mass", "off"]


@dataclass(slots=True, frozen=True)
class PhysicsVisualizeResult:
    ok: bool
    mode: str
    active_settings: tuple[str, ...]
