# Current Probe Runtime Profile Gate

Date: 2026-06-26

Scope: static unit guard for the current `probe_mcp_surface.py` synopsis and
executable commands used as Robot + RTX and official asset proof references.
Historical baseline artifacts remain historical; this check covers
`scripts/CLAUDE.md`, the current guide, and the current proof artifact set that
a new agent is expected to copy.

## Guarded Contract

Every current executable probe command in the guarded source set must keep:

- `--expect-tool-profile full`
- `--expect-app-profile isaac-sim`
- `--expect-tool-count 152`, derived in the test from the registered tool SoT
- `--require-runtime-fresh`
- `--require-robot-probe-error-contract`
- either `--runtime-info` or `--live-preflight`

This prevents a future tool-surface edit from leaving current proof commands
with a stale full-profile count or without the runtime freshness / robot typed
error-contract gates.

## Evidence

- Added `test_f3b_current_probe_commands_pin_runtime_profile_gate` in
  `tests/unit/test_doc_references.py`.
- Targeted command:
  `.\.venv\Scripts\python.exe -m pytest tests\unit\test_doc_references.py -q`
- Targeted subset result after adding the guard:
  `2 passed` for the runtime/profile gate and usage-guide artifact-link tests.

## Public Boundary

- Static documentation/test validation only.
- No live scenario was run and no stage was mutated.
- No raw local absolute paths, worker/thread IDs, process IDs, secrets, Kit
  logs, generated catalog records, or capture paths are included.
