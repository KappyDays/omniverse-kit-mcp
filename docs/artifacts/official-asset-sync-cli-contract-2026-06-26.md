# Official Asset Sync CLI Contract Guard - 2026-06-26

## Scope

This artifact records a static guard for the bounded official asset live
verification chunk CLI. It covers the operator path that starts from an
existing URL/discovery snapshot, verifies a small live chunk, optionally reruns
exact classified items, and overrides a workspace REST endpoint when the
default profile endpoint does not match the worker runtime.

## Evidence

- CodeGraph inspection before the edit showed `scripts/sync_official_asset_catalog.py::parse_args`
  with no direct covering test.
- Added `tests/unit/test_official_asset_catalog_sync.py::test_parse_args_pins_bounded_live_verification_chunk_contract`.
- The guard pins `--source-run-id`, `--run-id`, single-profile `--profiles`,
  provider narrowing, `--verify full`, `--verify-kind`, `--verify-provider`,
  repeatable `--verify-id`, `--verify-limit`, `--rerun-classified`,
  longer live timeouts, `--retry`, `--base-url`, and `--resume`.

## Public Boundary

This was a static/unit contract guard, not a live Kit run. It records no local
absolute paths, worker/thread IDs, process IDs, secrets, temp log paths,
generated catalog JSON, or verification JSONL payloads.
