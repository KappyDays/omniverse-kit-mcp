"""Codex entrypoint drift guards.

- Group A: AGENTS.md ↔ root CLAUDE.md / invariants consistency
- Group B: .codex/config.toml ↔ .mcp.json mirror + no legacy launcher
- Group C: prevent reintroducing Claude-only phrasing into shared docs
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


def _agents_text() -> str:
    return (REPO / "AGENTS.md").read_text(encoding="utf-8")


def _plain_agents_text() -> str:
    return re.sub(r"\s+", " ", _agents_text().replace("`", ""))


def test_agents_md_references_root_claude_md():
    """t1: AGENTS.md references root CLAUDE.md as the entrypoint."""
    text = _agents_text()
    assert "Read root `CLAUDE.md`" in text or "Read root CLAUDE.md" in text


def test_agents_md_references_all_invariants():
    """t2: AGENTS.md references every docs/invariants/*.md file (drift guard)."""
    text = _agents_text()
    # Directory-wide references are accepted.
    if "docs/invariants/" in text or "docs\\invariants\\" in text:
        return
    missing = [p.name for p in INVARIANTS if p.name not in text]
    assert not missing, f"AGENTS.md missing invariants: {missing}"


def test_agents_md_declares_codex_adapter_not_canonical_copy():
    """t7: AGENTS.md is a Codex adapter and the CLAUDE.md hierarchy is canonical."""
    text = _plain_agents_text()
    assert re.search(r"CLAUDE\.md[^.]*canonical", text, re.IGNORECASE)
    assert re.search(r"AGENTS\.md[^.]*(adapter|entrypoint)", text, re.IGNORECASE)


def test_agents_md_requires_manual_claude_walk_before_editing():
    """t8: path-walk rules compensate for lack of nested CLAUDE.md auto-loading."""
    text = _plain_agents_text()
    assert re.search(r"nested[^.]*CLAUDE\.md[^.]*not auto-loaded", text, re.IGNORECASE)
    assert re.search(r"repo root[^.]*target path", text, re.IGNORECASE)
    assert re.search(r"multiple paths[^.]*(union|repeat)", text, re.IGNORECASE)


def test_agents_md_references_pull_docs_and_runbooks():
    """t9: pull-doc table, invariants, runbooks are explicit entrypoint concepts."""
    text = _agents_text()
    required = [
        "Required pull-docs before work",
        "docs/invariants/",
        "docs/runbooks/",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    assert not missing, f"AGENTS.md missing pull-doc references: {missing}"


def test_agents_md_protects_claude_hierarchy_from_migration():
    """t10: AGENTS.md must not become a migrated copy of CLAUDE.md files."""
    text = _plain_agents_text()
    assert re.search(r"do not[^.]*(migrate|copy)[^.]*CLAUDE\.md", text, re.IGNORECASE)
    assert re.search(
        r"do not[^.]*(delete|rename|replace)[^.]*CLAUDE\.md",
        text,
        re.IGNORECASE,
    )


def test_agents_md_final_report_requires_doc_and_risk_details():
    """t11: final report checklist keeps Codex honest about docs and verification."""
    text = _agents_text()
    required = [
        "files changed",
        "CLAUDE.md files read",
        "pull-docs read",
        "runbooks read",
        "tests/checks run",
        "commands not run",
        "remaining risks",
    ]
    missing = [phrase for phrase in required if phrase not in text]
    assert not missing, f"AGENTS.md final report checklist missing: {missing}"


def test_workspace_codex_configs_mirror_mcp_json():
    """t3: each workspace .codex/config.toml MCP entry mirrors its .mcp.json entry."""
    assert WORKSPACES, "no workspaces/*/instance-* directories found"
    for ws in WORKSPACES:
        mcp_json_path = ws / ".mcp.json"
        codex_toml_path = ws / ".codex/config.toml"
        assert mcp_json_path.exists(), f"missing: {mcp_json_path}"
        assert codex_toml_path.exists(), f"missing: {codex_toml_path}"

        mcp_json = json.loads(mcp_json_path.read_text(encoding="utf-8"))
        codex_toml = tomllib.loads(codex_toml_path.read_text(encoding="utf-8"))

        json_entries = mcp_json["mcpServers"]
        toml_entries = codex_toml["mcp_servers"]
        assert len(json_entries) == 1, f"{ws}/.mcp.json must have exactly 1 entry"
        assert len(toml_entries) == 1, f"{ws}/.codex/config.toml must have exactly 1 entry"

        json_name = next(iter(json_entries))
        toml_name = next(iter(toml_entries))
        assert json_name == toml_name, f"{ws}: server name {json_name!r} != {toml_name!r}"

        json_entry = json_entries[json_name]
        toml_entry = toml_entries[toml_name]
        assert json_entry["command"] == toml_entry["command"], f"{ws}: command mismatch"
        assert json_entry["args"] == toml_entry["args"], f"{ws}: args mismatch"
        assert json_entry["env"] == toml_entry["env"], f"{ws}: env mismatch"


def test_no_legacy_launch_codex_bats():
    """t4: Codex starts directly from the workspace folder; legacy launchers stay absent."""
    assert WORKSPACES, "no workspaces/*/instance-* directories found"
    leftovers = [
        str(ws / "launch-codex.bat")
        for ws in WORKSPACES
        if (ws / "launch-codex.bat").exists()
    ]
    assert not leftovers, (
        "legacy launch-codex.bat files should not be present: " + ", ".join(leftovers)
    )


def test_no_claude_only_phrasing_in_shared_docs():
    """t5: prevent reintroducing Claude-only verb phrases into shared docs."""
    deny_patterns = [
        re.compile(r"Claude Code\s*restart"),
        re.compile(r"Claude Code\s*(stdio|spawn|stdin|polling|job_status)"),
        re.compile(r"Claude Code(?:'s)?\s*(stdio|stdin)"),
        re.compile(r"displayed\s*in\s*Claude Code\s*UI", re.IGNORECASE),
        re.compile(r"bidirectional\s*with\s*Claude Code", re.IGNORECASE),
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
    assert not violations, "Claude-only phrasing reintroduced:\n  " + "\n  ".join(violations)


def test_agents_md_hard_rules_match_root_claude_md_key_phrases():
    """t6: AGENTS.md hard-rule key phrases stay synced with root CLAUDE.md."""
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    root = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    key_patterns = {
        "uv": r"\buv\b",
        "protected regression": r"protected\s+(incident|regression)",
        "dataclass": r"dataclass",
        "Pydantic": r"Pydantic",
        "mcp-tool-add": r"mcp-tool-add",
        "module-add": r"module-add",
        "ext-reload": r"ext-reload",
        "scenario-validation": r"scenario-validation",
        "process-lifecycle": r"process-lifecycle",
    }
    missing_in_agents = [
        name for name, pattern in key_patterns.items()
        if not re.search(pattern, agents, re.IGNORECASE)
    ]
    missing_in_root = [
        name for name, pattern in key_patterns.items()
        if not re.search(pattern, root, re.IGNORECASE)
    ]
    assert not missing_in_agents, f"AGENTS.md missing key phrase: {missing_in_agents}"
    assert not missing_in_root, f"root CLAUDE.md missing key phrase: {missing_in_root}"
