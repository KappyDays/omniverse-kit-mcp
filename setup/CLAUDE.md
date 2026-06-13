<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Installation script — repo clone / uv sync / .env / launcher install / ~/.claude.json legacy cleanup -->

# setup — installation script

Scripts that prepare omniverse-kit-mcp for use on a new PC. The actual logic is handled by PowerShell (`setup_omniverse_kit_mcp.ps1`), and the entry point is handled by a batch file (`setup-omniverse-kit-mcp.bat`).

## file

| file | Role |
|------|------|
| `setup-omniverse-kit-mcp.bat` | Windows entry point. Double click or run with `setup\setup-omniverse-kit-mcp.bat`. Invoking PowerShell script as `ExecutionPolicy Bypass` |
| `setup_omniverse_kit_mcp.ps1` | Actual Installation Logic (5 Steps) |
| `launchers/*_mcp.bat`, `launchers/*_mcp.ps1` | Original MCP-safe launcher for manual execution of Isaac Sim / USD Composer. Copy setup to the actual app folder |

## Script action

Steps `setup_omniverse_kit_mcp.ps1` performs:

1. **Check Prerequisites** — Check if `git` and `uv` are in PATH. If not, give instructions and end.
2. **Repo clone or verification** — If there is a repo in `$env:USERPROFILE\workspace\omniverse-kit-mcp`, `uv sync`, if not, `git clone` and then `uv sync`
3. Create **.env** — `.env.example` → Copy `.env` (skip if already present, preserve existing value)
4. **Install MCP-safe launcher** — Copy the original `setup/launchers` to the Isaac Sim standalone folder and the USD Composer release folder. If there is no target folder, WARN and then skip
5. **`~/.claude.json` legacy cleanup** — Remove 7 entries (`isaacsim-mcp-{1,2,3}`, `usdcomposer-mcp-{1,2,3}`, `omniverse-kit-mcp`) registered by previous setup from global `mcpServers`. No new registrations — MCP server loads from 4 in-repo `workspaces/<profile>/instance-<N>/.mcp.json`

## 🚨 MCP server load location

- **Current SoT**: 4 in-repo `workspaces/<profile>/instance-<N>/.mcp.json` (committed, `uv --directory ../../..` relative path — repo clone location is irrelevant)
- **NOT** global `mcpServers` of `~/.claude.json` — old registration method. Step 5 of this setup is cleanup
- CC entry is `cd workspaces/<profile>/instance-<N>`, then `claude` — load 1 MCP of that instance only from that folder (tool prefix `mcp__isaacsim-mcp-1__*`, etc., ~150 tools)
- Codex entry is `.\launch-codex.bat` in the same folder — `CODEX_HOME=%~dp0.codex` loads workspace-local `.codex/config.toml` into codex (same server name, same env)

## Idempotent design

- Re-execution safety: `uv sync`, `.env` skip, legacy cleanup are all idempotent (cleanup is no-op if entry is absent)
- If the repo path already exists, it will not be cloned again (determined by the existence of `pyproject.toml`)

## New PC installation procedure

```bash
setup\setup-omniverse-kit-mcp.bat
```

After running:
1. Install Isaac Sim 6.0 standalone separately — override the path from `.env` to `ISAAC_SIM_KIT_EXE` / `ISAAC_SIM_KIT_FILE` (see `../README.md` Isaac Sim Setup section)
2. Start `claude` after `cd workspaces/isaac/instance-1` (or other instance folder) → Check the display of `mcp__isaacsim-mcp-N__*` / `mcp__usdcomposer-mcp-N__*` tool prefix of the corresponding instance in the system reminder.
3. For manual execution, use `isaac-sim_mcp.bat` or `kkr_usd_composer_mcp.kit.bat` in each app folder — automatically select instance port when running twice
4. Kit extension activation is automatic with `kit.exe --ext-folder ... --enable omni.mycompany.validation_api` (no need to manually toggle Extension Manager) — For detailed flags, refer to `../src/omniverse_kit_mcp/modules/CLAUDE.md`

## Be careful when editing

- Only use the `$env:USERPROFILE` standard path (developer prohibits hardcoding of absolute path)
- Maintain PowerShell `$ErrorActionPreference = 'Stop'` — to avoid silently passing on intermediate failures.
- Console output is forced to be UTF-8 (`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`)
- Structure of 4 in-repo `.mcp.json` / `../../..` relative path / Absence of environment-specific substring / Absence of template-leftover is guarded by `tests/unit/test_workspace_mcp_configs.py`

## Related Boundaries

- kit.exe execution flags and process control: `../src/omniverse_kit_mcp/modules/CLAUDE.md` (ProcessModule)
- Extension development rules: `../kkr-extensions/CLAUDE.md`
- Full list of environment variables: root `CLAUDE.md`
- Workspace directory convention: `../workspaces/README.md`