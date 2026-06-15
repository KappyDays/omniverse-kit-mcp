# AGENTS.md — Codex Adapter for omniverse-kit-mcp

This repository is Claude Code-first. The `CLAUDE.md` hierarchy is canonical
project memory and SoT; `AGENTS.md` is only a Codex adapter and entrypoint.

Do not migrate or copy `CLAUDE.md` content into `AGENTS.md`. Do not delete,
rename, or replace `CLAUDE.md` files. Pull-First Architecture remains:
root `CLAUDE.md` routes, `docs/invariants/*.md` holds durable rules,
`docs/runbooks/*.md` holds failure/debug procedures, local `CLAUDE.md` files
hold directory rules, and tests guard drift.

## Codex Loading Rule

Claude Code auto-loads some `CLAUDE.md` context. Codex does not: nested
`CLAUDE.md` files are not auto-loaded. Codex must manually read applicable
`CLAUDE.md` files and pull-docs before planning or editing.

## Startup / Editing

Before planning or editing:

1. Read root `CLAUDE.md`.
2. Use its "Required pull-docs before work" table to choose required pull-docs.
3. Read relevant `docs/invariants/*.md`; for failures read relevant
   `docs/runbooks/*.md`.
4. Walk from repo root to target path and read every applicable `CLAUDE.md`.
   For multiple paths, repeat the walk and follow the union of instructions.
5. Preserve protected incident guards and their canonical docs.
6. If scope is unclear, enumerate rules with `rg --files -g CLAUDE.md`,
   `rg --files docs/invariants -g "*.md"`, and
   `rg --files docs/runbooks -g "*.md"`.
7. If `CLAUDE.md` references a `.claude/skills/*/SKILL.md` workflow, read it
   directly and follow it.
8. Use `uv`; do not use `pip install`.

## Shared Project Rules

Do not copy canonical project memory here. Root `CLAUDE.md` and required
pull-docs own durable rules such as dataclass/Pydantic boundaries,
`mcp-tool-add.md`, `module-add.md`, `ext-reload.md`,
`scenario-validation.md`, `process-lifecycle.md`, and live worker coordination.

Do not commit, push, or create PRs unless explicitly asked. Summarize changes
before any git operation.

## Quiet Parent Contract

For live worker coordination, follow `docs/invariants/live-worker-coordination.md`;
report milestones and final results, not parent polling chatter.

## Parallel Claude Code + Codex Use

Use a distinct `ISAAC_MCP_INSTANCE_ID` per host/session. Do not edit shared
`.env` concurrently. Each host owns only its own `kit.exe`; do not
double-launch the same instance. Use separate git branches for parallel
implementation work.

Workspace matrix and ports live in `workspaces/README.md`.

## Codex Runtime Details

- Start Codex directly from a workspace folder with `codex`.
- Codex reads workspace-local `.codex/config.toml`, which mirrors sibling
  `.mcp.json` and intentionally contains only the one Kit MCP entry.
- Keep optional code-navigation MCPs such as CodeGraph in user/global Codex
  config; use CodeGraph only after reading applicable `CLAUDE.md` and pull-docs.
- If a root-folder Codex thread receives live MCP work, follow
  `docs/invariants/live-worker-coordination.md`: keep the root thread as
  coordinator and create/continue work in matching
  `workspaces/<app>/instance-N` so the workspace-local MCP entry loads.
- Requests to launch/open/start Isaac Sim, USD Composer, or another Omniverse
  app are live MCP work. Treat that wording as explicit permission to create or
  continue the matching workspace Codex thread and run `kit_app_start` there.
  See `docs/invariants/live-worker-coordination.md`.
- Global Codex MCP entries may appear alongside the workspace entry.
- Runtime details and first-session checks live in `workspaces/README.md`.

## Final Response Checklist

Before claiming completion, report:

- files changed
- CLAUDE.md files read
- pull-docs read
- runbooks read, if any
- tests/checks run
- commands not run and why
- remaining risks

Prefer targeted checks first. On Windows-host workflows, prefer documented
Windows commands when they differ from WSL/Linux equivalents.
