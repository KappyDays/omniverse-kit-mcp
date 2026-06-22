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

from omniverse_kit_mcp.config import AppConfig, MCPServerConfig  # noqa: E402
from omniverse_kit_mcp.mcp.server import create_mcp_server  # noqa: E402
from omniverse_kit_mcp.tools.tool_profiles import (  # noqa: E402
    CATALOG_GROUPS,
    PROFILE_FULL,
    tool_catalog_group,
)


OUTPUT = PROJECT_ROOT / "docs" / "tool-catalog.md"


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


def _full_catalog_config() -> AppConfig:
    """Build config for the generated canonical full-mode catalog."""
    return AppConfig(mcp_server=MCPServerConfig(tool_profile=PROFILE_FULL))


def main() -> int:
    config = _full_catalog_config()
    mcp = create_mcp_server(config)
    tools = mcp._tool_manager._tools

    grouped: dict[str, list[tuple[str, object]]] = {}
    for name, tool in sorted(tools.items()):
        grouped.setdefault(tool_catalog_group(name), []).append((name, tool))

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
    for title in CATALOG_GROUPS:
        bucket = grouped.get(title, [])
        if not bucket:
            continue
        anchor = re.sub(r"[^a-z0-9\- ]", "", title.lower()).replace(" ", "-")
        lines.append(f"- [{title}](#{anchor}) — {len(bucket)} tools")
    if grouped.get("Unclassified"):
        lines.append(f"- Unclassified ({len(grouped['Unclassified'])})")
    lines.append("")

    for title in CATALOG_GROUPS:
        bucket = grouped.get(title, [])
        if not bucket:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for name, tool in bucket:
            lines.append(_render_tool(name, tool))
    if grouped.get("Unclassified"):
        lines.append("## Unclassified")
        lines.append("")
        for name, tool in grouped["Unclassified"]:
            lines.append(_render_tool(name, tool))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} — {total} tools across {sum(1 for v in grouped.values() if v)} groups")
    return 0


if __name__ == "__main__":
    sys.exit(main())
