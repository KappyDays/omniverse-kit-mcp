"""Status-label formatting. Pure (no Kit imports) — unit-tested with pytest.

All strings are ASCII/English only: the Kit 107 ``omni.ui`` font atlas has no
CJK glyphs and renders non-ASCII as boxes, so even the progress arrow is "->"
rather than a unicode arrow (hard rule — see kkr-extensions/CLAUDE.md).
"""

from __future__ import annotations

# Extension lifecycle phases that drive the status Label.
PHASE_NO_SCENE = "no_scene"
PHASE_LOADING = "loading"
PHASE_SCENE_LOADED = "scene_loaded"
PHASE_NOT_PLAYING = "not_playing"
PHASE_READY = "ready"
PHASE_TRANSMITTING = "transmitting"
PHASE_DELIVERED = "delivered"
PHASE_ERROR = "error"


def format_status(
    phase: str,
    *,
    progress: float = 0.0,
    target_server: int = 0,
    total_servers: int = 0,
    lit_servers: int = 0,
    detail: str = "",
) -> str:
    if phase == PHASE_NO_SCENE:
        return "No scene loaded - press Load Scene"
    if phase == PHASE_LOADING:
        return "Loading scene ..."
    if phase == PHASE_SCENE_LOADED:
        return "Scene loaded - press Play"
    if phase == PHASE_NOT_PLAYING:
        return "Press Play first"
    if phase == PHASE_READY:
        return "Ready - click the PC power button"
    if phase == PHASE_TRANSMITTING:
        pct = int(round(_clamp01(progress) * 100))
        return f"Transmitting -> Server {target_server:02d} ({pct}%)"
    if phase == PHASE_DELIVERED:
        return f"Delivered: {lit_servers}/{total_servers} servers"
    if phase == PHASE_ERROR:
        return f"Error: {detail}" if detail else "Error"
    return str(phase)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
