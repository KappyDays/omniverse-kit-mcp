# AGENTS.md — Codex Entry Point for omniverse-kit-mcp

This repository was originally organized for Claude Code. The canonical project
instructions remain in `CLAUDE.md`; do not duplicate or reinterpret them here.

## Required startup procedure

Before planning or editing:

1. Read root `CLAUDE.md`.
2. Use its "작업 전 필수 pull-doc" table to choose required documents.
3. Read all relevant `docs/invariants/*.md` documents before touching files.
4. If diagnosing failures, read the relevant `docs/runbooks/*.md` document.
5. If touching a directory that has its own `CLAUDE.md`, read that file before editing.
6. If `CLAUDE.md` references a `.claude/skills/*/SKILL.md` workflow, read the
   `SKILL.md` directly and follow it as a written procedure.

## Codex-specific interpretation

- Do not rely on Claude Code's auto-loading behavior for nested `CLAUDE.md` files.
- Treat `CLAUDE.md` files as project documentation, not as Claude-only instructions.
- Preserve the Pull-First Architecture:
  - root `CLAUDE.md` stays under its line cap,
  - durable rules belong in `docs/invariants/*.md`,
  - incident/debug procedures belong in `docs/runbooks/*.md`,
  - subdirectory rules stay in local `CLAUDE.md` files.
- Do not create duplicated Codex-only copies of existing rules unless explicitly requested.

## Hard project rules

- Use `uv`; do not use `pip install`.
- Do not violate DO-NOT-EDIT protected regions in `CLAUDE.md`.
- Keep MCP server internal types as `@dataclass(slots=True, frozen=True)`.
- Use Pydantic only at the Extension REST boundary.
- For new MCP tools, follow `docs/invariants/mcp-tool-add.md`.
- For new modules or scenario actions, follow `docs/invariants/module-add.md`.
- For Extension `.py` changes, follow `docs/invariants/ext-reload.md`.
- For Scenario YAML changes, follow `docs/invariants/scenario-validation.md`.
- For Isaac/Kit process lifecycle issues, follow `docs/invariants/process-lifecycle.md`.

## Verification expectations

Before claiming completion, report:

- files changed,
- relevant pull-docs read,
- tests/checks run,
- commands that could not be run and why,
- remaining risks.

Prefer targeted tests first, then broader checks when appropriate:

```bash
uv run pytest tests/
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

On Windows-host workflows, prefer the repo's documented Windows commands when
they differ from WSL/Linux equivalents.
