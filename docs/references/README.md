# docs/references/ — Isaac Sim 참고 자료

## 파일

| 파일/폴더 | 무엇 | 편집 가능? |
|-----------|------|-----------|
| `extensions-catalog.md` | 621 ext 전수 카탈로그 (Markdown) | ❌ 파생물. JSON 수정 후 재렌더 |
| `extensions.json` | 권위 원시 메타 덤프 | ✅ 직접 편집 |
| `testbed-snapshot/` | `isaac-sim-testbed` 프로젝트의 reference docs + `nvidia-docs/` 복사 | ❌ 읽기 전용 |
| `harvest-progress.json` | 수확 4단계 진행도 (재개용) | 스크립트/Agent 수동 업데이트 |
| `CLAUDE.md` | 이 디렉토리 작업 지침 (검색 순서, 편집 규칙) | ✅ 작업 수정 시 동기화 |

## MCP 기능 확장 시 참조 순서

`CLAUDE.md` 의 동일 섹션 참조. 요약: `extensions-catalog.md` 키워드 검색 → `mcp_extension_idea` 확인 → `testbed-snapshot/03-api-patterns.md` → 실제 ext 소스.

## 재생성 명령

- `uv run python scripts/sync_testbed_snapshot.py` — testbed 복사
- `uv run python scripts/harvest_extension_metadata.py` — bootstrap
- Enrichment 는 수동 (Sonnet 세션). 세부는 `docs/superpowers/specs/2026-04-17-nvidia-reference-harvesting-design.md` §5.4 참조
- `uv run python scripts/render_catalog_md.py` — markdown 렌더

## 설계 및 플랜

- 설계 문서: `docs/superpowers/specs/2026-04-17-nvidia-reference-harvesting-design.md`
- 실행 계획: `docs/superpowers/plans/2026-04-17-nvidia-reference-harvesting-plan.md`
