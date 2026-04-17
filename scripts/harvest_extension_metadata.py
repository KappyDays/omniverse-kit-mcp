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


# 도메인 분류 규칙 (spec §Appendix A). 위에서 아래 순서로 첫 매칭이 이김.
# 예외: extsDeprecated/ 는 assign_category() 의 source_dir_name 체크가 모든 규칙보다 먼저.
DOMAIN_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    ("Core Foundation", [
        re.compile(r"^isaacsim\.core\.(api|prims|simulation_manager|cloner|nodes|utils|includes|version|throttling|deprecation_manager|experimental\..*)$"),
        re.compile(r"^isaacsim\.simulation_app$"),
        re.compile(r"^isaacsim\.storage\.native$"),
        re.compile(r"^omni\.kit\.loop-isaac$"),
    ]),
    ("Physics & PhysX", [
        re.compile(r"^(omni\.physx(?!\.tests)|omni\.physics|omni\.usdphysics|omni\.convexdecomposition).*$"),
        re.compile(r"^omni\.kit\.property\.physx$"),
    ]),
    ("Cortex & Behavior", [
        re.compile(r"^isaacsim\.cortex\..*$"),
    ]),
    ("Robot & Manipulation", [
        re.compile(r"^isaacsim\.robot(\.|_motion|_setup).*$"),
        re.compile(r"^isaacsim\.anim\.robot$"),
    ]),
    ("Sensors", [
        re.compile(r"^(isaacsim\.sensors\.|omni\.sensors\.nv\.|omni\.sensors\.net).*$"),
    ]),
    ("Animation", [
        re.compile(r"^omni\.anim\..*$"),
        re.compile(r"^omni\.usd\.schema\.anim$"),
    ]),
    ("Replicator & SDG", [
        re.compile(r"^(omni\.replicator|isaacsim\.replicator)\..*$"),
    ]),
    ("Asset Import/Export", [
        re.compile(r"^(isaacsim\.asset|omni\.kit\.asset_converter|omni\.importer|omni\.kit\.converter|omni\.kit\.tool\.asset_).*$"),
        re.compile(r"^omni\.exporter\.urdf$"),
    ]),
    ("OmniGraph", [
        re.compile(r"^(omni\.graph|omni\.kit\.graph)\..*$"),
    ]),
    ("ROS2", [
        re.compile(r"^(isaacsim\.ros2|omni\.isaac\.ros2_).*$"),
    ]),
    ("XR (VR/AR)", [
        re.compile(r"^(omni\.kit\.xr|isaacsim\.xr)\..*$"),
    ]),
    ("Kit Viewport & Manipulator", [
        re.compile(r"^omni\.kit\.viewport(\.|_).*$"),
        re.compile(r"^omni\.kit\.manipulator\..*$"),
    ]),
    ("Test & Examples", [
        re.compile(r"^isaacsim\.(examples|benchmark|test)\..*$"),
        re.compile(r"^omni\.physx\.tests.*$"),
        re.compile(r"^omni\.kit\.test(\..*)?$"),
        re.compile(r"^omni\.kit\.test_suite\..*$"),
    ]),
    ("Kit UI & Widget", [
        re.compile(r"^omni\.kit\.(widget|window|menu|property|hotkeys|context_menu|notification_manager|prim\.icon|quicklayout|mainwindow|uiapp|ui_test)(\..*)?$"),
        re.compile(r"^omni\.ui(\..*)?$"),
        re.compile(r"^isaacsim\.(app|code_editor|gui|util)\..*$"),
    ]),
]


def assign_category(name: str, source_dir_name: str) -> str:
    """Extension 이름과 source_dir 로부터 카테고리를 결정.

    규칙 0 (최우선): source_dir == 'extsDeprecated' 이면 무조건 Deprecated.
    """
    if source_dir_name == "extsDeprecated":
        return "Deprecated (omni.isaac.*)"
    for category, patterns in DOMAIN_RULES:
        for pat in patterns:
            if pat.match(name):
                return category
    return "Misc / Utilities"
