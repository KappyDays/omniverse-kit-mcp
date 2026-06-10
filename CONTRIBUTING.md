# Contributing

Thanks for taking a look at `omniverse-kit-mcp`.

## Development Setup

1. Install Python 3.11+, `uv`, and the target NVIDIA Kit application.
2. Copy `.env.example` to `.env` and set machine-local Kit paths.
3. Run `uv sync`.
4. Run `uv run pytest tests/`.

Use the workspace folders under `workspaces/` when testing MCP control against
Isaac Sim or USD Composer. Keep `.env`, generated captures, generated catalogs,
and local runtime state out of commits.

## Pull Requests

Before opening a PR:

- Run `uv run pytest tests/`.
- Run `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` after tool surface
  changes.
- Update `docs/invariants/` or `docs/runbooks/` when behavior changes create a
  durable rule.
- Keep generated local references under `docs/references/` untracked.

## Project Rules

The canonical project memory is the `CLAUDE.md` hierarchy. `AGENTS.md` is a
Codex adapter that points back to those rules.
