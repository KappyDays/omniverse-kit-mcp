@echo off
:: Activates this workspace's codex environment (single MCP entry).
:: %~dp0 = absolute path to this workspace folder (trailing backslash).
:: CODEX_HOME points to the workspace-local .codex/ — codex CLI reads config.toml from there.
:: cwd is NOT changed so that `--directory ../../..` in config.toml resolves to repo root.
set CODEX_HOME=%~dp0.codex
codex %*
