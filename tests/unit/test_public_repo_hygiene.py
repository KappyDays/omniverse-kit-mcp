"""Public repository hygiene guards."""

from __future__ import annotations

import re
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
_DISALLOWED_GENERATED_REFERENCES = (
    "docs/references/extensions.json",
    "docs/references/extensions-catalog.md",
    "docs/references/harvest-progress.json",
    "docs/references/app-specific/",
    "docs/references/testbed-snapshot/",
    "docs/references/official-assets/",
)
_SECRET_LIKE_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_key", re.compile(r"\bAWS_" + r"SECRET_ACCESS_KEY\s*=")),
    ("github_token", re.compile(r"\bghp_" + r"[A-Za-z0-9_]{20,}\b")),
    ("openai_token", re.compile(r"\bsk-" + r"[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox" + r"[baprs]-[A-Za-z0-9-]{20,}\b")),
)


def _tracked_files() -> list[str]:
    return subprocess.check_output(
        ["git", "-C", str(PROJECT), "ls-files"],
        text=True,
        encoding="utf-8",
    ).splitlines()


def _tracked_text_files() -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for rel in _tracked_files():
        path = PROJECT / rel
        try:
            files.append((rel, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return files


def test_tracked_text_files_do_not_embed_user_specific_paths() -> None:
    tracked = _tracked_text_files()
    offenders: list[str] = []
    for rel, text in tracked:
        for literal in _DISALLOWED_LITERALS:
            if literal in text:
                offenders.append(f"{rel}: contains {literal!r}")
    assert not offenders, "User-specific public path literals found:\n" + "\n".join(
        offenders[:50]
    )


def test_tracked_files_do_not_include_generated_reference_corpora() -> None:
    offenders: list[str] = []
    for rel in _tracked_files():
        if any(
            rel == generated.rstrip("/") or rel.startswith(generated)
            for generated in _DISALLOWED_GENERATED_REFERENCES
        ):
            offenders.append(rel)
    assert not offenders, "Generated local reference files are tracked:\n" + "\n".join(
        offenders[:50]
    )


def test_tracked_text_files_do_not_embed_secret_like_literals() -> None:
    offenders: list[str] = []
    for rel, text in _tracked_text_files():
        for label, pattern in _SECRET_LIKE_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{rel}: matches {label}")
    assert not offenders, "Secret-like literals found in tracked files:\n" + "\n".join(
        offenders[:50]
    )
