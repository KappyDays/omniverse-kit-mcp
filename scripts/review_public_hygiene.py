"""Review current tree and pending commit history for public-repo hygiene.

Default use before push:

    .venv/Scripts/python.exe scripts/review_public_hygiene.py

The default history range is the merge-base with the current upstream through
HEAD, so local commits that are about to be pushed are scanned. Pass --base and
--head for an explicit audit range.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]

DISALLOWED_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
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

SECRET_LIKE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_key", re.compile(r"\bAWS_" + r"SECRET_ACCESS_KEY\s*=")),
    ("github_token", re.compile(r"\bghp_" + r"[A-Za-z0-9_]{20,}\b")),
    ("openai_token", re.compile(r"\bsk-" + r"[A-Za-z0-9_-]{20,}\b")),
    ("slack_token", re.compile(r"\bxox" + r"[baprs]-[A-Za-z0-9-]{20,}\b")),
)

DISALLOWED_GENERATED_REFERENCES = (
    "docs/references/extensions.json",
    "docs/references/extensions-catalog.md",
    "docs/references/harvest-progress.json",
    "docs/references/app-specific/",
    "docs/references/testbed-snapshot/",
    "docs/references/official-assets/",
)


@dataclass(frozen=True)
class Finding:
    source: str
    label: str
    detail: str
    sample: str = ""

    def format(self) -> str:
        if self.sample:
            return f"[{self.source}] {self.detail}: matches {self.label}: {self.sample}"
        return f"[{self.source}] {self.detail}: matches {self.label}"


def _git(project: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_output(project: Path, *args: str, check: bool = True) -> str:
    result = _git(project, *args, check=check)
    return result.stdout


def _tracked_files(project: Path) -> list[str]:
    return _git_output(project, "ls-files").splitlines()


def _is_generated_reference(rel: str) -> bool:
    return any(
        rel == generated.rstrip("/") or rel.startswith(generated)
        for generated in DISALLOWED_GENERATED_REFERENCES
    )


def _scan_text(source: str, detail: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in DISALLOWED_PATH_PATTERNS + SECRET_LIKE_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        source=source,
                        label=label,
                        detail=f"{detail}:{line_no}",
                        sample=line.strip()[:240],
                    )
                )
    return findings


def scan_current_tree(project: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in _tracked_files(project):
        if _is_generated_reference(rel):
            findings.append(
                Finding("current-tree", "generated_reference", rel)
            )
            continue

        path = project / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            continue
        findings.extend(_scan_text("current-tree", rel, text))
    return findings


def _default_base(project: Path, head: str) -> str | None:
    upstream = _git_output(
        project,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
        check=False,
    ).strip()
    if upstream:
        merge_base = _git_output(project, "merge-base", upstream, head, check=False).strip()
        if merge_base:
            return merge_base

    count_text = _git_output(project, "rev-list", "--count", head, check=False).strip()
    try:
        count = int(count_text)
    except ValueError:
        return None
    if count > 1:
        return f"{head}~1"
    return None


def _changed_files_in_range(project: Path, base: str, head: str) -> list[str]:
    output = _git_output(project, "diff", "--name-only", f"{base}..{head}")
    return output.splitlines()


def _commits_in_range(project: Path, base: str, head: str) -> list[str]:
    output = _git_output(project, "rev-list", "--reverse", f"{base}..{head}")
    return output.splitlines()


def _scan_commit_added_lines(project: Path, commit: str) -> list[Finding]:
    subject = _git_output(project, "show", "-s", "--format=%h %s", commit).strip()
    diff = _git_output(project, "show", "--format=", "--unified=0", "--no-ext-diff", commit)
    findings: list[Finding] = []
    current_file = "<unknown>"
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/")
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        added = line[1:]
        for label, pattern in DISALLOWED_PATH_PATTERNS + SECRET_LIKE_PATTERNS:
            if pattern.search(added):
                findings.append(
                    Finding(
                        "history-added-line",
                        label,
                        f"{subject} {current_file}",
                        added.strip()[:240],
                    )
                )
    return findings


def scan_history(project: Path, base: str | None, head: str) -> list[Finding]:
    if not base:
        return []
    if _git_output(project, "rev-parse", base).strip() == _git_output(
        project, "rev-parse", head
    ).strip():
        return []

    findings: list[Finding] = []
    for rel in _changed_files_in_range(project, base, head):
        if _is_generated_reference(rel):
            findings.append(
                Finding("history-path", "generated_reference", f"{base}..{head} {rel}")
            )
    for commit in _commits_in_range(project, base, head):
        findings.extend(_scan_commit_added_lines(project, commit))
    return findings


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    parser.add_argument("--base", help="exclusive lower bound commit for history scan")
    parser.add_argument("--head", default="HEAD", help="inclusive upper bound commit")
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="scan only the current tracked tree",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or []))
    project = args.project.resolve()
    head = args.head
    base = args.base if args.base else _default_base(project, head)

    findings = scan_current_tree(project)
    if not args.skip_history:
        findings.extend(scan_history(project, base, head))

    if findings:
        print("Public repository hygiene review failed:")
        for finding in findings[:100]:
            print(f"  - {finding.format()}")
        if len(findings) > 100:
            print(f"  ... {len(findings) - 100} more finding(s)")
        return 1

    range_text = "skipped" if args.skip_history else (f"{base}..{head}" if base else "none")
    print("Public repository hygiene review OK")
    print(f"  project: {project}")
    print(f"  history range: {range_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
