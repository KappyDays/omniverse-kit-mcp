"""Validate USD URLs in isaac_course/docs/assets/*.md via S3 HEAD requests.

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
ASSETS_DIR = PROJECT_ROOT / "isaac_course" / "docs" / "assets"

PREFIX_DECL_RE = re.compile(r"^`(\$\w+)`\s*=\s*`(https?://[^`]+)`", re.MULTILINE)
USD_BACKTICK_RE = re.compile(r"`([^`\s]+\.usd)`")
# Section root declaration: 루트: `$ISAAC/Path/`
ROOT_DECL_RE = re.compile(r"^루트:\s*`(\$\w+/[^`]+?)/?`", re.MULTILINE)
# robots.md row form: | **Vendor** | Model | `file.usd` ✓ | type |
# Model column allows spaces (e.g. "Carter v1") so vendor sticky stays correct.
ROBOTS_ROW_RE = re.compile(
    r"^\|\s*(?:\*\*([\w]+)\*\*)?\s*\|\s*([\w_./\s-]+?)\s*\|\s*`([\w_./-]+\.usd)`",
    re.MULTILINE,
)
# robots.md file path declaration: $ISAAC/Robots/{Vendor}/{Model}/{model}.usd
ROBOTS_PATTERN = "Robots/{vendor}/{model}/{file}"
# Filter: paths containing template placeholders {var} are not real URLs
PLACEHOLDER_RE = re.compile(r"\{[^}]+\}")


def parse_prefixes(text: str) -> dict[str, str]:
    """Extract `$VAR = "https://..."` prefix declarations from md header."""
    return {var: url.rstrip("/") for var, url in PREFIX_DECL_RE.findall(text)}


def extract_urls_generic(md_path: Path) -> list[tuple[str, str]]:
    """Resolve every backtick-wrapped *.usd containing a `/` separator.

    Returns [(source_line, full_url), ...].
    - `$ISAAC/...usd` / `$SIM/...usd` → expand prefix
    - `Characters/foo.usd` (relative) → use most-recent `루트:` declaration in scope
    - paths with `{placeholder}` skipped
    Bare file names (e.g. robots.md) handled by extract_urls_robots.
    """
    text = md_path.read_text(encoding="utf-8")
    prefixes = parse_prefixes(text)
    isaac = prefixes.get("$ISAAC", "")
    sim = prefixes.get("$SIM", "")
    if not isaac and not sim:
        return []

    def _expand(prefix_var: str) -> str:
        # `$ISAAC/People/Characters` → "https://.../Isaac/People/Characters"
        if prefix_var.startswith("$ISAAC"):
            return isaac + prefix_var[len("$ISAAC"):]
        if prefix_var.startswith("$SIM"):
            return sim + prefix_var[len("$SIM"):]
        return ""

    # First `루트:` in the file is the canonical category root for all relative
    # paths. Subsequent `루트:` are sub-section context only — table path columns
    # are still expressed against the *first* root.
    main_root = ""
    m_first_root = ROOT_DECL_RE.search(text)
    if m_first_root:
        main_root = _expand(m_first_root.group(1)).rstrip("/")

    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        for path in USD_BACKTICK_RE.findall(line):
            if "/" not in path:
                continue
            if PLACEHOLDER_RE.search(path):
                continue  # template like `{name}/{name}.usd`
            if path.startswith("$ISAAC/"):
                if isaac:
                    out.append((line.strip(), isaac + path[len("$ISAAC"):]))
            elif path.startswith("$SIM/"):
                if sim:
                    out.append((line.strip(), sim + path[len("$SIM"):]))
            else:
                # relative: use the file's main `루트:` (or $ISAAC top if absent)
                base = main_root or isaac
                if base:
                    out.append((line.strip(), f"{base}/{path}"))
    return out


def extract_urls_robots(md_path: Path) -> list[tuple[str, str]]:
    """robots.md uses `{file}.usd` only, with vendor/model in adjacent columns."""
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
    """Return [(md_filename, source_line, full_url), ...] across all asset md files."""
    out: list[tuple[str, str, str]] = []
    for md in sorted(ASSETS_DIR.glob("*.md")):
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
