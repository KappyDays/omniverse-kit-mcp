<!-- Parent: ../../CLAUDE.md -->
<!-- Scope: 씬 빌드 / asset 선택 (robot·character·environment·prop·simready 추가) 작업 시작 전 필수 숙지 -->
# Asset Discovery — Invariants

씬을 만들거나 robot / character / environment / prop / SimReady asset 을 추가하기
**전에** 이 파일을 Read. NVIDIA·Isaac Sim 5.1 은 풍부한 실 asset (robots 100+,
environments 10, people·animations, props, SimReady 1000+) 을 제공한다 — 기억된 URL
이나 primitive (Cube/Sphere) 로 흐르지 말고 **카탈로그에서 실 asset 을 먼저 찾는다**.

이 문서는 Validation Rule **R1** ("실 asset 만 — primitive 대체 금지") 를 사후
validation 이 아닌 **진입 워크플로** 로 operationalize 한다.

## Discovery 워크플로 (4 단계)

1. **요청 유형 분류** — 무엇을 놓을 것인가? (robot / character / environment / prop /
   simready / 기타). 아래 매핑 표 참조.
2. **URL 획득** — 자연어 니즈 → 구체 USD URL. **`asset_search` 우선** (오프라인, Isaac
   미기동에도 동작). 보조로 카탈로그 markdown 직접 Read, live `asset_list` /
   `content_browse`. 아래 "URL 획득 경로".
3. **로드 안전 조건 확인** — `docs/invariants/usd-load.md` 의 로드 조건 준수 (full HTTPS
   S3 URL, `file://` 금지, play 중 자동 stop-guard, skip/fallback/placeholder 금지).
4. **로드** — `stage_load_usd` (composition) / `stage_open` (scene 교체) / `robot_load` /
   `character_load`. character 는 반드시 `character_load` (raw reference 는 T-pose).

## 요청 유형 → 카탈로그 파일 매핑

카탈로그 SoT 진입점: `docs/assets/isaac/asset_inventory.md` (인덱스). 필요한 카테고리
파일만 Read — 불필요한 토큰 소비 없음.

| 요청 유형 | 읽을 카탈로그 파일 | 로드 tool |
|---|---|---|
| 로봇 (AMR·휴머노이드·4족·암·그리퍼·드론) | `docs/assets/isaac/assets/robots.md` | `robot_load` |
| 환경 / 씬 (창고·사무실·병원·그리드) | `docs/assets/isaac/assets/environments.md` | `stage_open` (교체) / `stage_load_usd` |
| 사람 / 캐릭터 / 애니메이션 | `docs/assets/isaac/assets/people.md` | `character_load` |
| 산업용 prop (팔레트·지게차·선반·KLT) | `docs/assets/isaac/assets/props.md` | `stage_load_usd` |
| 가구 / 박스 / 컨테이너 (SimReady 1000+) | `docs/assets/isaac/assets/simready.md` | `stage_load_usd` |
| RL 학습 / 재질 / 예제 / 센서 USD | `docs/assets/isaac/assets/other.md` | 용도별 |

## URL 획득 경로

세 경로는 보완 관계. **계획 단계 / Isaac 미기동이면 `asset_search` 가 1차.**

1. **`asset_search(query, category=None, limit=20)` — 1차, 오프라인.** 큐레이션 markdown
   카탈로그를 MCP 서버 프로세스에서 직접 read + 랭킹 → `[{name, url, category,
   source_file}]`. 라이브 REST / Isaac 기동 **불필요**. 예: `asset_search("forklift")`,
   `asset_search("warehouse", category="environments")`. ("지게차 찾아줘" 같은 자연어
   질의를 구체 USD URL 로 매핑하는 1급 경로.)
2. **`asset_list(category, subpath)` — 라이브, S3 directory listing.** Isaac 기동 필요.
   카탈로그에 없는 최신 폴더 / 정확한 파일명 실측 확인용. `is_folder=false` 엔트리가
   spawnable url.
3. **`content_browse(url, max_entries)` — 라이브, omni.client list.** SimReady 1000+ 종
   알파벳 순 pagination (`$SIM` 루트). 카탈로그가 prose 요약만 담은 경우 정확 파일명 확인.

> SimReady canonical 규칙: `$SIM/{name}/{name}.usd`. 카탈로그 prefix (`$ISAAC` / `$SIM`)
> 는 카탈로그 파일 상단에 선언 — full HTTPS URL 로 치환해 사용 (`file://` 금지).

## R1 operationalize — 실 asset only

- **primitive 대체 금지**: 요청이 "로봇을 놓아라" 인데 Cube 를 만드는 것은 False Positive.
  카탈로그/`asset_search` 로 실 NVIDIA asset URL 을 확보해 로드한다.
- **기억된 URL 금지**: 하드코드/기억 URL 대신 카탈로그 SoT 또는 `asset_search` 결과 URL 사용
  (404 / 버전 drift 회피). URL 404 / inventory 갱신은 skill
  `/omniverse-asset-inventory-sync`.
- **로드 실패 시 skip/fallback 금지**: `usd-load.md` 금지 사항 — 근본 원인 분석 후 반드시
  성공시킨다.

## 관련 경계

- 카탈로그 SoT 진입점 + 포맷 규약: `docs/assets/isaac/asset_inventory.md` (+ `assets/*.md`)
- 로드 안전 조건 (deadlock 방지 baseline): `docs/invariants/usd-load.md`
- 시각 검증 (capture 후 Read 의무, R3): `docs/invariants/visual-validation.md`
- Character T-pose 방지 / AnimGraph 제약: `src/omniverse_kit_mcp/modules/CLAUDE.md`
- asset_search tool 등록 / caveat: `src/omniverse_kit_mcp/tools/CLAUDE.md` (Asset 그룹)
- URL 404 / inventory 갱신 skill: `.claude/skills/omniverse-asset-inventory-sync/SKILL.md`
