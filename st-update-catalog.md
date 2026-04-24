# 세션 인수인계 — Multi-App Extension Catalog Enrichment

> **이 파일 하나만으로 새 세션이 작업을 이어갈 수 있어야 한다. Read 순서와 제약을 엄격히 따를 것.**

---

## 0. 당신의 미션 (한 문장)

Isaac Sim 과 KKR USD Composer 두 Kit 기반 앱의 **전체 Extension 을 catalog 화** 하여 **MCP 개발/발전 시 빠른 reference lookup** 을 가능하게 한다. 스키마·구조·Isaac Sim 쪽 enrichment 는 이미 완료. 남은 **핵심 작업은 USD Composer 358 ext 의 enrichment** 와 부가적인 review 작업.

### 현재 상태 (인수인계 시점)

- **HEAD**: `d5bfbbf` (feat: Phase I + Stage 2 — multi-app catalog)
- **origin/main**: sync 완료
- **Unit tests**: 376 passed
- **`docs/references/extensions.json`**: **658 unique ext** 통합 완료 (v2 schema)
  - Isaac Sim: 624 (516 enriched + 108 bootstrap/skipped)
  - USD Composer: 358 (대부분 bootstrap, **34개가 USD 전용**)
  - Common (both apps): 318
  - api_delta_note detected: 135 건
- **MCP tool 수**: 108 (불변 유지)

---

## 1. 절대 원칙 (위반 감지 시 즉시 revert)

### 원칙 1 — MCP surface 불변
- `tests/unit/test_tools_registration.py` 의 `EXPECTED_*_TOOLS` frozenset 절대 변경 금지
- `docs/tool-catalog.md` diff 는 이번 작업 전체 기간 empty 여야 함
- Extension REST endpoint (`isaac_extension/`) 변경 금지
- **이 규칙을 깨는 Phase 는 Phase E (새 MCP tool 추가) 뿐이며, Phase E 는 반드시 사용자 승인 필요**

### 원칙 2 — 기존 enrichment 보존
- Isaac Sim 의 기존 516 enriched 엔트리는 **변경 금지** (의도적 업데이트가 아니면)
- `enrichment_status: "enriched"` 엔트리는 이미 수동 검수된 것 — 덮어쓰면 원본 손실
- 예외: 명백히 stale/잘못된 내용이면 별도 commit `chore(enrichment-fix): <ext-name> - <이유>` 로 수정

### 원칙 3 — v2 schema 유지
- `apps` map 구조 변경 금지 (isaacsim / usd_composer 양쪽 모두 key 후보)
- field name 변경 금지: `mcp_research_hint` (NOT `mcp_extension_idea`), `api_delta_note`, `public_modules`, `key_symbols` 등
- `schema_version: 2` 고정

### 원칙 4 — 루트 / 하드캡 유지
- 루트 `CLAUDE.md` ≤ 100줄 (현재 95줄)
- sub-`CLAUDE.md` ≤ 150줄
- `docs/invariants/*.md` ≤ 200줄
- `docs/runbooks/*.md` ≤ 300줄

### 원칙 5 — v1 backward compat
- `test_harvest_bootstrap.py` (76 tests) 와 `test_render_catalog.py` (5 tests) 는 v1 API / fixture 를 검증. 계속 pass 해야 함
- `scripts/harvest_extension_metadata.py` 의 `bootstrap()`, `parse_single_extension()`, `make_error_entry()` 제거 금지
- `--mode v1-bootstrap` flag 유지

### 원칙 6 — 매 commit 전 필수 체크
```bash
.venv/Scripts/python.exe -m pytest tests/unit/ -q          # 376 passed 유지
.venv/Scripts/python.exe scripts/verify_mcp_sync.py         # OK
git diff docs/tool-catalog.md                               # empty 여야 함
wc -l CLAUDE.md                                             # ≤ 100
```

어느 하나라도 실패 시 **commit 취소 + 원인 분석**. 자율 revert 금지.

---

## 2. 세션 환경 + 시작 즉시 해야 할 일 (순서 엄수)

### Step 0 — 세션 환경 확인 (첫 응답 전에)

| 항목 | 값 | 이유 |
|---|---|---|
| 모델 | **Opus 4.7 (1M context)** | enrichment 수작업에서 ext 소스 다수 동시 열람 필요 |
| 권한 모드 | **`acceptEdits`** (`Shift+Tab`) | Write/Edit 매번 승인 프롬프트 제거 |
| Effort | `high` (enrichment 반복 작업) · **Phase E 설계 시 `max`** | Phase 별 조정 |

사용자 설정 완료면 pass. 미설정이면 설정 요청.

### Step 1 — baseline 검증

```bash
git status                                                  # clean (untracked dev-mcp.md / mcp-multi.md 제외)
git log --oneline -5                                        # HEAD = d5bfbbf 또는 이후
git rev-parse HEAD                                          # 기록
.venv/Scripts/python.exe -m pytest tests/unit/ -q           # 376 passed
.venv/Scripts/python.exe scripts/verify_mcp_sync.py         # OK
```

어느 하나라도 이상하면 **작업 시작 금지, 즉시 사용자에게 보고**.

### Step 2 — 현재 Phase 자동 판단

아래 bash + Python one-liner 실행 결과로 판단:

```bash
.venv/Scripts/python.exe -c "
import json
d = json.loads(open('docs/references/extensions.json', encoding='utf-8').read())
exts = d['extensions']
from collections import Counter
status = Counter(e['enrichment_status'] for e in exts)

# USD Composer only 중 enriched 비율
usd_only = [e for e in exts if set(e['apps']) == {'usd_composer'}]
usd_enriched = sum(1 for e in usd_only if e['enrichment_status'] == 'enriched')

# Common entries with bootstrap status (they may be USD-side bootstrap even if Isaac-side enriched)
common_boot = sum(1 for e in exts if 'isaacsim' in e['apps'] and 'usd_composer' in e['apps'] and e['enrichment_status'] == 'bootstrap')

api_delta = sum(1 for e in exts if e.get('api_delta_note'))

print(f'enrichment_status: {dict(status)}')
print(f'USD-only enriched: {usd_enriched}/{len(usd_only)}')
print(f'common bootstrap (dual-app but unenriched): {common_boot}')
print(f'api_delta_note: {api_delta}')

print()
print(f'PHASE_A_USD_COMPOSER_ENRICHMENT: ' + ('DONE' if usd_enriched >= len(usd_only)*0.9 else f'TODO ({len(usd_only)-usd_enriched} left)'))
print(f'PHASE_B_API_DELTA_REVIEW:      ' + ('DONE' if api_delta < 20 else f'TODO ({api_delta} to review)'))
"
```

**판단 규칙** (위에서 아래로 — 첫 번째 적용):

| 신호 | 시작할 Phase |
|---|---|
| Phase A 90%+ 완료 + Phase B 20건 미만 + Phase E test 있음 | **없음 — 카탈로그 enrichment 완료, 사용자 추가 지시 요청** |
| Phase A 완료 + Phase B TODO | **Phase B** (api_delta review) |
| Phase A TODO (USD-only enriched 비율 낮음) | **Phase A** (USD Composer enrichment) |

판단 결과를 **§9 작업 시작 선언** 에 기록.

### Step 3 — 필수 문서 Read

**모든 Phase 공통**:
1. `CLAUDE.md` (루트, 95줄) — 메타룰 확인
2. `docs/references/CLAUDE.md` (93줄) — 편집 규칙 + research flow
3. `docs/references/app-specific/usd-composer-unique.md` (118줄) — USD 전용 34개 맥락

**Phase A 시작 시 추가**:
- `scripts/harvest_extension_metadata.py` — `enrich_*` 관련 helper 있는지 확인 (현재는 없음 — 필요 시 추가)
- `docs/references/extensions.json` 에서 bootstrap 엔트리 샘플 5-10개 미리 검토

**Phase B 시작 시 추가**:
- api_delta_note 가 설정된 135개 엔트리 중 대표 10개 샘플 — 실제 API break 인지 version bump 만 인지 판단 기준 학습

### Step 4 — 작업 시작 선언 후 착수

§9 형식으로 보고 → 결정된 Phase 의 첫 작업 자율 실행.

---

## 3. Phase 별 작업 정의 + 자율 권한 범위

### Phase A — USD Composer enrichment (**최우선, 자율 OK**)

**목표**: `enrichment_status: "bootstrap"` 인 USD Composer ext 의 summary·key_symbols·mcp_research_hint 를 채워 `"enriched"` 로 승격.

**범위**:
- USD-only 34 ext + common 엔트리 중 USD-side metadata 가 얕은 것
- 우선순위: USD Composer 고유 category (Procedural Generation / Scene Optimization / Configurator / No-Code UI / Lighting Rigs / USD Schemas extended) 의 ext 먼저

**절차** (ext 1개 당):
1. 해당 ext 소스 Read: `C:/Users/<you>/workspace/branch/kit-app-template/_build/windows-x86_64/release/<source_dir>/<raw_dirname>/`
2. `config/extension.toml` 에서 description / dependencies / keywords 확인
3. Python 모듈 (`public_modules` 의 이름으로 `.../{module}/__init__.py`) 에서 exported class/function 추출 → `key_symbols`
4. `docs/references/testbed-snapshot/03-api-patterns.md` 에서 관련 도메인 섹션 있으면 `testbed_refs` 에 추가
5. `mcp_research_hint` 작성: "MCP 로 wrapping 시 고려할 기능 포인트" — 1-2 문장
6. `summary` 한국어 한 문장 (Isaac Sim enrichment 패턴 참조)
7. `enriched_at` 현재 UTC timestamp, `enrichment_status: "enriched"` 설정

**Commit 전략**: batch 당 50 ext → 1 commit. commit message 포맷:
```
docs(catalog-enrichment): USD Composer batch <N>/<M> — <N ext enriched>

- category breakdown: ...
- key mcp_research_hints added: ...
```

**자율 권한**: 전체 자율 수행 OK. 사용자 승인 불필요.
**매 batch commit 전**: 원칙 6 의 4개 체크 실행.

### Phase B — api_delta_note review (자율 OK)

**목표**: 자동 감지된 135개 중 "실제 API breaking change" 만 남기고 나머지는 null 로 clear.

**판단 기준**:
- 같은 class/function 의 signature 가 양 버전에서 동일하면 → null (Kit 패키지 버전 bump 만)
- 인자 추가/삭제/이름 변경 / return type 변경 있으면 → 간결한 note (예: "Kit 110 에서 `signature` 인자 추가")
- 판단 불가 (ext 이름 변경 불확실) → 그대로 유지 + `[manual-review-pending]` prefix

**도구**: `diff <isaacsim-path> <usd-composer-path>` 또는 주요 파일만 Read 대조.

**Commit 전략**: 전체 135건 처리 후 1 commit `docs(catalog): api_delta_note manual review — <N건 실제 break, M건 false positive clear>`

### Phase C — Isaac Sim enrichment 재점검 (자율 OK)

**목표**: 2026-04-17 이전 enriched 엔트리 중 stale 한 것 찾아 업데이트.

**기준**: `enriched_at < 2026-04-01` AND (`summary` 가 현재 소스와 부합 안 함 OR `key_symbols` 비어있음).

**범위**: 샘플링 (전수 불필요 — 오래된 것 중심).
**Commit**: `chore(catalog): Isaac Sim stale enrichment refresh — <list>`

### Phase D — testbed_refs 필드 채우기 (자율 OK)

**목표**: 주요 ext (특히 enriched) 의 `testbed_refs` 에 `testbed-snapshot/03-api-patterns.md` 관련 섹션 anchor 링크 추가.

**범위**: enriched 된 것 중 testbed 문서와 연결 가능한 것 (~100개 예상).
**Commit**: `docs(catalog): testbed_refs 연결 — <N건>`

### Phase E — extension_search MCP tool (**사용자 승인 필요 — 원칙 1 위반 가능성**)

**목표**: `extensions.json` 을 programmatic 하게 query 하는 MCP tool.

**scope**:
- `extension_search(keyword: str, app: str | None, category: str | None, limit: int = 20) -> list[dict]`
- `docs/invariants/mcp-tool-add.md` 의 7곳 동시 수정 절차 전원 수행

**자율 권한**: **없음**. 착수 전 반드시 사용자에게 설계안 제시 → 승인 대기.

### Phase F — USD Composer MCP bridge (Phase III, demand-driven)

**목표**: `kkr_composer_validation_api` 같은 universal Extension 으로 REST endpoint 제공.

**착수 조건**: 실제 user task 요청 ("USD Composer 에서 X 해줘") 이 들어와서 필요성이 구체화될 때.

**자율 권한**: **없음**. 사용자가 명시 요청 시 진행.

---

## 4. Phase 완료 기준 + 사용자 보고 지점

### Phase A 완료 기준
- USD-only 34 ext 모두 `enrichment_status: "enriched"`
- Common entries 중 USD-side 얕은 것도 enriched (best-effort)
- 원칙 6 의 4개 체크 pass
- 최종 commit 후 사용자 보고

### Phase 별 보고 형식
```
[Phase X 완료 보고]
- 처리한 ext: <N>/<Total>
- 신규 enriched: <N>
- 주요 변경 내용: ...
- 원칙 6 체크: pass
- 다음 Phase 착수 승인 요청 (해당 시)
```

---

## 5. 안전망 / Rollback

### 5.1 Regression 감지 시
- 원인 commit 식별 (`git log --oneline HEAD~5..HEAD`)
- **자율 revert 금지** — 사용자 보고 후 결정
- 허용되는 중간 조치: `git stash` 로 working tree clean 복구

### 5.2 절대 금지
- `git reset --hard` 에 대한 force push (main)
- `--no-verify` 로 pre-commit hook 우회
- `git commit --amend` 로 push 된 commit 수정
- `src/isaacsim_mcp/` 수정 (원칙 1 위반 — Phase E 승인 후에만)
- `tests/unit/` 기존 테스트 수정

### 5.3 세션 중단 시
- commit + push 된 상태로 종료
- 중간 중단 시: `git stash save "wip: Phase <N> 중단"` 후 종료
- 이 파일 § 아래 임시 블록 추가 (다음 세션 재개 지점 기록)

---

## 6. 주요 참조 경로

### 데이터
- **SoT JSON**: `docs/references/extensions.json` (v2, 658 entries) — **수동 편집 OK**
- **Rendered MD**: `docs/references/extensions-catalog.md` (7824줄) — **편집 금지** (파생물)
- **USD 전용 가이드**: `docs/references/app-specific/usd-composer-unique.md`
- **Isaac deprecated 매핑**: `docs/references/app-specific/isaacsim-deprecated.md`
- **Research flow**: `docs/references/CLAUDE.md`

### 소스 경로
- **Isaac Sim**: `C:/Users/<you>/workspace/branch/isaac-sim-standalone-5.1.0-windows-x86_64/<exts|extscache|extsDeprecated>/<ext>/`
- **USD Composer**: `C:/Users/<you>/workspace/branch/kit-app-template/_build/windows-x86_64/release/<exts|extscache|extsbuild>/<ext>/`

### Scripts
- **Harvest v2**: `scripts/harvest_extension_metadata.py` (기본 multi-app mode)
- **Render v2**: `scripts/render_catalog_md.py`
- **MCP sync**: `scripts/verify_mcp_sync.py`

### Progress tracking
- **Harvest progress**: `docs/references/harvest-progress.json` (Phase A 에서 `enrichment` phase 를 재활성 가능)

### 루트 진입
- **Root CLAUDE.md** line 19: `새 MCP tool 기능 research (사전) | docs/references/CLAUDE.md` — Stage 1 에서 추가된 pull-doc 진입점

---

## 7. 기억할 기술 사항

### 7.1 extensions.json 수동 편집 시
- 전체 파일을 한 번에 rewrite 하지 말 것 (900KB+, 느리고 risky)
- JSON 단위 편집: Python one-liner 로 `load → modify → dump` 패턴 사용
- `indent=2, sort_keys=True, ensure_ascii=False` 로 write (기존 포맷 유지)

예시 batch enrichment 패턴:
```python
import json, datetime as dt
path = 'docs/references/extensions.json'
d = json.loads(open(path, encoding='utf-8').read())
for e in d['extensions']:
    if e['name'] == 'omni.genproc.core':
        e['summary'] = '절차적 콘텐츠 생성 core runtime — USD Composer 특화.'
        e['mcp_research_hint'] = '자연어 "지형 생성" 요청 시 1차 후보'
        e['enrichment_status'] = 'enriched'
        e['enriched_at'] = dt.datetime.now(dt.UTC).isoformat()
open(path, 'w', encoding='utf-8').write(
    json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False)
)
```

### 7.2 편집 후 반드시 render 재실행
```bash
.venv/Scripts/python.exe scripts/render_catalog_md.py
```
→ `extensions-catalog.md` 동기화. commit 전 필수.

### 7.3 tests 영향 없음 확인
- `test_harvest_bootstrap.py` / `test_render_catalog.py` 는 v1 fixtures + 실제 CATALOG_JSON 과 무관
- Enrichment 편집은 이들 tests 에 영향 없음 (fixture 기반)

### 7.4 Kit 소스 Read 시 주의
- Isaac Sim `extsDeprecated/` 는 **참조만 가능, MCP 기반 금지** (원칙 1)
- 실제 wrapping 대상은 `exts/` + `extscache/` 의 modern `isaacsim.*` 또는 `omni.*`
- Deprecated 매핑 참조: `docs/references/app-specific/isaacsim-deprecated.md`

---

## 8. Self-check (작업 시작 전 마음속으로 답변)

1. **"USD Composer ext enrichment 중 common entry 에서 Isaac Sim 쪽 enriched `summary` 를 덮어쓰려 하면?"**
   → 덮어쓰지 말 것. `summary` / `key_symbols` 등 agnostic field 는 이미 enriched 면 유지. 필요하면 `api_delta_note` 에 앱 차이 기록.

2. **"bootstrap ext 의 description 이 영어인데 한국어 summary 써야 하나?"**
   → Yes. 기존 Isaac Sim enrichment 패턴 (한국어 1-2 문장) 따름. 원문 description 은 `raw_description` 에 이미 보존됨.

3. **"api_delta_note 판단 불가 시?"**
   → 그대로 유지하되 `[manual-review-pending]` prefix 붙임. 억지 판정 금지.

4. **"enrichment 완료 후 375/376 이면?"**
   → 즉시 stop. 어느 test 가 FAIL 인지 확인. 보통 enrichment 자체는 test 무관이나, 우연히 F1 reference 테스트에서 새 경로가 해석 안 되는 경우 가능.

5. **"새 Python 스크립트 (예: `enrich_usd_composer.py`) 를 `scripts/` 에 추가해도 되나?"**
   → OK. Phase A 지원용 script 는 자율 추가 허용. `scripts/CLAUDE.md` 카탈로그 표에도 한 행 추가.

6 답을 모두 기억하고 있다면 작업 시작 OK.

---

## 9. 작업 시작 선언 (§2 Step 0-3 완료 후 Step 4 직전 보고 양식)

```
[세션 시작 확인]
- git HEAD: <git rev-parse HEAD>
- working tree: <clean / dirty>
- 376 unit tests: <passed / failed>
- MCP sync: <OK / FAIL>
- 루트 CLAUDE.md: <줄수>

[Phase 판단 결과]
- Phase A (USD enrichment): <DONE / TODO — <N left>>
- Phase B (api_delta review): <DONE / TODO — <N건>>
- Phase C (Isaac 재점검): <opt / TODO>
- Phase D (testbed_refs): <opt / TODO>
- Phase E (extension_search tool): <사용자 승인 대기>
- → 시작할 Phase: <X>

[목표 (고정)]
두 앱 Extension catalog enrichment 완성 — USD Composer 358 ext 의 분석/문서화 완료.

[시작할 작업]
Phase <X> — <작업 내용 요약>. 자율 권한 <OK / 승인 필요>.
```

그리고 Step 4 실행 — 해당 Phase 의 첫 batch 부터 자율 수행.

---

## 10. 이 파일의 유지보수

### 정상 진행 중 — 갱신 불필요
§2 Step 2 의 자동 Phase 판단 로직이 `extensions.json` 상태만으로 현재 Phase 결정. 매 세션 동일 파일 주입 가능.

### 비정상 종료 시
§0 바로 아래에 임시 블록 추가:
```markdown
> ⚠️ **최근 중단 기록** — 수동 추가:
> - 시점: <YYYY-MM-DD HH:MM>
> - Phase: <X> / batch <N>
> - 마지막 처리 ext: <name>
> - 재개 시 다음 ext: <name>
> - `git stash list` 에 해당 wip stash 존재
```

### 완료 후 정리
모든 Phase (A, B, 선택 C/D) 완료 + 최종 push 후:
1. `mv st-update-catalog.md archive/st-update-catalog-2026-04-24-completed.md`
2. `git commit -m "chore: st-update-catalog.md archived — enrichment complete"`

---

**끝. 이 파일을 끝까지 읽었다면 §2 Step 0 부터 시작하세요.**

> **매 세션 동일 파일 주입 OK** — §2 Step 2 가 현재 Phase 를 자동 판단. 갱신은 §10 예외 시만.
