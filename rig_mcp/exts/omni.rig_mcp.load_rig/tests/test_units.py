"""Plain-CPython unit tests for omni.rig_mcp.load_rig (no Kit runtime).

Run: .venv/Scripts/python.exe rig_mcp/exts/omni.rig_mcp.load_rig/tests/test_units.py
"""
from __future__ import annotations

import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))

from omni.rig_mcp.load_rig import config, kinematics, measure  # noqa: E402


def test_lift_schedule_monotonic_and_reaches_targets():
    sched = kinematics.lift_schedule()
    times = [t for (t, _l, _ti) in sched]
    assert times == sorted(times)
    lift_final, tilt_final = kinematics.final_targets()
    assert lift_final == config.LIFT_HEIGHT
    assert tilt_final == config.TILT_ANGLE


def test_lift_target_within_limits():
    assert config.LIFT_LOWER <= config.LIFT_HEIGHT <= config.LIFT_UPPER


def test_measure_summary_empty():
    s = measure.summarize([])
    assert s["samples"] == 0 and s["max_force"] == 0.0


def test_measure_summary_series():
    series = [(0.0, 10.0, 1.0), (1.0, 25.0, -3.0), (2.0, 18.0, 2.0)]
    s = measure.summarize(series)
    assert s["samples"] == 3
    assert s["max_force"] == 25.0
    assert s["final_force"] == 18.0
    assert s["max_effort"] == -3.0  # largest by abs


def test_masses_positive():
    for m in (config.CARRIAGE_MASS, config.FORK_MASS, config.PALLET_MASS, config.BOX_MASS):
        assert m > 0.0


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
