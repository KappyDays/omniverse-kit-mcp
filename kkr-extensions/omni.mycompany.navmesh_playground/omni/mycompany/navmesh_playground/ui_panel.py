"""UI panel for NavMesh Playground. English-only text (Kit 107 font atlas)."""
from __future__ import annotations

import asyncio
from typing import Callable

import carb
import omni.kit.async_engine
import omni.ui as ui


WAREHOUSE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Simple_Warehouse/full_warehouse.usd"
)


SIT_VARIANTS = ["SitIdle", "SitTalk", "SitReading"]


class NavMeshPlaygroundPanel:

    def __init__(
        self,
        agent_manager,
        people_controller,
        robot_controller,
        load_warehouse_cb: Callable[[], "asyncio.Future"],
    ):
        self._agent_manager = agent_manager
        self._people_controller = people_controller
        self._robot_controller = robot_controller
        self._load_warehouse_cb = load_warehouse_cb
        self._status_label: ui.Label | None = None
        self._triangles_label: ui.Label | None = None
        self._agents_container: ui.VStack | None = None
        self._spawn_type_combo: ui.ComboBox | None = None
        self._spawn_sit_combo: ui.ComboBox | None = None
        self._spawn_count_field: ui.IntField | None = None
        self._status_log: ui.Label | None = None
        self._status_history: list[str] = []
        self._window: ui.Window | None = None
        # Defer _refresh_agents to avoid omni.ui Container::clear during draw
        self._refresh_pending: bool = False

    def build(self) -> ui.Window:
        # fswatcher reload race: previous on_shutdown destroy may not have
        # finished Workspace deregister before this build runs, leaving a
        # duplicate "NavMesh Playground" entry. Sweep any existing instance
        # before constructing to keep widget tree walkers from picking up the
        # zombie ("found 2 windows" warning).
        try:
            existing = ui.Workspace.get_window("NavMesh Playground")
            if existing is not None:
                existing.visible = False
                existing.destroy()
        except Exception as exc:
            carb.log_warn(f"[navmesh_playground] zombie sweep failed: {exc}")
        self._window = ui.Window("NavMesh Playground", width=360, height=720)
        with self._window.frame:
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                with ui.VStack(spacing=4, height=0):
                    # Stage section
                    with ui.CollapsableFrame("Stage", collapsed=False, name="frame_stage"):
                        with ui.VStack(spacing=4, height=0):
                            ui.Button(
                                "Load Warehouse", name="load_warehouse",
                                tooltip="Load Simple_Warehouse/full_warehouse.usd from S3 "
                                        "(deadlock-safe CreatePayloadCommand). No-op if "
                                        "already loaded.",
                                clicked_fn=self._on_load_warehouse, height=28,
                            )

                    # NavMesh section
                    with ui.CollapsableFrame("NavMesh", collapsed=False, name="frame_navmesh"):
                        with ui.VStack(spacing=4, height=0):
                            ui.Button("Bake (Stage)", name="bake_stage",
                                      tooltip="Bake NavMesh using EXISTING NavMeshVolume(s) "
                                              "in the stage. Stops timeline first (R1a).",
                                      clicked_fn=self._on_bake_stage, height=28)
                            ui.Button("Bake (New)", name="bake_new",
                                      tooltip="Create a new 30m NavMeshVolume(Include) "
                                              "centered at origin and bake.",
                                      clicked_fn=self._on_bake_new, height=28)
                            ui.Button("Bake (Only Warehouse)", name="bake_only_warehouse",
                                      tooltip="Warehouse demo bake: drops the canonical "
                                              "Include + Exclude NavMeshVolumes sized for "
                                              "Simple_Warehouse (Include 35x87x4.83 hugging "
                                              "the floor at z=1.45, Exclude 2x2.6x2 marking "
                                              "a hazard zone) and bakes. Skips creation if "
                                              "a volume with the same prim_path already exists.",
                                      clicked_fn=self._on_bake_only_warehouse, height=28)
                            ui.Button("Toggle Overlay", name="toggle_overlay",
                                      tooltip="Toggle walkable overlay (carb.settings).",
                                      clicked_fn=self._on_toggle_overlay, height=28)
                            ui.Button("Preview Paths", name="preview_paths",
                                      tooltip="Draw the NavMesh shortest-path each agent "
                                              "would follow from its Start to Goal as a "
                                              "BasisCurves under /World/NavMeshPaths/. "
                                              "Green = People, Blue = Robot. Re-click to "
                                              "refresh after editing Start/Goal.",
                                      clicked_fn=self._on_preview_paths, height=28)
                            ui.Button("Clear Paths", name="clear_paths",
                                      tooltip="Remove all path visualizations (the "
                                              "/World/NavMeshPaths scope).",
                                      clicked_fn=self._on_clear_paths, height=28)
                            self._triangles_label = ui.Label("Triangles: 0", name="triangles_label",
                                                             height=20)

                    # Spawn section
                    with ui.CollapsableFrame("Spawn", collapsed=False, name="frame_spawn"):
                        with ui.VStack(spacing=4, height=0):
                            with ui.HStack(height=24):
                                ui.Label("Type:", width=50)
                                self._spawn_type_combo = ui.ComboBox(
                                    0, "People", "Robot", name="spawn_type",
                                    tooltip="Spawn category.",
                                )
                            with ui.HStack(height=24):
                                ui.Label("Sit:", width=50)
                                self._spawn_sit_combo = ui.ComboBox(
                                    0, *SIT_VARIANTS, name="spawn_sit_variant",
                                    tooltip="Sit animation variant (People only).",
                                )
                            with ui.HStack(height=24):
                                ui.Label("Count:", width=50)
                                self._spawn_count_field = ui.IntField(name="spawn_count")
                                self._spawn_count_field.model.set_value(1)
                            ui.Button("Spawn @ Random Walkable", name="spawn_random",
                                      tooltip="Spawn N agents at NavMesh-sampled walkable points.",
                                      clicked_fn=self._on_spawn_random, height=28)

                    # Agents section
                    with ui.CollapsableFrame("Agents", collapsed=False, name="frame_agents"):
                        self._agents_container = ui.VStack(spacing=4, height=0)
                        with self._agents_container:
                            ui.Label("(no agents)", name="agents_empty_label", height=20)

                    # Simulation section
                    with ui.CollapsableFrame("Simulation", collapsed=False, name="frame_sim"):
                        with ui.VStack(spacing=4, height=0):
                            ui.Button("Sim Play", name="sim_play",
                                      tooltip="Start timeline.", clicked_fn=self._on_sim_play,
                                      height=28)
                            ui.Button("Pause", name="sim_pause",
                                      clicked_fn=self._on_sim_pause, height=28)
                            ui.Button("Stop", name="sim_stop",
                                      clicked_fn=self._on_sim_stop, height=28)
                            ui.Button("Reset All Agents", name="reset_all",
                                      tooltip="Remove all spawned agents. Warehouse stays.",
                                      clicked_fn=self._on_reset_all, height=28)

                    # Status Log section (사용자 요구 — history 누적)
                    with ui.CollapsableFrame("Status Log", collapsed=False, name="frame_status"):
                        with ui.ScrollingFrame(height=120,
                                               horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                                               vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED):
                            self._status_log = ui.Label("(ready)",
                                                        name="status_log",
                                                        word_wrap=True,
                                                        alignment=ui.Alignment.LEFT_TOP)
                    # Latest message (always visible — bottom of window)
                    self._status_label = ui.Label("Stage: not_loaded",
                                                  name="status_label", height=20)

        return self._window

    # ---------- Button callbacks ----------

    def _on_load_warehouse(self) -> None:
        # Sync GUI drag&drop equivalent — UI thread direct CreatePayloadCommand.
        # Async run_coroutine 경로는 character/sub-mesh-heavy USD 에서
        # silent crash 재현 (validation 2026-04-23). Warehouse 는 OK 였지만
        # 일관성 위해 sync 통일.
        from .usd_loader import safe_load_usd_sync
        try:
            self._set_status("Loading warehouse...")
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            existing = stage.GetPrimAtPath("/World/Warehouse")
            if existing and existing.IsValid():
                self._set_status("Warehouse already loaded")
                return
            result = safe_load_usd_sync(
                usd_url=WAREHOUSE_URL, prim_path="/World/Warehouse",
                position=[0.0, 0.0, 0.0],
            )
            self._set_status(f"Warehouse loaded: {result.get('prim_path')}")
        except Exception as exc:
            carb.log_error(f"[navmesh_playground] load failed: {exc}")
            self._set_status(f"Load failed: {exc}")

    def _on_bake_stage(self) -> None:
        """Bake using existing NavMeshVolume prims in the stage (warehouse 내장)."""
        omni.kit.async_engine.run_coroutine(self._bake_async(create_volume=False))

    def _on_bake_new(self) -> None:
        """Create a fresh 30m NavMeshVolume(Include) at origin and bake."""
        omni.kit.async_engine.run_coroutine(self._bake_async(create_volume=True))

    def _on_bake_only_warehouse(self) -> None:
        """Warehouse-tuned bake: ensures the canonical Include + Exclude
        NavMeshVolumes exist with the exact Transform / Scale / Type that
        cover Simple_Warehouse properly, then bakes.

        The user originally observed the working values when authoring the
        warehouse demo and asked the button to recreate them deterministically:
          • /World/NavMeshVolume      Include  scale (35.03, 86.92,  4.83)  translate (-11.89, -8.54,  1.45)
          • /World/NavMeshVolume_01   Exclude  scale ( 2.00,  2.60,  2.00)  translate (-25.71,  1.14,  0.00)

        Idempotent — if a prim already exists at the target path it is left
        alone (so the user can hand-tune positions and re-bake without
        being overwritten).
        """
        omni.kit.async_engine.run_coroutine(self._bake_only_warehouse_async())

    async def _bake_only_warehouse_async(self) -> None:
        try:
            self._set_status("Ensuring warehouse-tuned NavMeshVolumes...")
            created_summary = _ensure_warehouse_navmesh_volumes()
            self._set_status(
                "Warehouse-tuned volumes ready:\n" + "\n".join(created_summary)
                + "\nBaking..."
            )
            await self._bake_async(create_volume=False)
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] bake_only_warehouse failed: {exc}")
            self._set_status(f"Bake (Only Warehouse) failed: {exc}")

    async def _bake_async(self, create_volume: bool) -> None:
        """Async bake — yields the Kit main loop between polls.

        Sync `time.sleep` would block Kit's main thread for the entire bake
        duration; the navigation worker depends on that thread to advance,
        so the previous sync implementation had `start_navmesh_baking()`
        return False or produce 0 triangles. Mirrors validation_api's
        navigation_service async polling pattern.
        """
        try:
            import omni.kit.app
            import omni.timeline
            import omni.usd
            app = omni.kit.app.get_app()
            tl = omni.timeline.get_timeline_interface()
            if tl.is_playing():
                tl.stop()
                # Let the timeline transition propagate before we start.
                for _ in range(5):
                    await app.next_update_async()
            stage = omni.usd.get_context().get_stage()
            existing = [
                p.GetPath().pathString for p in stage.Traverse()
                if p.GetTypeName() == "NavMeshVolume"
            ]
            if create_volume:
                _ensure_navmesh_volume()
                existing = [
                    p.GetPath().pathString for p in stage.Traverse()
                    if p.GetTypeName() == "NavMeshVolume"
                ]
                self._set_status(
                    f"NavMeshVolume ready ({len(existing)}); baking..."
                )
            else:
                if not existing:
                    self._set_status(
                        "No NavMeshVolume in stage. Click 'Bake (New)' to create one."
                    )
                    return
                self._set_status(f"Baking with {len(existing)} stage volume(s)...")

            import omni.anim.navigation.core as nav
            iface = nav.acquire_interface()

            # Wait for any prior bake to finish (cache lock release).
            for _ in range(100):  # 100 frames ~ 1.6 s @ 60 fps
                try:
                    if not bool(iface.is_navmesh_baking()):
                        break
                except Exception:  # noqa: BLE001
                    break
                await app.next_update_async()

            kicked = bool(iface.start_navmesh_baking())
            if not kicked:
                # Yield more frames + retry — sometimes the underlying
                # nav worker is just slow to release the lock.
                for _ in range(30):
                    await app.next_update_async()
                kicked = bool(iface.start_navmesh_baking())
            if not kicked:
                self._set_status(
                    "Bake: start_navmesh_baking returned False after retry. "
                    "Stop timeline and try again, or isaac_sim_restart."
                )
                return

            # Poll is_navmesh_baking — async so the worker thread can run.
            for tick in range(60 * 60):  # ~60 s cap @ 60 fps
                try:
                    if not bool(iface.is_navmesh_baking()):
                        break
                except Exception:  # noqa: BLE001
                    break
                await app.next_update_async()

            mesh = iface.get_navmesh()
            tri_count_fn = getattr(mesh, "get_triangle_count", None) if mesh else None
            n = int(tri_count_fn()) if tri_count_fn else 0
            if self._triangles_label is not None:
                self._triangles_label.text = f"Triangles: {n}"
            volume_kind = "new 30m" if create_volume else f"{len(existing)} stage"
            self._set_status(f"Bake done ({n} tri, {volume_kind} volume)")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] bake failed: {exc}")
            self._set_status(f"Bake failed: {exc}")

    def _on_preview_paths(self) -> None:
        """Draw NavMesh shortest path per agent into stage as BasisCurves."""
        try:
            agents = list(self._agent_manager.list())
            if not agents:
                self._set_status("Preview Paths: no agents to visualise")
                return
            _ensure_path_root()
            drawn = 0
            skipped: list[str] = []
            for a in agents:
                pts = _query_path_points(a.start, a.goal)
                if len(pts) < 2:
                    skipped.append(f"{a.id} (no NavMesh path)")
                    continue
                color = (0.2, 0.95, 0.3) if a.kind == "People" else (0.2, 0.5, 1.0)
                _draw_path_curve(a.id, pts, color)
                drawn += 1
            msg = f"Preview Paths: drew {drawn}/{len(agents)} agent path(s)"
            if skipped:
                msg += " — skipped: " + ", ".join(skipped)
            self._set_status(msg)
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] preview_paths failed: {exc}")
            self._set_status(f"Preview Paths failed: {exc}")

    def _on_clear_paths(self) -> None:
        """Remove all path visualizations (deletes /World/NavMeshPaths)."""
        try:
            removed = _clear_all_path_curves()
            self._set_status(f"Clear Paths: removed {removed} curve(s)")
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] clear_paths failed: {exc}")
            self._set_status(f"Clear Paths failed: {exc}")

    def _on_toggle_overlay(self) -> None:
        try:
            import carb.settings
            key = "/persistent/exts/omni.anim.navigation.core/navMesh/viewNavMesh"
            s = carb.settings.get_settings()
            cur = bool(s.get(key) or False)
            s.set(key, not cur)
            self._set_status(f"Overlay: {'ON' if not cur else 'OFF'}")
        except Exception as exc:
            self._set_status(f"Overlay toggle failed: {exc}")

    def _on_spawn_random(self) -> None:
        """Sync spawn — direct Kit SDK calls only, no validation_api.

        People: ``safe_spawn_character_sync`` (CreatePayloadCommand for
        Biped_Setup + skin payload + ApplyAnimationGraphAPICommand bind).

        Robot: ``safe_load_usd_sync`` (CreatePayloadCommand). Articulation
        initialisation happens lazily on first drive (RobotController._drive
        calls SingleArticulation.initialize() after timeline.play()).

        Sync UI thread is acceptable here — each load completes in a few
        seconds and the panel updates Status Log so the user sees progress.
        """
        try:
            from .usd_loader import safe_load_usd_sync, safe_spawn_character_sync
            from .navmesh_sampler import sample_walkable_points_sync
            from .agent_manager import AgentRecord

            type_model = self._spawn_type_combo.model.get_item_value_model()  # type: ignore[union-attr]
            kind_idx = type_model.as_int if hasattr(type_model, "as_int") else int(type_model.get_value_as_int())
            kind = "People" if kind_idx == 0 else "Robot"
            count = int(self._spawn_count_field.model.get_value_as_int())  # type: ignore[union-attr]
            count = max(1, min(10, count))
            sit_variant = SIT_VARIANTS[
                self._spawn_sit_combo.model.get_item_value_model().as_int  # type: ignore[union-attr]
            ]

            self._set_status(f"Sampling {count} walkable points...")
            try:
                points = sample_walkable_points_sync(count=count, seed=None)
            except Exception as exc:
                carb.log_error(f"[navmesh_playground.spawn] sample failed: {exc!r}")
                self._set_status(f"Sample failed: {exc}")
                return
            if not points:
                self._set_status("No walkable points (bake NavMesh first)")
                return

            import random
            spawned = 0
            if kind == "People":
                skin_pool = [
                    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/People/Characters/F_Business_02/F_Business_02.usd",
                    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/People/Characters/F_Medical_01/F_Medical_01.usd",
                    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/People/Characters/M_Medical_01/M_Medical_01.usd",
                ]
                for pt in points:
                    agent_id = self._agent_manager.allocate_id("People")
                    name_safe = self._agent_manager.sanitize_prim_name(agent_id)
                    skin_url = random.choice(skin_pool)
                    self._set_status(f"Loading {agent_id} ({skin_url.rsplit('/', 1)[-1]})...")
                    try:
                        result = safe_spawn_character_sync(
                            char_name=name_safe, skin_url=skin_url,
                            position=[pt[0], pt[1], pt[2]],
                        )
                    except Exception as exc:
                        carb.log_error(f"[navmesh_playground.spawn] People spawn failed: {exc!r}")
                        self._set_status(f"{agent_id} spawn failed: {exc}")
                        continue
                    rec = AgentRecord(
                        id=agent_id, kind="People",
                        prim_path=result["prim_path"],
                        skel_root_path=result["skel_root_path"],
                        start=(pt[0], pt[1], pt[2]),
                        goal=(pt[0] + 3.0, pt[1] + 3.0, pt[2]),
                        sit_variant=sit_variant,
                        asset_url=skin_url,
                    )
                    self._agent_manager.add(rec)
                    spawned += 1
            else:
                # Robot pool — (name, url, wheel_radius, wheel_base, v_max, w_max).
                # v_max chosen so wheel angular velocity stays sane:
                #   joint_vel_rad_s = v_max / wheel_radius.
                # NovaCarter (r=0.14): 1.0 m/s → 7.1 rad/s — fine.
                # Jetbot      (r=0.03): 1.0 m/s → 33.3 rad/s — too fast for
                #   such a small chassis; 0.3 m/s → 10 rad/s is realistic.
                robot_pool = [
                    ("NovaCarter",
                     "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd",
                     0.14, 0.413, 1.0, 1.2),
                    ("Jetbot",
                     "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd",
                     0.03, 0.1, 0.3, 1.5),
                ]
                for pt in points:
                    agent_id = self._agent_manager.allocate_id("Robot")
                    name_safe = self._agent_manager.sanitize_prim_name(agent_id)
                    rname, url, wr, wb, vmax, wmax = random.choice(robot_pool)
                    prim_path = f"/World/{name_safe}"
                    self._set_status(f"Loading {agent_id} ({rname})...")
                    try:
                        safe_load_usd_sync(
                            usd_url=url, prim_path=prim_path,
                            position=[pt[0], pt[1], pt[2] + wr + 0.02],
                        )
                    except Exception as exc:
                        carb.log_error(f"[navmesh_playground.spawn] Robot spawn failed: {exc!r}")
                        self._set_status(f"{agent_id} spawn failed: {exc}")
                        continue
                    rec = AgentRecord(
                        id=agent_id, kind="Robot",
                        prim_path=prim_path,
                        skel_root_path=prim_path,
                        start=(pt[0], pt[1], pt[2]),
                        goal=(pt[0] + 3.0, pt[1] + 3.0, pt[2]),
                        wheel_radius=wr, wheel_base=wb,
                        v_max=vmax, w_max=wmax,
                        asset_url=url,
                    )
                    self._agent_manager.add(rec)
                    spawned += 1

            self._schedule_refresh_agents()
            self._set_status(f"Spawned {spawned} {kind}")
        except Exception as exc:
            carb.log_error(f"[navmesh_playground] spawn failed: {exc}")
            self._set_status(f"Spawn failed: {exc}")

    def _on_sim_play(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().play()
        self._set_status("Sim: playing")

    def _on_sim_pause(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().pause()
        self._set_status("Sim: paused")

    def _on_sim_stop(self) -> None:
        import omni.timeline
        omni.timeline.get_timeline_interface().stop()
        self._set_status("Sim: stopped")

    def _on_reset_all(self) -> None:
        for a in list(self._agent_manager.list()):
            try:
                if a.kind == "People" and self._people_controller is not None:
                    self._people_controller.remove(a)
                elif a.kind == "Robot" and self._robot_controller is not None:
                    self._robot_controller.remove(a)
            except Exception as exc:
                carb.log_warn(f"[navmesh_playground] reset remove {a.id}: {exc}")
        self._schedule_refresh_agents()
        self._set_status("Reset complete")

    def _set_status(self, text: str) -> None:
        if self._status_label is not None:
            self._status_label.text = text
        # Append to history log (keep last 50 lines)
        import time
        ts = time.strftime("%H:%M:%S")
        self._status_history.append(f"[{ts}] {text}")
        if len(self._status_history) > 50:
            self._status_history = self._status_history[-50:]
        if self._status_log is not None:
            self._status_log.text = "\n".join(self._status_history)

    def _schedule_refresh_agents(self) -> None:
        """Schedule _refresh_agents to next Kit main loop frame.

        Avoids `Container::clear was called during an event or draw` error
        when called from button callbacks. omni.ui forbids container.clear()
        during widget event/draw — must defer to next frame.
        """
        if self._refresh_pending:
            return
        self._refresh_pending = True
        async def _deferred():
            import omni.kit.app
            app = omni.kit.app.get_app()
            await app.next_update_async()
            self._refresh_pending = False
            self._refresh_agents()  # actual rebuild — sync after frame yield
        omni.kit.async_engine.run_coroutine(_deferred())

    # ---------- Agent rows (Phase 3/4) ----------

    def _refresh_agents(self) -> None:
        if self._agents_container is None:
            return
        self._agents_container.clear()
        with self._agents_container:
            agents = self._agent_manager.list()
            if not agents:
                ui.Label("(no agents)", name="agents_empty_label")
                return
            for a in agents:
                self._build_agent_row(a)

    def _build_agent_row(self, a) -> None:
        skin = self._skin_name(a.asset_url)
        with ui.CollapsableFrame(
            f"{a.id}  ({skin})  state={a.state}",
            name=a.id, collapsed=False,
        ):
            with ui.VStack(spacing=2):
                # Start — every FloatField writes back to agent.start so a
                # subsequent _refresh_agents() (triggered when ANOTHER agent
                # gets a Go click) does not destroy the user's typed values.
                # Without these callbacks the rebuilt FloatFields seed from
                # the stale agent.start tuple and the user sees their input
                # "reset" — the exact bug the user reported 2026-04-23.
                with ui.HStack(height=24):
                    ui.Label("Start", width=40)
                    sx = ui.FloatField(name="start_x"); sx.model.set_value(a.start[0])
                    sy = ui.FloatField(name="start_y"); sy.model.set_value(a.start[1])
                    sz = ui.FloatField(name="start_z"); sz.model.set_value(a.start[2])
                    self._bind_xyz_to_record(a, "start", sx, sy, sz)
                    ui.Button(
                        "Set Cur", name="set_start_cur",
                        clicked_fn=lambda a=a, sx=sx, sy=sy, sz=sz:
                            self._set_current_pos(a, "start", sx, sy, sz),
                    )
                # Goal — same callback wiring so multi-agent Goal entry survives.
                with ui.HStack(height=24):
                    ui.Label("Goal", width=40)
                    gx = ui.FloatField(name="goal_x"); gx.model.set_value(a.goal[0])
                    gy = ui.FloatField(name="goal_y"); gy.model.set_value(a.goal[1])
                    gz = ui.FloatField(name="goal_z"); gz.model.set_value(a.goal[2])
                    self._bind_xyz_to_record(a, "goal", gx, gy, gz)
                    ui.Button(
                        "Set Cur", name="set_goal_cur",
                        clicked_fn=lambda a=a, gx=gx, gy=gy, gz=gz:
                            self._set_current_pos(a, "goal", gx, gy, gz),
                    )
                # Kind-specific row
                if a.kind == "People":
                    with ui.HStack(height=24):
                        ui.Label("Sit", width=40)
                        ui.Label(f"{a.sit_variant}")
                        ui.Spacer(width=20)
                        ui.Label("Tol", width=30)
                        tol = ui.FloatField(name="tol"); tol.model.set_value(a.arrival_tol)
                else:
                    with ui.HStack(height=24):
                        ui.Label("v_max", width=50)
                        vf = ui.FloatField(name="v_max"); vf.model.set_value(a.v_max)
                        ui.Label("w_max", width=50)
                        wf = ui.FloatField(name="w_max"); wf.model.set_value(a.w_max)
                        ui.Label("Tol", width=30)
                        tol = ui.FloatField(name="tol"); tol.model.set_value(a.arrival_tol)
                # Action row
                with ui.HStack(height=24):
                    ui.Button(
                        "Go", name="go",
                        clicked_fn=lambda a=a, gx=gx, gy=gy, gz=gz:
                            self._on_agent_go(a, gx, gy, gz),
                    )
                    ui.Button(
                        "Stop", name="stop",
                        clicked_fn=lambda a=a: self._on_agent_stop(a),
                    )
                    ui.Button(
                        "Remove", name="remove",
                        clicked_fn=lambda a=a: self._on_agent_remove(a),
                    )

    def _skin_name(self, url: str) -> str:
        if not url:
            return "?"
        leaf = url.rsplit("/", 1)[-1]
        return leaf.removesuffix(".usd")

    def _bind_xyz_to_record(self, agent, attr_name: str, fx, fy, fz) -> None:
        """Hook value-changed callbacks so user typing immediately writes
        back to ``agent.<attr_name>`` (Start or Goal).

        Without these hooks, agent.start / agent.goal only updated when the
        Go button was clicked — meaning typed values for OTHER agents were
        lost as soon as one agent's Go triggered _schedule_refresh_agents()
        (which destroys + rebuilds every row from the stale record).
        """
        def _sync(_=None, _agent=agent, _attr=attr_name, _fx=fx, _fy=fy, _fz=fz):
            try:
                vals = (
                    float(_fx.model.get_value_as_float()),
                    float(_fy.model.get_value_as_float()),
                    float(_fz.model.get_value_as_float()),
                )
                setattr(_agent, _attr, vals)
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(
                    f"[navmesh_playground] sync {_agent.id}.{_attr} failed: {exc}"
                )
        for f in (fx, fy, fz):
            try:
                f.model.add_value_changed_fn(_sync)
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(
                    f"[navmesh_playground] add_value_changed_fn for {agent.id} "
                    f"{attr_name}: {exc}"
                )

    def _on_agent_go(self, a, gx, gy, gz) -> None:
        # The value-changed callback already keeps agent.goal synced, but
        # do a defensive final read in case the user clicked Go before the
        # callback fired (e.g., immediately after typing without focus loss).
        a.goal = (
            float(gx.model.get_value_as_float()),
            float(gy.model.get_value_as_float()),
            float(gz.model.get_value_as_float()),
        )
        if a.kind == "People" and self._people_controller is not None:
            self._people_controller.go(a)
        elif a.kind == "Robot" and self._robot_controller is not None:
            self._robot_controller.go(a)
        self._schedule_refresh_agents()

    def _on_agent_stop(self, a) -> None:
        if a.kind == "People" and self._people_controller is not None:
            self._people_controller.stop(a)
        elif a.kind == "Robot" and self._robot_controller is not None:
            self._robot_controller.stop(a)
        self._schedule_refresh_agents()

    def _on_agent_remove(self, a) -> None:
        if a.kind == "People" and self._people_controller is not None:
            self._people_controller.remove(a)
        elif a.kind == "Robot" and self._robot_controller is not None:
            self._robot_controller.remove(a)
        # Clean up path preview curve if any (silently no-op if absent).
        try:
            _clear_agent_path_curve(a.id)
        except Exception:  # noqa: BLE001
            pass
        self._schedule_refresh_agents()

    def _set_current_pos(self, a, attr_name, fx, fy, fz) -> None:
        """Read current world position into the given fields + agent record.

        ``attr_name`` is "start" or "goal" — the matching ``agent.<attr>``
        tuple is updated in addition to the FloatField models so the value
        survives the next _refresh_agents() rebuild (otherwise the new
        FloatFields seed from the stale agent record and the user sees
        their Set Cur work disappear when another agent's Go fires refresh).

        Falls back through:
          1. xformOp:translate on parent payload prim (Robot, People parent)
          2. AnimGraph world transform (People — handles SkelRoot under DHGen)
          3. UsdGeom.Imageable.ComputeWorldBound center
        """
        try:
            import omni.usd
            from pxr import UsdGeom, Usd, Gf
            stage = omni.usd.get_context().get_stage()
            pos = None
            # Try the parent payload's xformOp:translate first (set by spawn).
            prim = stage.GetPrimAtPath(a.prim_path)
            if prim and prim.IsValid():
                t_attr = prim.GetAttribute("xformOp:translate")
                if t_attr and t_attr.IsValid():
                    t = t_attr.Get()
                    if t is not None:
                        pos = (float(t[0]), float(t[1]), float(t[2]))
            # People: also try AnimGraph world transform via character_service
            if pos is None and a.kind == "People" and a.skel_root_path:
                try:
                    import carb
                    import omni.anim.graph.core as ag
                    g = ag.get_character(a.skel_root_path)
                    if g is not None:
                        p = carb.Float3(0.0, 0.0, 0.0)
                        r = carb.Float4(0.0, 0.0, 0.0, 0.0)
                        g.get_world_transform(p, r)
                        pos = (float(p.x), float(p.y), float(p.z))
                except Exception:
                    pass
            # Final fallback: imageable bbox center
            if pos is None and prim and prim.IsValid():
                imageable = UsdGeom.Imageable(prim)
                if imageable:
                    bb = imageable.ComputeWorldBound(
                        Usd.TimeCode.Default(), UsdGeom.Tokens.default_,
                    )
                    box = bb.ComputeAlignedBox()
                    center = box.GetMidpoint()
                    pos = (float(center[0]), float(center[1]), float(center[2]))
            if pos is None:
                self._set_status(f"Set Cur: no position resolvable for {a.id}")
                return
            fx.model.set_value(pos[0])
            fy.model.set_value(pos[1])
            fz.model.set_value(pos[2])
            # Mirror to the agent record so a subsequent refresh keeps the
            # value (FloatField value-changed callbacks will also do this,
            # but writing here is defensive in case the model.set_value
            # call above does not always fire change notifications).
            try:
                if attr_name in ("start", "goal"):
                    setattr(a, attr_name, (float(pos[0]), float(pos[1]), float(pos[2])))
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(
                    f"[navmesh_playground] Set Cur record-sync failed "
                    f"({a.id}.{attr_name}): {exc}"
                )
            self._set_status(
                f"Set Cur ({a.id} {attr_name}): "
                f"({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"
            )
        except Exception as exc:
            carb.log_warn(f"[navmesh_playground] set_cur failed: {exc}")
            self._set_status(f"Set Cur failed: {exc}")


async def _sleep_ticks(n: int) -> None:
    import omni.kit.app
    app = omni.kit.app.get_app()
    for _ in range(n):
        await app.next_update_async()


def _volume_type(prim) -> str:
    """Return 'Include' / 'Exclude' for a NavMeshVolume prim."""
    attr = prim.GetAttribute("nav:volume:type")
    if attr and attr.IsValid():
        v = attr.Get()
        if v:
            return str(v)
    return "Include"  # USD default when attr unset


def _ensure_navmesh_volume(scale: float = 30.0) -> str:
    """Create NavMeshVolume(Include) at origin if no Include volume exists.

    Distinguishes Include from Exclude — earlier impl returned the first
    NavMeshVolume of any type, so a stage that had only an Exclude volume
    would erroneously skip Include creation and bake nothing.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    for prim in stage.Traverse():
        if prim.GetTypeName() == "NavMeshVolume" and _volume_type(prim) == "Include":
            return prim.GetPath().pathString

    # CreateNavMeshVolumeCommand: volume_type=0 → Include, 1 → Exclude.
    pre_paths = {
        p.GetPath().pathString
        for p in stage.Traverse() if p.GetTypeName() == "NavMeshVolume"
    }
    omni.kit.commands.execute("CreateNavMeshVolumeCommand", volume_type=0)
    created = None
    for prim in stage.Traverse():
        if prim.GetTypeName() != "NavMeshVolume":
            continue
        if prim.GetPath().pathString in pre_paths:
            continue
        if _volume_type(prim) != "Include":
            continue
        created = prim.GetPath().pathString
        break
    if created is None:
        raise RuntimeError("Include NavMeshVolume creation failed")
    prim = stage.GetPrimAtPath(created)
    s_attr = prim.GetAttribute("xformOp:scale")
    if s_attr.IsValid():
        s_attr.Set(Gf.Vec3d(scale, scale, scale))
    return created


def _ensure_navmesh_exclude_volume(
    center: tuple[float, float, float] = (-10.0, 0.0, 1.5),
    scale: tuple[float, float, float] = (4.0, 4.0, 3.0),
) -> str:
    """Create NavMeshVolume(Exclude) at given center+scale if no Exclude exists.

    Default placement (-10, 0, 1.5) with scale (4,4,3) carves a 4×4×3 m
    no-walk zone inside the 30 m default Include — visible enough to be
    a meaningful demo of "blocked area" behavior. Users can move/scale
    the resulting prim in the Stage panel and re-bake to refit.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    for prim in stage.Traverse():
        if prim.GetTypeName() == "NavMeshVolume" and _volume_type(prim) == "Exclude":
            return prim.GetPath().pathString

    pre_paths = {
        p.GetPath().pathString
        for p in stage.Traverse() if p.GetTypeName() == "NavMeshVolume"
    }
    omni.kit.commands.execute("CreateNavMeshVolumeCommand", volume_type=1)
    created = None
    for prim in stage.Traverse():
        if prim.GetTypeName() != "NavMeshVolume":
            continue
        if prim.GetPath().pathString in pre_paths:
            continue
        if _volume_type(prim) != "Exclude":
            continue
        created = prim.GetPath().pathString
        break
    if created is None:
        raise RuntimeError("Exclude NavMeshVolume creation failed")

    prim = stage.GetPrimAtPath(created)
    t_attr = prim.GetAttribute("xformOp:translate")
    if t_attr.IsValid():
        t_attr.Set(Gf.Vec3d(*center))
    s_attr = prim.GetAttribute("xformOp:scale")
    if s_attr.IsValid():
        s_attr.Set(Gf.Vec3d(*scale))
    return created


# ---------------------------------------------------------------------------
# Path visualization helpers (Preview Paths / Clear Paths)
# ---------------------------------------------------------------------------

_PATHS_ROOT = "/World/NavMeshPaths"


def _ensure_path_root() -> None:
    """Define a Scope at /World/NavMeshPaths if absent."""
    import omni.usd
    from pxr import Sdf, UsdGeom
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    if not stage.GetPrimAtPath(_PATHS_ROOT).IsValid():
        UsdGeom.Scope.Define(stage, Sdf.Path(_PATHS_ROOT))


def _query_path_points(
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    """Return baked-NavMesh shortest-path waypoints. [] if unavailable."""
    try:
        import omni.anim.navigation.core as nav
    except ImportError:
        return []
    iface = nav.acquire_interface()
    mesh = iface.get_navmesh()
    if mesh is None:
        return []
    try:
        path = mesh.query_shortest_path(
            carb.Float3(*start),
            carb.Float3(*goal),
            agent_radius=0.25,
            agent_height=1.0,
            straighten=True,
        )
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[navmesh_playground] preview query: {exc}")
        return []
    if path is None:
        return []
    raw = path.get_points() or []
    return [(float(p.x), float(p.y), float(p.z)) for p in raw]


def _draw_path_curve(
    agent_id: str,
    points: list[tuple[float, float, float]],
    color_rgb: tuple[float, float, float],
    line_width: float = 0.05,
    z_offset: float = 0.05,
) -> str:
    """Create / replace a BasisCurves prim that draws the path.

    z_offset lifts the curve slightly above the floor so it does not
    Z-fight with the warehouse mesh. line_width is in scene units
    (meters) — 0.05 m = 5 cm thick line, visible from a few meters
    away without forming a capsule that obstructs the viewport or
    overloads the RTX fragment shader.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Sdf, UsdGeom, Vt, Gf

    safe_id = agent_id.replace("-", "_")
    prim_path = f"{_PATHS_ROOT}/{safe_id}_path"

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    # Replace existing curve so re-clicking refreshes after Start/Goal change.
    if stage.GetPrimAtPath(prim_path).IsValid():
        omni.kit.commands.execute("DeletePrims", paths=[prim_path])

    curves = UsdGeom.BasisCurves.Define(stage, Sdf.Path(prim_path))
    pts = [Gf.Vec3f(float(p[0]), float(p[1]), float(p[2]) + z_offset) for p in points]
    curves.CreatePointsAttr(pts)
    curves.CreateCurveVertexCountsAttr([len(pts)])
    # type=linear → straight segments between waypoints (no bspline curvature
    # bulging the tube outward). basis attr is irrelevant for linear and
    # omitted to avoid renderer ambiguity.
    curves.CreateTypeAttr(UsdGeom.Tokens.linear)
    widths_attr = curves.CreateWidthsAttr([line_width] * len(pts))
    # constant interpolation = single width per curve; cheaper than per-vertex
    # interpolation and matches the visual intent (uniform thin line).
    widths_attr.SetMetadata("interpolation", "constant")
    curves.CreateDisplayColorAttr(
        Vt.Vec3fArray([Gf.Vec3f(color_rgb[0], color_rgb[1], color_rgb[2])])
    )
    return prim_path


def _clear_all_path_curves() -> int:
    """Remove the entire /World/NavMeshPaths scope. Returns curve count."""
    import omni.kit.commands
    import omni.usd

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return 0
    root = stage.GetPrimAtPath(_PATHS_ROOT)
    if not root or not root.IsValid():
        return 0
    count = sum(1 for _ in root.GetChildren())
    omni.kit.commands.execute("DeletePrims", paths=[_PATHS_ROOT])
    return count


def _clear_agent_path_curve(agent_id: str) -> bool:
    """Remove path curve for a single agent (called from controllers' remove)."""
    import omni.kit.commands
    import omni.usd
    safe_id = agent_id.replace("-", "_")
    prim_path = f"{_PATHS_ROOT}/{safe_id}_path"
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        return False
    if not stage.GetPrimAtPath(prim_path).IsValid():
        return False
    omni.kit.commands.execute("DeletePrims", paths=[prim_path])
    return True


# Warehouse-tuned NavMeshVolume canon — observed by the user when they
# first hand-authored the warehouse demo, used by the
# "Bake (Only Warehouse)" button so the same setup is reproducible across
# stage opens.
_WAREHOUSE_NAVMESH_VOLUMES = (
    {
        "prim_path": "/World/NavMeshVolume",
        "volume_type": "Include",
        # Translate Z 1.45049 + Scale Z 4.83158 keep the volume tightly
        # hugging the warehouse floor + walkable shelf height instead of
        # spanning a full 30 m vertical column (user request 2026-04-23).
        # X/Y values unchanged from the original hand-tuned canon.
        "translate": (-11.891392, -8.544497, 1.45049),
        "scale": (35.034203, 86.915306, 4.83158),
    },
    {
        "prim_path": "/World/NavMeshVolume_01",
        "volume_type": "Exclude",
        "translate": (-25.714649, 1.140778, 0.0),
        "scale": (2.0, 2.595942, 2.0),
    },
)


def _ensure_warehouse_navmesh_volumes() -> list[str]:
    """Create the canonical warehouse NavMeshVolume set if absent.

    Idempotent: existing prims at the target paths are left untouched
    (so user hand-tuning survives), missing ones are created with the
    canonical Transform / Scale / Type. Returns one human-readable
    summary line per volume for the panel status log.
    """
    import omni.kit.commands
    import omni.usd
    from pxr import Gf

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    summaries: list[str] = []
    for spec in _WAREHOUSE_NAVMESH_VOLUMES:
        target_path = spec["prim_path"]
        target_type = spec["volume_type"]
        target_t = spec["translate"]
        target_s = spec["scale"]

        existing = stage.GetPrimAtPath(target_path)
        if existing and existing.IsValid() and existing.GetTypeName() == "NavMeshVolume":
            cur_vt = _volume_type(existing)
            t_attr = existing.GetAttribute("xformOp:translate")
            s_attr = existing.GetAttribute("xformOp:scale")
            t = t_attr.Get() if t_attr and t_attr.IsValid() else (0.0, 0.0, 0.0)
            s = s_attr.Get() if s_attr and s_attr.IsValid() else (1.0, 1.0, 1.0)
            summaries.append(
                f"  KEEP {target_path} [{cur_vt}] "
                f"t=({float(t[0]):.2f},{float(t[1]):.2f},{float(t[2]):.2f}) "
                f"s=({float(s[0]):.2f},{float(s[1]):.2f},{float(s[2]):.2f})"
            )
            continue

        # Create — CreateNavMeshVolumeCommand always emits at /World/NavMeshVolume
        # (or _NN suffix). Capture the new prim path then move/rename if needed.
        pre_paths = {
            p.GetPath().pathString
            for p in stage.Traverse() if p.GetTypeName() == "NavMeshVolume"
        }
        cmd_volume_type = 0 if target_type == "Include" else 1
        omni.kit.commands.execute(
            "CreateNavMeshVolumeCommand", volume_type=cmd_volume_type,
        )
        new_path = None
        for prim in stage.Traverse():
            if prim.GetTypeName() != "NavMeshVolume":
                continue
            if prim.GetPath().pathString in pre_paths:
                continue
            if _volume_type(prim) != target_type:
                continue
            new_path = prim.GetPath().pathString
            break
        if new_path is None:
            raise RuntimeError(
                f"Failed to create {target_type} NavMeshVolume for {target_path}"
            )

        # Rename to the canonical path so subsequent calls find it.
        if new_path != target_path:
            omni.kit.commands.execute(
                "MovePrim", path_from=new_path, path_to=target_path,
            )
            new_prim = stage.GetPrimAtPath(target_path)
            if not new_prim or not new_prim.IsValid():
                # Move may have failed (e.g., target path collision). Fall
                # back to whatever path the create produced — bake still
                # honors it because we add it to the volume scan.
                new_prim = stage.GetPrimAtPath(new_path)
                if not new_prim or not new_prim.IsValid():
                    raise RuntimeError(
                        f"NavMeshVolume disappeared after MovePrim "
                        f"{new_path} → {target_path}"
                    )
                target_path = new_path
        else:
            new_prim = stage.GetPrimAtPath(target_path)

        # Apply hardcoded translate / scale.
        t_attr = new_prim.GetAttribute("xformOp:translate")
        if t_attr and t_attr.IsValid():
            t_attr.Set(Gf.Vec3d(*target_t))
        s_attr = new_prim.GetAttribute("xformOp:scale")
        if s_attr and s_attr.IsValid():
            s_attr.Set(Gf.Vec3d(*target_s))

        summaries.append(
            f"  NEW  {target_path} [{target_type}] "
            f"t=({target_t[0]:.2f},{target_t[1]:.2f},{target_t[2]:.2f}) "
            f"s=({target_s[0]:.2f},{target_s[1]:.2f},{target_s[2]:.2f})"
        )

    return summaries
