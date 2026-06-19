"""Sync generated NVIDIA official asset/material catalog snapshots.

The script writes only JSON/JSONL artifacts under the ignored
docs/references/official-assets/ directory. It never launches Kit. For
--verify full, start or attach the relevant app from workspaces/<app>/instance-1
first, then run this script against that already-running REST bridge.
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import copy
import datetime as dt
import json
import os
import re
import sys
import time
import tomllib
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import parse, request
import xml.etree.ElementTree as ET

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from omniverse_kit_mcp.modules.asset_module import (  # noqa: E402
    OFFICIAL_ASSET_LOAD_VERIFIED_QUALITIES,
    official_asset_load_quality_evidence,
)
from omniverse_kit_mcp.types.profile import get_profile  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "references" / "official-assets"
BASE_PATH = "/validation/v1"
CLEANUP_TIMEOUT_S = 10.0

PROVIDERS = (
    "omni.kit.browser.asset",
    "omni.simready.explorer",
    "omni.kit.browser.material",
)
MATERIAL_OVERRIDE_EXT = "omni.kit.browser.material"
ALLOWLISTED_PATH_ENV_KEYS = frozenset(
    {
        "ISAAC_SIM_ROOT",
        "USD_COMPOSER_ROOT",
        "ISAAC_SIM_KIT_FILE",
        "ISAAC_SIM_KIT_EXE",
        "USD_COMPOSER_KIT_FILE",
        "USD_COMPOSER_KIT_EXE",
    }
)

PROFILE_SOURCE_DIRS = {
    "isaac-sim": ("exts", "extscache", "extsDeprecated", "extsInternal", "kit/extscore"),
    "usd-composer": ("exts", "extscache", "extsbuild", "kit/extscore"),
}
PROFILE_VERSION_HINTS = {
    "isaac-sim": {"app_version": "6.0.0", "kit_version": "110.1.1"},
    "usd-composer": {"app_version": "usd-composer", "kit_version": None},
}
PROFILE_ROOT_ENV = {
    "isaac-sim": "ISAAC_SIM_ROOT",
    "usd-composer": "USD_COMPOSER_ROOT",
}
PROFILE_KIT_FILE_ENV = {
    "isaac-sim": "ISAAC_SIM_KIT_FILE",
    "usd-composer": "USD_COMPOSER_KIT_FILE",
}
PROFILE_KIT_EXE_ENV = {
    "isaac-sim": "ISAAC_SIM_KIT_EXE",
    "usd-composer": "USD_COMPOSER_KIT_EXE",
}
PROFILE_BASE_URLS = {
    "isaac-sim": "http://127.0.0.1:8111",
    "usd-composer": "http://127.0.0.1:8114",
}

VERSION_TAG_RE = re.compile(r"-\d+\.\d+.*$")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
QUOTED_RE = re.compile(r"[\"']([^\"']+)[\"']")
LINE_QUOTED_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'')
CONTENT_HINT_RE = re.compile(
    r"(omniverse-content|/Assets/|Assets/|Materials/|simready|vMaterials)",
    re.IGNORECASE,
)
ASSET_SUFFIX_RE = re.compile(r"\.(usd|usda)$", re.IGNORECASE)
MATERIAL_SUFFIX_RE = re.compile(r"\.(mdl|usd|usda)$", re.IGNORECASE)
URL_VALIDATION_WORKERS = 16


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def item_id(canonical_url: str) -> str:
    return f"url:{canonical_url.strip()}"


def strip_version_tag(dirname: str) -> str:
    return VERSION_TAG_RE.sub("", dirname)


def profile_slug(profile_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", profile_name.strip()).strip("-") or profile_name


def profile_latest_name(profile_name: str) -> str:
    return f"latest-{profile_slug(profile_name)}.json"


def _parse_env_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def load_allowlisted_env_values(paths: list[Path] | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths or allowlisted_env_paths():
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw_value = stripped.split("=", 1)
            key = key.strip()
            if key in ALLOWLISTED_PATH_ENV_KEYS:
                values[key] = _parse_env_value(raw_value)
    values.update(load_allowlisted_config_env_values())
    return values


def allowlisted_env_paths() -> list[Path]:
    paths = [PROJECT_ROOT / ".env"]
    workspace_root = PROJECT_ROOT / "workspaces"
    for profile_dir in ("isaac", "usd-composer"):
        base = workspace_root / profile_dir
        paths.append(base / ".env")
        for instance in ("instance-1", "instance-2"):
            paths.append(base / instance / ".env")
    return paths


def load_allowlisted_config_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    workspace_root = PROJECT_ROOT / "workspaces"
    for profile_dir in ("isaac", "usd-composer"):
        for instance in ("instance-1", "instance-2"):
            instance_dir = workspace_root / profile_dir / instance
            values.update(_read_mcp_json_env(instance_dir / ".mcp.json"))
            values.update(_read_codex_toml_env(instance_dir / ".codex" / "config.toml"))
    return values


def _filter_allowlisted_env(raw: dict[str, Any]) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in raw.items()
        if key in ALLOWLISTED_PATH_ENV_KEYS and value is not None
    }


def _read_mcp_json_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    values: dict[str, str] = {}
    for server in (data.get("mcpServers") or {}).values():
        if isinstance(server, dict):
            values.update(_filter_allowlisted_env(server.get("env") or {}))
    return values


def _read_codex_toml_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = read_toml(path)
    values: dict[str, str] = {}
    for server in (data.get("mcp_servers") or {}).values():
        if isinstance(server, dict):
            values.update(_filter_allowlisted_env(server.get("env") or {}))
    return values


def allowlisted_env_value(name: str) -> str | None:
    return os.environ.get(name) or load_allowlisted_env_values().get(name)


def profile_root(profile_name: str) -> Path:
    env_name = PROFILE_ROOT_ENV.get(profile_name)
    if env_name and allowlisted_env_value(env_name):
        return Path(str(allowlisted_env_value(env_name)))
    kit_file = profile_kit_file(profile_name)
    if kit_file.parts and len(kit_file.parents) >= 2:
        return kit_file.parents[1]
    kit_exe = profile_kit_exe(profile_name)
    if kit_exe.parts and len(kit_exe.parents) >= 2:
        return kit_exe.parents[1]
    return Path(".")


def profile_kit_file(profile_name: str) -> Path:
    env_name = PROFILE_KIT_FILE_ENV.get(profile_name)
    if env_name and allowlisted_env_value(env_name):
        return Path(str(allowlisted_env_value(env_name)))
    return Path(get_profile(profile_name).kit_file)


def profile_kit_exe(profile_name: str) -> Path:
    env_name = PROFILE_KIT_EXE_ENV.get(profile_name)
    if env_name and allowlisted_env_value(env_name):
        return Path(str(allowlisted_env_value(env_name)))
    return Path(get_profile(profile_name).kit_exe)


def profile_versions(profile_name: str) -> dict[str, str | None]:
    return dict(PROFILE_VERSION_HINTS.get(profile_name, {}))


def read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def find_extension_dir(root: Path, profile_name: str, ext_id: str) -> Path | None:
    for source_dir in PROFILE_SOURCE_DIRS.get(profile_name, ()):
        base = root / source_dir
        if not base.is_dir():
            continue
        for candidate in sorted(base.iterdir()):
            if candidate.is_dir() and strip_version_tag(candidate.name) == ext_id:
                return candidate
    return None


def extension_version(ext_dir: Path | None) -> str | None:
    if ext_dir is None:
        return None
    data = read_toml(ext_dir / "config" / "extension.toml")
    version = (data.get("package") or {}).get("version")
    return str(version) if version is not None else None


def relevant_files(ext_dir: Path) -> list[Path]:
    if not ext_dir or not ext_dir.is_dir():
        return []
    files: list[Path] = []
    for pattern in ("*.toml", "*.kit", "*.json", "*.py"):
        files.extend(ext_dir.rglob(pattern))
    return [p for p in files if p.is_file()]


def normalize_root(url: str) -> str:
    cleaned = url.strip().rstrip("),]")
    cleaned = cleaned.replace("\\", "/")
    if cleaned.endswith(("'", '"')):
        cleaned = cleaned[:-1]
    return cleaned.rstrip("/")


def discover_extension_roots(ext_dir: Path | None) -> list[str]:
    roots: list[str] = []
    if ext_dir is None:
        return roots
    for path in relevant_files(ext_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in URL_RE.findall(text):
            if CONTENT_HINT_RE.search(match):
                roots.append(normalize_root(match))
        for quoted in QUOTED_RE.findall(text):
            if CONTENT_HINT_RE.search(quoted) and quoted.startswith("http"):
                roots.append(normalize_root(quoted))
    return stable_unique(roots)


def discover_material_overrides(app_kit: Path) -> list[str]:
    if not app_kit.is_file():
        return []
    try:
        text = app_kit.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    overrides = []
    in_material_section = False
    saw_material_section = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_material_section = (
                stripped.startswith("[settings.exts.")
                and MATERIAL_OVERRIDE_EXT in stripped
            )
            saw_material_section = saw_material_section or in_material_section
            continue
        if not in_material_section:
            continue
        for quoted in line_quoted_values(raw_line):
            override = normalize_material_override(quoted)
            if override:
                overrides.append(override)
    if not saw_material_section:
        for quoted in QUOTED_RE.findall(text):
            override = normalize_material_override(quoted)
            if override:
                overrides.append(override)
    return stable_unique(overrides)


def line_quoted_values(line: str) -> list[str]:
    values = []
    for match in LINE_QUOTED_RE.finditer(line):
        values.append(match.group(1) if match.group(1) is not None else match.group(2))
    return values


def normalize_material_override(value: str) -> str | None:
    cleaned = value.replace("\\", "/").strip().strip(",")
    if "::" in cleaned:
        _label, _sep, rhs = cleaned.partition("::")
        if rhs.startswith("http"):
            cleaned = rhs
    if not CONTENT_HINT_RE.search(cleaned):
        return None
    if "Materials/" not in cleaned and "vMaterials" not in cleaned:
        return None
    if cleaned.startswith("http"):
        return normalize_root(cleaned)
    return cleaned.strip("/")


def apply_material_overrides(roots: list[str], overrides: list[str]) -> list[str]:
    if not overrides:
        return roots
    absolute = [normalize_root(o) for o in overrides if o.startswith("http")]
    relative = [o for o in overrides if not o.startswith("http")]
    if not relative:
        return stable_unique(roots + absolute)
    bases = [r for r in roots if "/Assets" in r]
    if not bases:
        return stable_unique(roots + absolute)
    expanded = []
    for base in bases:
        prefix = base.split("/Assets", 1)[0] + "/Assets"
        for rel in relative:
            expanded.append(f"{prefix}/{rel.strip('/')}")
    return stable_unique(absolute + expanded)


def provider_roots_for_profile(
    profile_name: str,
    enabled_providers: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = profile_root(profile_name)
    app_kit = profile_kit_file(profile_name)
    providers = []
    errors = []
    overrides = discover_material_overrides(app_kit)
    for provider in PROVIDERS:
        if enabled_providers is not None and provider not in enabled_providers:
            continue
        ext_dir = find_extension_dir(root, profile_name, provider)
        roots = discover_extension_roots(ext_dir)
        if provider == "omni.kit.browser.material":
            roots = apply_material_overrides(roots, overrides)
        if not roots:
            errors.append(
                {
                    "app_profile": profile_name,
                    "provider": provider,
                    "error": "provider roots not found in static extension/app settings",
                    "extension_dir": str(ext_dir) if ext_dir else None,
                }
            )
        providers.append(
            {
                "provider": provider,
                "extension_id": provider,
                "extension_version": extension_version(ext_dir),
                "extension_dir": str(ext_dir) if ext_dir else None,
                "source_roots": roots,
                "material_overrides": overrides if provider == "omni.kit.browser.material" else [],
            }
        )
    return providers, errors


def stable_unique(values: list[str]) -> list[str]:
    out = []
    seen = set()
    for value in values:
        key = value.lower()
        if value and key not in seen:
            out.append(value)
            seen.add(key)
    return out


def load_progress(path: Path, run_id: str) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": utc_now(),
        "updated_at": None,
        "profiles": {},
        "errors": [],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def s3_list_url(url: str, continuation_token: str | None = None) -> str | None:
    parsed = parse.urlparse(url)
    if not parsed.scheme.startswith("http") or ".s3" not in parsed.netloc:
        return None
    prefix = parsed.path.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    query = {
        "list-type": "2",
        "prefix": prefix,
        "max-keys": "1000",
    }
    if continuation_token:
        query["continuation-token"] = continuation_token
    return parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/", "", parse.urlencode(query), "")
    )


def list_s3_objects(root_url: str, max_entries: int) -> tuple[list[str], list[str]]:
    listing_url = s3_list_url(root_url)
    if listing_url is None:
        return ([root_url] if root_url.lower().endswith((".usd", ".usda", ".mdl")) else []), []
    parsed_root = parse.urlparse(root_url)
    urls: list[str] = []
    errors: list[str] = []
    token: str | None = None
    while True:
        current = s3_list_url(root_url, token)
        if current is None:
            break
        try:
            with request.urlopen(current, timeout=30) as response:
                payload = response.read()
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            break
        xml = ET.fromstring(payload)
        ns = ""
        if xml.tag.startswith("{"):
            ns = xml.tag.split("}", 1)[0] + "}"
        for contents in xml.findall(f"{ns}Contents"):
            key = contents.findtext(f"{ns}Key")
            if not key:
                continue
            urls.append(parse.urlunparse((parsed_root.scheme, parsed_root.netloc, "/" + key, "", "", "")))
            if len(urls) >= max_entries:
                return urls, errors
        truncated = (xml.findtext(f"{ns}IsTruncated") or "").lower() == "true"
        token = xml.findtext(f"{ns}NextContinuationToken")
        if not truncated or not token:
            break
    return urls, errors


def validate_url(url: str) -> tuple[str, str | None]:
    req = request.Request(url, method="HEAD")
    try:
        with request.urlopen(req, timeout=15) as response:
            status = getattr(response, "status", 200)
        return ("url_validated" if status < 400 else "failed"), None
    except urlerror.HTTPError as exc:
        if exc.code == 405:
            return validate_url_get(url)
        return "failed", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return "failed", str(exc)


def validate_url_get(url: str) -> tuple[str, str | None]:
    req = request.Request(url, headers={"Range": "bytes=0-0"})
    try:
        with request.urlopen(req, timeout=15) as response:
            status = getattr(response, "status", 200)
        return ("url_validated" if status < 400 else "failed"), None
    except Exception as exc:  # noqa: BLE001
        return "failed", str(exc)


def item_from_url(
    url: str,
    profile_name: str,
    provider: dict[str, Any],
    root_url: str,
    verify_mode: str,
) -> dict[str, Any] | None:
    suffix_ok = MATERIAL_SUFFIX_RE.search(url) if provider["provider"] == "omni.kit.browser.material" else ASSET_SUFFIX_RE.search(url)
    if not suffix_ok:
        return None
    kind = "material" if provider["provider"] == "omni.kit.browser.material" or url.lower().endswith(".mdl") else "asset"
    status = "discovered"
    error_text = None
    if verify_mode in {"url", "full"}:
        status, error_text = validate_url(url)
    name = url.rsplit("/", 1)[-1]
    versions = profile_versions(profile_name)
    provided = {
        "app_profile": profile_name,
        "app_version": versions.get("app_version"),
        "kit_version": versions.get("kit_version"),
        "provider": provider["provider"],
        "extension_id": provider.get("extension_id"),
        "extension_version": provider.get("extension_version"),
        "source_root": root_url,
        "category": category_from_url(url, root_url),
    }
    item = {
        "id": item_id(url),
        "kind": kind,
        "name": name,
        "aliases": aliases_for_url(url),
        "canonical_url": url,
        "provider": provider["provider"],
        "source_root": root_url,
        "category": provided["category"],
        "app_profile": profile_name,
        "app_version": versions.get("app_version"),
        "kit_version": versions.get("kit_version"),
        "extension_id": provider.get("extension_id"),
        "extension_version": provider.get("extension_version"),
        "provided_in": [provided],
        "loadable_in": [],
        "verification_status": status,
        "checked_at": utc_now() if verify_mode in {"url", "full"} else None,
        "error": error_text,
    }
    if kind == "material":
        item["material_name"] = re.sub(r"\.(mdl|usd|usda)$", "", name, flags=re.IGNORECASE)
    return item


def items_from_urls(
    urls: list[str],
    profile_name: str,
    provider: dict[str, Any],
    root_url: str,
    verify_mode: str,
) -> list[dict[str, Any]]:
    if verify_mode not in {"url", "full"}:
        return [
            item
            for url in urls
            if (item := item_from_url(url, profile_name, provider, root_url, verify_mode))
            is not None
        ]
    if not urls:
        return []
    workers = min(URL_VALIDATION_WORKERS, len(urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(
            lambda url: item_from_url(url, profile_name, provider, root_url, verify_mode),
            urls,
        )
        return [item for item in results if item is not None]


def category_from_url(url: str, root_url: str) -> str | None:
    rel = url[len(root_url):].strip("/") if url.startswith(root_url) else url
    parts = [p for p in rel.split("/") if p]
    if len(parts) > 1:
        return parts[0]
    return None


def aliases_for_url(url: str) -> list[str]:
    name = url.rsplit("/", 1)[-1]
    stem = re.sub(r"\.(usd|usda|mdl)$", "", name, flags=re.IGNORECASE)
    parts = [p for p in url.split("/") if p and not p.startswith("http")]
    aliases = [stem]
    aliases.extend(parts[-4:-1])
    return stable_unique(aliases)


def merge_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item["id"]
        if key not in merged:
            merged[key] = dict(item)
            continue
        target = merged[key]
        target["aliases"] = stable_unique(target.get("aliases", []) + item.get("aliases", []))
        target["provided_in"] = dedupe_dicts(target.get("provided_in", []) + item.get("provided_in", []))
        target["loadable_in"] = dedupe_dicts(target.get("loadable_in", []) + item.get("loadable_in", []))
        if status_rank(item.get("verification_status")) > status_rank(target.get("verification_status")):
            target["verification_status"] = item.get("verification_status")
            target["checked_at"] = item.get("checked_at")
            target["error"] = item.get("error")
    return sorted(merged.values(), key=lambda item: (item.get("kind", ""), item.get("canonical_url", "")))


def dedupe_dicts(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            out.append(value)
            seen.add(key)
    return out


def status_rank(status: Any) -> int:
    ranks = {
        "failed": -1,
        "stale": -1,
        "discovered": 0,
        "url_validated": 1,
        "inspect_verified": 2,
        "load_verified": 3,
        "assign_verified": 3,
        "skipped": 3,
    }
    return ranks.get(str(status or "discovered"), 0)


def counts_for(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "items": len(items),
        "asset": 0,
        "material": 0,
        "discovered": 0,
        "url_validated": 0,
        "inspect_verified": 0,
        "load_verified": 0,
        "assign_verified": 0,
        "failed": 0,
        "skipped": 0,
    }
    for item in items:
        kind = item.get("kind", "asset")
        if kind in counts:
            counts[kind] += 1
        status = item.get("verification_status", "discovered")
        if status in counts:
            counts[status] += 1
    return counts


async def rest_get(
    client: httpx.AsyncClient,
    path: str,
    request_timeout_s: float | None = None,
    **params: Any,
) -> dict[str, Any]:
    response = await client.get(
        path,
        params={k: v for k, v in params.items() if v is not None},
        timeout=request_timeout_s,
    )
    response.raise_for_status()
    return response.json()


async def rest_post(
    client: httpx.AsyncClient,
    path: str,
    payload: dict[str, Any] | None = None,
    request_timeout_s: float | None = None,
) -> dict[str, Any]:
    response = await client.post(path, json=payload or {}, timeout=request_timeout_s)
    response.raise_for_status()
    return response.json()


async def rest_delete(
    client: httpx.AsyncClient,
    path: str,
    request_timeout_s: float | None = None,
    **params: Any,
) -> dict[str, Any]:
    response = await client.delete(path, params=params, timeout=request_timeout_s)
    response.raise_for_status()
    return response.json()


async def verify_one(
    client: httpx.AsyncClient,
    item: dict[str, Any],
    profile_name: str,
    asset_timeout_s: float,
    material_timeout_s: float,
    retry: int,
) -> dict[str, Any]:
    timeout = material_timeout_s if item.get("kind") == "material" else asset_timeout_s
    last: dict[str, Any] | None = None
    for attempt in range(1, retry + 2):
        started = time.perf_counter()
        try:
            record = await asyncio.wait_for(
                verify_material(client, item, profile_name, timeout)
                if item.get("kind") == "material"
                else verify_asset(client, item, profile_name, timeout),
                timeout=timeout,
            )
            record["attempt"] = attempt
            record["timeout_s"] = timeout
            record["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
            last = record
            if record.get("verification_status") != "failed":
                break
        except Exception as exc:  # noqa: BLE001
            last = base_verify_record(item, profile_name, "failed", str(exc))
            last["error_code"] = type(exc).__name__
            last["error_message"] = str(exc)
            last["attempt"] = attempt
            last["timeout_s"] = timeout
            last["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    assert last is not None
    return last


async def ensure_stopped(client: httpx.AsyncClient, request_timeout_s: float) -> None:
    status = await rest_get(client, f"{BASE_PATH}/simulation/status", request_timeout_s=request_timeout_s)
    if status.get("is_playing"):
        await rest_post(client, f"{BASE_PATH}/simulation/stop", request_timeout_s=request_timeout_s)


async def cleanup_prim(client: httpx.AsyncClient, prim_path: str) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(
            rest_delete(
                client,
                f"{BASE_PATH}/stage/prim",
                prim_path=prim_path,
                request_timeout_s=CLEANUP_TIMEOUT_S,
            ),
            timeout=CLEANUP_TIMEOUT_S + 1.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(exc),
            "error_code": type(exc).__name__,
            "timeout_s": CLEANUP_TIMEOUT_S,
        }


async def verify_asset(
    client: httpx.AsyncClient,
    item: dict[str, Any],
    profile_name: str,
    request_timeout_s: float,
) -> dict[str, Any]:
    prim_path = f"/World/OfficialAssetVerify/{safe_name(item)}"
    record = base_verify_record(item, profile_name, "failed", None)
    try:
        await ensure_stopped(client, request_timeout_s)
        load = await rest_post(
            client,
            f"{BASE_PATH}/stage/load_usd",
            {"usd_url": item["canonical_url"], "prim_path": prim_path, "position": None, "rotation": None},
            request_timeout_s=request_timeout_s,
        )
        bbox = await rest_post(
            client,
            f"{BASE_PATH}/stage/compute_world_bbox",
            {"prim_path": prim_path, "include_purposes": ["default", "render"]},
            request_timeout_s=request_timeout_s,
        )
        inspect = await rest_post(
            client,
            f"{BASE_PATH}/content/inspect",
            {"url": item["canonical_url"]},
            request_timeout_s=request_timeout_s,
        )
        quality = official_asset_load_quality_evidence(load, bbox, inspect)
        load_verified = (
            quality["load_quality"] in OFFICIAL_ASSET_LOAD_VERIFIED_QUALITIES
        )
        record.update(
            {
                "verification_status": "load_verified" if load_verified else "failed",
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
        record["cleanup"] = await cleanup_prim(client, prim_path)


async def verify_material(
    client: httpx.AsyncClient,
    item: dict[str, Any],
    profile_name: str,
    request_timeout_s: float,
) -> dict[str, Any]:
    prim_path = f"/World/OfficialMaterialVerify/{safe_name(item)}Target"
    material_name = item.get("material_name") or re.sub(
        r"\.(mdl|usd|usda)$", "", item.get("name", "Material"), flags=re.IGNORECASE
    )
    record = base_verify_record(item, profile_name, "failed", None)
    try:
        create = await rest_post(
            client,
            f"{BASE_PATH}/stage/create_prim",
            {"prim_path": prim_path, "prim_type": "Cube", "position": [0.0, 0.0, 0.0]},
            request_timeout_s=request_timeout_s,
        )
        assign = await rest_post(
            client,
            f"{BASE_PATH}/material/assign_mdl",
            {"prim_path": prim_path, "mdl_url": item["canonical_url"], "material_name": material_name},
            request_timeout_s=request_timeout_s,
        )
        bound = await rest_get(
            client,
            f"{BASE_PATH}/material/get_bound",
            prim_path=prim_path,
            request_timeout_s=request_timeout_s,
        )
        create_ok = bool(create.get("ok", True))
        assign_ok = bool(assign.get("ok", True))
        bound_ok = bool(bound.get("ok", True)) and bool(bound.get("material_path"))
        ok = create_ok and assign_ok and bound_ok
        record.update(
            {
                "verification_status": "assign_verified" if ok else "failed",
                "prim_path": prim_path,
                "material_name": material_name,
                "create_prim": create,
                "assign": assign,
                "bound": bound,
                "error": None if ok else "material assign or binding readback failed",
            }
        )
        return record
    finally:
        record["cleanup"] = await cleanup_prim(client, prim_path)


def base_verify_record(
    item: dict[str, Any],
    profile_name: str,
    status: str,
    error_text: str | None,
) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "kind": item.get("kind"),
        "name": item.get("name"),
        "canonical_url": item.get("canonical_url"),
        "provider": item.get("provider"),
        "source_root": item.get("source_root"),
        "category": item.get("category"),
        "extension_id": item.get("extension_id"),
        "app_profile": profile_name,
        "verification_status": status,
        "checked_at": utc_now(),
        "error": error_text,
    }


def safe_name(item: dict[str, Any]) -> str:
    stem = re.sub(r"\.(usd|usda|mdl)$", "", item.get("name", "Entry"), flags=re.IGNORECASE)
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_")
    if not safe:
        return "Entry"
    if not re.match(r"[A-Za-z_]", safe):
        return f"Asset_{safe}"
    return safe


async def verify_profile_items(
    profile_name: str,
    items: list[dict[str, Any]],
    outdir: Path,
    run_id: str,
    base_url: str,
    asset_timeout_s: float,
    material_timeout_s: float,
    retry: int,
    verify_kinds: set[str] | None = None,
    verify_providers: set[str] | None = None,
    verify_offset: int = 0,
    verify_limit: int | None = None,
    rerun_classified: bool = False,
) -> list[dict[str, Any]]:
    verify_log = outdir / "verification" / f"{run_id}.jsonl"
    verified: dict[str, dict[str, Any]] = {}
    if verify_log.is_file():
        for line in verify_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("app_profile") == profile_name:
                verified[str(record.get("id"))] = record

    candidates: list[dict[str, Any]] = []
    for item in items:
        item_id = str(item.get("id"))
        record = verified.get(item_id)
        if record and is_classified_status(record.get("verification_status")):
            update_item_with_verify_record(item, record)
            if not rerun_classified:
                continue
        elif is_classified_status(item.get("verification_status")) and not rerun_classified:
            continue
        if verify_kinds and str(item.get("kind")) not in verify_kinds:
            continue
        if verify_providers and str(item.get("provider")) not in verify_providers:
            continue
        candidates.append(item)
    if verify_offset:
        candidates = candidates[verify_offset:]
    if verify_limit is not None:
        candidates = candidates[:verify_limit]

    candidate_ids = {str(item.get("id")) for item in candidates}
    async with httpx.AsyncClient(base_url=base_url, timeout=None) as client:
        for item in items:
            if str(item.get("id")) not in candidate_ids:
                continue
            record = await verify_one(client, item, profile_name, asset_timeout_s, material_timeout_s, retry)
            append_jsonl(verify_log, record)
            update_item_with_verify_record(item, record)
            print(
                json.dumps(
                    {
                        "event": "verify_item",
                        "run_id": run_id,
                        "app_profile": profile_name,
                        "id": item.get("id"),
                        "provider": item.get("provider"),
                        "kind": item.get("kind"),
                        "verification_status": record.get("verification_status"),
                        "error": record.get("error"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return items


def is_classified_status(status: Any) -> bool:
    return str(status or "") in {"load_verified", "assign_verified", "failed", "skipped"}


def update_item_with_verify_record(item: dict[str, Any], record: dict[str, Any]) -> None:
    status = record.get("verification_status")
    item["verification_status"] = status
    item["checked_at"] = record.get("checked_at")
    item["error"] = record.get("error")
    for key in ("bbox", "meters_per_unit", "up_axis", "prim_count"):
        if key in record:
            item[key] = record[key]
    versions = profile_versions(str(record.get("app_profile")))
    if status in {"load_verified", "assign_verified"}:
        item["loadable_in"] = dedupe_dicts(
            item.get("loadable_in", [])
            + [
                {
                    "app_profile": record.get("app_profile"),
                    "app_version": versions.get("app_version"),
                    "kit_version": versions.get("kit_version"),
                    "verification_status": status,
                    "checked_at": record.get("checked_at"),
                    "elapsed_ms": record.get("elapsed_ms"),
                    "bbox": record.get("bbox"),
                    "meters_per_unit": record.get("meters_per_unit"),
                    "up_axis": record.get("up_axis"),
                    "prim_count": record.get("prim_count"),
                }
            ]
        )


def load_source_snapshots(
    outdir: Path,
    source_run_id: str,
    profiles: list[str],
) -> dict[str, dict[str, Any]]:
    path = outdir / "snapshots" / f"{source_run_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    requested = set(profiles)
    snapshots: dict[str, dict[str, Any]] = {}
    for snapshot in data.get("snapshots") or []:
        profile_name = str(snapshot.get("app_profile") or "")
        if profile_name in requested:
            snapshots[profile_name] = copy.deepcopy(snapshot)
            snapshots[profile_name]["source_run_id"] = source_run_id
    missing = sorted(requested - set(snapshots))
    if missing:
        raise SystemExit(f"source snapshot {path} missing profiles: {', '.join(missing)}")
    return snapshots


def verification_summary(
    run_id: str,
    catalog: dict[str, Any],
    verify_log: Path,
) -> dict[str, Any]:
    records: dict[tuple[str, str], dict[str, Any]] = {}
    if verify_log.is_file():
        for line in verify_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            records[(str(record.get("app_profile")), str(record.get("id")))] = record

    groups: dict[str, dict[str, Any]] = {}
    for snapshot in catalog.get("snapshots") or []:
        profile_name = str(snapshot.get("app_profile") or "unknown")
        for item in snapshot.get("items") or []:
            provider = str(item.get("provider") or "unknown")
            key = f"{profile_name}|{provider}"
            group = groups.setdefault(
                key,
                {
                    "app_profile": profile_name,
                    "provider": provider,
                    "total": 0,
                    "verified_usable": 0,
                    "failed_unusable": 0,
                    "skipped": 0,
                    "unclassified": 0,
                    "timeout_or_hang": 0,
                    "by_status": {},
                    "by_kind": {},
                    "skipped_reasons": {},
                },
            )
            item_id = str(item.get("id"))
            record = records.get((profile_name, item_id))
            status = str((record or item).get("verification_status") or "discovered")
            kind = str(item.get("kind") or "unknown")
            group["total"] += 1
            group["by_status"][status] = group["by_status"].get(status, 0) + 1
            group["by_kind"][kind] = group["by_kind"].get(kind, 0) + 1
            if status in {"load_verified", "assign_verified"}:
                group["verified_usable"] += 1
            elif status == "failed":
                group["failed_unusable"] += 1
            elif status == "skipped":
                group["skipped"] += 1
                reason = str((record or item).get("skip_reason") or (record or item).get("error") or "unspecified")
                group["skipped_reasons"][reason] = group["skipped_reasons"].get(reason, 0) + 1
            else:
                group["unclassified"] += 1
            error_code = str((record or {}).get("error_code") or "")
            error_text = str((record or item).get("error") or "")
            if "Timeout" in error_code or "timeout" in error_text.lower() or "hang" in error_text.lower():
                group["timeout_or_hang"] += 1

    return {
        "run_id": run_id,
        "generated_at": utc_now(),
        "verification_log": str(verify_log),
        "groups": sorted(groups.values(), key=lambda g: (g["app_profile"], g["provider"])),
    }


def write_verification_summary(outdir: Path, run_id: str, catalog: dict[str, Any]) -> Path:
    verify_log = outdir / "verification" / f"{run_id}.jsonl"
    summary = verification_summary(run_id, catalog, verify_log)
    path = outdir / "verification" / f"{run_id}-summary.json"
    write_json(path, summary)
    write_json(outdir / "verification" / "latest-summary.json", summary)
    return path


def discover_profile(
    profile_name: str,
    verify_mode: str,
    max_entries_per_root: int,
    progress: dict[str, Any],
    enabled_providers: set[str] | None = None,
) -> dict[str, Any]:
    providers, root_errors = provider_roots_for_profile(profile_name, enabled_providers)
    versions = profile_versions(profile_name)
    profile_progress = progress["profiles"].setdefault(profile_name, {"roots": {}})
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = list(root_errors)
    for provider in providers:
        for root_url in provider.get("source_roots") or []:
            root_state = profile_progress["roots"].setdefault(
                root_url,
                {"provider": provider["provider"], "listed": False, "count": 0, "errors": []},
            )
            urls, list_errors = list_s3_objects(root_url, max_entries=max_entries_per_root)
            root_state["listed"] = True
            root_state["count"] = len(urls)
            root_state["errors"] = list_errors
            for err in list_errors:
                errors.append({"app_profile": profile_name, "provider": provider["provider"], "root": root_url, "error": err})
            items.extend(
                items_from_urls(urls, profile_name, provider, root_url, verify_mode)
            )
            progress["updated_at"] = utc_now()
    items = merge_items(items)
    return {
        "app_profile": profile_name,
        "app_version": versions.get("app_version"),
        "kit_version": versions.get("kit_version"),
        "generated_at": utc_now(),
        "providers": providers,
        "counts": counts_for(items),
        "errors": errors,
        "items": items,
    }


def build_catalog(run_id: str, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    all_items = []
    for snapshot in snapshots:
        all_items.extend(snapshot.get("items") or [])
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "generator": "scripts/sync_official_asset_catalog.py",
        "run_id": run_id,
        "artifact_policy": "json-only",
        "snapshots": snapshots,
        "items": merge_items(all_items),
    }


def write_latest_catalogs(
    outdir: Path,
    run_id: str,
    catalog: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Path]:
    written: dict[str, Path] = {}
    default_latest = outdir / "latest.json"
    write_json(default_latest, catalog)
    written["default"] = default_latest
    for snapshot in snapshots:
        profile_name = str(snapshot.get("app_profile") or "").strip()
        if not profile_name:
            continue
        profile_catalog = build_catalog(run_id, [snapshot])
        path = outdir / profile_latest_name(profile_name)
        write_json(path, profile_catalog)
        written[profile_name] = path
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", choices=sorted(PROFILE_SOURCE_DIRS), default=["isaac-sim", "usd-composer"])
    parser.add_argument("--providers", nargs="+", choices=PROVIDERS, default=list(PROVIDERS), help="Reserved for future narrowing; V1 discovers all providers.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ"))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--source-run-id", help="Use an existing snapshot run as discovery input instead of crawling providers again.")
    parser.add_argument("--verify", choices=["none", "url", "full"], default="url")
    parser.add_argument("--max-entries-per-root", type=int, default=20000)
    parser.add_argument("--verify-kind", action="append", choices=["asset", "material"], default=[], help="When --verify full, verify only these item kinds. Repeatable.")
    parser.add_argument("--verify-provider", action="append", default=[], help="When --verify full, verify only these providers. Repeatable.")
    parser.add_argument("--verify-offset", type=int, default=0, help="Skip this many not-yet-classified verification candidates after filtering.")
    parser.add_argument("--verify-limit", type=int, help="Verify at most this many not-yet-classified candidates after filtering.")
    parser.add_argument("--rerun-classified", action="store_true", help="Rerun items already classified in this run's verification JSONL or source snapshot.")
    parser.add_argument("--asset-timeout-s", type=float, default=120.0)
    parser.add_argument("--material-timeout-s", type=float, default=45.0)
    parser.add_argument("--retry", type=int, default=1)
    parser.add_argument("--base-url", action="append", default=[], help="Override profile REST base as profile=url, e.g. isaac-sim=http://127.0.0.1:8111")
    parser.add_argument("--allow-missing-roots", action="store_true", help="Write partial JSON even when a provider root cannot be explained; default exits non-zero.")
    return parser.parse_args()


def base_url_map(overrides: list[str]) -> dict[str, str]:
    result = dict(PROFILE_BASE_URLS)
    for override in overrides:
        profile, sep, url = override.partition("=")
        if sep and profile and url:
            result[profile] = url
    return result


async def amain() -> int:
    args = parse_args()
    outdir: Path = args.output_dir
    progress_path = outdir / "progress" / f"{args.run_id}.json"
    progress = load_progress(progress_path, args.run_id) if args.resume else load_progress(Path("__missing__"), args.run_id)
    snapshots = []
    urls = base_url_map(args.base_url)
    enabled_providers = set(args.providers) if args.providers else None
    source_snapshots = (
        load_source_snapshots(outdir, args.source_run_id, args.profiles)
        if args.source_run_id
        else {}
    )
    for profile_name in args.profiles:
        snapshot = source_snapshots.get(profile_name)
        if snapshot is None:
            snapshot = discover_profile(
                profile_name,
                args.verify,
                args.max_entries_per_root,
                progress,
                enabled_providers=enabled_providers,
            )
        if args.verify == "full":
            snapshot["items"] = await verify_profile_items(
                profile_name,
                snapshot["items"],
                outdir,
                args.run_id,
                urls[profile_name],
                args.asset_timeout_s,
                args.material_timeout_s,
                args.retry,
                verify_kinds=set(args.verify_kind) or None,
                verify_providers=set(args.verify_provider) or None,
                verify_offset=args.verify_offset,
                verify_limit=args.verify_limit,
                rerun_classified=args.rerun_classified,
            )
            snapshot["counts"] = counts_for(snapshot["items"])
        snapshots.append(snapshot)
        progress["updated_at"] = utc_now()
        write_json(progress_path, progress)
    catalog = build_catalog(args.run_id, snapshots)
    snapshot_path = outdir / "snapshots" / f"{args.run_id}.json"
    write_json(snapshot_path, catalog)
    latest_paths = write_latest_catalogs(outdir, args.run_id, catalog, snapshots)
    summary_path = write_verification_summary(outdir, args.run_id, catalog) if args.verify == "full" else None
    write_json(progress_path, progress)
    missing_root_errors = [
        err
        for snapshot in snapshots
        for err in snapshot.get("errors") or []
        if "provider roots not found" in str(err.get("error", ""))
    ]
    ok = not missing_root_errors or args.allow_missing_roots
    print(json.dumps({
        "ok": ok,
        "run_id": args.run_id,
        "latest": str(latest_paths["default"]),
        "profile_latest": {
            key: str(value) for key, value in latest_paths.items() if key != "default"
        },
        "snapshot": str(snapshot_path),
        "summary": str(summary_path) if summary_path else None,
        "counts": counts_for(catalog["items"]),
        "profile_counts": {s["app_profile"]: s["counts"] for s in snapshots},
        "errors": sum(len(s.get("errors") or []) for s in snapshots),
        "missing_root_errors": missing_root_errors,
    }, indent=2, ensure_ascii=False))
    return 0 if ok else 2


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
