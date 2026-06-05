# metadata_store.py
"""Whitelist + descriptions persistence and lookup.

Stored under stage.GetRootLayer().customLayerData["usdMouseInteractDemo"]
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

from .config_model import (
    UsdMouseInteractConfig,
    camera_set_size_for_key,
    config_from_dict,
    config_to_dict,
)

ROOT_KEY = "usdMouseInteractDemo"
ALLOWED_KEY = "allowed_prims"
DESCRIPTIONS_KEY = "descriptions"
CONFIG_VERSION_KEY = "config_version"
RUNTIME_KEY = "runtime"
TOP_VIEW_KEY = "top_view"
BUTTON_MODE_KEY = "button_mode"


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


def load_config_from_stage(stage: Usd.Stage) -> UsdMouseInteractConfig:
    """Read the runtime config from root layer customLayerData."""
    if stage is None:
        return UsdMouseInteractConfig.default()
    layer = stage.GetRootLayer()
    data = dict(layer.customLayerData or {})
    bucket = dict(data.get(ROOT_KEY) or {})
    raw = {
        RUNTIME_KEY: bucket.get(RUNTIME_KEY),
        TOP_VIEW_KEY: bucket.get(TOP_VIEW_KEY),
        BUTTON_MODE_KEY: bucket.get(BUTTON_MODE_KEY),
    }
    return config_from_dict(raw)


def save_config_to_stage(stage: Usd.Stage, config: UsdMouseInteractConfig) -> None:
    """Write runtime config while preserving whitelist + descriptions."""
    if stage is None:
        return
    layer = stage.GetRootLayer()
    data = dict(layer.customLayerData or {})
    bucket = dict(data.get(ROOT_KEY) or {})
    config_data = config_to_dict(config)

    bucket[CONFIG_VERSION_KEY] = 1
    bucket[RUNTIME_KEY] = config_data[RUNTIME_KEY]
    bucket[TOP_VIEW_KEY] = config_data[TOP_VIEW_KEY]
    bucket[BUTTON_MODE_KEY] = _to_usd_button_mode_dict(config_data[BUTTON_MODE_KEY])
    data[ROOT_KEY] = bucket
    layer.customLayerData = data


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

    bucket = dict(data.get(ROOT_KEY) or {})
    bucket[ALLOWED_KEY] = Vt.StringArray(sorted(set(allowed)))
    bucket[DESCRIPTIONS_KEY] = dict(descriptions)
    data[ROOT_KEY] = bucket
    layer.customLayerData = data


def _to_usd_button_mode_dict(button_mode: dict) -> dict:
    usd_button_mode = dict(button_mode)
    camera_sets = dict(usd_button_mode.get("camera_sets") or {})
    usd_button_mode["camera_sets"] = {
        key: Vt.StringArray(_normalize_camera_set(key, paths))
        for key, paths in camera_sets.items()
    }
    return usd_button_mode


def _normalize_camera_set(key: str, paths: object) -> list[str]:
    try:
        values = list(paths) if paths is not None else []
    except TypeError:
        values = []
    camera_count = camera_set_size_for_key(key)
    normalized = [str(value) for value in values[:camera_count]]
    while len(normalized) < camera_count:
        normalized.append("")
    return normalized
