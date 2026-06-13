<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Direct execution of external .bat in branch/ fails in 3 seconds / diagnosis / recovery of unresolved dependency solver -->
# Kit dependency solver fail (`.bat` quits immediately in 3 seconds)

External Kit app build of `branch/` (`isaac-sim.bat`, `kkr_usd_composer.kit.bat`,
`kkr_usd_composer_streaming.kit.bat` etc.) runs directly and terminates in 3 seconds + in log
Enter when you see `Failed to resolve extension dependencies`.

## Symptoms

- Double-click `.bat` or run PowerShell `Start-Process` in about 3 seconds.
  cmd window is closed (before kit.exe shows GUI)
-last line of stdout log:
  ```
  [3.4xxs] [Error] [omni.kit.app.plugin] Exiting app because of dependency solver failure...
  ```
- List unresolved dependencies on stderr:
  ```
  Failed to resolve extension dependencies. Failure hints:
    * No versions of <ext-id> that satisfies: <app-id> depends on <ext-id> version *
      - Available packages for <ext-id> version *:
        (none found)
  ```
- If the unresolved candidate is a package belonging to the company or kkr-extensions, such as `omni.mycompany.*`
  There are almost 100% cases where the ext folder path is stale.

## Root cause

**Absolute path** embedded in the `[settings.app.exts.folders]` `'++'` list of the `.kit` file.
(Example: `"<old-repo>/kkr-extensions"`)
After rename / repo move, stale → Even if the kit scans the path, only empty folders are found →
Unresolved dependent extensions like `omni.mycompany.*` → Solver ends.

Representative example (2026-05-04):
-commit `be4aced refactor: rename Isaac-sim-MCP -> omniverse-kit-mcp`
  Only the working directory was renamed, but the absolute path in the `.kit` file was not updated.
- The old route `<old-repo>/kkr-extensions/` is stale (at the time of the accident),
  `<repo>/kkr-extensions/` with thread extension
  Located at → solver fails to find anything and exits

> ⚠️ Correction (2026-05-26): The above is recorded at the time of the accident on 2026-05-04. Currently `<old-repo>/`
> is not an “empty folder” because **full clone** (stale, unused, 639M) remains before renaming.
> Live uses `omniverse-kit-mcp/` — When diagnosing the solver, do not assume that the old path is empty.

## Diagnosis steps

### 1. Capture `.bat` stdout/stderr and identify unresolved dependencies

```powershell
$bat = "<workspace>\branch\<...>\<app>.kit.bat"
Start-Process $bat `
  -RedirectStandardOutput "$env:TEMP\kit_dep.log" `
  -RedirectStandardError  "$env:TEMP\kit_dep.err" `
  -PassThru -WindowStyle Hidden
# After waiting for about 5 seconds
Get-Content "$env:TEMP\kit_dep.err"
```

(Note: `Start-Process cmd.exe -ArgumentList "/c","..."` mode + inline redirect
The quoting is broken and no log is created at all — use the above pattern)

### 2. Extract from message which ext is unresolved

`* No versions of <ext-id> that satisfies: <app-id> depends on <ext-id>` in stderr
Note `<ext-id>` in line.

### 3. Verify `[settings.app.exts.folders]` path of `.kit` file```bash
grep -rn '"<workspace>/' --include='*.kit' <workspace>/branch/
# for each matched path
ls <hardcoded-path>
# stale if empty or missing
```

### 4. Check actual ext location

```bash
ls <repo>/kkr-extensions/ | grep <ext-id-stem>
```

### 5. Check recent directory rename/move commit

```bash
cd <repo>
git log --oneline -n 10 | grep -iE 'rename|move|relocat'
```

## Recovery

Update the stale absolute path of the `.kit` file to the actual ext folder location:

```bash
# grep all .kit files for stale paths
grep -rln '"<old-repo>' --include='*.kit' <workspace>/branch/
# edit each file from old to new path
# rerun the .bat after updating to validate
```

`source/apps/<app>.kit` of `kit-app-template`
`_build/.../release/apps/<app>.kit` is hardlink (same inode) as source only
Even if modified, both sides are updated — this can be confirmed by comparing the Inode of `stat <source> <build>`.

## Verification (success signal)

-`Failed to resolve extension dependencies` disappears from stderr
-`[NN.NNNs] [ext: kkr_usd_composer-<ver>] startup` or to stdout
  Reach `[ext: isaacsim.exp.full-<ver>] startup`
- `[NN.NNNs] app ready` + `[NN.NNNs] RTX ready` (Composer) /
  Proceed to `Isaac Sim Full App is loaded.` (Standalone)

## Prevent recurrence

- `docs/invariants/multi-app.md` before starting work when renaming/repo moving a directory
  Read the `## .kit ext folder absolute path` section of
- `grep -rn '"<workspace>/' --include='*.kit' branch/` immediately after rename
  Update after batch detection of stale paths
- Accident record (replay evidence): `kkr-extensions/docs/lessons-learned.md` (2026-05-04 entry)

## Related Boundaries

- Multi-app invariant Main text: `docs/invariants/multi-app.md`
- Accident record/replay evidence: `kkr-extensions/docs/lessons-learned.md`
- Cold boot diagnosis (different signature): `docs/runbooks/cold-boot-timeout.md`
- `.bat` quoting / process lifecycle: user `~/.claude/CLAUDE.md` "Shell" §