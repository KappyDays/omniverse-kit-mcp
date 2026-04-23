"""Compare pre/post pointer_map.json — flag broken-pointer regression.

Context
-------
Operating Invariant §2.4.2: documentation restructuring must not break any
cross-reference. This compares the JSON emitted by
``scripts/extract_pointer_map.py`` before and after the restructure.

A file that used to reach an existing target but now reaches a missing
one is a regression. A file that was already broken in pre and is still
broken post is noted but does not fail the comparison (historical drift,
not caused by this restructure).

File *renames* (e.g. ``modules/CLAUDE.md §Integration Facts`` →
``modules/integration-facts.md``) are expected: any ``source → new target``
edge is treated as legal provided the new target exists.

Exit code 0 iff no new broken edge was introduced (plan §12.2 AC #13).

Usage
-----

.. code-block:: bash

    .venv/Scripts/python.exe scripts/compare_pointer_maps.py \\
        docs/artifacts/restructure-baseline/pre/pointer_map.json \\
        docs/artifacts/restructure-baseline/post/pointer_map.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _edge_key(edge: dict) -> tuple[str, str, str]:
    return (edge["source"], edge["target_resolved"], edge["text"])


def _diff(pre: dict, post: dict) -> dict:
    pre_edges = {_edge_key(e): e for e in pre.get("edges", [])}
    post_edges = {_edge_key(e): e for e in post.get("edges", [])}

    newly_broken: list[dict] = []  # was OK in pre, broken in post
    still_broken: list[dict] = []  # broken in both (historical, not regression)
    newly_added_broken: list[dict] = []  # did not exist in pre, broken in post

    for key, post_e in post_edges.items():
        if post_e["exists"]:
            continue
        pre_e = pre_edges.get(key)
        if pre_e is None:
            newly_added_broken.append(post_e)
        elif pre_e["exists"] is False:
            still_broken.append(post_e)
        else:
            newly_broken.append(post_e)

    disappeared_edges = [e for key, e in pre_edges.items() if key not in post_edges]

    return {
        "newly_broken": newly_broken,
        "newly_added_broken": newly_added_broken,
        "still_broken": still_broken,
        "disappeared": disappeared_edges,
        "pre_edge_count": len(pre_edges),
        "post_edge_count": len(post_edges),
    }


def _render(diff: dict) -> bool:
    """Print diff; return True iff a regression was detected."""
    regressed = False
    print(f"edges: pre={diff['pre_edge_count']} post={diff['post_edge_count']}")

    if diff["newly_broken"]:
        regressed = True
        print(f"\n❌ NEWLY BROKEN ({len(diff['newly_broken'])}) — links that were OK in pre:")
        for e in diff["newly_broken"]:
            print(f"  - {e['source']} → [{e['text']}]({e['target_raw']}) ⇒ {e['target_resolved']}")

    if diff["newly_added_broken"]:
        regressed = True
        print(
            f"\n❌ NEW BROKEN LINKS ({len(diff['newly_added_broken'])}) "
            "— added in post, point at missing targets:"
        )
        for e in diff["newly_added_broken"]:
            print(f"  - {e['source']} → [{e['text']}]({e['target_raw']}) ⇒ {e['target_resolved']}")

    if diff["still_broken"]:
        print(
            f"\nℹ️  still broken ({len(diff['still_broken'])}) — "
            "pre-existing drift, not caused by this restructure:"
        )
        for e in diff["still_broken"][:10]:
            print(f"  - {e['source']} → {e['target_resolved']}")

    if diff["disappeared"]:
        print(
            f"\nℹ️  disappeared ({len(diff['disappeared'])}) — "
            "edges removed in post (intentional deletions OK):"
        )
        for e in diff["disappeared"][:10]:
            print(f"  - {e['source']} → {e['target_resolved']}")

    if not regressed:
        print("\nOK — no new broken pointers introduced.")
    return regressed


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("pre", type=Path, help="pre pointer_map.json")
    parser.add_argument("post", type=Path, help="post pointer_map.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pre = _load(args.pre)
    post = _load(args.post)
    diff = _diff(pre, post)
    return 1 if _render(diff) else 0


if __name__ == "__main__":
    sys.exit(main())
