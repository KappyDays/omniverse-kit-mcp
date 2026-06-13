<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Historical incident log — For tracking accident context/reproducible evidence. Permanent rules are incorporated into docs/invariants/ -->

# Lessons Learned — Historical Incident Log

**The role of this file has changed** (2026-04-24 Pull-First restructure):
- In the past, it was "must read before new work", but **Permanent rules (L14/L15/L16/L17, etc.) have been transferred to `../../docs/invariants/*.md` and `../../docs/runbooks/*.md`**
- Must read when starting a new task → Read invariants/pull-doc. The "Required pull-doc before work" table in root `../../CLAUDE.md` is the entry point.
- This file is a historical log for **accident context tracking / reproduction evidence / incorrect diagnosis avoidance records**. Refer to detailed symptoms/reprocedures in case of recurrence.
- Do not add new permanent rules here, but create a new pull-doc in `docs/invariants/` (target for loading before work)

Entry format (historical entries):
- **Cause** — What went wrong (1-2 sentences)
- **Symptoms** — How do they manifest themselves?
- **Prevention of recurrence** — What to do next time (specific procedures) — Permanently regularized items add invariants/ pointer

---

## 2026-05-04 — `branch/` External Kit app `.bat` direct execution fails (directory rename aftereffects)

###L18. The absolute path of `[settings.app.exts.folders]` of `.kit` is stale after repo rename → dependency solver terminates immediately

- **Cause**: Commit `be4aced refactor: rename Isaac-sim-MCP -> omniverse-kit-mcp` renames only the working directory, and the absolute path of `.kit` embedded in the external kit app build of `branch/` (`<old-repo>/kkr-extensions`, etc.) is missing from update. In the old path, only an empty folder remains, and the actual extension moves to `omniverse-kit-mcp/kkr-extensions/` → Kit does not find `omni.mycompany.*` in the ext folder → Solver terminates immediately.
- **Files affected** (3 locations, all stale pattern):
  -`branch/isaac-sim-standalone-5.1.0-windows-x86_64/apps/isaacsim.exp.full.kit` line 191
  - `branch/kit-app-template/source/apps/kkr_usd_composer.kit` line 188 (hardlink with `_build/.../release/apps/`)
  - `branch/usd-composer-webrtc-streaming/kit-app-template/source/apps/kkr_usd_composer.kit` line 189 (old path is `isaac_extension`, but same stale pattern)
- **Symptoms (actual measurement 2026-05-04)**:
  - Direct execution of `.bat` closes cmd window in about 3 seconds (before kit.exe shows GUI)
  -stderr last line:
    ```
    [3,235ms] [Error] [omni.ext.plugin] Failed to resolve extension dependencies. Failure hints:
      [isaacsim.exp.full-5.1.0] dependency: 'omni.mycompany.navmesh_playground' = { version='^' } can't be satisfied. ...
    [3,236ms] [Error] [omni.kit.app.plugin] Exiting app because of dependency solver failure...
    ```
  - kkr_usd_composer side has unresolved ext `omni.mycompany.validation_api`
- **Avoiding incorrect diagnosis**:
  - `%%` of `"%%~dp0apps/..."` in kkr_usd_composer.kit.bat line 3 is batch escape — evaluated normally as the second expansion within `call`. **Do not touch here** (First hypothesis, but wrong answer)
  - "Extension registry sync problem" / "registry URL incorrect" are also just post-symptoms — the `Synced registries: ... found N packages` message in the solver is normal, and the real cause is that the ext folder is an empty directory.
- **Prevention of recurrence**:
  - When renaming / repo moving a directory, read the `## .kit ext folder absolute path` section of [`docs/invariants/multi-app.md`](../../docs/invariants/multi-app.md)] before starting work.
  - Batch detection of stale paths with `grep -rn '"<workspace>/' --include='*.kit' branch/` immediately after rename
  - Diagnostic/recovery procedure text: [`docs/runbooks/kit-dep-solver-fail.md`](../../docs/runbooks/kit-dep-solver-fail.md)
- **Residual cleanup (concurrent processing on 2026-05-04)**:
  - Remove empty stale directory `<old-repo>/` (rename remnants)
  - All three `.kit` are unified into `<repo>/kkr-extensions`

---

## 2026-04-24 — ProcessModule cold boot hang root cause

### L17. Omission of `stdin` in `subprocess.Popen` = boot stop in MCP server child process- **Cause**: `subprocess.Popen(...)` of `src/omniverse_kit_mcp/modules/process_module.py::start()` does not specify the `stdin` factor. MCP server (`omniverse-kit-mcp`) is a stdio child of Claude Code, so stdin = MCP protocol two-way pipe. The child kit.exe inherits the pipe stdin → cold boot Attempts to read stdin at some init stage → indefinite block in the MCP pipe → the thread + join waiting threads all stop → the entire boot stops.
- **Symptoms (actual hang twice on 2026-04-23, root cause confirmed on 2026-04-24)**:
  - `isaac_sim_start` response `status=timeout` (after 240s) or `status=still_loading`
  - PowerShell `Get-Process kit`: alive (PID normal), CPU < 5s (idle for 5 minutes), WS ~60MB (failed to boot)
  - internal kit log (`%LocalAppData%/../.nvidia-omniverse/logs/Kit/Isaac-Sim Full/5.1/kit_*.log`) mtime is stagnant at **~85-91ms** (last line is usually `[ext: omni.kit.loop-isaac] registered`)
  - If you call the same code/same .env from `bash` to `scripts/run_process_module_standalone.py start`, **normally ready in 15 seconds** — false negative risk
- **Avoiding incorrect diagnosis** (mistake on 2026-04-23):
  - "extra_ext_ids 7-8 races", "GPU shader cache cold", "user.config corruption", etc. are all correlational and not causal.
  - Changing the number of exts / dependencies only changes the timing of the stdin race — hides the real cause
  - When the next hang occurs, **Make sure to check first whether stdin is specified** (suspect of omission when modifying the code)
- **Prevention of recurrence (code baseline)**:
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
  - Other `subprocess.Popen` calls also specify `stdin=DEVNULL` in the same way if the child does not receive input (default = inherit, so silent leak)
  - Reproducibility verification (Fix regression prevention): `python -c "import subprocess; p=subprocess.Popen(['.venv/Scripts/python.exe','scripts/run_process_module_standalone.py','start'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True); print(p.communicate(input='', timeout=300))"` → PASS must be ~13s ready, stdin DEVNULL is missing if timeout is 240s
- **Details**: Root `CLAUDE.md §"kit.exe cold boot hang — stdin pipe deadlock"` and `src/omniverse_kit_mcp/modules/CLAUDE.md §"ProcessModule hang recovery"` 1

---

## 2026-04-23 — NavMesh Playground (Phase J) implementation session### L15. `ext_ui_invoke` Real cause of "float division by zero" = Panel layout not initialized- **Cause**: `omni.kit.ui_test.input.emulate_mouse:49` calls `pos.x / window_width`. `window_width = ui.Workspace.get_main_window_width()` **returns 0 for 1 to 10 frames immediately after panel creation (or immediately after `extension_activate(reload=True)`) → `ZeroDivisionError`. OS window is normal (3864×2100, check `window_list`).
- **Symptoms (Actual measurement 2026-04-23)**:
  - First `ext_ui_invoke` failure: HTTP 500 "float division by zero"
  - Recalling the same path also fails (workspace does not settle)
  - After calling `window_ui_show(name, focus=true, settle_frames=10)` → all ext_ui_invoke success
- **True Avoidance**: Call sequence
  ```
  window_ui_show(panel, focus=true, settle_frames=10)
    → ext_ui_invoke(widget_path)  # now works normally
  ```
- **Prevention of recurrence (code)**:
  - `validation_api/services/ui_service.py::ui_invoke` automatically calls `_auto_show_window(name, settle_frames=10)` in the window part of widget_path (auto-settle)
  - Additional defense measures: `_install_ui_test_dimensions_patch()` replaces `omni.kit.ui_test.input.emulate_mouse` with monkey-patch — OS app-window dimensions when workspace dimensions=0 (legacy normalized channel; absolute coordinates are not affected)
  - Apply both layers — either one alone is sufficient for fixation, but if applied together, it is robust against future timing changes.
- **L8 Update**: Previously diagnosed as "ext_ui_invoke binding stale", but actually it was a layout race. L8's "Only click directly with the user's mouse is stable" is invalid — Claude can also click with the above sequence.

### L14. pydantic-settings v2 sub-config does not accept parent `env_file`

- **Cause**: When `AppConfig(BaseSettings)` has `model_config = SettingsConfigDict(env_file=".env")` and a sub-config (`IsaacSimProcessConfig`, etc.) is instantiated as `Field(default_factory=IsaacSimProcessConfig)`, **each sub-config is an independent BaseSettings instance**, so it does not propagate the parent's `env_file`. If you do not have your own `env_file`, refer only to the OS environment variable.
- **Symptoms (Actual measurement 2026-04-23)**:
  - Always ignore `ISAAC_SIM_STARTUP_TIMEOUT=120.0` of `.env` → Use default 240.0
  - `ISAAC_SIM_EXTRA_EXT_IDS=[7 entries]` of `.env` is always ignored → default 4 only → navmesh_playground, etc. are inactive
  - Silent failure with no effect even if user/operator changes `.env`
- **Prevention of recurrence**:
  - Specify `env_file=".env"` in all sub-`BaseSettings` (config.py is SoT)
  - Same pattern when adding a new sub-config (env_prefix + env_file + extra="ignore")
  - Verification command (required before PR):
    ```bash
    .venv/Scripts/python.exe -c "from omniverse_kit_mcp.config import AppConfig; ac=AppConfig(); print(ac.isaac_sim_process.startup_timeout)"
    ```
    → Confirm that `.env` value is reflected### L13. Replacing Extension UI verification with direct MCP call eliminates bugs in the controller code path.

- **Cause**: Verify the spawn/Go/Sit operation of navmesh_playground by directly calling MCP `character_load` / `character_play_animation_variant` → Passed. However, when the user clicks the Extension UI button, a **different path** of `_on_spawn_random` → `safe_spawn_character_sync` (self-implementation) → `_walk_then_sit` (controller code) is used. 6 bugs accumulated (AnimGraph incorrect path suffix, JobService method name error, SkelRoot vs parent prim path confusion, etc.).
- **Symptom**: MCP verification result = "all PASSED", user UI click result = "Animation graph not assigned valid skeleton" + "Type mismatch (Action, Walk variables)" + "Unsupported type: list" + "JobService has no attribute status".
- **Prevention of recurrence**:
  - Extension UI button operation **must be measured by button clicking like the user**. The MCP equivalent call only checks the possibility of operation, not verification.
  - When controller / usd_loader uses validation_api singleton, prevent dual-path drift by directly matching the method name + signature + response dict key with **service code SoT**. Example: `vr._job.get_status` (sync) vs `vr._job.status` (X). `_ANIM_GRAPH_SUFFIX` also follows character_service.py SoT.
  - If there are two types of paths (parent payload vs SkelRoot) like AgentRecord, separate them into separate fields (`prim_path` + `skel_root_path`) — Reusing a single field causes delete vs animation API conflict.

###L7. `tasklist //FI "IMAGENAME eq kit.exe"` (git bash) is false negative

- **Cause**: The `tasklist //FI` call in git bash has a timing/filter processing buggy. alive Kit also returns an empty result.
- **Symptom**: During this session, all 8+ “silent crash” diagnoses were incorrect. Kit was alive (confirmed by PowerShell `Get-Process -Name kit` + MCP `simulation_get_status` 200 response).
- **Prevention of recurrence**: Kit alive can only be judged using the following tools:
  - **PowerShell** `Get-Process -Name kit -ErrorAction SilentlyContinue`
  - **MCP** `simulation_get_status` (response ≤ 1s = alive)
  - **`curl http://127.0.0.1:8111/validation/v1/health`** (200 = alive)
  - Never use `tasklist //FI` (git bash). Correction in `src/omniverse_kit_mcp/modules/CLAUDE.md §"ProcessModule hang recovery"`.

###L8. `extension_ui_invoke` callback call inconsistency (after hot-reload)- **Cause**: Mouse event simulation of `omni.kit.ui_test.click` points to stale button widget reference when hot-reload accumulates (closure of previous panel instance).
- **Symptom**: ext_ui_invoke response OK + post_state normal, but button callback itself is not called (no carb.log_warn log, prim not created). User mouse direct click only stable.
- **Prevention of recurrence**: Autonomous verification creates equivalent results through **MCP direct operation** (`stage_load_usd`, `character_load`, `navigation_*`, etc.) (spec §14 intent). Extension UI button is for user demonstration. Automatic verification is blocked when multiple `extension_ui_invoke` are used in the spec's scenarios YAML — Rewrite as an equivalent MCP action if necessary.

### L9. Extension `.py` hot-reload — fswatcher can only be disabled → enabled, sys.modules cleanup cannot be trusted

- **Cause (Re-diagnosis verified on 2026-04-23)**: omni.ext.plugin (C++) fswatcher automatically watches the ext python folder — When saving a file, the kit log `FS Change triggers reloading: <path>` + `Processing ext disable request` + `on_shutdown` + `enable` + `on_startup` sequence occurs. **But sys.modules cleanup is not guaranteed** — `_reload_enabled = False` (omni/ext/_impl/_internal.py:152 default) is assumed to apply to the fswatcher path as well.
- **Validation (verification after adding hard-coded `_reload_marker` response field in validation_api)**: Modify code → Save file → fswatcher reload sequence occurs correctly → However, marker field does not appear in response = **New code is not imported**. In other words, disable → enable occurs, but `from .rest_router import router` returns to the old cached module.
- **Previous (2026-04-23 am) Wrong conclusion**: The correction to "fswatcher automatically reloads — MCP toggle not required" was inferred from the fact that the `ui.Button` label change of navmesh_playground was reflected on the screen. In fact, as ui_panel's build() was newly called with the `ui.Workspace.get_window()` zombie sweep code (L16), some of the new ui_panel module was *accidentally* cleaned up, or more precisely, the reload itself was a partial operation.
- **Reliable Conclusion** (no changes):
  - **To ensure that the code is reflected after modifying Extension `.py`, Kit process restart** (`isaac_sim_restart` or `scripts/run_process_module_standalone.py stop + start`)
  - fswatcher reload may work for some changes, but is unreliable — always requires verification. Like validation_api, the module-level singleton (`_window = WindowService()`) pattern fails to reload 100% of the time.
  - MCP `extension_activate(ext_id, reload=True)` also does not cleanup sys.modules — same limitations as fswatcher
  - **Change verification pattern**: Call with a hard-coded marker (e.g. add a response field) to the code → If the marker is not visible, reload fails → Kit restart

###L16. fswatcher auto reload + ui.Window orphan zombie

- **Cause**: omni.ext.plugin fswatcher automatically disable→enable when saving .py. Just calling `self._window.destroy()` from `on_shutdown` does not immediately unregister it from the window registry of `ui.Workspace`, but is processed at the **next update tick**. Next `on_startup` creates a new `ui.Window` with the same name within the same tick → 2 entries with the same name in the registry (OLD-being-destroyed + NEW).
-**Symptoms**:
  - kit log: `[Warning] [omni.ui_query.query] found 2 windows named "<name>". Using first visible window found`
  - `extension_get_ui_tree` reports two matches as `matched_windows: ["<name>", "<name>"]`
  - When Walker walks OLD (visible), stale widget tree is returned → MCP UI automation calls old widget path → callback is not fired
  - If accumulated, memory leaks (until Kit restart)
- **Prevention of recurrence** (`navmesh_playground/extension.py` + `ui_panel.py` application pattern):
  ```python
  # extension.py on_shutdown
  if self._window is not None:
      self._window.visible = False  # deregister hint for Workspace
      self._window.destroy()
      self._window = None

  # ui_panel.py build() start
  existing = ui.Workspace.get_window("<name>")
  if existing is not None:
      existing.visible = False
      existing.destroy()
  self._window = ui.Window("<name>", ...)
  ```
  - Both layers must be applied to be effective — If destroy is deferred, build() sweep is backup
  - If you need a completely zero zombie, yield next_update_async() twice in build() and then sweep — Currently, one invisible orphan remains, but since the walker picks only normal NEWs with the first visible rule, there is no effect on the user.
  - **Recommended standardization of `visible=False; destroy(); =None` pattern for on_shutdown of all new/existing extensions**

### L10. `DifferentialController.forward()` Isaac Sim 5.1 type change

- **Cause**: Different from spec §T2.1 assumption "numpy.ndarray (2,) or list[2]". `DifferentialController.forward([lin, ang])` in Kit 5.1 returns **`ArticulationAction` object** (wheel velocity in joint_velocities property).
- **Symptom**: `TypeError: 'ArticulationAction' object is not subscriptable` (when trying subscript `wv[0]`).
- **Prevention of recurrence**: Kit SDK API return type is not enough to simply check `extension_list_all` enabled in Phase 0. You need to check the type by actually calling `forward()`. This ext of `_drive_physics_coro` is compatible with both sides:
  ```python
  wv = ctrl.forward([lin, ang])
  if hasattr(wv, "joint_velocities") and wv.joint_velocities is not None:
      jv = np.asarray(wv.joint_velocities, dtype=np.float32)
  else:
      jv = np.asarray(wv, dtype=np.float32)
  ```### L11. CreatePayloadCommand silently fails when the nested parent is not created- **Cause**: When `CreatePayloadCommand(path_to="/World/People/People_01")` is called, if `/World/People` Xform does not exist, silent fail. prim not created, error not raised.
- **Symptom**: The callback log outputs "safe_load_usd_sync OK", but prim does not exist in the stage. It was caught next time by strengthening validation (raise if `prim.GetTypeName()` is empty).
- **Prevention of recurrence**:
  - Automatic creation of nested intermediate Xform with `_ensure_parent_xform(stage, prim_path)`
  - Or use a simple 1-step path (`/World/People/People_01` instead of `/World/People_01`) — User Insight (same pattern as Load Warehouse)
  - When checking prim validity, only `IsValid()` is not enough — `GetTypeName()` is also verified

###L12. `stage_capture_snapshot` glob `*` does not match `/`

- **Cause**: `*` of glob does not cross the path separator (`/`).
- **Symptom**: `include_prim_patterns=["/World/People*"]` does not match `/World/People/People_01`.
- **Prevention of recurrence**: Specify exactly as `["/World/People/*"]` (stage 1 children) or `stage_assert_prim_exists(prim_path=...)`.

---

## 2026-04-22 — isaac_tutorial first implementation session

###L1. Service signature is called as an assumption in the plan step

**Cause**: Instead of directly checking the `validation_api.services.*` method signature, the calling code was written as “I would usually use this kwarg.” In reality, most methods have a single `request: dict` argument + Pydantic `ConfigDict(extra="forbid")` and one unfamiliar key will immediately throw a TypeError.

**Symptoms**:
-`StageService.load_usd() got an unexpected keyword argument 'url'`
-`TypeError: RobotService.__init__() missing 1 required positional argument: 'job_service'`

Both only work with the live kit. pytest cannot detect MagicMock because it accepts all signatures.

**Prevent recurrence**:
1. Check the signature as `grep "async def\|def "` in the relevant `services/<name>_service.py` before calling.
2. If the request is a dict, check the field name by looking for `class ...RequestModel` in `models/<name>.py`
3. To confirm the return, check the dict key with `grep "return {"`
4. Assert **positional dict argument + correct key** in test (`call_args.args[0] == {...}` form)

###L2. Trying to create a Service instance directly

**Cause**: Instantiated without arg like `RobotService()`, `CharacterService()`. Actually `RobotService(job_service)`, `CharacterService(job_service, stage_service)` dependency chain.

**Symptom**: `TypeError: RobotService.__init__() missing 1 required positional argument: 'job_service'` (live Kit only)

**Prevent recurrence**:
- When reusing validation_api, **never instantiate it directly**
- After `from omni.mycompany.validation_api import rest_router as vr`, use module level singleton such as `vr._stage`, `vr._robot`, `vr._character`, `vr._job`
- This reuse guide is obsolete. Current extension policy is validation_api service import
  Instead, call the Kit SDK directly.

###L3. Kit 107 omni.ui font atlas does not have CJK glyph

**Cause**: Inserting Korean into UI label / tooltip / status. Kit 107 `omni.ui` font atlas only loads ASCII + Latin glyph when starting kit.exe, and there is no font replacement path at the time of Extension `on_startup`.

**Symptom**: All Korean characters are rendered as mojibake (□□□ / broken square). The function works, but the student cannot read it.

**Prevent recurrence**:
- **All UI strings English only**. label, tooltip, status_label text, notification message all
- Be careful of special characters: `✓` / `✗` / `→` / `×` / `÷`, some of which are in Latin, but conservatively, `[OK]` / `[FAIL]` / `->` / `x` / Use `/`
- Korean is only allowed in docstring / code comment / git commit message (Kit Console output is OK, not UI widget)
- Actual measurement: Inspection with `grep "[Hangul]" kkr-extensions/omni.mycompany.<ext>/`, leaving only the runtime string

###L4. omni.ui widget cannot be unit verified in pytest

**Cause**: Attempting to write a pytest test in a UI panel (env_setup_panel, steps_panel, main_window). `omni.ui` is an empty ModuleType stubbed in conftest.py — does not simulate the actual behavior of the widget.

**Symptom**: UI-related tests such as `assert btn.text == "..."` are in the state of “the test passes, but the actual behavior is unknown.” Or the import fails altogether due to stub limitations.

**Prevent recurrence**:
- Code using `omni.ui` is separated from **actions / state / services logic**, and only the logic part is verified with pytest.
- The UI part is verified with **live Kit + Extension’s unique QA_CHECKLIST**
- The stub in conftest.py is at the “import only” level — it is stated in the comment that it is not for verifying widget behavior.

###L5. New extension is independent structure (policy)

**Cause**: When initially designing `isaac_tutorial`, "validation_api services in-process import" was suggested as the default pattern. But this is due to the special situation of tutorial_ext (heavy orchestration — office load, sit_on_prim, NavMesh navigate needs to be reused).

**Symptom**: If all new extensions follow this pattern, the dependency graph increases, student distribution 2-Extension is required, and validation_api updates risk breaking downstream.**Reoccurrence Prevention (Policy)**:
- New Extension calls **Kit SDK directly (independent structure)** by default
- If you need to load S3 MDL-heavy asset, **copy** the defense code of `usd-load-deadlock-recipe.md` (not import)
- Do not reuse validation_api service import. The necessary functions are in the Kit SDK within the extension.
  Implemented by direct call
- Copy and paste the “New Independent Extension Skeleton” template from `extension-basics.md` when starting a new extension.

### L6. Large single CLAUDE.md is not maintained**Cause**: `kkr-extensions/CLAUDE.md` contains all validation_api internal implementation + domain trap + Extension common rules + tutorial_ext section in a single file, resulting in a bloat of 275+ lines.

**Symptoms**:
- It is difficult for the person creating a new extension to determine “what to read” (even unrelated content in validation_api is read)
- No location to record lessons learned
- Topics mix together, reducing searchability

**Prevent recurrence**:
- Operate `kkr-extensions/CLAUDE.md` only as **nav hub** (Extension list + policy + docs/* pointer)
- Separated by topic under `kkr-extensions/docs/` (extension-basics / kit-sdk-pitfalls / usd-load-deadlock-recipe / lessons-learned)
- New Extensions should not have a **CLAUDE.md file itself** — Common content should be limited to docs/, and individual QA should be limited to QA_CHECKLIST.md in each Extension folder.

---

## How to add an entry

If you encounter a new mistake:

1. Add section at the top of this file (most recent session) (date + session title H2)
2. `### L<number>. title` + **Cause/Symptom/Recurrence Prevention** 3 fields for each mistake
3. Include specific file paths/symptom logs/prevention procedure scripts if possible.
4. `docs(lessons): ...` prefix in Commit message