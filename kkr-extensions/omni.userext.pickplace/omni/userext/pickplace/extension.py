"""PickPlaceWorkshopExtension entry point.

Wiring:
    on_startup → build UI panel + subscribe to update stream (gated on running)
    on_shutdown → cleanup

The UI buttons drive :mod:`scene_builder` + :mod:`cube_spawner` +
:class:`NVIDIAPickPlaceWorker` (per-robot stop-and-grasp cycle). The update
tick advances the worker cycles with the live cube list and the current
sim time.

Task 6 rewrite: replaced ``PickPlaceWorker`` (custom FSM with FrankaAdapter
+ SuctionAttachment) with NVIDIA's ``PickPlaceController`` +
``ParallelGripper`` driven by :class:`NVIDIAPickPlaceWorker`. Cube hold uses
:class:`CubeFreezer` (per-cube velocity zero) instead of SurfaceGripper.
Conveyor velocity remains driven by NVIDIA's ``CreateConveyorBelt``
ActionGraph.
"""
from __future__ import annotations

import asyncio

import carb
import omni.ext

from . import cube_spawner, scene_builder
from .cube_attach import CubeAttach
from .cube_freezer import CubeFreezer
from .metrics import arrival_rate, cube_in_box
from .nvidia_worker import NVIDIAPickPlaceWorker
from .phase_log import PhaseLog
from .reach_assignment import ReachAssigner
from .ui_panel import WorkshopPanel
from .zone_selector import ZoneSelector


_SOURCE = "omni.userext.pickplace"

CUBE_SPAWN_INTERVAL = 3.0
STATUS_THROTTLE = 0.5


def _measure_box_top_plus_clearance(stage, box_path: str, clearance: float = 0.10) -> float:
    """Measure box top z (world) via BBoxCache + add EE drop clearance.

    Used to set the PickPlaceController placing_position.z without any
    hardcoded box-height assumption — auto-adapts to BOX_SCALE / asset
    swap (e.g., switching from small_KLT to a different bin USD).
    """
    from pxr import Sdf, UsdGeom

    box_prim = stage.GetPrimAtPath(Sdf.Path(box_path))
    if not box_prim.IsValid():
        return 0.30  # safe fallback
    bbox_cache = UsdGeom.BBoxCache(0.0, [UsdGeom.Tokens.default_])
    bb = bbox_cache.ComputeWorldBound(box_prim).ComputeAlignedRange()
    if bb.IsEmpty():
        return 0.30
    return float(bb.GetMax()[2]) + float(clearance)


class PickPlaceWorkshopExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id

        self._panel: WorkshopPanel | None = None
        self._update_sub = None
        self._running = False
        self._sim_time = 0.0
        self._last_spawn_t = -CUBE_SPAWN_INTERVAL
        self._status_t = 0.0

        self._scene_builder: scene_builder.SceneBuilder | None = None
        self._assigner: ReachAssigner | None = None
        self._selector: ZoneSelector | None = None
        self._freezer: CubeFreezer | None = None
        self._attach: CubeAttach | None = None
        self._phase_log: PhaseLog | None = None
        self._workers: list[NVIDIAPickPlaceWorker] = []

        self._panel = WorkshopPanel(callbacks={
            "build_scene": self._on_build,
            "start": self._on_start,
            "pause": self._on_pause,
            "reset": self._on_reset,
            "spawn_cube": self._on_spawn_now,
            "dump_state": self._on_dump_state,
        })

        import omni.kit.app
        self._update_sub = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self._on_update, name="pickplace_update")
        )

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        try:
            if self._update_sub is not None:
                self._update_sub.unsubscribe()
        finally:
            self._update_sub = None
        if self._panel is not None:
            self._panel.destroy()
            self._panel = None
        # Best-effort scene teardown so a fresh enable starts clean.
        try:
            scene_builder.reset_builder()
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] scene reset on shutdown raised: {exc!r}")

    # ----- button callbacks -----

    def _on_build(self) -> None:
        self._set_status("building scene...")

        async def _run():
            try:
                builder = await scene_builder.build_full_scene()
                self._scene_builder = builder

                # Physics warm-up: play+pause so articulations populate
                # physics_sim_view (Articulation §, kit-sdk-pitfalls).
                # Task 9 — 8 ticks was insufficient; raised to 30 so the
                # Franka articulation_view is fully populated before
                # initialize() and end_effector RigidPrim binding.
                import omni.timeline, omni.kit.app
                timeline = omni.timeline.get_timeline_interface()
                timeline.play()
                for _ in range(30):
                    await omni.kit.app.get_app().next_update_async()
                # capture_homes is a noop in v4 but kept for symmetry.
                await builder.capture_homes()
                timeline.pause()

                # Wire the assigner / selector / freezer / log + workers.
                import numpy as np
                import omni.usd
                from isaacsim.robot.manipulators.examples.franka.controllers import (  # type: ignore
                    PickPlaceController,
                )

                stage = omni.usd.get_context().get_stage()
                # v5 round-5: REACH_OFFSET = 0.72 m (belt center → robot
                # base). reach_radius matches Franka Panda spec (0.855 m
                # sphere) less a small margin so we only attempt cubes
                # genuinely inside the IK-feasible region — overshooting
                # to e.g. 1.6 m makes ZoneSelector dispatch unreachable
                # cubes, wastes a phase 0-2 cycle, then the controller
                # times out at the IK boundary.
                self._assigner = ReachAssigner(
                    franka_a_pos=scene_builder.FRANKA_A_POS,
                    franka_b_pos=scene_builder.FRANKA_B_POS,
                    reach_radius=0.80,
                )
                self._selector = ZoneSelector(self._assigner)
                self._freezer = CubeFreezer(stage)
                self._attach = CubeAttach(stage)
                self._phase_log = PhaseLog()

                init_failures: list[str] = []
                self._workers = []
                franka_paths = {
                    "A": scene_builder.FRANKA_A_PATH,
                    "B": scene_builder.FRANKA_B_PATH,
                }
                # Place position = box top + 10 cm clearance for EE drop.
                # Box bottom snapped to z=0 by ground_snap.place_on_ground;
                # height = scale × native KLT height. Measured at runtime
                # via BBoxCache so future asset changes auto-propagate.
                #
                # v5 round-5e BUGFIX: previously the release z was
                # BOX_A_POS[2] + _release_z, but _release_z is ALREADY a
                # world-absolute z (box top + clearance), so the addition
                # double-counted by ~0.146 m and pushed the EE target to
                # 0.466 m. PickPlaceController IK could not reach that
                # high at the bin's xy, fell back to a saturated pose
                # short of the bin → cube dropped on the bin's near edge
                # (~1 mm short of cube_in_box). Use the absolute z directly.
                _release_z = _measure_box_top_plus_clearance(
                    stage, scene_builder.BOX_A_PATH, clearance=0.10
                )
                box_a_release = (
                    scene_builder.BOX_A_POS[0],
                    scene_builder.BOX_A_POS[1],
                    _release_z,
                )
                box_b_release = (
                    scene_builder.BOX_B_POS[0],
                    scene_builder.BOX_B_POS[1],
                    _release_z,
                )

                # NVIDIA Franka PickPlaceController default events_dt =
                # [0.008, 0.005, 1, 0.1, 0.05, 0.05, 0.0025, 1, 0.008, 0.08].
                # v5 round-5c: revert to NVIDIA default — round-5b's
                # halved phase 4/5/6 dt (0.025/0.025/0.001) caused phase 6
                # to take 13.6 s (instead of ~1 s), letting EE drift away
                # from placing_position so the cube ended up at a Franka
                # reach-limit fallback position (~0.7 m off the bin center).
                _SLOW_EVENTS_DT = [0.008, 0.005, 1, 0.1, 0.05, 0.05, 0.0025, 1, 0.008, 0.08]
                for key, robot_id, box_pos in (
                    ("A", "franka_A", box_a_release),
                    ("B", "franka_B", box_b_release),
                ):
                    franka = builder.frankas[key]
                    try:
                        franka.initialize()
                        carb.log_warn(f"[{_SOURCE}] franka_{key} initialize OK")
                    except Exception as exc:
                        init_failures.append(f"{key}: {exc!r}")
                        carb.log_error(
                            f"[{_SOURCE}] franka_{key}.initialize() FAILED: {exc!r}"
                        )
                        continue
                    controller = PickPlaceController(
                        name=f"pick_place_controller_{key}",
                        gripper=franka.gripper,
                        robot_articulation=franka,
                        events_dt=_SLOW_EVENTS_DT,
                    )
                    art_ctrl = franka.get_articulation_controller()

                    def _resolver(cube_path: str, _stage=stage) -> np.ndarray:
                        from pxr import Sdf, UsdGeom
                        prim = _stage.GetPrimAtPath(Sdf.Path(cube_path))
                        if not prim.IsValid():
                            return np.zeros(3, dtype=np.float32)
                        xf = UsdGeom.Xformable(prim)
                        m = xf.ComputeLocalToWorldTransform(0.0)
                        t = m.ExtractTranslation()
                        return np.array(
                            [float(t[0]), float(t[1]), float(t[2])],
                            dtype=np.float32,
                        )

                    self._workers.append(
                        NVIDIAPickPlaceWorker(
                            robot_id=robot_id,
                            franka=franka,
                            controller=controller,
                            art_ctrl=art_ctrl,
                            zone_selector=self._selector,
                            freezer=self._freezer,
                            phase_log=self._phase_log,
                            cube_attach=self._attach,
                            panda_hand_path=f"{franka_paths[key]}/panda_hand",
                            box_pos=np.array(list(box_pos), dtype=np.float32),
                            cube_pos_resolver=_resolver,
                        )
                    )

                if init_failures:
                    self._set_status(
                        "BUILD WARN — Franka init failures:\n  "
                        + "\n  ".join(init_failures)
                    )
                else:
                    self._set_status(
                        "scene built\n"
                        f"conveyor: {len(builder.conveyor_paths)} segments\n"
                        f"frankas: {list(builder.frankas.keys())}"
                    )
            except Exception as exc:
                carb.log_error(f"[{_SOURCE}] build failed: {exc!r}")
                self._set_status(f"build failed: {exc!r}")

        asyncio.ensure_future(_run())

    def _on_start(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().play()
        self._running = True
        self._set_status("running")

    def _on_pause(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().pause()
        self._running = False
        self._set_status("paused")

    def _on_reset(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().stop()
        try:
            cube_spawner.clear_all_cubes()
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] clear cubes warning: {exc!r}")
        try:
            cube_spawner.reset_state()
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] spawner reset warning: {exc!r}")
        if self._assigner is not None:
            self._assigner.reset()
        if self._selector is not None:
            self._selector.reset()
        if self._attach is not None:
            self._attach.reset()
        if self._phase_log is not None:
            self._phase_log.clear()
        for w in self._workers:
            try:
                w.reset_state()
            except Exception:
                pass
        self._sim_time = 0.0
        self._last_spawn_t = -CUBE_SPAWN_INTERVAL
        self._running = False
        self._set_status("reset")

    def _on_spawn_now(self) -> None:
        try:
            cube_spawner.spawn_cube(self._sim_time)
            self._set_status(f"spawned cube at t={self._sim_time:0.1f}s")
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] manual spawn failed: {exc!r}")

    def _on_dump_state(self) -> None:
        """Dump in-process state to a JSON file (worker-agnostic).

        Captures EVERY field needed for an independent same-run cross-check:
        raw cube positions (in-process Stage walk, bypasses MCP traversal
        cap) + spawn_count + worker phases + extension-computed metric
        (in_a/in_b/rate via the same cube_in_box used by _update_metrics)
        + actual timeline play state (not self._running).

        Reliability primitives:
          - run_id (uuid4) so the reader can tell consecutive dumps apart
          - completion_marker = "OK" written last, before the atomic rename
          - atomic write: tempfile in same dir + os.replace
          - PICKPLACE_DUMP_PATH env override; default <tempdir>/pickplace_state_dump.json
        """
        import json
        import os
        import tempfile
        import uuid
        from datetime import datetime, timezone

        try:
            import omni.timeline
            import omni.usd
            from pxr import Sdf, UsdGeom

            stage = omni.usd.get_context().get_stage()
            cubes: list[dict] = []
            cubes_root = stage.GetPrimAtPath(Sdf.Path("/World/Cubes"))
            if cubes_root.IsValid():
                for child in cubes_root.GetAllChildren():
                    xf = UsdGeom.Xformable(child)
                    if not xf:
                        continue
                    m = xf.ComputeLocalToWorldTransform(0.0)
                    t = m.ExtractTranslation()
                    cubes.append({
                        "path": str(child.GetPath()),
                        "pos": [float(t[0]), float(t[1]), float(t[2])],
                    })

            workers_dump: list[dict] = []
            for w in getattr(self, "_workers", []) or []:
                entry = {"robot_id": getattr(w, "robot_id", "?")}
                phase = getattr(w, "phase", None)
                if phase is not None:
                    entry["phase"] = getattr(phase, "value", str(phase))
                target = getattr(w, "target_cube", None)
                if target is not None:
                    entry["target_cube"] = target
                workers_dump.append(entry)

            spawn_count = None
            try:
                spawn_count = cube_spawner.get_spawn_count()
            except Exception:
                pass

            spawn_times = None
            for attr in ("get_spawn_times", "spawn_times"):
                fn = getattr(cube_spawner, attr, None)
                if callable(fn):
                    try:
                        spawn_times = list(fn())
                        break
                    except Exception:
                        continue

            phase_log_entries = None
            phase_log = getattr(self, "_phase_log", None)
            if phase_log is not None:
                try:
                    phase_log_entries = phase_log.entries()
                except Exception:
                    pass

            # Same-run extension-computed metric (cube_in_box on the SAME
            # cubes the dump just walked; rules out non-contemporaneous
            # cross-check critique). Codex pass 7 F1: pass MEASURED bounds
            # (klt_geometry computed below — order-of-evaluation handled by
            # deferring this block) so the runtime metric uses live asset
            # geometry instead of the hard-coded KLT_INNER_HALF default in
            # metrics.py. ext_metric is now genuinely independent of the
            # assumed-bound code path.
            ext_metric = None
            ext_metric_bounds_source = "deferred_until_klt_geometry_built"

            # MEASURED KLT bin geometry — replaces the assumed
            # KLT_INNER_HALF constant with a live geometry probe so a reader
            # can verify the metric's hit-test region matches actual asset
            # bounds (codex pass 4 Q4 + pass 5 Q1a: prior pass used
            # BBoxCache.ComputeWorldBound which returned LOCAL bbox for both
            # bins — fix: compute the local (untransformed) bbox via
            # ComputeUntransformedBound + read the prim's world transform
            # separately, then derive world bbox from both. KLT bins are
            # axis-aligned with no rotation/scale, so element-wise add of
            # local bbox + world translate gives the correct world bbox.
            klt_geometry = {}
            try:
                from pxr import Usd as _Usd
                bbox_cache = UsdGeom.BBoxCache(
                    _Usd.TimeCode.Default(),
                    [UsdGeom.Tokens.default_],
                )
                for label, path in (
                    ("Box_A", scene_builder.BOX_A_PATH),
                    ("Box_B", scene_builder.BOX_B_PATH),
                ):
                    bp = stage.GetPrimAtPath(Sdf.Path(path))
                    if not bp.IsValid():
                        klt_geometry[label] = {"error": "prim not found"}
                        continue
                    untransformed = bbox_cache.ComputeUntransformedBound(bp)
                    rng = untransformed.GetRange()
                    lmn, lmx = rng.GetMin(), rng.GetMax()
                    xf = UsdGeom.Xformable(bp)
                    wxf = xf.ComputeLocalToWorldTransform(
                        _Usd.TimeCode.Default()
                    )
                    wtr = wxf.ExtractTranslation()
                    wmn = [
                        float(lmn[0]) + float(wtr[0]),
                        float(lmn[1]) + float(wtr[1]),
                        float(lmn[2]) + float(wtr[2]),
                    ]
                    wmx = [
                        float(lmx[0]) + float(wtr[0]),
                        float(lmx[1]) + float(wtr[1]),
                        float(lmx[2]) + float(wtr[2]),
                    ]
                    klt_geometry[label] = {
                        "local_min": [float(lmn[0]), float(lmn[1]), float(lmn[2])],
                        "local_max": [float(lmx[0]), float(lmx[1]), float(lmx[2])],
                        "world_translate": [float(wtr[0]), float(wtr[1]), float(wtr[2])],
                        "world_min": wmn,
                        "world_max": wmx,
                        "extent": [
                            float(lmx[0] - lmn[0]),
                            float(lmx[1] - lmn[1]),
                            float(lmx[2] - lmn[2]),
                        ],
                    }
            except Exception as exc:
                klt_geometry["error"] = repr(exc)

            # Codex pass 7 F1: now that klt_geometry is built, compute
            # ext_metric using the MEASURED per-bin half-extents
            # (extent / 2). Falls back to default KLT_INNER_HALF only if
            # geometry is degraded (missing prim, exception) — in which case
            # ext_metric_bounds_source flags the degradation explicitly so
            # the reader does not silently trust hard-coded numbers.
            try:
                box_a_geom = klt_geometry.get("Box_A") if isinstance(klt_geometry, dict) else None
                box_b_geom = klt_geometry.get("Box_B") if isinstance(klt_geometry, dict) else None
                if (
                    isinstance(box_a_geom, dict) and isinstance(box_b_geom, dict)
                    and "extent" in box_a_geom and "extent" in box_b_geom
                ):
                    ea = box_a_geom["extent"]
                    eb = box_b_geom["extent"]
                    half_a = (float(ea[0]) / 2.0, float(ea[1]) / 2.0, float(ea[2]) / 2.0)
                    half_b = (float(eb[0]) / 2.0, float(eb[1]) / 2.0, float(eb[2]) / 2.0)
                    a = sum(
                        1 for c in cubes
                        if cube_in_box(tuple(c["pos"]), scene_builder.BOX_A_POS, half_extent=half_a)
                    )
                    b = sum(
                        1 for c in cubes
                        if cube_in_box(tuple(c["pos"]), scene_builder.BOX_B_POS, half_extent=half_b)
                    )
                    rate = arrival_rate(spawn_count or 0, a, b)
                    ext_metric = {"in_a": a, "in_b": b, "rate": rate}
                    ext_metric_bounds_source = "measured_via_BBoxCache"
                else:
                    a = sum(
                        1 for c in cubes
                        if cube_in_box(tuple(c["pos"]), scene_builder.BOX_A_POS)
                    )
                    b = sum(
                        1 for c in cubes
                        if cube_in_box(tuple(c["pos"]), scene_builder.BOX_B_POS)
                    )
                    rate = arrival_rate(spawn_count or 0, a, b)
                    ext_metric = {"in_a": a, "in_b": b, "rate": rate}
                    ext_metric_bounds_source = "fallback_KLT_INNER_HALF_geometry_degraded"
            except Exception as exc:
                carb.log_warn(f"[{_SOURCE}] dump ext_metric failed: {exc!r}")
                ext_metric_bounds_source = f"error: {exc!r}"

            # Actual timeline state (not the extension's own _running flag —
            # external pause via simulation_pause leaves _running stale).
            try:
                tl = omni.timeline.get_timeline_interface()
                tl_state = {
                    "is_playing": bool(tl.is_playing()),
                    "is_stopped": bool(tl.is_stopped()),
                    "current_time": float(tl.get_current_time()),
                }
            except Exception as exc:
                tl_state = {"error": repr(exc)}

            run_id = uuid.uuid4().hex
            payload = {
                "schema_version": 5,
                "run_id": run_id,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "captured_at_sim_time_s": self._sim_time,
                "extension_running_flag": self._running,
                "timeline_state": tl_state,
                "spawn_count": spawn_count,
                "spawn_times": spawn_times,
                "cubes": cubes,
                "workers": workers_dump,
                "phase_log": phase_log_entries,
                "ext_metric_at_dump": ext_metric,
                "ext_metric_bounds_source": ext_metric_bounds_source,
                "klt_geometry_measured": klt_geometry,
                "completion_marker": "OK",
            }

            override = os.environ.get("PICKPLACE_DUMP_PATH")
            out_path = override or os.path.join(
                tempfile.gettempdir(), "pickplace_state_dump.json"
            )
            out_dir = os.path.dirname(out_path) or "."
            os.makedirs(out_dir, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(
                prefix=".pickplace_dump.",
                suffix=".tmp",
                dir=out_dir,
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        pass
                os.replace(tmp_path, out_path)
                # Best-effort directory fsync (Windows often returns
                # EACCES on directory fds — ignore; the artifact is also
                # archived under captures/v3-baseline/state_dump.json).
                try:
                    dir_fd = os.open(out_dir, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except (OSError, AttributeError):
                    pass
            except Exception:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                raise

            carb.log_warn(
                f"[{_SOURCE}] dump_state run_id={run_id} wrote {len(cubes)} "
                f"cubes / spawn_count={spawn_count} / "
                f"ext_metric={ext_metric} / timeline={tl_state} → {out_path}"
            )
            self._set_status(
                f"dumped {len(cubes)} cubes (spawn={spawn_count}) "
                f"run_id={run_id[:8]} → {out_path}"
            )
        except Exception as exc:
            carb.log_error(f"[{_SOURCE}] dump_state failed: {exc!r}")
            self._set_status(f"dump_state failed: {exc!r}")

    # ----- update tick -----

    def _on_update(self, event) -> None:
        if not self._running:
            return
        # Codex pass 6 Defect 1: external simulation_pause does NOT call
        # _on_pause, so self._running stays True. _on_update would keep
        # advancing _sim_time + triggering spawns under paused physics →
        # state_dump.json captured_at_sim_time would diverge from
        # timeline_state.current_time. Gate on the actual timeline state.
        try:
            import omni.timeline
            if not omni.timeline.get_timeline_interface().is_playing():
                return
        except Exception:
            pass
        try:
            payload = event.payload
            dt = float(payload.get("dt", 0.0)) if payload is not None else 0.0
        except Exception:
            dt = 0.0
        if dt <= 0.0:
            dt = 1.0 / 60.0
        self._sim_time += dt
        self._status_t += dt

        if self._sim_time - self._last_spawn_t >= CUBE_SPAWN_INTERVAL:
            try:
                cube_spawner.spawn_cube(self._sim_time)
            except Exception as exc:
                carb.log_warn(f"[{_SOURCE}] spawn cube failed: {exc!r}")
            self._last_spawn_t = self._sim_time

        # Cube list with pos+vel for the worker state machines.
        cubes = self._collect_cubes()
        if self._selector is not None:
            self._selector.update(cubes)

        for w in self._workers:
            try:
                w.tick(now=self._sim_time)
            except Exception as exc:
                carb.log_warn(f"[{_SOURCE}] worker {w.robot_id} tick failed: {exc!r}")

        if self._status_t >= STATUS_THROTTLE:
            self._status_t = 0.0
            wphases = ", ".join(
                f"{w.robot_id}={'idle' if w.target_cube is None else 'busy'}"
                for w in self._workers
            )
            text = (
                f"t={self._sim_time:0.1f}s  cubes={len(cubes)}\n"
                f"{wphases}"
            )
            self._set_status(text)
            self._update_metrics(cubes)

    def _collect_cubes(self) -> list[dict]:
        """Build the worker-tick cube list ``[{path, pos, vel}, ...]``.

        Task 6 wired this to :func:`cube_spawner.list_cubes`, which reads
        live position + linear velocity (from the rigid-body's
        ``physics:velocity`` attribute). The predictive tracker now sees
        non-zero ``vel`` once the timeline is playing, so the lookahead
        actually leads moving cubes along the conveyor.
        """
        try:
            return cube_spawner.list_cubes()
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] list_cubes failed: {exc!r}")
            return []

    def _count_cubes_in_box(
        self, cubes: list[dict], box_pos: tuple[float, float, float]
    ) -> int:
        """Count cubes whose center sits inside the given KLT bin."""
        return sum(1 for c in cubes if cube_in_box(c["pos"], box_pos))

    def _update_metrics(self, cubes: list[dict]) -> None:
        """Refresh the workshop UI metric label (spawned + box arrivals)."""
        panel = getattr(self, "_panel", None)
        if panel is None:
            return
        try:
            spawned = cube_spawner.get_spawn_count()
            in_a = self._count_cubes_in_box(cubes, scene_builder.BOX_A_POS)
            in_b = self._count_cubes_in_box(cubes, scene_builder.BOX_B_POS)
            rate = arrival_rate(spawned, in_a, in_b)
            panel.update_metrics(spawned=spawned, in_a=in_a, in_b=in_b, rate=rate)
        except Exception as exc:
            carb.log_warn(f"[{_SOURCE}] metric update failed: {exc!r}")

    def _set_status(self, text: str) -> None:
        panel = getattr(self, "_panel", None)
        if panel is not None:
            panel.set_status(text)
