"""Unit tests for telemetry.format_status (pure label formatting)."""

from omni.office_mcp.network_demo import telemetry as tel


def test_no_scene():
    assert tel.format_status(tel.PHASE_NO_SCENE) == "No scene loaded - press Load Scene"


def test_scene_loaded():
    assert tel.format_status(tel.PHASE_SCENE_LOADED) == "Scene loaded - press Play"


def test_ready():
    assert tel.format_status(tel.PHASE_READY) == "Ready - click the PC power button"


def test_not_playing_hint():
    assert tel.format_status(tel.PHASE_NOT_PLAYING) == "Press Play first"


def test_transmitting_format():
    s = tel.format_status(
        tel.PHASE_TRANSMITTING, progress=0.45, target_server=2, total_servers=3,
    )
    assert s == "Transmitting -> Server 02 (45%)"


def test_transmitting_progress_clamped():
    s = tel.format_status(tel.PHASE_TRANSMITTING, progress=1.5, target_server=3)
    assert "(100%)" in s


def test_delivered_format():
    s = tel.format_status(tel.PHASE_DELIVERED, lit_servers=3, total_servers=3)
    assert s == "Delivered: 3/3 servers"


def test_error_with_detail():
    assert tel.format_status(tel.PHASE_ERROR, detail="boom") == "Error: boom"


def test_error_without_detail():
    assert tel.format_status(tel.PHASE_ERROR) == "Error"


def test_all_phase_strings_are_ascii():
    """Kit 107 font atlas has no CJK glyphs — every label must be pure ASCII."""
    samples = [
        tel.format_status(tel.PHASE_NO_SCENE),
        tel.format_status(tel.PHASE_LOADING),
        tel.format_status(tel.PHASE_SCENE_LOADED),
        tel.format_status(tel.PHASE_NOT_PLAYING),
        tel.format_status(tel.PHASE_READY),
        tel.format_status(tel.PHASE_TRANSMITTING, progress=0.5, target_server=1),
        tel.format_status(tel.PHASE_DELIVERED, lit_servers=2, total_servers=3),
        tel.format_status(tel.PHASE_ERROR, detail="x"),
    ]
    for s in samples:
        assert s.isascii(), f"non-ASCII in label: {s!r}"
