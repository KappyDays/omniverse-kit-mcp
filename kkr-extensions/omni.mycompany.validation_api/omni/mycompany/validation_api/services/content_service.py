"""Content browser service — omni.client list / stat / normalize wrappers (Phase H)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ContentService:
    """Thin async wrapper around ``omni.client``.

    ``omni.client`` functions are synchronous I/O; we hop to a worker
    thread so the FastAPI event loop is not blocked on Nucleus / S3
    latency. All entries come back as JSON-friendly dicts (no Pixar /
    numpy types) for MCP consumption.
    """

    async def browse(self, request: dict[str, Any]) -> dict[str, Any]:
        url = request["url"]
        recursive = bool(request.get("recursive", False))
        max_depth = int(request.get("max_depth", 2))
        max_entries = int(request.get("max_entries", 500))

        backend = "omni.client"
        entries: list[dict[str, Any]] = []
        truncated = False
        try:
            import omni.client  # type: ignore[import-not-found]

            async def _walk(current_url: str, depth: int) -> None:
                nonlocal truncated
                if len(entries) >= max_entries:
                    truncated = True
                    return
                result, listing = await asyncio.to_thread(omni.client.list, current_url)
                if not _is_ok(result):
                    return
                for entry in listing or []:
                    if len(entries) >= max_entries:
                        truncated = True
                        return
                    info = _entry_to_dict(entry, current_url)
                    entries.append(info)
                    if (
                        recursive
                        and depth < max_depth
                        and info.get("is_folder")
                    ):
                        await _walk(info["url"], depth + 1)

            await _walk(url, depth=0)
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        return {
            "ok": True,
            "url": url,
            "recursive": recursive,
            "entries": entries,
            "entry_count": len(entries),
            "truncated": truncated,
            "backend": backend,
        }

    async def preview(self, request: dict[str, Any]) -> dict[str, Any]:
        url = request["url"]
        backend = "omni.client"
        info: dict[str, Any] = {}
        try:
            import omni.client  # type: ignore[import-not-found]

            result, entry = await asyncio.to_thread(omni.client.stat, url)
            if not _is_ok(result) or entry is None:
                raise ValueError(f"stat failed on {url!r} (result={result})")
            info = _entry_to_dict(entry, url.rsplit("/", 1)[0] or url)
            info["url"] = url
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"
            info = {"url": url, "error": str(exc)}

        return {
            "ok": True,
            "url": url,
            "info": info,
            "backend": backend,
        }

    async def inspect(self, request: dict[str, Any]) -> dict[str, Any]:
        """Open a USD asset and return geometric info (bbox / default prim / units).

        ``Usd.Stage.Open`` is synchronous I/O (and may resolve heavy MDL payloads),
        so it runs on a worker thread — the Kit main loop is never blocked
        (deadlock-safe). The stage is independent of the live context stage.
        """
        url = request["url"]

        def _do() -> dict[str, Any]:
            from pxr import Usd, UsdGeom  # lazy — runtime only

            stage = Usd.Stage.Open(url)
            if stage is None:
                raise ValueError(f"could not open USD stage {url!r}")

            default_prim = stage.GetDefaultPrim()
            has_default = bool(default_prim and default_prim.IsValid())
            default_path = default_prim.GetPath().pathString if has_default else ""
            mpu = float(UsdGeom.GetStageMetersPerUnit(stage) or 0.0)
            up_axis = str(UsdGeom.GetStageUpAxis(stage) or "")
            prim_count = sum(1 for _ in stage.Traverse())

            root = default_prim if has_default else stage.GetPseudoRoot()
            bbox_min = bbox_max = None
            try:
                cache = UsdGeom.BBoxCache(
                    Usd.TimeCode.Default(),
                    [UsdGeom.Tokens.default_, UsdGeom.Tokens.render],
                )
                rng = cache.ComputeWorldBound(root).ComputeAlignedRange()
                if not rng.IsEmpty():
                    mn, mx = rng.GetMin(), rng.GetMax()
                    bbox_min = [float(mn[0]), float(mn[1]), float(mn[2])]
                    bbox_max = [float(mx[0]), float(mx[1]), float(mx[2])]
            except Exception:  # noqa: BLE001
                pass  # bbox best-effort; metadata still useful

            return {
                "default_prim": default_path,
                "bbox_min": bbox_min,
                "bbox_max": bbox_max,
                "meters_per_unit": mpu,
                "up_axis": up_axis,
                "prim_count": int(prim_count),
            }

        try:
            data = await asyncio.to_thread(_do)
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False, "url": url, "default_prim": "", "bbox_min": None,
                "bbox_max": None, "meters_per_unit": 0.0, "up_axis": "",
                "prim_count": 0, "backend": f"fallback:{type(exc).__name__}",
                "error": str(exc),
            }

        return {"ok": True, "url": url, "backend": "usd", **data}

    async def resolve(self, request: dict[str, Any]) -> dict[str, Any]:
        url = request["url"]
        backend = "omni.client"
        resolved = url
        try:
            import omni.client  # type: ignore[import-not-found]

            normalize = getattr(omni.client, "normalize_url", None)
            if normalize is not None:
                resolved = await asyncio.to_thread(normalize, url)
            else:
                # older Kit builds — fall back to make_absolute_url
                make_abs = getattr(omni.client, "make_absolute_url", None)
                if make_abs is not None:
                    resolved = await asyncio.to_thread(make_abs, "", url)
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        return {
            "ok": True,
            "url": url,
            "resolved": str(resolved) if resolved is not None else url,
            "backend": backend,
        }


def _is_ok(result: Any) -> bool:
    """omni.client.Result is an Enum — OK == 0 / "OK" across builds."""
    if result is None:
        return False
    name = getattr(result, "name", None)
    if name is not None:
        return name == "OK"
    try:
        return int(result) == 0
    except Exception:  # noqa: BLE001
        return False


def _entry_to_dict(entry: Any, parent_url: str) -> dict[str, Any]:
    """Convert an omni.client.ListEntry to a JSON-friendly dict."""
    relative_path = getattr(entry, "relative_path", None) or ""
    # Flags bitfield — bit 4 == "can have children" (folder) in omni.client
    flags = int(getattr(entry, "flags", 0) or 0)
    is_folder = bool(flags & (1 << 4))
    size = getattr(entry, "size", None)
    modified_ns = getattr(entry, "modified_time_ns", None)
    parent = parent_url.rstrip("/")
    full_url = f"{parent}/{relative_path}" if relative_path else parent_url
    return {
        "url": full_url,
        "name": relative_path,
        "is_folder": is_folder,
        "size": int(size) if size is not None else None,
        "modified_time_ns": int(modified_ns) if modified_ns is not None else None,
        "flags": flags,
    }
