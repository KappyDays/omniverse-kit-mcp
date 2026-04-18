"""One-shot sync verifier for the MCP tool surface.

Runs in order:

1. Regenerate `docs/tool-catalog.md` from the live FastMCP server.
2. Fail loudly if the regen produced a diff (catalog was stale).
3. Run the two drift-detection pytest modules.

Exit 0 only when the catalog is up-to-date AND every drift test passes.
Use before committing any change that touches `@mcp.tool()` registrations,
`EXPECTED_MODULE_TOOLS` / `EXPECTED_SCENARIO_TOOLS`, or the Extension REST
surface. Install as a git pre-commit hook via
`scripts/install_pre_commit_hook.py`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG = PROJECT_ROOT / "docs" / "tool-catalog.md"
PYTHON = Path(sys.executable)


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m" if sys.stdout.isatty() else s


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m" if sys.stdout.isatty() else s


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m" if sys.stdout.isatty() else s


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def _catalog_hash() -> str:
    if not CATALOG.exists():
        return ""
    import hashlib
    return hashlib.sha256(CATALOG.read_bytes()).hexdigest()


def main() -> int:
    failures: list[str] = []

    print("== verify_mcp_sync ==")
    print(f"project: {PROJECT_ROOT}")
    print(f"python:  {PYTHON}")
    print()

    # 1. Regenerate catalog
    print(_yellow("[1/3] regenerating docs/tool-catalog.md ..."))
    before = _catalog_hash()
    code, out, err = _run([
        str(PYTHON), str(PROJECT_ROOT / "scripts" / "generate_tool_catalog.py"),
    ])
    if code != 0:
        print(_red(f"  generate_tool_catalog.py exited {code}"))
        print(err)
        return 2
    print(f"  {out.strip()}")
    after = _catalog_hash()

    if before != after:
        failures.append(
            "docs/tool-catalog.md was stale — regen produced a diff. "
            "Stage the updated file before committing."
        )
        print(_red("  ⚠ catalog changed — stale before regen"))
    else:
        print(_green("  ✓ catalog already up-to-date"))
    print()

    # 2. Run drift-detection pytest
    print(_yellow("[2/3] running registration + catalog-sync pytest ..."))
    code, out, err = _run([
        str(PYTHON), "-m", "pytest", "-q",
        "tests/unit/test_tools_registration.py",
        "tests/unit/test_tool_catalog_sync.py",
    ])
    if code != 0:
        failures.append("pytest drift tests failed — inspect output below")
        print(_red(out))
        print(_red(err))
    else:
        print(_green("  ✓ registration + catalog-sync tests green"))
        print(f"  {out.strip().splitlines()[-1]}")
    print()

    # 3. Check git status for uncommitted generated changes
    print(_yellow("[3/3] git status of generated files ..."))
    code, out, _err = _run(["git", "status", "--porcelain", "docs/tool-catalog.md"])
    if out.strip():
        print(_yellow(f"  catalog has uncommitted changes: {out.strip()}"))
        print("  → include docs/tool-catalog.md in the commit.")
    else:
        print(_green("  ✓ catalog matches committed version"))
    print()

    if failures:
        print(_red("verify_mcp_sync FAILED:"))
        for f in failures:
            print(_red(f"  - {f}"))
        print()
        print("Fix suggestions:")
        print("  - Run `.venv/Scripts/python.exe scripts/generate_tool_catalog.py`")
        print("  - Ensure EXPECTED_MODULE_TOOLS/EXPECTED_SCENARIO_TOOLS frozenset "
              "in tests/unit/test_tools_registration.py lists every new tool")
        print("  - Stage the updated docs/tool-catalog.md alongside your tool commit")
        return 1

    print(_green("verify_mcp_sync OK — safe to commit"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
