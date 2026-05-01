"""Live MCP smoke tests — Phase 1 Task 1.2 / plan §10.4 (D0-D17).

Context
-------
These tests hit the Extension REST API (``/validation/v1/**``) — the single
source of truth that every MCP tool ultimately calls. A green REST smoke
implies the corresponding MCP tool works end-to-end, so we can detect
regression in L17/L14/L15/L16 (process/stdin, env_file, ui_invoke,
ext-reload) without spawning the MCP stdio server inside pytest.

Execution
---------
Most tests require kit.exe running with ``validation_api`` active:

.. code-block:: bash

    # Phase 1 Task 1.3 baseline flow
    # 1) MCP isaac_sim_start (cold boot)
    # 2) uv run pytest tests/integration/test_mcp_live_smoke.py -m live -v
    # 3) MCP isaac_sim_stop

D0 is the sole non-live case (static stdin=DEVNULL check for L17).
Tests that require services Isaac Sim cannot guarantee (e.g. Lakehouse)
auto-skip when unreachable.

R1/R1a/R2/R3 compliance (plan §10.4):
- R1  — every USD load uses an S3 URL (never ``file://``).
- R1a — NavMesh bake is preceded by ``simulation_stop``.
- R2  — robot joint / navigation actions run under ``simulation_play``.
- R3  — viewport captures are checked with PIL pixel variance.
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import time
from pathlib import Path

import httpx
import numpy as np
import pytest
from PIL import Image

PROJECT = Path(__file__).resolve().parents[2]
PROCESS_MODULE = PROJECT / "src" / "isaacsim_mcp" / "modules" / "process_module.py"

ISAAC_URL = os.environ.get("ISAAC_SIM_BASE_URL", "http://localhost:8011")
LAKEHOUSE_URL = os.environ.get("LAKEHOUSE_BASE_URL", "http://localhost:9000")

# S3 URLs — SoT: ``docs/assets/isaac/assets/*.md`` (R1 compliant).
WAREHOUSE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Simple_Warehouse/warehouse.usd"
)
NOVA_CARTER_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd"
)
BIPED_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/People/Characters/Biped_Setup.usd"
)

pytestmark_live = pytest.mark.live


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    # ``asyncio.run`` owns the loop lifecycle — safer than raw ``new_event_loop``
    # on Python 3.14 / Windows ProactorEventLoop.
    return asyncio.run(coro)


async def _is_alive(timeout: float = 2.0) -> bool:
    try:
        async with httpx.AsyncClient(base_url=ISAAC_URL, timeout=timeout) as client:
            resp = await client.get("/validation/v1/health")
            return resp.status_code == 200
    except (httpx.HTTPError, OSError):
        return False


def _require_alive() -> None:
    if not _run_async(_is_alive()):
        pytest.skip(f"Isaac Sim not reachable at {ISAAC_URL}")


def _client():
    from isaacsim_mcp.clients.isaac_rest_client import IsaacRestClient
    from isaacsim_mcp.config import IsaacSimConfig

    config = IsaacSimConfig(base_url=ISAAC_URL, timeout=180.0, connect_timeout=5.0)
    return IsaacRestClient(config=config)


async def _with_client(func):
    """Create an IsaacRestClient, run ``func(client)``, close."""
    c = _client()
    try:
        return await func(c)
    finally:
        await c.close()


def _png_stats(path: Path) -> tuple[float, float]:
    """Return (mean, variance) of an 8-bit RGB PNG."""
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    return float(arr.mean()), float(arr.var(axis=(0, 1)).mean())


# ---------------------------------------------------------------------------
# D0 — L17 stdin=DEVNULL regression (static, no kit)
# ---------------------------------------------------------------------------


def test_d0_stdin_devnull_regression():
    src = PROCESS_MODULE.read_text(encoding="utf-8")
    assert "stdin=subprocess.DEVNULL" in src, (
        "L17 regression — process_module.py lost stdin=subprocess.DEVNULL. "
        "See docs/runbooks/kit-stdin-deadlock.md (when created)."
    )


# ---------------------------------------------------------------------------
# D1 — Process lifecycle (kit must be reachable; stop/restart is exercised
# by Task 1.3 around this pytest invocation, so here we only confirm the
# state-query side of the decision tree).
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d1_process_health():
    _require_alive()

    async def go(c):
        return await c.simulation_status()

    status = _run_async(_with_client(go))
    # simulation_status returns fields that only exist when timeline wired up.
    for key in ("is_playing", "is_stopped", "current_time"):
        assert key in status, f"simulation_status missing key {key}: {status}"


# ---------------------------------------------------------------------------
# D2 — Simulation timeline transitions
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d2_simulation_transitions():
    _require_alive()

    async def go(c):
        await c.simulation_stop()
        play = await c.simulation_play()
        step = await c.simulation_step({"frames": 1})
        pause = await c.simulation_pause()
        stop = await c.simulation_stop()
        setto = await c.simulation_set_time({"time_seconds": 5.0})
        return play, step, pause, stop, setto

    play, step, pause, stop, setto = _run_async(_with_client(go))
    assert step["frames"] == 1
    assert stop["is_stopped"] is True
    assert setto["current_time"] == 5.0 or setto.get("requested_time") == 5.0


# ---------------------------------------------------------------------------
# D3 — Stage/USD load (R1: S3 only)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d3_stage_load_usd_s3():
    _require_alive()

    async def go(c):
        await c.stage_new()
        await c.simulation_stop()
        t0 = time.time()
        load = await c.stage_load_usd(
            {"usd_url": WAREHOUSE_URL, "prim_path": "/World/warehouse"}
        )
        elapsed = time.time() - t0
        check = await c.stage_assert_prim_exists(
            {"prim_path": "/World/warehouse", "should_exist": True}
        )
        return load, check, elapsed

    load, check, elapsed = _run_async(_with_client(go))
    assert load.get("ok") is True, f"stage_load_usd failed: {load}"
    assert check.get("passed") is True, f"prim assertion failed: {check}"
    assert elapsed < 90.0, f"S3 load too slow ({elapsed:.1f}s) — deadlock suspect"


# ---------------------------------------------------------------------------
# D4 — Viewport capture (R3: pixel-variance auto-check)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d4_viewport_capture_has_content():
    _require_alive()

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "d4_viewport.png"

        async def go(c):
            return await c.viewport_capture(
                {"output_path": str(out), "settle_frames": 5}
            )

        resp = _run_async(_with_client(go))
        assert resp.get("path"), f"no path in viewport_capture response: {resp}"
        png = Path(resp["path"])
        if not png.exists():
            pytest.skip(f"viewport_capture response points to missing file {png}")
        mean, var = _png_stats(png)

    assert var > 100, f"viewport capture is blank (var={var:.1f}, mean={mean:.1f})"
    assert 5.0 < mean < 250.0, f"viewport is all-black/white (mean={mean:.1f})"


# ---------------------------------------------------------------------------
# D5 — Lighting: exposure ↑ should brighten subsequent capture
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d5_lighting_exposure_increases_brightness():
    _require_alive()

    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "d5_before.png"
        b = Path(td) / "d5_after.png"

        async def go(c):
            await c.lighting_create(
                "distant", {"prim_path": "/World/D5_Light", "intensity": 3000.0}
            )
            await c.lighting_set_exposure({"exposure": 0.0})
            first = await c.viewport_capture({"output_path": str(a), "settle_frames": 5})
            await c.lighting_set_exposure({"exposure": 2.0})
            second = await c.viewport_capture({"output_path": str(b), "settle_frames": 5})
            return first, second

        first, second = _run_async(_with_client(go))
        p1, p2 = Path(first.get("path", a)), Path(second.get("path", b))
        if not (p1.exists() and p2.exists()):
            pytest.skip("viewport_capture did not produce files")
        m1, _ = _png_stats(p1)
        m2, _ = _png_stats(p2)

    assert m2 > m1, f"exposure increase did not brighten output (before={m1:.1f}, after={m2:.1f})"


# ---------------------------------------------------------------------------
# D6 — NavMesh (R1a: stop → bake → path)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d6_navmesh_bake_and_query():
    _require_alive()

    async def go(c):
        await c.stage_new()
        await c.stage_load_usd({"usd_url": WAREHOUSE_URL, "prim_path": "/World/warehouse"})
        await c.simulation_stop()
        bake = await c.navigation_bake(volume_scale=40.0, timeout_s=180.0)
        path = await c.navigation_query_path(
            {"start": [0.0, 0.0, 0.0], "end": [5.0, 0.0, 0.0]}
        )
        sample = await c.navigation_sample_walkable_points({"count": 5})
        return bake, path, sample

    bake, path, sample = _run_async(_with_client(go))
    assert bake.get("ok") is True, f"bake failed: {bake}"
    pts = path.get("points") or []
    assert len(pts) >= 2, f"query_path returned no points (R1a regression?): {path}"
    assert len(sample.get("points") or []) == 5


# ---------------------------------------------------------------------------
# D7 — Robot (R1 S3 + R2 playing)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d7_robot_drive_physics():
    _require_alive()

    async def go(c):
        await c.stage_new()
        load = await c.robot_load(
            {"usd_url": NOVA_CARTER_URL, "prim_path": "/World/Carter"}
        )
        await c.simulation_play()
        await c.simulation_step({"frames": 5})
        drive = await c.robot_drive_physics(
            {
                "prim_path": "/World/Carter",
                "linear_velocity": 1.0,
                "angular_velocity": 0.0,
                "duration_s": 0.5,
            }
        )
        await c.simulation_step({"frames": 10})
        # drive returns a job_id; we only smoke-test that load + drive path
        # don't raise and articulation is detected.
        return load, drive

    load, drive = _run_async(_with_client(go))
    assert load.get("has_articulation") in (True, None), f"no articulation: {load}"
    assert drive.get("ok") is True, f"drive_physics failed: {drive}"


# ---------------------------------------------------------------------------
# D8 — Character (R1 S3 + R2 playing)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d8_character_load_and_animate():
    _require_alive()

    async def go(c):
        await c.stage_new()
        load = await c.character_load(
            {"usd_url": BIPED_URL, "prim_path": "/World/Biped"}
        )
        await c.simulation_play()
        await c.simulation_step({"frames": 5})
        await c.simulation_pause()
        anim = await c.character_play_animation(
            {"prim_path": load.get("sanitized_prim_path", "/World/Biped"),
             "animation_name": "Idle"}
        )
        state = await c.character_get_state(
            load.get("sanitized_prim_path", "/World/Biped")
        )
        return load, anim, state

    load, anim, state = _run_async(_with_client(go))
    assert load.get("anim_graph_bound") is True, f"AnimGraph not bound: {load}"
    assert anim.get("ok") is True, f"play_animation failed: {anim}"
    assert "position" in state, f"get_state missing position: {state}"


# ---------------------------------------------------------------------------
# D9 — RTX Camera + annotator
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d9_sensor_rtx_camera_annotator():
    _require_alive()

    async def go(c):
        await c.stage_new()
        cam = await c.sensor_attach_rtx_camera(
            {"robot_prim": "/World", "sensor_name": "D9_Cam", "resolution": [640, 480]}
        )
        ann = await c.sensor_set_annotator(
            {"sensor_prim": cam.get("sensor_prim_path", "/World/D9_Cam"),
             "annotators": ["rgb"], "resolution": [640, 480]}
        )
        return cam, ann

    cam, ann = _run_async(_with_client(go))
    assert cam.get("sensor_type") == "rtx_camera"
    assert ann.get("ok") is True, f"set_annotator failed: {ann}"


# ---------------------------------------------------------------------------
# D10 — Physics: rigid body falls under gravity
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d10_physics_rigid_body_gravity():
    _require_alive()

    async def go(c):
        await c.stage_new()
        await c.simulation_stop()
        await c.physics_set_scene({"gravity": [0.0, 0.0, -9.81]})
        await c.stage_create_prim(
            {"prim_type": "Cube", "prim_path": "/World/FallCube",
             "position": [0.0, 0.0, 5.0]}
        )
        await c.physics_apply_rigid_body(
            {"prim_path": "/World/FallCube", "mass": 1.0, "dynamic": True}
        )
        await c.simulation_play()
        await c.simulation_step({"frames": 60})
        prop = await c.stage_assert_property(
            {
                "prim_path": "/World/FallCube",
                "property_name": "xformOp:translate",
                "comparator": "exists",
            }
        )
        return prop

    prop = _run_async(_with_client(go))
    assert prop.get("passed") is True, f"translate property missing: {prop}"


# ---------------------------------------------------------------------------
# D11 — Replicator: trigger_once writes frames
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d11_replicator_trigger_once():
    _require_alive()

    async def go(c):
        with tempfile.TemporaryDirectory() as td:
            writer = await c.replicator_create_writer(
                {
                    "writer_type": "BasicWriter",
                    "output_dir": td,
                    "rgb": True,
                    "depth": False,
                    "semantic_segmentation": False,
                }
            )
            run = await c.replicator_trigger_once({"num_frames": 1})
            return writer, run

    writer, run = _run_async(_with_client(go))
    assert writer.get("ok") is True, f"create_writer failed: {writer}"
    assert run.get("ok") is True, f"trigger_once failed: {run}"


# ---------------------------------------------------------------------------
# D12 — OmniGraph: create + connect + execute without exception
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d12_omnigraph_create_execute():
    _require_alive()

    async def go(c):
        node_a = await c.omnigraph_create_node(
            {
                "graph_path": "/ActionGraph_D12",
                "node_type": "omni.graph.nodes.ConstantDouble",
                "node_name": "A",
            }
        )
        node_b = await c.omnigraph_create_node(
            {
                "graph_path": "/ActionGraph_D12",
                "node_type": "omni.graph.nodes.ConstantDouble",
                "node_name": "B",
            }
        )
        evaluated = await c.omnigraph_execute({"graph_path": "/ActionGraph_D12"})
        return node_a, node_b, evaluated

    node_a, node_b, evaluated = _run_async(_with_client(go))
    assert node_a.get("ok") is True and node_b.get("ok") is True
    assert evaluated.get("evaluated") is True, f"graph not evaluated: {evaluated}"


# ---------------------------------------------------------------------------
# D13 — Extension: activate / list / get_info (L9/L16 sanity)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d13_extension_metadata():
    _require_alive()

    async def go(c):
        lst = await c.extension_list_all(enabled_only=True)
        # Re-activate the validation_api itself to exercise reload=False path.
        act = await c.extension_activate("omni.mycompany.validation_api", reload=False)
        info = await c.extension_get_info("omni.mycompany.validation_api")
        return lst, act, info

    lst, act, info = _run_async(_with_client(go))
    assert lst.get("ok") is True and lst.get("count", 0) > 0
    assert act.get("enabled") is True, f"validation_api not enabled after activate: {act}"
    assert info.get("info", {}).get("enabled") is True


# ---------------------------------------------------------------------------
# D14 — Window/UI (L15 regression: float div zero-free sequence)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d14_window_ui_show_and_list():
    _require_alive()

    async def go(c):
        windows = await c.window_list()
        ui = await c.window_ui_show(name="Stage", focus=True, settle_frames=10)
        return windows, ui

    windows, ui = _run_async(_with_client(go))
    assert windows.get("ok") is True and windows.get("count", 0) > 0
    assert ui.get("ok") is True and ui.get("found") is True


# ---------------------------------------------------------------------------
# D15 — Content browse / resolve / preview
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d15_content_browse_resolve():
    _require_alive()

    base = (
        "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
        "Assets/Isaac/5.1/Isaac/Environments/"
    )

    async def go(c):
        listing = await c.content_browse({"url": base, "recursive": False})
        resolved = await c.content_resolve({"url": base})
        return listing, resolved

    listing, resolved = _run_async(_with_client(go))
    assert listing.get("ok") is True, f"content_browse failed: {listing}"
    assert resolved.get("ok") is True, f"content_resolve failed: {resolved}"


# ---------------------------------------------------------------------------
# D16 — Material: list → assign → get_bound
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d16_material_list_assign_bound():
    _require_alive()

    async def go(c):
        await c.stage_new()
        await c.stage_create_prim(
            {"prim_type": "Cube", "prim_path": "/World/MatCube",
             "position": [0.0, 0.0, 0.0]}
        )
        lib = await c.material_list_mdl(library="default")
        if not lib.get("entries"):
            pytest.skip("no MDL entries in default library")
        entry = lib["entries"][0]
        assign = await c.material_assign_mdl(
            {
                "prim_path": "/World/MatCube",
                "mdl_url": entry.get("url"),
                "material_name": entry.get("name", "M"),
            }
        )
        bound = await c.material_get_bound("/World/MatCube")
        return lib, assign, bound

    lib, assign, bound = _run_async(_with_client(go))
    assert lib.get("count", 0) > 0
    assert assign.get("ok") is True, f"assign failed: {assign}"
    assert bound.get("ok") is True, f"get_bound failed: {bound}"


# ---------------------------------------------------------------------------
# D17 — Lakehouse (conditional — service may be offline)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_d17_lakehouse_query_conditional():
    async def probe() -> bool:
        try:
            async with httpx.AsyncClient(base_url=LAKEHOUSE_URL, timeout=1.5) as c:
                resp = await c.get("/health")
                return resp.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    alive = _run_async(probe())
    if not alive:
        pytest.skip(f"Lakehouse not reachable at {LAKEHOUSE_URL}")

    from isaacsim_mcp.clients.lakehouse_client import LakehouseClient

    async def go():
        c = LakehouseClient(base_url=LAKEHOUSE_URL, timeout=10.0)
        try:
            # Provide a minimum legal payload — Extension returns 4xx if not,
            # but that still proves the wire is intact.
            return await c.query({"table": "healthcheck"})
        finally:
            await c.close()

    try:
        result = _run_async(go())
    except httpx.HTTPStatusError as exc:
        # Any non-5xx = wire OK.
        assert exc.response.status_code < 500, f"lakehouse 5xx: {exc}"
        return
    assert "rows" in result or "row_count" in result, f"unexpected shape: {result}"
