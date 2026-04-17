<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: Isaac Sim extension 카탈로그 탐색 + MCP 확장 아이디어 참조 -->

# docs/references/ — 작업 지침

## MCP 기능 추가 시 참조 순서

1. `extensions-catalog.md` 에서 키워드로 Ctrl+F. 후보 ext 식별.
2. 각 후보의 `mcp_extension_idea` 확인.
3. `testbed-snapshot/03-api-patterns.md` 에서 해당 도메인 섹션 읽기.
4. 해당 ext 의 실제 소스 (`C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/<source>/<ext>/`) 열어서 확인.
5. `testbed-snapshot/nvidia-docs/` 에 관련 공식 문서 있으면 참고.

## 편집 규칙

- **`extensions.json` 만 직접 편집**. `extensions-catalog.md` 는 파생물 — 재렌더로만 변경.
- `testbed-snapshot/` 은 **읽기 전용**. 수정하면 `sync_testbed_snapshot.py` 재실행 시 손실됨.
- `CLAUDE.md` (이 파일) 와 `testbed-snapshot/CLAUDE.md` 는 **다른 파일** — 후자는 testbed 원본 스냅샷.

## 카탈로그 재생성 시나리오

| 상황 | 명령 |
|------|------|
| testbed 원본 변경 | `uv run python scripts/sync_testbed_snapshot.py` |
| JSON 만 수정 후 MD 동기화 | `uv run python scripts/render_catalog_md.py` |
| Isaac Sim 버전 업그레이드 | `uv run python scripts/harvest_extension_metadata.py --resume` → 수동 diff 검수 → render |
| 처음부터 재구축 | 3 스크립트 순서대로 + enrichment 수동 루프 |

## harvest-progress.json 해석

- 각 phase status: `pending` → `running` → `complete`
- enrichment 단계만 수동 (Sonnet 루프). 나머지는 스크립트 자동.
- Sonnet 세션이 끊겼다가 재개할 때 이 파일 먼저 읽기.

## 향후 MCP tool 화 (제안, 미구현)

`extensions.json` 을 기반으로 MCP tool `extension_search(keyword, category=None)` 구현 가능. 설계 문서 §9.2 참조.
