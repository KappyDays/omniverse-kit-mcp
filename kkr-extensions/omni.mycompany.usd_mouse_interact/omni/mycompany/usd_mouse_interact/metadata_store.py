# metadata_store.py
"""Whitelist + descriptions persistence and lookup.

Stored under stage.GetRootLayer().customLayerData["usdMouseInteract"]
with two keys:
    - allowed_prims: VtArray[str]  (list of prim paths)
    - descriptions: dict[str, str] (prim path → user-supplied text)

Pure functions where possible; USD-touching helpers segregated for clarity.
Kit / omni.* not imported — load/save take a Usd.Stage directly so this is
testable with plain pytest.
"""

from __future__ import annotations

from typing import Iterable

from pxr import Sdf, Usd, Vt

ROOT_KEY = "usdMouseInteract"
ALLOWED_KEY = "allowed_prims"
DESCRIPTIONS_KEY = "descriptions"


# --- pure logic ------------------------------------------------------------


def is_whitelisted(hit_path: str, allowed: set[str]) -> bool:
    """Return True iff hit_path is in allowed or is a descendant of any path in allowed."""
    return any(
        hit_path == p or hit_path.startswith(p + "/")
        for p in allowed
    )


def _longest_ancestor(hit_path: str, paths: Iterable[str]) -> str | None:
    """Return the longest path in `paths` that is hit_path itself or an ancestor of it."""
    candidates = [p for p in paths if hit_path == p or hit_path.startswith(p + "/")]
    if not candidates:
        return None
    return max(candidates, key=len)


def lookup_description(
    hit_path: str,
    descriptions: dict[str, str],
    stage: Usd.Stage,
) -> tuple[str, str]:
    """Return (title, description) for the given hit_path.

    Priority:
      1. exact / longest-ancestor match in user-supplied descriptions.
      2. fallback to prim metadata: f"{typeName} — under {parent_path}".
      3. invalid prim → "(unknown prim)".
    """
    title = hit_path.rsplit("/", 1)[-1] or hit_path

    matched = _longest_ancestor(hit_path, descriptions.keys())
    if matched is not None:
        return title, descriptions[matched]

    prim = stage.GetPrimAtPath(hit_path)
    if not prim or not prim.IsValid():
        return title, "(unknown prim)"
    type_name = prim.GetTypeName() or "(no type)"
    parent = prim.GetParent()
    parent_path = parent.GetPath().pathString if parent else "/"
    return title, f"{type_name} — under {parent_path}"


# --- USD-touching helpers --------------------------------------------------


def load_from_stage(stage: Usd.Stage) -> tuple[set[str], dict[str, str]]:
    """Read whitelist + descriptions from root layer customLayerData."""
    if stage is None:
        return set(), {}
    layer = stage.GetRootLayer()
    data = dict(layer.customLayerData or {})
    bucket = data.get(ROOT_KEY) or {}
    allowed_raw = bucket.get(ALLOWED_KEY) or []
    descs_raw = bucket.get(DESCRIPTIONS_KEY) or {}

    allowed = {str(p) for p in allowed_raw}
    descs = {str(k): str(v) for k, v in dict(descs_raw).items()}
    return allowed, descs


def save_to_stage(
    stage: Usd.Stage,
    allowed: Iterable[str],
    descriptions: dict[str, str],
) -> None:
    """Write whitelist + descriptions back into root layer customLayerData."""
    if stage is None:
        return
    layer = stage.GetRootLayer()
    data = dict(layer.customLayerData or {})

    bucket = {
        ALLOWED_KEY: Vt.StringArray(sorted(set(allowed))),
        DESCRIPTIONS_KEY: dict(descriptions),
    }
    data[ROOT_KEY] = bucket
    layer.customLayerData = data
