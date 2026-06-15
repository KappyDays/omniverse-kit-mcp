<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: kit.exe Diagnosis / reproduction / recovery when cold boot hang occurs -->
<!-- ========================================================== -->
<!-- Protected regression note — L17 4-hour debugging result (2026-04-24) -->
<!-- -->
<!-- This file is the root when reconfiguring (CLAUDE.md Pull-First) -->
<!-- CLAUDE.md §"kit.exe cold boot hang — stdin pipe deadlock" -->
<!-- Where the main text has been transferred. Protection intent (4h+ debugging results correct -->
<!-- preservation) follows as is. Abbreviations are allowed / only the 5 items below -->
<!-- Must survive abbreviations: -->
<!-- 1. "stdin=subprocess.DEVNULL" string -->
<!-- 2. "process_module.py::start" location notation -->
<!-- 3. Verification number 240 / 13 -->
<!-- 4. "extra_ext_ids race" diagnosis invalid cross-ref -->
<!-- 5. lessons-learned See L17 -->
<!-- -->
<!-- Automatic verification: tests/unit/test_do_not_edit_guards.py G1-G7 -->
<!-- ========================================================== -->

# kit.exe cold boot hang — stdin pipe deadlock

> 4 hours of debugging (2026-04-23 hang × 2 → 2026-04-24 root cause confirmed).
> In case of recurrence, this file is entered first.

## Symptoms

- Call MCP tool `kit_app_start` / `kit_app_restart` → health until startup_timeout
  No response → `status=timeout` (or `status=still_loading` after 240s)
- `Get-Process kit` = alive (PID normal), CPU almost 0 (<5s after 5 minutes), WS ~60MB (boot
  Can't even start)
- internal kit log
  (`%LocalAppData%/../.nvidia-omniverse/logs/Kit/Isaac-Sim Full/5.1/kit_*.log`)
  At ~85-91ms, right after ext registration, mtime stagnates — the same line as `[ext: omni.kit.loop-isaac]
  registered` is the last
- Execute the same args directly with isaac-sim.bat / `scripts/run_process_module_standalone.py
  start` (in bash) is ready in 15 seconds — Same code, same .env, but different results

## Root cause

**stdin inheritance** of `subprocess.Popen`:

- MCP server (`omniverse-kit-mcp`) spawns from MCP host (Claude Code / Codex CLI) to stdio → MCP server
  stdin = bidirectional MCP protocol pipe with MCP host (Claude Code / Codex CLI)
- `subprocess.Popen(...)` of ProcessModule did not specify `stdin` argument →
  The child kit.exe inherits the MCP pipe stdin as is.
- Which init component (carb plugin / GLFW / some Python ext) during kit.exe cold boot?
  Attempt to read stdin → block in MCP pipe (MCP host (Claude Code / Codex CLI) does not fill stdin)
- The thread blocks → Waits for other init threads to join → The entire boot stops
- It is not specified which component the exact thread is (~85ms point = end of ext registration /
  (just before entering ext startup)
- When running standalone in bash, stdin = TTY → `isatty()` check passes or EOF immediately
  Return → Proceed as normal

## Fix application location

From `src/omniverse_kit_mcp/modules/process_module.py::start` to `subprocess.Popen(...)`
**Add `stdin=subprocess.DEVNULL`**. Just one line. Absolutely no omissions/changes allowed.

```python
self._process = subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,  # CRITICAL — never omit
    stdout=self._stdout_handle,
    stderr=subprocess.STDOUT,
    env=env,
    ...
)
```

## Verification (2026-04-24 actual measurement)

- Before Fix: stdin=PIPE environment simulation (`subprocess.Popen([standalone_script],
  stdin=subprocess.PIPE)`) → **240s** timeout (100% reproduction)
- After Fix: Same simulation → **13.0s** ready ✅

Reproducibility Verification (Fix Regression Prevention):
```bash
python -c "import subprocess; p=subprocess.Popen(['.venv/Scripts/python.exe','scripts/run_process_module_standalone.py','start'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True); print(p.communicate(input='', timeout=300))"
```
→ PASS must be ~13s ready, stdin DEVNULL is missing if timeout is 240s

## ⚠️ Avoid incorrect diagnosis

2026-04-23 mistake (this avoidance notation must never be removed):
- "extra_ext_ids 7-8 races" diagnosis is incorrect — stdin pipe is the actual cause.
- "GPU shader cache cold" / "user.config corruption" etc. There are only correlations.
  No causal relationship
- Changing the number of exts / dependencies only changes the timing of the stdin race — hides the real cause

When the next hang occurs:
1. **Make sure to check first whether stdin is specified** (suspect stdin=DEVNULL missing after changing the code)
2. Reducing the number of ext_ids / changing dependency is the last resort

## If additional related fixes are needed

Other `subprocess.Popen` call locations (`scripts/`, `clients/`, etc.) also have child input
If you do not want to receive it, specify `stdin=subprocess.DEVNULL` in the same manner. inheritance is default
silent leak.

## Related Boundaries

- L17 accident record original text: `kkr-extensions/docs/lessons-learned.md`
-Code location SoT: `src/omniverse_kit_mcp/modules/process_module.py::start`
- ProcessModule decision tree / hang recovery 4 types of traps: `src/omniverse_kit_mcp/modules/process-ops.md`
- Process life cycle invariants: `docs/invariants/process-lifecycle.md`
- Cold boot timeout response branch (still_loading vs crashed): `docs/runbooks/cold-boot-timeout.md`
