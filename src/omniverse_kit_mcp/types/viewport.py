"""Viewport capture and image comparison types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


@dataclass(slots=True, frozen=True)
class ViewportDestroyRequest:
    viewport_name: str


@dataclass(slots=True, frozen=True)
class ViewportDestroyResult:
    ok: bool
    viewport_name: str
    destroyed: bool


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
