# Simulation Control Settled Status Evidence (2026-06-23)

## Change

- `simulation_play`, `simulation_pause`, and `simulation_stop` now wait for at
  least one Kit update tick before returning timeline state.
- Each command waits briefly for the expected post-action state:
  - play: `is_playing=true`, `is_stopped=false`
  - pause: `is_playing=false`, `is_stopped=false`
  - stop: `is_playing=false`, `is_stopped=true`
- Control responses include `timeline_settled` and
  `timeline_settle_updates` diagnostics. If the expected state is not observed
  within the bounded wait, the command still returns the current status with
  `timeline_settled=false`.

## Unit Evidence

- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_simulation_ext_tools.py -q`
  - `8 passed`
- `.\.venv\Scripts\python.exe -m pytest tests\unit\test_simulation_module.py tests\unit\test_simulation_ext_tools.py -q`
  - `15 passed`

## Live Isaac Sim Evidence

Validation route:

- The normal live path is a workspace-local MCP worker.
- A workspace-worker route was unavailable during this smoke, and this batch
  changed `omni.mycompany.validation_api` itself, so the self-change required a
  fresh Kit process per `docs/invariants/ext-reload.md`.
- The standalone route below was used as the documented import-cache /
  low-level diagnosis bypass from `scripts/CLAUDE.md` and
  `docs/invariants/live-worker-coordination.md`, targeting only
  `workspaces/isaac/instance-1` / port `8111`.

```powershell
.\.venv\Scripts\python.exe scripts\run_process_module_standalone.py start --profile isaac-sim --instance 1
```

REST smoke sequence on `http://127.0.0.1:8111`:

1. `extension_clear_logs`
2. `simulation_get_status`
3. `simulation_play`
4. `simulation_get_status`
5. `simulation_pause`
6. `simulation_get_status`
7. `simulation_stop`
8. `simulation_get_status`
9. `extension_capture_logs(level=WARN, limit=50)`

Observed settled control payloads:

| Command | `current_time` | `is_playing` | `is_stopped` | `timeline_settled` | `timeline_settle_updates` |
|---|---:|---|---|---|---:|
| initial status | `0.0` | `false` | `true` | n/a | n/a |
| `simulation_play` | `0.016666666666666666` | `true` | `false` | `true` | `1` |
| after play status | `0.03333333333333333` | `true` | `false` | n/a | n/a |
| `simulation_pause` | `0.05` | `false` | `false` | `true` | `1` |
| after pause status | `0.05` | `false` | `false` | n/a | n/a |
| `simulation_stop` | `0.0` | `false` | `true` | `true` | `1` |
| after stop status | `0.0` | `false` | `true` | n/a | n/a |

WARN log capture:

- `count=0`
- `log_truncated=false`

Cleanup:

```powershell
.\.venv\Scripts\python.exe scripts\run_process_module_standalone.py stop --profile isaac-sim --instance 1
```
