"""Scenario result reporters (JSON / Markdown)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from omniverse_kit_mcp.types.scenario import ScenarioRunSummary


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
        "| Step | Phase | Status | Duration | Message |",
        "|------|-------|--------|----------|---------|",
    ]
    for sr in summary.step_results:
        dur = f"{sr.duration_ms}ms" if sr.duration_ms is not None else "-"
        msg = sr.message or ""
        lines.append(f"| {sr.step_id} | {sr.phase} | {sr.status.value} | {dur} | {msg} |")

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
