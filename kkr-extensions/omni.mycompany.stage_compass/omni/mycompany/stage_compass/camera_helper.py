"""Camera read/write + world↔radar projection.

Read pose: pulled fresh per-frame so the HUD reflects manual tumble/dolly.
Write pose: ``teleport_to`` preserves the up-axis component of the camera
so click-on-radar feels like dragging the player on a 2-D map without
changing altitude.
"""
from __future__ import annotations

import dataclasses
import math
from typing import Optional

import carb

from .stage_scanner import CameraPose, floor_axes


@dataclasses.dataclass(slots=True, frozen=True)
class RadarProjection:
    hud_size: float
    world_radius: float

    def world_to_hud(
        self,
        wa: float, wb: float,
        cam_a: float, cam_b: float,
        cam_heading_rad: float,
    ) -> tuple[float, float]:
        """Project a floor-plane world point to HUD pixel coords.

        Camera at HUD center; heading rotated so it faces "up" on screen
        (north). World radius maps to half the HUD edge so a marker at
        ``world_radius`` from the camera lands at the HUD edge.
        """
        dx = wa - cam_a
        dy = wb - cam_b
        # Rotate world → HUD frame: -heading so heading-direction is +y_hud.
        cos_h = math.cos(-cam_heading_rad + math.pi / 2.0)
        sin_h = math.sin(-cam_heading_rad + math.pi / 2.0)
        rx = dx * cos_h - dy * sin_h
        ry = dx * sin_h + dy * cos_h
        scale = (self.hud_size / 2.0) / max(self.world_radius, 1e-3)
        # HUD origin is top-left, +y_hud goes down → invert ry.
        px = self.hud_size / 2.0 + rx * scale
        py = self.hud_size / 2.0 - ry * scale
        return px, py

    def hud_to_world(
        self,
        px: float, py: float,
        cam_a: float, cam_b: float,
        cam_heading_rad: float,
    ) -> tuple[float, float]:
        """Inverse of ``world_to_hud`` — used by click-to-teleport."""
        scale = (self.hud_size / 2.0) / max(self.world_radius, 1e-3)
        rx = (px - self.hud_size / 2.0) / scale
        ry = (self.hud_size / 2.0 - py) / scale
        cos_h = math.cos(cam_heading_rad - math.pi / 2.0)
        sin_h = math.sin(cam_heading_rad - math.pi / 2.0)
        dx = rx * cos_h - ry * sin_h
        dy = rx * sin_h + ry * cos_h
        return cam_a + dx, cam_b + dy


def get_camera_pose() -> Optional[CameraPose]:
    """Read active viewport's camera world pose, projected to floor plane."""
    try:
        import omni.usd
        from omni.kit.viewport.utility import get_active_viewport
        from pxr import Gf, UsdGeom

        vp = get_active_viewport()
        if vp is None:
            return None
        cam_path = vp.camera_path
        if cam_path is None:
            return None
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            return None
        cam_prim = stage.GetPrimAtPath(str(cam_path))
        if not cam_prim or not cam_prim.IsValid():
            return None
        cache = UsdGeom.XformCache()
        world = cache.GetLocalToWorldTransform(cam_prim)
        pos = world.ExtractTranslation()
        # Kit camera convention: looks down -Z in local space.
        fwd_vec = -world.TransformDir(Gf.Vec3d(0, 0, 1))
        up_axis = "Y"
        try:
            up_axis = UsdGeom.GetStageUpAxis(stage)
        except Exception:
            pass
        a_idx, b_idx, h_idx = floor_axes(up_axis)
        floor_a = float(pos[a_idx])
        floor_b = float(pos[b_idx])
        height  = float(pos[h_idx])
        fa, fb = float(fwd_vec[a_idx]), float(fwd_vec[b_idx])
        # atan2(b, a) — returned heading is in radians, 0 = +A axis,
        # pi/2 = +B axis.
        heading = math.atan2(fb, fa) if (fa or fb) else 0.0

        # Try to read FOV; default 60° if camera lacks attribute or for
        # ortho cameras where the cone visualization is meaningless.
        fov_deg = 60.0
        try:
            cam = UsdGeom.Camera(cam_prim)
            if cam:
                focal = cam.GetFocalLengthAttr().Get() or 24.0
                ap_h = cam.GetHorizontalApertureAttr().Get() or 20.955
                # Standard photographic FOV formula: 2 * atan(aperture/(2*focal))
                fov_deg = math.degrees(
                    2.0 * math.atan(float(ap_h) / (2.0 * float(focal)))
                )
        except Exception:
            pass

        return CameraPose(
            floor_a=floor_a, floor_b=floor_b, height=height,
            heading_rad=heading, fov_deg=float(fov_deg),
        )
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[stage_compass] get_camera_pose failed: {exc}")
        return None


def teleport_to(
    target_a: float,
    target_b: float,
    camera_prim_path: Optional[str] = None,
) -> bool:
    """Move the active viewport camera (or a named one) to ``(target_a, target_b)``.

    Up-axis component preserved so altitude is unchanged. Returns True on
    success.

    Kit-managed cameras (``/OmniverseKit_Persp``, ``/OmniverseKit_Top`` …)
    have their transform owned by ``omni.kit.manipulator.camera`` on the
    *session layer*; a write to the rootLayer xformOp is shadowed and
    appears to "do nothing" (the manipulator re-asserts session-layer
    values every frame). The fix is to also author the same translate on
    the session layer so it composes on top — that's what the modern
    viewport actually reads. We do both writes so user-authored cameras
    in the rootLayer keep persisting normally.
    """
    try:
        import omni.usd
        from omni.kit.viewport.utility import get_active_viewport
        from pxr import Gf, Sdf, Usd, UsdGeom

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            return False
        if camera_prim_path is not None:
            cam_path = camera_prim_path
        else:
            vp = get_active_viewport()
            if vp is None:
                return False
            cam_path = vp.camera_path
            if cam_path is None:
                return False
        cam_prim = stage.GetPrimAtPath(str(cam_path))
        if not cam_prim or not cam_prim.IsValid():
            return False
        up_axis = "Y"
        try:
            up_axis = UsdGeom.GetStageUpAxis(stage)
        except Exception:
            pass
        a_idx, b_idx, h_idx = floor_axes(up_axis)

        xformable = UsdGeom.Xformable(cam_prim)
        ops = xformable.GetOrderedXformOps()
        translate_op = next(
            (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
            None,
        )
        if translate_op is None:
            translate_op = xformable.AddTranslateOp()
            translate_op.Set(Gf.Vec3d(0, 0, 0))
        cur = translate_op.Get() or Gf.Vec3d(0, 0, 0)
        new_xyz = [float(cur[0]), float(cur[1]), float(cur[2])]
        new_xyz[a_idx] = float(target_a)
        new_xyz[b_idx] = float(target_b)
        new_vec = Gf.Vec3d(*new_xyz)

        # 1. Write on the current EditTarget (root layer by default).
        translate_op.Set(new_vec)

        # 2. Mirror onto the session layer if this is a Kit-managed
        #    camera, so the manipulator's per-frame re-authoring picks
        #    up our new value next tick. ``Usd.EditContext`` swaps the
        #    edit target temporarily so we don't pollute the user's
        #    rootLayer with session-only data when re-running.
        if str(cam_path).startswith("/OmniverseKit_"):
            session = stage.GetSessionLayer()
            try:
                with Usd.EditContext(stage, Usd.EditTarget(session)):
                    sxformable = UsdGeom.Xformable(cam_prim)
                    sops = sxformable.GetOrderedXformOps()
                    s_translate = next(
                        (op for op in sops
                         if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
                        None,
                    )
                    if s_translate is None:
                        s_translate = sxformable.AddTranslateOp()
                    s_translate.Set(new_vec)
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(
                    f"[stage_compass] session-layer teleport for {cam_path}: {exc}"
                )
        return True
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[stage_compass] teleport failed: {exc}")
        return False


def frame_camera_on_extents(
    min_a: float, min_b: float, max_a: float, max_b: float,
) -> bool:
    """Move camera to the centre of the (min..max) bounding rect on floor."""
    cx = (min_a + max_a) / 2.0
    cy = (min_b + max_b) / 2.0
    return teleport_to(cx, cy)
