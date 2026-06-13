"""Asset module — live catalog listing (Phase B+) + offline catalog search.

``list`` browses the live S3 catalog through the Extension (Isaac must be up).
``search`` is fully **offline**: it reads the curated markdown catalog under
``docs/assets/isaac/`` directly in the MCP server process, ranks entries, and
returns concrete USD URLs — usable at planning time without Isaac running.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.asset import AssetCategory, AssetItem, AssetListResult
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta

logger = logging.getLogger(__name__)

# Project-root-relative default catalog dir (…/docs/assets/isaac).
_DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[3] / "docs" / "assets" / "isaac"

# Curated per-category catalog files (stems double as the `category` value).
_CATEGORY_FILES = ("robots", "environments", "people", "props", "simready", "other")

# `$VAR` = `https://…`  prefix declaration (line-anchored, mirrors the format
# contract guarded by tests/unit/test_asset_inventory_integrity.py).
_PREFIX_RE = re.compile(r"^`(\$\w+)`\s*=\s*`(https?://[^`]+)`", re.MULTILINE)
# Root: `$VAR/path/`  section-root declaration.
_ROOT_RE = re.compile(r"^(?:루트|Root):\s*`(\$\w+/[^`]*?)/?`")
# Any backtick-quoted token.
_BACKTICK_RE = re.compile(r"`([^`]+)`")
# Markdown heading.
_HEADING_RE = re.compile(r"^#{1,6}\s")
# Bold-stripped value (e.g. **Simple_Warehouse** → Simple_Warehouse).
_BOLD_RE = re.compile(r"\*+")
# Plausible SimReady prose asset name (lowercase props, ranges/variants allowed).
_SIMREADY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*[a-z0-9_~/,. ]*$")


class AssetModule:
    def __init__(
        self, client: IsaacRestClient, catalog_dir: Path | None = None
    ) -> None:
        self._client = client
        self._catalog_dir = catalog_dir or _DEFAULT_CATALOG_DIR
        self._index: list[dict[str, Any]] | None = None

    async def list(
        self,
        meta: OperationMeta,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> ModuleResult[AssetListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.asset_list(
                category=category,
                subpath=subpath,
                recursive=recursive,
                max_depth=max_depth,
                max_entries=max_entries,
            )
            return ok_result(_parse_list(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="ASSET_LIST_ERROR"
            )

    # ------------------------------------------------------------------
    # Offline catalog search (no REST / no Isaac Sim)
    # ------------------------------------------------------------------

    def _load_index(self) -> list[dict[str, Any]]:
        if self._index is None:
            self._index = _build_index(self._catalog_dir)
        return self._index

    async def search(
        self,
        meta: OperationMeta,
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> ModuleResult[list[dict[str, Any]]]:
        started = int(time.time() * 1000)
        try:
            index = self._load_index()
            cat = (category or "").strip().lower() or None
            tokens = [t for t in (query or "").lower().split() if t]
            full = " ".join(tokens)

            scored: list[tuple[int, dict[str, Any]]] = []
            for e in index:
                if cat and e["category"] != cat:
                    continue
                score = _score(e, tokens, full)
                if tokens and score <= 0:
                    continue
                scored.append((score, e))

            scored.sort(key=lambda s: (-s[0], s[1]["name"].lower()))

            results: list[dict[str, Any]] = []
            seen: set[str] = set()
            for _score_val, e in scored:
                if e["url"] in seen:
                    continue
                seen.add(e["url"])
                results.append(
                    {
                        "name": e["name"],
                        "url": e["url"],
                        "category": e["category"],
                        "source_file": e["source_file"],
                    }
                )
                if len(results) >= limit:
                    break
            return ok_result(results, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ASSET_SEARCH_ERROR",
            )


# ----------------------------------------------------------------------
# Catalog markdown parser (pure functions — unit-testable in isolation)
# ----------------------------------------------------------------------


def _build_index(catalog_dir: Path) -> list[dict[str, Any]]:
    """Parse every per-category catalog markdown into searchable entries."""
    entries: list[dict[str, Any]] = []
    assets_dir = catalog_dir / "assets"
    if not assets_dir.is_dir():
        return entries
    for cat in _CATEGORY_FILES:
        md = assets_dir / f"{cat}.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        entries.extend(_parse_catalog_file(text, category=cat, source_file=md.name))
    return entries


def resolve_catalog_asset_url(
    category: str,
    relative_path: str,
    catalog_dir: Path | None = None,
) -> str:
    """Resolve a catalog-relative asset path through the markdown SoT."""
    normalized_category = category.strip().lower()
    normalized_path = relative_path.strip().replace("\\", "/").strip("/")
    suffix = f"/{normalized_path}"
    for entry in _build_index(catalog_dir or _DEFAULT_CATALOG_DIR):
        if entry["category"] != normalized_category:
            continue
        if str(entry["url"]).replace("\\", "/").endswith(suffix):
            return str(entry["url"])
    raise KeyError(f"Asset catalog entry not found: {category}/{relative_path}")


def _parse_catalog_file(
    text: str, category: str, source_file: str
) -> list[dict[str, Any]]:
    prefix_map = {
        var: url for var, url in _PREFIX_RE.findall(text)
    }

    def resolve_prefix(s: str) -> str:
        for var, url in prefix_map.items():
            if s.startswith(var):
                return url + s[len(var):]
        return s

    entries: list[dict[str, Any]] = []
    file_root: str | None = None
    current_root: str | None = None
    current_group: str | None = None
    prose_header: str = ""

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # Section boundaries reset the rowspan group.
        root_m = _ROOT_RE.match(stripped)
        if root_m:
            current_root = resolve_prefix(root_m.group(1)) + "/"
            if file_root is None:
                file_root = current_root
            current_group = None
            continue
        if _HEADING_RE.match(stripped):
            current_group = None
            # A bold-only heading-ish line is rare; headings carry no assets.
            continue

        # Table rows.
        if stripped.startswith("|"):
            cells = _split_cells(stripped)
            if not cells or _is_separator_row(cells):
                continue
            col0 = _BOLD_RE.sub("", cells[0]).strip()
            # Update group from a plain (non-USD) col0; empty col0 inherits.
            if col0 and ".usd" not in cells[0]:
                current_group = col0
            usd_tokens = _usd_tokens(stripped)
            if not usd_tokens:
                continue
            row_text = " ".join(cells)
            for tok in usd_tokens:
                url = _build_url(
                    tok,
                    category=category,
                    prefix_map=prefix_map,
                    resolve_prefix=resolve_prefix,
                    file_root=file_root,
                    current_root=current_root,
                    group=current_group,
                    cells=cells,
                )
                if not url:
                    continue
                entries.append(
                    _make_entry(
                        name=_basename(tok),
                        url=url,
                        category=category,
                        source_file=source_file,
                        text=f"{row_text} {current_group or ''} {prose_header}",
                    )
                )
            continue

        # Prose (SimReady curated name lists).
        if category == "simready":
            if stripped.startswith("**") and stripped.endswith("**"):
                prose_header = _BOLD_RE.sub("", stripped).strip()
                continue
            for tok in _BACKTICK_RE.findall(stripped):
                name = tok.strip()
                if not _SIMREADY_NAME_RE.match(name):
                    continue
                canonical = _simready_canonical(name)
                if not canonical:
                    continue
                sim = prefix_map.get("$SIM")
                if not sim:
                    continue
                url = f"{sim}/{canonical}/{canonical}.usd"
                entries.append(
                    _make_entry(
                        name=name,
                        url=url,
                        category=category,
                        source_file=source_file,
                        text=f"{name} {prose_header}",
                    )
                )

    return entries


def _make_entry(
    name: str, url: str, category: str, source_file: str, text: str
) -> dict[str, Any]:
    hay = f"{name} {text} {category}".lower()
    return {
        "name": name,
        "url": url,
        "category": category,
        "source_file": source_file,
        "_text": hay,
    }


def _split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c) is not None for c in cells if c)


def _usd_tokens(line: str) -> list[str]:
    """Backtick tokens that reference a .usd/.usda file."""
    out: list[str] = []
    for tok in _BACKTICK_RE.findall(line):
        t = tok.strip()
        if ".usd" not in t and ".usda" not in t:
            continue
        # Skip prose-rule placeholders like `$SIM/{name}/{name}.usd`.
        if "{" in t or "(" in t or t.startswith("$"):
            continue
        out.append(t)
    return out


def _basename(token: str) -> str:
    return token.rstrip("/").split("/")[-1]


def _simready_canonical(name: str) -> str:
    """First concrete asset name from a SimReady shorthand token.

    `box_a01~a11` → `box_a01`; `aluminumpallet_a01/a02` → `aluminumpallet_a01`;
    `pallet_a1/b1/c1` → `pallet_a1`.
    """
    head = re.split(r"[~,/ ]", name, maxsplit=1)[0].strip()
    return head


def _build_url(
    token: str,
    *,
    category: str,
    prefix_map: dict[str, str],
    resolve_prefix,
    file_root: str | None,
    current_root: str | None,
    group: str | None,
    cells: list[str],
) -> str | None:
    if token.startswith("$"):
        return resolve_prefix(token)

    if category == "robots":
        isaac = prefix_map.get("$ISAAC")
        if not isaac:
            return None
        base = f"{isaac}/Robots/"
        vendor = group
        if not vendor:
            return None
        if "/" in token:
            return f"{base}{vendor}/{token}"
        model = _BOLD_RE.sub("", cells[1]).strip() if len(cells) > 1 else ""
        if model:
            return f"{base}{vendor}/{model}/{token}"
        return f"{base}{vendor}/{token}"

    # Path with subfolders → relative to the file-level category root.
    if "/" in token:
        if file_root:
            return f"{file_root}{token}"
        return None

    # Bare filename → nearest section root + (rowspan group folder).
    base = current_root or file_root
    if not base:
        return None
    if group:
        return f"{base}{group}/{token}"
    return f"{base}{token}"


def _score(entry: dict[str, Any], tokens: list[str], full: str) -> int:
    if not tokens:
        return 0
    name = entry["name"].lower()
    stem = re.sub(r"\.usda?$", "", name)
    hay = entry["_text"]
    score = 0
    for tok in tokens:
        if tok == stem:
            score += 100
        elif tok in name:
            score += 10
        if tok in hay:
            score += 3
    if full and full in name:
        score += 50
    return score


def _parse_list(raw: dict) -> AssetListResult:
    categories = tuple(
        AssetCategory(name=c["name"], url=c["url"])
        for c in raw.get("categories", [])
    )
    items = tuple(
        AssetItem(
            name=i["name"],
            url=i["url"],
            is_folder=bool(i.get("is_folder", False)),
            size=i.get("size"),
        )
        for i in raw.get("items", [])
    )
    return AssetListResult(
        assets_root=raw.get("assets_root"),
        category=raw.get("category"),
        subpath=raw.get("subpath", ""),
        base_url=raw.get("base_url"),
        target_url=raw.get("target_url"),
        categories=categories,
        items=items,
        count=int(raw.get("count", len(items))),
    )
