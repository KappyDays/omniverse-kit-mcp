"""Stage module — snapshot capture, diff, prim/property assertions."""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import asdict

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, fail_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.stage import (
    AssertionFailure,
    AssertionReport,
    DiffKind,
    PrimExistenceAssertion,
    PrimSpec,
    PropertyAssertion,
    StageCaptureFilter,
    StageDiff,
    StageDiffEntry,
    StageSelection,
    StageSnapshot,
    UsdPropertyValue,
)

logger = logging.getLogger(__name__)


class StageModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def capture_snapshot(
        self, meta: OperationMeta, capture_filter: StageCaptureFilter
    ) -> ModuleResult[StageSnapshot]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_snapshot({
                "include_prim_patterns": list(capture_filter.include_prim_patterns),
                "exclude_prim_patterns": list(capture_filter.exclude_prim_patterns),
                "include_properties": capture_filter.include_properties,
                "include_metadata": capture_filter.include_metadata,
                "max_prim_count": capture_filter.max_prim_count,
            })
            snapshot = _parse_snapshot(raw, capture_filter)
            return ok_result(snapshot, started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="STAGE_SNAPSHOT_ERROR")

    async def diff_snapshots(
        self, meta: OperationMeta, before: StageSnapshot, after: StageSnapshot
    ) -> ModuleResult[StageDiff]:
        started = int(time.time() * 1000)
        try:
            entries = _compute_diff(before, after)
            diff = StageDiff(
                entries=tuple(entries),
                before_snapshot_id=before.stage_identifier,
                after_snapshot_id=after.stage_identifier,
                total_changes=len(entries),
            )
            return ok_result(diff, started_ms=started)
        except Exception as exc:
            return error_result(str(exc), started_ms=started)

    async def assert_prim_exists(
        self, meta: OperationMeta, assertion: PrimExistenceAssertion
    ) -> ModuleResult[AssertionReport]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_assert_prim_exists({
                "prim_path": assertion.prim_path,
                "should_exist": assertion.should_exist,
                "expected_type_name": assertion.expected_type_name,
                "expected_active": assertion.expected_active,
            })
            report = _parse_assertion_report(raw)
            if report.passed:
                return ok_result(report, started_ms=started)
            return fail_result(
                f"Prim assertion failed for {assertion.prim_path}",
                started_ms=started,
                data=report,
                error_code="PRIM_ASSERTION_FAILED",
            )
        except Exception as exc:
            from omniverse_kit_mcp.exceptions import StageError, TransportError
            code = "PRIM_ASSERTION_ERROR"
            if isinstance(exc, TransportError):
                code = "TRANSPORT_ERROR"
            elif isinstance(exc, StageError):
                code = exc.error_code
            return error_result(str(exc), started_ms=started, error_code=code)

    async def assert_property(
        self, meta: OperationMeta, assertion: PropertyAssertion
    ) -> ModuleResult[AssertionReport]:
        started = int(time.time() * 1000)
        try:
            payload: dict = {
                "prim_path": assertion.prim_path,
                "property_name": assertion.property_name,
                "property_type": assertion.property_kind,
                "comparator": assertion.comparator,
            }
            if assertion.expected is not None:
                payload["expected_value"] = assertion.expected.value
                payload["expected_type_name"] = assertion.expected.type_name
            if assertion.tolerance is not None:
                payload["tolerance"] = assertion.tolerance
            raw = await self._client.stage_assert_property(payload)
            report = _parse_assertion_report(raw)
            if report.passed:
                return ok_result(report, started_ms=started)
            return fail_result(
                f"Property assertion failed for {assertion.prim_path}.{assertion.property_name}",
                started_ms=started,
                data=report,
                error_code="PROPERTY_ASSERTION_FAILED",
            )
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="PROPERTY_ASSERTION_FAILED")

    # ------------------------------------------------------------------
    # Selection (Phase B+) — GUI Stage panel selection
    # ------------------------------------------------------------------

    async def get_selection(
        self, meta: OperationMeta,
    ) -> ModuleResult[StageSelection]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_get_selection()
            paths = tuple(raw.get("selected_prim_paths", []))
            return ok_result(
                StageSelection(
                    selected_prim_paths=paths,
                    count=int(raw.get("count", len(paths))),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SELECTION_GET_ERROR"
            )

    async def set_selection(
        self,
        meta: OperationMeta,
        prim_paths: list[str],
        expand_in_stage: bool = True,
    ) -> ModuleResult[StageSelection]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.stage_set_selection(
                list(prim_paths), expand_in_stage
            )
            paths = tuple(raw.get("selected_prim_paths", prim_paths))
            return ok_result(
                StageSelection(
                    selected_prim_paths=paths,
                    count=int(raw.get("count", len(paths))),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="SELECTION_SET_ERROR"
            )


# --- Parsing helpers ---


def _parse_snapshot(raw: dict, capture_filter: StageCaptureFilter) -> StageSnapshot:
    prims: dict[str, PrimSpec] = {}
    for path, prim_data in raw.get("prims", {}).items():
        props = {}
        for k, v in prim_data.get("attributes", {}).items():
            if isinstance(v, dict) and "type_name" in v:
                props[k] = UsdPropertyValue(type_name=v["type_name"], value=v["value"])
            else:
                props[k] = UsdPropertyValue(type_name="unknown", value=v)
        rels = {}
        for k, v in prim_data.get("relationships", {}).items():
            rels[k] = tuple(v) if isinstance(v, list) else (v,)
        prims[path] = PrimSpec(
            path=path,
            type_name=prim_data.get("type_name", ""),
            active=prim_data.get("active", True),
            defined=prim_data.get("defined", True),
            instanceable=prim_data.get("instanceable", False),
            properties=props,
            relationships=rels,
            metadata=prim_data.get("metadata", {}),
        )
    return StageSnapshot(
        root_layer_identifier=raw.get("root_layer_identifier", ""),
        stage_identifier=raw.get("stage_identifier", ""),
        default_prim=raw.get("default_prim"),
        prims=prims,
        captured_at_epoch_ms=raw.get("captured_at_epoch_ms", int(time.time() * 1000)),
        capture_filter=capture_filter,
    )


def _compute_diff(before: StageSnapshot, after: StageSnapshot) -> list[StageDiffEntry]:
    entries: list[StageDiffEntry] = []
    all_paths = set(before.prims) | set(after.prims)
    for path in sorted(all_paths):
        b = before.prims.get(path)
        a = after.prims.get(path)
        if b is None and a is not None:
            entries.append(StageDiffEntry(DiffKind.PRIM_ADDED, path, None, None, a))
        elif b is not None and a is None:
            entries.append(StageDiffEntry(DiffKind.PRIM_REMOVED, path, None, b, None))
        elif b is not None and a is not None:
            # Detect prim-level changes (type, active, metadata)
            prim_changes = []
            if b.type_name != a.type_name:
                prim_changes.append(f"type_name: {b.type_name} → {a.type_name}")
            if b.active != a.active:
                prim_changes.append(f"active: {b.active} → {a.active}")
            if b.metadata != a.metadata:
                prim_changes.append("metadata changed")
            if b.instanceable != a.instanceable:
                prim_changes.append(f"instanceable: {b.instanceable} → {a.instanceable}")
            if prim_changes:
                entries.append(StageDiffEntry(
                    DiffKind.PRIM_CHANGED, path, None, b, a,
                    details="; ".join(prim_changes),
                ))
            all_props = set(b.properties) | set(a.properties)
            for prop in sorted(all_props):
                bp = b.properties.get(prop)
                ap = a.properties.get(prop)
                if bp is None and ap is not None:
                    entries.append(StageDiffEntry(DiffKind.PROPERTY_ADDED, path, prop, None, ap))
                elif bp is not None and ap is None:
                    entries.append(StageDiffEntry(DiffKind.PROPERTY_REMOVED, path, prop, bp, None))
                elif bp is not None and ap is not None and bp != ap:
                    entries.append(StageDiffEntry(DiffKind.PROPERTY_CHANGED, path, prop, bp, ap))
    return entries


def _parse_assertion_report(raw: dict) -> AssertionReport:
    failures = tuple(
        AssertionFailure(
            code=f.get("code", "UNKNOWN"),
            message=f.get("message", ""),
            prim_path=f.get("prim_path"),
            property_name=f.get("property_name"),
            actual=UsdPropertyValue(f["actual"]["type_name"], f["actual"]["value"])
            if isinstance(f.get("actual"), dict) and "type_name" in f.get("actual", {})
            else None,
            expected=UsdPropertyValue(f["expected"]["type_name"], f["expected"]["value"])
            if isinstance(f.get("expected"), dict) and "type_name" in f.get("expected", {})
            else None,
        )
        for f in raw.get("failures", [])
    )
    return AssertionReport(
        passed=raw.get("passed", False),
        failures=failures,
        checked_count=raw.get("checked_count", 0),
    )
