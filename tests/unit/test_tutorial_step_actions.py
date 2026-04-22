"""Tests for step_actions — office/nova_carter load, navigate, sensors, people sit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omni.mycompany.isaac_tutorial.actions.state import TutorialState


# ---------------- T10: step 1 + step 2 ----------------

OFFICE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Office/office.usd"
)
NOVA_CARTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)


@pytest.mark.asyncio
async def test_open_office_calls_stage_open():
    services = MagicMock()
    services.stage.open_stage = AsyncMock(return_value=MagicMock(ok=True))
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import open_office
    msg = await open_office(services, state)

    services.stage.open_stage.assert_awaited_once_with(OFFICE_URL)
    assert state.office_loaded is True
    assert "office" in msg.lower()


@pytest.mark.asyncio
async def test_open_office_idempotent():
    services = MagicMock()
    services.stage.open_stage = AsyncMock()
    state = TutorialState(office_loaded=True)

    from omni.mycompany.isaac_tutorial.actions.step_actions import open_office
    msg = await open_office(services, state)
    services.stage.open_stage.assert_not_called()
    assert "already" in msg.lower()


@pytest.mark.asyncio
async def test_load_nova_carter_calls_stage_load_usd():
    services = MagicMock()
    services.stage.load_usd = AsyncMock(return_value=MagicMock(ok=True))
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import load_nova_carter
    msg = await load_nova_carter(services, state)

    services.stage.load_usd.assert_awaited_once()
    call = services.stage.load_usd.call_args
    assert call.kwargs.get("url") == NOVA_CARTER_URL
    assert call.kwargs.get("prim_path") == "/World/nova_carter"
    assert state.nova_carter_loaded is True


@pytest.mark.asyncio
async def test_load_nova_carter_idempotent():
    services = MagicMock()
    services.stage.load_usd = AsyncMock()
    state = TutorialState(nova_carter_loaded=True)

    from omni.mycompany.isaac_tutorial.actions.step_actions import load_nova_carter
    msg = await load_nova_carter(services, state)
    services.stage.load_usd.assert_not_called()
    assert "already" in msg.lower()


# ---------------- T12: navigate ----------------

@pytest.mark.asyncio
@patch(
    "omni.mycompany.isaac_tutorial.actions.step_actions._find_nearest_chair",
    new_callable=AsyncMock,
)
async def test_navigate_via_navmesh_full_sequence(mock_find):
    mock_find.return_value = ("/World/office/Chair_01", (1.0, 2.0, 0.0))

    services = MagicMock()
    services.simulation.stop = AsyncMock()
    services.simulation.play = AsyncMock()
    services.navigation.bake = AsyncMock(
        return_value=MagicMock(mesh_signature="sig123"),
    )
    services.navigation.query_path = AsyncMock(
        return_value=MagicMock(waypoints=[(0, 0, 0), (1, 2, 0)]),
    )
    services.robot.navigate_path = AsyncMock(return_value=MagicMock(job_id="jobX"))

    state = TutorialState(office_loaded=True, nova_carter_loaded=True)
    from omni.mycompany.isaac_tutorial.actions.step_actions import navigate_via_navmesh
    msg = await navigate_via_navmesh(services, state)

    services.simulation.stop.assert_awaited()
    services.navigation.bake.assert_awaited_once()
    services.navigation.query_path.assert_awaited_once()
    services.simulation.play.assert_awaited_once()
    services.robot.navigate_path.assert_awaited_once()
    assert state.active_job_ids.get("step_3") == "jobX"
    assert state.chair_anchor_path == "/World/office/Chair_01"
    assert state.navigated is True
    assert "jobX" in msg


@pytest.mark.asyncio
async def test_navigate_bake_failure_raises():
    services = MagicMock()
    services.simulation.stop = AsyncMock()
    services.navigation.bake = AsyncMock(
        return_value=MagicMock(mesh_signature=None),
    )
    state = TutorialState(office_loaded=True, nova_carter_loaded=True)

    from omni.mycompany.isaac_tutorial.actions.step_actions import navigate_via_navmesh
    with pytest.raises(RuntimeError, match="NavMesh bake"):
        await navigate_via_navmesh(services, state)


# ---------------- T13: navmesh viz + sensor ----------------

@pytest.mark.asyncio
async def test_toggle_navmesh_viz_alternates():
    services = MagicMock()
    services.navigation.set_visualization = AsyncMock(
        return_value=MagicMock(backend="carb_settings"),
    )
    state = TutorialState(navmesh_viz_mode="off")

    from omni.mycompany.isaac_tutorial.actions.step_actions import toggle_navmesh_viz
    await toggle_navmesh_viz(services, state)
    assert state.navmesh_viz_mode == "walkable"
    services.navigation.set_visualization.assert_awaited_with(mode="walkable")

    await toggle_navmesh_viz(services, state)
    assert state.navmesh_viz_mode == "off"


@pytest.mark.asyncio
async def test_attach_sensors_and_record():
    services = MagicMock()
    services.sensor.attach_rtx_camera = AsyncMock(return_value=MagicMock(ok=True))
    services.sensor.attach_rtx_lidar = AsyncMock(return_value=MagicMock(ok=True))
    services.replicator.create_writer = AsyncMock(return_value=MagicMock(ok=True))
    services.replicator.trigger_on_time = AsyncMock(return_value=MagicMock(ok=True))
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import attach_sensors_and_record
    await attach_sensors_and_record(services, state)

    services.sensor.attach_rtx_camera.assert_awaited_once()
    services.sensor.attach_rtx_lidar.assert_awaited_once()
    services.replicator.create_writer.assert_awaited_once()
    services.replicator.trigger_on_time.assert_awaited_once()
    assert state.sensor_writer_id == "tutorial_writer"
    assert state.sensor_output_dir is not None
    assert "isaac_tutorial" in state.sensor_output_dir


# ---------------- T14: people sit ----------------

@pytest.mark.asyncio
async def test_load_people_and_sit_uses_chair_anchor():
    services = MagicMock()
    services.character.load = AsyncMock(
        return_value=MagicMock(
            ok=True, sanitized_prim_path="/World/Characters/Biped_01",
        ),
    )
    services.simulation.play = AsyncMock()
    services.character.sit_on_prim = AsyncMock(return_value=MagicMock(ok=True))

    state = TutorialState(
        office_loaded=True,
        chair_anchor_path="/World/office/Chair_01",
    )
    from omni.mycompany.isaac_tutorial.actions.step_actions import load_people_and_sit
    msg = await load_people_and_sit(services, state)

    services.character.load.assert_awaited_once()
    services.simulation.play.assert_awaited_once()
    services.character.sit_on_prim.assert_awaited_once()
    call = services.character.sit_on_prim.call_args
    assert call.kwargs.get("chair_prim_path") == "/World/office/Chair_01"
    assert state.people_loaded is True
    assert "/World/office/Chair_01" in msg


@pytest.mark.asyncio
async def test_load_people_and_sit_fallback_when_no_chair():
    services = MagicMock()
    services.character.load = AsyncMock(
        return_value=MagicMock(
            ok=True, sanitized_prim_path="/World/Characters/Biped_01",
        ),
    )
    services.simulation.play = AsyncMock()
    services.character.navigate_to = AsyncMock(
        return_value=MagicMock(job_id="navJob"),
    )
    services.character.play_animation_variant = AsyncMock(return_value=MagicMock(ok=True))

    state = TutorialState(office_loaded=True, chair_anchor_path=None)
    from omni.mycompany.isaac_tutorial.actions.step_actions import load_people_and_sit
    msg = await load_people_and_sit(services, state)

    services.character.navigate_to.assert_awaited_once()
    services.character.play_animation_variant.assert_awaited_once()
    assert "fallback" in msg.lower()
