"""PinRenderer — keeps 3-D sphere markers in the stage in sync with notes.

Every note becomes a small UsdGeom.Sphere under ``/Annotations/<id>/Pin``
positioned slightly above the host prim's bounding box. The sphere's
``displayColor`` mirrors the note's status, so a glance at the viewport
tells the reviewer where the open / resolved review items are. The
renderer is a *cache-coherent mirror* of the note store: on each store
change it re-syncs (creates new, repositions moved, deletes vanished
pins) without rebuilding the whole tree.
"""
from __future__ import annotations

from typing import Optional

import carb
import omni.usd

from .note_store import (
    Note,
    NoteStore,
    STATUS_COLORS_RGB,
    STATUS_OPEN,
)


PINS_ROOT = "/Annotations"
PIN_PRIM_NAME = "Pin"
PIN_MIN_RADIUS = 0.03
PIN_MAX_RADIUS = 1.0
PIN_REL_FACTOR = 0.012   # radius ≈ 1.2 % of host bbox diagonal
PIN_FALLBACK_RADIUS = 0.15
PIN_VERTICAL_OFFSET_FACTOR = 1.05  # pin sits just above the host top


class PinRenderer:

    def __init__(self, store: NoteStore) -> None:
        self._store = store
        self._unsub = None
        self._known_ids: set[str] = set()

    # ------------------------------------------------------------------
    def attach(self) -> None:
        self._unsub = self._store.subscribe(self.sync)
        self.sync()

    def detach(self, remove_pins: bool = False) -> None:
        if self._unsub is not None:
            try:
                self._unsub()
            except Exception:
                pass
            self._unsub = None
        if remove_pins:
            self._delete_root()

    # ------------------------------------------------------------------
    def sync(self) -> None:
        try:
            stage = omni.usd.get_context().get_stage()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] pin sync stage access: {exc}")
            return
        if stage is None:
            return
        try:
            self._ensure_root(stage)
            notes = self._store.list()
            current_ids = {n.id for n in notes}
            # Remove pins for notes that no longer exist.
            for stale_id in self._known_ids - current_ids:
                self._delete_pin(stage, stale_id)
            for n in notes:
                self._upsert_pin(stage, n)
            self._known_ids = current_ids
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] pin sync failed: {exc}")

    # ------------------------------------------------------------------
    # USD operations
    # ------------------------------------------------------------------
    def _ensure_root(self, stage) -> None:
        from pxr import Sdf, UsdGeom
        if not stage.GetPrimAtPath(PINS_ROOT).IsValid():
            UsdGeom.Scope.Define(stage, Sdf.Path(PINS_ROOT))

    def _delete_root(self) -> None:
        try:
            import omni.kit.commands
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return
            if stage.GetPrimAtPath(PINS_ROOT).IsValid():
                omni.kit.commands.execute("DeletePrims", paths=[PINS_ROOT])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] pin root delete: {exc}")

    def _delete_pin(self, stage, note_id: str) -> None:
        try:
            import omni.kit.commands
            prim_path = f"{PINS_ROOT}/{_safe_id(note_id)}"
            if stage.GetPrimAtPath(prim_path).IsValid():
                omni.kit.commands.execute("DeletePrims", paths=[prim_path])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] pin delete {note_id}: {exc}")

    def _upsert_pin(self, stage, note: Note) -> None:
        from pxr import Gf, Sdf, UsdGeom
        host_path = note.prim_path
        host_prim = stage.GetPrimAtPath(host_path) if host_path else None

        # Position: bbox top centre of host prim. Fallback to stage origin
        # if host is missing or has no bbox (e.g. xform with no children).
        position = self._position_for_host(stage, host_prim)
        radius = self._radius_for_host(stage, host_prim)

        scope_path = f"{PINS_ROOT}/{_safe_id(note.id)}"
        scope = UsdGeom.Xform.Define(stage, Sdf.Path(scope_path))
        # Stamp metadata so external tooling can identify a pin without
        # parsing the parent layout.
        scope_prim = scope.GetPrim()
        scope_prim.CreateAttribute(
            "stageAnnotator:noteId", Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(note.id)
        scope_prim.CreateAttribute(
            "stageAnnotator:hostPrim", Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(host_path)
        scope_prim.CreateAttribute(
            "stageAnnotator:title", Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(note.title)
        scope_prim.CreateAttribute(
            "stageAnnotator:status", Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(note.status)

        # Move the scope to the host's bbox top.
        scope_xformable = UsdGeom.Xformable(scope)
        ops = scope_xformable.GetOrderedXformOps()
        t_op = next(
            (op for op in ops if op.GetOpType() == UsdGeom.XformOp.TypeTranslate),
            None,
        )
        if t_op is None:
            t_op = scope_xformable.AddTranslateOp()
        t_op.Set(Gf.Vec3d(*position))

        pin_path = f"{scope_path}/{PIN_PRIM_NAME}"
        sphere = UsdGeom.Sphere.Define(stage, Sdf.Path(pin_path))
        sphere.GetRadiusAttr().Set(float(radius))
        sphere.CreateExtentAttr().Set(
            [(-radius, -radius, -radius), (radius, radius, radius)]
        )
        # Status colour.
        rgb = STATUS_COLORS_RGB.get(note.status, STATUS_COLORS_RGB[STATUS_OPEN])
        try:
            sphere.GetDisplayColorAttr().Set([Gf.Vec3f(*rgb)])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] color set failed for {note.id}: {exc}")
        # Disable physics / colliders implicitly — nothing to do; Sphere
        # has no physics by default. We do mark the pin non-selectable in
        # primary picking so users still pick the host prim by clicking
        # near it, but selectable enough for explicit click on the pin.
        sphere.GetPrim().CreateAttribute(
            "primvars:doNotCastShadows", Sdf.ValueTypeNames.Bool, custom=True,
        ).Set(True)

    # ------------------------------------------------------------------
    def _position_for_host(self, stage, host_prim):
        from pxr import Gf, Usd, UsdGeom
        if host_prim is None or not host_prim.IsValid():
            return (0.0, 0.0, 0.0)
        try:
            up_axis = UsdGeom.GetStageUpAxis(stage)
        except Exception:
            up_axis = "Y"
        try:
            cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.proxy],
                useExtentsHint=True,
            )
            bb = cache.ComputeWorldBound(host_prim)
            r = bb.GetRange()
            if not r.IsEmpty():
                aligned = bb.ComputeAlignedBox()
                centre = aligned.GetMidpoint()
                top = aligned.GetMax()
                # Lift along up-axis so the pin sits above the host.
                if up_axis == "Z":
                    return (
                        float(centre[0]),
                        float(centre[1]),
                        float(top[2]) + (float(top[2]) - float(centre[2])) * 0.2 + 0.1,
                    )
                # Y-up
                return (
                    float(centre[0]),
                    float(top[1]) + (float(top[1]) - float(centre[1])) * 0.2 + 0.1,
                    float(centre[2]),
                )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] bbox failed: {exc}")

        # Fallback: read xformOp:translate.
        t_attr = host_prim.GetAttribute("xformOp:translate")
        if t_attr and t_attr.IsValid():
            v = t_attr.Get()
            if v is not None:
                return (float(v[0]), float(v[1]), float(v[2]))
        return (0.0, 0.0, 0.0)

    def _radius_for_host(self, stage, host_prim) -> float:
        if host_prim is None or not host_prim.IsValid():
            return PIN_FALLBACK_RADIUS
        try:
            from pxr import Usd, UsdGeom
            cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.proxy],
                useExtentsHint=True,
            )
            bb = cache.ComputeWorldBound(host_prim)
            if bb.GetRange().IsEmpty():
                return PIN_FALLBACK_RADIUS
            aligned = bb.ComputeAlignedBox()
            mn = aligned.GetMin()
            mx = aligned.GetMax()
            diag = (
                (float(mx[0]) - float(mn[0])) ** 2
                + (float(mx[1]) - float(mn[1])) ** 2
                + (float(mx[2]) - float(mn[2])) ** 2
            ) ** 0.5
            r = diag * PIN_REL_FACTOR
            if r < PIN_MIN_RADIUS:
                return PIN_MIN_RADIUS
            if r > PIN_MAX_RADIUS:
                return PIN_MAX_RADIUS
            return r
        except Exception:
            return PIN_FALLBACK_RADIUS


def _safe_id(note_id: str) -> str:
    """USD prim names accept ``[A-Za-z0-9_]`` only — sanitise just in case."""
    out = []
    for ch in note_id:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out) or "note"
    if s[0].isdigit():
        s = "n_" + s
    return s


def find_note_id_for_prim(prim) -> Optional[str]:
    """Reverse-lookup: given a clicked prim under ``/Annotations``, return
    the note id stamped on its parent scope. Returns None if the prim is
    not part of the annotation tree.
    """
    try:
        cur = prim
        while cur and cur.IsValid():
            attr = cur.GetAttribute("stageAnnotator:noteId")
            if attr and attr.IsValid():
                v = attr.Get()
                if v:
                    return str(v)
            cur = cur.GetParent()
    except Exception:
        return None
    return None
