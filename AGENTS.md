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
- Do not commit, push, or create PRs unless explicitly asked. Summarize changes before any git operation.

## Concurrent use with Claude Code

This repository is designed to support Claude Code and Codex CLI in parallel
sessions. Apply these guards to avoid resource conflicts:

- **Instance separation**: Use different `ISAAC_MCP_INSTANCE_ID` per host
  (e.g., Claude Code on instance-1, Codex CLI on instance-2). Each workspace
  binds to a distinct port (Isaac: 8011 / 8012, USD Composer: 8014 / 8015).
- **`.env` editing**: Both hosts read the same `.env`. Do not edit it from
  both sides concurrently — coordinate edits in one session.
- **`kit.exe` ownership**: Each host owns only its own `kit.exe` instance.
  Do not call `kit_app_start` for the same instance from both hosts (double-launch causes port conflict on 801N and hub-orphan symptoms — see `docs/runbooks/hub-orphan.md`).
- **Git branch separation**: For parallel work, branch off so each session
  commits on its own branch.

## Codex MCP server access

Each workspace folder activates a single Isaac Sim or USD Composer instance:

```cmd
cd workspaces\isaac\instance-1
.\launch-codex.bat
```

Up to two apps can run concurrently — open two terminals and `cd` into two
different workspace folders. Each codex session owns one `kit.exe` process.

| Workspace | MCP server | App | Port |
|---|---|---|---|
| `workspaces/isaac/instance-1` | `isaacsim-mcp-1` | Isaac Sim 5.1 | 8011 |
| `workspaces/isaac/instance-2` | `isaacsim-mcp-2` | Isaac Sim 5.1 | 8012 |
| `workspaces/usd-composer/instance-1` | `usdcomposer-mcp-1` | USD Composer | 8014 |
| `workspaces/usd-composer/instance-2` | `usdcomposer-mcp-2` | USD Composer | 8015 |

The launcher sets `CODEX_HOME=%~dp0.codex` so codex reads the workspace-local
`.codex/config.toml` (which mirrors the sibling `.mcp.json` used by Claude Code).

## Codex environment requirements

Each workspace's `.codex/config.toml` ships with the following block (informative — already deployed by Task 2; do not recreate):

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true   # required for localhost:801N Extension REST calls
```

**Scope of these settings**: `sandbox_mode` and `approval_policy` apply only to
*model-generated shell commands* the codex agent runs directly. The MCP server
(spawned by codex via stdio) and its child `kit.exe` are **separate process
trees** — they are not constrained by these sandbox settings, so file writes
to `%TEMP%/omniverse_kit_mcp/`, `%LOCALAPPDATA%/ov/`, etc. proceed normally.

`network_access = true` is required because the MCP server tools call the
Kit Extension REST at `http://localhost:801N`. If localhost is blocked,
all MCP tool calls fail.

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

```cmd
:: Codex first-session verification (run inside a workspace folder):
.\launch-codex.bat mcp list   :: should list this workspace's single MCP entry
```

On Windows-host workflows, prefer the repo's documented Windows commands when
they differ from WSL/Linux equivalents.
