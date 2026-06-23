"""Review current tree and pending commit history for public-repo hygiene.

Default use before push:

    .venv/Scripts/python.exe scripts/review_public_hygiene.py

The default history range is the merge-base with the current upstream through
HEAD, so local commits that are about to be pushed are scanned. Pass --base and
--head for an explicit audit range, --since for a session/day audit after
commits have already been pushed, --date for a named local day, or --today for
the current local day.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date
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
SECRET_LIKE_LABELS = frozenset(label for label, _ in SECRET_LIKE_PATTERNS)

SENSITIVE_IDENTIFIER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "process_id_number",
        re.compile(
            r"\b(?:pid|process[_ -]?id)\b"
            r"['\"]?\s*[:=]\s*['\"]?"
            r"\d+\b"
        ),
    ),
    (
        "worker_thread_uuid",
        re.compile(
            r"\b(?:thread[_ -]?id|worker[_ -]?id|worker[_ -]?thread[_ -]?id|"
            r"pendingWorktreeId|pending[_ -]?worktree[_ -]?id)\b"
            r"['\"]?\s*[:=]\s*['\"]?"
            r"(?:019[0-9A-Fa-f]{5}|[0-9A-Fa-f]{8})"
            r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}"
            r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"
        ),
    ),
)

DISALLOWED_GENERATED_REFERENCES = (
    "docs/references/extensions.json",
    "docs/references/extensions-catalog.md",
    "docs/references/harvest-progress.json",
    "docs/references/app-specific/",
    "docs/references/testbed-snapshot/",
    "docs/references/official-assets/",
)


def _local_user_names() -> tuple[str, ...]:
    candidates = {
        os.environ.get("USERNAME", ""),
        os.environ.get("USER", ""),
        Path.home().name,
    }
    return tuple(
        sorted(
            name
            for name in candidates
            if name and re.fullmatch(r"[A-Za-z0-9._-]+", name)
        )
    )


LOCAL_USER_NAMES = _local_user_names()


@dataclass(frozen=True)
class Finding:
    source: str
    label: str
    detail: str
    sample: str = ""
    commit: str | None = None
    reachability: str | None = None

    def format(self) -> str:
        source = (
            f"{self.source}/{self.reachability}"
            if self.reachability
            else self.source
        )
        if self.sample:
            return f"[{source}] {self.detail}: matches {self.label}: {self.sample}"
        return f"[{source}] {self.detail}: matches {self.label}"


def _redact_output_text(value: str) -> str:
    redacted = value
    for label, pattern in (
        DISALLOWED_PATH_PATTERNS
        + SECRET_LIKE_PATTERNS
        + SENSITIVE_IDENTIFIER_PATTERNS
    ):
        if label in SECRET_LIKE_LABELS:
            replacement = f"<secret-like:{label}>"
        elif label.startswith(("process_id", "worker_thread")):
            replacement = f"<sensitive-id:{label}>"
        else:
            replacement = "<local-user-path>"
        redacted = pattern.sub(replacement, redacted)
    for user_name in LOCAL_USER_NAMES:
        redacted = re.sub(
            rf"(['\"]){re.escape(user_name)}(['\"])",
            r"\1<local-user>\2",
            redacted,
            flags=re.IGNORECASE,
        )
    return redacted


def _redact_finding_for_output(finding: Finding) -> Finding:
    return Finding(
        source=finding.source,
        label=finding.label,
        detail=_redact_output_text(finding.detail),
        sample=_redact_output_text(finding.sample),
        commit=finding.commit,
        reachability=finding.reachability,
    )


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


def _untracked_files(project: Path) -> list[str]:
    return _git_output(
        project, "ls-files", "--others", "--exclude-standard"
    ).splitlines()


def _is_generated_reference(rel: str) -> bool:
    return any(
        rel == generated.rstrip("/") or rel.startswith(generated)
        for generated in DISALLOWED_GENERATED_REFERENCES
    )


def _scan_text(
    source: str,
    detail: str,
    text: str,
    *,
    path: str | None = None,
    commit: str | None = None,
    reachability: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, pattern in (
            DISALLOWED_PATH_PATTERNS
            + SECRET_LIKE_PATTERNS
            + SENSITIVE_IDENTIFIER_PATTERNS
        ):
            if label == "process_id_number" and _is_python_source_path(path):
                continue
            if pattern.search(line):
                findings.append(
                    Finding(
                        source=source,
                        label=label,
                        detail=f"{detail}:{line_no}",
                        sample=line.strip()[:240],
                        commit=commit,
                        reachability=reachability,
                    )
                )
        if _looks_like_split_user_path(line):
            findings.append(
                Finding(
                    source=source,
                    label="split_windows_user_path",
                    detail=f"{detail}:{line_no}",
                    sample=line.strip()[:240],
                    commit=commit,
                    reachability=reachability,
                )
            )
    return findings


def _is_python_source_path(path: str | None) -> bool:
    return bool(path and path.lower().endswith(".py"))


def _looks_like_split_user_path(line: str) -> bool:
    if "/Users/" not in line and "\\Users\\" not in line:
        return False
    for user_name in LOCAL_USER_NAMES:
        if re.search(rf"['\"]{re.escape(user_name)}['\"]", line, re.IGNORECASE):
            return True
    return False


def _scan_worktree_file(project: Path, source: str, rel: str) -> list[Finding]:
    findings: list[Finding] = []
    if _is_generated_reference(rel):
        return [Finding(source, "generated_reference", rel)]

    path = project / rel
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return findings
    except FileNotFoundError:
        return findings
    findings.extend(_scan_text(source, rel, text, path=rel))
    return findings


def scan_current_tree(project: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in _tracked_files(project):
        findings.extend(_scan_worktree_file(project, "current-tree", rel))
    for rel in _untracked_files(project):
        findings.extend(_scan_worktree_file(project, "untracked-tree", rel))
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


def _ref_exists(project: Path, ref: str) -> bool:
    return _git(project, "rev-parse", "--verify", ref, check=False).returncode == 0


def _default_public_ref(project: Path) -> str | None:
    upstream = _git_output(
        project,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
        check=False,
    ).strip()
    if upstream:
        return upstream
    if _ref_exists(project, "origin/main"):
        return "origin/main"
    return None


def _resolve_public_ref(project: Path, public_ref: str | None) -> str | None:
    if public_ref:
        if not _ref_exists(project, public_ref):
            raise ValueError(f"invalid --public-ref value: {public_ref}")
        return public_ref
    return _default_public_ref(project)


def _commit_reachability(project: Path, commit: str, public_ref: str | None) -> str:
    if not public_ref:
        return "unknown"
    result = _git(project, "merge-base", "--is-ancestor", commit, public_ref, check=False)
    return "already_public" if result.returncode == 0 else "pending_push"


def _base_and_commits_since(
    project: Path,
    head: str,
    since: str,
) -> tuple[str | None, list[str]]:
    result = _git(
        project,
        "rev-list",
        "--reverse",
        f"--since={since}",
        head,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"invalid --since value: {since}")
    commits = result.stdout.splitlines()
    if not commits:
        return head, []
    parent_result = _git(project, "rev-parse", f"{commits[0]}^", check=False)
    parent = parent_result.stdout.strip() if parent_result.returncode == 0 else None
    return parent, commits


def _today_since_expression() -> str:
    return f"{date.today().isoformat()} 00:00"


def _date_since_expression(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"invalid --date value: {value}; expected YYYY-MM-DD"
        ) from exc
    return f"{parsed.isoformat()} 00:00"


def _changed_files_in_range(project: Path, base: str, head: str) -> list[str]:
    output = _git_output(project, "diff", "--name-only", f"{base}..{head}")
    return output.splitlines()


def _commits_in_range(project: Path, base: str, head: str) -> list[str]:
    output = _git_output(project, "rev-list", "--reverse", f"{base}..{head}")
    return output.splitlines()


def _changed_files_in_commits(project: Path, commits: list[str]) -> list[str]:
    files: set[str] = set()
    for commit in commits:
        output = _git_output(
            project,
            "show",
            "--format=",
            "--name-only",
            "--no-renames",
            commit,
        )
        files.update(line for line in output.splitlines() if line)
    return sorted(files)


def _scan_commit_added_lines(
    project: Path,
    commit: str,
    public_ref: str | None,
) -> list[Finding]:
    full_commit = _git_output(project, "rev-parse", commit).strip()
    reachability = _commit_reachability(project, full_commit, public_ref)
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
        findings.extend(
            _scan_text(
                "history-added-line",
                f"{subject} {current_file}",
                line[1:],
                path=current_file,
                commit=full_commit,
                reachability=reachability,
            )
        )
    return findings


def scan_history(
    project: Path,
    base: str | None,
    head: str,
    *,
    commits: list[str] | None = None,
    public_ref: str | None = None,
) -> list[Finding]:
    if commits is None and not base:
        return []
    if commits is None and _git_output(project, "rev-parse", base).strip() == _git_output(
        project, "rev-parse", head
    ).strip():
        return []

    history_commits = commits if commits is not None else _commits_in_range(project, base, head)
    if not history_commits:
        return []

    findings: list[Finding] = []
    changed_files = (
        _changed_files_in_range(project, base, head)
        if base
        else _changed_files_in_commits(project, history_commits)
    )
    for rel in changed_files:
        if _is_generated_reference(rel):
            findings.append(
                Finding("history-path", "generated_reference", f"{base}..{head} {rel}")
            )
    for commit in history_commits:
        findings.extend(_scan_commit_added_lines(project, commit, public_ref))
    return findings


def _reachability_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        if not finding.reachability:
            continue
        counts[finding.reachability] = counts.get(finding.reachability, 0) + 1
    return dict(sorted(counts.items()))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=PROJECT)
    range_group = parser.add_mutually_exclusive_group()
    range_group.add_argument(
        "--base",
        help="exclusive lower bound commit for history scan",
    )
    range_group.add_argument(
        "--since",
        help=(
            "scan history since this git date expression, e.g. "
            "'2026-06-23 00:00'"
        ),
    )
    range_group.add_argument(
        "--today",
        action="store_true",
        help="scan history since local midnight today",
    )
    range_group.add_argument(
        "--date",
        help="scan history since local midnight for YYYY-MM-DD",
    )
    parser.add_argument("--head", default="HEAD", help="inclusive upper bound commit")
    parser.add_argument(
        "--public-ref",
        help=(
            "ref treated as already public for history finding classification; "
            "defaults to the current upstream, then origin/main"
        ),
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="scan only the current tracked tree",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    parser.add_argument(
        "--redact-samples",
        action="store_true",
        help=(
            "redact project path, finding details, and samples in output for "
            "public-safe review summaries; scan logic is unchanged"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or []))
    project = args.project.resolve()
    head = args.head
    history_commits: list[str] | None = None
    try:
        if args.today:
            since = _today_since_expression()
        elif args.date:
            since = _date_since_expression(args.date)
        else:
            since = args.since
        if since:
            base, history_commits = _base_and_commits_since(project, head, since)
        else:
            base = args.base if args.base else _default_base(project, head)
        public_ref = None if args.skip_history else _resolve_public_ref(project, args.public_ref)
    except ValueError as exc:
        print(f"Public repository hygiene review error: {exc}", file=sys.stderr)
        return 2

    findings = scan_current_tree(project)
    if not args.skip_history:
        findings.extend(
            scan_history(
                project,
                base,
                head,
                commits=history_commits,
                public_ref=public_ref,
            )
        )

    if args.skip_history:
        range_text = "skipped"
    elif since:
        range_text = f"{base}..{head} (since {since})" if base else "none"
    else:
        range_text = f"{base}..{head}" if base else "none"
    output_findings = (
        [_redact_finding_for_output(finding) for finding in findings]
        if args.redact_samples
        else findings
    )
    output_project = (
        _redact_output_text(str(project)) if args.redact_samples else str(project)
    )
    if args.format == "json":
        print(json.dumps(
            {
                "ok": not findings,
                "project": output_project,
                "history_range": range_text,
                "public_ref": public_ref,
                "finding_count": len(findings),
                "reachability_counts": _reachability_counts(findings),
                "findings": [asdict(finding) for finding in output_findings],
            },
            indent=2,
        ))
        return 1 if findings else 0

    if findings:
        print("Public repository hygiene review failed:")
        print(f"  project: {output_project}")
        print(f"  history range: {range_text}")
        if public_ref:
            print(f"  public ref: {public_ref}")
        reachability_counts = _reachability_counts(findings)
        if reachability_counts:
            counts_text = ", ".join(
                f"{key}={value}" for key, value in reachability_counts.items()
            )
            print(f"  reachability: {counts_text}")
        for finding in output_findings[:100]:
            print(f"  - {finding.format()}")
        if len(findings) > 100:
            print(f"  ... {len(findings) - 100} more finding(s)")
        return 1

    print("Public repository hygiene review OK")
    print(f"  project: {output_project}")
    print(f"  history range: {range_text}")
    if public_ref:
        print(f"  public ref: {public_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
