<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: docs/references/ 편집 규칙 + 재생성 파이프라인 (extensions-catalog · sensor_menu_catalog · app-specific 관리) -->
<!-- Sibling: testbed-snapshot/CLAUDE.md (읽기 순서 가이드 — 모듈 구현 시 어떤 파일부터 볼지) -->

# docs/references/ — 편집 규칙 & 재생성 파이프라인

> 이 파일은 **편집 / 재생성 규칙**. 읽기 순서 (모듈 구현 시 어느 문서부터 볼지) 는 `testbed-snapshot/CLAUDE.md` 참조.
>
> **Multi-app 범위** (2026-04-24~): 본 디렉토리의 카탈로그는 **Isaac Sim 5.1 (Kit 107.3) + USD Composer (kit-app-template, Kit 110.0-110.1) 두 앱**을 동시 커버. extensions.json 의 `apps` map 이 per-app metadata 를 보관.

## 레퍼런스 파일 맵

| 파일 / 하위 디렉토리 | 용도 | 재생성 방식 |
|---------------------|------|------------|
| `extensions-catalog.md` / `extensions.json` | **두 앱 658 unique extension 통합 카탈로그** + MCP research hint. `apps` map 으로 per-app version / path / deprecated / dependencies. `api_delta_note` 는 Kit major.minor 가 다른 공통 ext 표시 | `harvest_extension_metadata.py` (v2 multi-app) + `render_catalog_md.py` |
| `app-specific/usd-composer-unique.md` | USD Composer 에만 있는 34 ext 카테고리별 요약 (Procedural Gen / Scene Opt / Configurator / No-Code UI / Lighting Rigs / Extended Schemas) | 수동 편집 (해당 ext 목록 변동 시 재수확 결과로 갱신) |
| `app-specific/isaacsim-deprecated.md` | `omni.isaac.*` → `isaacsim.*` migration 매핑 테이블 (72 deprecated 중 30 직접 대체 + 40 부분 대체) | 수동 편집 |
| `testbed-snapshot/` | Kit SDK 원본 API 패턴 스냅샷 (읽기 전용) | `sync_testbed_snapshot.py` |
| `sensor_menu_catalog.md` | `Create > Sensors` 메뉴의 모든 센서 — vendor × model grouping + `window_menu_trigger` menu_path | Isaac Sim 기동 후 `window_menu_list(menu_path="Create")` 재호출 |

## MCP 기능 research 순서 (task-driven, 자율 루프 기준)

사용자 자연어 task 를 MCP 로 수행하려 할 때의 research flow. 각 단계는 이전 단계 결과에 의존.

0. **중복 확인**: `docs/tool-catalog.md` 에서 task 에 해당하는 기존 MCP tool 이 있는지 검색. 있으면 재사용 (이 flow 종료).
1. **카탈로그 검색**: `extensions-catalog.md` 에서 키워드로 Ctrl+F → 후보 ext 식별. entry 의 `apps` 필드로 **작업 대상 앱** 결정 (Isaac Sim / USD Composer / both). USD Composer 고유 도메인이면 `app-specific/usd-composer-unique.md` 도 교차 참조.
2. **MCP research hint 확인**: 후보 ext 의 `mcp_research_hint` (구 `mcp_extension_idea`) 필드. wrapping 아이디어가 미리 적혀있을 수 있음.
3. **API 패턴**: `testbed-snapshot/03-api-patterns.md` 에서 해당 도메인 섹션 읽기.
4. **통합 사용 예제**: Isaac Sim 의 경우 `C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/standalone_examples/` (api/ · benchmarks/ · data/) 에서 실동작 호출 패턴 확인. USD Composer 는 해당 앱의 빌드 산출물 확인.
5. **실 소스 탐색** — app 별 경로:
   - Isaac Sim: `C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/<source_dir>/<ext>/` (source_dir = `exts` / `extscache` / ~~`extsDeprecated`~~ 참조 금지 → `app-specific/isaacsim-deprecated.md` 매핑으로 modern 대체 찾기)
   - USD Composer: `C:/Users/<you>/workspace/branch/kit-app-template/_build/windows-x86_64/release/<source_dir>/<ext>/` (source_dir = `exts` / `extscache` / `extsbuild`)
   - **`api_delta_note` 있으면 양쪽 소스 diff 필수**: Kit 버전 상이로 signature 가 다를 수 있음.
   - **Command 패턴 search 팁**: 많은 ext 는 `omni.kit.commands.execute("<CommandName>", **kwargs)` 형태로 일회성 작업을 노출한다. 후보 탐색: MCP 의 `extension_search("<keyword>")` 로 관련 ext 조회 → `.commands` 로 끝나는 것 우선 (예: `omni.kit.commands`, `omni.physx.commands`, `omni.fabric.commands`, `omni.kit.graph.usd.commands`). 실행: MCP 의 `kit_command_execute("<CommandName>", payload)` 로 1줄 호출 (예: `isaacsim.asset.gen.conveyor` 의 `CreateConveyorBelt`).
6. **공식 문서**: `testbed-snapshot/nvidia-docs/` 에 관련 문서 있으면 참고.

## 센서 요청 응답 순서

사용자가 "특정 센서 사용해달라" 요청 시:

1. `sensor_menu_catalog.md` 에서 해당 vendor/model 검색
2. menu_path 확인 (e.g. `Create/Sensors/RTX Lidar/Ouster/OS1`)
3. `window_menu_trigger(menu_path=...)` 호출로 USD prim 생성 (실물 센서 schema)
4. `created_prims` 필드로 새 prim path 확인
5. 필요시 `stage_set_property` 로 mount_offset / mount_rotation 조정

mock 센서 (`sensor_attach_rtx_*` MCP tool) 는 시각 교육용 · 실 센서 데이터 필요 시 이 카탈로그 경로 사용.

## 편집 규칙

- **`extensions.json` 만 직접 편집**. `extensions-catalog.md` 는 파생물 — 재렌더로만 변경.
- `app-specific/*.md` 는 **수동 편집 허용** — 매핑 테이블 / 기능 영역 설명은 harvest 가 자동 생성하지 못함. 단 ext 이름·버전은 `extensions.json` 과 일치해야 함 (검증: render 결과와 diff).
- `testbed-snapshot/` 은 **읽기 전용**. 수정하면 `sync_testbed_snapshot.py` 재실행 시 손실됨.
- `CLAUDE.md` (이 파일) 와 `testbed-snapshot/CLAUDE.md` 는 **다른 파일** — 후자는 testbed 원본 스냅샷.

## extensions.json v2 스키마 주의사항

- `schema_version: 2` — apps map 기반 (v1 은 backward compat 위해 render 에서만 지원).
- `apps.<app>` 의 app 이름: `"isaacsim"` / `"usd_composer"` (두 개 허용). present 는 `true` 고정.
- `apps.<app>.source_dir` 허용값: Isaac Sim = `exts` / `extscache` / `extsDeprecated` / `kit/extscore`. USD Composer = `exts` / `extscache` / `extsbuild`.
- `apps.<app>.deprecated: true` 는 Isaac Sim `extsDeprecated/` 에서만 자동 설정.
- `enrichment_status` 허용값: `"enriched"` / `"skipped"` / `"bootstrap"` 3가지만. `skipped` 항목은 반드시 `skipped_reason` 설정.
- `api_delta_note` — 두 앱의 major.minor 버전이 다를 때만 자동 설정 (patch diff 는 무시). 수동 편집 가능.
- `mcp_research_hint` (v2) == `mcp_extension_idea` (v1). v2 전용 필드명.

## 카탈로그 재생성 시나리오

| 상황 | 명령 |
|------|------|
| 두 앱 중 하나라도 extscache 변동 (새 ext / 버전 업) | `uv run python scripts/harvest_extension_metadata.py` → `uv run python scripts/render_catalog_md.py` |
| JSON 수정 후 MD 재동기 | `uv run python scripts/render_catalog_md.py` |
| v1 레거시 single-app 모드 (deprecated) | `uv run python scripts/harvest_extension_metadata.py --mode v1-bootstrap [--resume]` |
| 기존 enrichment 포기하고 전수 재수확 (파괴적) | `uv run python scripts/harvest_extension_metadata.py --no-preserve-enrichment` |
| testbed 원본 변경 | `uv run python scripts/sync_testbed_snapshot.py` |
| 처음부터 재구축 | sync_testbed → harvest → render → enrichment 수동 루프 |

## harvest-progress.json 해석

- 각 phase status: `pending` → `running` → `complete`.
- v2 multi-app harvest 는 v1 bootstrap phase 를 덮지 않고 병렬 trace (향후 재설계 후보 — 현재는 v1 마커 유지).
- enrichment 단계만 수동 (Sonnet 루프). 나머지는 스크립트 자동.

## MCP tool: `extension_search` (Phase E 구현 완료)

`extensions.json` 를 local 쿼리하는 `extension_search(keyword, app, category, limit)` MCP tool. 구현: `src/isaacsim_mcp/modules/catalog_module.py` (+ `tools/module_tools.py` 등록). Isaac Sim / REST 의존 없음 — MCP 서버 프로세스 내부에서 JSON 1회 load 후 cache. 상세 사용법은 `src/isaacsim_mcp/tools/CLAUDE.md` Catalog 섹션 참조.

## Kit / app 업데이트 후 catalog 동기화

Canonical 절차는 `/catalog-sync` skill (`.claude/skills/catalog-sync/SKILL.md`). Kit / Isaac Sim / USD Composer 설치 갱신 시 사용자가 호출 → 6-step workflow (diff → integrity → harvest → render → enrichment → commit). 절차·invariants·stop-condition 은 SKILL.md 가 SoT.

## 관련 경계

- 상위 문서 루트: `../CLAUDE.md`
- 읽기 순서 가이드 (testbed-snapshot 전용): `testbed-snapshot/CLAUDE.md`
- 파생 카탈로그 (편집 금지, 재생성만): `extensions-catalog.md`, `extensions.json`, `sensor_menu_catalog.md`
- 수동 편집 허용 보강 문서: `app-specific/usd-composer-unique.md`, `app-specific/isaacsim-deprecated.md`
- 재생성 스크립트 규약: `../../scripts/CLAUDE.md`
