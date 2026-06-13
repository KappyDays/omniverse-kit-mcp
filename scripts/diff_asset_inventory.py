"""Validate USD URLs in docs/assets/isaac/assets/*.md via S3 HEAD requests.

Detects:
  - 404 (file moved or removed at NVIDIA bucket)
  - 5xx (transient — re-run; if persistent, NVIDIA-side issue)
  - 0   (network timeout / DNS failure — local connectivity)

Usage:
    .venv/Scripts/python.exe scripts/diff_asset_inventory.py
    .venv/Scripts/python.exe scripts/diff_asset_inventory.py --verbose
    .venv/Scripts/python.exe scripts/diff_asset_inventory.py --json

Exit 0 if all URLs valid (HTTP 200), exit 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Two catalog scopes — both validated by this script:
#   docs/assets/isaac/assets/  → Isaac Sim 6.0 bundle (strict prefix)
#   docs/assets/composer/      → USD Composer / cross-app sample library
# Both live in the same omniverse-content-production S3 bucket.
ASSETS_DIRS = [
    PROJECT_ROOT / "docs" / "assets" / "isaac" / "assets",
    PROJECT_ROOT / "docs" / "assets" / "composer",
]
# Backwards-compat alias for tests that imported the singular name.
ASSETS_DIR = ASSETS_DIRS[0]

PREFIX_DECL_RE = re.compile(r"^`(\$\w+)`\s*=\s*`(https?://[^`]+)`", re.MULTILINE)
USD_BACKTICK_RE = re.compile(r"`([^`\s]+\.(?:usd|usda))`")
# Section root declaration: Root: `$ISAAC/Path/`
ROOT_DECL_RE = re.compile(r"^Root:\s*`(\$\w+/[^`]+?)/?`", re.MULTILINE)
# robots.md row form: | **Vendor** | Model | `file.usd[a]` ✓ | type |
# Model column allows spaces (e.g. "Carter v1") so vendor sticky stays correct.
ROBOTS_ROW_RE = re.compile(
    r"^\|\s*(?:\*\*([\w]+)\*\*)?\s*\|\s*([\w_./\s-]+?)\s*\|\s*`([\w_./-]+\.(?:usd|usda))`",
    re.MULTILINE,
)
# robots.md file path declaration: $ISAAC/Robots/{Vendor}/{Model}/{model}.usd[a]
ROBOTS_PATTERN = "Robots/{vendor}/{model}/{file}"
# Filter: paths containing template placeholders {var} are not real URLs
PLACEHOLDER_RE = re.compile(r"\{[^}]+\}")


def parse_prefixes(text: str) -> dict[str, str]:
    """Extract `$VAR = "https://..."` prefix declarations from md header."""
    return {var: url.rstrip("/") for var, url in PREFIX_DECL_RE.findall(text)}


def extract_urls_generic(md_path: Path) -> list[tuple[str, str]]:
    """Resolve every backtick-wrapped *.usd/*.usda containing a `/` separator.

    Returns [(source_line, full_url), ...].
    - `$VAR/...usd[a]` for any declared `$VAR = "https://..."` → expand prefix
    - `Characters/foo.usd[a]` (relative) → use most-recent `Root:` declaration in scope
    - paths with `{placeholder}` skipped
    Bare file names (e.g. robots.md) handled by extract_urls_robots.

    Prefix handling is fully dynamic — adding a new catalog .md with its own
    `$VAR` (e.g. `$DT` for DigitalTwin) just works without touching this code.
    """
    text = md_path.read_text(encoding="utf-8")
    prefixes = parse_prefixes(text)
    if not prefixes:
        return []

    def _expand_decl(var_path: str) -> str:
        """Expand `$VAR/Path/Sub` against the declared prefix table."""
        var, _, rest = var_path.partition("/")
        base = prefixes.get(var)
        if base is None:
            return ""
        return f"{base}/{rest}".rstrip("/") if rest else base.rstrip("/")

    # First `Root:` in the file is the canonical category root for slash-relative
    # paths. Bare filenames use the current section root while scanning.
    main_root = ""
    m_first_root = ROOT_DECL_RE.search(text)
    if m_first_root:
        main_root = _expand_decl(m_first_root.group(1))

    # Fallback base for relative paths when no `Root:` is declared — use whichever
    # prefix is most likely the catalog root (deterministic via dict order).
    fallback_base = next(iter(prefixes.values()), "").rstrip("/")

    out: list[tuple[str, str]] = []
    current_group = ""
    active_root = main_root
    for line in text.splitlines():
        stripped = line.strip()
        root_m = ROOT_DECL_RE.match(stripped)
        if root_m:
            active_root = _expand_decl(root_m.group(1))
            current_group = ""
            continue
        if not stripped.startswith("|"):
            current_group = ""
            continue
        cells = _split_cells(line)
        if cells and not _is_separator_row(cells):
            col0 = re.sub(r"\*+", "", cells[0]).strip()
            if (
                col0
                and "**" in cells[0]
                and ".usd" not in cells[0]
                and ".usda" not in cells[0]
            ):
                current_group = col0
        for path in USD_BACKTICK_RE.findall(line):
            if PLACEHOLDER_RE.search(path):
                continue  # template like `{name}/{name}.usd`
            if "/" not in path and not current_group and path not in cells[0]:
                continue
            # Try declared prefix vars first (longest match would also work,
            # but $VAR/ + first-match is unambiguous given USD path shape).
            expanded = None
            for var, base in prefixes.items():
                if path.startswith(var + "/"):
                    expanded = base + path[len(var):]
                    break
            if expanded:
                out.append((line.strip(), expanded))
            else:
                # relative path: anchor to the file's main `Root:` (or the first
                # declared prefix if no Root: present).
                base = main_root or fallback_base
                if base:
                    if "/" in path:
                        out.append((line.strip(), f"{base}/{path}"))
                    elif current_group:
                        out.append((line.strip(), f"{base}/{current_group}/{path}"))
                    else:
                        section_base = active_root or base
                        out.append((line.strip(), f"{section_base}/{path}"))
    return out


def _split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c) is not None for c in cells if c)


def extract_urls_robots(md_path: Path) -> list[tuple[str, str]]:
    """robots.md uses `{file}.usd[a]`, with vendor/model in adjacent columns."""
    text = md_path.read_text(encoding="utf-8")
    prefixes = parse_prefixes(text)
    isaac = prefixes.get("$ISAAC", "")
    if not isaac:
        return []

    out: list[tuple[str, str]] = []
    current_vendor = ""
    for m in ROBOTS_ROW_RE.finditer(text):
        vendor, model, file = m.group(1), m.group(2), m.group(3)
        if vendor:
            current_vendor = vendor
        if not current_vendor or "/" in file:
            # `/` in file means the file column already encodes the path
            continue
        rel = ROBOTS_PATTERN.format(vendor=current_vendor, model=model, file=file)
        out.append((m.group(0).strip(), f"{isaac}/{rel}"))
    return out


def collect_all_urls() -> list[tuple[str, str, str]]:
    """Return [(md_filename, source_line, full_url), ...] across all asset md files.

    Walks every directory in ASSETS_DIRS that exists on disk, so the composer
    catalog directory is optional — the validator runs even before it's
    populated. README.md files (catalog index) are skipped: they reference
    sub-md filenames, not USD URLs.
    """
    out: list[tuple[str, str, str]] = []
    for assets_dir in ASSETS_DIRS:
        if not assets_dir.is_dir():
            continue
        for md in sorted(assets_dir.glob("*.md")):
            if md.name.lower() == "readme.md":
                continue
            if md.name == "robots.md":
                urls = extract_urls_robots(md)
            else:
                urls = extract_urls_generic(md)
            for line, url in urls:
                out.append((md.name, line, url))
    return out


async def head(client: httpx.AsyncClient, url: str) -> int:
    try:
        r = await client.head(url, follow_redirects=True, timeout=10.0)
        return r.status_code
    except Exception:
        return 0


async def validate(urls: list[tuple[str, str, str]], concurrency: int = 16) -> list[tuple[str, str, str, int]]:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(http2=False) as client:
        async def worker(t: tuple[str, str, str]) -> tuple[str, str, str, int]:
            async with sem:
                return (*t, await head(client, t[2]))
        return await asyncio.gather(*[worker(t) for t in urls])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--concurrency", type=int, default=16)
    args = p.parse_args()

    urls = collect_all_urls()
    if not urls:
        print("No URLs extracted — check ASSETS_DIR contents.")
        return 0

    results = asyncio.run(validate(urls, args.concurrency))
    invalid = [r for r in results if r[3] != 200]

    if args.json:
        print(json.dumps([
            {"file": r[0], "line": r[1], "url": r[2], "status": r[3]}
            for r in invalid
        ], indent=2, ensure_ascii=False))
    else:
        per_file: dict[str, int] = {}
        for r in results:
            per_file[r[0]] = per_file.get(r[0], 0) + 1
        print(f"Validated {len(results)} URLs across {len(per_file)} files:")
        for f, n in sorted(per_file.items()):
            f_invalid = sum(1 for r in invalid if r[0] == f)
            mark = "✓" if f_invalid == 0 else "✗"
            print(f"  {mark} {f:<20} {n:4d} URLs  ({f_invalid} invalid)")
        if invalid:
            print(f"\nInvalid ({len(invalid)}):")
            for fname, line, url, code in invalid[: 100 if args.verbose else 30]:
                print(f"  [{code or 'NET'}] {fname}: {url}")
            if not args.verbose and len(invalid) > 30:
                print(f"  ... ({len(invalid) - 30} more — rerun with --verbose)")

    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
