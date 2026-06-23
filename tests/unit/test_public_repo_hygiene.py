"""Public repository hygiene guards."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
_LOCAL_USER = "ka" + "ng"

_DISALLOWED_LITERALS = (
    "C:" + f"/Users/{_LOCAL_USER}",
    "C:" + f"\\Users\\{_LOCAL_USER}",
    "C--Users-" + _LOCAL_USER,
    ".codex" + "\\worktrees",
    ".codex" + "/worktrees",
)


def test_tracked_text_files_do_not_embed_user_specific_paths() -> None:
    tracked = subprocess.check_output(
        ["git", "-C", str(PROJECT), "ls-files"],
        text=True,
        encoding="utf-8",
    ).splitlines()
    offenders: list[str] = []
    for rel in tracked:
        path = PROJECT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for literal in _DISALLOWED_LITERALS:
            if literal in text:
                offenders.append(f"{rel}: contains {literal!r}")
    assert not offenders, "User-specific public path literals found:\n" + "\n".join(
        offenders[:50]
    )
