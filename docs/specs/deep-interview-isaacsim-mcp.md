# Deep Interview Spec: Isaac Sim 5.1 Custom Extension Validation MCP Server

## Metadata
- Interview ID: isaacsim-mcp-deep-001
- Rounds: 9
- Final Ambiguity Score: 19%
- Type: greenfield
- Generated: 2026-04-08
- Threshold: 20%
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.85 | 0.40 | 0.34 |
| Constraint Clarity | 0.75 | 0.30 | 0.23 |
| Success Criteria | 0.80 | 0.30 | 0.24 |
| **Total Clarity** | | | **0.81** |
| **Ambiguity** | | | **19%** |

## Goal

Isaac Sim 5.1 환경에서 Custom Extension이 외부 Lakehouse와 통신하며 수행하는 USD Stage 변경(Prim 추가/삭제, Property 변경)을 자동으로 검증하는 MCP(Model Context Protocol) 서버를 구축한다. Claude가 자동으로 검증 시나리오를 실행하거나, 개발자가 대화형으로 개별 Tool을 호출하여 디버깅할 수 있다.

### 핵심 검증 흐름

**모드 1 - 트리거 모드:**
MCP가 Extension에 동기화 트리거 전송 → Extension이 Lakehouse에서 데이터 읽기 → Stage에 Prim/Property 반영 → MCP가 Lakehouse 기대값 조회 + Stage 실제값 비교 검증

**모드 2 - 상태 검증 모드:**
Extension이 이미 동기화를 완료한 상태 → MCP가 현재 Stage 상태와 Lakehouse 데이터를 비교하여 정합성 검증

### 데이터 매핑
- Lakehouse 1개 테이블 = 1개 Prim에 직접 대응
- 테이블의 컬럼들이 해당 Prim의 Property로 매핑됨

## Constraints

- **배포 환경**: 같은 로컬 머신에서 Isaac Sim과 MCP 서버 동시 실행 (localhost 통신)
- **Isaac Sim 버전**: 5.1 (omni.services 기반 REST 엔드포인트)
- **Isaac Sim 통신**: localhost:8011 (omni.services 기본 포트)
- **Lakehouse 접근**: 자체 REST API를 통한 조회 전용 (데이터 주입/삭제 안 함)
- **MCP 역할**: 검증 전용 (테스트 데이터 준비는 MCP 범위 밖)
- **Property 타입**: 모든 USD Property 타입 지원 (xformOp, material, mesh, custom attribute 등)
- **판정 기준**: float 값은 tolerance 허용 (시나리오별 설정 가능), 동기화 반영 타이밍은 여유 있게 (~30초)

## Non-Goals

- Lakehouse에 테스트 데이터를 주입하거나 정리하는 기능 (별도 도구로 처리)
- 원격 Isaac Sim 인스턴스와의 통신 (localhost only)
- CI/CD 파이프라인 통합 (1차 범위 밖)
- Isaac Sim 실행 자체를 관리하는 기능 (이미 실행 중인 상태 가정)
- ROS 2 토픽 검증, 물리 시뮬레이션 검증 (확장 모듈로 향후 추가)

## Acceptance Criteria

- [ ] MCP 서버가 Isaac Sim의 omni.services REST 엔드포인트와 정상 통신
- [ ] `stage_capture_snapshot` Tool로 현재 Stage의 Prim 트리 스냅샷 조회 가능
- [ ] `stage_assert_prim_exists` Tool로 특정 Prim의 존재 여부 검증 가능
- [ ] `stage_assert_property` Tool로 Prim Property 값 검증 가능 (tolerance 기반 근사 비교 포함)
- [ ] `viewport_capture` Tool로 Viewport 스크린샷 캡처 가능
- [ ] `viewport_compare_ssim` Tool로 변경 전후 이미지 SSIM 비교 가능
- [ ] `lakehouse_query` Tool로 Lakehouse 자체 REST API에서 기대값 조회 가능
- [ ] `extension_trigger` Tool로 Extension에 동기화 트리거 전송 가능
- [ ] `extension_get_state` Tool로 Extension 현재 상태 조회 가능
- [ ] `scenario_validate` Tool로 YAML 시나리오 파일 기반 자동 검증 수행 가능
- [ ] 시나리오에서 Lakehouse 기대값과 Stage 실제값의 교차 비교 검증 가능
- [ ] 모든 USD Property 타입 (float, vector, string, bool, relationship 등) 직렬화/역직렬화 지원
- [ ] Claude가 시나리오를 자동 실행하여 검증 결과를 보고할 수 있음
- [ ] 개발자가 개별 Tool을 대화형으로 호출하여 디버깅할 수 있음

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| MCP가 Lakehouse에 데이터를 주입해야 한다 | Simplifier Mode: 정말 MCP가 데이터 주입까지 해야 하는가? | MCP는 검증만. 데이터 준비는 별도 |
| Isaac Sim이 원격에서 실행될 수 있다 | Contrarian Mode: localhost 가정이 맞는가? | 같은 로컬 머신 확정 |
| 1 row = 1 Prim 매핑이다 | 더 복잡한 매핑은? | 1 테이블 = 1 Prim (테이블 레벨 매핑) |
| Transform 속성만 검증하면 된다 | 다른 Property 타입은? | 모든 USD Property 타입 지원 필요 |
| 정확한 값 일치가 필요하다 | tolerance가 필요한가? | 근사치 비교 + 시나리오별 설정 가능 |

## Technical Context

- **Isaac Sim 5.1**: omni.services (FastAPI 기반 REST, 기본 포트 8011)
- **MCP SDK**: Python `mcp` 패키지 (FastMCP)
- **HTTP 클라이언트**: httpx (AsyncClient)
- **이미지 비교**: scikit-image SSIM
- **시나리오 정의**: YAML + JSON Schema 검증
- **기존 설계도**: `2026-04-07_isaacsim-mcp-blueprint/isaacsim-mcp-blueprint.md`

### 기존 설계도 대비 변경사항

| 항목 | 기존 설계도 | 인터뷰 결과 |
|------|-----------|------------|
| LakehouseModule | inject + query + cleanup (3 메서드) | **query only** (1 메서드) |
| Lakehouse 접근 | 미정 | **자체 REST API** |
| 검증 모드 | 시나리오 기반만 | **트리거 모드 + 상태 검증 모드** |
| 사용자 | 미정 | **Claude 자동 + 개발자 대화형** |
| 배포 | 미정 | **로컬 머신 (localhost)** |
| Property 타입 | 미정 | **모든 USD Property 타입** |
| 판정 기준 | 미정 | **근사치(tolerance) + 여유 타이밍(~30s)** |
| MCP Tool 수 | 17개 (12 모듈 + 5 시나리오) | **14개** (9 모듈 + 5 시나리오, lakehouse inject/cleanup 제거) |

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| MCP Server | core | tools, modules, config, port | orchestrates Modules, exposes Tools |
| Custom Extension | core | operations, state, busy flag | modifies Stage, reads Lakehouse |
| Lakehouse | external system | REST API URL, tables | queried by MCP, read by Extension |
| USD Stage | core domain | root_layer, default_prim, prims | contains Prims |
| Prim | core domain | path, type, active, properties | belongs to Stage, maps from Table |
| Property | core domain | name, type, value, authored | belongs to Prim |
| Scenario | supporting | steps, variables, phases, modes | composes Module actions |
| Module | supporting | name, methods, protocol | wraps REST client calls |
| Validation Mode | supporting | trigger/state-check | determines execution flow |
| Table-Prim Mapping | supporting | 1 table = 1 prim, columns = properties | links Lakehouse to Stage |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 8 | 8 | - | - | N/A |
| 2 | 8 | 0 | 0 | 8 | 100% |
| 3 | 9 | 1 | 0 | 8 | 89% |
| 4-6 | 9 | 0 | 0 | 9 | 100% |
| 7 | 10 | 1 | 0 | 9 | 90% |
| 8-9 | 10 | 0 | 0 | 10 | 100% |

Ontology는 Round 8부터 완전 수렴 (stability 100%, 10 entities).

## Interview Transcript

<details>
<summary>Full Q&A (9 rounds)</summary>

### Round 1
**Q:** 이 MCP 서버를 주로 사용하는 주체는 누구인가요?
**A:** 둘 다 — Claude 자동 검증(주) + 개발자 대화형 디버깅(부)
**Ambiguity:** 73% (Goal: 0.45, Constraints: 0.20, Criteria: 0.10)

### Round 2
**Q:** 실제로 이 MCP로 검증하려는 가장 대표적인 시나리오는?
**A:** Property 동기화 검증 — Lakehouse 속성값 변경 → Extension이 Prim Property 업데이트 → 반영 확인
**Ambiguity:** 65% (Goal: 0.50, Constraints: 0.20, Criteria: 0.30)

### Round 3
**Q:** Lakehouse 테이블과 Prim의 매핑 구조는?
**A:** Lakehouse 1개 테이블 = 1개 Prim에 직접 대응
**Ambiguity:** 60% (Goal: 0.55, Constraints: 0.20, Criteria: 0.40)

### Round 4 [Contrarian Mode]
**Q:** MCP 서버와 Isaac Sim이 같은 로컬 머신에서 돌아간다는 가정이 맞는가?
**A:** 같은 로컬 머신
**Ambiguity:** 52% (Goal: 0.55, Constraints: 0.45, Criteria: 0.40)

### Round 5
**Q:** Property 비교 시 tolerance와 타이밍 기준은?
**A:** 근사치(tolerance 허용) + 여유 있는 타이밍(30초 이내)
**Ambiguity:** 44% (Goal: 0.60, Constraints: 0.45, Criteria: 0.60)

### Round 6 [Simplifier Mode]
**Q:** MCP 서버가 Lakehouse에 직접 데이터를 주입해야 하는가?
**A:** MCP는 검증만 (데이터 주입 안 함)
**Ambiguity:** 36% (Goal: 0.65, Constraints: 0.60, Criteria: 0.65)

### Round 7
**Q:** Extension 동기화 트리거는 누가 하는가?
**A:** 둘 다 지원 (MCP 트리거 + 이미 완료된 상태 검증)
**Ambiguity:** 29% (Goal: 0.80, Constraints: 0.60, Criteria: 0.70)

### Round 8
**Q:** Lakehouse 접근 프로토콜은?
**A:** 자체 REST API
**Ambiguity:** 22% (Goal: 0.80, Constraints: 0.75, Criteria: 0.75)

### Round 9
**Q:** 검증할 Property 타입 범위는?
**A:** 모든 USD Property 타입 (transform, material, mesh, custom attribute 등)
**Ambiguity:** 19% (Goal: 0.85, Constraints: 0.75, Criteria: 0.80)

</details>
