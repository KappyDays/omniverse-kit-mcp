"""Scenario result reporters (JSON / Markdown)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from omniverse_kit_mcp.types.scenario import ScenarioRunSummary

_MAX_HIGHLIGHT_PARTS = 16
_DIAGNOSTIC_SUMMARY_PATHS = (
    ("num_points", (("num_points",),)),
    ("backend", (("backend",),)),
    ("frames_waited", (("frames_waited",),)),
    ("empty_reason", (("empty_reason",), ("diagnostics", "empty_reason"))),
    ("suggested_next", (("diagnostics", "suggested_next"),)),
    ("raw_keys", (("raw_keys",),)),
    ("warning", (("warning",),)),
    ("truncated", (("truncated",),)),
    ("timeline_settled", (("timeline_settled",), ("status", "timeline_settled"))),
    (
        "timeline_settle_updates",
        (("timeline_settle_updates",), ("status", "timeline_settle_updates")),
    ),
    ("is_playing", (("is_playing",), ("status", "is_playing"))),
    ("is_stopped", (("is_stopped",), ("status", "is_stopped"))),
    ("capture_path", (("capture_path",), ("artifact", "path"), ("path",))),
    ("sha256", (("sha256",), ("artifact", "sha256"))),
    ("non_empty", (("non_empty",),)),
    ("passed", (("passed",),)),
)


def to_json(summary: ScenarioRunSummary) -> str:
    """Serialize summary to JSON string."""
    return json.dumps(_to_dict(summary), indent=2, ensure_ascii=False)


def to_markdown(summary: ScenarioRunSummary) -> str:
    """Render summary as Markdown report."""
    lines = [
        f"# Scenario Report: {summary.scenario_id}",
        "",
        f"**Status**: {summary.status.value.upper()}",
        f"**Duration**: {summary.ended_at_epoch_ms - summary.started_at_epoch_ms}ms",
        f"**Steps**: {summary.passed_steps} passed, {summary.failed_steps} failed, {summary.skipped_steps} skipped",
        "",
        "## Step Results",
        "",
        "| Step | Phase | Status | Attempts | Duration | Message |",
        "|------|-------|--------|----------|----------|---------|",
    ]
    for sr in summary.step_results:
        dur = f"{sr.duration_ms}ms" if sr.duration_ms is not None else "-"
        attempts = f"{sr.attempts}/{sr.max_attempts}"
        msg = sr.message or ""
        lines.append(
            f"| {sr.step_id} | {sr.phase} | {sr.status.value} | "
            f"{attempts} | {dur} | {msg} |"
        )

    data_rows = [
        (sr.step_id, _format_data_summary_highlight(sr.data_summary))
        for sr in summary.step_results
        if sr.data_summary and _has_diagnostic_summary(sr.data_summary)
    ]
    if data_rows:
        lines.extend(["", "## Data Summary Highlights", ""])
        for step_id, detail in data_rows:
            lines.append(f"- `{step_id}`: {detail}")

    retry_rows = [
        (sr.step_id, failure)
        for sr in summary.step_results
        for failure in sr.retry_failures
    ]
    if retry_rows:
        lines.extend(["", "## Retry Failures", ""])
        for step_id, failure in retry_rows:
            lines.append(
                f"- `{step_id}` attempt {failure.get('attempt')}: "
                f"{failure.get('status')} {failure.get('error_code')} - "
                f"{failure.get('message') or ''}"
            )

    if summary.artifact_paths:
        lines.extend(["", "## Artifacts", ""])
        for path in summary.artifact_paths:
            lines.append(f"- `{path}`")

    return "\n".join(lines)


def _to_dict(summary: ScenarioRunSummary) -> dict[str, Any]:
    d = asdict(summary)  # type: ignore[arg-type]
    # Convert enum values to strings
    d["status"] = summary.status.value
    d["step_results"] = [
        {**asdict(sr), "status": sr.status.value}  # type: ignore[arg-type]
        for sr in summary.step_results
    ]
    return d


def _has_diagnostic_summary(data_summary: dict[str, Any]) -> bool:
    return bool(_diagnostic_summary_parts(data_summary))


def _format_data_summary_highlight(data_summary: dict[str, Any]) -> str:
    parts = _diagnostic_summary_parts(data_summary)
    emitted = {
        path[0]
        for _key, paths in _DIAGNOSTIC_SUMMARY_PATHS
        for path in paths
        if _lookup_summary_path(data_summary, path)[0]
    }
    for key, value in data_summary.items():
        if len(parts) >= _MAX_HIGHLIGHT_PARTS:
            break
        if value is None and key in {"empty_reason"}:
            continue
        if key not in emitted and _is_compact_scalar(value):
            parts.extend(_format_summary_pair(key, value))
    return "; ".join(parts[:_MAX_HIGHLIGHT_PARTS])


def _diagnostic_summary_parts(data_summary: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for key, paths in _DIAGNOSTIC_SUMMARY_PATHS:
        for path in paths:
            found, value = _lookup_summary_path(data_summary, path)
            if found:
                if value is None and key in {"empty_reason", "suggested_next"}:
                    continue
                parts.extend(_format_summary_pair(key, value))
                break
    return parts


def _lookup_summary_path(
    data_summary: dict[str, Any], path: tuple[str, ...],
) -> tuple[bool, Any]:
    current: Any = data_summary
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _format_summary_pair(key: str, value: Any) -> list[str]:
    if isinstance(value, dict) and "count" in value:
        parts = [f"{key}.count={_format_summary_value(value['count'])}"]
        if "sample" in value:
            parts.append(f"{key}.sample={_format_summary_value(value['sample'])}")
        return parts
    return [f"{key}={_format_summary_value(value)}"]


def _format_summary_value(value: Any) -> str:
    if isinstance(value, list):
        formatted = ", ".join(_format_summary_value(v) for v in value[:6])
        if len(value) > 6:
            formatted += ", ..."
        return f"[{formatted}]"
    if isinstance(value, tuple):
        return _format_summary_value(list(value))
    if isinstance(value, dict):
        compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return compact[:117] + "..." if len(compact) > 120 else compact
    if value is None:
        return "null"
    return str(value)


def _is_compact_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None
