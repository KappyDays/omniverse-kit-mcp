"""NoteStore — note + reply data model with JSON persistence on the stage.

Notes live on the stage's rootLayer customData (key
``stage_annotator:notes``) so they round-trip through ``save`` / ``open``
just like any other USD authoring change. The store is the single source
of truth — UI widgets, the 3D pin renderer, and the JSON export all read
from here. Edit operations dispatch a list of subscribers so external
listeners (like the pin renderer) can re-sync without polling.
"""
from __future__ import annotations

import dataclasses
import getpass
import json
import time
import uuid
from typing import Callable, Iterable, Optional

import carb


CUSTOM_DATA_KEY = "stage_annotator:notes"
SCHEMA_VERSION = 1
MAX_NOTES = 256
MAX_REPLIES_PER_NOTE = 64

STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"
STATUS_WONTFIX = "wontfix"

STATUSES: tuple[str, ...] = (
    STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_WONTFIX,
)

STATUS_LABELS: dict[str, str] = {
    STATUS_OPEN:        "Open",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_RESOLVED:    "Resolved",
    STATUS_WONTFIX:     "Won't Fix",
}

STATUS_COLORS_ARGB: dict[str, int] = {
    STATUS_OPEN:        0xFFE04050,
    STATUS_IN_PROGRESS: 0xFFFFC040,
    STATUS_RESOLVED:    0xFF40D060,
    STATUS_WONTFIX:     0xFF808088,
}

# 0..1 RGB tuples (used for USD displayColor on the 3-D pin sphere).
STATUS_COLORS_RGB: dict[str, tuple[float, float, float]] = {
    STATUS_OPEN:        (0.88, 0.25, 0.31),
    STATUS_IN_PROGRESS: (1.00, 0.75, 0.25),
    STATUS_RESOLVED:    (0.25, 0.82, 0.38),
    STATUS_WONTFIX:     (0.50, 0.50, 0.55),
}


@dataclasses.dataclass(slots=True)
class Reply:
    body: str
    author: str
    created_at: float

    def to_json(self) -> dict:
        return {"b": self.body, "a": self.author, "t": self.created_at}

    @classmethod
    def from_json(cls, blob: dict) -> "Reply":
        return cls(
            body=str(blob.get("b", "")),
            author=str(blob.get("a", "")),
            created_at=float(blob.get("t", 0.0)),
        )


@dataclasses.dataclass(slots=True)
class Note:
    id: str
    prim_path: str
    title: str
    body: str
    author: str
    created_at: float
    updated_at: float
    status: str
    replies: list[Reply] = dataclasses.field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "id":       self.id,
            "prim":     self.prim_path,
            "title":    self.title,
            "body":     self.body,
            "author":   self.author,
            "created":  self.created_at,
            "updated":  self.updated_at,
            "status":   self.status,
            "replies":  [r.to_json() for r in self.replies],
        }

    @classmethod
    def from_json(cls, blob: dict) -> "Note":
        return cls(
            id=str(blob.get("id", "")),
            prim_path=str(blob.get("prim", "")),
            title=str(blob.get("title", "")),
            body=str(blob.get("body", "")),
            author=str(blob.get("author", "")),
            created_at=float(blob.get("created", 0.0)),
            updated_at=float(blob.get("updated", 0.0)),
            status=str(blob.get("status", STATUS_OPEN)),
            replies=[Reply.from_json(r) for r in blob.get("replies", [])],
        )


def default_author() -> str:
    """OS user (best-effort) — falls back to "anonymous" inside Kit-only env."""
    try:
        return getpass.getuser() or "anonymous"
    except Exception:
        return "anonymous"


def new_note_id() -> str:
    """Random UUID for the note. Used as USD prim name suffix → safe chars."""
    return uuid.uuid4().hex[:12]


class NoteStore:
    def __init__(self) -> None:
        self._notes: list[Note] = []
        self._loaded_for_layer_id: Optional[int] = None
        self._listeners: list[Callable[[], None]] = []

    # ---------------------- subscribe ----------------------
    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a no-arg callback fired after every mutation. Returns a
        cancel handle the subscriber can call from its on_shutdown."""
        self._listeners.append(callback)
        def _cancel() -> None:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass
        return _cancel

    def _notify(self) -> None:
        for cb in list(self._listeners):
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_annotator] subscriber error: {exc}")

    # ---------------------- queries ----------------------
    def list(self) -> list[Note]:
        self._maybe_reload()
        return list(self._notes)

    def get(self, note_id: str) -> Optional[Note]:
        self._maybe_reload()
        for n in self._notes:
            if n.id == note_id:
                return n
        return None

    def by_prim(self, prim_path: str) -> list[Note]:
        self._maybe_reload()
        return [n for n in self._notes if n.prim_path == prim_path]

    def filter(
        self,
        status: Optional[str] = None,
        author: Optional[str] = None,
        substring: Optional[str] = None,
    ) -> list[Note]:
        self._maybe_reload()
        sub = (substring or "").lower().strip()
        out: list[Note] = []
        for n in self._notes:
            if status is not None and n.status != status:
                continue
            if author is not None and n.author != author:
                continue
            if sub:
                hay = (n.title + " " + n.body + " " + n.prim_path).lower()
                if sub not in hay:
                    continue
            out.append(n)
        return out

    def authors(self) -> list[str]:
        self._maybe_reload()
        seen: dict[str, None] = {}
        for n in self._notes:
            if n.author and n.author not in seen:
                seen[n.author] = None
        return list(seen.keys())

    def stats(self) -> dict[str, int]:
        self._maybe_reload()
        counts = {s: 0 for s in STATUSES}
        for n in self._notes:
            counts[n.status] = counts.get(n.status, 0) + 1
        counts["total"] = len(self._notes)
        return counts

    # ---------------------- mutations ----------------------
    def add(self, note: Note) -> bool:
        self._maybe_reload()
        if len(self._notes) >= MAX_NOTES:
            carb.log_warn(
                f"[stage_annotator] note cap {MAX_NOTES} reached"
            )
            return False
        if not note.id:
            note.id = new_note_id()
        if not note.created_at:
            note.created_at = time.time()
        if not note.updated_at:
            note.updated_at = note.created_at
        if note.status not in STATUSES:
            note.status = STATUS_OPEN
        self._notes.append(note)
        self._save()
        self._notify()
        return True

    def update(self, note_id: str, **fields) -> bool:
        self._maybe_reload()
        for n in self._notes:
            if n.id != note_id:
                continue
            allowed = {"title", "body", "status", "prim_path"}
            for k, v in fields.items():
                if k in allowed:
                    setattr(n, k, v)
            n.updated_at = time.time()
            self._save()
            self._notify()
            return True
        return False

    def remove(self, note_id: str) -> bool:
        self._maybe_reload()
        before = len(self._notes)
        self._notes = [n for n in self._notes if n.id != note_id]
        if len(self._notes) != before:
            self._save()
            self._notify()
            return True
        return False

    def add_reply(self, note_id: str, body: str, author: str) -> bool:
        self._maybe_reload()
        if not body.strip():
            return False
        for n in self._notes:
            if n.id != note_id:
                continue
            if len(n.replies) >= MAX_REPLIES_PER_NOTE:
                carb.log_warn(
                    f"[stage_annotator] reply cap reached on note {note_id}"
                )
                return False
            n.replies.append(Reply(
                body=body.strip(),
                author=author or default_author(),
                created_at=time.time(),
            ))
            n.updated_at = time.time()
            self._save()
            self._notify()
            return True
        return False

    def delete_reply(self, note_id: str, reply_index: int) -> bool:
        self._maybe_reload()
        for n in self._notes:
            if n.id != note_id:
                continue
            if 0 <= reply_index < len(n.replies):
                del n.replies[reply_index]
                n.updated_at = time.time()
                self._save()
                self._notify()
                return True
        return False

    def clear_all(self) -> int:
        self._maybe_reload()
        n = len(self._notes)
        self._notes = []
        self._save()
        self._notify()
        return n

    # ---------------------- export / import ----------------------
    def export_json(self) -> str:
        self._maybe_reload()
        return json.dumps(
            {
                "schema": SCHEMA_VERSION,
                "exported_at": time.time(),
                "notes": [n.to_json() for n in self._notes],
            },
            indent=2,
        )

    def import_json(self, blob: str) -> int:
        try:
            decoded = json.loads(blob)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] import failed: {exc}")
            return 0
        items = decoded.get("notes") if isinstance(decoded, dict) else decoded
        if not isinstance(items, list):
            return 0
        loaded = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                n = Note.from_json(it)
                if not n.id:
                    n.id = new_note_id()
                self._notes.append(n)
                loaded += 1
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_annotator] skip bad entry: {exc}")
        if loaded:
            self._save()
            self._notify()
        return loaded

    # ---------------------- persistence ----------------------
    def _root_layer(self):
        try:
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                return None
            return stage.GetRootLayer()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] root layer access: {exc}")
            return None

    def _maybe_reload(self) -> None:
        layer = self._root_layer()
        if layer is None:
            self._notes = []
            self._loaded_for_layer_id = None
            return
        if self._loaded_for_layer_id == id(layer):
            return
        try:
            cd = layer.customLayerData or {}
            blob = cd.get(CUSTOM_DATA_KEY)
            if blob is None:
                self._notes = []
            else:
                if isinstance(blob, str):
                    decoded = json.loads(blob)
                else:
                    decoded = blob
                if isinstance(decoded, dict):
                    items = decoded.get("notes", [])
                else:
                    items = decoded
                self._notes = [
                    Note.from_json(b) for b in items if isinstance(b, dict)
                ]
            self._loaded_for_layer_id = id(layer)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] note load failed: {exc}")
            self._notes = []
            self._loaded_for_layer_id = id(layer)

    def _save(self) -> None:
        layer = self._root_layer()
        if layer is None:
            return
        try:
            cd = dict(layer.customLayerData or {})
            cd[CUSTOM_DATA_KEY] = json.dumps(
                {
                    "schema": SCHEMA_VERSION,
                    "notes": [n.to_json() for n in self._notes],
                }
            )
            layer.customLayerData = cd
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] note save failed: {exc}")
