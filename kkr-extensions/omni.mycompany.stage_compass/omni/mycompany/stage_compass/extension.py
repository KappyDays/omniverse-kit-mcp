"""Stage Compass extension entry point.

Wires together:

  * StageScanner (cached prim list, dirty-on-stage-event)
  * CompassHUD (radar window)
  * CompassSettingsPanel (filter + waypoints + stats)
  * Update tick (refreshes camera pose at ~12 Hz)
  * Self-test (stamps `/Compass/SelfTestResult` so MCP can read pass/fail)

Independent — no validation_api dependency. Pure Kit SDK.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import carb
import omni.ext
import omni.kit.app
import omni.usd

from . import camera_helper
from .compass_hud import CompassHUD
from .settings_panel import CompassSettingsPanel
from .stage_scanner import StageScanner
from .waypoint_store import Waypoint, WaypointStore


_SOURCE = "omni.mycompany.stage_compass"
UPDATE_PERIOD_FRAMES = 5  # ≈ 12 Hz at 60 fps

SELF_TEST_PRIM_PATH = "/Compass/SelfTestResult"


class StageCompassExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        self._scanner = StageScanner()
        self._waypoints = WaypointStore()
        self._hud = CompassHUD(
            scanner=self._scanner,
            waypoints=self._waypoints,
            teleport_cb=self._teleport,
        )
        self._panel = CompassSettingsPanel(
            scanner=self._scanner,
            waypoints=self._waypoints,
            teleport_cb=self._teleport,
            on_filter_changed=self._on_filter_changed,
            on_pin_current=self._pin_current_camera,
            on_rescan=self._rescan,
        )
        self._hud.set_save_waypoint_callback(
            lambda: self._pin_current_camera(name=None)
        )
        self._hud.build()
        self._panel.build()
        self._frame_counter = 0
        self._update_sub = None
        self._stage_event_sub = None
        self._self_test_task: Optional[asyncio.Task] = None
        self._setup_subscriptions()
        # Self-test on a delay so the active viewport has time to come up
        # — particularly important on cold-boot kit where the camera prim
        # is created lazily.
        self._self_test_task = asyncio.ensure_future(self._run_self_tests())

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        self._teardown_subscriptions()
        if self._self_test_task is not None:
            try:
                if not self._self_test_task.done():
                    self._self_test_task.cancel()
            except Exception:
                pass
            self._self_test_task = None
        if self._hud is not None:
            self._hud.destroy()
        if self._panel is not None:
            self._panel.destroy()

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------
    def _setup_subscriptions(self) -> None:
        try:
            app = omni.kit.app.get_app()
            self._update_sub = app.get_update_event_stream().create_subscription_to_pop(
                self._on_update, name="stage_compass_update"
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] update subscribe failed: {exc}")
        try:
            ctx = omni.usd.get_context()
            self._stage_event_sub = ctx.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event, name="stage_compass_stage"
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] stage subscribe failed: {exc}")

    def _teardown_subscriptions(self) -> None:
        for attr in ("_update_sub", "_stage_event_sub"):
            sub = getattr(self, attr, None)
            if sub is None:
                continue
            try:
                sub.unsubscribe()
            except Exception:
                pass
            setattr(self, attr, None)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    def _on_update(self, _event) -> None:
        self._frame_counter = (self._frame_counter + 1) % UPDATE_PERIOD_FRAMES
        if self._frame_counter != 0:
            return
        try:
            pose = camera_helper.get_camera_pose()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] pose read failed: {exc}")
            pose = None
        if self._hud is not None:
            self._hud.update(pose)

    def _on_stage_event(self, event) -> None:
        try:
            event_type = int(event.type)
            opened = int(omni.usd.StageEventType.OPENED)
            closing = int(omni.usd.StageEventType.CLOSING)
            asset_loaded = int(getattr(omni.usd.StageEventType, "ASSETS_LOADED",
                                        omni.usd.StageEventType.OPENED))
        except Exception:
            return
        if event_type in (opened, asset_loaded, closing):
            self._scanner.mark_dirty()
            if self._panel is not None:
                self._panel.mark_stage_changed()

    # ------------------------------------------------------------------
    # Hooks invoked by sub-widgets
    # ------------------------------------------------------------------
    def _on_filter_changed(self, types: Optional[set[str]]) -> None:
        self._scanner.set_type_filter(types)
        if self._hud is not None:
            self._hud.set_allowed_types(types)
            self._hud.update(camera_helper.get_camera_pose())

    def _teleport(self, target_a: float, target_b: float) -> bool:
        ok = camera_helper.teleport_to(target_a, target_b)
        if ok and self._hud is not None:
            # Refresh immediately rather than waiting for the next tick so
            # the click feels instant.
            self._hud.update(camera_helper.get_camera_pose())
        return ok

    def _pin_current_camera(self, name: Optional[str]) -> bool:
        pose = camera_helper.get_camera_pose()
        if pose is None:
            carb.log_warn(f"[{_SOURCE}] no active camera — cannot pin")
            return False
        if not name:
            base = "Spot"
            existing = {w.name for w in self._waypoints.list()}
            i = 1
            name = f"{base} {i}"
            while name in existing:
                i += 1
                name = f"{base} {i}"
        wp = Waypoint(
            name=name,
            floor_a=pose.floor_a,
            floor_b=pose.floor_b,
            height=pose.height,
        )
        ok = self._waypoints.add(wp)
        if ok and self._hud is not None:
            self._hud.update(pose)  # repaint waypoint flag immediately
        return ok

    def _rescan(self) -> None:
        self._scanner.mark_dirty()
        # Force scan now so the panel shows fresh stats.
        self._scanner.get_markers(force_refresh=True)

    # ------------------------------------------------------------------
    # Self test
    # ------------------------------------------------------------------
    async def _run_self_tests(self) -> None:
        app = omni.kit.app.get_app()
        for _ in range(60):
            await app.next_update_async()

        scan_ok = False
        scan_msg = ""
        teleport_ok = False
        teleport_msg = ""
        waypoint_ok = False
        waypoint_msg = ""

        # 1) Spawn a recognisable cube and confirm scanner picks it up.
        try:
            from pxr import Sdf, UsdGeom, Gf
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                scan_msg = "NO STAGE"
            else:
                test_path = "/Compass/TestCube"
                cube = UsdGeom.Cube.Define(stage, Sdf.Path(test_path))
                cube.GetSizeAttr().Set(0.6)
                xformable = UsdGeom.Xformable(cube)
                ops = xformable.GetOrderedXformOps()
                t_op = next(
                    (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
                    None,
                )
                if t_op is None:
                    t_op = xformable.AddTranslateOp()
                t_op.Set(Gf.Vec3d(2.0, 0.0, 0.0))
                self._scanner.mark_dirty()
                markers = self._scanner.get_markers(force_refresh=True)
                scan_ok = any(m.prim_path == test_path for m in markers)
                scan_msg = (
                    f"found_in_{len(markers)}_markers"
                    if scan_ok else f"missing_among_{len(markers)}"
                )
        except Exception as exc:  # noqa: BLE001
            scan_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] scan self-test exception: {exc}")

        # 2) Teleport — exercises the write logic against a dedicated
        #    /Compass/TestCamera so we're not racing Kit's manipulator
        #    on /OmniverseKit_Persp (which re-asserts session-layer
        #    values every tick and makes immediate-after reads see no
        #    change). Direct test camera is the same idiom the existing
        #    omni.mycompany.usd_composer_input extension uses for the
        #    same reason.
        try:
            from pxr import Gf, Sdf, UsdGeom
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                teleport_msg = "NO_STAGE"
            else:
                test_cam_path = "/Compass/TestCamera"
                cam = UsdGeom.Camera.Define(stage, Sdf.Path(test_cam_path))
                xformable = UsdGeom.Xformable(cam)
                # Reset xform ops to a clean translate-only stack so the
                # delta read below is unambiguous.
                xformable.ClearXformOpOrder()
                t_op = xformable.AddTranslateOp()
                t_op.Set(Gf.Vec3d(0.0, 0.0, 0.0))
                target_a, target_b = 7.5, -3.5
                ok = camera_helper.teleport_to(
                    target_a, target_b,
                    camera_prim_path=test_cam_path,
                )
                cache = UsdGeom.XformCache()
                after = cache.GetLocalToWorldTransform(
                    cam.GetPrim()
                ).ExtractTranslation()
                delta = (
                    float(after[0]) ** 2
                    + float(after[1]) ** 2
                    + float(after[2]) ** 2
                ) ** 0.5
                teleport_ok = bool(ok) and delta > 0.5
                teleport_msg = (
                    f"ok={ok} after=("
                    f"{float(after[0]):+.2f},{float(after[1]):+.2f},"
                    f"{float(after[2]):+.2f}) delta={delta:.3f}"
                )
        except Exception as exc:  # noqa: BLE001
            teleport_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] teleport self-test exception: {exc}")

        # 3) Waypoint round-trip in the store.
        try:
            test_name = "__compass_self_test"
            self._waypoints.remove(test_name)
            ok_add = self._waypoints.add(
                Waypoint(name=test_name, floor_a=1.0, floor_b=2.0, height=0.0)
            )
            present = any(w.name == test_name for w in self._waypoints.list())
            ok_remove = self._waypoints.remove(test_name)
            waypoint_ok = bool(ok_add and present and ok_remove)
            waypoint_msg = f"add={ok_add} present={present} remove={ok_remove}"
        except Exception as exc:  # noqa: BLE001
            waypoint_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] waypoint self-test exception: {exc}")

        # Stamp results into a USD prim so MCP-driven verification can
        # read pass/fail without needing UI hooks.
        try:
            from pxr import Sdf, UsdGeom
            stage = omni.usd.get_context().get_stage()
            if stage is not None:
                result = UsdGeom.Xform.Define(stage, Sdf.Path(SELF_TEST_PRIM_PATH))
                prim = result.GetPrim()
                prim.CreateAttribute("scan_ok", Sdf.ValueTypeNames.Bool).Set(scan_ok)
                prim.CreateAttribute("teleport_ok", Sdf.ValueTypeNames.Bool).Set(
                    teleport_ok
                )
                prim.CreateAttribute("waypoint_ok", Sdf.ValueTypeNames.Bool).Set(
                    waypoint_ok
                )
                prim.CreateAttribute("scan_msg", Sdf.ValueTypeNames.String).Set(
                    scan_msg
                )
                prim.CreateAttribute("teleport_msg", Sdf.ValueTypeNames.String).Set(
                    teleport_msg
                )
                prim.CreateAttribute("waypoint_msg", Sdf.ValueTypeNames.String).Set(
                    waypoint_msg
                )
                carb.log_info(
                    f"[{_SOURCE}] self-test stamped: scan={scan_ok} ({scan_msg}) "
                    f"teleport={teleport_ok} ({teleport_msg}) "
                    f"waypoint={waypoint_ok} ({waypoint_msg})"
                )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] self-test stamp failed: {exc}")
