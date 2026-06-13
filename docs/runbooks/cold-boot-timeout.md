<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: kit_app_start timeout response (still_loading / crashed) branch analysis -->
#Interpretation of cold boot timeout response

When `kit_app_start` gives a timeout response after `startup_timeout` expires, take the following action:
Your decision-making quarterly guide.

## response branch

| `process_alive` | `status` | meaning | next action |
|---|---|---|---|
| `true` | `still_loading` | Cold boot in progress. Do not spawn | **Recall** (Branch 2 Falling Continues) — Do not force kill |
| `false` | `crashed` | Immediate death or boot failure after spawn | **Instant Diagnosis** — log_tail analysis |

## still_loading processing

Cold boot may take 5-10 minutes due to GPU shader cache rebuilding, etc. status after timeout
If still_loading is:
1. Check the last line of `log_tail` — If ext registration is in progress, it is normal.
2. `kit_app_start` Recall — Enter Branch 2 (alive but health no response) and spawn
   Just continue polling without any
3. If still_loading continues even after re-invoking multiple times, hang is suspected:
   - **stdin pipe deadlock suspected** → `docs/runbooks/kit-stdin-deadlock.md`
   - Suspected hub orphan → `docs/runbooks/hub-orphan.md`
   - mtime stagnant for several minutes → `cmd //c "taskkill /F /IM kit.exe /T"` + restart

## crashed handling — log_tail analysis pattern

Diagnosis by signature of the last entries of `startup_log` / `log_tail`:

### missing ext
```
[Error] [omni.ext.plugin] Extension 'X' could not be found
```
→ Possible when `ISAAC_SIM_EXTRA_EXT_IDS` of `.env` is silently ignored (L14) →
`docs/runbooks/env-sub-config.md`

### MDL deadlock (when loading S3 asset)
```
[Warning] [omni.usd.resolver] Disabling base URL to resolve MDL identifier 'OmniPBR.mdl'
... (repeated) ...
(silent)
```
→ `LogCaptureService` active + S3 MDL-heavy asset load → carb log callback GIL contention →
Kit main loop deadlock. Avoidance: USD load 4 conditions → `docs/invariants/usd-load.md`

### GPU driver problem
```
[Error] [carb.graphics-vulkan.plugin] Failed to create Vulkan instance
```
→ Reinstall GPU driver / Check Vulkan SDK

### Hub failure
```
Hub failed to launch: child exited with exit code: 1
```
→`docs/runbooks/hub-orphan.md`

## When changing the startup_timeout default value

`ISAAC_SIM_STARTUP_TIMEOUT=600` of `.env` (e.g. when you want to wait until cold boot) —
Caution: Diagnosis is delayed in case of silent failure. Default 120 is recommended for quick diagnosis.

If the settings are not applied, check the env sub-config trap → `docs/runbooks/env-sub-config.md`

## Related Boundaries

- ProcessModule decision tree + stdin/stdout convention: `src/omniverse_kit_mcp/modules/process-ops.md`
- Process life cycle invariants: `docs/invariants/process-lifecycle.md`
- stdin pipe hang Main text: `docs/runbooks/kit-stdin-deadlock.md`
- env ignore trap: `docs/runbooks/env-sub-config.md`
- Hub orphan: `docs/runbooks/hub-orphan.md`