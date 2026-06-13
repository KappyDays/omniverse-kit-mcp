<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Rebuild thin USD with code → File locking / registry / pycache trap when reopening repeatedly -->
# Scene Re-export Lock — Runbook

## Symptoms

- I modified the worker/scene `.py` builder and re-exported it to the same path, but **the disk file did not change**
  (After `stage_open` reload this old content). farm session: 6 worker modifications are silently ignored.
- `CreateNew` reuses old partial content → `AddXformOp` crashes with residual xformOp.
- Misdiagnosis, such as traceback pointing to a comment line → Execution of old bytecode of stale `__pycache__`.

## Root cause

1. **File Lock**: When the Live Kit opens USD with `stage_open`, the OS locks the file, and the same path
   re-export failed silently.
2. **Sdf layer registry cache**: A failed build run leaves the layer stale in memory,
   `USD.Stage.CreateNew(path)` reuses the cache.
3. **stale `__pycache__`**: When the builder is loaded with importlib, the old `.pyc` bytecode is executed.

## Standard solving loop

1. Clear the live kit stage to release the lock: `stage_new` (no restart required unless kit crashes).
   - If only the user extension code other than the validation_api itself has changed, enter `extension_reload(ext_id)`.
     Sufficient (no kit restart required). Details: `../invariants/ext-reload.md`.
2. Builder exports using **registry/lock bypass technique**:
   ```python
   import sys
   sys.dont_write_bytecode = True          # prevents stale .pyc
   from pxr import Sdf
   layer = Sdf.Layer.CreateAnonymous()     # bypasses registry/disk locks
   # ... author the stage into the layer ...
   layer.Export(out_path)                  # atomic disk write
   ```
3. Re-open and verify: `stage_open(out_path)`.

## helper

`scripts/rebuild_scene.py <builder.py> --out <out.usd> [--reopen]` does the above loop with one command.
Perform. The builder uses either `build(layer)` (authored on anonymous layer) or `build_to(out_path)`.
Just expose it. The wrapper sets `sys.dont_write_bytecode=True` and prioritizes the anonymous-layer path.

## Related Boundaries

- USD load 4 conditions + copy paste recipe: `../invariants/usd-load.md`, `../../kkr-extensions/docs/usd-load-deadlock-recipe.md`
- Extension reload (avoid kit restart): `../invariants/ext-reload.md`
- Memory: `project_scene-reexport-file-lock`