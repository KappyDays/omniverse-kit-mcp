<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-08 | Updated: 2026-04-08 -->

# docs

## Purpose
프로젝트의 설계 문서와 요구사항 스펙을 보관하는 디렉토리. 아키텍처 블루프린트와 Deep Interview 결과물이 포함되어 있으며, 구현의 기준이 되는 문서들이다.

## Key Files

| File | Description |
|------|-------------|
| (없음) | 이 디렉토리 자체에는 파일 없음. 하위 디렉토리에 문서 존재 |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `blueprint/` | MCP 서버 아키텍처 설계도 — 디렉토리 구조, 타입 정의, 모듈 설계, Tool 레지스트리, 시나리오 엔진 (see `blueprint/AGENTS.md`) |
| `specs/` | 요구사항 인터뷰 스펙 — 목표, 제약조건, 수용 기준, 온톨로지 (see `specs/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- **blueprint**는 "어떻게(How)" 구현할지, **specs**는 "무엇을(What)" 만들지를 정의한다.
- 두 문서 간 차이가 있을 경우 `specs/deep-interview-isaacsim-mcp.md`가 우선한다 (인터뷰가 설계도보다 나중에 확정됨).
- 주요 차이: LakehouseModule이 설계도에서는 inject/query/cleanup 3개 메서드였으나, 인터뷰 결과 **query only**로 축소됨.

### Document Relationships
```
specs/deep-interview  ──정의──→  목표, 제약조건, 수용기준
        │
        ▼ (반영)
blueprint/isaacsim-mcp-blueprint  ──설계──→  구현 구조, 타입, 모듈
```

## Dependencies

### Internal
- 루트 `AGENTS.md` — 프로젝트 전체 컨텍스트

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
