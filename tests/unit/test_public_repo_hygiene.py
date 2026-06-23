"""Public repository hygiene guards."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]

_DISALLOWED_PATH_PATTERNS = (
    (
        "windows_user_path",
        re.compile(
            r"\b[A-Za-z]:[\\/]+Users[\\/]+(?![$%<{])"
            r"[A-Za-z0-9._-]+(?:[\\/]|$)"
        ),
    ),
    (
        "msys_user_path",
        re.compile(
            r"(?<![A-Za-z0-9_])/[A-Za-z]/Users/(?![$%<{])"
            r"[A-Za-z0-9._-]+(?:/|$)"
        ),
    ),
    (
        "sanitized_windows_user_path",
        re.compile(r"\b[A-Za-z]--Users-(?![$%<{])[A-Za-z0-9._-]+\b"),
    ),
    ("codex_worktree_path", re.compile(r"\.codex[\\/]+worktrees")),
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
        for label, pattern in _DISALLOWED_PATH_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{rel}: matches {label}")
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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)


def test_public_hygiene_script_flags_new_history_added_local_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")

    (repo / "evidence.md").write_text("capture: redacted\n", encoding="utf-8")
    _commit_all(repo, "baseline")

    leaked_path = "C:" + "/Users/" + "localuser" + "/AppData/Local/Temp/capture.png"
    (repo / "evidence.md").write_text(f"capture: {leaked_path}\n", encoding="utf-8")
    _commit_all(repo, "leak local path")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts" / "review_public_hygiene.py"),
            "--project",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 1
    assert "history-added-line" in result.stdout
    assert "windows_user_path" in result.stdout


def test_public_hygiene_script_accepts_redacted_history(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test User")

    (repo / "evidence.md").write_text("capture: redacted\n", encoding="utf-8")
    _commit_all(repo, "baseline")

    (repo / "evidence.md").write_text(
        "capture: local validation capture path redacted\n",
        encoding="utf-8",
    )
    _commit_all(repo, "redacted evidence")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts" / "review_public_hygiene.py"),
            "--project",
            str(repo),
            "--base",
            "HEAD~1",
            "--head",
            "HEAD",
        ],
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stdout + result.stderr
