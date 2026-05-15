"""Codex entrypoint drift guards.

- Group A: AGENTS.md ↔ root CLAUDE.md / invariants 정합
- Group B: .codex/config.toml ↔ .mcp.json 미러 + launcher byte-identical
- Group C: shared docs 에 Claude-only 표현 재도입 방지
- Group D: AGENTS.md hard rules ↔ root CLAUDE.md key phrase sync
"""
import json
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKSPACES = sorted((REPO / "workspaces").glob("*/instance-*"))
INVARIANTS = sorted((REPO / "docs/invariants").glob("*.md"))
RUNBOOKS = sorted((REPO / "docs/runbooks").glob("*.md"))


def test_agents_md_references_root_claude_md():
    """t1: AGENTS.md 가 root CLAUDE.md 를 진입점으로 참조."""
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "Read root `CLAUDE.md`" in text or "Read root CLAUDE.md" in text


def test_agents_md_references_all_invariants():
    """t2: AGENTS.md 가 모든 docs/invariants/*.md 파일을 reference (drift 가드)."""
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    # 디렉토리 통합 reference 인정
    if "docs/invariants/" in text or "docs\\invariants\\" in text:
        return
    missing = [p.name for p in INVARIANTS if p.name not in text]
    assert not missing, f"AGENTS.md 가 빠뜨린 invariants: {missing}"


def test_workspace_codex_configs_mirror_mcp_json():
    """t3: 각 workspace 의 .codex/config.toml 의 MCP entry 가
    같은 workspace 의 .mcp.json 의 entry 와 server name / args / env 1:1 일치."""
    assert WORKSPACES, "no workspaces/*/instance-* directories found"
    for ws in WORKSPACES:
        mcp_json = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))
        codex_toml = tomllib.loads((ws / ".codex/config.toml").read_text(encoding="utf-8"))

        json_entries = mcp_json["mcpServers"]
        toml_entries = codex_toml["mcp_servers"]
        assert len(json_entries) == 1, f"{ws}/.mcp.json must have exactly 1 entry"
        assert len(toml_entries) == 1, f"{ws}/.codex/config.toml must have exactly 1 entry"

        json_name = next(iter(json_entries))
        toml_name = next(iter(toml_entries))
        assert json_name == toml_name, f"{ws}: server name {json_name!r} != {toml_name!r}"

        json_entry = json_entries[json_name]
        toml_entry = toml_entries[toml_name]
        assert json_entry["args"] == toml_entry["args"], f"{ws}: args mismatch"
        assert json_entry["env"] == toml_entry["env"], f"{ws}: env mismatch"


def test_launch_codex_bats_byte_identical():
    """t4: 4 workspace 의 launch-codex.bat 가 byte-identical (drift 방지)."""
    bats = sorted(ws / "launch-codex.bat" for ws in WORKSPACES)
    assert bats, "no launch-codex.bat files found"
    contents = [b.read_bytes() for b in bats]
    first = contents[0]
    mismatches = [str(bats[i]) for i, c in enumerate(contents) if c != first]
    assert not mismatches, f"launch-codex.bat drift: {mismatches}"


def test_no_claude_only_phrasing_in_shared_docs():
    """t5: Shared docs 에 Claude-only 동사 결합 표현 재도입 방지."""
    deny_patterns = [
        re.compile(r"Claude Code\s*재시작"),
        re.compile(r"Claude Code\s*가\s*(stdio|spawn|stdin|폴링|job_status)"),
        re.compile(r"Claude Code\s*UI에\s*표시"),
        re.compile(r"Claude Code\s*와의\s*양방향"),
        re.compile(r"Claude Code\s*는\s*stdin"),
    ]
    targets = [
        REPO / "CLAUDE.md",
        REPO / "scripts/CLAUDE.md",
        REPO / "src/omniverse_kit_mcp/CLAUDE.md",
        REPO / "src/omniverse_kit_mcp/tools/CLAUDE.md",
        REPO / "src/omniverse_kit_mcp/modules/process-ops.md",
        *INVARIANTS,
        *RUNBOOKS,
    ]
    violations = []
    for f in targets:
        text = f.read_text(encoding="utf-8")
        for pat in deny_patterns:
            for m in pat.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                violations.append(f"{f.relative_to(REPO)}:L{line_no}: {m.group(0)!r}")
    assert not violations, "Claude-only 표현 재도입:\n  " + "\n  ".join(violations)


def test_agents_md_hard_rules_match_root_claude_md_key_phrases():
    """t6: AGENTS.md 의 Hard project rules 핵심 phrase 가 root CLAUDE.md 와 sync."""
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    root = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    key_phrases = [
        "uv",
        "DO-NOT-EDIT",
        "dataclass",
        "Pydantic",
        "mcp-tool-add",
        "module-add",
        "ext-reload",
        "scenario-validation",
        "process-lifecycle",
    ]
    missing_in_agents = [p for p in key_phrases if p not in agents]
    missing_in_root = [p for p in key_phrases if p not in root]
    assert not missing_in_agents, f"AGENTS.md 빠뜨린 key phrase: {missing_in_agents}"
    assert not missing_in_root, f"root CLAUDE.md 빠뜨린 key phrase: {missing_in_root}"
