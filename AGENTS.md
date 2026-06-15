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
5. Preserve DO-NOT-EDIT regions, especially in `CLAUDE.md`.
6. If scope is unclear, enumerate rules with `rg --files -g CLAUDE.md`,
   `rg --files docs/invariants -g "*.md"`, and
   `rg --files docs/runbooks -g "*.md"`.
7. If `CLAUDE.md` references a `.claude/skills/*/SKILL.md` workflow, read it
   directly and follow it.
8. Use `uv`; do not use `pip install`.

## Shared Project Rules

Pointers to canonical rules, not replacements:

- MCP server internal types stay `@dataclass(slots=True, frozen=True)`.
- Use Pydantic only at the Extension REST boundary.
- New MCP tools follow `docs/invariants/mcp-tool-add.md`.
- New modules or scenario actions follow `docs/invariants/module-add.md`.
- Extension `.py` changes follow `docs/invariants/ext-reload.md`.
- Scenario YAML changes follow `docs/invariants/scenario-validation.md`.
- Isaac/Kit lifecycle work follows `docs/invariants/process-lifecycle.md`.
- Parent/coordinator and live MCP worker split follows
  `docs/invariants/live-worker-coordination.md`.
- Do not commit, push, or create PRs unless explicitly asked. Summarize
  changes before any git operation.

## Quiet Parent Contract

When a root Codex thread coordinates live MCP worker threads, internally monitor
workers silently. Do not report `read_thread` polling, waiting, checking again,
no-new-tool-call, tool-read failure, or output-size adjustment updates to the
user. Report only worker creation, attach/start result, terminal validation,
Console WARN/ERROR summary, artifacts, blocker, or final.

## Parallel Claude Code + Codex Use

Use a distinct `ISAAC_MCP_INSTANCE_ID` per host/session. Do not edit shared
`.env` concurrently. Each host owns only its own `kit.exe`; do not
double-launch the same instance. Use separate git branches for parallel
implementation work.

Workspace mapping:

| Workspace | MCP server | App | Port |
|---|---|---|---|
| `workspaces/isaac/instance-1` | `isaacsim-mcp-1` | Isaac Sim 6.0.0 | 8111 |
| `workspaces/isaac/instance-2` | `isaacsim-mcp-2` | Isaac Sim 6.0.0 | 8112 |
| `workspaces/usd-composer/instance-1` | `usdcomposer-mcp-1` | USD Composer | 8114 |
| `workspaces/usd-composer/instance-2` | `usdcomposer-mcp-2` | USD Composer | 8115 |

## Codex Runtime Details

- Start Codex directly from a workspace folder with `codex`.
- Codex reads workspace-local `.codex/config.toml`, which mirrors sibling
  `.mcp.json` and intentionally contains only the one Kit MCP entry.
- Keep optional code-navigation MCPs such as CodeGraph in user/global Codex
  config. For CodeGraph, initialize repo root with `codegraph init -i`.
- Use CodeGraph only after reading applicable `CLAUDE.md` and pull-docs.
- If a root-folder Codex thread receives live MCP work, follow
  `docs/invariants/live-worker-coordination.md`: keep the root thread as
  coordinator and create/continue work in matching
  `workspaces/<app>/instance-N` so the workspace-local MCP entry loads.
- Requests to launch/open/start Isaac Sim, USD Composer, or another Omniverse
  app are live MCP work. Treat that wording as explicit permission to create or
  continue the matching workspace Codex thread and run `kit_app_start` there.
  See `docs/invariants/live-worker-coordination.md`.
- Warning: this common parent/worker contract has only been live-verified with
  Codex threads so far; non-Codex hosts should report adapter gaps.
- Global Codex MCP entries may appear alongside the workspace entry.
- Codex shell sandbox settings apply to model-generated shell commands only;
  MCP server processes and child `kit.exe` are separate process trees.
- Local loopback access is required because MCP tools call
  `http://127.0.0.1:811N`.

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

Codex first-session MCP check inside a workspace folder:

```cmd
codex mcp list
```

On Windows-host workflows, prefer documented Windows commands when they differ
from WSL/Linux equivalents.
