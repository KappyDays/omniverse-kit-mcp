"""Install a git pre-commit hook that runs scripts/verify_mcp_sync.py.

.git/hooks/ is not tracked by git, so each clone must install the hook
locally. Run once after clone:

    .venv/Scripts/python.exe scripts/install_pre_commit_hook.py

The hook checks whether the staged diff touches any MCP-tool-adjacent file
(module_tools.py, rest_router.py, frozenset SoT, generate script, or the
catalog). When it does, it calls verify_mcp_sync.py and blocks the commit
on failure. Unrelated commits are not slowed down.

Use `--uninstall` to remove the hook.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOOK = PROJECT_ROOT / ".git" / "hooks" / "pre-commit"

_HOOK_BODY = r"""#!/usr/bin/env bash
# isaacsim-mcp pre-commit hook — verifies MCP tool surface sync.
# Managed by scripts/install_pre_commit_hook.py. Regenerate if edited.

set -e

CHANGED=$(git diff --cached --name-only)

# Fast-skip: commit does not touch anything that can change MCP surface.
if ! echo "$CHANGED" | grep -qE '(tools/module_tools\.py|tools/scenario_tools\.py|mcp/server\.py|rest_router\.py|modules/|services/|clients/isaac_rest_client\.py|scenario/(action_registry|schema|runner)\.py|scenario\.schema\.json|types/common\.py|tests/unit/test_tools_registration\.py|scripts/generate_tool_catalog\.py|docs/tool-catalog\.md)'; then
  exit 0
fi

echo "[pre-commit] MCP-surface file touched — running verify_mcp_sync.py ..."

# Prefer project venv Python; fall back to whatever 'python' resolves to.
if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python"
fi

if ! "$PY" scripts/verify_mcp_sync.py; then
  echo ""
  echo "[pre-commit] verify_mcp_sync FAILED — commit aborted."
  echo "Fix the errors above, stage any regenerated docs/tool-catalog.md, then retry."
  exit 1
fi

# If the verifier regenerated docs/tool-catalog.md, stop and ask the user
# to include it in the commit (git only stages explicitly staged files).
if ! git diff --quiet docs/tool-catalog.md; then
  echo ""
  echo "[pre-commit] docs/tool-catalog.md was regenerated. Stage it:"
  echo "    git add docs/tool-catalog.md"
  echo "and retry the commit."
  exit 1
fi

echo "[pre-commit] verify_mcp_sync OK."
"""


def install() -> int:
    if not (PROJECT_ROOT / ".git").exists():
        print("Not a git repo — .git/ missing", file=sys.stderr)
        return 2

    HOOK.parent.mkdir(parents=True, exist_ok=True)
    HOOK.write_text(_HOOK_BODY, encoding="utf-8")
    # chmod +x — required on Unix, no-op on Windows but harmless
    try:
        HOOK.chmod(HOOK.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:  # noqa: BLE001
        pass
    print(f"Installed pre-commit hook → {HOOK}")
    print("Hook will run scripts/verify_mcp_sync.py when any MCP-surface file is staged.")
    return 0


def uninstall() -> int:
    if HOOK.exists():
        HOOK.unlink()
        print(f"Removed {HOOK}")
    else:
        print(f"No hook at {HOOK}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uninstall", action="store_true", help="Remove the hook")
    args = parser.parse_args()
    return uninstall() if args.uninstall else install()


if __name__ == "__main__":
    sys.exit(main())
