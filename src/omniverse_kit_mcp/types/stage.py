"""Stage-related types for Prim/Property validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from omniverse_kit_mcp.types.common import JsonValue


@dataclass(slots=True, frozen=True)
class StageFileResult:
    """Result of save/open/new file operations."""

    ok: bool
    path: str | None
    mode: str | None = None


@dataclass(slots=True, frozen=True)
class StageSelection:
    selected_prim_paths: tuple[str, ...]
    count: int


@dataclass(slots=True, frozen=True)
class ViewportActiveCameraResult:
    viewport_name: str
    camera_path: str


@dataclass(slots=True, frozen=True)
class UsdPropertyValue:
    """USD property with explicit type info for faithful serialization."""

    type_name: str  # e.g. "float", "double3", "token", "asset", "relationship"
    value: JsonValue


@dataclass(slots=True, frozen=True)
class PrimSpec:
    path: str
    type_name: str
    active: bool
    defined: bool
    instanceable: bool
    properties: dict[str, UsdPropertyValue]
    relationships: dict[str, tuple[str, ...]]
    metadata: dict[str, JsonValue]


@dataclass(slots=True, frozen=True)
class StageCaptureFilter:
    include_prim_patterns: tuple[str, ...] = ("*",)
    exclude_prim_patterns: tuple[str, ...] = ()
    include_properties: bool = True
    include_metadata: bool = True
    max_prim_count: int = 10_000


@dataclass(slots=True, frozen=True)
class StageSnapshot:
    root_layer_identifier: str
    stage_identifier: str
    default_prim: str | None
    prims: dict[str, PrimSpec]
    captured_at_epoch_ms: int
    capture_filter: StageCaptureFilter


@dataclass(slots=True, frozen=True)
class StageWorldBboxRequest:
    prim_path: str
    include_purposes: tuple[str, ...] = ("default", "render")


@dataclass(slots=True, frozen=True)
class StageWorldBbox:
    ok: bool
    prim_path: str
    min: tuple[float, float, float]
    max: tuple[float, float, float]
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    world_translate: tuple[float, float, float]
    world_orient_wxyz: tuple[float, float, float, float]
    is_empty: bool


@dataclass(slots=True, frozen=True)
class StageVisualAlignmentRequest:
    reference_prim_path: str
    candidate_prim_paths: tuple[str, ...]
    include_purposes: tuple[str, ...] = ("default", "render")
    min_iou_xy: float = 0.5
    max_center_delta_m: float = 0.05


@dataclass(slots=True, frozen=True)
class StageVisualAlignmentEntry:
    candidate_prim_path: str
    passed: bool
    iou_xy: float
    center_delta_m: float
    center_delta: tuple[float, float, float]
    failure_codes: tuple[str, ...]
    candidate_bbox: StageWorldBbox


@dataclass(slots=True, frozen=True)
class StageVisualAlignmentReport:
    reference_prim_path: str
    passed: bool
    reference_bbox: StageWorldBbox
    entries: tuple[StageVisualAlignmentEntry, ...]


@dataclass(slots=True, frozen=True)
class StagePlacementValidationRequest:
    subject_prim_paths: tuple[str, ...]
    container_prim_path: str | None = None
    support_prim_path: str | None = None
    obstacle_prim_paths: tuple[str, ...] = ()
    checks: tuple[str, ...] = ("containment",)
    include_purposes: tuple[str, ...] = ("default", "render")
    containment_axes: tuple[str, ...] = ("x", "y")
    margin_m: float = 0.0
    min_clearance_m: float = 0.0
    floor_tolerance_m: float = 0.01
    floor_axis: str = "z"


@dataclass(slots=True, frozen=True)
class StagePlacementValidationEntry:
    subject_prim_path: str
    passed: bool
    failure_codes: tuple[str, ...]
    bbox: StageWorldBbox | None
    checks: dict[str, JsonValue]
    prim: dict[str, JsonValue]


@dataclass(slots=True, frozen=True)
class StagePlacementValidationReport:
    passed: bool
    checked_count: int
    approximation: str
    entries: tuple[StagePlacementValidationEntry, ...]
    container_bbox: StageWorldBbox | None
    support_bbox: StageWorldBbox | None
    obstacle_bboxes: tuple[StageWorldBbox, ...]
    settings: dict[str, JsonValue]


class DiffKind(str, Enum):
    PRIM_ADDED = "prim_added"
    PRIM_REMOVED = "prim_removed"
    PRIM_CHANGED = "prim_changed"
    PROPERTY_ADDED = "property_added"
    PROPERTY_REMOVED = "property_removed"
    PROPERTY_CHANGED = "property_changed"


@dataclass(slots=True, frozen=True)
class StageDiffEntry:
    kind: DiffKind
    prim_path: str
    property_name: str | None
    before: JsonValue | PrimSpec | UsdPropertyValue | None
    after: JsonValue | PrimSpec | UsdPropertyValue | None
    details: str | None = None


@dataclass(slots=True, frozen=True)
class StageDiff:
    entries: tuple[StageDiffEntry, ...]
    before_snapshot_id: str | None
    after_snapshot_id: str | None
    total_changes: int


@dataclass(slots=True, frozen=True)
class PrimExistenceAssertion:
    prim_path: str
    should_exist: bool = True
    expected_type_name: str | None = None
    expected_active: bool | None = None


@dataclass(slots=True, frozen=True)
class PropertyAssertion:
    prim_path: str
    property_name: str
    property_kind: Literal["attribute", "relationship"] = "attribute"
    comparator: Literal[
        "equals",
        "not_equals",
        "contains",
        "regex",
        "approx",
        "gt",
        "gte",
        "lt",
        "lte",
        "exists",
    ] = "equals"
    expected: UsdPropertyValue | None = None
    tolerance: float | None = None


@dataclass(slots=True, frozen=True)
class AssertionFailure:
    code: str
    message: str
    prim_path: str | None = None
    property_name: str | None = None
    actual: UsdPropertyValue | None = None
    expected: UsdPropertyValue | None = None


@dataclass(slots=True, frozen=True)
class AssertionReport:
    passed: bool
    failures: tuple[AssertionFailure, ...]
    checked_count: int
