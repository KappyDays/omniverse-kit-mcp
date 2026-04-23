# STOP_LINE — RESCINDED 2026-04-23 10:30

## 회수 사유
사용자 직접 검증 + 정확한 진단 도구 (PowerShell `Get-Process`, MCP `simulation_get_status`, `window_capture`) 사용 결과:

- **Kit 은 죽지 않았음** (이전 모든 silent crash 진단 false negative — `tasklist //FI` git bash issue)
- **spawn 자체 동작** — `stage_load_usd` / `character_load` 직접 호출 시 stage 에 prim 정상 등록
- **Walk→Sit 시퀀스 라이브 검증 완료** (character_load → play_animation Walk → arrival → play_animation_variant SitIdle)

진짜 issue 들 분리되어 `docs/implementation_issues.md#i3, #i4, #i5, #i6, #i7` 에 기록.

## 현재 상태 (commit `<TBD>`)

| Phase | 상태 |
|---|---|
| 0 | ✅ 완료 (commit 1a54cef) |
| 1 | ✅ 완료 (commit 8c88911, +2 MCP tool) |
| 2 | ✅ 완료 (commit 22600f2, Load Warehouse + Bake live) |
| 3 | 🟡 핵심 검증 OK (Walk→Sit MCP 직접) — Extension UI button I5 별도 수정 |
| 4 | 🟡 코드 완료 + drive_physics fix I7 적용 — Kit restart 후 재검증 |
| 5 | ⏳ scenarios YAML 작성 + SSIM baseline |
| 6 | ⏳ QA + PR draft |

## 다음 단계 결정 사항 (사용자 판단)

1. **Kit restart 후 Robot drive 검증** — `_drive_physics_coro` fix (ArticulationAction.joint_velocities) 가 stale closure 로 미반영. Kit restart 후 wheel rotation delta > 2 rad 검증.
2. **Extension UI button I5 우회** — 옵션:
   - (a) MCP 직접 동작 검증 (현재 패턴) — Extension UI 는 사용자 시연용
   - (b) Extension 자체 REST endpoint 추가 (validation_api 의존 X) — claude curl 호출
3. **Phase 5 진행** — scenarios YAML + SSIM baseline (mock test 가능)

## 진짜 issue 정리

- **I3** tasklist false negative — 정확 도구로 PowerShell `Get-Process` / MCP `simulation_get_status`
- **I4** stage_capture_snapshot glob `*` 가 `/` 매치 안 함
- **I5** extension_ui_invoke callback 호출 inconsistency (hot-reload binding stale)
- **I6** validation_api hot-reload 가 module-level closure stale (Kit restart 필요)
- **I7** DifferentialController.forward() Isaac Sim 5.1 ArticulationAction 반환

이전 STOP_LINE I1, I2 의 진단 (silent crash 환경 issue) 는 **잘못된 진단** (tasklist false negative 영향). 진짜 issue 는 위 5개로 분리됨.
