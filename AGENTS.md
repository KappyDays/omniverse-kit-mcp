# AGENTS.md — Codex Adapter for omniverse-kit-mcp

This repository is Claude Code-first. The `CLAUDE.md` hierarchy is the
canonical project memory and SoT; `AGENTS.md` is only a Codex adapter and
entrypoint.

Do not migrate or copy `CLAUDE.md` content into `AGENTS.md`. Do not delete,
rename, or replace `CLAUDE.md` files. Keep the Pull-First Architecture:
root `CLAUDE.md` routes, `docs/invariants/*.md` holds durable rules,
`docs/runbooks/*.md` holds failure/debug procedures, local `CLAUDE.md` files
hold directory rules, and tests guard drift.

## Codex Loading Rule

Claude Code auto-loads some `CLAUDE.md` context. Codex does not: nested
`CLAUDE.md` files are not auto-loaded. Codex must manually read the applicable
`CLAUDE.md` files and pull-docs before planning or editing.

## Startup Checklist

Before planning or editing:

1. Read root `CLAUDE.md`.
2. Use its "작업 전 필수 pull-doc" table to choose required pull-docs.
3. Read all relevant `docs/invariants/*.md` files before touching files.
4. If diagnosing failures, read the relevant `docs/runbooks/*.md` file.
5. Enumerate available local rules when scope is unclear:
   - `rg --files -g CLAUDE.md`
   - `rg --files docs/invariants -g "*.md"`
   - `rg --files docs/runbooks -g "*.md"`
6. If `CLAUDE.md` references a `.claude/skills/*/SKILL.md` workflow, read that
   `SKILL.md` directly and follow it before acting.

## Before-Editing Checklist

Before editing any path:

1. Walk from repo root to the target path and read every applicable
   `CLAUDE.md` on that path.
2. For multiple paths, repeat the walk for each path and follow the union of
   instructions.
3. Read the pull-docs selected from root `CLAUDE.md` and any local
   `CLAUDE.md` table.
4. Preserve protected regions, especially DO-NOT-EDIT blocks in `CLAUDE.md`.
5. Use `uv`; do not use `pip install`.

## Failure-Diagnosis Checklist

When debugging a failure:

1. Read `docs/tool-diagnostic-map.md` if the failure path is unclear.
2. Read only the relevant `docs/runbooks/*.md`; do not duplicate runbook
   content into `AGENTS.md`.
3. For Isaac/Kit process lifecycle issues, start with
   `docs/invariants/process-lifecycle.md`, then the matching runbook.
4. For Extension `.py`, Scenario YAML, new MCP tools, or new modules, follow
   the corresponding invariant named in root `CLAUDE.md`.

## Shared Project Rules

These are pointers to canonical rules, not replacements for them:

- MCP server internal types stay `@dataclass(slots=True, frozen=True)`.
- Use Pydantic only at the Extension REST boundary.
- New MCP tools follow `docs/invariants/mcp-tool-add.md`.
- New modules or scenario actions follow `docs/invariants/module-add.md`.
- Extension `.py` changes follow `docs/invariants/ext-reload.md`.
- Scenario YAML changes follow `docs/invariants/scenario-validation.md`.
- Isaac/Kit lifecycle work follows `docs/invariants/process-lifecycle.md`.
- Do not commit, push, or create PRs unless explicitly asked. Summarize
  changes before any git operation.

## Parallel Claude Code + Codex Use

This repo supports parallel Claude Code and Codex sessions. Avoid resource
conflicts:

- Use a distinct `ISAAC_MCP_INSTANCE_ID` per host/session.
- Do not edit shared `.env` concurrently.
- Each host owns only its own `kit.exe`; do not double-launch the same
  instance.
- Use separate git branches for parallel implementation work.

Workspace mapping:

| Workspace | MCP server | App | Port |
|---|---|---|---|
| `workspaces/isaac/instance-1` | `isaacsim-mcp-1` | Isaac Sim 5.1 | 8111 |
| `workspaces/isaac/instance-2` | `isaacsim-mcp-2` | Isaac Sim 5.1 | 8112 |
| `workspaces/usd-composer/instance-1` | `usdcomposer-mcp-1` | USD Composer | 8114 |
| `workspaces/usd-composer/instance-2` | `usdcomposer-mcp-2` | USD Composer | 8115 |

## Codex Runtime Details

These details are Codex-specific runtime notes, separate from shared project
rules:

- Start Codex directly from a workspace folder with `codex`.
- Codex reads the workspace-local `.codex/config.toml` for that folder.
- Each `.codex/config.toml` mirrors the sibling `.mcp.json` server entry.
- If a root-folder Codex thread receives live MCP work, keep the root thread as
  coordinator and create/continue the actual work in the matching
  `workspaces/<app>/instance-N` folder so the workspace-local MCP entry loads.
- Global Codex MCP entries may appear alongside the workspace entry.
- Codex shell sandbox settings apply to model-generated shell commands only.
  The MCP server process and its child `kit.exe` are separate process trees.
- Local loopback network access is required because MCP tools call the
  Extension REST bridge at `http://127.0.0.1:811N`.

## Final Response Checklist

Before claiming completion, report:

- files changed
- CLAUDE.md files read
- pull-docs read
- runbooks read, if any
- tests/checks run
- commands not run and why
- remaining risks

Prefer targeted checks first, then broader checks when appropriate:

```bash
uv run pytest tests/
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

Codex first-session MCP check, run inside a workspace folder:

```cmd
codex mcp list
```

On Windows-host workflows, prefer the repo's documented Windows commands when
they differ from WSL/Linux equivalents.
