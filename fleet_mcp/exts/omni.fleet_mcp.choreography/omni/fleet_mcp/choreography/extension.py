"""Robot Fleet Choreography extension.

on_startup builds the fleet scene; "Choreograph" authors the OmniGraph ActionGraph
skeleton (LIVE-only — omni.graph.* exists only in the Kit runtime). UI is ASCII.
The full waypoint-follow wiring + sim_time formation change are the live integration
points — confirm node types on first run per mcp-upgrade/make_progress/fleet_make.md.
"""
from __future__ import annotations

import carb
import omni.ext
import omni.ui as ui
import omni.usd

from . import config, graph_spec, scene_builder


class FleetChoreographyExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._built = False
        self._window = ui.Window("Robot Fleet Choreography", width=360, height=220)
        with self._window.frame:
            with ui.VStack(spacing=6):
                self._status = ui.Label("Status: idle")
                ui.Button("Build Fleet", clicked_fn=lambda *_a: self._on_build())
                ui.Button("Choreograph", clicked_fn=lambda *_a: self._on_choreograph())
        carb.log_info("[fleet] startup")

    def _on_build(self) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Status: no stage"
            return
        info = scene_builder.build(stage)
        self._built = True
        self._status.text = (
            f"Status: built ({len(info['robots'])} robots, {len(info['waypoints'])} waypoints)"
        )
        carb.log_info(f"[fleet] built {info}")

    def _on_choreograph(self) -> None:
        if not self._built:
            self._status.text = "Status: build fleet first"
            return
        # Schedule as asyncio task — synchronous app.update() loops in UI callbacks
        # corrupt Vulkan after ~30+ ticks (live-observed crash). next_update_async
        # is the deadlock-safe yield.
        import asyncio
        self._status.text = "Status: driving..."
        asyncio.ensure_future(self._choreograph_async())

    async def _choreograph_async(self) -> None:
        try:
            reached = await self._drive_fleet()
            self._status.text = (
                f"Status: {reached}/{len(config.ROBOT_NAMES)} robots reached"
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[fleet] choreograph failed: {exc}")
            self._status.text = f"Status: choreograph error: {exc}"

    async def _drive_fleet(self) -> int:
        """LIVE path: drive 3 Carter via inline DifferentialController + per-tick
        Pure Pursuit toward the formation waypoints, with a sim_time-precise
        triangle->line formation change at config.FORMATION_CHANGE_TIME.

        This is the physics-based controller path (writes joint_velocities) — not
        per-tick teleport. Replaces the previous OmniGraph stub. The OmniGraph
        ActionGraph wiring of equivalent nodes per robot remains a follow-up; the
        controller logic here mirrors validation_api.robot_service.drive_physics."""
        import math
        import omni.kit.app
        import omni.timeline
        from pxr import Gf, Usd, UsdGeom

        from . import path_planner

        stage = omni.usd.get_context().get_stage()
        app = omni.kit.app.get_app()
        tl = omni.timeline.get_timeline_interface()
        if not tl.is_playing():
            tl.play()
            for _ in range(2):
                await app.next_update_async()

        # Resolve isaacsim runtime classes (Kit-only).
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.robot.wheeled_robots.controllers.differential_controller import (
            DifferentialController,
        )

        # Per-robot setup: Articulation + DifferentialController + wheel DOF indices.
        leader_path = [(x, y) for (x, y, _t) in path_planner.leader_schedule()][1:]
        formations = config.FORMATIONS
        robots = []
        for i, name in enumerate(config.ROBOT_NAMES):
            prim_path = f"{config.FLEET_ROOT}/{name}/Model"
            if not stage.GetPrimAtPath(prim_path).IsValid():
                continue
            art = SingleArticulation(prim_path)
            try:
                art.initialize()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[fleet] {name} initialize: {exc}")
            dof_names = list(getattr(art, "dof_names", []) or [])
            def _find(subs):
                for j, dn in enumerate(dof_names):
                    dl = dn.lower()
                    if any(s in dl for s in subs):
                        return j
                return None
            li = _find(["wheel_left", "left_wheel", "joint_wheel_left"])
            ri = _find(["wheel_right", "right_wheel", "joint_wheel_right"])
            if li is None or ri is None:
                carb.log_warn(
                    f"[fleet] {name}: wheel DOFs not found in {dof_names!r}; skip"
                )
                continue
            ctrl = DifferentialController(
                name=f"ctrl_{name}",
                wheel_radius=config.WHEEL_RADIUS,
                wheel_base=config.WHEEL_BASE,
            )
            robots.append({
                "name": name,
                "idx": i,
                "art": art,
                "ctrl": ctrl,
                "li": li,
                "ri": ri,
                "ndof": len(dof_names),
                "wp_i": 0,
                "waypoints": [],
            })

        if not robots:
            return 0

        def waypoints_for(formation_key: str) -> None:
            form = formations[formation_key]
            for r in robots:
                dx, dy = form[r["idx"]]
                r["waypoints"] = [(x + dx, y + dy) for (x, y) in leader_path]
                r["wp_i"] = 0

        waypoints_for("triangle")
        formation_switched = False

        # Pure Pursuit on chassis world pose.
        def chassis_pose(prim_path: str):
            prim = stage.GetPrimAtPath(prim_path + "/chassis_link")
            if not prim.IsValid():
                prim = stage.GetPrimAtPath(prim_path)
            xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()
            )
            pos = xf.ExtractTranslation()
            rot = xf.ExtractRotation()
            fwd = rot.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
            return float(pos[0]), float(pos[1]), math.atan2(fwd[1], fwd[0])

        max_v = config.DRIVE_MAX_LINEAR
        max_w = config.DRIVE_MAX_ANGULAR
        tol = config.DRIVE_ARRIVAL_TOL

        for _tick in range(config.DRIVE_MAX_TICKS):
            # sim_time-precise formation change (dogfooded done-criterion #2).
            if (not formation_switched
                    and tl.get_current_time() >= config.FORMATION_CHANGE_TIME):
                waypoints_for("line")
                formation_switched = True
                carb.log_info(
                    f"[fleet] formation -> line at sim_time={tl.get_current_time():.2f}"
                )
            all_done = True
            for r in robots:
                if r["wp_i"] >= len(r["waypoints"]):
                    self._zero_wheels(r)
                    continue
                all_done = False
                cx, cy, yaw = chassis_pose(f"{config.FLEET_ROOT}/{r['name']}/Model")
                tx, ty = r["waypoints"][r["wp_i"]]
                dx, dy = tx - cx, ty - cy
                dist = math.hypot(dx, dy)
                if dist < tol:
                    r["wp_i"] += 1
                    continue
                target_yaw = math.atan2(dy, dx)
                heading_err = math.atan2(
                    math.sin(target_yaw - yaw), math.cos(target_yaw - yaw)
                )
                # Slow forward when turning sharply; clamp turn rate.
                v = max_v * max(0.05, math.cos(heading_err))
                w = max(-max_w, min(max_w, 2.0 * heading_err))
                # DifferentialController.forward returns an ArticulationAction
                # (not a list); pull the joint_velocities numpy array.
                action = r["ctrl"].forward([v, w])
                jv = getattr(action, "joint_velocities", None)
                if jv is None:
                    jv = action  # legacy builds: forward returned an array
                vels = [0.0] * r["ndof"]
                vels[r["li"]] = float(jv[0])
                vels[r["ri"]] = float(jv[1])
                try:
                    r["art"].set_joint_velocities(vels)
                except Exception as exc:  # noqa: BLE001
                    carb.log_warn(f"[fleet] {r['name']} set_joint_velocities: {exc}")
            await app.next_update_async()
            if all_done:
                break

        # Always brake wheels on exit.
        for r in robots:
            self._zero_wheels(r)
        return sum(1 for r in robots if r["wp_i"] >= len(r["waypoints"]))

    def _zero_wheels(self, r: dict) -> None:
        try:
            vels = [0.0] * r["ndof"]
            r["art"].set_joint_velocities(vels)
        except Exception:  # noqa: BLE001
            pass

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[fleet] shutdown")
