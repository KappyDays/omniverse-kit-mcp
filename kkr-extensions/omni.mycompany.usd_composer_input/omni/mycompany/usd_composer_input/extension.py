"""USD Composer Input — hover highlight + QWEASD camera (Phase A).

Activates on omni.timeline PLAY event, deactivates on STOP/PAUSE.
"""

from __future__ import annotations

import carb
import carb.input
import omni.ext
import omni.kit.app
import omni.timeline
import omni.usd
import omni.ui as ui
from pxr import Gf, UsdGeom

HIGHLIGHT_COLOR = Gf.Vec3f(1.0, 0.843, 0.0)  # FFD700
MOVE_SPEED = 0.1  # m / frame baseline
SHIFT_MULT = 2.0

KEY_AXIS = {
    "W": ("forward", +1.0),
    "S": ("forward", -1.0),
    "A": ("right", -1.0),
    "D": ("right", +1.0),
    "Q": ("up", -1.0),
    "E": ("up", +1.0),
}


class UsdComposerInputExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        carb.log_info(f"[usd_composer_input] startup ext_id={ext_id}")
        self._ext_id = ext_id
        self._window: ui.Window | None = None
        self._mouse_sub = None
        self._keyboard_sub = None
        self._timeline_sub = None
        self._update_sub = None
        self._is_active = False
        self._highlighted_prim_path: str | None = None
        self._original_color: list | None = None
        self._held_keys: dict = {}
        self._shift_held = False
        self._self_test_task = None
        self._build_status_window()
        self._setup_subscriptions()
        # Schedule self-tests so MCP-driven verification can read the results
        # from stage state (USD Composer lacks omni.kit.ui_test for widget click).
        import asyncio
        self._self_test_task = asyncio.ensure_future(self._run_self_tests())

    def on_shutdown(self) -> None:
        carb.log_info("[usd_composer_input] shutdown")
        self._teardown_subscriptions()
        self._restore_highlight()
        if self._window is not None:
            self._window.visible = False
            self._window.destroy()
            self._window = None

    # --- UI ---
    def _build_status_window(self) -> None:
        existing = ui.Workspace.get_window("USD Composer Input")
        if existing is not None:
            existing.visible = False
            existing.destroy()
        self._window = ui.Window("USD Composer Input", width=320, height=240)
        with self._window.frame:
            with ui.VStack(spacing=4):
                ui.Label("USD Composer Input Extension", style={"font_size": 16})
                self._status_label = ui.Label("Status: inactive (timeline not playing)")
                ui.Label("Hover: prim under mouse -> yellow highlight")
                ui.Label("Camera: Q E A S D W (Shift = 2x)")
                ui.Button("Test: Spawn /World/TestCube + Hover", clicked_fn=self._test_hover)
                ui.Button("Test: Camera Forward 1.0", clicked_fn=self._test_move)
                self._test_result_label = ui.Label("Test result: (none)")

    def _set_active(self, active: bool) -> None:
        self._is_active = active
        if hasattr(self, "_status_label") and self._status_label is not None:
            self._status_label.text = (
                "Status: ACTIVE (timeline playing)" if active else "Status: inactive"
            )
        if active:
            carb.log_info("[usd_composer_input] activated (timeline play)")
        else:
            carb.log_info("[usd_composer_input] deactivated (timeline stop/pause)")
            self._restore_highlight()
            self._held_keys.clear()

    # --- Subscriptions ---
    def _setup_subscriptions(self) -> None:
        try:
            timeline = omni.timeline.get_timeline_interface()
            self._timeline_sub = timeline.get_timeline_event_stream().create_subscription_to_pop(
                self._on_timeline_event, name="usd_composer_input_timeline"
            )
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] timeline subscribe error: {exc}")
        self._mouse_sub = self._subscribe_mouse_via_viewport()
        self._keyboard_sub = self._subscribe_keyboard()
        try:
            app = omni.kit.app.get_app()
            self._update_sub = app.get_update_event_stream().create_subscription_to_pop(
                self._on_update, name="usd_composer_input_update"
            )
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] update subscribe error: {exc}")

    def _teardown_subscriptions(self) -> None:
        for sub_attr in ("_timeline_sub", "_mouse_sub", "_keyboard_sub", "_update_sub"):
            sub = getattr(self, sub_attr, None)
            if sub is not None and hasattr(sub, "unsubscribe"):
                try:
                    sub.unsubscribe()
                except Exception:
                    pass
            setattr(self, sub_attr, None)

    def _on_timeline_event(self, event) -> None:
        try:
            t_play = int(omni.timeline.TimelineEventType.PLAY)
            t_stop = int(omni.timeline.TimelineEventType.STOP)
            t_pause = int(omni.timeline.TimelineEventType.PAUSE)
            if event.type == t_play:
                self._set_active(True)
            elif event.type in (t_stop, t_pause):
                self._set_active(False)
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] timeline event error: {exc}")

    # --- Hover (A.2) ---
    def _subscribe_mouse_via_viewport(self):
        """Hover handler. Picks prim under mouse using viewport's pick API.

        Tries known method names on the active viewport window. Falls back to
        a no-op (carb log warn) if the API is not exposed on this Kit version.
        """
        try:
            from omni.kit.viewport.utility import get_active_viewport_window
            vp_window = get_active_viewport_window()
            if vp_window is None:
                carb.log_warn(
                    "[usd_composer_input] no active viewport window -- hover disabled"
                )
                return None
            for method_name in ("subscribe_to_pick_event", "subscribe_to_mouse_hover"):
                if hasattr(vp_window, method_name):
                    return getattr(vp_window, method_name)(self._on_pick)
            carb.log_warn(
                "[usd_composer_input] viewport pick API not found -- hover disabled. "
                "Tried: subscribe_to_pick_event, subscribe_to_mouse_hover."
            )
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] mouse subscribe error: {exc}")
        return None

    def _on_pick(self, prim_path_or_event) -> None:
        if not self._is_active:
            return
        if isinstance(prim_path_or_event, str):
            prim_path = prim_path_or_event
        elif hasattr(prim_path_or_event, "prim_path"):
            prim_path = prim_path_or_event.prim_path
        else:
            return
        if prim_path == self._highlighted_prim_path:
            return
        self._restore_highlight()
        if not prim_path:
            return
        try:
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(prim_path) if stage else None
            if not prim or not prim.IsValid():
                return
            gprim = UsdGeom.Gprim(prim)
            if not gprim:
                return
            attr = gprim.GetDisplayColorAttr()
            self._original_color = list(attr.Get()) if attr.HasAuthoredValue() else None
            attr.Set([HIGHLIGHT_COLOR])
            self._highlighted_prim_path = prim_path
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] highlight error: {exc}")

    def _restore_highlight(self) -> None:
        if self._highlighted_prim_path is None:
            return
        try:
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(self._highlighted_prim_path) if stage else None
            if prim and prim.IsValid():
                gprim = UsdGeom.Gprim(prim)
                if gprim:
                    attr = gprim.GetDisplayColorAttr()
                    if self._original_color is not None:
                        attr.Set(self._original_color)
                    else:
                        attr.Clear()
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] restore highlight error: {exc}")
        self._highlighted_prim_path = None
        self._original_color = None

    # --- Keyboard (A.3) ---
    def _subscribe_keyboard(self):
        try:
            input_iface = carb.input.acquire_input_interface()
            keyboard = input_iface.get_default_keyboard()
            return input_iface.subscribe_to_keyboard_events(
                keyboard, self._on_keyboard_event
            )
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] keyboard subscribe error: {exc}")
            return None

    def _on_keyboard_event(self, event) -> bool:
        if not self._is_active:
            return True
        try:
            key_name = event.input.name if hasattr(event.input, "name") else str(event.input)
        except Exception:
            return True
        if key_name not in KEY_AXIS:
            return True
        try:
            et = event.type
            if et == carb.input.KeyboardEventType.KEY_PRESS:
                self._held_keys[key_name] = True
            elif et == carb.input.KeyboardEventType.KEY_RELEASE:
                self._held_keys.pop(key_name, None)
        except Exception:
            pass
        try:
            self._shift_held = bool(
                getattr(event, "modifiers", 0)
                & getattr(carb.input, "KEYBOARD_MODIFIER_FLAG_SHIFT", 0)
            )
        except Exception:
            self._shift_held = False
        return True

    def _on_update(self, event) -> None:
        if not self._is_active or not self._held_keys:
            return
        fwd = right = up = 0.0
        for key in list(self._held_keys.keys()):
            axis, sign = KEY_AXIS[key]
            if axis == "forward":
                fwd += sign
            elif axis == "right":
                right += sign
            elif axis == "up":
                up += sign
        if fwd == 0.0 and right == 0.0 and up == 0.0:
            return
        speed = MOVE_SPEED * (SHIFT_MULT if self._shift_held else 1.0)
        self._move_camera(forward=fwd * speed, right=right * speed, up=up * speed)

    # --- Self-test runner (auto on startup) ---
    async def _run_self_tests(self) -> None:
        app = omni.kit.app.get_app()
        # Wait ~1s so the viewport is fully built
        for _ in range(60):
            await app.next_update_async()
        hover_ok = False
        move_ok = False
        hover_msg = ""
        move_msg = ""
        try:
            hover_ok, hover_msg = self._test_hover()
        except Exception as exc:
            hover_msg = f"EXC {exc}"
            carb.log_warn(f"[usd_composer_input] self-test hover error: {exc}")
        for _ in range(60):
            await app.next_update_async()
        try:
            move_ok, move_msg = self._test_move()
        except Exception as exc:
            move_msg = f"EXC {exc}"
            carb.log_warn(f"[usd_composer_input] self-test move error: {exc}")
        # Stamp results to /World/SelfTestResult so they survive any
        # subsequent _restore_highlight or timeline-driven state change.
        try:
            from pxr import Sdf
            stage = omni.usd.get_context().get_stage()
            if stage is not None:
                result = UsdGeom.Xform.Define(stage, Sdf.Path("/World/SelfTestResult"))
                prim = result.GetPrim()
                prim.CreateAttribute("hover_ok", Sdf.ValueTypeNames.Bool).Set(hover_ok)
                prim.CreateAttribute("move_ok", Sdf.ValueTypeNames.Bool).Set(move_ok)
                prim.CreateAttribute("hover_msg", Sdf.ValueTypeNames.String).Set(hover_msg)
                prim.CreateAttribute("move_msg", Sdf.ValueTypeNames.String).Set(move_msg)
                carb.log_info(
                    f"[usd_composer_input] self-tests stamped: hover={hover_ok} ({hover_msg}) "
                    f"move={move_ok} ({move_msg})"
                )
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] self-test stamp error: {exc}")

    # --- Test hooks (programmatic UX verification — no real input event needed) ---
    def _test_hover(self) -> tuple[bool, str]:
        """Spawn /World/TestCube and trigger _on_pick directly. Returns (ok, msg).
        Clears _highlighted_prim_path after capture so subsequent
        _restore_highlight calls are no-ops (otherwise the FFD700 color reverts
        to baseline before MCP can read the stage)."""
        try:
            from pxr import Sdf
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return False, "NO STAGE"
            test_path = "/World/TestCube"
            cube = UsdGeom.Cube.Define(stage, Sdf.Path(test_path))
            cube.GetSizeAttr().Set(0.5)
            cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.4, 0.9)])  # blue baseline
            prev_active = self._is_active
            self._is_active = True
            self._on_pick(test_path)
            self._is_active = prev_active
            after = list(cube.GetDisplayColorAttr().Get() or [])
            ok = (
                self._highlighted_prim_path == test_path
                and len(after) == 1
                and abs(after[0][0] - HIGHLIGHT_COLOR[0]) < 1e-3
                and abs(after[0][1] - HIGHLIGHT_COLOR[1]) < 1e-3
                and abs(after[0][2] - HIGHLIGHT_COLOR[2]) < 1e-3
            )
            # Detach so future _restore_highlight is a no-op
            self._highlighted_prim_path = None
            self._original_color = None
            msg = "FFD700 applied" if ok else f"color={after}"
            if hasattr(self, "_test_result_label") and self._test_result_label is not None:
                self._test_result_label.text = (
                    f"Test result: HOVER {'OK' if ok else 'FAIL'} ({msg})"
                )
            carb.log_info(f"[usd_composer_input] test_hover -> ok={ok} {msg}")
            return ok, msg
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] _test_hover error: {exc}")
            return False, f"EXC {exc}"

    def _test_move(self) -> tuple[bool, str]:
        """Create a dedicated /World/TestCamera and apply _move_camera to it.
        Avoids Kit-managed cameras (OmniverseKit_Persp) that the viewport
        may overwrite each tick."""
        try:
            from pxr import Sdf
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return False, "NO STAGE"
            test_cam_path = "/World/TestCamera"
            cam = UsdGeom.Camera.Define(stage, Sdf.Path(test_cam_path))
            xformable = UsdGeom.Xformable(cam)
            xformable.ClearXformOpOrder()
            translate_op = xformable.AddTranslateOp()
            translate_op.Set(Gf.Vec3d(0.0, 0.0, 0.0))
            before = translate_op.Get()
            prev_active = self._is_active
            self._is_active = True
            self._move_camera(
                forward=1.0, right=0.0, up=0.0, target_prim_path=test_cam_path
            )
            self._is_active = prev_active
            after = translate_op.Get()
            delta = after - before
            mag = (delta[0] ** 2 + delta[1] ** 2 + delta[2] ** 2) ** 0.5
            ok = mag > 0.5  # forward=1.0 expected ~1m world delta
            msg = f"delta_mag={mag:.3f} after={tuple(round(v,3) for v in after)}"
            if hasattr(self, "_test_result_label") and self._test_result_label is not None:
                self._test_result_label.text = (
                    f"Test result: MOVE {'OK' if ok else 'FAIL'} {msg}"
                )
            carb.log_info(
                f"[usd_composer_input] test_move -> ok={ok} {msg} before={before}"
            )
            return ok, msg
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] _test_move error: {exc}")
            return False, f"EXC {exc}"

    def _move_camera(
        self, forward: float, right: float, up: float, target_prim_path: str | None = None
    ) -> None:
        try:
            stage = omni.usd.get_context().get_stage()
            if target_prim_path is not None:
                cam_path = target_prim_path
            else:
                from omni.kit.viewport.utility import get_active_viewport
                viewport = get_active_viewport()
                if viewport is None:
                    return
                cam_path = viewport.camera_path
            cam_prim = stage.GetPrimAtPath(cam_path) if stage else None
            if not cam_prim or not cam_prim.IsValid():
                return
            xformable = UsdGeom.Xformable(cam_prim)
            cache = UsdGeom.XformCache()
            world = cache.GetLocalToWorldTransform(cam_prim)
            forward_vec = -world.TransformDir(Gf.Vec3d(0, 0, 1))
            right_vec = world.TransformDir(Gf.Vec3d(1, 0, 0))
            up_vec = world.TransformDir(Gf.Vec3d(0, 1, 0))
            delta = forward_vec * forward + right_vec * right + up_vec * up
            ops = xformable.GetOrderedXformOps()
            translate_op = next(
                (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
                None,
            )
            if translate_op is None:
                translate_op = xformable.AddTranslateOp()
                translate_op.Set(Gf.Vec3d(0, 0, 0))
            cur = translate_op.Get() or Gf.Vec3d(0, 0, 0)
            translate_op.Set(cur + delta)
        except Exception as exc:
            carb.log_warn(f"[usd_composer_input] camera move error: {exc}")
