"""Viewport module — screenshot capture and SSIM comparison."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, fail_result, ok_result
from omniverse_kit_mcp.types.common import JsonValue, ModuleResult, OperationMeta
from omniverse_kit_mcp.types.stage import ViewportActiveCameraResult
from omniverse_kit_mcp.types.viewport import (
    ImageArtifact,
    SSIMComparisonRequest,
    SSIMComparisonResult,
    ViewportCaptureAssertRequest,
    ViewportCaptureAssertResult,
    ViewportCaptureRequest,
    ViewportCreateRequest,
    ViewportCreateResult,
    ViewportDestroyRequest,
    ViewportDestroyResult,
    ViewportFocusPrimRequest,
    ViewportFocusPrimResult,
    ViewportFramePrimsRequest,
    ViewportFramePrimsResult,
    ViewportProjectedPoint,
    ViewportProjectPointsRequest,
    ViewportProjectPointsResult,
    ViewportSetCameraLookatRequest,
    ViewportSetCameraLookatResult,
    ViewportSetFovRequest,
    ViewportSetFovResult,
    ViewportSetRenderModeRequest,
    ViewportSetRenderModeResult,
    ViewportSetRenderQualityRequest,
    ViewportSetRenderQualityResult,
    ViewportToggleOverlayRequest,
    ViewportToggleOverlayResult,
)

logger = logging.getLogger(__name__)


class ViewportModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def capture(
        self, meta: OperationMeta, request: ViewportCaptureRequest
    ) -> ModuleResult[ImageArtifact]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_capture({
                "viewport_name": request.viewport_name,
                "camera_prim_path": request.camera_prim_path,
                "renderer": request.renderer,
                "width": request.width,
                "height": request.height,
                "samples_per_pixel": request.samples_per_pixel,
                "settle_frames": request.settle_frames,
                "output_format": request.output_format,
                "transparent_background": request.transparent_background,
                "warmup_frames": request.warmup_frames,
                "return_stats": request.return_stats,
            })
            artifact = ImageArtifact(
                artifact_id=raw["artifact_id"],
                path=raw["path"],
                width=raw.get("width", request.width),
                height=raw.get("height", request.height),
                sha256=raw.get("sha256", ""),
                created_at_epoch_ms=raw.get("created_at_epoch_ms", int(time.time() * 1000)),
                pixel_mean=tuple(raw["pixel_mean"]) if raw.get("pixel_mean") is not None else None,
                pixel_variance=tuple(raw["pixel_variance"]) if raw.get("pixel_variance") is not None else None,
                warmup_frames_used=int(raw.get("warmup_frames_used", 0)),
            )
            return ok_result(artifact, started_ms=started, artifacts={"image": artifact.path})
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="VIEWPORT_CAPTURE_ERROR")

    async def compare_ssim(
        self, meta: OperationMeta, request: SSIMComparisonRequest
    ) -> ModuleResult[SSIMComparisonResult]:
        started = int(time.time() * 1000)
        try:
            payload: dict = {
                "baseline_artifact_path": request.baseline_artifact_path,
                "candidate_artifact_path": request.candidate_artifact_path,
                "min_ssim": request.min_ssim,
            }
            if request.crop is not None:
                payload["crop"] = list(request.crop)
            raw = await self._client.viewport_compare_ssim(payload)
            result = SSIMComparisonResult(
                score=raw["score"],
                passed=raw["passed"],
                diff_heatmap_path=raw.get("diff_heatmap_path"),
                compared_width=raw.get("compared_width"),
                compared_height=raw.get("compared_height"),
            )
            artifacts = {}
            if result.diff_heatmap_path:
                artifacts["diff_heatmap"] = result.diff_heatmap_path
            if result.passed:
                return ok_result(result, started_ms=started, artifacts=artifacts)
            return fail_result(
                f"SSIM {result.score:.4f} < threshold {request.min_ssim}",
                started_ms=started,
                data=result,
                error_code="VIEWPORT_COMPARISON_FAILED",
            )
        except Exception as exc:
            return error_result(str(exc), started_ms=started, error_code="VIEWPORT_COMPARISON_ERROR")

    async def set_active_camera(
        self,
        meta: OperationMeta,
        camera_path: str,
        viewport_name: str = "Viewport",
    ) -> ModuleResult[ViewportActiveCameraResult]:
        """Switch the active camera of a viewport (GUI toolbar equivalent)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_set_active_camera(
                camera_path, viewport_name
            )
            return ok_result(
                ViewportActiveCameraResult(
                    viewport_name=raw.get("viewport_name", viewport_name),
                    camera_path=raw.get("camera_path", camera_path),
                ),
                started_ms=started,
            )
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="VIEWPORT_SET_CAMERA_ERROR"
            )

    async def create(
        self, meta: OperationMeta, request: ViewportCreateRequest,
    ) -> ModuleResult[ViewportCreateResult]:
        """Create a secondary viewport window bound to an optional camera (Phase E)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_create({
                "viewport_name": request.viewport_name,
                "camera_path": request.camera_path,
                "width": request.width,
                "height": request.height,
                "docked": request.docked,
            })
            return ok_result(
                ViewportCreateResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    existed=bool(raw.get("existed", False)),
                    camera_path=raw.get("camera_path"),
                    width=int(raw.get("width", request.width)),
                    height=int(raw.get("height", request.height)),
                    docked=bool(raw.get("docked", request.docked)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="VIEWPORT_CREATE_ERROR",
            )

    async def destroy(
        self, meta: OperationMeta, request: ViewportDestroyRequest,
    ) -> ModuleResult[ViewportDestroyResult]:
        """Destroy a secondary viewport window (Phase E)."""
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_destroy({
                "viewport_name": request.viewport_name,
            })
            return ok_result(
                ViewportDestroyResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    destroyed=bool(raw.get("destroyed", False)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, error_code="VIEWPORT_DESTROY_ERROR",
            )

    # --- Phase F: Render extension --------------------------------------

    async def set_render_mode(
        self, meta: OperationMeta, request: ViewportSetRenderModeRequest,
    ) -> ModuleResult[ViewportSetRenderModeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_set_render_mode({
                "viewport_name": request.viewport_name,
                "mode": request.mode,
            })
            return ok_result(
                ViewportSetRenderModeResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    mode=str(raw.get("mode", request.mode)),
                    setting_value=str(raw.get("setting_value", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_SET_RENDER_MODE_ERROR",
            )

    async def set_render_quality(
        self, meta: OperationMeta, request: ViewportSetRenderQualityRequest,
    ) -> ModuleResult[ViewportSetRenderQualityResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_set_render_quality({
                "samples": request.samples,
                "denoiser": request.denoiser,
            })
            return ok_result(
                ViewportSetRenderQualityResult(
                    ok=bool(raw.get("ok", True)),
                    samples=int(raw.get("samples", request.samples)),
                    denoiser=str(raw.get("denoiser", request.denoiser)),
                    aa_op=int(raw.get("aa_op", 0)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_SET_RENDER_QUALITY_ERROR",
            )

    async def toggle_overlay(
        self, meta: OperationMeta, request: ViewportToggleOverlayRequest,
    ) -> ModuleResult[ViewportToggleOverlayResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_toggle_overlay({
                "viewport_name": request.viewport_name,
                "overlay": request.overlay,
                "visible": request.visible,
            })
            return ok_result(
                ViewportToggleOverlayResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    overlay=str(raw.get("overlay", request.overlay)),
                    visible=bool(raw.get("visible", request.visible)),
                    setting_path=str(raw.get("setting_path", "")),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_TOGGLE_OVERLAY_ERROR",
            )

    async def set_fov(
        self, meta: OperationMeta, request: ViewportSetFovRequest,
    ) -> ModuleResult[ViewportSetFovResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_set_fov({
                "viewport_name": request.viewport_name,
                "fov_deg": request.fov_deg,
            })
            return ok_result(
                ViewportSetFovResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    camera_path=str(raw.get("camera_path", "")),
                    fov_deg=float(raw.get("fov_deg", request.fov_deg)),
                    focal_length=float(raw.get("focal_length", 0.0)),
                    horizontal_aperture=float(raw.get("horizontal_aperture", 0.0)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_SET_FOV_ERROR",
            )

    async def set_camera_lookat(
        self, meta: OperationMeta, request: ViewportSetCameraLookatRequest,
    ) -> ModuleResult[ViewportSetCameraLookatResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_set_camera_lookat({
                "eye": list(request.eye),
                "target": list(request.target),
                "up": list(request.up),
                "viewport_name": request.viewport_name,
                "camera_path": request.camera_path,
            })
            return ok_result(
                ViewportSetCameraLookatResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    camera_path=str(raw.get("camera_path", "")),
                    eye=tuple(raw.get("eye", request.eye)),
                    target=tuple(raw.get("target", request.target)),
                    up=tuple(raw.get("up", request.up)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_SET_CAMERA_LOOKAT_ERROR",
            )

    async def focus_prim(
        self, meta: OperationMeta, request: ViewportFocusPrimRequest,
    ) -> ModuleResult[ViewportFocusPrimResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_focus_prim({
                "prim_path": request.prim_path,
                "viewport_name": request.viewport_name,
                "camera_path": request.camera_path,
                "padding": request.padding,
                "select": request.select,
            })
            return ok_result(
                ViewportFocusPrimResult(
                    ok=bool(raw.get("ok", True)),
                    prim_path=str(raw.get("prim_path", request.prim_path)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    camera_path=str(raw.get("camera_path", "")),
                    method=str(raw.get("method", "")),
                    target=tuple(raw.get("target", (0.0, 0.0, 0.0))),
                    eye=tuple(raw["eye"]) if raw.get("eye") is not None else None,
                    bbox_min=tuple(raw["bbox_min"]) if raw.get("bbox_min") is not None else None,
                    bbox_max=tuple(raw["bbox_max"]) if raw.get("bbox_max") is not None else None,
                    radius=float(raw.get("radius", 0.0)),
                    selected=bool(raw.get("selected", request.select)),
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_FOCUS_PRIM_ERROR",
            )

    async def project_points(
        self, meta: OperationMeta, request: ViewportProjectPointsRequest,
    ) -> ModuleResult[ViewportProjectPointsResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_project_points({
                "points": [list(point) for point in request.points],
                "viewport_name": request.viewport_name,
                "camera_path": request.camera_path,
                "width": request.width,
                "height": request.height,
            })
            points = tuple(
                ViewportProjectedPoint(
                    world=tuple(item.get("world", (0.0, 0.0, 0.0))),
                    ndc_xy=tuple(item.get("ndc_xy", (0.0, 0.0))),
                    pixel_xy=tuple(item.get("pixel_xy", (0.0, 0.0))),
                    depth=item.get("depth"),
                    in_front=bool(item.get("in_front", False)),
                    in_frame=bool(item.get("in_frame", False)),
                )
                for item in raw.get("points", [])
            )
            return ok_result(
                ViewportProjectPointsResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    camera_path=str(raw.get("camera_path", "")),
                    width=int(raw.get("width", request.width)),
                    height=int(raw.get("height", request.height)),
                    points=points,  # type: ignore[arg-type]
                ),
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_PROJECT_POINTS_ERROR",
            )

    async def frame_prims(
        self, meta: OperationMeta, request: ViewportFramePrimsRequest,
    ) -> ModuleResult[ViewportFramePrimsResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.viewport_frame_prims({
                "prim_paths": list(request.prim_paths),
                "viewport_name": request.viewport_name,
                "camera_path": request.camera_path,
                "include_purposes": list(request.include_purposes),
                "margin": request.margin,
                "fov_deg": request.fov_deg,
                "view_direction": list(request.view_direction),
                "up": list(request.up),
                "set_camera": request.set_camera,
            })
            return ok_result(
                ViewportFramePrimsResult(
                    ok=bool(raw.get("ok", True)),
                    viewport_name=str(raw.get("viewport_name", request.viewport_name)),
                    camera_path=str(raw.get("camera_path", "")),
                    prim_paths=tuple(raw.get("prim_paths", request.prim_paths)),
                    eye=tuple(raw.get("eye", (0.0, 0.0, 0.0))),
                    target=tuple(raw.get("target", (0.0, 0.0, 0.0))),
                    up=tuple(raw.get("up", request.up)),
                    fov_deg=float(raw.get("fov_deg", request.fov_deg)),
                    distance=float(raw.get("distance", 0.0)),
                    combined_bbox=dict(raw.get("combined_bbox", {})),
                    prim_bboxes=tuple(raw.get("prim_bboxes", ())),
                ),  # type: ignore[arg-type]
                started_ms=started,
            )
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started,
                error_code="VIEWPORT_FRAME_PRIMS_ERROR",
            )

    async def capture_assert(
        self, meta: OperationMeta, request: ViewportCaptureAssertRequest,
    ) -> ModuleResult[ViewportCaptureAssertResult]:
        started = int(time.time() * 1000)
        capture = await self.capture(
            meta,
            ViewportCaptureRequest(
                viewport_name=request.viewport_name,
                camera_prim_path=request.camera_prim_path,
                renderer=request.renderer,
                width=request.width,
                height=request.height,
                samples_per_pixel=request.samples_per_pixel,
                settle_frames=request.settle_frames,
                output_format=request.output_format,
                transparent_background=request.transparent_background,
                warmup_frames=request.warmup_frames,
                return_stats=True,
            ),
        )
        if capture.data is None:
            return error_result(
                capture.message or "Viewport capture failed",
                started_ms=started,
                error_code=capture.error_code or "VIEWPORT_CAPTURE_ASSERT_ERROR",
            )

        artifact = capture.data
        failures: list[str] = []
        mean_avg = (
            sum(artifact.pixel_mean) / len(artifact.pixel_mean)
            if artifact.pixel_mean else None
        )
        variance_avg = (
            sum(artifact.pixel_variance) / len(artifact.pixel_variance)
            if artifact.pixel_variance else None
        )
        if mean_avg is None:
            failures.append("PIXEL_MEAN_MISSING")
        elif mean_avg < request.min_mean:
            failures.append("PIXEL_MEAN_BELOW_THRESHOLD")
        if variance_avg is None:
            failures.append("PIXEL_VARIANCE_MISSING")
        elif variance_avg < request.min_variance:
            failures.append("PIXEL_VARIANCE_BELOW_THRESHOLD")

        data = ViewportCaptureAssertResult(
            passed=not failures,
            artifact=artifact,
            pixel_mean_average=mean_avg,
            pixel_variance_average=variance_avg,
            failure_codes=tuple(failures),
            diagnostics=(
                _capture_assert_diagnostics(
                    request=request,
                    failure_codes=tuple(failures),
                    pixel_mean_average=mean_avg,
                    pixel_variance_average=variance_avg,
                )
                if failures else {}
            ),
        )
        if data.passed:
            return ok_result(data, started_ms=started, artifacts={"image": artifact.path})
        return fail_result(
            "Viewport capture assertion failed",
            started_ms=started,
            data=data,
            error_code="VIEWPORT_CAPTURE_ASSERT_FAILED",
        )


def _capture_assert_diagnostics(
    *,
    request: ViewportCaptureAssertRequest,
    failure_codes: tuple[str, ...],
    pixel_mean_average: float | None,
    pixel_variance_average: float | None,
) -> dict[str, JsonValue]:
    reason = _capture_assert_failure_reason(failure_codes)
    diagnostics: dict[str, JsonValue] = {
        "reason": reason,
        "failure_codes": list(failure_codes),
        "pixel_mean_average": pixel_mean_average,
        "pixel_variance_average": pixel_variance_average,
        "min_mean": request.min_mean,
        "min_variance": request.min_variance,
        "suggested_next": _capture_assert_suggested_next(reason),
        "fallback_tool_order": [
            "simulation_get_status",
            "viewport_frame_prims",
            "viewport_capture_assert",
            "extension_capture_logs",
        ],
    }
    return diagnostics


def _capture_assert_failure_reason(failure_codes: tuple[str, ...]) -> str:
    codes = set(failure_codes)
    if {"PIXEL_MEAN_MISSING", "PIXEL_VARIANCE_MISSING"} & codes:
        return "capture_stats_missing"
    if {
        "PIXEL_MEAN_BELOW_THRESHOLD",
        "PIXEL_VARIANCE_BELOW_THRESHOLD",
    } <= codes:
        return "capture_blank_or_flat"
    if "PIXEL_MEAN_BELOW_THRESHOLD" in codes:
        return "capture_too_dark"
    if "PIXEL_VARIANCE_BELOW_THRESHOLD" in codes:
        return "capture_flat_or_unframed"
    return "capture_assert_failed"


def _capture_assert_suggested_next(reason: str) -> list[str]:
    suggestions = {
        "capture_stats_missing": [
            "Retry viewport_capture_assert so the capture path returns pixel statistics.",
            "If stats stay missing, run viewport_capture(return_stats=true) and inspect the raw response.",
        ],
        "capture_blank_or_flat": [
            "Frame the target prims with viewport_frame_prims, then retry viewport_capture_assert with warmup_frames > 0.",
            "Add or brighten a DomeLight or DistantLight before retrying if the frame remains dark.",
        ],
        "capture_too_dark": [
            "Add or brighten scene lighting, then retry viewport_capture_assert with warmup_frames > 0.",
            "Inspect the capture artifact before lowering min_mean.",
        ],
        "capture_flat_or_unframed": [
            "Use viewport_frame_prims on the target prims before retrying viewport_capture_assert.",
            "Inspect the capture artifact for off-camera, occluded, or single-color frames before lowering min_variance.",
        ],
        "capture_assert_failed": [
            "Inspect failure_codes, pixel_mean_average, and pixel_variance_average before adjusting thresholds.",
            "Capture extension WARN/ERROR logs if repeated retries produce the same failure codes.",
        ],
    }
    return suggestions.get(reason, suggestions["capture_assert_failed"])
