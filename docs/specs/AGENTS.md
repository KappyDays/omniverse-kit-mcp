<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-08 | Updated: 2026-04-08 -->

# specs

## Purpose
프로젝트 요구사항을 정의하는 Deep Interview 스펙 문서를 보관하는 디렉토리. 9라운드 인터뷰를 통해 목표, 제약조건, 수용 기준, 온톨로지를 확정한 결과물이다.

## Key Files

| File | Description |
|------|-------------|
| `deep-interview-isaacsim-mcp.md` | Deep Interview 스펙 (9.2KB) — 9라운드 인터뷰 결과, 최종 모호성 19% (PASSED), 목표/제약조건/비목표/수용기준 14개/온톨로지 10개 엔티티/기존 설계도 대비 변경사항 |

## For AI Agents

### Working In This Directory
- 이 문서는 **요구사항의 최종 권위(authority)**이다. 설계도와 충돌 시 이 문서가 우선한다.
- 최종 모호성 스코어 19% (임계값 20% 이하 통과). Clarity breakdown: Goal 85%, Constraint 75%, Success Criteria 80%.

### Key Decisions (설계도 대비 변경)
| 항목 | 설계도 → 인터뷰 확정 |
|------|---------------------|
| LakehouseModule | inject+query+cleanup → **query only** |
| Lakehouse 접근 | 미정 → **자체 REST API** |
| 검증 모드 | 시나리오만 → **트리거 모드 + 상태 검증 모드** |
| MCP Tool 수 | 17개 → **14개** (lakehouse inject/cleanup 제거) |
| 배포 환경 | 미정 → **localhost 전용** |
| Property 타입 | 미정 → **모든 USD Property 타입** |

### Acceptance Criteria (14개)
구현 완료 판정의 기준. `deep-interview-isaacsim-mcp.md`의 "Acceptance Criteria" 섹션 참조.

### Testing Requirements
- 수용 기준 변경 시 blueprint 설계도와의 정합성을 업데이트해야 한다.
- 새로운 인터뷰 라운드 추가 시 모호성 스코어를 재계산한다.

## Dependencies

### Internal
- `../blueprint/isaacsim-mcp-blueprint.md` — 이 스펙을 구현으로 변환한 설계도

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
