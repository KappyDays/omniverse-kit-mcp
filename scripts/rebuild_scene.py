"""Rebuild a scene USD without hitting the live-Kit file-lock / layer-registry trap.

Usage:
    .venv/Scripts/python.exe scripts/rebuild_scene.py <builder.py> --out <out.usd> [--reopen]

The <builder.py> must expose either:
  - ``build(layer) -> None`` that authors into the given anonymous ``Sdf.Layer``
    (preferred — wrapper Exports it), OR
  - ``build_to(out_path: str) -> None`` that writes the final .usd itself.

This wrapper sets ``sys.dont_write_bytecode`` and prefers the anonymous-layer
path to bypass the Sdf registry + OS file lock.

See docs/runbooks/scene-reexport-lock.md for the full rationale.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def _load_module(builder_path: Path):
    spec = importlib.util.spec_from_file_location("_scene_builder", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import builder: {builder_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    sys.dont_write_bytecode = True  # avoid stale __pycache__ bytecode

    ap = argparse.ArgumentParser()
    ap.add_argument("builder", help="path to scene builder .py")
    ap.add_argument("--out", help="output .usd path (required for build(layer) builders)")
    ap.add_argument("--reopen", action="store_true", help="print stage_open hint for the result")
    args = ap.parse_args()

    builder_path = Path(args.builder).resolve()
    if not builder_path.exists():
        print(f"[rebuild_scene] builder not found: {builder_path}", file=sys.stderr)
        return 2

    mod = _load_module(builder_path)

    if hasattr(mod, "build"):
        if not args.out:
            print("[rebuild_scene] --out is required for build(layer) builders", file=sys.stderr)
            return 2
        from pxr import Sdf  # lazy — only the anonymous-layer path needs pxr
        layer = Sdf.Layer.CreateAnonymous()
        mod.build(layer)
        layer.Export(args.out)
        out = args.out
    elif hasattr(mod, "build_to"):
        mod.build_to(args.out)
        out = args.out
    else:
        print("[rebuild_scene] builder must expose build(layer) or build_to(out)", file=sys.stderr)
        return 2

    print(f"[rebuild_scene] wrote {out}")
    if args.reopen and out:
        print(f"[rebuild_scene] reopen with: stage_open(url='{out}')")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
