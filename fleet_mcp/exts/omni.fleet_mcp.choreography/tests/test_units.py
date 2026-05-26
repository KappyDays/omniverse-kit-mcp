"""Plain-CPython unit tests for omni.fleet_mcp.choreography (no Kit runtime).

Run: .venv/Scripts/python.exe fleet_mcp/exts/omni.fleet_mcp.choreography/tests/test_units.py
"""
from __future__ import annotations

import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))

from omni.fleet_mcp.choreography import config, graph_spec, path_planner  # noqa: E402


def test_formations_have_three_robots():
    for name, offs in config.FORMATIONS.items():
        assert len(offs) == len(config.ROBOT_NAMES), name


def test_leader_schedule_monotonic_time():
    sched = path_planner.leader_schedule()
    assert len(sched) == len(config.LEADER_WAYPOINTS)
    times = [t for (_x, _y, t) in sched]
    assert times == sorted(times)
    assert times[0] == 0.0


def test_start_poses_match_offsets():
    poses = path_planner.start_poses("triangle")
    x0, y0 = config.LEADER_WAYPOINTS[0]
    for (px, py), (dx, dy) in zip(poses, config.FORMATIONS["triangle"]):
        assert abs(px - (x0 + dx)) < 1e-9 and abs(py - (y0 + dy)) < 1e-9


def test_robot_waypoints_shape_and_offset():
    wps = path_planner.robot_waypoints("line")
    assert len(wps) == len(config.ROBOT_NAMES)
    for robot in wps:
        assert len(robot) == len(config.LEADER_WAYPOINTS)
    # robot 1 offset (0,-1.5) applied to every leader waypoint
    leader = path_planner.leader_schedule()
    for (lx, ly, lt), (rx, ry, rt) in zip(leader, wps[1]):
        assert abs(rx - lx) < 1e-9 and abs(ry - (ly - 1.5)) < 1e-9 and rt == lt


def test_graph_spec():
    spec = graph_spec.build_spec(["/World/Fleet/Carter_0"])
    assert spec.graph_path == config.GRAPH_PATH
    assert spec.wheel_radius == config.WHEEL_RADIUS
    assert spec.tick_node_type == "omni.graph.action.OnPlaybackTick"


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
