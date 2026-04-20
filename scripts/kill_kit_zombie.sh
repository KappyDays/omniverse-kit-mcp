#!/usr/bin/env bash
# Kit 좀비 프로세스 회복 스크립트.
#
# 루트 CLAUDE.md "kit.exe USD 로드 hang — 재발 방지 프로토콜 (변경 금지)" 의
# 표준 절차 (C) 구현. Git Bash 에서 실행 시 검증된 유일한 kill 방법
# (`cmd //c "taskkill /F /IM kit.exe /T"`) 을 사용한다. `Stop-Process`,
# `.Kill()`, `taskkill /F /PID <pid>` 은 "Access is denied" 로 실패.
#
# Usage:
#     ./scripts/kill_kit_zombie.sh          # kill + restart
#     ./scripts/kill_kit_zombie.sh --no-start   # kill only
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[kill_kit_zombie] Forcing kit.exe + children termination..."
# /F: force. /IM: image name (kit.exe). /T: include child tree.
cmd //c "taskkill /F /IM kit.exe /T" 2>&1 | sed 's/^/  /' || true
sleep 3

# Verify no kit.exe remaining
REMAINING=$(powershell -NoProfile -Command \
    "Get-Process -Name kit -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count")
if [[ "${REMAINING}" != "0" ]]; then
    echo "[kill_kit_zombie] WARNING: ${REMAINING} kit.exe still alive after taskkill"
    exit 1
fi
echo "[kill_kit_zombie] All kit.exe terminated."

if [[ "${1:-}" == "--no-start" ]]; then
    exit 0
fi

echo "[kill_kit_zombie] Starting fresh Kit via ProcessModule (uses .env ISAAC_SIM_STARTUP_TIMEOUT=600.0)..."
.venv/Scripts/python.exe scripts/run_process_module_standalone.py start
