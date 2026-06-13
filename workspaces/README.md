# Workspaces — omniverse-kit-mcp Consumer Workspaces

This directory is a workspace for **using** the omniverse-kit-mcp server. For server code / docs / tests, see `../` (repo root).

## Usage pattern

Each instance folder = 1 MCP host session (Claude Code or codex) = Kit MCP entry provided for the corresponding app/instance (~150 tool names). If there is a Codex global MCP entry, it can be displayed together. Multi-app scenario operates two host windows simultaneously.

Root repo thread is parent/coordinator and only actual Kit MCP verification instance
When delegating to a thread, use `../docs/invariants/live-worker-coordination.md`
Follow. This rule is a common operating rule, but live thread operation is currently only available in Codex.
Verified.

```
cd workspaces/isaac/instance-1   # Isaac Sim instance 1 (port 8111)
claude                            # Claude Code entry
codex                             # Codex CLI entry
```

## First use

`.mcp.json` and `.codex/config.toml` are committed in 4 instance folders (`uv --directory ../../..` relative path — host working dir = instance folder → repo root). `cd` + `claude` or `codex` is possible immediately after cloning without additional setup. Separate installation of uv / Isaac Sim / USD Composer — `../setup/CLAUDE.md`. Codex CLI self-installation (`npm install -g @openai/codex`) can be found in the `../README.md` Wiring section.

Code navigation MCPs such as CodeGraph are placed in user/global Codex config. This
Only 1 Kit MCP entry must be maintained in workspace-local `.codex/config.toml`
And `tests/unit/test_codex_entrypoint_sync.py` is with sibling `.mcp.json`.
Verify 1:1 mirror. To use CodeGraph, go to the repo root
Create `.codegraph/` with `codegraph init -i` and in the workspace folder
`codex mcp list` to global `codegraph` and workspace kit MCP together
Just check what you can see.

## Scenario → Folder Matrix

| Scenario | CC Window | Entry Folder |
|---|---|---|
| isaac × 1 | 1 | `isaac/instance-1/` |
| composer × 1 | 1 | `usd-composer/instance-1/` |
| isaac + composer | 2 simultaneously | `isaac/instance-1/` + `usd-composer/instance-1/` |
| isaac × 2 | 2 simultaneously | `isaac/instance-1/` + `isaac/instance-2/` |
| composer × 2 | 2 simultaneously | `usd-composer/instance-1/` + `usd-composer/instance-2/` |

## Directory conventions

- `{profile}/CLAUDE.md` — Work rules for each profile + pull-doc table (refer to server `docs/` relative path)
- `{profile}/scenarios/` — work-only YAML. Commit possible when R1 is met
- `{profile}/scratch/` — gitignored. Temporary USD / Screenshot
- `{profile}/instance-{N}/.mcp.json` — committed. `uv --directory ../../..` relative path. CC (Claude Code) entry point
- `{profile}/instance-{N}/.codex/config.toml` — committed. Codex CLI entry point (Kit MCP entry by workspace)

## ExpansionThe procedure for adding a new profile is “New App Profile” in `../docs/invariants/multi-app.md`.
Follow “Additional Procedures”. When you add a new profile, the corresponding profile folder, instance
`.mcp.json`, `.codex/config.toml`, profile `CLAUDE.md`, setup registration, config/test
must move together.

## Promote work scenario → server regression

When promoting a work-only scenario to server regression, the 4 items below must be passed.
Then move to `git mv` and down to server `scenarios/`.

1. Only use actual NVIDIA/Hub assets. Promoting primitive replacement verification is prohibited.
2. `scenario_validate` or equivalent live verification passes.
3. Visually check the `viewport_capture` results for scenarios that require capture.
4. App/profile-specific premises are specified in YAML or adjacent README.