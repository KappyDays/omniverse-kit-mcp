"""External free 3D asset providers and local ingest cache helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


DEFAULT_CACHE_ROOT = (
    Path(__file__).resolve().parents[3] / ".omniverse-kit-mcp" / "external_assets"
)
DEFAULT_PROVIDER_ORDER = ("polyhaven", "sketchfab")
DEFAULT_FORMAT_PREFERENCE = ("glb", "gltf", "usdz", "blend")
POLYHAVEN_USER_AGENT = "omniverse-kit-mcp/0.1 external-asset-ingest"
SKETCHFAB_TOKEN_ENV = "SKETCHFAB_API_TOKEN"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_SKETCHFAB_LICENSES = {
    "cc0",
    "by",
    "by-sa",
    "cc-by",
    "cc-by-sa",
    "cc attribution",
    "cc attribution-sharealike",
    "creative commons attribution",
    "creative commons attribution-sharealike",
}


@dataclass(slots=True, frozen=True)
class ExternalAssetCandidate:
    provider: str
    asset_id: str
    name: str
    license: str
    license_url: str | None
    author: str | None
    source_url: str
    available_formats: tuple[str, ...]
    requires_auth: bool
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["available_formats"] = list(self.available_formats)
        return data


@dataclass(slots=True, frozen=True)
class ExternalDownloadFile:
    path: str
    url: str
    size_bytes: int
    sha256: str


@dataclass(slots=True, frozen=True)
class ExternalDownloadResult:
    manifest_path: str
    cache_dir: str
    primary_file: str
    chosen_format: str
    candidate: ExternalAssetCandidate
    files: tuple[ExternalDownloadFile, ...]
    skipped_formats: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "cache_dir": self.cache_dir,
            "primary_file": self.primary_file,
            "chosen_format": self.chosen_format,
            "candidate": self.candidate.to_dict(),
            "files": [asdict(f) for f in self.files],
            "skipped_formats": list(self.skipped_formats),
        }


class ExternalAssetError(RuntimeError):
    """External asset ingest failure with a user-facing message."""


class ExternalAssetRegistry:
    """Provider registry plus ignored local cache/manifest management."""

    def __init__(
        self,
        cache_root: Path | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        sketchfab_token: str | None = None,
    ) -> None:
        self.cache_root = (cache_root or DEFAULT_CACHE_ROOT).resolve()
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._providers: dict[str, ExternalAssetProvider] = {
            "polyhaven": PolyHavenProvider(self._http),
            "sketchfab": SketchfabProvider(
                self._http, token=sketchfab_token or os.getenv(SKETCHFAB_TOKEN_ENV)
            ),
        }

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def search(
        self,
        query: str,
        providers: list[str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        requested = tuple(providers or DEFAULT_PROVIDER_ORDER)
        provider_rank = {name: index for index, name in enumerate(requested)}
        provider_status: dict[str, str] = {}
        candidates: list[ExternalAssetCandidate] = []
        for name in requested:
            provider = self._providers.get(name)
            if provider is None:
                provider_status[name] = "unknown_provider"
                continue
            if not provider.enabled:
                provider_status[name] = provider.disabled_reason or "disabled"
                continue
            try:
                hits = await provider.search(query=query, limit=limit)
            except Exception as exc:
                provider_status[name] = f"error:{type(exc).__name__}"
                continue
            provider_status[name] = "ok"
            candidates.extend(hits)
        candidates.sort(
            key=lambda c: (
                provider_rank.get(c.provider, len(provider_rank)),
                -c.score,
                c.name.lower(),
            )
        )
        return {
            "query": query,
            "provider_status": provider_status,
            "candidates": [c.to_dict() for c in candidates[:limit]],
        }

    async def download(
        self,
        provider_name: str,
        asset_id: str,
        format_preference: list[str] | None = None,
    ) -> ExternalDownloadResult:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ExternalAssetError(f"Unknown external asset provider: {provider_name}")
        if not provider.enabled:
            raise ExternalAssetError(provider.disabled_reason or f"{provider_name} is disabled")

        preference = tuple(format_preference or DEFAULT_FORMAT_PREFERENCE)
        plan = await provider.download_plan(asset_id=asset_id, format_preference=preference)
        candidate = plan["candidate"]
        chosen_format = str(plan["chosen_format"])
        file_specs = tuple(plan["files"])
        if not file_specs:
            raise ExternalAssetError(f"No downloadable files for {provider_name}:{asset_id}")

        fingerprint = _hash_text(f"{provider_name}:{asset_id}:{chosen_format}")[:12]
        cache_dir = self._asset_dir(provider_name, asset_id, fingerprint)
        cache_dir.mkdir(parents=True, exist_ok=True)

        downloaded: list[ExternalDownloadFile] = []
        for index, spec in enumerate(file_specs):
            url = str(spec["url"])
            filename = _safe_filename(str(spec.get("filename") or _filename_from_url(url)))
            if index == 0 and "." not in filename:
                filename = f"{filename}.{chosen_format}"
            path = _safe_child(cache_dir, filename)
            digest = hashlib.sha256()
            size = 0
            async with self._http.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with path.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        if not chunk:
                            continue
                        handle.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
            downloaded.append(
                ExternalDownloadFile(
                    path=str(path),
                    url=url,
                    size_bytes=size,
                    sha256=digest.hexdigest(),
                )
            )

        primary = downloaded[0].path
        manifest = {
            "schema_version": 1,
            "provider": provider_name,
            "asset_id": asset_id,
            "name": candidate.name,
            "source_url": candidate.source_url,
            "author": candidate.author,
            "license": candidate.license,
            "license_url": candidate.license_url,
            "downloaded_at_epoch_ms": int(time.time() * 1000),
            "cache_dir": str(cache_dir),
            "primary_file": primary,
            "chosen_format": chosen_format,
            "files": [asdict(f) for f in downloaded],
            "conversion": {"status": "not_started"},
        }
        manifest_path = cache_dir / "manifest.json"
        _write_json(manifest_path, manifest)
        return ExternalDownloadResult(
            manifest_path=str(manifest_path),
            cache_dir=str(cache_dir),
            primary_file=primary,
            chosen_format=chosen_format,
            candidate=candidate,
            files=tuple(downloaded),
            skipped_formats=tuple(plan.get("skipped_formats", ())),
        )

    def update_conversion(
        self,
        manifest_path: str,
        conversion_result: dict[str, Any],
    ) -> dict[str, Any]:
        manifest_file = _safe_existing_manifest(self.cache_root, manifest_path)
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest["conversion"] = {
            "status": "converted" if conversion_result.get("ok", True) else "error",
            "updated_at_epoch_ms": int(time.time() * 1000),
            **conversion_result,
        }
        _write_json(manifest_file, manifest)
        return manifest

    def read_manifest(self, manifest_path: str) -> dict[str, Any]:
        manifest_file = _safe_existing_manifest(self.cache_root, manifest_path)
        return json.loads(manifest_file.read_text(encoding="utf-8"))

    def _asset_dir(self, provider: str, asset_id: str, fingerprint: str) -> Path:
        return _safe_child(
            _safe_child(self.cache_root, _safe_filename(provider)),
            f"{_safe_filename(asset_id)}-{fingerprint}",
        )


class ExternalAssetProvider:
    name: str = ""
    enabled: bool = True
    disabled_reason: str | None = None

    async def search(self, query: str, limit: int) -> list[ExternalAssetCandidate]:
        raise NotImplementedError

    async def download_plan(
        self, asset_id: str, format_preference: tuple[str, ...]
    ) -> dict[str, Any]:
        raise NotImplementedError


class PolyHavenProvider(ExternalAssetProvider):
    name = "polyhaven"

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    async def search(self, query: str, limit: int) -> list[ExternalAssetCandidate]:
        response = await self._http.get(
            "https://api.polyhaven.com/assets",
            params={"type": "models"},
            headers={"User-Agent": POLYHAVEN_USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()
        tokens = _tokens(query)
        hits: list[ExternalAssetCandidate] = []
        for asset_id, raw in data.items():
            name = str(raw.get("name") or asset_id)
            tags = " ".join(str(t) for t in raw.get("tags", []))
            categories = " ".join(str(t) for t in raw.get("categories", []))
            haystack = f"{asset_id} {name} {tags} {categories}".lower()
            score = _score_tokens(tokens, haystack, name.lower())
            if tokens and score <= 0:
                continue
            hits.append(
                ExternalAssetCandidate(
                    provider=self.name,
                    asset_id=str(asset_id),
                    name=name,
                    license="CC0",
                    license_url="https://polyhaven.com/license",
                    author="Poly Haven",
                    source_url=f"https://polyhaven.com/a/{asset_id}",
                    available_formats=tuple(DEFAULT_FORMAT_PREFERENCE),
                    requires_auth=False,
                    score=score,
                )
            )
        hits.sort(key=lambda c: (-c.score, c.name.lower()))
        return hits[:limit]

    async def download_plan(
        self, asset_id: str, format_preference: tuple[str, ...]
    ) -> dict[str, Any]:
        metadata = await self._get_json(f"https://api.polyhaven.com/info/{asset_id}")
        files = await self._get_json(f"https://api.polyhaven.com/files/{asset_id}")
        candidate = ExternalAssetCandidate(
            provider=self.name,
            asset_id=asset_id,
            name=str(metadata.get("name") or asset_id),
            license="CC0",
            license_url="https://polyhaven.com/license",
            author=str(metadata.get("authors") or "Poly Haven"),
            source_url=f"https://polyhaven.com/a/{asset_id}",
            available_formats=tuple(files.keys()),
            requires_auth=False,
            score=0.0,
        )
        chosen, file_specs, skipped = _select_polyhaven_files(files, format_preference)
        return {
            "candidate": candidate,
            "chosen_format": chosen,
            "files": file_specs,
            "skipped_formats": skipped,
        }

    async def _get_json(self, url: str) -> dict[str, Any]:
        response = await self._http.get(url, headers={"User-Agent": POLYHAVEN_USER_AGENT})
        response.raise_for_status()
        return response.json()


class SketchfabProvider(ExternalAssetProvider):
    name = "sketchfab"

    def __init__(self, http_client: httpx.AsyncClient, token: str | None) -> None:
        self._http = http_client
        self._token = token
        self.enabled = bool(token)
        self.disabled_reason = None if self.enabled else "disabled_missing_token"

    @property
    def _headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Token {self._token}"}

    async def search(self, query: str, limit: int) -> list[ExternalAssetCandidate]:
        response = await self._http.get(
            "https://api.sketchfab.com/v3/search",
            params={
                "type": "models",
                "downloadable": "true",
                "q": query,
                "count": str(limit),
            },
            headers=self._headers,
        )
        response.raise_for_status()
        hits: list[ExternalAssetCandidate] = []
        for raw in response.json().get("results", []):
            license_info = raw.get("license") or {}
            license_slug = str(license_info.get("slug") or license_info.get("label") or "").lower()
            if not _sketchfab_license_allowed(license_slug):
                continue
            user = raw.get("user") or {}
            uid = str(raw.get("uid") or raw.get("id") or "")
            if not uid:
                continue
            hits.append(
                ExternalAssetCandidate(
                    provider=self.name,
                    asset_id=uid,
                    name=str(raw.get("name") or uid),
                    license=license_slug,
                    license_url=license_info.get("url"),
                    author=user.get("displayName") or user.get("username"),
                    source_url=str(raw.get("viewerUrl") or raw.get("uri") or ""),
                    available_formats=("glb", "gltf", "usdz"),
                    requires_auth=True,
                    score=float(raw.get("likeCount") or 0),
                )
            )
        return hits

    async def download_plan(
        self, asset_id: str, format_preference: tuple[str, ...]
    ) -> dict[str, Any]:
        meta_response = await self._http.get(
            f"https://api.sketchfab.com/v3/models/{asset_id}",
            headers=self._headers,
        )
        meta_response.raise_for_status()
        metadata = meta_response.json()
        license_info = metadata.get("license") or {}
        license_slug = str(license_info.get("slug") or license_info.get("label") or "").lower()
        if not _sketchfab_license_allowed(license_slug):
            raise ExternalAssetError(f"Unsupported Sketchfab license: {license_slug}")

        dl_response = await self._http.get(
            f"https://api.sketchfab.com/v3/models/{asset_id}/download",
            headers=self._headers,
        )
        dl_response.raise_for_status()
        downloads = dl_response.json()
        chosen = ""
        spec: dict[str, Any] | None = None
        skipped: list[str] = []
        for fmt in format_preference:
            entry = downloads.get(fmt)
            if not entry or not entry.get("url"):
                skipped.append(fmt)
                continue
            chosen = fmt
            spec = {
                "url": entry["url"],
                "filename": f"{_safe_filename(metadata.get('name') or asset_id)}.{fmt}",
            }
            break
        if spec is None:
            raise ExternalAssetError(f"No supported Sketchfab download format for {asset_id}")
        user = metadata.get("user") or {}
        candidate = ExternalAssetCandidate(
            provider=self.name,
            asset_id=asset_id,
            name=str(metadata.get("name") or asset_id),
            license=license_slug,
            license_url=license_info.get("url"),
            author=user.get("displayName") or user.get("username"),
            source_url=str(metadata.get("viewerUrl") or metadata.get("uri") or ""),
            available_formats=tuple(downloads.keys()),
            requires_auth=True,
            score=0.0,
        )
        return {
            "candidate": candidate,
            "chosen_format": chosen,
            "files": (spec,),
            "skipped_formats": tuple(skipped),
        }


def _select_polyhaven_files(
    files: dict[str, Any], format_preference: tuple[str, ...]
) -> tuple[str, tuple[dict[str, str], ...], tuple[str, ...]]:
    skipped: list[str] = []
    for fmt in format_preference:
        raw = files.get(fmt)
        specs = _flatten_polyhaven_downloads(raw)
        if not specs:
            skipped.append(fmt)
            continue
        return fmt, tuple(specs), tuple(skipped)
    raise ExternalAssetError("No supported Poly Haven download format found")


def _flatten_polyhaven_downloads(raw: Any) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []

    def visit(node: Any, name_hint: str = "") -> None:
        if isinstance(node, dict):
            url = node.get("url")
            if isinstance(url, str):
                specs.append({"url": url, "filename": name_hint or _filename_from_url(url)})
            for key, value in node.items():
                if key == "url":
                    continue
                visit(value, str(key))
        elif isinstance(node, list):
            for item in node:
                visit(item, name_hint)

    visit(raw)
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for spec in specs:
        if spec["url"] in seen:
            continue
        seen.add(spec["url"])
        unique.append(spec)
    return unique


def _safe_existing_manifest(cache_root: Path, manifest_path: str) -> Path:
    path = Path(manifest_path).resolve()
    root = cache_root.resolve()
    if not path.is_file():
        raise ExternalAssetError(f"Manifest does not exist: {manifest_path}")
    if root not in path.parents:
        raise ExternalAssetError(f"Manifest path is outside external asset cache: {manifest_path}")
    if path.name != "manifest.json":
        raise ExternalAssetError("External asset manifest must be named manifest.json")
    return path


def _safe_child(parent: Path, child_name: str) -> Path:
    path = (parent / child_name).resolve()
    parent_resolved = parent.resolve()
    if parent_resolved != path and parent_resolved not in path.parents:
        raise ExternalAssetError(f"Unsafe external asset path: {child_name}")
    return path


def _safe_filename(value: object) -> str:
    text = _SAFE_NAME_RE.sub("_", str(value).strip()).strip("._")
    return text[:120] or "asset"


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or _hash_text(url)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if t]


def _score_tokens(tokens: list[str], haystack: str, name: str) -> float:
    if not tokens:
        return 0.0
    score = 0.0
    for token in tokens:
        if token in name:
            score += 10.0
        if token in haystack:
            score += 3.0
    return score


def _sketchfab_license_allowed(slug_or_label: str) -> bool:
    normalized = slug_or_label.lower().replace("_", "-").strip()
    return normalized in _ALLOWED_SKETCHFAB_LICENSES
