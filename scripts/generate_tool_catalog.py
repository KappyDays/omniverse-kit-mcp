"""Generate docs/tool-catalog.md from the live FastMCP server.

The catalog is the single consumable artifact for any outside session that
needs to know "which MCP tools are available, what do they take, what do
they do, and which REST endpoint sit behind them" without reading
module_tools.py / rest_router.py / clients directly.

Re-run on every tool change:

    .venv/Scripts/python.exe scripts/generate_tool_catalog.py

`tests/unit/test_tool_catalog_sync.py` then guards against drift between
the catalog file and the frozenset SoT in test_tools_registration.
"""

from __future__ import annotations

import inspect
import re
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniverse_kit_mcp.config import AppConfig  # noqa: E402
from omniverse_kit_mcp.mcp.server import create_mcp_server  # noqa: E402


OUTPUT = PROJECT_ROOT / "docs" / "tool-catalog.md"


# Prefix → (group title, order key)
_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("Process — Isaac Sim kit.exe lifecycle", ("isaac_sim_",)),
    ("Stage — READ / ASSERT / file & selection", (
        "stage_capture_snapshot", "stage_diff_snapshots",
        "stage_assert_prim_exists", "stage_assert_property",
        "stage_get_selection", "stage_set_selection",
    )),
    ("Stage — WRITE (mutations routed to SimulationModule)", (
        "stage_load_usd", "stage_set_property",
        "stage_create_prim", "stage_delete_prim",
        "stage_save", "stage_open", "stage_new",
    )),
    ("Simulation — timeline", (
        "simulation_play", "simulation_pause", "simulation_stop",
        "simulation_get_status",
    )),
    ("Viewport — 3D renderer capture + camera", ("viewport_",)),
    ("Window — Kit GUI (app window / menus / omni.ui windows)", ("window_",)),
    ("Extension — lifecycle / UI automation / carb log capture", ("extension_",)),
    ("Lakehouse — query-only", ("lakehouse_",)),
    ("Robot — articulation + navigation (ASYNC Job)", ("robot_",)),
    ("Job — async job polling / cancel", ("job_",)),
    ("Asset — catalog browsing (GUI Asset Browser equivalent)", ("asset_",)),
    ("Character — Biped_Setup + AnimationGraph + NavMesh (ASYNC Job)", ("character_",)),
    ("Navigation — NavMesh bake / path query / exclude volume", ("navigation_",)),
    ("Scenario — YAML Arrange / Act / Assert / Cleanup runner", ("scenario_",)),
]


def _match_group(name: str) -> int:
    """Return the group index a tool name belongs to. Prefers exact prefix,
    falls back to explicit-name membership for the hybrid `stage_*` split."""
    for i, (_title, keys) in enumerate(_GROUPS):
        # Exact-name match wins over prefix match
        for key in keys:
            if key == name:
                return i
    for i, (_title, keys) in enumerate(_GROUPS):
        for key in keys:
            if key.endswith("_") and name.startswith(key):
                return i
    return len(_GROUPS)  # unknown → last bucket


def _render_tool(name: str, tool) -> str:
    description = (tool.description or "").strip()
    params = tool.parameters or {}
    props = params.get("properties") or {}
    required = set(params.get("required") or [])

    # Function signature — from the wrapped fn
    try:
        sig = inspect.signature(tool.fn)
        sig_str = f"{name}{sig}"
    except (ValueError, TypeError):
        sig_str = f"{name}(...)"

    buf: list[str] = []
    buf.append(f"### `{name}`")
    buf.append("")
    buf.append(f"```python\n{sig_str}\n```")
    buf.append("")
    if description:
        # Indent-safe line wrap so wide paragraphs stay readable in diff view
        wrapped = textwrap.fill(description, width=95)
        buf.append(wrapped)
        buf.append("")

    if props:
        buf.append("**Parameters**")
        buf.append("")
        buf.append("| name | type | default | required |")
        buf.append("|------|------|---------|----------|")
        for pname, spec in props.items():
            type_str = _type_str(spec)
            default = spec.get("default", "—")
            if default in (None, "None"):
                default = "`None`"
            elif isinstance(default, str):
                default = f"`{default!r}`"
            else:
                default = f"`{default}`"
            req = "✓" if pname in required else ""
            buf.append(f"| `{pname}` | `{type_str}` | {default} | {req} |")
        buf.append("")
    return "\n".join(buf)


def _type_str(spec: dict) -> str:
    """Compact type rendering that keeps JSON-schema tagged unions readable."""
    if "anyOf" in spec:
        parts = [_type_str(s) for s in spec["anyOf"]]
        return " \\| ".join(parts)
    if "type" in spec:
        t = spec["type"]
        if t == "array":
            items = spec.get("items") or {}
            return f"list[{_type_str(items)}]"
        if t == "null":
            return "None"
        return str(t)
    if "$ref" in spec:
        return spec["$ref"].rsplit("/", 1)[-1]
    return "Any"


def _extract_header(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    config = AppConfig()
    mcp = create_mcp_server(config)
    tools = mcp._tool_manager._tools

    grouped: dict[int, list[tuple[str, object]]] = {}
    for name, tool in sorted(tools.items()):
        grouped.setdefault(_match_group(name), []).append((name, tool))

    total = sum(len(v) for v in grouped.values())
    lines: list[str] = []
    lines.append("# Isaac-sim MCP — Tool Catalog")
    lines.append("")
    lines.append(
        "Auto-generated from the live FastMCP server. Regenerate with "
        "`.venv/Scripts/python.exe scripts/generate_tool_catalog.py` after "
        "any tool addition / removal / signature change. "
        "`tests/unit/test_tool_catalog_sync.py` fails if this file drifts "
        "out of sync with the `EXPECTED_MODULE_TOOLS` / "
        "`EXPECTED_SCENARIO_TOOLS` frozenset SoT."
    )
    lines.append("")
    lines.append(f"**Tool count**: {total}")
    lines.append("")
    lines.append("## Table of contents")
    lines.append("")
    for i, (title, _) in enumerate(_GROUPS):
        bucket = grouped.get(i, [])
        if not bucket:
            continue
        anchor = re.sub(r"[^a-z0-9\- ]", "", title.lower()).replace(" ", "-")
        lines.append(f"- [{title}](#{anchor}) — {len(bucket)} tools")
    if grouped.get(len(_GROUPS)):
        lines.append(f"- Unclassified ({len(grouped[len(_GROUPS)])})")
    lines.append("")

    for i, (title, _keys) in enumerate(_GROUPS):
        bucket = grouped.get(i, [])
        if not bucket:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for name, tool in bucket:
            lines.append(_render_tool(name, tool))
    if grouped.get(len(_GROUPS)):
        lines.append("## Unclassified")
        lines.append("")
        for name, tool in grouped[len(_GROUPS)]:
            lines.append(_render_tool(name, tool))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} — {total} tools across {sum(1 for v in grouped.values() if v)} groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
