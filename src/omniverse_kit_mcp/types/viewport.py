"""Viewport capture and image comparison types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from omniverse_kit_mcp.types.common import JsonValue


@dataclass(slots=True, frozen=True)
class ViewportCaptureRequest:
    viewport_name: str = "Viewport"
    camera_prim_path: str | None = None
    renderer: Literal["rtx", "hydra"] = "rtx"
    width: int = 1280
    height: int = 720
    samples_per_pixel: int = 64
    settle_frames: int = 5
    output_format: Literal["png", "jpg"] = "png"
    transparent_background: bool = False
    warmup_frames: int = 0
    return_stats: bool = False


@dataclass(slots=True, frozen=True)
class ImageArtifact:
    artifact_id: str
    path: str
    width: int
    height: int
    sha256: str
    created_at_epoch_ms: int
    pixel_mean: tuple[float, ...] | None = None
    pixel_variance: tuple[float, ...] | None = None
    warmup_frames_used: int = 0
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportProjectedPoint:
    world: tuple[float, float, float]
    ndc_xy: tuple[float, float]
    pixel_xy: tuple[float, float]
    depth: float | None
    in_front: bool
    in_frame: bool


@dataclass(slots=True, frozen=True)
class ViewportProjectPointsRequest:
    points: tuple[tuple[float, float, float], ...]
    viewport_name: str = "Viewport"
    camera_path: str | None = None
    width: int = 1280
    height: int = 720


@dataclass(slots=True, frozen=True)
class ViewportProjectPointsResult:
    ok: bool
    viewport_name: str
    camera_path: str
    width: int
    height: int
    points: tuple[ViewportProjectedPoint, ...]
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportFramePrimsRequest:
    prim_paths: tuple[str, ...]
    viewport_name: str = "Viewport"
    camera_path: str | None = None
    include_purposes: tuple[str, ...] = ("default", "render")
    margin: float = 0.15
    fov_deg: float = 60.0
    view_direction: tuple[float, float, float] = (1.0, -1.0, 0.65)
    up: tuple[float, float, float] = (0.0, 0.0, 1.0)
    set_camera: bool = True


@dataclass(slots=True, frozen=True)
class ViewportFramePrimsResult:
    ok: bool
    viewport_name: str
    camera_path: str
    prim_paths: tuple[str, ...]
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]
    fov_deg: float
    distance: float
    combined_bbox: dict[str, object]
    prim_bboxes: tuple[dict[str, object], ...]
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportCaptureAssertRequest:
    viewport_name: str = "Viewport"
    camera_prim_path: str | None = None
    renderer: Literal["rtx", "hydra"] = "rtx"
    width: int = 1280
    height: int = 720
    samples_per_pixel: int = 64
    settle_frames: int = 5
    output_format: Literal["png", "jpg"] = "png"
    transparent_background: bool = False
    warmup_frames: int = 0
    min_mean: float = 8.0
    min_variance: float = 1.0


@dataclass(slots=True, frozen=True)
class ViewportCaptureAssertResult:
    passed: bool
    artifact: ImageArtifact | None
    pixel_mean_average: float | None
    pixel_variance_average: float | None
    failure_codes: tuple[str, ...]
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SSIMComparisonRequest:
    baseline_artifact_path: str
    candidate_artifact_path: str
    min_ssim: float = 0.99
    crop: tuple[int, int, int, int] | None = None  # (x, y, w, h) ROI


@dataclass(slots=True, frozen=True)
class SSIMComparisonResult:
    score: float
    passed: bool
    diff_heatmap_path: str | None = None
    compared_width: int | None = None
    compared_height: int | None = None
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportCreateRequest:
    viewport_name: str
    camera_path: str | None = None
    width: int = 1280
    height: int = 720
    docked: bool = False


@dataclass(slots=True, frozen=True)
class ViewportCreateResult:
    ok: bool
    viewport_name: str
    existed: bool
    camera_path: str | None
    width: int
    height: int
    docked: bool
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportDestroyRequest:
    viewport_name: str


@dataclass(slots=True, frozen=True)
class ViewportDestroyResult:
    ok: bool
    viewport_name: str
    destroyed: bool
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


# --- Phase F: Render extension --------------------------------------------


@dataclass(slots=True, frozen=True)
class ViewportSetRenderModeRequest:
    viewport_name: str
    mode: Literal["RealTime", "PathTracing"]


@dataclass(slots=True, frozen=True)
class ViewportSetRenderModeResult:
    ok: bool
    viewport_name: str
    mode: str
    setting_value: str
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportSetRenderQualityRequest:
    samples: int = 1
    denoiser: Literal["auto", "DLSS", "NRD", "off"] = "auto"


@dataclass(slots=True, frozen=True)
class ViewportSetRenderQualityResult:
    ok: bool
    samples: int
    denoiser: str
    aa_op: int
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportToggleOverlayRequest:
    viewport_name: str
    overlay: Literal["gridlines", "axis", "stats"]
    visible: bool = True


@dataclass(slots=True, frozen=True)
class ViewportToggleOverlayResult:
    ok: bool
    viewport_name: str
    overlay: str
    visible: bool
    setting_path: str
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportSetFovRequest:
    viewport_name: str
    fov_deg: float


@dataclass(slots=True, frozen=True)
class ViewportSetFovResult:
    ok: bool
    viewport_name: str
    camera_path: str
    fov_deg: float
    focal_length: float
    horizontal_aperture: float
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportSetCameraLookatRequest:
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float] = (0.0, 0.0, 1.0)
    viewport_name: str = "Viewport"
    camera_path: str | None = None


@dataclass(slots=True, frozen=True)
class ViewportSetCameraLookatResult:
    ok: bool
    viewport_name: str
    camera_path: str
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ViewportFocusPrimRequest:
    prim_path: str
    viewport_name: str = "Viewport"
    camera_path: str | None = None
    padding: float = 1.35
    select: bool = True


@dataclass(slots=True, frozen=True)
class ViewportFocusPrimResult:
    ok: bool
    prim_path: str
    viewport_name: str
    camera_path: str
    method: str
    target: tuple[float, float, float]
    eye: tuple[float, float, float] | None = None
    bbox_min: tuple[float, float, float] | None = None
    bbox_max: tuple[float, float, float] | None = None
    radius: float = 0.0
    selected: bool = False
    diagnostics: dict[str, JsonValue] = field(default_factory=dict)
