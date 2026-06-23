"""Asset module — live catalog listing (Phase B+) + offline catalog search.

``list`` browses the live S3 catalog through the Extension (Isaac must be up).
``search`` is fully **offline**: it reads the curated markdown catalog under
``docs/assets/isaac/`` directly in the MCP server process, ranks entries, and
returns concrete USD URLs — usable at planning time without Isaac running.
``official_*`` reads generated NVIDIA official browser-extension snapshots from
``docs/references/official-assets/`` and can verify one entry on demand.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.modules.external_asset import ExternalAssetRegistry
from omniverse_kit_mcp.types.asset import AssetCategory, AssetItem, AssetListResult
from omniverse_kit_mcp.types.common import ExecutionStatus, ModuleResult, OperationMeta

logger = logging.getLogger(__name__)

# Project-root-relative default catalog dir (…/docs/assets/isaac).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CATALOG_DIR = _PROJECT_ROOT / "docs" / "assets" / "isaac"
_DEFAULT_OFFICIAL_CATALOG_DIR = (
    _PROJECT_ROOT / "docs" / "references" / "official-assets"
)

# Curated per-category catalog files (stems double as the `category` value).
_CATEGORY_FILES = ("robots", "environments", "people", "props", "simready", "other")

# `$VAR` = `https://…`  prefix declaration (line-anchored, mirrors the format
# contract guarded by tests/unit/test_asset_inventory_integrity.py).
_PREFIX_RE = re.compile(r"^`(\$\w+)`\s*=\s*`(https?://[^`]+)`", re.MULTILINE)
# Root: `$VAR/path/`  section-root declaration.
_ROOT_RE = re.compile(r"^(?:루트|Root):\s*`(\$\w+/[^`]*?)/?`")
# Any backtick-quoted token.
_BACKTICK_RE = re.compile(r"`([^`]+)`")
# Markdown heading.
_HEADING_RE = re.compile(r"^#{1,6}\s")
# Bold-stripped value (e.g. **Simple_Warehouse** → Simple_Warehouse).
_BOLD_RE = re.compile(r"\*+")
# Plausible SimReady prose asset name (lowercase props, ranges/variants allowed).
_SIMREADY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*[a-z0-9_~/,. ]*$")
_OFFICIAL_STATUS_RANK = {
    "failed": -1,
    "stale": -1,
    "discovered": 0,
    "url_validated": 1,
    "inspect_verified": 2,
    "load_verified": 3,
    "assign_verified": 3,
}
OFFICIAL_ASSET_LOAD_VERIFIED_QUALITIES = frozenset(
    {"valid", "content_verified_no_bbox"}
)
_OFFICIAL_MAX_AGE_DAYS = int(
    os.environ.get("OFFICIAL_ASSET_CATALOG_MAX_AGE_DAYS", "30")
)


class AssetModule:
    def __init__(
        self,
        client: IsaacRestClient,
        catalog_dir: Path | None = None,
        external_assets: ExternalAssetRegistry | None = None,
        official_catalog_dir: Path | None = None,
    ) -> None:
        self._client = client
        self._catalog_dir = catalog_dir or _DEFAULT_CATALOG_DIR
        self._external_assets = external_assets
        self._index: list[dict[str, Any]] | None = None
        self._official_catalog_dir = (
            official_catalog_dir or _DEFAULT_OFFICIAL_CATALOG_DIR
        )
        self._official_catalog_cache: dict[
            str, tuple[tuple[str, int, int], dict[str, Any]]
        ] = {}

    async def list(
        self,
        meta: OperationMeta,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> ModuleResult[AssetListResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.asset_list(
                category=category,
                subpath=subpath,
                recursive=recursive,
                max_depth=max_depth,
                max_entries=max_entries,
            )
            return ok_result(_parse_list(raw), started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc), started_ms=started, error_code="ASSET_LIST_ERROR"
            )

    # ------------------------------------------------------------------
    # Offline catalog search (no REST / no Isaac Sim)
    # ------------------------------------------------------------------

    def _load_index(self) -> list[dict[str, Any]]:
        if self._index is None:
            self._index = _build_index(self._catalog_dir)
        return self._index

    async def search(
        self,
        meta: OperationMeta,
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> ModuleResult[list[dict[str, Any]]]:
        started = int(time.time() * 1000)
        try:
            index = self._load_index()
            cat = (category or "").strip().lower() or None
            tokens = [t for t in (query or "").lower().split() if t]
            full = " ".join(tokens)

            scored: list[tuple[int, dict[str, Any]]] = []
            for e in index:
                if cat and e["category"] != cat:
                    continue
                score = _score(e, tokens, full)
                if tokens and score <= 0:
                    continue
                scored.append((score, e))

            scored.sort(key=lambda s: (-s[0], s[1]["name"].lower()))

            results: list[dict[str, Any]] = []
            seen: set[str] = set()
            for _score_val, e in scored:
                if e["url"] in seen:
                    continue
                seen.add(e["url"])
                results.append(
                    {
                        "name": e["name"],
                        "url": e["url"],
                        "category": e["category"],
                        "source_file": e["source_file"],
                    }
                )
                if len(results) >= limit:
                    break
            return ok_result(results, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="ASSET_SEARCH_ERROR",
            )

    async def external_search(
        self,
        meta: OperationMeta,
        query: str,
        providers: list[str] | None = None,
        limit: int = 10,
    ) -> ModuleResult[dict[str, Any]]:
        """Search external free asset providers after catalog search misses."""
        started = int(time.time() * 1000)
        try:
            data = await self._external_registry().search(
                query=query,
                providers=providers,
                limit=limit,
            )
            return ok_result(data, started_ms=started)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="EXTERNAL_ASSET_SEARCH_ERROR",
            )

    async def external_download(
        self,
        meta: OperationMeta,
        provider: str,
        asset_id: str,
        format_preference: list[str] | None = None,
    ) -> ModuleResult[dict[str, Any]]:
        """Download one selected external asset into the ignored local cache."""
        started = int(time.time() * 1000)
        try:
            result = await self._external_registry().download(
                provider_name=provider,
                asset_id=asset_id,
                format_preference=format_preference,
            )
            data = result.to_dict()
            return ok_result(
                data,
                started_ms=started,
                artifacts={"manifest": result.manifest_path},
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="EXTERNAL_ASSET_DOWNLOAD_ERROR",
            )

    async def external_convert(
        self,
        meta: OperationMeta,
        manifest_path: str,
        output_format: str = "usd",
        timeout_s: float = 180.0,
    ) -> ModuleResult[dict[str, Any]]:
        """Convert a downloaded external asset through the live Kit converter."""
        started = int(time.time() * 1000)
        try:
            registry = self._external_registry()
            manifest = registry.read_manifest(manifest_path)
            output_path = _conversion_output_path(
                manifest["cache_dir"],
                manifest["asset_id"],
                output_format,
            )
            raw = await self._client.external_asset_convert(
                {
                    "input_path": manifest["primary_file"],
                    "output_path": output_path,
                    "output_format": output_format,
                    "timeout_s": timeout_s,
                }
            )
            updated = registry.update_conversion(manifest_path, raw)
            data = {
                "manifest_path": manifest_path,
                "converted_path": updated["conversion"].get("output_path"),
                "conversion": updated["conversion"],
                "manifest": updated,
            }
            artifacts = {"manifest": manifest_path}
            if data["converted_path"]:
                artifacts["converted_asset"] = str(data["converted_path"])
            return ok_result(data, started_ms=started, artifacts=artifacts)
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="EXTERNAL_ASSET_CONVERT_ERROR",
            )

    def _external_registry(self) -> ExternalAssetRegistry:
        if self._external_assets is None:
            self._external_assets = ExternalAssetRegistry()
        return self._external_assets

    # ------------------------------------------------------------------
    # Generated NVIDIA official asset/material catalog
    # ------------------------------------------------------------------

    def _load_official_catalog(self, app_profile: str | None = None) -> dict[str, Any]:
        path = _official_catalog_path(self._official_catalog_dir, app_profile)
        file_id = _official_catalog_file_id(path)
        cache_key = str(path.resolve()) if path.exists() else str(path)
        cached = self._official_catalog_cache.get(cache_key)
        if cached and cached[0] == file_id:
            return cached[1]
        catalog = _load_official_catalog(self._official_catalog_dir, app_profile)
        self._official_catalog_cache[cache_key] = (file_id, catalog)
        return catalog

    async def official_search(
        self,
        meta: OperationMeta,
        query: str,
        kind: str | None = None,
        app_profile: str | None = None,
        provider: str | None = None,
        min_status: str = "url_validated",
        allow_stale: bool = True,
        limit: int = 20,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            catalog = self._load_official_catalog(app_profile)
            entries = _official_entries(catalog)
            min_rank = _official_status_rank(min_status)
            scored: list[tuple[int, str, dict[str, Any]]] = []
            for entry in entries:
                if kind and str(entry.get("kind", "")).lower() != kind.lower():
                    continue
                if app_profile and not _official_entry_has_app(entry, app_profile):
                    continue
                if provider and not _official_entry_has_provider(entry, provider):
                    continue
                status = _official_entry_status(entry, app_profile)
                if _official_status_rank(status) < min_rank:
                    continue
                stale_warning = _official_stale_warning(catalog, entry, app_profile)
                if stale_warning and not allow_stale:
                    continue
                score = _official_score(entry, query)
                if query.strip() and score <= 0:
                    continue
                scored.append((score, str(entry.get("name", "")), entry))

            scored.sort(key=lambda item: (-item[0], item[1].lower()))
            candidates = [
                _official_candidate(catalog, entry, app_profile)
                for _, _, entry in scored[: max(0, limit)]
            ]
            catalog_path = catalog.get("_catalog_path") or _official_catalog_path(
                self._official_catalog_dir, app_profile
            )
            data = {
                "catalog_path": _official_public_catalog_path(catalog_path),
                "catalog_identity": _official_public_catalog_identity(catalog),
                "query": query,
                "kind": kind,
                "app_profile": app_profile,
                "provider": provider,
                "min_status": min_status,
                "allow_stale": allow_stale,
                "count": len(candidates),
                "candidates": candidates,
            }
            if not candidates:
                data["diagnostics"] = _official_search_diagnostics(
                    catalog,
                    query=query,
                    kind=kind,
                    app_profile=app_profile,
                    provider=provider,
                    min_status=min_status,
                    allow_stale=allow_stale,
                    limit=limit,
                )
            return ok_result(
                data,
                started_ms=started,
            )
        except FileNotFoundError as exc:
            return _official_error_result(
                str(exc),
                started_ms=started,
                error_code="OFFICIAL_ASSET_CATALOG_UNAVAILABLE",
                data=_official_catalog_unavailable_data(
                    self._official_catalog_dir, app_profile
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="OFFICIAL_ASSET_SEARCH_ERROR",
            )

    async def official_resolve(
        self,
        meta: OperationMeta,
        name_or_id: str,
        kind: str | None = None,
        app_profile: str | None = None,
        prefer_loadable: bool = True,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            catalog = self._load_official_catalog(app_profile)
            entry = _find_official_entry(
                catalog,
                name_or_id,
                kind=kind,
                app_profile=app_profile,
                prefer_loadable=prefer_loadable,
            )
            if entry is None:
                return _official_error_result(
                    f"Official asset entry not found: {name_or_id}",
                    started_ms=started,
                    error_code="OFFICIAL_ASSET_NOT_FOUND",
                    data=_official_not_found_data(
                        catalog,
                        name_or_id=name_or_id,
                        kind=kind,
                        app_profile=app_profile,
                        prefer_loadable=prefer_loadable,
                    ),
                )
            return ok_result(
                _official_resolved(catalog, entry, app_profile),
                started_ms=started,
            )
        except FileNotFoundError as exc:
            return _official_error_result(
                str(exc),
                started_ms=started,
                error_code="OFFICIAL_ASSET_CATALOG_UNAVAILABLE",
                data=_official_catalog_unavailable_data(
                    self._official_catalog_dir, app_profile
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="OFFICIAL_ASSET_RESOLVE_ERROR",
            )

    async def official_get(
        self,
        meta: OperationMeta,
        asset_id: str,
        app_profile: str | None = None,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            catalog = self._load_official_catalog(app_profile)
            entry = _find_official_entry(catalog, asset_id, app_profile=app_profile)
            if entry is None:
                return _official_error_result(
                    f"Official asset entry not found: {asset_id}",
                    started_ms=started,
                    error_code="OFFICIAL_ASSET_NOT_FOUND",
                    data=_official_not_found_data(
                        catalog,
                        name_or_id=asset_id,
                        kind=None,
                        app_profile=app_profile,
                        prefer_loadable=True,
                    ),
                )
            data = dict(entry)
            data["stale_warning"] = _official_stale_warning(
                catalog, entry, app_profile
            )
            data["verify_required_before_use"] = _official_verify_required(
                catalog, entry, app_profile
            )
            return ok_result(data, started_ms=started)
        except FileNotFoundError as exc:
            return _official_error_result(
                str(exc),
                started_ms=started,
                error_code="OFFICIAL_ASSET_CATALOG_UNAVAILABLE",
                data=_official_catalog_unavailable_data(
                    self._official_catalog_dir, app_profile
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="OFFICIAL_ASSET_GET_ERROR",
            )

    async def official_sync_status(
        self,
        meta: OperationMeta,
        app_profile: str | None = None,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            catalog = self._load_official_catalog(app_profile)
            entries = _official_entries(catalog)
            snapshots = [
                s for s in catalog.get("snapshots", [])
                if not app_profile or s.get("app_profile") == app_profile
            ]
            profiles = []
            for snapshot in snapshots:
                profile = str(snapshot.get("app_profile", ""))
                profile_entries = [
                    e for e in entries if _official_entry_has_app(e, profile)
                ]
                failure_count = sum(
                    1
                    for e in profile_entries
                    if _official_entry_status(e, profile) == "failed"
                )
                profiles.append(
                    {
                        "app_profile": profile,
                        "app_version": snapshot.get("app_version"),
                        "kit_version": snapshot.get("kit_version"),
                        "generated_at": snapshot.get("generated_at")
                        or catalog.get("generated_at"),
                        "providers": _official_public_providers(
                            snapshot.get("providers") or []
                        ),
                        "counts": snapshot.get("counts")
                        or _official_counts(profile_entries, profile),
                        "stale": _official_snapshot_is_stale(catalog, snapshot),
                        "stale_warning": _official_snapshot_stale_warning(
                            catalog, snapshot
                        ),
                        "failure_count": failure_count,
                    }
                )
            filtered_entries = [
                e for e in entries
                if not app_profile or _official_entry_has_app(e, app_profile)
            ]
            catalog_path = catalog.get("_catalog_path") or _official_catalog_path(
                self._official_catalog_dir, app_profile
            )
            data = {
                "catalog_path": _official_public_catalog_path(catalog_path),
                "catalog_identity": _official_public_catalog_identity(catalog),
                "schema_version": catalog.get("schema_version"),
                "generated_at": catalog.get("generated_at"),
                "app_profile": app_profile,
                "profile_count": len(profiles),
                "profiles": profiles,
                "counts": _official_counts(filtered_entries, app_profile),
            }
            diagnostics = _official_sync_status_diagnostics(
                catalog,
                app_profile=app_profile,
                profiles=profiles,
                filtered_entries=filtered_entries,
            )
            if diagnostics:
                data["diagnostics"] = diagnostics
            return ok_result(
                data,
                started_ms=started,
            )
        except FileNotFoundError as exc:
            return _official_error_result(
                str(exc),
                started_ms=started,
                error_code="OFFICIAL_ASSET_CATALOG_UNAVAILABLE",
                data=_official_catalog_unavailable_data(
                    self._official_catalog_dir, app_profile
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="OFFICIAL_ASSET_SYNC_STATUS_ERROR",
            )

    async def official_verify(
        self,
        meta: OperationMeta,
        asset_id: str,
        app_profile: str | None = None,
        timeout_s: float | None = None,
    ) -> ModuleResult[dict[str, Any]]:
        started = int(time.time() * 1000)
        try:
            catalog = self._load_official_catalog(app_profile)
            entry = _find_official_entry(
                catalog,
                asset_id,
                app_profile=app_profile,
                prefer_loadable=False,
            )
            if entry is None:
                return _official_error_result(
                    f"Official asset entry not found: {asset_id}",
                    started_ms=started,
                    error_code="OFFICIAL_ASSET_NOT_FOUND",
                    data=_official_not_found_data(
                        catalog,
                        name_or_id=asset_id,
                        kind=None,
                        app_profile=app_profile,
                        prefer_loadable=False,
                    ),
                )
            default_timeout = 45.0 if entry.get("kind") == "material" else 120.0
            timeout = float(timeout_s or default_timeout)
            attempts = 2
            last_record: dict[str, Any] | None = None
            for attempt in range(1, attempts + 1):
                attempt_started = time.perf_counter()
                try:
                    record = await asyncio.wait_for(
                        self._verify_official_entry(meta, entry, app_profile),
                        timeout=timeout,
                    )
                    record["attempt"] = attempt
                    record["timeout_s"] = timeout
                    record["elapsed_ms"] = int(
                        (time.perf_counter() - attempt_started) * 1000
                    )
                    last_record = record
                    if record.get("verification_status") != "failed":
                        break
                except Exception as exc:  # noqa: BLE001 - preserve retry evidence
                    last_record = _official_verify_record(
                        entry,
                        app_profile,
                        status="failed",
                        error=str(exc),
                    )
                    last_record["attempt"] = attempt
                    last_record["timeout_s"] = timeout
                    last_record["elapsed_ms"] = int(
                        (time.perf_counter() - attempt_started) * 1000
                    )
            record = last_record or _official_verify_record(
                entry, app_profile, status="failed", error="verification did not run"
            )
            record["retry_count"] = attempts - 1
            _append_official_verify_record(self._official_catalog_dir, record)
            return ok_result(record, started_ms=started)
        except FileNotFoundError as exc:
            return _official_error_result(
                str(exc),
                started_ms=started,
                error_code="OFFICIAL_ASSET_CATALOG_UNAVAILABLE",
                data=_official_catalog_unavailable_data(
                    self._official_catalog_dir, app_profile
                ),
            )
        except Exception as exc:
            return error_result(
                str(exc),
                started_ms=started,
                exc=exc,
                error_code="OFFICIAL_ASSET_VERIFY_ERROR",
            )

    async def _verify_official_entry(
        self,
        meta: OperationMeta,
        entry: dict[str, Any],
        app_profile: str | None,
    ) -> dict[str, Any]:
        if entry.get("kind") == "material":
            return await self._verify_official_material(meta, entry, app_profile)
        return await self._verify_official_asset(meta, entry, app_profile)

    async def _verify_official_asset(
        self,
        meta: OperationMeta,
        entry: dict[str, Any],
        app_profile: str | None,
    ) -> dict[str, Any]:
        url = str(entry.get("canonical_url", ""))
        prim_path = f"/World/OfficialAssetVerify/{_safe_prim_name(entry)}"
        cleanup: dict[str, Any] | None = None
        record = _official_verify_record(entry, app_profile, status="failed")
        try:
            await self._ensure_timeline_stopped()
            load = await self._client.stage_load_usd(
                {"usd_url": url, "prim_path": prim_path, "position": None, "rotation": None}
            )
            bbox = await self._client.stage_compute_world_bbox(
                {"prim_path": prim_path, "include_purposes": ["default", "render"]}
            )
            inspect = await self._client.content_inspect({"url": url})
            quality = official_asset_load_quality_evidence(load, bbox, inspect)
            load_verified = (
                quality["load_quality"] in OFFICIAL_ASSET_LOAD_VERIFIED_QUALITIES
            )
            record.update(
                {
                    "verification_status": (
                        "load_verified" if load_verified else "failed"
                    ),
                    "prim_path": prim_path,
                    "stage_load": load,
                    "bbox": {
                        "min": bbox.get("min"),
                        "max": bbox.get("max"),
                        "center": bbox.get("center"),
                        "size": bbox.get("size"),
                    },
                    "meters_per_unit": inspect.get("meters_per_unit"),
                    "up_axis": inspect.get("up_axis"),
                    "prim_count": inspect.get("prim_count"),
                    "load_quality": quality["load_quality"],
                    "load_quality_warning": quality["load_quality_warning"],
                    "bbox_valid": quality["bbox_valid"],
                    "bbox_validation_reasons": quality["bbox_validation_reasons"],
                    "has_authored_children": quality["has_authored_children"],
                    "has_default_prim": quality["has_default_prim"],
                    "prim_count_valid": quality["prim_count_valid"],
                    "error": None if load_verified else quality["load_quality_warning"],
                }
            )
            return record
        finally:
            await self._prepare_official_verify_cleanup()
            try:
                cleanup = await self._client.stage_delete_prim(prim_path)
            except Exception as exc:  # noqa: BLE001
                cleanup = {"ok": False, "error": str(exc)}
            record["cleanup"] = cleanup

    async def _verify_official_material(
        self,
        meta: OperationMeta,
        entry: dict[str, Any],
        app_profile: str | None,
    ) -> dict[str, Any]:
        url = str(entry.get("canonical_url", ""))
        material_name = _official_material_name(entry)
        prim_path = f"/World/OfficialMaterialVerify/{_safe_prim_name(entry)}Target"
        cleanup: dict[str, Any] | None = None
        record = _official_verify_record(entry, app_profile, status="failed")
        try:
            create = await self._client.stage_create_prim(
                {"prim_path": prim_path, "prim_type": "Cube", "position": [0.0, 0.0, 0.0]}
            )
            assign = await self._client.material_assign_mdl(
                {
                    "prim_path": prim_path,
                    "mdl_url": url,
                    "material_name": material_name,
                }
            )
            bound = await self._client.material_get_bound(prim_path)
            create_ok = bool(create.get("ok", True))
            assign_ok = bool(assign.get("ok", True))
            bound_ok = bool(bound.get("ok", True)) and bool(bound.get("material_path"))
            record.update(
                {
                    "verification_status": (
                        "assign_verified" if create_ok and assign_ok and bound_ok else "failed"
                    ),
                    "prim_path": prim_path,
                    "material_name": material_name,
                    "create_prim": create,
                    "assign": assign,
                    "bound": bound,
                    "error": None if create_ok and assign_ok and bound_ok else "material assign or binding readback failed",
                }
            )
            return record
        finally:
            await self._prepare_official_verify_cleanup()
            try:
                cleanup = await self._client.stage_delete_prim(prim_path)
            except Exception as exc:  # noqa: BLE001
                cleanup = {"ok": False, "error": str(exc)}
            record["cleanup"] = cleanup

    async def _prepare_official_verify_cleanup(self) -> None:
        try:
            await self._client.stage_set_selection([], expand_in_stage=False)
        except Exception:
            logger.debug("official verify cleanup selection clear failed", exc_info=True)

    async def _ensure_timeline_stopped(self) -> None:
        status = await self._client.simulation_status()
        if status.get("is_playing"):
            await self._client.simulation_stop()


# ----------------------------------------------------------------------
# Catalog markdown parser (pure functions — unit-testable in isolation)
# ----------------------------------------------------------------------


def _build_index(catalog_dir: Path) -> list[dict[str, Any]]:
    """Parse every per-category catalog markdown into searchable entries."""
    entries: list[dict[str, Any]] = []
    assets_dir = catalog_dir / "assets"
    if not assets_dir.is_dir():
        return entries
    for cat in _CATEGORY_FILES:
        md = assets_dir / f"{cat}.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        entries.extend(_parse_catalog_file(text, category=cat, source_file=md.name))
    return entries


def resolve_catalog_asset_url(
    category: str,
    relative_path: str,
    catalog_dir: Path | None = None,
) -> str:
    """Resolve a catalog-relative asset path through the markdown SoT."""
    normalized_category = category.strip().lower()
    normalized_path = relative_path.strip().replace("\\", "/").strip("/")
    suffix = f"/{normalized_path}"
    for entry in _build_index(catalog_dir or _DEFAULT_CATALOG_DIR):
        if entry["category"] != normalized_category:
            continue
        if str(entry["url"]).replace("\\", "/").endswith(suffix):
            return str(entry["url"])
    raise KeyError(f"Asset catalog entry not found: {category}/{relative_path}")


def _parse_catalog_file(
    text: str, category: str, source_file: str
) -> list[dict[str, Any]]:
    prefix_map = {
        var: url for var, url in _PREFIX_RE.findall(text)
    }

    def resolve_prefix(s: str) -> str:
        for var, url in prefix_map.items():
            if s.startswith(var):
                return url + s[len(var):]
        return s

    entries: list[dict[str, Any]] = []
    file_root: str | None = None
    current_root: str | None = None
    current_group: str | None = None
    prose_header: str = ""

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # Section boundaries reset the rowspan group.
        root_m = _ROOT_RE.match(stripped)
        if root_m:
            current_root = resolve_prefix(root_m.group(1)) + "/"
            if file_root is None:
                file_root = current_root
            current_group = None
            continue
        if _HEADING_RE.match(stripped):
            current_group = None
            # A bold-only heading-ish line is rare; headings carry no assets.
            continue

        # Table rows.
        if stripped.startswith("|"):
            cells = _split_cells(stripped)
            if not cells or _is_separator_row(cells):
                continue
            col0 = _BOLD_RE.sub("", cells[0]).strip()
            # Update group from a plain (non-USD) col0; empty col0 inherits.
            if col0 and ".usd" not in cells[0]:
                current_group = col0
            usd_tokens = _usd_tokens(stripped)
            if not usd_tokens:
                continue
            row_text = " ".join(cells)
            for tok in usd_tokens:
                url = _build_url(
                    tok,
                    category=category,
                    prefix_map=prefix_map,
                    resolve_prefix=resolve_prefix,
                    file_root=file_root,
                    current_root=current_root,
                    group=current_group,
                    cells=cells,
                )
                if not url:
                    continue
                entries.append(
                    _make_entry(
                        name=_basename(tok),
                        url=url,
                        category=category,
                        source_file=source_file,
                        text=f"{row_text} {current_group or ''} {prose_header}",
                    )
                )
            continue

        # Prose (SimReady curated name lists).
        if category == "simready":
            if stripped.startswith("**") and stripped.endswith("**"):
                prose_header = _BOLD_RE.sub("", stripped).strip()
                continue
            for tok in _BACKTICK_RE.findall(stripped):
                name = tok.strip()
                if not _SIMREADY_NAME_RE.match(name):
                    continue
                canonical = _simready_canonical(name)
                if not canonical:
                    continue
                sim = prefix_map.get("$SIM")
                if not sim:
                    continue
                url = f"{sim}/{canonical}/{canonical}.usd"
                entries.append(
                    _make_entry(
                        name=name,
                        url=url,
                        category=category,
                        source_file=source_file,
                        text=f"{name} {prose_header}",
                    )
                )

    return entries


def _make_entry(
    name: str, url: str, category: str, source_file: str, text: str
) -> dict[str, Any]:
    hay = f"{name} {text} {category}".lower()
    return {
        "name": name,
        "url": url,
        "category": category,
        "source_file": source_file,
        "_text": hay,
    }


def _split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c) is not None for c in cells if c)


def _usd_tokens(line: str) -> list[str]:
    """Backtick tokens that reference a .usd/.usda file."""
    out: list[str] = []
    for tok in _BACKTICK_RE.findall(line):
        t = tok.strip()
        if ".usd" not in t and ".usda" not in t:
            continue
        # Skip prose-rule placeholders like `$SIM/{name}/{name}.usd`.
        if "{" in t or "(" in t or t.startswith("$"):
            continue
        out.append(t)
    return out


def _basename(token: str) -> str:
    return token.rstrip("/").split("/")[-1]


def _simready_canonical(name: str) -> str:
    """First concrete asset name from a SimReady shorthand token.

    `box_a01~a11` → `box_a01`; `aluminumpallet_a01/a02` → `aluminumpallet_a01`;
    `pallet_a1/b1/c1` → `pallet_a1`.
    """
    head = re.split(r"[~,/ ]", name, maxsplit=1)[0].strip()
    return head


def _build_url(
    token: str,
    *,
    category: str,
    prefix_map: dict[str, str],
    resolve_prefix,
    file_root: str | None,
    current_root: str | None,
    group: str | None,
    cells: list[str],
) -> str | None:
    if token.startswith("$"):
        return resolve_prefix(token)

    if category == "robots":
        isaac = prefix_map.get("$ISAAC")
        if not isaac:
            return None
        base = f"{isaac}/Robots/"
        vendor = group
        if not vendor:
            return None
        if "/" in token:
            return f"{base}{vendor}/{token}"
        model = _BOLD_RE.sub("", cells[1]).strip() if len(cells) > 1 else ""
        if model:
            return f"{base}{vendor}/{model}/{token}"
        return f"{base}{vendor}/{token}"

    # Path with subfolders → relative to the file-level category root.
    if "/" in token:
        if file_root:
            return f"{file_root}{token}"
        return None

    # Bare filename → nearest section root + (rowspan group folder).
    base = current_root or file_root
    if not base:
        return None
    if group:
        return f"{base}{group}/{token}"
    return f"{base}{token}"


def _score(entry: dict[str, Any], tokens: list[str], full: str) -> int:
    if not tokens:
        return 0
    name = entry["name"].lower()
    stem = re.sub(r"\.usda?$", "", name)
    hay = entry["_text"]
    score = 0
    for tok in tokens:
        if tok == stem:
            score += 100
        elif tok in name:
            score += 10
        if tok in hay:
            score += 3
    if full and full in name:
        score += 50
    return score


def _parse_list(raw: dict) -> AssetListResult:
    categories = tuple(
        AssetCategory(name=c["name"], url=c["url"])
        for c in raw.get("categories", [])
    )
    items = tuple(
        AssetItem(
            name=i["name"],
            url=i["url"],
            is_folder=bool(i.get("is_folder", False)),
            size=i.get("size"),
        )
        for i in raw.get("items", [])
    )
    return AssetListResult(
        assets_root=raw.get("assets_root"),
        category=raw.get("category"),
        subpath=raw.get("subpath", ""),
        base_url=raw.get("base_url"),
        target_url=raw.get("target_url"),
        categories=categories,
        items=items,
        count=int(raw.get("count", len(items))),
    )


def official_asset_id(canonical_url: str) -> str:
    """Stable URL-based catalog id used by generated snapshots and MCP tools."""
    return f"url:{canonical_url.strip()}"


def _official_profile_latest_name(app_profile: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", app_profile.strip()).strip("-")
    return f"latest-{safe or app_profile}.json"


def _official_catalog_path(
    catalog_dir: Path,
    app_profile: str | None = None,
) -> Path:
    names: list[str] = []
    if app_profile:
        names.append(_official_profile_latest_name(app_profile))
    names.extend(("latest.json", "catalog.json", "official-assets.latest.json"))
    for name in names:
        candidate = catalog_dir / name
        if candidate.is_file():
            return candidate
    return catalog_dir / (_official_profile_latest_name(app_profile) if app_profile else "latest.json")


def _official_catalog_file_id(path: Path) -> tuple[str, int, int]:
    if not path.is_file():
        return (str(path), -1, -1)
    stat = path.stat()
    return (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))


def _official_public_catalog_path(path: Path | str) -> str:
    candidate = Path(path)
    try:
        resolved = candidate.resolve()
        return resolved.relative_to(_PROJECT_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        pass
    if not candidate.is_absolute():
        return candidate.as_posix()
    return f"<external-catalog>/{candidate.name or 'catalog'}"


def _official_public_external_path(path: Path | str, marker: str) -> str:
    candidate = Path(path)
    try:
        resolved = candidate.resolve()
        return resolved.relative_to(_PROJECT_ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        pass
    if not candidate.is_absolute():
        return candidate.as_posix()
    return f"{marker}/{candidate.name or 'path'}"


def _official_public_providers(providers: list[Any]) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        item = dict(provider)
        extension_dir = item.get("extension_dir")
        if extension_dir:
            item["extension_dir"] = _official_public_external_path(
                str(extension_dir), "<external-extension>"
            )
        public.append(item)
    return public


def _official_public_catalog_identity(catalog: dict[str, Any]) -> dict[str, Any]:
    return dict(catalog.get("_catalog_identity") or {})


def _load_official_catalog(
    catalog_dir: Path,
    app_profile: str | None = None,
) -> dict[str, Any]:
    path = _official_catalog_path(catalog_dir, app_profile)
    if not path.is_file():
        raise FileNotFoundError(
            "Official asset catalog is not available. Generate "
            "docs/references/official-assets/latest.json with "
            "scripts/sync_official_asset_catalog.py before using official_asset_* tools."
        )
    catalog = json.loads(path.read_text(encoding="utf-8"))
    public_path = _official_public_catalog_path(path)
    catalog["_catalog_path"] = public_path
    stat = path.stat()
    catalog["_catalog_identity"] = {
        "path": public_path,
        "mtime_ns": int(stat.st_mtime_ns),
        "size": int(stat.st_size),
        "run_id": catalog.get("run_id"),
        "generated_at": catalog.get("generated_at"),
        "profiles": [
            snapshot.get("app_profile")
            for snapshot in catalog.get("snapshots") or []
            if snapshot.get("app_profile")
        ],
    }
    return catalog


def _official_error_result(
    message: str,
    *,
    started_ms: int,
    error_code: str,
    data: dict[str, Any],
) -> ModuleResult[dict[str, Any]]:
    return ModuleResult(
        ok=False,
        status=ExecutionStatus.ERROR,
        data=data,
        message=message,
        error_code=error_code,
        duration_ms=int(time.time() * 1000) - started_ms,
    )


def _official_catalog_unavailable_data(
    catalog_dir: Path,
    app_profile: str | None,
) -> dict[str, Any]:
    expected_files = ["latest.json", "catalog.json", "official-assets.latest.json"]
    if app_profile:
        expected_files.insert(0, _official_profile_latest_name(app_profile))
    return {
        "app_profile": app_profile,
        "diagnostics": {
            "reason": "catalog_unavailable",
            "checked_catalog_path": _official_public_catalog_path(
                _official_catalog_path(catalog_dir, app_profile)
            ),
            "expected_files": expected_files,
            "suggested_next": _official_suggested_next("catalog_unavailable"),
            "fallback_tool_order": _official_fallback_tool_order(),
        },
    }


def _official_not_found_data(
    catalog: dict[str, Any],
    *,
    name_or_id: str,
    kind: str | None,
    app_profile: str | None,
    prefer_loadable: bool,
) -> dict[str, Any]:
    return {
        "name_or_id": name_or_id,
        "kind": kind,
        "app_profile": app_profile,
        "prefer_loadable": prefer_loadable,
        "diagnostics": _official_search_diagnostics(
            catalog,
            query=name_or_id,
            kind=kind,
            app_profile=app_profile,
            provider=None,
            min_status="discovered",
            allow_stale=True,
            limit=20,
        ),
    }


def _official_sync_status_diagnostics(
    catalog: dict[str, Any],
    *,
    app_profile: str | None,
    profiles: list[dict[str, Any]],
    filtered_entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not app_profile:
        return None
    if not profiles:
        reason = "app_profile_not_covered"
    elif not filtered_entries:
        reason = "empty_catalog"
    else:
        return None
    return {
        "reason": reason,
        "requested_app_profile": app_profile,
        "available_profiles": _official_catalog_profiles(catalog),
        "profile_count": len(profiles),
        "matching_item_count": len(filtered_entries),
        "suggested_next": _official_suggested_next(reason),
        "fallback_tool_order": _official_fallback_tool_order(),
    }


def _official_catalog_profiles(catalog: dict[str, Any]) -> list[str]:
    profiles = [
        str(snapshot.get("app_profile"))
        for snapshot in catalog.get("snapshots") or []
        if snapshot.get("app_profile")
    ]
    return _dedupe_strs(profiles)


def _official_search_diagnostics(
    catalog: dict[str, Any],
    *,
    query: str,
    kind: str | None,
    app_profile: str | None,
    provider: str | None,
    min_status: str,
    allow_stale: bool,
    limit: int,
) -> dict[str, Any]:
    entries = _official_entries(catalog)
    by_kind = [
        e
        for e in entries
        if not kind or str(e.get("kind", "")).lower() == kind.lower()
    ]
    by_app = [
        e
        for e in by_kind
        if not app_profile or _official_entry_has_app(e, app_profile)
    ]
    by_provider = [
        e
        for e in by_app
        if not provider or _official_entry_has_provider(e, provider)
    ]
    min_rank = _official_status_rank(min_status)
    by_status = [
        e
        for e in by_provider
        if _official_status_rank(_official_entry_status(e, app_profile)) >= min_rank
    ]
    query_text = query.strip()
    query_matches_before_stale = [
        e
        for e in by_status
        if not query_text or _official_score(e, query) > 0
    ]
    stale_query_matches = [
        e
        for e in query_matches_before_stale
        if _official_stale_warning(catalog, e, app_profile)
    ]
    by_stale = [
        e
        for e in by_status
        if allow_stale or not _official_stale_warning(catalog, e, app_profile)
    ]
    query_matches = [
        e
        for e in by_stale
        if not query_text or _official_score(e, query) > 0
    ]
    counts = {
        "total_entries": len(entries),
        "after_kind": len(by_kind),
        "after_app_profile": len(by_app),
        "after_provider": len(by_provider),
        "after_min_status": len(by_status),
        "query_matches_before_stale_filter": len(query_matches_before_stale),
        "after_allow_stale": len(by_stale),
        "query_matches": len(query_matches),
        "result_limit": max(0, limit),
    }
    reason = _official_no_results_reason(
        counts,
        kind=kind,
        app_profile=app_profile,
        provider=provider,
        query=query_text,
        allow_stale=allow_stale,
        stale_query_match_count=len(stale_query_matches),
        limit=limit,
    )
    return {
        "reason": reason,
        "filters": {
            "query": query,
            "kind": kind,
            "app_profile": app_profile,
            "provider": provider,
            "min_status": min_status,
            "allow_stale": allow_stale,
            "limit": limit,
        },
        "candidate_counts": counts,
        "suggested_next": _official_suggested_next(reason),
        "fallback_tool_order": _official_fallback_tool_order(),
    }


def _official_no_results_reason(
    counts: dict[str, int],
    *,
    kind: str | None,
    app_profile: str | None,
    provider: str | None,
    query: str,
    allow_stale: bool,
    stale_query_match_count: int,
    limit: int,
) -> str:
    if limit <= 0:
        return "limit_zero"
    if counts["total_entries"] == 0:
        return "empty_catalog"
    if kind and counts["after_kind"] == 0:
        return "kind_not_found"
    if app_profile and counts["after_app_profile"] == 0:
        return "app_profile_not_covered"
    if provider and counts["after_provider"] == 0:
        return "provider_not_covered"
    if counts["after_min_status"] == 0:
        return "min_status_too_strict"
    if not allow_stale and stale_query_match_count and counts["query_matches"] == 0:
        return "only_stale_matches"
    if query and counts["query_matches"] == 0:
        return "query_no_match"
    return "no_results"


def _official_suggested_next(reason: str) -> list[str]:
    suggestions = {
        "catalog_unavailable": [
            "Generate the ignored official catalog with scripts/sync_official_asset_catalog.py, then retry official_asset_sync_status.",
            "Use asset_search as the offline fallback while the official catalog is unavailable.",
        ],
        "empty_catalog": [
            "Regenerate the official catalog with provider discovery enabled for the target app profile.",
            "Use asset_search for Isaac curated USD assets while auditing catalog generation.",
        ],
        "kind_not_found": [
            "Retry without kind, or switch kind between asset and material.",
            "Check official_asset_sync_status counts before falling back to asset_search.",
        ],
        "app_profile_not_covered": [
            "Call official_asset_sync_status without app_profile to list covered profiles.",
            "Retry official_asset_search with a covered app_profile or no app_profile.",
        ],
        "provider_not_covered": [
            "Call official_asset_sync_status for provider coverage, then retry without provider.",
            "If the provider is expected, rerun catalog sync for that app profile before use.",
        ],
        "min_status_too_strict": [
            "Retry official_asset_search with min_status='discovered' to inspect lower-confidence hits.",
            "Run official_asset_verify on promising hits before stage placement or material assignment.",
        ],
        "only_stale_matches": [
            "Retry with allow_stale=True, then pass the selected id to official_asset_verify.",
            "Do not stage-place or assign stale results until verification succeeds.",
        ],
        "query_no_match": [
            "Retry with a broader asset family, category, provider, or filename stem.",
            "If official search still misses, use asset_search for Isaac curated USD assets.",
        ],
        "limit_zero": [
            "Retry official_asset_search with limit greater than 0.",
            "Keep other filters unchanged before widening the search.",
        ],
    }
    return suggestions.get(
        reason,
        [
            "Call official_asset_sync_status to inspect catalog coverage.",
            "Retry official_asset_search with fewer filters before using asset_search fallback.",
        ],
    )


def _official_fallback_tool_order() -> list[str]:
    return [
        "official_asset_sync_status",
        "official_asset_search",
        "official_asset_resolve",
        "official_asset_verify",
        "asset_search",
    ]


def _official_entries(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}
    raw_items = list(catalog.get("items") or [])
    for snapshot in catalog.get("snapshots") or []:
        for item in snapshot.get("items") or []:
            raw_items.append(_official_item_with_snapshot_defaults(item, snapshot))
    for raw in raw_items:
        entry = _normalize_official_entry(raw)
        key = str(entry["id"])
        if key in flattened:
            _merge_official_entry(flattened[key], entry)
        else:
            flattened[key] = entry
    return list(flattened.values())


def _official_item_with_snapshot_defaults(
    item: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    out = dict(item)
    for key in ("app_profile", "app_version", "kit_version"):
        out.setdefault(key, snapshot.get(key))
    if not out.get("provided_in"):
        out["provided_in"] = [
            {
                "app_profile": snapshot.get("app_profile"),
                "app_version": snapshot.get("app_version"),
                "kit_version": snapshot.get("kit_version"),
                "provider": item.get("provider"),
                "extension_id": item.get("extension_id"),
                "extension_version": item.get("extension_version"),
                "source_root": item.get("source_root"),
                "category": item.get("category"),
            }
        ]
    return out


def _normalize_official_entry(raw: dict[str, Any]) -> dict[str, Any]:
    canonical_url = str(raw.get("canonical_url") or raw.get("url") or "").strip()
    entry = dict(raw)
    entry["canonical_url"] = canonical_url
    entry["id"] = str(raw.get("id") or official_asset_id(canonical_url))
    entry["kind"] = str(raw.get("kind") or _guess_official_kind(canonical_url))
    entry["name"] = str(raw.get("name") or _url_name(canonical_url))
    entry["aliases"] = _dedupe_strs(raw.get("aliases") or [])
    entry["provided_in"] = _dedupe_dicts(raw.get("provided_in") or [])
    entry["loadable_in"] = _dedupe_dicts(raw.get("loadable_in") or [])
    if raw.get("app_profile") and not entry["provided_in"]:
        entry["provided_in"] = [
            {
                "app_profile": raw.get("app_profile"),
                "app_version": raw.get("app_version"),
                "kit_version": raw.get("kit_version"),
                "provider": raw.get("provider"),
                "extension_id": raw.get("extension_id"),
                "extension_version": raw.get("extension_version"),
                "source_root": raw.get("source_root"),
                "category": raw.get("category"),
            }
        ]
    entry["verification_status"] = str(
        raw.get("verification_status") or _status_from_loadable(entry) or "discovered"
    )
    return entry


def _merge_official_entry(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in (
        "kind",
        "name",
        "canonical_url",
        "provider",
        "source_root",
        "category",
        "app_profile",
        "app_version",
        "kit_version",
        "extension_id",
        "extension_version",
        "material_name",
    ):
        if not target.get(key) and source.get(key):
            target[key] = source[key]
    target["aliases"] = _dedupe_strs(
        list(target.get("aliases") or []) + list(source.get("aliases") or [])
    )
    target["provided_in"] = _dedupe_dicts(
        list(target.get("provided_in") or []) + list(source.get("provided_in") or [])
    )
    target["loadable_in"] = _dedupe_dicts(
        list(target.get("loadable_in") or []) + list(source.get("loadable_in") or [])
    )
    if _official_status_rank(source.get("verification_status")) > _official_status_rank(
        target.get("verification_status")
    ):
        target["verification_status"] = source.get("verification_status")


def _dedupe_strs(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = text.lower()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _dedupe_dicts(values: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            continue
        key = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        if key not in seen:
            out.append(dict(value))
            seen.add(key)
    return out


def _guess_official_kind(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".mdl"):
        return "material"
    return "asset"


def _url_name(url: str) -> str:
    clean = url.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1] or clean


def _status_from_loadable(entry: dict[str, Any]) -> str | None:
    statuses = [
        str(item.get("verification_status") or "")
        for item in entry.get("loadable_in") or []
    ]
    statuses = [s for s in statuses if s]
    if not statuses:
        return None
    return max(statuses, key=_official_status_rank)


def _official_status_rank(status: Any) -> int:
    return _OFFICIAL_STATUS_RANK.get(str(status or "discovered"), 0)


def _official_entry_has_app(entry: dict[str, Any], app_profile: str) -> bool:
    if entry.get("app_profile") == app_profile:
        return True
    return any(
        item.get("app_profile") == app_profile
        for item in list(entry.get("provided_in") or []) + list(entry.get("loadable_in") or [])
    )


def _official_entry_has_provider(entry: dict[str, Any], provider: str) -> bool:
    if entry.get("provider") == provider:
        return True
    return any(
        item.get("provider") == provider
        for item in entry.get("provided_in") or []
    )


def _official_entry_status(
    entry: dict[str, Any],
    app_profile: str | None,
) -> str:
    if app_profile:
        statuses = [
            str(item.get("verification_status") or "")
            for item in entry.get("loadable_in") or []
            if item.get("app_profile") == app_profile
        ]
        statuses = [s for s in statuses if s]
        if statuses:
            return max(statuses, key=_official_status_rank)
    return str(entry.get("verification_status") or _status_from_loadable(entry) or "discovered")


def _official_score(entry: dict[str, Any], query: str) -> int:
    tokens = [t for t in (query or "").lower().split() if t]
    if not tokens:
        return 0
    name = str(entry.get("name", "")).lower()
    stem = re.sub(r"\.(usd|usda|mdl)$", "", name)
    aliases = " ".join(str(a) for a in entry.get("aliases") or []).lower()
    hay = " ".join(
        str(part or "")
        for part in (
            entry.get("id"),
            entry.get("canonical_url"),
            entry.get("provider"),
            entry.get("category"),
            aliases,
        )
    ).lower()
    full = " ".join(tokens)
    score = 0
    for token in tokens:
        if token == stem:
            score += 100
        elif token in name:
            score += 20
        if token in aliases:
            score += 15
        if token in hay:
            score += 3
    if full and (full in name or full in aliases):
        score += 50
    return score


def _official_candidate(
    catalog: dict[str, Any],
    entry: dict[str, Any],
    app_profile: str | None,
) -> dict[str, Any]:
    status = _official_entry_status(entry, app_profile)
    stale_warning = _official_stale_warning(catalog, entry, app_profile)
    provider_evidence = _official_provider_evidence(entry, app_profile)
    app_evidence = _official_app_evidence(entry, app_profile)
    return {
        "id": entry.get("id"),
        "kind": entry.get("kind"),
        "name": entry.get("name"),
        "aliases": entry.get("aliases") or [],
        "canonical_url": entry.get("canonical_url"),
        "provider": entry.get("provider"),
        "category": entry.get("category"),
        "status": "stale" if stale_warning else status,
        "verification_status": status,
        "provider_evidence": provider_evidence,
        "app_version_evidence": app_evidence,
        "stale_warning": stale_warning,
        "verify_required_before_use": _official_verify_required(
            catalog, entry, app_profile
        ),
        "target": _official_target(entry),
    }


def _official_provider_evidence(
    entry: dict[str, Any],
    app_profile: str | None,
) -> list[dict[str, Any]]:
    evidence = []
    for item in entry.get("provided_in") or []:
        if app_profile and item.get("app_profile") != app_profile:
            continue
        evidence.append(
            {
                "provider": item.get("provider") or entry.get("provider"),
                "app_profile": item.get("app_profile"),
                "extension_id": item.get("extension_id") or entry.get("extension_id"),
                "extension_version": item.get("extension_version")
                or entry.get("extension_version"),
                "source_root": item.get("source_root") or entry.get("source_root"),
                "category": item.get("category") or entry.get("category"),
            }
        )
    return evidence


def _official_app_evidence(
    entry: dict[str, Any],
    app_profile: str | None,
) -> list[dict[str, Any]]:
    evidence = []
    for item in list(entry.get("provided_in") or []) + list(entry.get("loadable_in") or []):
        if app_profile and item.get("app_profile") != app_profile:
            continue
        evidence.append(
            {
                "app_profile": item.get("app_profile"),
                "app_version": item.get("app_version"),
                "kit_version": item.get("kit_version"),
                "verification_status": item.get("verification_status"),
                "checked_at": item.get("checked_at"),
            }
        )
    return _dedupe_dicts(evidence)


def _official_target(entry: dict[str, Any]) -> dict[str, Any]:
    if entry.get("kind") == "material":
        return {
            "mdl_url": entry.get("canonical_url"),
            "material_name": _official_material_name(entry),
        }
    return {"usd_url": entry.get("canonical_url")}


def _official_resolved(
    catalog: dict[str, Any],
    entry: dict[str, Any],
    app_profile: str | None,
) -> dict[str, Any]:
    return {
        **_official_candidate(catalog, entry, app_profile),
        "provided_in": entry.get("provided_in") or [],
        "loadable_in": entry.get("loadable_in") or [],
        "bbox": entry.get("bbox"),
        "meters_per_unit": entry.get("meters_per_unit"),
        "up_axis": entry.get("up_axis"),
        "prim_count": entry.get("prim_count"),
        "error": entry.get("error"),
    }


def _find_official_entry(
    catalog: dict[str, Any],
    name_or_id: str,
    kind: str | None = None,
    app_profile: str | None = None,
    prefer_loadable: bool = True,
) -> dict[str, Any] | None:
    needle = str(name_or_id or "").strip()
    if not needle:
        return None
    entries = [
        e for e in _official_entries(catalog)
        if not kind or str(e.get("kind", "")).lower() == kind.lower()
    ]
    if app_profile:
        entries = [e for e in entries if _official_entry_has_app(e, app_profile)]
    exact = [
        e for e in entries
        if needle in {str(e.get("id")), str(e.get("canonical_url"))}
    ]
    if not exact:
        lower = needle.lower()
        exact = [
            e for e in entries
            if lower == str(e.get("name", "")).lower()
            or lower in {str(a).lower() for a in e.get("aliases") or []}
        ]
    if not exact:
        scored = [
            (_official_score(e, needle), e) for e in entries
            if _official_score(e, needle) > 0
        ]
        scored.sort(key=lambda item: (-item[0], str(item[1].get("name", "")).lower()))
        exact = [item[1] for item in scored[:5]]
    if prefer_loadable and app_profile:
        loadable = [
            e for e in exact
            if any(
                item.get("app_profile") == app_profile
                for item in e.get("loadable_in") or []
            )
        ]
        if loadable:
            return loadable[0]
    return exact[0] if exact else None


def _official_verify_required(
    catalog: dict[str, Any],
    entry: dict[str, Any],
    app_profile: str | None,
) -> bool:
    if _official_stale_warning(catalog, entry, app_profile):
        return True
    status = _official_entry_status(entry, app_profile)
    required_status = (
        "assign_verified" if entry.get("kind") == "material" else "load_verified"
    )
    if _official_status_rank(status) < _official_status_rank(required_status):
        return True
    if app_profile and not any(
        item.get("app_profile") == app_profile
        for item in entry.get("loadable_in") or []
    ):
        return True
    return False


def _official_stale_warning(
    catalog: dict[str, Any],
    entry: dict[str, Any],
    app_profile: str | None,
) -> str | None:
    if entry.get("stale"):
        return "Official asset entry is marked stale; run official_asset_verify before use."
    relevant_profiles = [app_profile] if app_profile else _entry_profiles(entry)
    snapshots = {
        str(s.get("app_profile")): s for s in catalog.get("snapshots") or []
    }
    stale_profiles = []
    for profile in relevant_profiles:
        snapshot = snapshots.get(str(profile))
        if not snapshot:
            continue
        warning = _official_snapshot_stale_warning(catalog, snapshot)
        if warning:
            stale_profiles.append(f"{profile}: {warning}")
    if stale_profiles:
        return "; ".join(stale_profiles)
    return None


def _entry_profiles(entry: dict[str, Any]) -> list[str]:
    profiles = []
    for item in list(entry.get("provided_in") or []) + list(entry.get("loadable_in") or []):
        profile = item.get("app_profile")
        if profile and profile not in profiles:
            profiles.append(str(profile))
    if entry.get("app_profile") and entry.get("app_profile") not in profiles:
        profiles.append(str(entry.get("app_profile")))
    return profiles


def _official_snapshot_is_stale(
    catalog: dict[str, Any],
    snapshot: dict[str, Any],
) -> bool:
    return _official_snapshot_stale_warning(catalog, snapshot) is not None


def _official_snapshot_stale_warning(
    catalog: dict[str, Any],
    snapshot: dict[str, Any],
) -> str | None:
    if snapshot.get("stale"):
        return "snapshot metadata is marked stale"
    generated = snapshot.get("generated_at") or catalog.get("generated_at")
    parsed = _parse_iso_datetime(str(generated or ""))
    if parsed is None:
        return "snapshot generated_at is missing or invalid"
    age_days = (datetime.now(timezone.utc) - parsed).days
    if age_days > _OFFICIAL_MAX_AGE_DAYS:
        return (
            f"snapshot is {age_days} days old "
            f"(max {_OFFICIAL_MAX_AGE_DAYS}); verify before use"
        )
    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _official_counts(
    entries: list[dict[str, Any]],
    app_profile: str | None,
) -> dict[str, int]:
    counts = {
        "items": len(entries),
        "asset": 0,
        "material": 0,
        "discovered": 0,
        "url_validated": 0,
        "inspect_verified": 0,
        "load_verified": 0,
        "assign_verified": 0,
        "failed": 0,
    }
    for entry in entries:
        kind = str(entry.get("kind") or "asset")
        if kind in counts:
            counts[kind] += 1
        status = _official_entry_status(entry, app_profile)
        if status in counts:
            counts[status] += 1
    return counts


def _official_material_name(entry: dict[str, Any]) -> str:
    value = entry.get("material_name")
    if value:
        return str(value)
    name = str(entry.get("name") or _url_name(str(entry.get("canonical_url", ""))))
    return re.sub(r"\.(mdl|usd|usda)$", "", name, flags=re.IGNORECASE)


_BBOX_EPSILON = 1.0e-9
_BBOX_SENTINEL_ABS_LIMIT = 1.0e12


def official_asset_load_quality_evidence(
    load: dict[str, Any],
    bbox: dict[str, Any],
    inspect: dict[str, Any],
) -> dict[str, Any]:
    """Classify an on-stage asset load using API, bbox, and USD inspect evidence."""
    load_ok = bool(load.get("ok", True))
    bbox_ok = bool(bbox.get("ok", True))
    inspect_ok = bool(inspect.get("ok", True))
    bbox_reasons = _official_bbox_invalid_reasons(bbox)
    bbox_valid = not bbox_reasons
    prim_count = _official_int(inspect.get("prim_count"))
    prim_count_valid = prim_count is not None and prim_count > 0
    has_authored_children = bool(
        load.get("has_authored_children") or load.get("has_children")
    )
    has_default_prim = bool(str(inspect.get("default_prim") or "").strip())
    has_content_evidence = (
        has_authored_children or has_default_prim or prim_count_valid
    )

    if not (load_ok and bbox_ok and inspect_ok):
        quality = "failed"
        warning = "load, bbox, or inspect call failed"
    elif not has_content_evidence:
        quality = "empty_content"
        warning = "no authored child, default prim, or prim_count evidence"
    elif not bbox_valid:
        quality = "content_verified_no_bbox"
        warning = "invalid bbox evidence: " + ", ".join(bbox_reasons)
    else:
        quality = "valid"
        warning = None

    return {
        "load_quality": quality,
        "load_quality_warning": warning,
        "load_ok": load_ok,
        "bbox_ok": bbox_ok,
        "inspect_ok": inspect_ok,
        "bbox_valid": bbox_valid,
        "bbox_validation_reasons": bbox_reasons,
        "has_authored_children": has_authored_children,
        "has_default_prim": has_default_prim,
        "prim_count_valid": prim_count_valid,
    }


def _official_bbox_invalid_reasons(bbox: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if bool(bbox.get("is_empty")):
        reasons.append("empty_flag")
    bbox_min = _official_float_triplet(bbox.get("min") or bbox.get("bbox_min"))
    bbox_max = _official_float_triplet(bbox.get("max") or bbox.get("bbox_max"))
    if bbox_min is None or bbox_max is None:
        reasons.append("missing_or_nonfinite_min_max")
        return reasons
    if any(lo > hi for lo, hi in zip(bbox_min, bbox_max, strict=True)):
        reasons.append("min_greater_than_max")
    if any(
        abs(value) > _BBOX_SENTINEL_ABS_LIMIT
        for value in [*bbox_min, *bbox_max]
    ):
        reasons.append("sentinel_magnitude")
    extent = [hi - lo for lo, hi in zip(bbox_min, bbox_max, strict=True)]
    if all(abs(value) <= _BBOX_EPSILON for value in extent):
        reasons.append("zero_extent")
    return reasons


def _official_float_triplet(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        triplet = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in triplet):
        return None
    return triplet


def _official_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_prim_name(entry: dict[str, Any]) -> str:
    stem = re.sub(
        r"\.(usd|usda|mdl)$",
        "",
        str(entry.get("name") or _url_name(str(entry.get("canonical_url", "")))),
        flags=re.IGNORECASE,
    )
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_")
    if not safe:
        return "Entry"
    if not re.match(r"[A-Za-z_]", safe):
        return f"Asset_{safe}"
    return safe


def _official_verify_record(
    entry: dict[str, Any],
    app_profile: str | None,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "id": entry.get("id"),
        "kind": entry.get("kind"),
        "name": entry.get("name"),
        "canonical_url": entry.get("canonical_url"),
        "app_profile": app_profile,
        "verification_status": status,
        "checked_at": now,
        "error": error,
    }


def _append_official_verify_record(
    catalog_dir: Path,
    record: dict[str, Any],
) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    path = catalog_dir / "verification-on-demand.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _conversion_output_path(cache_dir: str, asset_id: str, output_format: str) -> str:
    ext = output_format.strip().lower().lstrip(".") or "usd"
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", asset_id).strip("._") or "asset"
    return str(Path(cache_dir) / f"{safe_id}.{ext}")
