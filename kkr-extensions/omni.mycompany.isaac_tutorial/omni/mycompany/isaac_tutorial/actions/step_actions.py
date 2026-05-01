"""Tutorial step actions — office open, nova_carter load, navigate, sensor attach, people sit.

All functions take (services, state) where:
  services = isaac_tutorial.bindings.services.get_services() — the
             validation_api singletons imported from rest_router
  state    = isaac_tutorial.actions.state.TutorialState

IMPORTANT — validation_api method calling conventions
=====================================================

Most validation_api service methods take a SINGLE `request: dict` argument
shaped by a Pydantic model with `ConfigDict(extra="forbid")`. Passing
unexpected kwargs raises `TypeError: got an unexpected keyword argument`.
A few take positional scalar args (see `stage.open_stage(url)`,
`stage.compute_world_bbox(prim_path, ...)`, `robot.navigate_path(prim_path,
points, duration_s)`). `job_service.get_status` / `cancel` are sync, not async.

Returns are plain dicts (not objects) — use `dict["key"]`, never `obj.attr`.
"""
from __future__ import annotations

import math
import tempfile
from datetime import datetime
from pathlib import Path

import carb
import omni.usd

from .state import TutorialState


# ---------------- S3 asset URL constants ----------------

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

_CHAIR_KEYWORDS = ("chair", "seat", "armchair", "sofa")
_FALLBACK_TARGET = (-10.0, -15.0, 0.0)


# ---------------- T10: step 1 + step 2 ----------------

async def open_office(services, state: TutorialState) -> str:
    if state.office_loaded:
        return "Office already loaded (skipped)"
    # open_stage takes positional str (not dict)
    await services.stage.open_stage(OFFICE_URL)
    state.office_loaded = True
    return "Opened office.usd"


async def load_nova_carter(services, state: TutorialState) -> str:
    if state.nova_carter_loaded:
        return "Nova Carter already loaded (skipped)"
    # StageLoadUsdRequestModel — {usd_url, prim_path, position?, rotation?}
    # Pydantic forbids extra keys — use these exact field names.
    await services.stage.load_usd({
        "usd_url": NOVA_CARTER_URL,
        "prim_path": "/World/nova_carter",
        "position": [0.0, 0.0, 0.0],
    })
    state.nova_carter_loaded = True
    return "Loaded Nova Carter @ (0,0,0)"


# ---------------- T11: chair finder ----------------

async def _find_nearest_chair(services, start: tuple[float, float, float]):
    """Returns (prim_path, world_center). Fallback ('', (-10,-15,0)) when no match."""
    stage = omni.usd.get_context().get_stage()
    candidates = []
    for prim in stage.Traverse():
        name = prim.GetName().lower()
        if any(kw in name for kw in _CHAIR_KEYWORDS):
            path = str(prim.GetPath())
            # compute_world_bbox takes positional (prim_path, include_purposes?)
            bbox = await services.stage.compute_world_bbox(path)
            # return dict shape: {min, max, center, size, ...}
            center = tuple(bbox["center"])
            dist = math.dist(center, start)
            candidates.append((dist, path, center))
    if not candidates:
        carb.log_warn(
            f"[isaac_tutorial] No chair-like prim found — fallback {_FALLBACK_TARGET}"
        )
        return ("", _FALLBACK_TARGET)
    candidates.sort()
    _, path, center = candidates[0]
    return (path, center)


# ---------------- T12: step 3 — NavMesh navigate ----------------

async def navigate_via_navmesh(services, state: TutorialState) -> str:
    await services.simulation.stop()

    # bake takes an optional dict ({volume_scale, timeout_s}) — None uses defaults
    bake = await services.navigation.bake()
    if not bake.get("mesh_signature"):
        raise RuntimeError(f"NavMesh bake failed: {bake}")

    chair_path, chair_center = await _find_nearest_chair(services, start=(0.0, 0.0, 0.0))
    state.chair_anchor_path = chair_path or None

    # NavigationQueryPathRequestModel — {start, end, agent_radius, agent_height, straighten}
    path = await services.navigation.query_path({
        "start": [0.0, 0.0, 0.0],
        "end": list(chair_center),
        "agent_radius": 0.4,
        "agent_height": 1.2,
        "straighten": True,
    })
    waypoints = path.get("points") or []

    await services.simulation.play()
    # robot.navigate_path is POSITIONAL: (prim_path, points, duration_s)
    job = await services.robot.navigate_path(
        "/World/nova_carter",
        waypoints,
        5.0,
    )
    # job is dict: {ok, job_id, prim_path, target}
    state.active_job_ids["step_3"] = job["job_id"]
    state.navigated = True
    target_desc = chair_path or "fallback target"
    return f"Navigating to {target_desc} (job={job['job_id']})"


# ---------------- T13: sub-buttons ----------------

async def toggle_navmesh_viz(services, state: TutorialState) -> str:
    target = "walkable" if state.navmesh_viz_mode != "walkable" else "off"
    # NavigationSetVisualizationRequestModel — {mode}
    result = await services.navigation.set_visualization({"mode": target})
    state.navmesh_viz_mode = target
    backend = result.get("backend", "?") if isinstance(result, dict) else "?"
    return f"NavMesh visualization: {target} (backend={backend})"


async def attach_sensors_and_record(services, state: TutorialState) -> str:
    # SensorAttachRtxCameraRequestModel — {robot_prim, mount_offset, mount_rotation, sensor_name?, ...}
    # All three mount fields are 3-length lists; Pydantic validates length.
    await services.sensor.attach_rtx_camera({
        "robot_prim": "/World/nova_carter/chassis_link",
        "sensor_name": "tutorial_cam",
        "mount_offset": [0.5, 0.0, 1.0],
        "mount_rotation": [0.0, 0.0, 0.0],
    })
    await services.sensor.attach_rtx_lidar({
        "robot_prim": "/World/nova_carter/chassis_link",
        "sensor_name": "tutorial_lidar",
        "mount_offset": [0.0, 0.0, 1.2],
        "mount_rotation": [0.0, 0.0, 0.0],
        "config_preset": "Example_Rotary",
    })
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(tempfile.gettempdir()) / "isaac_tutorial" / stamp
    state.sensor_writer_id = "tutorial_writer"
    state.sensor_output_dir = str(output_dir)
    # ReplicatorCreateWriterRequestModel — field is 'depth' NOT 'distance_to_camera'
    await services.replicator.create_writer({
        "writer_type": "BasicWriter",
        "output_dir": str(output_dir),
        "rgb": True,
        "depth": True,
    })
    # ReplicatorTriggerOnTimeRequestModel — {interval_s}
    await services.replicator.trigger_on_time({"interval_s": 0.1})
    return f"Recording to {output_dir}"


# ---------------- T14: step 4 — people + sit ----------------

async def load_people_and_sit(services, state: TutorialState) -> str:
    if state.people_loaded:
        return "People already loaded (skipped)"

    # CharacterLoadRequestModel — {usd_url, prim_path?, ...}. usd_url not url.
    biped = await services.character.load({
        "usd_url": BIPED_URL,
        "prim_path": "/World/Characters/Biped_01",
    })
    state.people_loaded = True
    # Response includes sanitized_prim_path (hyphens/dots stripped).
    char_path = (
        biped.get("sanitized_prim_path")
        or biped.get("prim_path")
        or "/World/Characters/Biped_01"
    )

    await services.simulation.play()

    if state.chair_anchor_path:
        # CharacterSitOnPrimRequestModel — {character_prim_path, chair_prim_path, ...}
        await services.character.sit_on_prim({
            "character_prim_path": char_path,
            "chair_prim_path": state.chair_anchor_path,
            "approach_distance": 0.8,
        })
        return f"Loaded People + sit on {state.chair_anchor_path}"

    # fallback: CharacterNavigateRequestModel — {prim_path, target, speed}
    # Note: Character navigate uses 'prim_path', not 'character_prim_path'.
    job_res = await services.character.navigate_to({
        "prim_path": char_path,
        "target": [-10.0, -15.0, 0.0],
        "speed": 1.0,
    })
    # CharacterPlayAnimationVariantRequestModel — {prim_path, variant, ...}
    await services.character.play_animation_variant({
        "prim_path": char_path,
        "variant": "Sit",
    })
    job_id = job_res.get("job_id", "?") if isinstance(job_res, dict) else "?"
    return f"Loaded People + navigate + Sit (fallback; job={job_id})"
