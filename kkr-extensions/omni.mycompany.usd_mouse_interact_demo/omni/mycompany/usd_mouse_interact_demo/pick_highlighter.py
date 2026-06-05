# pick_highlighter.py — viewport-center ray → whitelist filter → selection + info overlay.

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import carb
import omni.usd
from pxr import Gf, UsdGeom, Usd

from . import metadata_store

if TYPE_CHECKING:
    from .info_overlay import InfoOverlay

_SOURCE = "omni.mycompany.usd_mouse_interact_demo.pick_highlighter"

RAY_DISTANCE = 100000.0


def _physx_query():
    """Return PhysX scene query interface or None."""
    try:
        from omni.physx import get_physx_scene_query_interface
        return get_physx_scene_query_interface()
    except Exception:
        return None


class PickHighlighter:

    def __init__(self, info_overlay: Optional["InfoOverlay"] = None) -> None:
        self._info: Optional["InfoOverlay"] = info_overlay
        self._allowed: set[str] = set()
        self._descriptions: dict[str, str] = {}
        self._last_hit_path: Optional[str] = None
        # Reused across ticks; .Clear() invalidates cached bounds each frame.
        self._bbox_cache: Optional[UsdGeom.BBoxCache] = None
        self._point_query_generation = 0
        self._point_query_pending = False
        self._point_query_wait_frames = 0

    @property
    def last_path(self) -> Optional[str]:
        """Alias used by InteractionController._get_status_dict."""
        return self._last_hit_path

    # --- metadata wiring ---

    def set_metadata(self, allowed: set[str], descriptions: dict[str, str]) -> None:
        self._allowed = allowed
        self._descriptions = descriptions

    def reload_from_stage(self) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self.set_metadata(set(), {})
            return
        allowed, descs = metadata_store.load_from_stage(stage)
        self.set_metadata(allowed, descs)

    # --- per-frame entry point ---

    def update_at_center(self) -> Optional[str]:
        """Cast a ray from viewport-center, filter by whitelist, update selection
        and info overlay. Returns the hit path (or None)."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._clear()
            return None

        try:
            import omni.kit.viewport.utility as vp_utils
            from omni.kit.viewport.utility.camera_state import ViewportCameraState
        except Exception:  # noqa: BLE001
            self._clear()
            return None

        viewport = vp_utils.get_active_viewport()
        if viewport is None:
            self._clear()
            return None

        try:
            camera_state = ViewportCameraState()
            cam_pos = camera_state.position_world
            cam_target = camera_state.target_world
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] ViewportCameraState failed: {exc!r}")
            self._clear()
            return None

        forward = Gf.Vec3d(cam_target) - Gf.Vec3d(cam_pos)
        flen = forward.GetLength()
        if flen < 1e-9:
            self._clear()
            return None
        forward = forward / flen

        hit_path = self._raycast(stage, Gf.Vec3d(cam_pos), forward)
        # DIAG — log raycast outcome (rate-limited via _last_diag_state).
        diag_state = (hit_path, frozenset(self._allowed))
        if getattr(self, "_last_diag_state", None) != diag_state:
            self._last_diag_state = diag_state
            if hit_path is None:
                carb.log_warn(
                    f"[{_SOURCE}] DIAG raycast missed (no hit). "
                    f"cam_pos={tuple(cam_pos)} forward={tuple(forward)} "
                    f"allowed={sorted(self._allowed)}"
                )
            elif not metadata_store.is_whitelisted(hit_path, self._allowed):
                carb.log_warn(
                    f"[{_SOURCE}] DIAG hit '{hit_path}' NOT in whitelist "
                    f"{sorted(self._allowed)}"
                )
            else:
                carb.log_warn(
                    f"[{_SOURCE}] DIAG highlighting '{hit_path}'"
                )
        return self._apply_hit_path(stage, hit_path)

    def update_at_viewport_point(self, x: float, y: float) -> Optional[str]:
        """Best-effort async pick at a viewport-local point.

        ``ViewportAPI.request_query`` reports the hit later through a callback,
        so the immediate return is the current/last highlighted path.
        """
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._clear()
            return None

        try:
            px = float(x)
            py = float(y)
        except Exception:  # noqa: BLE001
            self._clear()
            return None
        if not math.isfinite(px) or not math.isfinite(py):
            self._clear()
            return None

        try:
            return self._pick_path_at_viewport_point(stage, px, py)
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] viewport point pick failed: {exc!r}")
            self._clear()
            return None

    def update_from_camera_viewport_point(
        self,
        camera_path: str,
        x: float,
        y: float,
        viewport_width: float,
        viewport_height: float,
    ) -> Optional[str]:
        """Pick by constructing a ray from a USD camera and viewport pixel."""
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._clear()
            return None
        ray = _camera_ray_from_viewport_point(
            stage,
            camera_path,
            x,
            y,
            viewport_width,
            viewport_height,
        )
        if ray is None:
            self._clear()
            return None
        origin, direction = ray
        hit_path = self._raycast(stage, origin, direction)
        return self._apply_hit_path(stage, hit_path)

    def clear(self) -> None:
        """Explicit clear — called by InteractionController on deactivate."""
        self._clear()

    def _clear(self) -> None:
        self._invalidate_pending_point_queries()
        if self._last_hit_path is not None:
            try:
                omni.usd.get_context().get_selection().set_selected_prim_paths([], True)
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] selection clear failed: {exc!r}")
            if self._info is not None:
                try:
                    self._info.hide()
                except Exception as exc:  # noqa: BLE001
                    carb.log_info(f"[{_SOURCE}] info overlay hide failed: {exc!r}")
            self._last_hit_path = None

    def cancel_pending_queries(self) -> None:
        """Invalidate async viewport-point callbacks without changing selection."""
        self._invalidate_pending_point_queries()

    def _invalidate_pending_point_queries(self) -> None:
        self._point_query_generation += 1
        self._point_query_pending = False
        self._point_query_wait_frames = 0

    def _apply_hit_path(self, stage: Usd.Stage, hit_path: Optional[str]) -> Optional[str]:
        """Apply whitelist, selection, and info overlay updates for a hit path."""
        if hit_path is None or not metadata_store.is_whitelisted(hit_path, self._allowed):
            self._clear()
            return None

        if hit_path != self._last_hit_path:
            try:
                omni.usd.get_context().get_selection().set_selected_prim_paths([hit_path], True)
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] selection update failed: {exc!r}")
            if self._info is not None:
                try:
                    title, desc = metadata_store.lookup_description(
                        hit_path, self._descriptions, stage
                    )
                    self._info.show(title, desc)
                except Exception as exc:  # noqa: BLE001
                    carb.log_info(f"[{_SOURCE}] info overlay show failed: {exc!r}")
            self._last_hit_path = hit_path
        return hit_path

    def _pick_path_at_viewport_point(self, stage: Usd.Stage, x: float, y: float) -> Optional[str]:
        """Request a prim path under a viewport-local point when Kit exposes one.

        The public ``ViewportAPI.request_query`` API is async. Its callback
        applies the hit path, while this method returns the current/last path.
        """
        if not math.isfinite(x) or not math.isfinite(y):
            self._clear()
            return None
        try:
            import omni.kit.viewport.utility as vp_utils
        except Exception:  # noqa: BLE001
            self._clear()
            return None

        try:
            viewport = vp_utils.get_active_viewport()
        except Exception:  # noqa: BLE001
            self._clear()
            return None
        if viewport is None:
            self._clear()
            return None

        request_query = getattr(viewport, "request_query", None)
        if not callable(request_query):
            self._clear()
            return None

        if self._point_query_pending and self._point_query_wait_frames > 0:
            self._point_query_wait_frames -= 1
            return self._last_hit_path
        self._point_query_pending = False

        pixel = (int(x), int(y))
        self._point_query_generation += 1
        query_generation = self._point_query_generation
        query_stage = stage
        self._point_query_pending = True
        self._point_query_wait_frames = 3

        def on_query(prim_path, world_pos=None, *args) -> None:
            del world_pos, args
            if query_generation == self._point_query_generation:
                self._point_query_pending = False
                self._point_query_wait_frames = 0
            if query_generation != self._point_query_generation:
                return
            try:
                current_stage = omni.usd.get_context().get_stage()
            except Exception:  # noqa: BLE001
                return
            if current_stage is not query_stage:
                return
            try:
                self._apply_hit_path(query_stage, _coerce_hit_path(prim_path))
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] request_query callback failed: {exc!r}")
                self._clear()

        try:
            request_query(pixel, on_query, query_name="usd_mouse_interact_demo.hover")
        except TypeError:
            try:
                request_query(pixel, on_query)
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] request_query failed: {exc!r}")
                self._point_query_pending = False
                self._clear()
                return None
        except Exception as exc:  # noqa: BLE001
            carb.log_info(f"[{_SOURCE}] request_query failed: {exc!r}")
            self._point_query_pending = False
            self._clear()
            return None
        return self._last_hit_path

    # --- raycast (PhysX → BBox fallback) ---

    def _raycast(self, stage: Usd.Stage, origin: Gf.Vec3d, direction: Gf.Vec3d) -> Optional[str]:
        # PhysX first (precise occlusion when colliders are present), but if
        # the closest collider isn't in our whitelist (e.g. a ground plane
        # blocks the ray before it reaches a whitelisted prim, or the
        # whitelisted prim has no collider at all), fall through to the
        # BBox path which only tests whitelist prims and so naturally
        # ignores irrelevant occluders like ground.
        physx = _physx_query()
        if physx is not None:
            try:
                hit = physx.raycast_closest(
                    carb.Float3(origin[0], origin[1], origin[2]),
                    carb.Float3(direction[0], direction[1], direction[2]),
                    RAY_DISTANCE,
                )
                if hit and hit.get("hit"):
                    for key in ("rigidBody", "collision", "collider", "rigid_body", "body"):
                        v = hit.get(key)
                        if isinstance(v, str) and v:
                            if metadata_store.is_whitelisted(v, self._allowed):
                                return v
                            break  # closest collider isn't whitelisted — try BBox
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] PhysX raycast failed, falling back: {exc!r}")

        # USD BBoxCache fallback — only tests whitelisted prims, so a
        # collider-less whitelisted prim still gets picked up, and ground/
        # other non-whitelisted occluders are naturally ignored.
        return self._bbox_raycast(stage, origin, direction)

    def _bbox_raycast(self, stage: Usd.Stage, origin: Gf.Vec3d, direction: Gf.Vec3d) -> Optional[str]:
        """Brute-force ray-AABB test against imageable prims under whitelist roots."""
        if not self._allowed:
            return None
        if self._bbox_cache is None:
            try:
                self._bbox_cache = UsdGeom.BBoxCache(
                    Usd.TimeCode.Default(), [UsdGeom.Tokens.default_], useExtentsHint=True
                )
            except Exception as exc:  # noqa: BLE001
                carb.log_info(f"[{_SOURCE}] BBoxCache init failed: {exc!r}")
                return None
        else:
            self._bbox_cache.Clear()
        bbox_cache = self._bbox_cache

        best_t = float("inf")
        best_path: Optional[str] = None
        for root in self._allowed:
            prim = stage.GetPrimAtPath(root)
            if not prim or not prim.IsValid():
                continue
            for p in Usd.PrimRange(prim):
                if not p.IsA(UsdGeom.Imageable):
                    continue
                if p.IsA(UsdGeom.Camera):
                    continue
                try:
                    bbox = bbox_cache.ComputeWorldBound(p)
                    arange = bbox.ComputeAlignedRange()
                    if arange.IsEmpty():
                        continue
                    lo = arange.GetMin()
                    hi = arange.GetMax()
                except Exception:  # noqa: BLE001
                    continue
                t = _ray_aabb_intersect(origin, direction, lo, hi)
                if t is not None and 0 < t < best_t:
                    best_t = t
                    best_path = p.GetPath().pathString
        return best_path

    @staticmethod
    def _ray_aabb(origin: Gf.Vec3d, direction: Gf.Vec3d,
                  bmin: Gf.Vec3d, bmax: Gf.Vec3d) -> Optional[float]:
        """Spec-named alias; delegates to module-level helper."""
        return _ray_aabb_intersect(origin, direction, bmin, bmax)


def _ray_aabb_intersect(
    origin: Gf.Vec3d,
    direction: Gf.Vec3d,
    lo: Gf.Vec3d,
    hi: Gf.Vec3d,
) -> Optional[float]:
    """Slab method. Returns the entry t (or exit t when origin is inside box), else None.

    Initialising t_min at -inf is required so that rays whose first slab entry is at
    negative t are not silently clamped — without this, the camera-inside-box case
    falls through and the prim is wrongly skipped at the call site (`0 < t` filter).
    """
    t_min = float("-inf")
    t_max = float("inf")
    for axis in range(3):
        o = origin[axis]
        d = direction[axis]
        bmin = lo[axis]
        bmax = hi[axis]
        if abs(d) < 1e-9:
            if o < bmin or o > bmax:
                return None
            continue
        inv = 1.0 / d
        t1 = (bmin - o) * inv
        t2 = (bmax - o) * inv
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > t_min:
            t_min = t1
        if t2 < t_max:
            t_max = t2
        if t_min > t_max:
            return None
    # Camera outside box → return entry t_min.
    # Camera inside box → t_min < 0 < t_max → return exit t_max as picking distance.
    if t_min > 0:
        return t_min
    if t_max > 0:
        return t_max
    return None


def _camera_ray_from_viewport_point(
    stage: Usd.Stage,
    camera_path: str,
    x: float,
    y: float,
    viewport_width: float,
    viewport_height: float,
) -> Optional[tuple[Gf.Vec3d, Gf.Vec3d]]:
    if viewport_width <= 0 or viewport_height <= 0:
        return None
    try:
        px = float(x)
        py = float(y)
        width = float(viewport_width)
        height = float(viewport_height)
    except Exception:  # noqa: BLE001
        return None
    if not all(math.isfinite(v) for v in (px, py, width, height)):
        return None

    try:
        prim = stage.GetPrimAtPath(str(camera_path).strip())
    except Exception:  # noqa: BLE001
        return None
    if not prim or not prim.IsValid() or not prim.IsA(UsdGeom.Camera):
        return None

    try:
        camera = UsdGeom.Camera(prim)
        transform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
    except Exception as exc:  # noqa: BLE001
        carb.log_info(f"[{_SOURCE}] camera transform failed: {exc!r}")
        return None

    ndc_x = (px / width - 0.5) * 2.0
    ndc_y = (0.5 - py / height) * 2.0

    try:
        position = Gf.Vec3d(transform.ExtractTranslation())
        right = _normalized(transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0)))
        up = _normalized(transform.TransformDir(Gf.Vec3d(0.0, 1.0, 0.0)))
        forward = _normalized(transform.TransformDir(Gf.Vec3d(0.0, 0.0, -1.0)))
    except Exception as exc:  # noqa: BLE001
        carb.log_info(f"[{_SOURCE}] camera basis failed: {exc!r}")
        return None

    aspect = width / height
    horizontal = _camera_horizontal_extent(camera)
    vertical = _camera_vertical_extent(camera, horizontal, aspect)
    projection = _camera_projection(camera)

    if projection == "orthographic":
        origin = position + right * (ndc_x * horizontal * 0.5) + up * (
            ndc_y * vertical * 0.5
        )
        direction = forward
    else:
        try:
            focal = float(camera.GetFocalLengthAttr().Get() or 50.0)
        except Exception:  # noqa: BLE001
            focal = 50.0
        if focal <= 0:
            focal = 50.0
        direction = _normalized(
            right * (ndc_x * horizontal * 0.5)
            + up * (ndc_y * vertical * 0.5)
            + forward * focal
        )
        origin = position

    if direction.GetLength() < 1e-9:
        return None
    return Gf.Vec3d(origin), Gf.Vec3d(direction)


def _camera_projection(camera: UsdGeom.Camera) -> str:
    try:
        value = camera.GetProjectionAttr().Get()
        return str(value)
    except Exception:  # noqa: BLE001
        return "perspective"


def _camera_horizontal_extent(camera: UsdGeom.Camera) -> float:
    try:
        value = float(camera.GetHorizontalApertureAttr().Get() or 20.955)
    except Exception:  # noqa: BLE001
        value = 20.955
    return max(1e-6, value)


def _camera_vertical_extent(
    camera: UsdGeom.Camera,
    horizontal: float,
    aspect: float,
) -> float:
    try:
        value = float(camera.GetVerticalApertureAttr().Get() or 0.0)
    except Exception:  # noqa: BLE001
        value = 0.0
    if value > 0:
        return value
    if aspect <= 0:
        return horizontal
    return horizontal / aspect


def _normalized(value: Gf.Vec3d) -> Gf.Vec3d:
    vec = Gf.Vec3d(value)
    length = vec.GetLength()
    if length < 1e-9:
        return Gf.Vec3d(0.0)
    return vec / length


def _coerce_hit_path(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    path_string = getattr(value, "pathString", None)
    if isinstance(path_string, str):
        return path_string or None
    try:
        text = str(value)
    except Exception:  # noqa: BLE001
        return None
    return text if text.startswith("/") else None
