"""Isaac Sim 5.1 extension 전수 카탈로그 bootstrap.

Usage:
    uv run python scripts/harvest_extension_metadata.py [--resume]

상세 동작은 docs/superpowers/specs/2026-04-17-nvidia-reference-harvesting-design.md §5.3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ISAAC_SIM_ROOT = Path(
    "C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_JSON = PROJECT_ROOT / "docs" / "references" / "extensions.json"
PROGRESS_JSON = PROJECT_ROOT / "docs" / "references" / "harvest-progress.json"

SOURCE_DIRS = ("exts", "extscache", "extsDeprecated")
EXPECTED_COUNTS = {"exts": 97, "extscache": 452, "extsDeprecated": 72}

# VERSION_TAG_RE: 디렉토리명 뒤의 `-<digit>.<digit>...` 이후를 버전 태그로 간주.
# 주의: `omni.kit.loop-isaac` 처럼 `-<alpha>` 인 경우는 제거 안 함 (정규식 뒤에 \d 요구).
VERSION_TAG_RE = re.compile(r"-\d+\.\d+.*$")


def strip_version_tag(dirname: str) -> str:
    """`omni.physx.demos-107.3.26+107.3.3.cp311.u353` → `omni.physx.demos`."""
    return VERSION_TAG_RE.sub("", dirname)
