"""Validates workspace .mcp.json.template files structure (Option B / Fallback A).

워크스페이스 분할 spec § 6.1 + plan Option B 검증:
- 4 instance .mcp.json.template 존재 (committed)
- 각 mcpServers entry 에 정확한 server name / env 매핑
- {{REPO_DIR}} placeholder 사용 (setup 시 절대경로로 치환됨)
- workspaces/.gitignore 가 generated .mcp.json + scratch / USD / 미디어 차단

OQ1 (relative path .mcp.json) 검증되면 후속 변경:
- template → 직접 .mcp.json commit, 본 파일 placeholder 검증을 path 검증으로 교체
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACES = REPO_ROOT / "workspaces"

# (folder relative to workspaces/, expected mcp server name, expected profile, expected instance_id)
INSTANCES = [
    ("isaac/instance-1", "isaacsim-mcp-1", "isaac-sim", "1"),
    ("isaac/instance-2", "isaacsim-mcp-2", "isaac-sim", "2"),
    ("usd-composer/instance-1", "usdcomposer-mcp-1", "usd-composer", "1"),
    ("usd-composer/instance-2", "usdcomposer-mcp-2", "usd-composer", "2"),
]


@pytest.mark.parametrize("folder,server_name,profile,instance_id", INSTANCES)
def test_template_exists_and_structure(folder, server_name, profile, instance_id):
    template_path = WORKSPACES / folder / ".mcp.json.template"
    assert template_path.exists(), f".mcp.json.template missing at {template_path}"

    config = json.loads(template_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    assert server_name in servers, f"{server_name} not in {template_path} mcpServers"

    entry = servers[server_name]
    assert entry.get("env", {}).get("ISAAC_MCP_APP_PROFILE") == profile
    assert entry.get("env", {}).get("ISAAC_MCP_INSTANCE_ID") == instance_id


@pytest.mark.parametrize("folder,_a,_b,_c", INSTANCES)
def test_template_uses_placeholder(folder, _a, _b, _c):
    """template 의 args 는 {{REPO_DIR}} placeholder 를 포함해야 setup 이 치환 가능."""
    template_path = WORKSPACES / folder / ".mcp.json.template"
    raw = template_path.read_text(encoding="utf-8")
    assert "{{REPO_DIR}}" in raw, (
        f"{template_path} missing {{{{REPO_DIR}}}} placeholder — "
        f"setup script substitution will not work"
    )


@pytest.mark.parametrize("folder,_a,_b,_c", INSTANCES)
def test_template_no_environment_specific_substring(folder, _a, _b, _c):
    """template 에 사용자 / 머신 고유 값이 박혀 있으면 fail."""
    template_path = WORKSPACES / folder / ".mcp.json.template"
    raw = template_path.read_text(encoding="utf-8")
    forbidden_substrings = [
        "C:/Users/", "C:\\Users\\", "/Users/", "/home/",
        "$env:USERPROFILE", "${USERPROFILE}", "%USERPROFILE%",
        "$HOME", "${HOME}", "$env:HOME",
    ]
    for forbidden in forbidden_substrings:
        assert forbidden not in raw, (
            f"{template_path} contains environment-specific substring '{forbidden}'"
        )


def test_workspaces_gitignore_blocks_required_patterns():
    """workspaces/.gitignore 가 generated .mcp.json + scratch / 미디어 차단."""
    gitignore = WORKSPACES / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    required = ["scratch/", "*.usd", "*.png", "**/instance-*/.mcp.json"]
    for pat in required:
        assert pat in content, f".gitignore missing pattern '{pat}'"


def test_workspaces_directory_structure():
    """4 instance dir + 2 profile dir + scenarios / scratch 존재."""
    for profile in ["isaac", "usd-composer"]:
        assert (WORKSPACES / profile / "CLAUDE.md").exists()
        assert (WORKSPACES / profile / "README.md").exists()
        assert (WORKSPACES / profile / "scenarios").is_dir()
        assert (WORKSPACES / profile / "scratch").is_dir()
        for inst in ["instance-1", "instance-2"]:
            assert (WORKSPACES / profile / inst).is_dir()
