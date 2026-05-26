"""Headless build + export of the SDG scene (usd-core; no Kit runtime).

Run: .venv/Scripts/python.exe sdg_mcp/exts/omni.sdg_mcp.dataset_gen/tools/export_scene.py

Verifies every USD authoring call + idempotency + semantic labels + camera prims,
then exports sdg_mcp/scenes/sdg_scene.usd.
"""
from __future__ import annotations

import pathlib
import sys

_EXT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_EXT_ROOT))
sys.dont_write_bytecode = True

from pxr import Usd, UsdGeom  # noqa: E402

from omni.sdg_mcp.dataset_gen import config, scene_builder  # noqa: E402


def _prim_paths(stage) -> set[str]:
    return {p.GetPath().pathString for p in stage.Traverse()}


def main() -> int:
    stage = Usd.Stage.CreateInMemory()
    info = scene_builder.build(stage)

    # Idempotency: a second build yields the identical prim set.
    before = _prim_paths(stage)
    scene_builder.build(stage)
    after = _prim_paths(stage)
    assert before == after, f"not idempotent; diff={before ^ after}"

    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
    assert stage.GetPrimAtPath(config.ENV_PRIM).GetReferences()

    props, cams = info["props"], info["cameras"]
    assert len(props) == 3, props
    assert len(cams) == config.CAMERA_COUNT, cams

    label_attr = f"semantics:labels:{config.SEMANTIC_LABEL_TYPE}"
    for pp in props:
        prim = stage.GetPrimAtPath(pp)
        attr = prim.GetAttribute(label_attr)
        assert attr and attr.Get(), f"missing semantic label on {pp}"
        model = stage.GetPrimAtPath(pp + "/Model")
        assert model and model.GetReferences(), f"missing /Model reference under {pp}"

    for cp in cams:
        assert stage.GetPrimAtPath(cp).GetTypeName() == "Camera", cp

    out = _EXT_ROOT.parents[1] / "scenes" / "sdg_scene.usd"
    out.parent.mkdir(parents=True, exist_ok=True)
    stage.GetRootLayer().Export(str(out))
    print(f"OK: env + {len(props)} labeled props + {len(cams)} cams, idempotent -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
