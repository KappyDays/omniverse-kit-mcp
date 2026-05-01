"""Persistent waypoint store — survives stage save/load.

Waypoints are user-marked floor-plane points the radar shows as anchored
flags. Stored as a JSON blob in the rootLayer's customData under
``stage_compass:waypoints``. Each waypoint has a label, color, and the
floor-plane (a, b) coordinate plus the up-axis component captured at save
time. The HUD shows a flag glyph at each waypoint and clicking it
teleports the camera there with the saved height restored.
"""
from __future__ import annotations

import dataclasses
import json
import time
from typing import Iterable

import carb


CUSTOM_DATA_KEY = "stage_compass:waypoints"
MAX_WAYPOINTS = 64
DEFAULT_COLOR = 0xFFFF80E0


@dataclasses.dataclass(slots=True)
class Waypoint:
    name: str
    floor_a: float
    floor_b: float
    height: float
    color_argb: int = DEFAULT_COLOR
    created_at: float = 0.0

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "a": self.floor_a,
            "b": self.floor_b,
            "h": self.height,
            "color": self.color_argb,
            "ts": self.created_at,
        }

    @classmethod
    def from_json(cls, blob: dict) -> "Waypoint":
        return cls(
            name=str(blob.get("name", "")),
            floor_a=float(blob.get("a", 0.0)),
            floor_b=float(blob.get("b", 0.0)),
            height=float(blob.get("h", 0.0)),
            color_argb=int(blob.get("color", DEFAULT_COLOR)),
            created_at=float(blob.get("ts", 0.0)),
        )


class WaypointStore:
    """In-memory list backed by stage rootLayer customData JSON."""

    def __init__(self) -> None:
        self._waypoints: list[Waypoint] = []
        self._loaded_for_layer_id: int | None = None

    def list(self) -> list[Waypoint]:
        self._maybe_reload()
        return list(self._waypoints)

    def add(self, wp: Waypoint) -> bool:
        self._maybe_reload()
        if len(self._waypoints) >= MAX_WAYPOINTS:
            carb.log_warn(
                f"[stage_compass] waypoint cap {MAX_WAYPOINTS} reached"
            )
            return False
        if not wp.created_at:
            wp.created_at = time.time()
        self._waypoints.append(wp)
        self._save()
        return True

    def remove(self, name: str) -> bool:
        self._maybe_reload()
        before = len(self._waypoints)
        self._waypoints = [w for w in self._waypoints if w.name != name]
        if len(self._waypoints) != before:
            self._save()
            return True
        return False

    def clear(self) -> None:
        self._maybe_reload()
        self._waypoints = []
        self._save()

    def rename(self, old: str, new: str) -> bool:
        self._maybe_reload()
        if not new or any(w.name == new for w in self._waypoints):
            return False
        for w in self._waypoints:
            if w.name == old:
                w.name = new
                self._save()
                return True
        return False

    # ------------------------------------------------------------------
    def _root_layer(self):
        try:
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return None
            return stage.GetRootLayer()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] root layer access failed: {exc}")
            return None

    def _maybe_reload(self) -> None:
        layer = self._root_layer()
        if layer is None:
            self._waypoints = []
            self._loaded_for_layer_id = None
            return
        # ``id()`` is a cheap stable handle while the stage is open. Stage
        # reload swaps in a fresh layer object — id() differs → reload.
        if self._loaded_for_layer_id == id(layer):
            return
        try:
            cd = layer.customLayerData or {}
            blob = cd.get(CUSTOM_DATA_KEY)
            if blob is None:
                self._waypoints = []
            else:
                if isinstance(blob, str):
                    decoded = json.loads(blob)
                else:
                    decoded = blob
                items = decoded if isinstance(decoded, list) else decoded.get(
                    "waypoints", []
                )
                self._waypoints = [Waypoint.from_json(b) for b in items]
            self._loaded_for_layer_id = id(layer)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] waypoint load failed: {exc}")
            self._waypoints = []
            self._loaded_for_layer_id = id(layer)

    def _save(self) -> None:
        layer = self._root_layer()
        if layer is None:
            return
        try:
            cd = dict(layer.customLayerData or {})
            cd[CUSTOM_DATA_KEY] = json.dumps(
                [w.to_json() for w in self._waypoints]
            )
            layer.customLayerData = cd
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_compass] waypoint save failed: {exc}")


def replace_all(store: WaypointStore, items: Iterable[Waypoint]) -> None:
    """Used by the settings panel "Import" flow."""
    store.clear()
    for w in items:
        store.add(w)
