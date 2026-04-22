"""Tests for step_actions — office/nova_carter load, navigate, sensors, people sit.

Tests assert against the ACTUAL validation_api service signatures:
- Most service methods take a single request dict (Pydantic extra='forbid').
- Some take positional args (open_stage, compute_world_bbox, robot.navigate_path).
- All returns are dicts (not objects with attributes).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omni.mycompany.isaac_tutorial.actions.state import TutorialState


OFFICE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Office/office.usd"
)
NOVA_CARTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)
BIPED_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/People/Characters/Biped_Setup.usd"
)


# ---------------- T10: step 1 + step 2 ----------------

@pytest.mark.asyncio
async def test_open_office_calls_stage_open():
    services = MagicMock()
    services.stage.open_stage = AsyncMock(return_value={"ok": True})
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import open_office
    msg = await open_office(services, state)

    # open_stage takes positional str
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
async def test_load_nova_carter_calls_stage_load_usd_with_request_dict():
    services = MagicMock()
    services.stage.load_usd = AsyncMock(return_value={"ok": True})
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import load_nova_carter
    msg = await load_nova_carter(services, state)

    services.stage.load_usd.assert_awaited_once()
    # Single positional dict argument (not kwargs)
    (req,) = services.stage.load_usd.call_args.args
    assert req == {
        "usd_url": NOVA_CARTER_URL,
        "prim_path": "/World/nova_carter",
        "position": [0.0, 0.0, 0.0],
    }
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
    # bake returns dict with mesh_signature (not object attr)
    services.navigation.bake = AsyncMock(return_value={"mesh_signature": "sig123"})
    # query_path returns dict with 'points' key
    services.navigation.query_path = AsyncMock(
        return_value={"points": [[0.0, 0.0, 0.0], [1.0, 2.0, 0.0]]},
    )
    # robot.navigate_path returns dict with job_id
    services.robot.navigate_path = AsyncMock(
        return_value={"ok": True, "job_id": "jobX", "prim_path": "/World/nova_carter"},
    )

    state = TutorialState(office_loaded=True, nova_carter_loaded=True)
    from omni.mycompany.isaac_tutorial.actions.step_actions import navigate_via_navmesh
    msg = await navigate_via_navmesh(services, state)

    services.simulation.stop.assert_awaited()
    services.navigation.bake.assert_awaited_once()
    # query_path takes a request dict (positional)
    (qp_req,) = services.navigation.query_path.call_args.args
    assert qp_req["start"] == [0.0, 0.0, 0.0]
    assert qp_req["end"] == [1.0, 2.0, 0.0]
    assert qp_req["agent_radius"] == 0.4
    services.simulation.play.assert_awaited_once()
    # robot.navigate_path is positional: (prim_path, points, duration_s)
    args = services.robot.navigate_path.call_args.args
    assert args[0] == "/World/nova_carter"
    assert args[1] == [[0.0, 0.0, 0.0], [1.0, 2.0, 0.0]]
    assert isinstance(args[2], float)
    assert state.active_job_ids.get("step_3") == "jobX"
    assert state.chair_anchor_path == "/World/office/Chair_01"
    assert state.navigated is True
    assert "jobX" in msg


@pytest.mark.asyncio
async def test_navigate_bake_failure_raises():
    services = MagicMock()
    services.simulation.stop = AsyncMock()
    # bake returns dict with mesh_signature=None (bake failed signal)
    services.navigation.bake = AsyncMock(return_value={"mesh_signature": None})
    state = TutorialState(office_loaded=True, nova_carter_loaded=True)

    from omni.mycompany.isaac_tutorial.actions.step_actions import navigate_via_navmesh
    with pytest.raises(RuntimeError, match="NavMesh bake"):
        await navigate_via_navmesh(services, state)


# ---------------- T13: navmesh viz + sensor ----------------

@pytest.mark.asyncio
async def test_toggle_navmesh_viz_alternates():
    services = MagicMock()
    services.navigation.set_visualization = AsyncMock(
        return_value={"backend": "carb_settings"},
    )
    state = TutorialState(navmesh_viz_mode="off")

    from omni.mycompany.isaac_tutorial.actions.step_actions import toggle_navmesh_viz
    await toggle_navmesh_viz(services, state)
    assert state.navmesh_viz_mode == "walkable"
    # set_visualization is called with a request dict {mode}
    (req,) = services.navigation.set_visualization.call_args.args
    assert req == {"mode": "walkable"}

    await toggle_navmesh_viz(services, state)
    assert state.navmesh_viz_mode == "off"


@pytest.mark.asyncio
async def test_attach_sensors_and_record():
    services = MagicMock()
    services.sensor.attach_rtx_camera = AsyncMock(return_value={"ok": True})
    services.sensor.attach_rtx_lidar = AsyncMock(return_value={"ok": True})
    services.replicator.create_writer = AsyncMock(return_value={"ok": True})
    services.replicator.trigger_on_time = AsyncMock(return_value={"ok": True})
    state = TutorialState()

    from omni.mycompany.isaac_tutorial.actions.step_actions import attach_sensors_and_record
    await attach_sensors_and_record(services, state)

    # attach_rtx_camera takes a dict with robot_prim + mount_offset + mount_rotation
    (cam_req,) = services.sensor.attach_rtx_camera.call_args.args
    assert cam_req["robot_prim"] == "/World/nova_carter/chassis_link"
    assert cam_req["mount_offset"] == [0.5, 0.0, 1.0]
    assert cam_req["mount_rotation"] == [0.0, 0.0, 0.0]

    (lidar_req,) = services.sensor.attach_rtx_lidar.call_args.args
    assert lidar_req["config_preset"] == "Example_Rotary"

    # create_writer uses 'depth' not 'distance_to_camera'
    (writer_req,) = services.replicator.create_writer.call_args.args
    assert writer_req["writer_type"] == "BasicWriter"
    assert writer_req["depth"] is True
    assert "distance_to_camera" not in writer_req

    (trigger_req,) = services.replicator.trigger_on_time.call_args.args
    assert trigger_req == {"interval_s": 0.1}

    assert state.sensor_writer_id == "tutorial_writer"
    assert state.sensor_output_dir is not None
    assert "isaac_tutorial" in state.sensor_output_dir


# ---------------- T14: people sit ----------------

@pytest.mark.asyncio
async def test_load_people_and_sit_uses_chair_anchor():
    services = MagicMock()
    services.character.load = AsyncMock(
        return_value={
            "ok": True,
            "sanitized_prim_path": "/World/Characters/Biped_01",
        },
    )
    services.simulation.play = AsyncMock()
    services.character.sit_on_prim = AsyncMock(return_value={"ok": True})

    state = TutorialState(
        office_loaded=True,
        chair_anchor_path="/World/office/Chair_01",
    )
    from omni.mycompany.isaac_tutorial.actions.step_actions import load_people_and_sit
    msg = await load_people_and_sit(services, state)

    # character.load takes dict with usd_url (not 'url')
    (load_req,) = services.character.load.call_args.args
    assert load_req["usd_url"] == BIPED_URL
    assert load_req["prim_path"] == "/World/Characters/Biped_01"

    services.simulation.play.assert_awaited_once()

    # sit_on_prim takes dict with character_prim_path + chair_prim_path
    (sit_req,) = services.character.sit_on_prim.call_args.args
    assert sit_req["character_prim_path"] == "/World/Characters/Biped_01"
    assert sit_req["chair_prim_path"] == "/World/office/Chair_01"

    assert state.people_loaded is True
    assert "/World/office/Chair_01" in msg


@pytest.mark.asyncio
async def test_load_people_and_sit_fallback_when_no_chair():
    services = MagicMock()
    services.character.load = AsyncMock(
        return_value={
            "ok": True,
            "sanitized_prim_path": "/World/Characters/Biped_01",
        },
    )
    services.simulation.play = AsyncMock()
    services.character.navigate_to = AsyncMock(return_value={"job_id": "navJob"})
    services.character.play_animation_variant = AsyncMock(return_value={"ok": True})

    state = TutorialState(office_loaded=True, chair_anchor_path=None)
    from omni.mycompany.isaac_tutorial.actions.step_actions import load_people_and_sit
    msg = await load_people_and_sit(services, state)

    # navigate_to takes dict with prim_path (not 'character_prim_path')
    (nav_req,) = services.character.navigate_to.call_args.args
    assert nav_req["prim_path"] == "/World/Characters/Biped_01"
    assert nav_req["target"] == [-10.0, -15.0, 0.0]

    (anim_req,) = services.character.play_animation_variant.call_args.args
    assert anim_req["prim_path"] == "/World/Characters/Biped_01"
    assert anim_req["variant"] == "Sit"

    assert "fallback" in msg.lower()
