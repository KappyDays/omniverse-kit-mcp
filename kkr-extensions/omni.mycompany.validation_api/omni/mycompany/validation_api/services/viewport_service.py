"""Viewport service — screenshot capture and SSIM comparison.

All omni.*/pxr.* imports are lazy (inside functions) per API rule #7.
Uses omni.replicator.core for deterministic render-product capture.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Writable output directory for captured images
_OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "validation_api_captures")


class ViewportService:
    """Captures viewport screenshots and compares images via SSIM."""

    async def create(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create (or reuse) a secondary omni.kit.viewport.window (Phase E).

        Tries ``omni.kit.viewport.window.create_viewport_window`` first; if that
        entry point isn't available in the running Kit flavour, falls back to
        ``omni.kit.viewport.utility.create_viewport_window``. Either way, if a
        window with the same title already exists the response is marked
        ``existed=true`` and the window is **not** duplicated.
        """
        import omni.kit.app  # lazy

        viewport_name = request["viewport_name"]
        camera_path = request.get("camera_path")
        width = int(request.get("width", 1280))
        height = int(request.get("height", 720))
        docked = bool(request.get("docked", False))
        if camera_path:
            _ensure_renderable_camera_path(camera_path, context="viewport_create")

        existed = False
        created_window = None

        # Detect pre-existing window via omni.ui workspace first (lazy)
        try:
            import omni.ui as ui
            existing = ui.Workspace.get_window(viewport_name)
            if existing is not None:
                existed = True
                created_window = existing
        except Exception:
            pass

        if not existed:
            try:
                from omni.kit.viewport.window import ViewportWindow
                created_window = ViewportWindow(viewport_name, width=width, height=height)
            except Exception:
                # Fallback path — older Kit deployments expose the helper under
                # ``omni.kit.viewport.utility`` instead of the dedicated module
                try:
                    from omni.kit.viewport.utility import create_viewport_window
                    created_window = create_viewport_window(
                        viewport_name, width=width, height=height,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"create_viewport_window failed — both entry points missing ({exc})"
                    ) from exc

        # Bind camera if requested
        if camera_path:
            try:
                from omni.kit.viewport.utility import get_viewport_from_window_name
                viewport = get_viewport_from_window_name(viewport_name)
                if viewport is not None:
                    viewport.camera_path = camera_path
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "viewport_create: camera bind failed for %s → %s (non-fatal)",
                    viewport_name, exc,
                )

        # Settle a couple of ticks so the new viewport picks up its first frame
        try:
            app = omni.kit.app.get_app()
            for _ in range(3):
                await app.next_update_async()
        except Exception:
            pass

        return {
            "ok": True,
            "viewport_name": viewport_name,
            "existed": existed,
            "camera_path": camera_path,
            "width": width,
            "height": height,
            "docked": docked,
        }

    async def destroy(self, request: dict[str, Any]) -> dict[str, Any]:
        """Destroy a secondary viewport window by name (Phase E). Idempotent."""
        viewport_name = request["viewport_name"]
        destroyed = False
        try:
            import omni.ui as ui
            window = ui.Workspace.get_window(viewport_name)
            if window is not None:
                try:
                    window.visible = False
                except Exception:
                    pass
                destroy_fn = getattr(window, "destroy", None)
                if callable(destroy_fn):
                    destroy_fn()
                    destroyed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "viewport_destroy(%s) failed: %s (non-fatal)", viewport_name, exc,
            )
        return {
            "ok": True,
            "viewport_name": viewport_name,
            "destroyed": destroyed,
        }

    async def set_active_camera(
        self,
        camera_path: str,
        viewport_name: str = "Viewport",
    ) -> dict[str, Any]:
        """Switch the active camera of *viewport_name* (GUI viewport toolbar equivalent)."""
        import omni.usd  # lazy
        from omni.kit.viewport.utility import get_active_viewport, get_viewport_from_window_name

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(camera_path)
        if not prim.IsValid():
            raise ValueError(f"Camera prim not found at {camera_path}")
        _ensure_renderable_camera_path(camera_path, context="viewport_set_active_camera")

        viewport = (
            get_viewport_from_window_name(viewport_name)
            if viewport_name and viewport_name != "Viewport"
            else get_active_viewport()
        ) or get_active_viewport()
        if viewport is None:
            raise RuntimeError("No viewport available (headless mode?)")

        viewport.camera_path = camera_path
        return {
            "ok": True,
            "viewport_name": viewport_name,
            "camera_path": camera_path,
        }

    async def capture(self, request: dict[str, Any]) -> dict[str, Any]:
        """Capture a screenshot from the active viewport."""
        import omni.kit.app  # lazy

        camera_path = request.get("camera_prim_path") or "/OmniverseKit_Persp"
        width = request.get("width", 1280)
        height = request.get("height", 720)
        settle_frames = request.get("settle_frames", 5)
        output_format = request.get("output_format", "png")
        warmup_frames = int(request.get("warmup_frames", 0))
        return_stats = bool(request.get("return_stats", False))
        if request.get("camera_prim_path"):
            _ensure_renderable_camera_path(camera_path, context="viewport_capture")

        # Let renderer settle, then extra warmup ticks to force a cold-RTX frame.
        app = omni.kit.app.get_app()
        for _ in range(settle_frames):
            await app.next_update_async()
        for _ in range(warmup_frames):
            await app.next_update_async()

        # Try replicator API (handles Isaac Sim 5.x HydraTexture return type),
        # falls back to omni.kit.viewport.utility on apps without replicator
        # (USD Composer). Each path collects a diag string so the failure mode
        # is readable instead of generic "empty data".
        #
        # Cold-RTX auto-recover: the RTX path can hand back an all-black frame
        # (mean+variance ~0) for the first lit frame(s) after sim activity even
        # when warmup_frames was set. Detect it and tick extra warmup + re-capture
        # (a few times) instead of returning a useless black PNG.
        import numpy as np
        extra_warmup_used = 0
        data, diag = await _capture_via_replicator(camera_path, width, height)
        for _retry in range(4):
            if data is None or (hasattr(data, "size") and data.size == 0):
                break  # empty handled below
            _rgb = data[:, :, :3].astype("float64")
            if float(_rgb.mean()) > 1.0 or float(_rgb.var()) > 1.0:
                break  # non-black frame
            for _ in range(8):
                await app.next_update_async()
            extra_warmup_used += 8
            data, diag = await _capture_via_replicator(camera_path, width, height)

        if data is None or (hasattr(data, "size") and data.size == 0):
            raise RuntimeError(
                "Viewport capture returned empty data. "
                "Diagnostic: " + (diag or "no specific error captured") + ". "
                "On apps without omni.replicator.core (e.g. USD Composer), use "
                "window_capture(hwnd=...) instead — call window_list to find the "
                "GLFW30 window's hwnd."
            )

        # Save to file
        os.makedirs(_OUTPUT_DIR, exist_ok=True)
        artifact_id = uuid.uuid4().hex[:12]
        filename = f"capture_{artifact_id}.{output_format}"
        filepath = os.path.join(_OUTPUT_DIR, filename).replace("\\", "/")

        _save_image(data, filepath, output_format)

        # Compute hash
        sha = _sha256_file(filepath)

        result = {
            "artifact_id": artifact_id,
            "path": filepath,
            "width": int(data.shape[1]),
            "height": int(data.shape[0]),
            "sha256": sha,
            "created_at_epoch_ms": int(time.time() * 1000),
            "warmup_frames_used": warmup_frames + extra_warmup_used,
        }
        if return_stats:
            rgb = data[:, :, :3].astype("float64")
            result["pixel_mean"] = [float(v) for v in rgb.mean(axis=(0, 1))]
            result["pixel_variance"] = [float(v) for v in rgb.var(axis=(0, 1))]
        return result

    async def compare_ssim(self, request: dict[str, Any]) -> dict[str, Any]:
        """Compute SSIM between two captured images."""
        baseline_path = request["baseline_artifact_path"]
        candidate_path = request["candidate_artifact_path"]
        min_ssim = request.get("min_ssim", 0.99)
        crop = request.get("crop")  # [x, y, w, h] or None

        baseline = _load_image(baseline_path)
        candidate = _load_image(candidate_path)

        if baseline is None:
            raise FileNotFoundError(f"Baseline image not found: {baseline_path}")
        if candidate is None:
            raise FileNotFoundError(f"Candidate image not found: {candidate_path}")

        # Crop if requested
        if crop and len(crop) == 4:
            x, y, w, h = crop
            baseline = baseline[y : y + h, x : x + w]
            candidate = candidate[y : y + h, x : x + w]

        # Resize candidate to match baseline if needed
        if baseline.shape != candidate.shape:
            candidate = _resize_to_match(candidate, baseline.shape)

        score = _compute_ssim(baseline, candidate)

        # Save diff heatmap
        diff_path = None
        if score < 1.0:
            diff_path = _save_diff_heatmap(baseline, candidate)

        return {
            "score": float(score),
            "passed": score >= min_ssim,
            "diff_heatmap_path": diff_path,
            "compared_width": int(baseline.shape[1]),
            "compared_height": int(baseline.shape[0]),
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _ensure_renderable_camera_path(camera_path: str, *, context: str) -> None:
    """Reject non-camera sensor prims before Kit/RTX native code can crash."""
    if not camera_path or camera_path == "/OmniverseKit_Persp":
        return

    import omni.usd
    from pxr import UsdGeom

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")

    prim = stage.GetPrimAtPath(camera_path)
    if not prim.IsValid():
        raise ValueError(f"Camera prim not found at {camera_path}")

    custom = prim.GetCustomData() or {}
    sensor_type = (custom.get("validation_api") or {}).get("sensor_type")
    if sensor_type == "rtx_lidar":
        raise ValueError(
            f"{context}: {camera_path} is an RTX Lidar prim, not a renderable "
            "viewport camera. Use sensor_lidar_get_point_cloud for Lidar data, "
            "or sensor_set_visualization plus a regular camera/viewport capture."
        )
    if not prim.IsA(UsdGeom.Camera):
        raise ValueError(
            f"{context}: camera_path must point to a UsdGeom.Camera prim "
            f"(got {prim.GetTypeName()} at {camera_path})"
        )


def _save_image(data: Any, filepath: str, fmt: str) -> None:
    """Save numpy RGBA array to image file."""
    try:
        from PIL import Image
        img = Image.fromarray(data[:, :, :3].astype("uint8"))
        img.save(filepath)
    except ImportError:
        import numpy as np
        np.save(filepath.replace(f".{fmt}", ".npy"), data)


def _load_image(path: str) -> Any:
    """Load an image from disk as numpy array (H, W, 3)."""
    import numpy as np

    if not os.path.exists(path):
        return None
    if path.endswith(".npy"):
        arr = np.load(path)
        return arr[:, :, :3] if arr.ndim == 3 and arr.shape[2] >= 3 else arr
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
        return np.array(img)
    except ImportError:
        return None


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _resize_to_match(img: Any, target_shape: tuple) -> Any:
    """Resize *img* to match *target_shape* (H, W, C)."""
    try:
        from PIL import Image
        import numpy as np
        pil = Image.fromarray(img)
        pil = pil.resize((target_shape[1], target_shape[0]), Image.LANCZOS)
        return np.array(pil)
    except ImportError:
        return img


def _compute_ssim(a: Any, b: Any) -> float:
    """Compute Structural Similarity Index between two images.

    Tries scikit-image first; falls back to a basic numpy MSE-based metric.
    """
    try:
        from skimage.metrics import structural_similarity
        score = structural_similarity(a, b, channel_axis=2)
        return float(score)
    except ImportError:
        pass

    # Fallback: MSE-based pseudo-SSIM (0 = identical → 1.0 score)
    import numpy as np
    a_f = a.astype(np.float64)
    b_f = b.astype(np.float64)
    mse = float(np.mean((a_f - b_f) ** 2))
    if mse == 0:
        return 1.0
    max_val = 255.0
    # Convert PSNR to a 0-1 range approximation
    import math
    psnr = 10 * math.log10((max_val ** 2) / mse)
    return min(1.0, max(0.0, psnr / 60.0))


async def _capture_via_replicator(camera_path: str, width: int, height: int) -> tuple[Any, str | None]:
    """Capture RGB data via replicator → fallback to viewport.utility.

    Returns (data_or_None, diag_message_or_None). The diag string concatenates
    each capture-path failure so the caller can surface a readable error
    instead of a generic "empty data" message — critical for USD Composer
    where `omni.replicator.core` is absent and the failure mode silently
    falls through.

    Replicator compatibility:
    - `render_product` returns a HydraTexture object; `rgb_annot.detach([rp])`
      crashes in `omni.syntheticdata._get_node_path` because it calls
      `.split()` on the HydraTexture. `get_data()` succeeds *before* detach,
      so we isolate detach in its own try block and drop the exception.
    """
    diags: list[str] = []
    try:
        import omni.replicator.core as rep

        rp = rep.create.render_product(camera_path, (width, height))

        rgb_annot = rep.AnnotatorRegistry.get_annotator("rgb")
        rgb_annot.attach([rp])

        await rep.orchestrator.step_async(rt_subframes=4, pause_timeline=False)

        data = rgb_annot.get_data()

        # Non-fatal: detach can raise AttributeError on some Kit builds due to
        # HydraTexture ↔ syntheticdata incompatibility. Annotator and render
        # product get GC'd when the function returns, so the leak is bounded.
        try:
            rgb_annot.detach([rp])
        except Exception as exc:
            logger.debug("rgb_annot.detach() raised (non-fatal): %s", exc)

        if data is not None and hasattr(data, "shape") and data.size > 0:
            return data, None
        diags.append(f"replicator returned empty/None data shape={getattr(data, 'shape', None)}")
    except ImportError as exc:
        diags.append(f"omni.replicator.core not available: {exc}")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        diags.append(f"replicator path raised {type(exc).__name__}: {exc}")

    # Fallback: omni.kit.viewport.utility capture_viewport_to_file.
    try:
        data, util_diag = await _capture_via_viewport_utility(camera_path, width, height)
        if data is not None and hasattr(data, "shape") and getattr(data, "size", 0) > 0:
            return data, None
        diags.append(f"viewport.utility: {util_diag or 'no data returned'}")
    except ImportError as exc:
        diags.append(f"omni.kit.viewport.utility not available: {exc}")
    except Exception as exc:
        import traceback
        traceback.print_exc()
        diags.append(f"viewport.utility raised {type(exc).__name__}: {exc}")

    return None, " | ".join(diags) if diags else None


async def _capture_via_viewport_utility(camera_path: str, width: int, height: int) -> tuple[Any, str | None]:
    """Fallback capture using omni.kit.viewport.utility — writes to a temp PNG
    then reads it back. Works on Isaac Sim + USD Composer without touching
    syntheticdata.

    Returns (np.array or None, diag_str or None). diag explains why None when
    that happens.
    """
    import numpy as np
    import omni.kit.app

    from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file

    viewport = get_active_viewport()
    if viewport is None:
        return None, "get_active_viewport() returned None (no viewport registered)"

    # Setting camera_path is best-effort — USD Composer uses different camera
    # default conventions than Isaac Sim's /OmniverseKit_Persp. Failure here
    # means we capture whatever camera the active viewport already has.
    if camera_path:
        try:
            viewport.camera_path = camera_path
        except Exception as exc:
            logger.debug("viewport.camera_path set raised (non-fatal): %s", exc)

    # Let renderer settle so the first frame isn't black
    app = omni.kit.app.get_app()
    for _ in range(3):
        await app.next_update_async()

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    tmp_path = os.path.join(_OUTPUT_DIR, f"fallback_{uuid.uuid4().hex[:8]}.png").replace("\\", "/")

    capture = capture_viewport_to_file(viewport, tmp_path)
    # capture_viewport_to_file returns a CaptureHelper whose .wait() awaits completion.
    if capture is not None and hasattr(capture, "wait"):
        try:
            await capture.wait()
        except Exception as exc:
            logger.debug("CaptureHelper.wait() raised: %s", exc)

    # Poll up to ~2s for the file to appear and have non-zero bytes
    poll_count = 0
    for poll_count in range(40):
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            break
        await app.next_update_async()

    if not os.path.exists(tmp_path):
        return None, f"capture_viewport_to_file did not produce {tmp_path} after {poll_count + 1} polls"
    file_size = os.path.getsize(tmp_path)
    if file_size == 0:
        return None, f"capture file is 0-byte after {poll_count + 1} polls (viewport renderer not producing frames?)"

    try:
        from PIL import Image
        img = Image.open(tmp_path).convert("RGB")
        return np.array(img), None
    except Exception as exc:
        return None, f"PIL.Image.open({tmp_path}) raised {type(exc).__name__}: {exc}"


def _save_diff_heatmap(a: Any, b: Any) -> str | None:
    """Save a visual diff heatmap and return its path."""
    try:
        import numpy as np
        os.makedirs(_OUTPUT_DIR, exist_ok=True)
        diff = np.abs(a.astype(np.float64) - b.astype(np.float64))
        diff_norm = (diff / diff.max() * 255).astype(np.uint8) if diff.max() > 0 else diff.astype(np.uint8)
        heatmap_id = uuid.uuid4().hex[:8]
        path = os.path.join(_OUTPUT_DIR, f"diff_{heatmap_id}.png").replace("\\", "/")
        _save_image(diff_norm, path, "png")
        return path
    except Exception:
        return None
