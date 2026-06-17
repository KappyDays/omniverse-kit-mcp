"""Asset service — GUI Asset Browser equivalent (list Isaac Sim asset catalog).

Mirrors the default folder configuration of ``isaacsim.asset.browser`` so MCP
consumers can browse the same Robots / Environments / Props / ... tree a
human user sees in the GUI. The root URL is resolved via
``isaacsim.storage.native.get_assets_root_path()`` — in Isaac Sim 6.0 that
points to a public S3 bucket by default, so no Nucleus connection is needed.

All omni.*/isaacsim.* imports are lazy (inside functions) per Extension
API rule #7.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_MARKER = ".omniverse-kit-mcp"
_EXTERNAL_ASSET_DIR = "external_assets"

# Matches exts/isaacsim.asset.browser/config/extension.toml `folders` list.
# Mirror here so the MCP catalog surface stays stable even if the browser
# extension reorders/renames its roots.
_CATEGORIES: dict[str, str] = {
    "robots": "/Isaac/Robots",
    "environments": "/Isaac/Environments",
    "props": "/Isaac/Props",
    "people": "/Isaac/People",
    "materials": "/Isaac/Materials",
    "isaaclab": "/Isaac/IsaacLab",
}


class AssetService:
    """Read-only catalog of assets reachable from the configured assets root."""

    async def list(
        self,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> dict[str, Any]:
        root = self._resolve_root()

        if category is None:
            return {
                "ok": True,
                "assets_root": root,
                "categories": [
                    {"name": name, "url": f"{root}{path}"}
                    for name, path in _CATEGORIES.items()
                ],
            }

        if category not in _CATEGORIES:
            raise ValueError(
                f"Unknown asset category '{category}' — "
                f"available: {sorted(_CATEGORIES)}"
            )

        base = f"{root}{_CATEGORIES[category]}"
        target = self._join_url(base, subpath)

        items = await self._list_url(
            target,
            recursive=recursive,
            max_depth=max_depth,
            max_entries=max_entries,
        )

        return {
            "ok": True,
            "category": category,
            "subpath": subpath,
            "base_url": base,
            "target_url": target,
            "items": items,
            "count": len(items),
        }

    async def convert_external_asset(self, request: dict[str, Any]) -> dict[str, Any]:
        """Convert a downloaded local asset to USD without adding it to the stage."""
        started = time.time()
        input_path = Path(str(request.get("input_path", ""))).expanduser().resolve()
        output_path = Path(str(request.get("output_path", ""))).expanduser().resolve()
        output_format = str(request.get("output_format") or "usd").lower().lstrip(".")
        timeout_s = float(request.get("timeout_s") or 180.0)

        if output_format != "usd":
            raise ValueError("external asset conversion v1 only supports output_format='usd'")
        if not input_path.is_file():
            raise ValueError(f"input_path does not exist or is not a file: {input_path}")
        if not _is_external_asset_cache_path(input_path):
            raise ValueError(
                "input_path must be inside .omniverse-kit-mcp/external_assets"
            )
        if not _is_external_asset_cache_path(output_path):
            raise ValueError(
                "output_path must be inside .omniverse-kit-mcp/external_assets"
            )
        if output_path.parent != input_path.parent:
            raise ValueError("output_path must stay in the source asset cache folder")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            import omni.kit.asset_converter as asset_converter  # lazy
        except Exception as exc:
            return {
                "ok": False,
                "status": "unsupported",
                "error_code": "ASSET_CONVERTER_UNAVAILABLE",
                "message": str(exc),
                "input_path": str(input_path),
                "output_path": str(output_path),
                "elapsed_s": round(time.time() - started, 3),
            }

        context = asset_converter.AssetConverterContext()
        for attr, value in {
            "ignore_materials": False,
            "ignore_animations": False,
            "single_mesh": False,
            "embed_textures": False,
            "convert_fbx_to_y_up": False,
            "convert_fbx_to_z_up": True,
            "use_meter_as_world_unit": True,
        }.items():
            if hasattr(context, attr):
                setattr(context, attr, value)

        progress: list[dict[str, Any]] = []

        def on_progress(current_step: int, total: int) -> None:
            progress.append({"current_step": current_step, "total": total})

        manager = asset_converter.get_instance()
        task = manager.create_converter_task(
            str(input_path),
            str(output_path),
            on_progress,
            context,
        )

        try:
            success = await asyncio.wait_for(task.wait_until_finished(), timeout=timeout_s)
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "status": "timeout",
                "error_code": "ASSET_CONVERT_TIMEOUT",
                "input_path": str(input_path),
                "output_path": str(output_path),
                "timeout_s": timeout_s,
                "elapsed_s": round(time.time() - started, 3),
                "progress": progress[-10:],
            }

        return {
            "ok": bool(success),
            "status": "converted" if success else "failed",
            "input_path": str(input_path),
            "output_path": str(output_path),
            "output_exists": output_path.exists(),
            "elapsed_s": round(time.time() - started, 3),
            "progress": progress[-10:],
        }

    # ------------------------------------------------------------------

    def _resolve_root(self) -> str:
        from isaacsim.storage.native import get_assets_root_path  # lazy

        root = get_assets_root_path()
        if not root:
            raise RuntimeError(
                "Isaac Sim assets root is not resolved. Check network reachability "
                "(default uses the public S3 bucket) or set a Nucleus mount."
            )
        return root.rstrip("/")

    @staticmethod
    def _join_url(base: str, subpath: str) -> str:
        if not subpath:
            return base
        return f"{base.rstrip('/')}/{subpath.strip('/')}"

    async def _list_url(
        self,
        url: str,
        *,
        recursive: bool,
        max_depth: int,
        max_entries: int,
    ) -> list[dict[str, Any]]:
        import omni.client  # lazy

        def _sync_list() -> tuple[Any, Any]:
            return omni.client.list(url)

        result, entries = await asyncio.to_thread(_sync_list)
        if result != omni.client.Result.OK:
            raise RuntimeError(f"omni.client.list failed: {url} → {result}")

        items: list[dict[str, Any]] = []
        for entry in entries or []:
            if len(items) >= max_entries:
                break
            name = (entry.relative_path or "").rstrip("/")
            if not name:
                continue
            is_folder = bool(
                entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN
            )
            item = {
                "name": name,
                "url": f"{url.rstrip('/')}/{name}",
                "is_folder": is_folder,
                "size": None if is_folder else getattr(entry, "size", None),
            }
            items.append(item)
            if recursive and is_folder and max_depth > 0 and len(items) < max_entries:
                try:
                    sub_items = await self._list_url(
                        item["url"],
                        recursive=True,
                        max_depth=max_depth - 1,
                        max_entries=max_entries - len(items),
                    )
                    items.extend(sub_items)
                except Exception as exc:
                    logger.debug("skip recurse %s: %s", item["url"], exc)
        return items


def _is_external_asset_cache_path(path: Path) -> bool:
    parts = [part.lower() for part in path.resolve().parts]
    marker = _CACHE_MARKER.lower()
    cache_dir = _EXTERNAL_ASSET_DIR.lower()
    return any(
        part == marker and index + 1 < len(parts) and parts[index + 1] == cache_dir
        for index, part in enumerate(parts)
    )
