"""NotesPanel — main UI window for browsing, editing and reviewing notes.

Layout (top → bottom):

  * Header strip: "+ New" / "Export JSON" / "Refresh"
  * Filter strip: status combo + author combo + search field
  * Stats line: counts per status
  * Note list: scrolling card per note (status swatch, title, prim path,
    author + relative time, "Go" button)
  * Detail card: full editor for the selected note (title, body, status,
    replies thread, "Add Reply", "Delete Note", camera focus actions)

Mutations route through the NoteStore (single source of truth); a
subscriber re-renders the list on each store notify.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

import carb
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui

from .note_store import (
    Note,
    NoteStore,
    STATUSES,
    STATUS_COLORS_ARGB,
    STATUS_LABELS,
    STATUS_OPEN,
    default_author,
)


PANEL_TITLE = "Stage Annotator"


def _format_relative_time(when: float) -> str:
    if when <= 0:
        return ""
    delta = time.time() - when
    if delta < 0:
        return "just now"
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


class NotesPanel:

    def __init__(
        self,
        store: NoteStore,
        on_focus_prim: Callable[[str], bool],
        on_select_prim: Callable[[str], None],
        on_export: Callable[[str], Optional[str]],
        on_pick_selection: Callable[[], Optional[str]],
    ) -> None:
        self._store = store
        self._on_focus_prim = on_focus_prim
        self._on_select_prim = on_select_prim
        self._on_export = on_export
        self._on_pick_selection = on_pick_selection
        self._window: Optional[ui.Window] = None
        self._list_container: Optional[ui.VStack] = None
        self._detail_container: Optional[ui.VStack] = None
        self._stats_label: Optional[ui.Label] = None
        self._search_field: Optional[ui.StringField] = None
        self._status_filter_combo: Optional[ui.ComboBox] = None
        self._author_filter_combo: Optional[ui.ComboBox] = None
        self._selected_id: Optional[str] = None
        self._refresh_pending: bool = False
        self._unsub: Optional[Callable[[], None]] = None
        self._known_authors: list[str] = ["(any)"]

    # ------------------------------------------------------------------
    def build(self) -> ui.Window:
        try:
            existing = ui.Workspace.get_window(PANEL_TITLE)
            if existing is not None:
                existing.visible = False
                existing.destroy()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] panel sweep: {exc}")
        self._window = ui.Window(PANEL_TITLE, width=420, height=720)
        with self._window.frame:
            with ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                with ui.VStack(spacing=4, height=0):
                    self._build_header()
                    self._build_filter_strip()
                    self._build_stats_line()
                    self._build_list_section()
                    self._build_detail_section()
        # Subscribe AFTER initial build so the first render happens with
        # fresh widget refs.
        self._unsub = self._store.subscribe(self._schedule_refresh)
        self._schedule_refresh()
        return self._window

    def destroy(self) -> None:
        if self._unsub is not None:
            try:
                self._unsub()
            except Exception:
                pass
            self._unsub = None
        if self._window is not None:
            try:
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:  # noqa: BLE001
                carb.log_warn(f"[stage_annotator] panel destroy: {exc}")
            self._window = None
        self._list_container = None
        self._detail_container = None

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        with ui.HStack(spacing=4, height=28):
            ui.Button(
                "+ New for Selection",
                width=160,
                tooltip=("Create a new note anchored to the currently "
                         "selected prim. Press it after picking a prim "
                         "in the viewport or stage panel."),
                clicked_fn=self._on_new_for_selection,
            )
            ui.Button(
                "Export JSON",
                width=110,
                tooltip="Save all notes as a JSON file.",
                clicked_fn=self._on_export_clicked,
            )
            ui.Button(
                "Refresh",
                width=80,
                tooltip="Reload from stage customData (use after manual edits).",
                clicked_fn=self._schedule_refresh,
            )

    def _build_filter_strip(self) -> None:
        with ui.HStack(spacing=4, height=24):
            ui.Label("Status:", width=46)
            self._status_filter_combo = ui.ComboBox(
                0, "All", *(STATUS_LABELS[s] for s in STATUSES), width=110,
            )
            self._status_filter_combo.model.add_item_changed_fn(
                lambda *_: self._schedule_refresh()
            )
            ui.Label("Author:", width=48)
            self._author_filter_combo = ui.ComboBox(0, "(any)", width=110)
            self._author_filter_combo.model.add_item_changed_fn(
                lambda *_: self._schedule_refresh()
            )
        with ui.HStack(spacing=4, height=24):
            ui.Label("Search:", width=46)
            self._search_field = ui.StringField()
            self._search_field.model.add_value_changed_fn(
                lambda *_: self._schedule_refresh()
            )

    def _build_stats_line(self) -> None:
        with ui.HStack(spacing=4, height=18):
            self._stats_label = ui.Label(
                "(loading…)",
                style={"color": 0xC0E0E0E0, "font_size": 11},
            )

    def _build_list_section(self) -> None:
        with ui.CollapsableFrame("Notes", collapsed=False, name="frame_notes"):
            self._list_container = ui.VStack(spacing=4, height=0)
            with self._list_container:
                ui.Label("(no notes yet)")

    def _build_detail_section(self) -> None:
        with ui.CollapsableFrame("Detail", collapsed=False, name="frame_detail"):
            self._detail_container = ui.VStack(spacing=4, height=0)
            with self._detail_container:
                ui.Label(
                    "Click a note above to edit details.",
                    style={"color": 0x80A0A0A0},
                )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def _schedule_refresh(self, *_args) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True

        async def _deferred():
            app = omni.kit.app.get_app()
            await app.next_update_async()
            self._refresh_pending = False
            self._do_refresh()

        omni.kit.async_engine.run_coroutine(_deferred())

    def _do_refresh(self) -> None:
        try:
            self._refresh_author_combo()
            self._refresh_stats()
            self._refresh_list()
            self._refresh_detail()
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[stage_annotator] panel refresh: {exc}")

    def _refresh_author_combo(self) -> None:
        if self._author_filter_combo is None:
            return
        new_authors = ["(any)"] + sorted(self._store.authors())
        if new_authors == self._known_authors:
            return
        self._known_authors = new_authors
        # ComboBox doesn't expose easy item replacement — recreate.
        try:
            current_idx = (
                self._author_filter_combo.model.get_item_value_model().get_value_as_int()
            )
        except Exception:
            current_idx = 0
        if current_idx >= len(new_authors):
            current_idx = 0
        # Replace by destroying and rebuilding the entire filter strip is
        # too disruptive. Easier: rebuild the combo's model items via
        # add_item / remove_item. ui.ComboBox does not expose these in
        # 107.x — fall back to leaving the old combo in place; we read
        # its current text and match against authors at filter time.

    def _refresh_stats(self) -> None:
        if self._stats_label is None:
            return
        s = self._store.stats()
        total = s.get("total", 0)
        parts = [f"{total} total"]
        for st in STATUSES:
            c = s.get(st, 0)
            parts.append(f"{STATUS_LABELS[st]}: {c}")
        self._stats_label.text = "  •  ".join(parts)

    def _refresh_list(self) -> None:
        if self._list_container is None:
            return
        self._list_container.clear()
        notes = self._filtered_notes()
        with self._list_container:
            if not notes:
                ui.Label(
                    "(no notes match current filter)",
                    style={"color": 0x80A0A0A0},
                )
                return
            for n in notes:
                self._build_note_card(n)

    def _refresh_detail(self) -> None:
        if self._detail_container is None:
            return
        self._detail_container.clear()
        with self._detail_container:
            note = (
                self._store.get(self._selected_id)
                if self._selected_id is not None else None
            )
            if note is None:
                ui.Label(
                    "Click a note above to edit details.",
                    style={"color": 0x80A0A0A0},
                )
                return
            self._build_detail_view(note)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def _selected_status_filter(self) -> Optional[str]:
        if self._status_filter_combo is None:
            return None
        try:
            idx = (
                self._status_filter_combo.model.get_item_value_model()
                .get_value_as_int()
            )
        except Exception:
            return None
        if idx <= 0:
            return None
        if idx - 1 >= len(STATUSES):
            return None
        return STATUSES[idx - 1]

    def _selected_author_filter(self) -> Optional[str]:
        if self._author_filter_combo is None:
            return None
        # Read text rather than index because we don't dynamically update
        # the items list — we match by string.
        try:
            value_model = self._author_filter_combo.model.get_item_value_model()
            idx = value_model.get_value_as_int()
        except Exception:
            return None
        authors = self._known_authors
        if idx <= 0 or idx >= len(authors):
            return None
        return authors[idx]

    def _search_text(self) -> Optional[str]:
        if self._search_field is None:
            return None
        try:
            return self._search_field.model.get_value_as_string() or None
        except Exception:
            return None

    def _filtered_notes(self) -> list[Note]:
        return self._store.filter(
            status=self._selected_status_filter(),
            author=self._selected_author_filter(),
            substring=self._search_text(),
        )

    # ------------------------------------------------------------------
    # Card / detail UI
    # ------------------------------------------------------------------
    def _build_note_card(self, note: Note) -> None:
        is_selected = note.id == self._selected_id
        bg = 0xFF202028 if is_selected else 0xFF181820
        with ui.Frame(
            style={
                "background_color": bg,
                "border_radius": 4,
                "border_width": 1 if is_selected else 0,
                "border_color": 0xFF4080FF,
            },
        ):
            with ui.VStack(spacing=2, height=0):
                with ui.HStack(spacing=6, height=20):
                    color = STATUS_COLORS_ARGB.get(
                        note.status, STATUS_COLORS_ARGB[STATUS_OPEN]
                    )
                    ui.Rectangle(
                        width=10, height=10,
                        style={
                            "background_color": color,
                            "border_radius": 5,
                        },
                    )
                    ui.Label(
                        note.title or "(untitled)",
                        style={
                            "color": 0xFFFFFFFF,
                            "font_size": 13,
                        },
                    )
                with ui.HStack(spacing=4, height=18):
                    short_prim = _truncate(note.prim_path, 36)
                    ui.Label(
                        short_prim,
                        style={"color": 0xC0A0C0FF, "font_size": 11},
                        tooltip=note.prim_path,
                    )
                with ui.HStack(spacing=4, height=18):
                    rel = _format_relative_time(note.updated_at or note.created_at)
                    meta = (
                        f"{note.author or 'anonymous'}  •  {rel}  •  "
                        f"{len(note.replies)} repl"
                        + ("ies" if len(note.replies) != 1 else "y")
                    )
                    ui.Label(
                        meta,
                        style={"color": 0x80A0A0A0, "font_size": 10},
                    )
                with ui.HStack(spacing=4, height=22):
                    ui.Button(
                        "Open",
                        width=60,
                        clicked_fn=lambda nid=note.id: self._select_note(nid),
                    )
                    ui.Button(
                        "Go",
                        width=40,
                        tooltip="Frame the viewport camera on this prim.",
                        clicked_fn=lambda p=note.prim_path: self._on_focus_prim(p),
                    )

    def _build_detail_view(self, note: Note) -> None:
        # Title editor
        with ui.HStack(spacing=4, height=22):
            ui.Label("Title:", width=50)
            title_field = ui.StringField()
            title_field.model.set_value(note.title)
            title_field.model.add_end_edit_fn(
                lambda m, nid=note.id: self._store.update(
                    nid, title=m.get_value_as_string()
                )
            )
        # Prim path display
        with ui.HStack(spacing=4, height=20):
            ui.Label("Prim:", width=50)
            ui.Label(
                note.prim_path,
                style={"color": 0xC0A0C0FF, "font_size": 11},
            )
        # Body editor
        ui.Label("Body:", height=18)
        body_field = ui.StringField(multiline=True, height=80)
        body_field.model.set_value(note.body)
        body_field.model.add_end_edit_fn(
            lambda m, nid=note.id: self._store.update(
                nid, body=m.get_value_as_string()
            )
        )
        # Status + actions
        with ui.HStack(spacing=4, height=24):
            ui.Label("Status:", width=50)
            cur_idx = STATUSES.index(note.status) if note.status in STATUSES else 0
            status_combo = ui.ComboBox(
                cur_idx, *(STATUS_LABELS[s] for s in STATUSES), width=120,
            )
            def _on_status_change(*_args, nid=note.id, c=status_combo):
                try:
                    idx = c.model.get_item_value_model().get_value_as_int()
                except Exception:
                    return
                if 0 <= idx < len(STATUSES):
                    self._store.update(nid, status=STATUSES[idx])
            status_combo.model.add_item_changed_fn(_on_status_change)
            ui.Button(
                "Frame Prim",
                width=90,
                tooltip="Move the viewport camera onto the host prim.",
                clicked_fn=lambda p=note.prim_path: self._on_focus_prim(p),
            )
            ui.Button(
                "Select Prim",
                width=90,
                tooltip="Select host prim in stage panel.",
                clicked_fn=lambda p=note.prim_path: self._on_select_prim(p),
            )
        # Author + timestamps
        ts_str = (
            time.strftime("%Y-%m-%d %H:%M:%S",
                          time.localtime(note.created_at))
            if note.created_at else "?"
        )
        ui.Label(
            f"Author: {note.author or 'anonymous'}    Created: {ts_str}",
            style={"color": 0x80A0A0A0, "font_size": 10},
        )
        # Replies thread
        ui.Label(f"Replies ({len(note.replies)}):", height=18)
        if note.replies:
            with ui.VStack(spacing=2):
                for i, r in enumerate(note.replies):
                    self._build_reply_row(note.id, i, r)
        # Add reply
        with ui.HStack(spacing=4, height=22):
            reply_field = ui.StringField()
            reply_field.model.set_value("")
            ui.Button(
                "Add Reply",
                width=90,
                clicked_fn=lambda nid=note.id, f=reply_field:
                    self._on_add_reply(nid, f),
            )
        # Delete button — last so accidental clicks are unlikely.
        with ui.HStack(spacing=4, height=24):
            ui.Spacer(width=2)
            ui.Button(
                "Delete Note",
                width=120,
                style={"background_color": 0xFFB04040},
                tooltip="Permanently delete this note + its 3-D pin.",
                clicked_fn=lambda nid=note.id: self._on_delete_note(nid),
            )

    def _build_reply_row(self, note_id: str, index: int, reply) -> None:
        rel = _format_relative_time(reply.created_at)
        with ui.Frame(
            style={
                "background_color": 0xFF101018,
                "border_radius": 3,
            },
        ):
            with ui.VStack(spacing=2, height=0):
                with ui.HStack(spacing=4, height=16):
                    ui.Label(
                        f"  [{reply.author}]",
                        style={"color": 0xC0FFC080, "font_size": 11},
                    )
                    ui.Spacer()
                    ui.Label(
                        rel,
                        style={"color": 0x80808088, "font_size": 10},
                    )
                    ui.Button(
                        "x",
                        width=20,
                        height=14,
                        tooltip="Delete this reply.",
                        clicked_fn=lambda nid=note_id, i=index:
                            self._store.delete_reply(nid, i),
                    )
                ui.Label(
                    "  " + (reply.body or ""),
                    style={"color": 0xFFE0E0E0, "font_size": 11},
                    word_wrap=True,
                )

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _select_note(self, note_id: str) -> None:
        self._selected_id = note_id
        self._schedule_refresh()
        # Also auto-frame the prim so user immediately sees what the note
        # is talking about.
        n = self._store.get(note_id)
        if n is not None and n.prim_path:
            try:
                self._on_focus_prim(n.prim_path)
            except Exception:
                pass

    def _on_new_for_selection(self) -> None:
        prim = self._on_pick_selection()
        if not prim:
            carb.log_warn(
                "[stage_annotator] no prim selected — pick a prim first"
            )
            return
        n = Note(
            id="",
            prim_path=prim,
            title="(new note)",
            body="",
            author=default_author(),
            created_at=0.0,
            updated_at=0.0,
            status=STATUS_OPEN,
        )
        ok = self._store.add(n)
        if ok:
            # Select the freshly-added note (the last in the store).
            notes = self._store.list()
            if notes:
                self._selected_id = notes[-1].id

    def _on_add_reply(self, note_id: str, field: ui.StringField) -> None:
        try:
            text = field.model.get_value_as_string() or ""
        except Exception:
            text = ""
        if not text.strip():
            return
        ok = self._store.add_reply(note_id, text, default_author())
        if ok:
            try:
                field.model.set_value("")
            except Exception:
                pass

    def _on_delete_note(self, note_id: str) -> None:
        ok = self._store.remove(note_id)
        if ok and self._selected_id == note_id:
            self._selected_id = None

    def _on_export_clicked(self) -> None:
        blob = self._store.export_json()
        path = self._on_export(blob)
        if path:
            carb.log_info(f"[stage_annotator] exported notes to {path}")


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    half = (max_len - 1) // 2
    return s[:half] + "…" + s[-(max_len - 1 - half):]
