"""Viewport module — screenshot capture and SSIM comparison."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, fail_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.stage import ViewportActiveCameraResult
from omniverse_kit_mcp.types.viewport import (
    ImageArtifact,
    SSIMComparisonRequest,
    SSIMComparisonResult,
    ViewportCaptureRequest,
    ViewportCreateRequest,
    ViewportCreateResult,
    ViewportDestroyRequest,
    ViewportDestroyResult,
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
