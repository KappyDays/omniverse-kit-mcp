"""Pydantic models for Viewport REST endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ViewportCaptureRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport_name: str = "Viewport"
    camera_prim_path: str | None = None
    renderer: str = "rtx"
    width: int = Field(default=1280, ge=1)
    height: int = Field(default=720, ge=1)
    samples_per_pixel: int = Field(default=64, ge=1)
    settle_frames: int = Field(default=5, ge=0)
    output_format: str = "png"
    transparent_background: bool = False


class SSIMComparisonRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_artifact_path: str
    candidate_artifact_path: str
    min_ssim: float = Field(default=0.99, ge=0.0, le=1.0)
    crop: list[int] | None = None


class UiWindowShowRequestModel(BaseModel):
    """Toggle visibility / focus of a registered omni.ui.Window by title."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Window title (as shown in Window menu).")
    visible: bool = True
    focus: bool = True
    settle_frames: int = Field(default=5, ge=0)


class ViewportCreateRequestModel(BaseModel):
    """Create a secondary omni.kit.viewport.window (Phase E multi-viewport)."""

    model_config = ConfigDict(extra="forbid")

    viewport_name: str = Field(description="Unique window title for the new viewport.")
    camera_path: str | None = Field(
        default=None,
        description="Optional camera prim to bind after creation.",
    )
    width: int = Field(default=1280, ge=1, le=7680)
    height: int = Field(default=720, ge=1, le=4320)
    docked: bool = Field(
        default=False,
        description="If True, dock the viewport next to the main window (best-effort).",
    )


class ViewportDestroyRequestModel(BaseModel):
    """Destroy a secondary viewport window by name (Phase E)."""

    model_config = ConfigDict(extra="forbid")

    viewport_name: str


class WindowCaptureRequestModel(BaseModel):
    """Full Isaac Sim application window capture (GUI + viewport + menus)."""

    model_config = ConfigDict(extra="forbid")

    mode: str = Field(
        default="kit",
        description=(
            "'kit' = auto-detect Isaac Sim / Kit main window by title. "
            "'foreground' = active foreground window (use when Kit has focus). "
            "If `hwnd` is provided, it overrides `mode`."
        ),
    )
    hwnd: int | None = Field(
        default=None,
        description="Explicit HWND (from /window/list). Overrides `mode`.",
    )
    settle_frames: int = Field(default=5, ge=0)
    output_format: str = "png"
    bring_to_front: bool = Field(
        default=False,
        description=(
            "If true, call SetForegroundWindow / BringWindowToTop before capture. "
            "Useful when Isaac Sim is minimized or occluded. Default false to avoid "
            "stealing focus from the caller."
        ),
    )
    use_client_rect: bool = Field(
        default=False,
        description="Capture only the window's client area (exclude title bar / borders).",
    )
    wait_stable: bool = Field(
        default=False,
        description=(
            "Re-capture until PNG sha256 matches for `stable_consecutive` consecutive "
            "polls or `stable_max_wait_s` elapses. Use for async UI loading (S3 thumbnails)."
        ),
    )
    stable_interval_s: float = Field(default=2.0, gt=0.0, le=30.0)
    stable_consecutive: int = Field(default=2, ge=2, le=10)
    stable_max_wait_s: float = Field(default=45.0, gt=0.0, le=300.0)
    stable_diff_threshold: float = Field(
        default=0.01, ge=0.0, le=1.0,
        description=(
            "Mean L1 pixel diff (0-1 scale, downsampled 128x128) below which two "
            "captures are considered equivalent. Tolerates FPS counter / timeline "
            "cursor drift. Lower = stricter."
        ),
    )
