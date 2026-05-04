"""Validates workspace .mcp.json files structure (post-OQ1, direct commit).

워크스페이스 분할 spec § 6.1 검증 (OQ1 PASS 후):
- 4 instance .mcp.json 존재 (committed, no template/setup-time generation)
- 각 mcpServers entry 에 정확한 server name / env 매핑
- args 의 `--directory` 가 `../../..` 상대경로 (CC working dir = instance 폴더 → repo root)
- 환경 / 머신 고유 substring 미포함
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
def test_mcp_json_exists_and_structure(folder, server_name, profile, instance_id):
    mcp_path = WORKSPACES / folder / ".mcp.json"
    assert mcp_path.exists(), f".mcp.json missing at {mcp_path}"

    config = json.loads(mcp_path.read_text(encoding="utf-8"))
    servers = config.get("mcpServers", {})
    assert server_name in servers, f"{server_name} not in {mcp_path} mcpServers"

    entry = servers[server_name]
    assert entry.get("env", {}).get("ISAAC_MCP_APP_PROFILE") == profile
    assert entry.get("env", {}).get("ISAAC_MCP_INSTANCE_ID") == instance_id


@pytest.mark.parametrize("folder,server_name,_p,_i", INSTANCES)
def test_mcp_json_uses_relative_repo_root(folder, server_name, _p, _i):
    """args 의 `uv --directory` 가 `../../..` 상대경로 — instance 폴더 (3 레벨 깊이) 기준 repo root."""
    mcp_path = WORKSPACES / folder / ".mcp.json"
    config = json.loads(mcp_path.read_text(encoding="utf-8"))
    args = config["mcpServers"][server_name]["args"]
    assert "--directory" in args, f"{mcp_path} args missing --directory"
    dir_value = args[args.index("--directory") + 1]
    assert dir_value == "../../..", (
        f"{mcp_path} --directory must be '../../..' (relative to instance folder), got '{dir_value}'"
    )


@pytest.mark.parametrize("folder,_a,_b,_c", INSTANCES)
def test_mcp_json_no_environment_specific_substring(folder, _a, _b, _c):
    """commit 된 .mcp.json 에 사용자 / 머신 고유 값이 박혀 있으면 fail."""
    mcp_path = WORKSPACES / folder / ".mcp.json"
    raw = mcp_path.read_text(encoding="utf-8")
    forbidden_substrings = [
        "C:/Users/", "C:\\Users\\", "/Users/", "/home/",
        "$env:USERPROFILE", "${USERPROFILE}", "%USERPROFILE%",
        "$HOME", "${HOME}", "$env:HOME",
        "{{REPO_DIR}}",  # placeholder leftover guard
    ]
    for forbidden in forbidden_substrings:
        assert forbidden not in raw, (
            f"{mcp_path} contains environment-specific substring '{forbidden}'"
        )


@pytest.mark.parametrize("folder,_a,_b,_c", INSTANCES)
def test_no_template_leftover(folder, _a, _b, _c):
    """OQ1 PASS 이후 .mcp.json.template 은 삭제되었어야 한다."""
    template_path = WORKSPACES / folder / ".mcp.json.template"
    assert not template_path.exists(), (
        f"{template_path} should have been removed after switching to direct .mcp.json commit"
    )


def test_workspaces_gitignore_blocks_required_patterns():
    """workspaces/.gitignore 가 scratch / 미디어 차단."""
    gitignore = WORKSPACES / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    required = ["scratch/", "*.usd", "*.png"]
    for pat in required:
        assert pat in content, f".gitignore missing pattern '{pat}'"


def test_workspaces_gitignore_does_not_block_committed_mcp_json():
    """OQ1 PASS 이후 .mcp.json 은 commit 대상 — gitignore 패턴 잔존하면 fail."""
    gitignore = WORKSPACES / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    forbidden = ["instance-*/.mcp.json", "**/instance-*/.mcp.json"]
    for pat in forbidden:
        assert pat not in content, (
            f".gitignore must not contain '{pat}' — .mcp.json is committed directly"
        )


def test_workspaces_directory_structure():
    """4 instance dir + 2 profile dir + scenarios / scratch 존재."""
    for profile in ["isaac", "usd-composer"]:
        assert (WORKSPACES / profile / "CLAUDE.md").exists()
        assert (WORKSPACES / profile / "README.md").exists()
        assert (WORKSPACES / profile / "scenarios").is_dir()
        assert (WORKSPACES / profile / "scratch").is_dir()
        for inst in ["instance-1", "instance-2"]:
            assert (WORKSPACES / profile / inst).is_dir()
