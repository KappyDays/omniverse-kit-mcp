"""Stage Annotator extension entry point.

Wires the note store, the 3-D pin renderer, and the panel together. Adds:

  * Stage event subscriptions (re-sync pins after stage open / asset
    reload, refresh panel)
  * "Frame prim" helper that prefers ``omni.kit.viewport.utility``'s
    built-in framing API, falling back to a manual bbox-centre teleport
    when that API isn't exposed in the current Kit build
  * Self-test that stamps results to ``/Annotator/SelfTestResult`` so
    headless MCP-driven validation can pass / fail without reading UI

Independent — no validation_api dependency.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

import carb
import omni.ext
import omni.kit.app
import omni.usd

from .note_store import (
    Note,
    NoteStore,
    STATUS_OPEN,
    STATUS_RESOLVED,
    default_author,
)
from .notes_panel import NotesPanel
from .pin_renderer import PinRenderer


_SOURCE = "omni.mycompany.stage_annotator"
SELF_TEST_PRIM_PATH = "/Annotator/SelfTestResult"


class StageAnnotatorExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        self._store = NoteStore()
        self._pin_renderer = PinRenderer(self._store)
        self._panel = NotesPanel(
            store=self._store,
            on_focus_prim=self._frame_prim,
            on_select_prim=self._select_prim,
            on_export=self._export_to_file,
            on_pick_selection=self._first_selected_prim_path,
        )
        self._stage_event_sub = None
        self._self_test_task: Optional[asyncio.Task] = None
        self._panel.build()
        self._pin_renderer.attach()
        self._setup_subscriptions()
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
        if self._pin_renderer is not None:
            self._pin_renderer.detach(remove_pins=False)
        if self._panel is not None:
            self._panel.destroy()

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------
    def _setup_subscriptions(self) -> None:
        try:
            ctx = omni.usd.get_context()
            self._stage_event_sub = ctx.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event, name="stage_annotator_stage"
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] stage subscribe failed: {exc}")

    def _teardown_subscriptions(self) -> None:
        sub = getattr(self, "_stage_event_sub", None)
        if sub is not None:
            try:
                sub.unsubscribe()
            except Exception:
                pass
            self._stage_event_sub = None

    def _on_stage_event(self, event) -> None:
        try:
            event_type = int(event.type)
        except Exception:
            return
        try:
            opened = int(omni.usd.StageEventType.OPENED)
            closing = int(omni.usd.StageEventType.CLOSING)
            assets_loaded = int(getattr(omni.usd.StageEventType, "ASSETS_LOADED",
                                         omni.usd.StageEventType.OPENED))
        except Exception:
            return
        if event_type in (opened, assets_loaded):
            # Stage swap → store needs to reload from new layer customData,
            # pins need to repopulate against new prims.
            self._store._loaded_for_layer_id = None  # type: ignore[attr-defined]
            self._pin_renderer.sync()
            # Panel rebuild via store notify isn't triggered for reloads
            # (no mutation), so manually push a refresh.
            try:
                self._panel._schedule_refresh()  # type: ignore[attr-defined]
            except Exception:
                pass
        elif event_type == closing:
            # Don't auto-clean pins on close — they're saved with the layer.
            pass

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _first_selected_prim_path(self) -> Optional[str]:
        try:
            sel = omni.usd.get_context().get_selection()
            paths = sel.get_selected_prim_paths()
            if paths:
                return str(paths[0])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] selection read: {exc}")
        return None

    def _select_prim(self, prim_path: str) -> None:
        try:
            omni.usd.get_context().get_selection().set_selected_prim_paths(
                [prim_path], True,
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] select_prim {prim_path}: {exc}")

    # ------------------------------------------------------------------
    # Frame prim helpers
    # ------------------------------------------------------------------
    def _frame_prim(self, prim_path: str) -> bool:
        if not prim_path:
            return False
        # Always set selection first — most framing APIs operate on the
        # current selection set, and it leaves the user with a useful
        # selection state regardless of which framing path runs.
        self._select_prim(prim_path)
        # Try Kit utility helpers first (preferred — they handle camera
        # rotation properly so the prim ends up actually centred).
        try:
            from omni.kit.viewport.utility import (
                get_active_viewport,
                frame_viewport_prims,  # type: ignore[attr-defined]
            )
            vp = get_active_viewport()
            if vp is not None:
                frame_viewport_prims(vp, prim_paths=[prim_path])
                return True
        except Exception:
            pass
        try:
            from omni.kit.viewport.utility import (
                get_active_viewport,
                frame_viewport_selection,  # type: ignore[attr-defined]
            )
            vp = get_active_viewport()
            if vp is not None:
                frame_viewport_selection(vp)
                return True
        except Exception:
            pass
        # Manual fallback: nudge camera translate so the prim's bbox centre
        # is in front of the camera.
        return self._manual_frame_prim(prim_path)

    def _manual_frame_prim(self, prim_path: str) -> bool:
        try:
            from omni.kit.viewport.utility import get_active_viewport
            from pxr import Gf, Usd, UsdGeom
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return False
            prim = stage.GetPrimAtPath(prim_path)
            if not prim or not prim.IsValid():
                return False
            cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.proxy],
                useExtentsHint=True,
            )
            bb = cache.ComputeWorldBound(prim)
            if bb.GetRange().IsEmpty():
                return False
            aligned = bb.ComputeAlignedBox()
            centre = aligned.GetMidpoint()
            size = aligned.GetSize()
            diag = float((size[0] ** 2 + size[1] ** 2 + size[2] ** 2) ** 0.5)
            vp = get_active_viewport()
            if vp is None:
                return False
            cam_prim = stage.GetPrimAtPath(str(vp.camera_path))
            if not cam_prim or not cam_prim.IsValid():
                return False
            xc = UsdGeom.XformCache()
            world = xc.GetLocalToWorldTransform(cam_prim)
            fwd_vec = -world.TransformDir(Gf.Vec3d(0, 0, 1))
            mag = float(
                (fwd_vec[0] ** 2 + fwd_vec[1] ** 2 + fwd_vec[2] ** 2) ** 0.5
            ) or 1.0
            unit = Gf.Vec3d(
                fwd_vec[0] / mag, fwd_vec[1] / mag, fwd_vec[2] / mag,
            )
            offset = -unit * (max(diag, 1.0) * 2.0 + 1.0)
            new_pos = Gf.Vec3d(centre) + offset
            xformable = UsdGeom.Xformable(cam_prim)
            ops = xformable.GetOrderedXformOps()
            t_op = next(
                (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
                None,
            )
            if t_op is None:
                t_op = xformable.AddTranslateOp()
            t_op.Set(new_pos)
            return True
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] manual frame failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _export_to_file(self, blob: str) -> Optional[str]:
        # Drop into the Kit user-data directory under
        # ``stage_annotator_export.json`` — predictable for headless tests
        # and easy for users to find via Documents/Kit.
        try:
            base_dir = os.path.expanduser("~/.stage_annotator_exports")
            os.makedirs(base_dir, exist_ok=True)
            fname = time.strftime("notes_%Y%m%d_%H%M%S.json")
            path = os.path.join(base_dir, fname)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(blob)
            return path
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] export write failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Self test
    # ------------------------------------------------------------------
    async def _run_self_tests(self) -> None:
        app = omni.kit.app.get_app()
        for _ in range(45):
            await app.next_update_async()

        crud_ok = False
        crud_msg = ""
        pin_ok = False
        pin_msg = ""
        export_ok = False
        export_msg = ""

        # 1) Notes CRUD round-trip.
        try:
            from pxr import Sdf, UsdGeom, Gf
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                crud_msg = "NO STAGE"
            else:
                # Spawn a host prim so the note has something to anchor to.
                host_path = "/Annotator/SelfTestHost"
                cube = UsdGeom.Cube.Define(stage, Sdf.Path(host_path))
                cube.GetSizeAttr().Set(0.5)
                xformable = UsdGeom.Xformable(cube)
                ops = xformable.GetOrderedXformOps()
                t_op = next(
                    (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
                    None,
                )
                if t_op is None:
                    t_op = xformable.AddTranslateOp()
                t_op.Set(Gf.Vec3d(-3.0, 0.0, 0.0))

                # Add a note → confirm it exists.
                n = Note(
                    id="", prim_path=host_path,
                    title="Self test", body="auto",
                    author=default_author(),
                    created_at=0.0, updated_at=0.0,
                    status=STATUS_OPEN,
                )
                ok_add = self._store.add(n)
                added_id = self._store.list()[-1].id if self._store.list() else ""
                # Update status → confirm it persisted.
                ok_status = self._store.update(added_id, status=STATUS_RESOLVED)
                got = self._store.get(added_id)
                ok_after = (got is not None and got.status == STATUS_RESOLVED)
                # Add reply
                ok_reply = self._store.add_reply(
                    added_id, "looks good", default_author(),
                )
                # Delete
                ok_remove = self._store.remove(added_id)
                still_present = self._store.get(added_id) is not None
                crud_ok = bool(
                    ok_add and ok_status and ok_after and ok_reply
                    and ok_remove and not still_present
                )
                crud_msg = (
                    f"add={ok_add} status={ok_status} after={ok_after} "
                    f"reply={ok_reply} remove={ok_remove}"
                )
        except Exception as exc:  # noqa: BLE001
            crud_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] crud self-test exception: {exc}")

        # 2) Pin sync — add a note, give renderer a tick, check pin exists.
        try:
            from pxr import UsdGeom
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                pin_msg = "NO STAGE"
            else:
                n = Note(
                    id="", prim_path="/World",
                    title="Pin test", body="",
                    author=default_author(),
                    created_at=0.0, updated_at=0.0,
                    status=STATUS_OPEN,
                )
                ok_add = self._store.add(n)
                pinned_id = self._store.list()[-1].id if self._store.list() else ""
                # Renderer subscribes to add — give it a frame to do its job.
                for _ in range(3):
                    await app.next_update_async()
                from .pin_renderer import PINS_ROOT, PIN_PRIM_NAME, _safe_id
                pin_path = f"{PINS_ROOT}/{_safe_id(pinned_id)}/{PIN_PRIM_NAME}"
                pin_prim = stage.GetPrimAtPath(pin_path)
                pin_ok = bool(pin_prim and pin_prim.IsValid()
                              and pin_prim.IsA(UsdGeom.Sphere))
                pin_msg = f"pin_at={pin_path} valid={pin_ok}"
                # Cleanup the test note.
                self._store.remove(pinned_id)
        except Exception as exc:  # noqa: BLE001
            pin_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] pin self-test exception: {exc}")

        # 3) Export round-trip.
        try:
            blob = self._store.export_json()
            ok_decoded = blob.startswith("{") and "\"notes\"" in blob
            export_ok = ok_decoded
            export_msg = f"len={len(blob)} ok={ok_decoded}"
        except Exception as exc:  # noqa: BLE001
            export_msg = f"EXC {exc!r}"
            carb.log_warn(f"[{_SOURCE}] export self-test exception: {exc}")

        # Stamp results into stage so MCP driver can read pass/fail
        # without UI hooks.
        try:
            from pxr import Sdf, UsdGeom
            stage = omni.usd.get_context().get_stage()
            if stage is not None:
                result = UsdGeom.Xform.Define(
                    stage, Sdf.Path(SELF_TEST_PRIM_PATH)
                )
                prim = result.GetPrim()
                prim.CreateAttribute("crud_ok", Sdf.ValueTypeNames.Bool).Set(
                    crud_ok
                )
                prim.CreateAttribute("pin_ok", Sdf.ValueTypeNames.Bool).Set(pin_ok)
                prim.CreateAttribute("export_ok", Sdf.ValueTypeNames.Bool).Set(
                    export_ok
                )
                prim.CreateAttribute("crud_msg", Sdf.ValueTypeNames.String).Set(
                    crud_msg
                )
                prim.CreateAttribute("pin_msg", Sdf.ValueTypeNames.String).Set(
                    pin_msg
                )
                prim.CreateAttribute("export_msg", Sdf.ValueTypeNames.String).Set(
                    export_msg
                )
                carb.log_info(
                    f"[{_SOURCE}] self-test stamped: crud={crud_ok} ({crud_msg}) "
                    f"pin={pin_ok} ({pin_msg}) export={export_ok} ({export_msg})"
                )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{_SOURCE}] self-test stamp failed: {exc}")
