"""Static guards for workspaces/coordination/ structure.

Discord multi-agent operating system 의 coordination 디렉토리가 spec §5 정의를
유지하는지 검증. spec 변경 없이 파일/구조가 drift 하면 fail.

Spec SoT: docs/superpowers/specs/2026-05-13-discord-omniverse-mcp-multi-agent-design.md
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COORD = REPO / "workspaces" / "coordination"
TEMPLATES = COORD / "templates"


def test_coordination_root_files_exist():
    """coordination 루트의 README + 4 state file 존재."""
    assert (COORD / "README.md").is_file()
    assert (COORD / "active-mission.md").is_file()
    assert (COORD / "board.md").is_file()
    assert (COORD / "agent-status.md").is_file()
    assert (COORD / "decisions.md").is_file()


def test_handoffs_and_evidence_dirs_have_gitkeep():
    """handoffs/ 와 evidence/ 디렉토리가 .gitkeep 으로 영구화."""
    assert (COORD / "handoffs" / ".gitkeep").is_file()
    assert (COORD / "evidence" / ".gitkeep").is_file()


def test_four_templates_exist():
    """templates/ 의 4 markdown 존재 (mission-packet/handoff/review/validation-report)."""
    assert (TEMPLATES / "mission-packet.md").is_file()
    assert (TEMPLATES / "handoff.md").is_file()
    assert (TEMPLATES / "review.md").is_file()
    assert (TEMPLATES / "validation-report.md").is_file()


def test_mission_packet_has_required_sections():
    """spec §4.4 의 mission packet 필수 섹션."""
    text = (TEMPLATES / "mission-packet.md").read_text(encoding="utf-8")
    for section in ["## Role", "## Must read first", "## Constraints",
                    "## Deliverables", "## Handoff path"]:
        assert section in text, f"missing section: {section}"


def test_handoff_has_required_sections():
    """spec §5.3 의 handoff 필수 섹션."""
    text = (TEMPLATES / "handoff.md").read_text(encoding="utf-8")
    for section in ["Status:", "## Summary", "## Files changed",
                    "## Commands run", "## Evidence", "## Blockers",
                    "## Next recommended action"]:
        assert section in text, f"missing section: {section}"


def test_agent_status_lists_five_panes():
    """agent-status.md 가 spec §6 의 5 작업 pane 모두 명시 (notes 제외)."""
    text = (COORD / "agent-status.md").read_text(encoding="utf-8")
    for pane in ["claude-main", "codex-main", "claude-review",
                 "codex-review", "validation"]:
        assert pane in text, f"missing pane: {pane}"


def test_readme_references_design_spec():
    """README 가 design spec 을 SoT 로 참조."""
    text = (COORD / "README.md").read_text(encoding="utf-8")
    assert "2026-05-13-discord-omniverse-mcp-multi-agent-design.md" in text
