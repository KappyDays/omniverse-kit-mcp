"""Preview image capture helpers for camera comparison UI."""

from __future__ import annotations

import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_CAPTURE_DIMENSION = 4096
MAX_CAMERA_SLUG_LENGTH = 96
DEFAULT_CAPTURE_SETTLE_SECONDS = 0.3


@dataclass(slots=True, frozen=True)
class CaptureResult:
    """Result of one camera preview capture attempt."""

    camera_path: str
    image_path: str
    width: int
    height: int
    error: str = ""


def choose_display_kind(result: CaptureResult) -> str:
    """Return the UI display mode for a capture result."""
    if result.image_path:
        return "image"
    return "fallback"


class PreviewCapture:
    """Capture preview PNGs for one or more USD cameras."""

    def __init__(
        self,
        settle_seconds: float = DEFAULT_CAPTURE_SETTLE_SECONDS,
        allow_viewport_fallback: bool = False,
    ) -> None:
        self.settle_seconds = max(0.0, float(settle_seconds))
        self.allow_viewport_fallback = bool(allow_viewport_fallback)

    def set_allow_viewport_fallback(self, enabled: bool) -> None:
        self.allow_viewport_fallback = bool(enabled)

    async def capture_many(
        self,
        camera_paths: list[str],
        width: int,
        height: int,
    ) -> list[CaptureResult]:
        """Capture previews in the same order as ``camera_paths``."""
        results: list[CaptureResult] = []
        for camera_path in camera_paths:
            try:
                results.append(await self.capture_one(camera_path, width, height))
            except Exception as exc:  # noqa: BLE001
                clean_camera_path = _clean_camera_path(camera_path)
                clean_width, clean_height, _ = _coerce_dimensions(width, height)
                results.append(
                    CaptureResult(
                        camera_path=clean_camera_path,
                        image_path="",
                        width=clean_width,
                        height=clean_height,
                        error=f"capture failed: {type(exc).__name__}: {exc}",
                    )
                )
        return results

    async def capture_one(
        self,
        camera_path: str,
        width: int,
        height: int,
    ) -> CaptureResult:
        """Capture one camera preview without letting backend failures escape."""
        clean_camera_path = _clean_camera_path(camera_path)
        clean_width, clean_height, dimension_error = _coerce_dimensions(width, height)
        if dimension_error:
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path="",
                width=clean_width,
                height=clean_height,
                error=dimension_error,
            )

        try:
            image_path = self._make_temp_png_path(
                clean_camera_path,
                clean_width,
                clean_height,
            )
        except Exception as exc:  # noqa: BLE001
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path="",
                width=clean_width,
                height=clean_height,
                error=f"temp path failed: {type(exc).__name__}: {exc}",
            )

        errors: list[str] = []

        try:
            captured_path = await self._capture_with_replicator(
                clean_camera_path,
                clean_width,
                clean_height,
                image_path,
            )
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path=captured_path,
                width=clean_width,
                height=clean_height,
            )
        except ImportError as exc:
            errors.append(_format_backend_error("replicator failed", exc))
        except Exception as exc:  # noqa: BLE001
            errors.append(_format_backend_error("replicator failed", exc))

        if self.allow_viewport_fallback:
            try:
                captured_path = await self._capture_with_viewport(
                    clean_camera_path,
                    clean_width,
                    clean_height,
                    image_path,
                )
                return CaptureResult(
                    camera_path=clean_camera_path,
                    image_path=captured_path,
                    width=clean_width,
                    height=clean_height,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(_format_backend_error("viewport fallback failed", exc))
        else:
            errors.append("viewport fallback disabled")

        return CaptureResult(
            camera_path=clean_camera_path,
            image_path="",
            width=clean_width,
            height=clean_height,
            error=" | ".join(errors) if errors else "capture failed",
        )

    def _make_temp_png_path(self, camera_path: str, width: int, height: int) -> str:
        output_dir = Path(tempfile.gettempdir()) / "usd_mouse_interact_demo_previews"
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = _camera_slug(camera_path)
        filename = f"{slug}_{int(width)}x{int(height)}_{uuid.uuid4().hex[:12]}.png"
        return (output_dir / filename).as_posix()

    async def capture_active_viewport(
        self,
        camera_path: str,
        width: int,
        height: int,
    ) -> CaptureResult:
        """Capture the current active viewport without switching cameras."""
        clean_camera_path = _clean_camera_path(camera_path)
        clean_width, clean_height, dimension_error = _coerce_dimensions(width, height)
        if dimension_error:
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path="",
                width=clean_width,
                height=clean_height,
                error=dimension_error,
            )
        try:
            image_path = self._make_temp_png_path(
                clean_camera_path,
                clean_width,
                clean_height,
            )
            captured_path = await self._capture_current_active_viewport_to_file(image_path)
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path=captured_path,
                width=clean_width,
                height=clean_height,
            )
        except Exception as exc:  # noqa: BLE001
            return CaptureResult(
                camera_path=clean_camera_path,
                image_path="",
                width=clean_width,
                height=clean_height,
                error=f"active viewport capture failed: {type(exc).__name__}: {exc}",
            )

    async def _capture_with_replicator(
        self,
        camera_path: str,
        width: int,
        height: int,
        image_path: str,
    ) -> str:
        """Capture through Replicator render products."""
        import omni.replicator.core as rep  # type: ignore[import-not-found] # noqa: WPS433

        render_product = None
        rgb_annotator = None
        attached = False
        try:
            render_product = rep.create.render_product(camera_path, (width, height))
            rgb_annotator = rep.AnnotatorRegistry.get_annotator("rgb")
            rgb_annotator.attach([render_product])
            attached = True
            await _wait_seconds(self.settle_seconds)
            data = await _read_annotator_data_without_orchestrator_step(rgb_annotator)
            _save_rgb_png(data, image_path)
            return image_path
        finally:
            if attached and rgb_annotator is not None and render_product is not None:
                try:
                    rgb_annotator.detach([render_product])
                except Exception:  # noqa: BLE001
                    pass
            _destroy_render_product(rep, render_product)

    async def _capture_with_viewport(
        self,
        camera_path: str,
        width: int,
        height: int,
        image_path: str,
    ) -> str:
        """Capture through active viewport utility while restoring camera state."""
        import omni.kit.app  # type: ignore[import-not-found] # noqa: WPS433
        from omni.kit.viewport.utility import (  # type: ignore[import-not-found] # noqa: WPS433
            capture_viewport_to_file,
            get_active_viewport,
        )

        from .viewport_camera import ViewportCameraSwitcher  # noqa: WPS433

        stage = _get_current_stage()
        if not _camera_prim_exists(stage, camera_path):
            raise RuntimeError(f"camera prim not found: {camera_path}")

        switcher = ViewportCameraSwitcher()
        switcher.save_current()
        app = omni.kit.app.get_app()
        try:
            if camera_path and not switcher.set_active_camera(camera_path, stage=stage):
                raise RuntimeError(f"viewport rejected camera path: {camera_path}")

            await _wait_seconds(self.settle_seconds, app=app)

            viewport = get_active_viewport()
            if viewport is None:
                raise RuntimeError("get_active_viewport() returned None")

            capture = capture_viewport_to_file(viewport, image_path)
            if capture is not None and hasattr(capture, "wait"):
                await capture.wait()

            for _ in range(40):
                if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                    return image_path
                await app.next_update_async()

            if not os.path.exists(image_path):
                raise RuntimeError(f"capture_viewport_to_file did not produce {image_path}")
            raise RuntimeError(f"capture_viewport_to_file produced an empty file: {image_path}")
        finally:
            switcher.restore_saved()

    async def _capture_current_active_viewport_to_file(self, image_path: str) -> str:
        import omni.kit.app  # type: ignore[import-not-found] # noqa: WPS433
        from omni.kit.viewport.utility import (  # type: ignore[import-not-found] # noqa: WPS433
            capture_viewport_to_file,
            get_active_viewport,
        )

        app = omni.kit.app.get_app()
        await _wait_seconds(self.settle_seconds, app=app)
        viewport = get_active_viewport()
        if viewport is None:
            raise RuntimeError("get_active_viewport() returned None")

        capture = capture_viewport_to_file(viewport, image_path)
        if capture is not None and hasattr(capture, "wait"):
            await capture.wait()

        for _ in range(40):
            if os.path.exists(image_path) and os.path.getsize(image_path) > 0:
                return image_path
            await app.next_update_async()
        if not os.path.exists(image_path):
            raise RuntimeError(f"capture_viewport_to_file did not produce {image_path}")
        raise RuntimeError(f"capture_viewport_to_file produced an empty file: {image_path}")


def _clean_camera_path(camera_path: str) -> str:
    return str(camera_path).strip() if camera_path is not None else ""


def _coerce_dimensions(width: int, height: int) -> tuple[int, int, str]:
    clean_width = _coerce_int(width)
    clean_height = _coerce_int(height)
    if clean_width <= 0 or clean_height <= 0:
        return (
            clean_width,
            clean_height,
            f"invalid capture dimensions: width={clean_width}, height={clean_height}",
        )
    if clean_width > MAX_CAPTURE_DIMENSION or clean_height > MAX_CAPTURE_DIMENSION:
        return (
            clean_width,
            clean_height,
            "capture dimensions exceed maximum "
            f"{MAX_CAPTURE_DIMENSION}: width={clean_width}, height={clean_height}",
        )
    return clean_width, clean_height, ""


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return 0


def _format_backend_error(label: str, exc: BaseException) -> str:
    return f"{label}: {type(exc).__name__}: {exc}"


def _camera_slug(camera_path: str) -> str:
    stripped = str(camera_path).strip().strip("/") or "camera"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", stripped).strip("_")
    slug = slug or "camera"
    if len(slug) <= MAX_CAMERA_SLUG_LENGTH:
        return slug
    head_length = MAX_CAMERA_SLUG_LENGTH // 2
    tail_length = MAX_CAMERA_SLUG_LENGTH - head_length - 1
    return f"{slug[:head_length].rstrip('_')}_{slug[-tail_length:].lstrip('_')}"


def _destroy_render_product(rep: Any, render_product: Any) -> None:
    if render_product is None:
        return

    for method_name in ("destroy", "release"):
        method = getattr(render_product, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:  # noqa: BLE001
                pass

    rep_destroy = getattr(rep, "destroy", None)
    if callable(rep_destroy):
        try:
            rep_destroy(render_product)
        except Exception:  # noqa: BLE001
            pass


def _save_rgb_png(data: Any, image_path: str) -> None:
    if data is None or not hasattr(data, "shape") or getattr(data, "size", 0) == 0:
        raise RuntimeError(
            f"replicator returned empty image data shape={getattr(data, 'shape', None)}"
        )

    try:
        from PIL import Image  # noqa: WPS433
    except ImportError as exc:
        raise RuntimeError(f"PIL unavailable for PNG encode: {exc}") from exc

    try:
        rgb = data[:, :, :3].astype("uint8")
        image = Image.fromarray(rgb)
        image.save(image_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"failed to save replicator PNG: {exc}") from exc


async def _read_annotator_data_without_orchestrator_step(rgb_annotator: Any) -> Any:
    app = _get_app()
    last_data = None
    for _ in range(30):
        if app is not None:
            await app.next_update_async()
        data = rgb_annotator.get_data()
        last_data = data
        if data is not None and hasattr(data, "shape") and getattr(data, "size", 0) > 0:
            return data
    return last_data


def _get_current_stage():
    try:
        import omni.usd as omni_usd  # type: ignore[import-not-found] # noqa: WPS433

        return omni_usd.get_context().get_stage()
    except Exception:  # noqa: BLE001
        return None


def _camera_prim_exists(stage: Any, camera_path: str) -> bool:
    if not camera_path:
        return False
    if stage is None:
        return True
    try:
        prim = stage.GetPrimAtPath(camera_path)
        return bool(prim and prim.IsValid())
    except Exception:  # noqa: BLE001
        return True


async def _wait_seconds(seconds: float, app: Any | None = None) -> None:
    if seconds <= 0:
        return
    if app is None:
        try:
            import omni.kit.app as omni_kit_app  # type: ignore[import-not-found] # noqa: WPS433

            app = omni_kit_app.get_app()
        except Exception:  # noqa: BLE001
            app = None
    if app is None:
        return
    end_time = time.monotonic() + float(seconds)
    while time.monotonic() < end_time:
        await app.next_update_async()


def _get_app() -> Any | None:
    try:
        import omni.kit.app as omni_kit_app  # type: ignore[import-not-found] # noqa: WPS433

        return omni_kit_app.get_app()
    except Exception:  # noqa: BLE001
        return None
