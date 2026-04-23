"""Extract the project documentation link graph as JSON.

Walks every ``CLAUDE.md`` plus ``docs/**/*.md`` and collects every relative
``.md`` pointer. The output is a stable, diff-able snapshot used to verify
Operating Invariant §2.4.2 (cross-reference integrity) across the CLAUDE.md
Pull-First restructure.

Output schema
-------------

.. code-block:: json

    {
      "generated_at_epoch": 1700000000,
      "project_root": "<absolute path>",
      "nodes": ["CLAUDE.md", "docs/CLAUDE.md", …],
      "edges": [
        {
          "source": "CLAUDE.md",                # project-relative, POSIX
          "text": "<link text>",
          "target_raw": "<as written in the .md>",
          "target_resolved": "<normalised, project-relative>",
          "exists": true
        }, …
      ]
    }

Usage
-----

.. code-block:: bash

    .venv/Scripts/python.exe scripts/extract_pointer_map.py \\
        --out docs/artifacts/restructure-baseline/pre/pointer_map.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_PROJECT_DEFAULT = Path(__file__).resolve().parent.parent

# Same relative-link matcher used by tests/unit/test_doc_integrity.py — keep
# them in sync if one is ever tightened/loosened.
_LINK_RE = re.compile(
    r"\[([^\]]+)\]\((?!https?://|mailto:|#)([^)\s]+?\.md)(#[^)]*)?\)"
)


def _collect_sources(project: Path) -> list[Path]:
    """Every CLAUDE.md anywhere, plus every .md under ``docs/``."""
    sources: set[Path] = set()
    for md in project.glob("**/CLAUDE.md"):
        sources.add(md)
    docs = project / "docs"
    if docs.exists():
        for md in docs.rglob("*.md"):
            sources.add(md)
    return sorted(sources)


def _project_rel(project_resolved: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_resolved).as_posix()
    except ValueError:
        # Points outside the project — keep the absolute form so drift
        # is still visible.
        return str(path.resolve()).replace("\\", "/")


def extract(project: Path) -> dict:
    project_resolved = project.resolve()
    sources = _collect_sources(project)
    nodes = sorted({_project_rel(project_resolved, p) for p in sources})
    edges: list[dict] = []

    for md in sources:
        parent = md.parent
        source_rel = _project_rel(project_resolved, md)
        for match in _LINK_RE.finditer(md.read_text(encoding="utf-8")):
            text = match.group(1).strip()
            raw = match.group(2).strip()
            if ":" in raw or raw.startswith("/"):
                # Skip absolute paths (C:/…, /usr/…) — not project-managed.
                continue
            target_abs = (parent / raw).resolve()
            edges.append(
                {
                    "source": source_rel,
                    "text": text,
                    "target_raw": raw,
                    "target_resolved": _project_rel(project_resolved, target_abs),
                    "exists": target_abs.exists(),
                }
            )

    edges.sort(
        key=lambda e: (e["source"], e["target_resolved"], e["text"], e["target_raw"])
    )
    return {
        "generated_at_epoch": int(time.time()),
        "project_root": str(project_resolved),
        "nodes": nodes,
        "edges": edges,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract the project documentation link graph as JSON."
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=_PROJECT_DEFAULT,
        help="Project root (default: parent of this script).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output JSON path (parents are created if missing).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    graph = extract(args.project)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(graph, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    broken = sum(1 for e in graph["edges"] if not e["exists"])
    print(
        f"pointer map: nodes={len(graph['nodes'])} "
        f"edges={len(graph['edges'])} broken={broken} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
