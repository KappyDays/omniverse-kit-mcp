<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: docs/references/ 편집 규칙 + public-safe reference 관리 -->

# docs/references/ — 편집 규칙 & public-safe reference 관리

> Public repo 에는 curated reference 만 둔다. 로컬 Kit / Isaac Sim / USD
> Composer 설치 메타데이터나 외부 문서 스냅샷은 생성 가능하지만 commit 하지
> 않는다.

## 레퍼런스 파일 맵

| 파일 / 하위 디렉토리 | 용도 | 재생성 방식 |
|---------------------|------|------------|
| `sensor_menu_catalog.md` | `Create > Sensors` 메뉴의 모든 센서 — vendor × model grouping + `window_menu_trigger` menu_path | Isaac Sim 기동 후 `window_menu_list(menu_path="Create")` 재호출 |
| `extensions.json` / `extensions-catalog.md` / `harvest-progress.json` | 로컬 설치 기반 extension catalog (public repo 에서는 ignored) | `harvest_extension_metadata.py` + `render_catalog_md.py` |
| `app-specific/` / `testbed-snapshot/` | 로컬 research 보강 자료 (public repo 에서는 ignored) | 필요 시 로컬에서 재생성 / 별도 보관 |

## MCP 기능 research 순서 (task-driven, 자율 루프 기준)

사용자 자연어 task 를 MCP 로 수행하려 할 때의 research flow. 각 단계는 이전 단계 결과에 의존.

0. **중복 확인**: `docs/tool-catalog.md` 에서 task 에 해당하는 기존 MCP tool 이 있는지 검색. 있으면 재사용 (이 flow 종료).
1. **기존 tool 중복 확인**: `docs/tool-catalog.md` 에서 task 에 해당하는 MCP tool 검색.
2. **로컬 catalog 가 있으면 검색**: `extension_search(...)` 또는 ignored
   `docs/references/extensions-catalog.md` 에서 후보 ext 식별. 없으면 다음 단계로
   진행하고 필요한 경우 catalog 를 로컬 재생성.
3. **실 소스 탐색** — app 별 설치 경로에서 직접 확인:
   - Isaac Sim: `<isaac-sim-root>/exts`, `extscache`, `kit/extscore`
   - USD Composer: `<usd-composer-root>/exts`, `extscache`, `extsbuild`, `kit/extscore`
   - **Command 패턴 search 팁**: 많은 ext 는 `omni.kit.commands.execute("<CommandName>", **kwargs)` 형태로 일회성 작업을 노출한다. 후보 탐색: MCP 의 `extension_search("<keyword>")` 로 관련 ext 조회 → `.commands` 로 끝나는 것 우선 (예: `omni.kit.commands`, `omni.physx.commands`, `omni.fabric.commands`, `omni.kit.graph.usd.commands`). 실행: MCP 의 `kit_command_execute("<CommandName>", payload)` 로 1줄 호출 (예: `isaacsim.asset.gen.conveyor` 의 `CreateConveyorBelt`).
4. **공식 문서**: NVIDIA / Omniverse 공식 문서를 직접 확인하고, durable rule 만
   project docs 로 요약.

## 센서 요청 응답 순서

사용자가 "특정 센서 사용해달라" 요청 시:

1. `sensor_menu_catalog.md` 에서 해당 vendor/model 검색
2. menu_path 확인 (e.g. `Create/Sensors/RTX Lidar/Ouster/OS1`)
3. `window_menu_trigger(menu_path=...)` 호출로 USD prim 생성 (실물 센서 schema)
4. `created_prims` 필드로 새 prim path 확인
5. 필요시 `stage_set_property` 로 mount_offset / mount_rotation 조정

mock 센서 (`sensor_attach_rtx_*` MCP tool) 는 시각 교육용 · 실 센서 데이터 필요 시 이 카탈로그 경로 사용.

## 편집 규칙

- `sensor_menu_catalog.md` 는 MCP resource source 이므로 tracked 유지.
- 생성 catalog / snapshot 은 `.gitignore` 대상이다. public repo 에 commit 금지.
- catalog 에서 발견한 durable rule 은 원문 덤프 대신 `docs/invariants/` 또는
  `docs/runbooks/` 로 요약 이관한다.

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

`extension_search(keyword, app, category, limit)` 는 local generated
`extensions.json` 이 있을 때만 검색한다. public clone 에서 파일이 없으면
`EXTENSION_CATALOG_UNAVAILABLE` 을 반환한다. 구현:
`src/omniverse_kit_mcp/modules/catalog_module.py`.

## Kit / app 업데이트 후 catalog 동기화

Canonical 절차는 `/omniverse-kit-extension-catalog-sync` skill (`.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md`). Kit / Isaac Sim / USD Composer 설치 갱신 시 사용자가 호출 → 6-step workflow (diff → integrity → harvest → render → enrichment → commit). 절차·invariants·stop-condition 은 SKILL.md 가 SoT.

## 관련 경계

- 상위 문서 루트: `../CLAUDE.md`
- tracked MCP resource source: `sensor_menu_catalog.md`
- ignored local generated refs: `extensions.json`, `extensions-catalog.md`,
  `harvest-progress.json`, `app-specific/`, `testbed-snapshot/`
- 재생성 스크립트 규약: `../../scripts/CLAUDE.md`
