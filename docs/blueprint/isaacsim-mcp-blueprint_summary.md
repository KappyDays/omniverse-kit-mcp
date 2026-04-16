# Isaac Sim 5.1 MCP 서버 설계도 - 요약

> CCG 합성: Codex (아키텍처) + Claude (DX/테스트), Gemini 쿼터 초과로 미참여

---

## 핵심 아키텍처

```
Claude (MCP Client) ──MCP──→ MCP Server (Python)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Isaac Sim      Lakehouse     시나리오 YAML
           (REST :8011)     (REST/SDK)     (Arrange→Act→Assert)
```

## 4개 핵심 모듈

| 모듈 | 역할 | 주요 메서드 |
|------|------|------------|
| **StageModule** | Prim/Property 검증 | `capture_snapshot`, `diff_snapshots`, `assert_prim_exists`, `assert_property` |
| **ViewportModule** | 스크린샷 & 이미지 비교 | `capture`, `compare_ssim` |
| **LakehouseModule** | 테스트 데이터 제어 | `inject`, `query`, `cleanup` |
| **ExtensionModule** | Extension 트리거/리셋 | `trigger`, `reset`, `get_state` |

## MCP Tools 2계층

- **계층 1**: 모듈 단위 12개 Tool (디버깅/단발 사용)
- **계층 2**: 시나리오 단위 5개 Tool (`scenario_validate`, `scenario_plan`, `scenario_list`, `scenario_schema`, `scenario_last_report`)

## 시나리오 실행 흐름

```
YAML 로드 → 스키마 검증 → 컴파일 → Arrange → Act → Assert → Cleanup(항상)
                                      ↓실패     ↓실패    ↓실패
                                    Cleanup   Cleanup   결과리포트
```

## Isaac Sim Extension REST 엔드포인트 (Base: `/validation/v1`)

| 카테고리 | 엔드포인트 수 | 핵심 경로 |
|----------|-------------|-----------|
| Health/Extension | 4개 | `/health`, `/extension/state`, `/extension/trigger`, `/extension/reset` |
| Stage | 3개 | `/stage/snapshot`, `/stage/assert/prim-exists`, `/stage/assert/property` |
| Viewport | 2개 | `/viewport/capture`, `/viewport/compare/ssim` |

## 타임아웃 전략

- Scenario 전체: 600s → Step: 60s → HTTP Request: 30s → Connect: 5s
- 재시도: 일시적 오류(408/429/5xx)만, 어설션 실패는 재시도 안 함

## 확장 가능 모듈

- ROS 2 토픽 검증 (`/ros2/assert/topic`)
- 물리 상태 검증 (`/physics/assert/rigid-body-state`)
- Sensor 데이터 검증 (Lidar, Depth Camera)

## 구현 우선순위

1. Isaac Extension REST 엔드포인트 (health + stage)
2. MCP 서버 골격 + StageModule + 1개 시나리오
3. ViewportModule + 이미지 비교
4. LakehouseModule + Composer/Runner
5. 확장 모듈 (ROS 2, Physics)
