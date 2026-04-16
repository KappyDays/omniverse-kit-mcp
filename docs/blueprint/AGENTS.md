<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-08 | Updated: 2026-04-08 -->

# blueprint

## Purpose
MCP 서버의 상세 아키텍처 설계도를 보관하는 디렉토리. 프로젝트 디렉토리 구조, 핵심 타입 정의, 모듈별 상세 설계, MCP Tool 레지스트리, 시나리오 엔진 설계, Isaac Sim Extension REST API 스펙을 포함한다.

## Key Files

| File | Description |
|------|-------------|
| `isaacsim-mcp-blueprint.md` | 전체 아키텍처 설계도 (39KB) — 디렉토리 구조, Python 타입 정의, 4개 모듈 상세 설계, 17→14개 MCP Tool 정의, 시나리오 YAML 스키마, Isaac Extension REST 엔드포인트, 타임아웃/재시도 전략 |
| `isaacsim-mcp-blueprint_summary.md` | 설계도 요약 (2.6KB) — 핵심 아키텍처 다이어그램, 모듈 요약, Tool 계층, 시나리오 흐름, 구현 우선순위 |

## For AI Agents

### Working In This Directory
- `isaacsim-mcp-blueprint.md`는 구현 시 **가장 중요한 참조 문서**이다. 파일/클래스/메서드 수준의 상세 설계를 포함한다.
- `_summary.md`는 빠른 컨텍스트 파악용. 상세 내용은 반드시 원본을 참조.
- 이 설계도는 CCG(Claude+Codex+Gemini) 합성 결과이며, 일부 항목은 인터뷰 스펙에 의해 **오버라이드**됨 (특히 LakehouseModule 범위).

### Key Sections in Blueprint
| Section | Content |
|---------|---------|
| §1 프로젝트 디렉토리 구조 | 전체 파일 트리 (src/, scenarios/, tests/, isaac_extension/) |
| §2 핵심 타입 정의 | Python dataclass/TypedDict 정의 (common, stage, viewport, lakehouse, extension, scenario) |
| §3 모듈 상세 설계 | StageModule, ViewportModule, LakehouseModule, ExtensionModule 메서드 시그니처 |
| §4 MCP Tool 레지스트리 | 계층1 모듈 Tool (12개) + 계층2 시나리오 Tool (5개) 정의 |
| §5 시나리오 엔진 | YAML 스키마, Compiler, Runner, State Machine |
| §6 Isaac Extension | REST 엔드포인트, Pydantic 모델, 서비스 계층 |
| §7 인프라 | 타임아웃 정책, 재시도 정책, 로깅, 설정 |

### Testing Requirements
- 설계 문서 수정 시 `specs/` 문서와의 정합성을 확인한다.
- 특히 Acceptance Criteria 항목과 설계가 일치하는지 검증.

## Dependencies

### Internal
- `../specs/deep-interview-isaacsim-mcp.md` — 요구사항 원천 (우선순위 높음)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
