"""Unit tests for transmission.WaveModel (pure progress wave)."""

import pytest

from omni.office_mcp.network_demo.transmission import (
    STATUS_DELIVERED,
    STATUS_IDLE,
    STATUS_TRANSMITTING,
    WaveModel,
)

# Demo topology: 4 cables (orders 0..3), 3 server LEDs fed by cables 1..3.
CABLES = 4
SERVERS = (1, 2, 3)


def _model(duration=1.0):
    return WaveModel(num_cables=CABLES, server_orders=SERVERS, duration=duration)


def test_initial_state_idle():
    m = _model()
    assert m.status == STATUS_IDLE
    assert m.progress == 0.0
    assert m.lit_count() == 0


def test_start_enters_transmitting():
    m = _model()
    m.start()
    assert m.status == STATUS_TRANSMITTING
    assert m.progress == 0.0
    assert m.current_target() == 1


def test_advance_reaches_delivered_and_lights_all():
    m = _model(duration=1.0)
    m.start()
    for _ in range(10):
        m.advance(0.1)
    assert m.status == STATUS_DELIVERED
    assert m.progress == 1.0
    assert m.lit_count() == len(SERVERS)
    assert m.current_target() == len(SERVERS)


def test_cable_fill_is_sequential_progress_wave():
    m = _model()
    m.start()
    m.progress = 0.0
    assert m.cable_fill(0) == 0.0
    # front = 2.4 -> cables 0,1 full, cable 2 at 0.4, cable 3 empty
    m.progress = 0.6
    assert m.cable_fill(0) == pytest.approx(1.0)
    assert m.cable_fill(1) == pytest.approx(1.0)
    assert m.cable_fill(2) == pytest.approx(0.4)
    assert m.cable_fill(3) == pytest.approx(0.0)


def test_server_lights_in_order():
    m = _model()
    m.start()
    # progress 0.4 -> front 1.6: cable1 partial, no server lit yet
    m.progress = 0.4
    assert m.lit_count() == 0
    assert m.current_target() == 1
    # progress 0.5 -> front 2.0: cable1 full -> server 1 lit
    m.progress = 0.5
    assert m.server_lit(1) is True
    assert m.server_lit(2) is False
    assert m.lit_count() == 1
    assert m.current_target() == 2
    # progress 0.75 -> front 3.0: cable2 full -> servers 1,2 lit
    m.progress = 0.75
    assert m.lit_count() == 2
    assert m.current_target() == 3


def test_lit_count_monotonic_over_run():
    m = _model(duration=1.0)
    m.start()
    seq = []
    for _ in range(12):
        seq.append(m.lit_count())
        m.advance(0.1)
    assert all(b >= a for a, b in zip(seq, seq[1:]))
    assert seq[0] == 0
    assert m.lit_count() == len(SERVERS)


def test_reset_returns_to_idle():
    m = _model()
    m.start()
    m.advance(0.5)
    m.reset()
    assert m.status == STATUS_IDLE
    assert m.progress == 0.0
    assert m.lit_count() == 0


def test_advance_only_runs_while_transmitting():
    m = _model()
    # not started: advance is a no-op
    m.advance(0.5)
    assert m.progress == 0.0
    assert m.status == STATUS_IDLE


def test_zero_cables_delivers_immediately():
    m = WaveModel(num_cables=0, server_orders=(), duration=1.0)
    m.start()
    assert m.status == STATUS_DELIVERED
    assert m.current_target() == 0


def test_nonpositive_duration_falls_back_to_default():
    m = WaveModel(num_cables=CABLES, server_orders=SERVERS, duration=0.0)
    assert m.duration > 0.0
