"""Unit tests for PhysicsModule + physics_* MCP tool registration (Phase F)."""

from __future__ import annotations

import pytest

from omniverse_kit_mcp.config import AppConfig
from omniverse_kit_mcp.mcp.server import create_mcp_server
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleName, OperationMeta
from omniverse_kit_mcp.types.physics import (
    PhysicsApplyColliderRequest,
    PhysicsApplyColliderResult,
    PhysicsApplyMaterialRequest,
    PhysicsApplyMaterialResult,
    PhysicsApplyRigidBodyRequest,
    PhysicsApplyRigidBodyResult,
    PhysicsCreateJointRequest,
    PhysicsCreateJointResult,
    PhysicsRigidBodyState,
    PhysicsSetJointDriveRequest,
    PhysicsSetJointDriveResult,
    PhysicsSetSceneRequest,
    PhysicsSetSceneResult,
    PhysicsVisualizeRequest,
    PhysicsVisualizeResult,
)


def _meta() -> OperationMeta:
    return OperationMeta(
        request_id="test", module=ModuleName.PHYSICS, started_at_epoch_ms=0,
    )


# --- Tool registration -----------------------------------------------------


@pytest.fixture
def mcp_server():
    return create_mcp_server(AppConfig())


def test_physics_tools_registered(mcp_server):
    names = set(mcp_server._tool_manager._tools)
    for tool in (
        "physics_apply_rigid_body",
        "physics_get_rigid_body_state",
        "physics_apply_collider",
        "physics_apply_material",
        "physics_create_joint",
        "physics_set_joint_drive",
        "physics_set_scene",
        "physics_visualize",
    ):
        assert tool in names, f"{tool} not registered"


def test_physics_enum_registered():
    assert ModuleName.PHYSICS.value == "physics"


# --- Module unit tests -----------------------------------------------------


@pytest.mark.asyncio
async def test_apply_rigid_body_success():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsApplyRigidBodyRequest(
        prim_path="/World/Box", mass=2.5, dynamic=True,
    )
    result = await module.apply_rigid_body(_meta(), request)

    assert result.ok
    assert result.status == ExecutionStatus.PASSED
    assert isinstance(result.data, PhysicsApplyRigidBodyResult)
    assert result.data.prim_path == "/World/Box"
    assert result.data.mass == 2.5
    assert result.data.dynamic is True
    assert "PhysicsRigidBodyAPI" in result.data.applied_apis
    assert ("physics_apply_rigid_body",
            {"prim_path": "/World/Box", "mass": 2.5, "dynamic": True}) in client.calls


@pytest.mark.asyncio
async def test_get_rigid_body_state_default_runtime():
    """Default mock returns physx_runtime source with -2.5 z velocity."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    result = await module.get_rigid_body_state(_meta(), "/World/Box")

    assert result.ok
    assert isinstance(result.data, PhysicsRigidBodyState)
    assert result.data.source == "physx_runtime"
    assert result.data.linear_velocity == (0.0, 0.0, -2.5)
    assert result.data.angular_velocity == (0.0, 0.0, 0.0)
    assert result.data.mass == 1.0
    assert result.data.is_kinematic is False
    assert result.data.is_enabled is True
    state_calls = [c for c in client.calls if c[0] == "physics_get_rigid_body_state"]
    assert len(state_calls) == 1
    assert state_calls[0][1]["prim_path"] == "/World/Box"


@pytest.mark.asyncio
async def test_get_rigid_body_state_usd_initial_fallback():
    """Custom mock simulates USD-only fallback (pre-play state)."""
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    client.responses["physics_get_rigid_body_state"] = {
        "ok": True,
        "prim_path": "/World/StaticBox",
        "source": "usd_initial",
        "linear_velocity": [0.0, 0.0, 0.0],
        "angular_velocity": [0.0, 0.0, 0.0],
        "mass": 5.0,
        "center_of_mass": [0.0, 0.0, 0.5],
        "is_kinematic": True,
        "is_enabled": True,
    }
    module = PhysicsModule(client)
    result = await module.get_rigid_body_state(_meta(), "/World/StaticBox")

    assert result.ok
    assert result.data.source == "usd_initial"
    assert result.data.is_kinematic is True
    assert result.data.mass == 5.0
    assert result.data.center_of_mass == (0.0, 0.0, 0.5)


@pytest.mark.asyncio
async def test_get_rigid_body_state_propagates_400():
    """Extension raises ValueError for missing RigidBodyAPI → wrapped error."""
    from tests.conftest import MockIsaacRestClient

    class FailingClient(MockIsaacRestClient):
        async def physics_get_rigid_body_state(self, prim_path):  # type: ignore[override]
            raise ValueError("Prim at /X has no UsdPhysics.RigidBodyAPI applied")

    module = PhysicsModule(FailingClient())
    result = await module.get_rigid_body_state(_meta(), "/X")

    assert not result.ok
    assert result.error_code == "PHYSICS_GET_RIGID_BODY_STATE_ERROR"
    assert "RigidBodyAPI" in (result.message or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approx", ["convexHull", "triangleMesh", "sdf", "box", "sphere", "none"],
)
async def test_apply_collider_all_modes(approx):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsApplyColliderRequest(
        prim_path="/World/Mesh", approximation=approx,
    )
    result = await module.apply_collider(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsApplyColliderResult)
    assert result.data.approximation == approx


@pytest.mark.asyncio
async def test_apply_material_defaults():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsApplyMaterialRequest(prim_path="/World/Box")
    result = await module.apply_material(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsApplyMaterialResult)
    assert result.data.friction == 0.5
    assert result.data.restitution == 0.0
    assert result.data.density == 1000.0
    assert result.data.material_prim_path.startswith("/World/PhysicsMaterials")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "joint_type", ["Fixed", "Revolute", "Prismatic", "Spherical"],
)
async def test_create_joint_all_types(joint_type):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsCreateJointRequest(
        joint_type=joint_type,
        body_a="/World/A",
        body_b="/World/B",
    )
    result = await module.create_joint(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsCreateJointResult)
    assert result.data.joint_type == joint_type
    assert result.data.body_a == "/World/A"
    assert result.data.body_b == "/World/B"


@pytest.mark.asyncio
async def test_set_joint_drive_linear_with_max_force():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsSetJointDriveRequest(
        joint_prim_path="/World/Rig/LiftJoint",
        drive_type="linear",
        target_position=1.5,
        stiffness=4000.0,
        damping=400.0,
        max_force=1.0e6,
    )
    result = await module.set_joint_drive(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsSetJointDriveResult)
    assert result.data.drive_type == "linear"
    assert result.data.target_position == 1.5
    assert result.data.stiffness == 4000.0
    assert result.data.max_force == 1.0e6
    sent = dict(client.calls)["physics_set_joint_drive"]
    assert sent["joint_prim_path"] == "/World/Rig/LiftJoint"
    assert sent["drive_type"] == "linear"


@pytest.mark.asyncio
async def test_set_joint_drive_max_force_none_stays_none():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsSetJointDriveRequest(
        joint_prim_path="/World/Rig/TiltJoint",
        drive_type="angular",
        target_position=8.0,
        stiffness=800.0,
        damping=80.0,
    )
    result = await module.set_joint_drive(_meta(), request)

    assert result.ok
    assert result.data.drive_type == "angular"
    assert result.data.max_force is None  # unset -> PhysX default (unbounded)


@pytest.mark.asyncio
async def test_set_joint_drive_propagates_400():
    class FailingClient:
        async def physics_set_joint_drive(self, _req):
            raise ValueError("Joint prim '/World/Nope' not found")

    module = PhysicsModule(FailingClient())  # type: ignore[arg-type]
    request = PhysicsSetJointDriveRequest(joint_prim_path="/World/Nope")
    result = await module.set_joint_drive(_meta(), request)

    assert not result.ok
    assert result.error_code == "PHYSICS_SET_JOINT_DRIVE_ERROR"
    assert "not found" in (result.message or "")


@pytest.mark.asyncio
async def test_set_scene_normalises_gravity():
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsSetSceneRequest(
        gravity=(0.0, 0.0, -9.81),
        timestep=1.0 / 120.0,
    )
    result = await module.set_scene(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsSetSceneResult)
    assert result.data.gravity_magnitude > 9.0
    assert result.data.time_steps_per_second == 120


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["collision", "joint", "mass", "off"])
async def test_visualize_all_modes(mode):
    from tests.conftest import MockIsaacRestClient

    client = MockIsaacRestClient()
    module = PhysicsModule(client)
    request = PhysicsVisualizeRequest(mode=mode)
    result = await module.visualize(_meta(), request)

    assert result.ok
    assert isinstance(result.data, PhysicsVisualizeResult)
    assert result.data.mode == mode
    if mode == "off":
        assert result.data.active_settings == ()
    else:
        assert len(result.data.active_settings) >= 1


@pytest.mark.asyncio
async def test_apply_rigid_body_propagates_client_error():
    class BrokenClient:
        async def physics_apply_rigid_body(self, _req):
            raise RuntimeError("extension offline")

    module = PhysicsModule(BrokenClient())  # type: ignore[arg-type]
    request = PhysicsApplyRigidBodyRequest(prim_path="/World/Box")
    result = await module.apply_rigid_body(_meta(), request)

    assert not result.ok
    assert result.status == ExecutionStatus.ERROR
    assert result.error_code == "PHYSICS_APPLY_RIGID_BODY_ERROR"
