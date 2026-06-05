# camera_controller.py -- update the active viewport camera's transform (CCT pattern).

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import carb
import omni.kit.commands
import omni.kit.viewport.utility as vp_utils
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from pxr import Gf, Usd, UsdGeom

from . import camera_math


@dataclass
class _CameraOrigState:
    camera_path: str
    pos: Gf.Vec3d
    target: Gf.Vec3d


class CameraController:
    """Read/write active viewport camera transform via Kit commands.

    On activate(), captures the active camera path + its current pos/target so
    Stop / ESC can restore them. Per-frame apply() updates the SAME camera's
    transform via omni.kit.commands.execute("TransformPrimCommand", ...).
    """

    def __init__(self) -> None:
        self._orig: Optional[_CameraOrigState] = None
        self._yaw: float = 0.0
        self._pitch: float = 0.0
        self._pos: Gf.Vec3d = Gf.Vec3d(0, 0, 0)
        self._up_axis: str = "Y"
        # Cached at activate() time; fixed for the lifetime of one activation.
        self._world_up: Gf.Vec3d = Gf.Vec3d(0, 1, 0)

    # --- lifecycle ---

    def activate(self) -> bool:
        """Capture original camera state. Returns True on success."""
        active_viewport = vp_utils.get_active_viewport()
        if active_viewport is None:
            carb.log_warn("usd_mouse_interact_demo: no active viewport on activate")
            return False
        camera_path = active_viewport.get_active_camera()
        if not camera_path:
            carb.log_warn("usd_mouse_interact_demo: active viewport has no active camera")
            return False

        camera_state = ViewportCameraState()
        pos = camera_state.position_world
        target = camera_state.target_world

        self._orig = _CameraOrigState(
            camera_path=str(camera_path),
            pos=Gf.Vec3d(pos),
            target=Gf.Vec3d(target),
        )

        # Seed yaw/pitch from current forward direction.
        forward_vec = Gf.Vec3d(target) - Gf.Vec3d(pos)
        flen = forward_vec.GetLength()
        if flen > 1e-9:
            f_norm = (forward_vec[0] / flen, forward_vec[1] / flen, forward_vec[2] / flen)
        else:
            carb.log_warn(
                "usd_mouse_interact_demo: activate — zero-length forward vector "
                "(camera at exact target); seeding yaw/pitch to defaults"
            )
            f_norm = (0.0, 0.0, -1.0)

        # Stage up-axis.
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        self._up_axis = UsdGeom.GetStageUpAxis(stage) if stage else "Y"
        self._world_up = Gf.Vec3d(0, 1, 0) if self._up_axis.upper() == "Y" else Gf.Vec3d(0, 0, 1)
        self._yaw, self._pitch = camera_math.yaw_pitch_from_forward(f_norm, self._up_axis)
        self._pos = Gf.Vec3d(pos)
        return True

    def deactivate(self) -> None:
        """Restore original camera position/target. Active camera path is not changed
        (we never set_active_camera, so no need to revert).

        Caveat: ViewportCameraState() reads the *current* active camera. If the user
        switched the active camera between activate() and deactivate(), the restore
        writes the original pos/target onto the wrong camera. v0.2.0 accepts this —
        camera-switch during navigation is out of scope.
        """
        if self._orig is None:
            return
        try:
            camera_state = ViewportCameraState()
            camera_state.set_position_world(self._orig.pos, False)
            camera_state.set_target_world(self._orig.target, True)
        except Exception as exc:  # pragma: no cover — Kit-runtime only
            carb.log_warn(f"usd_mouse_interact_demo: camera restore failed: {exc}")
        self._orig = None

    # --- per-frame ---

    def apply(self, dx_pixels: float, dy_pixels: float, keys: camera_math.MovementInput,
              speed: float, sensitivity: float, dt: float) -> None:
        """Update yaw/pitch from mouse delta, translate from keys, write transform.

        sensitivity is expected in [1, 100]; values <1 are clamped to 1. Caller is
        responsible for the upper bound — typical UI exposes a 1..100 slider mapping
        to a 0.0001..0.01 multiplier for camera_math.update_yaw_pitch.
        """
        if self._orig is None:
            return

        # Clamp dt (frame drop safety).
        dt = min(dt, 0.1)

        # v0.1.0 used 0.0025 default; we expose sensitivity as 1..100 → 0.0001..0.01.
        sens_factor = max(1, sensitivity) * 0.0001
        self._yaw, self._pitch = camera_math.update_yaw_pitch(
            self._yaw, self._pitch, dx_pixels, dy_pixels, sens_factor
        )

        # camera_math.basis_from_yaw_pitch convention: at yaw=0, pitch=0 the forward
        # vector is -Z (Y-up) or -Y (Z-up). SetLookAt below assumes -Z view direction
        # (USD/OpenGL convention). If basis_from_yaw_pitch ever changes, update here.
        forward, right, up = camera_math.basis_from_yaw_pitch(
            self._yaw, self._pitch, self._up_axis
        )
        delta = camera_math.translation_from_input(forward, right, up, keys, speed, dt)
        self._pos = Gf.Vec3d(self._pos[0] + delta[0], self._pos[1] + delta[1], self._pos[2] + delta[2])

        target = Gf.Vec3d(
            self._pos[0] + forward[0],
            self._pos[1] + forward[1],
            self._pos[2] + forward[2],
        )

        # SetLookAt builds a world→camera view matrix; GetInverse() yields the
        # camera's world transform — the matrix shape TransformPrimCommand expects.
        world_xform = Gf.Matrix4d().SetLookAt(self._pos, target, self._world_up).GetInverse()
        try:
            self._write_transform(world_xform)
        except Exception as exc:  # pragma: no cover
            carb.log_warn(f"usd_mouse_interact_demo: camera transform write failed: {exc}")

    def _write_transform(self, world_xform: Gf.Matrix4d) -> None:
        if self._orig is None:
            return
        import omni.usd

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        camera_prim = stage.GetPrimAtPath(self._orig.camera_path)
        if not camera_prim or not camera_prim.IsValid():
            return

        parent = camera_prim.GetParent()
        if parent and parent.IsValid():
            parent_world = UsdGeom.Xformable(parent).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()
            )
            # USD row-vector convention: local = world * parent_inv.
            local_xform = world_xform * parent_world.GetInverse()
        else:
            local_xform = world_xform

        omni.kit.commands.execute(
            "TransformPrimCommand",
            path=self._orig.camera_path,
            new_transform_matrix=local_xform,
        )

    # --- introspection (dev panel) ---

    @property
    def yaw(self) -> float:
        return self._yaw

    @property
    def pitch(self) -> float:
        return self._pitch

    @property
    def camera_path(self) -> str:
        return self._orig.camera_path if self._orig else ""
