# STOP_LINE — PR ready for review (Phase 6 Task 6.3 직전)

## 트리거
자율 운영 정책 종료 조건 — "Phase 6 Task 6.3 의 PR draft 직전까지 자율 수행. PR 생성은 사용자 승인 사안". Phase 0~6 완료, PR draft 생성 직전 정지.

## 완료 요약

| Phase | 상태 | Commit |
|-------|------|--------|
| 0 | ✅ Tier 0/1/2 제약 재검증 | `1a54cef` |
| 1 | ✅ MCP +2 tools (navigation_sample_walkable_points, robot_drive_physics) | `8c88911` |
| 2 | ✅ Extension 골격 + Load Warehouse + Bake (live) | `22600f2` |
| 3 | ✅ Walk→Sit MCP 직접 동작 라이브 검증 | `fc2768c` |
| 4 | ✅ drive_physics live (reached=true, 11.5m 이동) | `3633297` |
| 5 | ✅ scenarios/smoke/navmesh_playground_e2e.yaml 25/25 PASSED + SSIM baseline | `6d8f468` |
| 6 | ✅ QA_CHECKLIST + lessons-learned L7-L12 | `<HEAD>` |

## 검증 통과 증거

- **pytest**: 357 passed
- **drift test**: verify_mcp_sync.py green
- **scenario**: 52.6s, 25 step PASSED (arrange 8 + act 6 + assert 5 + cleanup 6)
- **MCP catalog**: 108 tools (+2 from Phase 1)
- **Live artifacts**:
  - `docs/artifacts/phase-2-extension/phase3_walk_then_sit_window.png`
  - `docs/artifacts/phase-2-extension/phase4_robot_drive_window.png`
  - `baselines/navmesh_playground/scenario_e2e.png` (SSIM bootstrap)
- **Constraint validation**: `docs/constraint-validation-2026-04-23.md`

## 새로 발견된 issue (commit 으로 기록됨)

`docs/implementation_issues.md` 참조:
- **I3** `tasklist //FI` (git bash) false negative
- **I4** `stage_capture_snapshot` glob `*` 가 `/` 미매치
- **I5** `extension_ui_invoke` callback inconsistency (hot-reload binding stale)
- **I6** validation_api hot-reload module-level closure stale
- **I7** `DifferentialController.forward()` Isaac Sim 5.1 ArticulationAction 반환

`isaac_extension/docs/lessons-learned.md` L7-L12 에 재발 방지 규칙으로 정리.

## PR 생성 시 사용자 승인 필요

자율 운영 정책상 **PR 생성 = 사용자 명시 승인 사안**. 다음 명령으로 사용자가 직접 생성:

```bash
gh pr create --title "feat: NavMesh Playground Extension (Phase J)" --body "$(cat <<'EOF'
## Summary
- Independent Kit Extension `omni.mycompany.navmesh_playground` — full_warehouse.usd 위에 People/Robot 을 random walkable 배치 후 Walk→Sit / NavMesh path drive
- 신규 MCP tool 2 개: `navigation_sample_walkable_points`, `robot_drive_physics`
- Phase 0 constraint validation report (Tier 0/1/2)
- 25-step scenario YAML deep verification PASSED

## Changes
- isaac_extension/omni.mycompany.navmesh_playground/ (신규 ext, 8 file)
- isaac_extension/omni.mycompany.validation_api/ (+2 services + REST endpoints)
- src/isaacsim_mcp/{clients,modules,types,tools,scenario}/ (Phase 1 +2 tools, scenario action_registry)
- scenarios/smoke/navmesh_playground_e2e.yaml (25-step e2e)
- docs/constraint-validation-2026-04-23.md + artifacts
- docs/implementation_issues.md (I3-I7)
- isaac_extension/docs/lessons-learned.md (L7-L12)
- baselines/navmesh_playground/scenario_e2e.png (SSIM)

## Test plan
- [x] uv run pytest tests/ — 357 passed
- [x] scripts/verify_mcp_sync.py — green (108 tools)
- [x] scripts/run_scenario_standalone.py scenarios/smoke/navmesh_playground_e2e.yaml — 25/25 PASSED (52.6s)
- [x] Live MCP: character Walk→Sit (artifact phase3) + robot drive (phase4)
- [ ] Manual QA: isaac_extension/omni.mycompany.navmesh_playground/QA_CHECKLIST.md (15 항목)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## 자율 운영 종료

본 STOP_LINE 이 자율 운영 정책 정상 종료 지점 (Phase 6 Task 6.3 PR draft 직전). 사용자 승인 시 위 `gh pr create` 명령 실행 또는 별도 review 후 결정.
