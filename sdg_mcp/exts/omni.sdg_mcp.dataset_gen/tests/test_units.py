"""Plain-CPython unit tests for omni.sdg_mcp.dataset_gen (no Kit runtime).

Run: .venv/Scripts/python.exe sdg_mcp/exts/omni.sdg_mcp.dataset_gen/tests/test_units.py
"""
from __future__ import annotations

import math
import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))

from omni.sdg_mcp.dataset_gen import config, labels, replicator_spec, sensor_rig  # noqa: E402


def test_classes():
    assert labels.classes() == ["bin", "forklift", "pallet"]


def test_prop_pairs():
    pairs = labels.prop_label_pairs()
    assert len(pairs) == 3
    for _name, url, cls, tr in pairs:
        assert url.startswith("https://") and url.endswith(".usd")
        assert isinstance(cls, str) and cls
        assert len(tr) == 3


def test_lookat_orthonormal_and_translation():
    m = sensor_rig.compute_lookat_matrix((6.0, 0.0, 3.0), (0.0, 0.0, 0.5))
    x, y, z = m[0:3], m[4:7], m[8:11]

    def dot(a, b):
        return sum(p * q for p, q in zip(a, b))

    for axis in (x, y, z):
        assert abs(dot(axis, axis) - 1.0) < 1e-9
    assert abs(dot(x, y)) < 1e-9 and abs(dot(x, z)) < 1e-9 and abs(dot(y, z)) < 1e-9
    assert m[12:15] == (6.0, 0.0, 3.0)  # translation row == eye


def test_ring_eyes_on_circle():
    eyes = sensor_rig.ring_camera_eyes(3, 6.0, 3.0)
    assert len(eyes) == 3
    for e in eyes:
        assert abs(math.hypot(e[0], e[1]) - 6.0) < 1e-9
        assert e[2] == 3.0


def test_spec():
    spec = replicator_spec.build_spec(["/World/Cameras/Cam_00"])
    assert spec.frame_count == config.FRAME_COUNT
    assert "semantic_segmentation" in spec.annotators
    assert spec.camera_paths == ("/World/Cameras/Cam_00",)


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
