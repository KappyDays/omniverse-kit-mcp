#!/usr/bin/env bash
# Runner for the CLAUDE.md Pull-First restructure regression suite (plan §5 / §9).
#
# Captures, in the target directory:
#   pointer_map.json   — documentation link graph (static, no kit)
#   unit_tests.json    — pytest tests/unit/ + integration env test (static, no kit)
#   live.json          — pytest tests/integration/test_mcp_live_smoke.py -m live
#   mcp_sync.txt       — verify_mcp_sync output
#   baseline_sha.txt   — current HEAD sha (kept as historical pointer)
#
# Usage
#   scripts/run_restructure_tests.sh docs/artifacts/restructure-baseline/pre
#   scripts/run_restructure_tests.sh docs/artifacts/restructure-baseline/post
#
# Env (optional):
#   CLAUDE_ROOT_HARDCAP   baseline=300  post=100
#   CLAUDE_SUB_HARDCAP    baseline=260  post=150
#   SKIP_LIVE=1           skip the live smoke (Isaac Sim not running)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <output_dir>" >&2
  exit 2
fi

OUT_DIR=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
mkdir -p "$OUT_DIR"

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PY=".venv/Scripts/python.exe"

cd "$PROJECT_ROOT"

echo "== [1/5] pointer_map =="
"$PY" scripts/extract_pointer_map.py --out "$OUT_DIR/pointer_map.json"

echo "== [2/5] unit_tests (tests/unit/ + env sub-config) =="
"$PY" scripts/capture_pytest_report.py \
  --out "$OUT_DIR/unit_tests.json" \
  -- tests/unit/ tests/integration/test_env_sub_config.py

echo "== [3/5] mcp_sync =="
"$PY" scripts/verify_mcp_sync.py > "$OUT_DIR/mcp_sync.txt" 2>&1 || true

echo "== [4/5] baseline_sha =="
git rev-parse HEAD > "$OUT_DIR/baseline_sha.txt"

if [[ "${SKIP_LIVE:-0}" == "1" ]]; then
  echo "== [5/5] live.json SKIPPED (SKIP_LIVE=1) =="
else
  echo "== [5/5] live smoke (tests/integration/test_mcp_live_smoke.py -m live) =="
  "$PY" scripts/capture_pytest_report.py \
    --out "$OUT_DIR/live.json" \
    -- tests/integration/test_mcp_live_smoke.py -m live || true
fi

echo "done → $OUT_DIR"
