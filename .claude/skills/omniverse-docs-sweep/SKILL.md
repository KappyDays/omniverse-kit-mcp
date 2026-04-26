---
name: omniverse-docs-sweep
description: Invoke during a working session to sync project docs (CLAUDE.md hierarchy + invariants/runbooks/pull-doc 표) with the work just completed. Hybrid input — git diff HEAD + conversation 의 결정 사항. Auto-edits L1 (변경 파급 매트릭스 함께-수정 누락) + L2 (tactical: 카운터·pointer·표 항목·라인캡), reports L3 (영구 규칙·신규 디렉토리·신규 sub-CLAUDE.md·lessons-learned 영구 규칙) candidates as dry-run for user approval. Skip if no diff. Not for: auto-generated docs (tool-catalog.md, phase-*-validation-report.md, references/testbed-snapshot/**), other skills' domains (extensions.json/extensions-catalog.md, isaac_course/docs/assets/*.md/asset_inventory.md).
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# omniverse-docs-sweep: Project Documentation Sweep

Prefix your first line with 🧹 inline.

**목표**: 직전 작업의 `git diff HEAD` + conversation 결정 사항을 분석해 root CLAUDE.md "변경 파급 매트릭스" + sub-CLAUDE.md / `docs/invariants/` / `docs/runbooks/` / 카운터·pointer / 표 항목을 자동 동기화. 영구 규칙·신규 문서 후보는 dry-run 으로 보고만 한다 (silent 자동 추가 금지). 매트릭스를 SoT 로 두고 skill 안에 룰을 hard-code 하지 않는다.

## When to Use

User says "docs sweep", "문서 갱신", "docs 동기화", "CLAUDE.md 정리" 등. **Skip** for:
- 단일 doc 의 typo 수정 (직접 Edit 가 cheaper)
- Kit Extension catalog 갱신 → `omniverse-kit-extension-catalog-sync`
- USD asset URL / inventory → `omniverse-asset-inventory-sync`
- `git diff HEAD` 가 비어 있을 때 (자동 정상 종료 — error 아님)

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | Auto-gen / 불변 history / 외부 sync 편집 금지 — `docs/tool-catalog.md` (auto-gen via `scripts/generate_tool_catalog.py`), `docs/phase-*-validation-report.md` (불변 history), `docs/references/testbed-snapshot/**` (외부 sync via `scripts/sync_testbed_snapshot.py`). drift 발견 시 *해당 sync 스크립트 재실행 제안* 만 한다. |
| I2 | 다른 skill 영역 침범 금지 — `docs/references/extensions.json` / `extensions-catalog.md` (`omniverse-kit-extension-catalog-sync`), `isaac_course/docs/assets/*.md` / `asset_inventory.md` (`omniverse-asset-inventory-sync`). |
| I3 | L3 (영구 규칙·신규 디렉토리·신규 sub-CLAUDE.md·`lessons-learned.md` 영구 규칙·매트릭스 자체 수정·stale 아닌 삭제) 는 dry-run only — user 승인 없이 편집 금지. Sign-off 의 후보 리스트로만 보고. |
| I4 | Pre-stage 검증 게이트 — Step 8 의 `pytest tests/unit/test_doc_integrity.py -q` + `pytest tests/unit/ -q` + `scripts/verify_mcp_sync.py` 가 모두 green 이어야 Step 9 (`git add`) 실행. 하나라도 fail 시 stage 안 함 + working tree 변경은 그대로 (auto-revert 금지). |
| I5 | 매트릭스가 SoT — 변경 파급 룰을 skill 안에 hard-code 금지. root `CLAUDE.md` "변경 파급 매트릭스" 표를 매번 parse. parse fail 시 STOP (skill stale 신호). |
| I6 | DO-NOT-EDIT 보호 영역 절대 편집 금지 — `<!-- DO-NOT-EDIT-START -->` … `<!-- DO-NOT-EDIT-END -->` 블록 내부 모든 라인 + inline `<!-- ⛔ DO-NOT-EDIT ... -->` 마커가 붙은 행 (자동 검증 G1-G7 가드). |

Breaking any → STOP and report.

## Workflow

All Python invocations use `.venv/Scripts/python.exe` (Windows; bypasses `uv run` lock contention with multi-instance MCP servers).

### Step 1 — 입력 수집 (Hybrid: git state + conversation)

**입력 (a) — git state**:

```bash
git diff HEAD --name-status
git diff HEAD
git status --porcelain
```

**입력 (b) — 현재 conversation (마지막 commit 이후)**: agent 의 session conversation history 를 boundary anchor *"마지막 commit 이후"* 까지 거슬러 스캔. 추출 대상은 *session 동안 발생한 결정·인사이트* 로 한정 (모든 발화 X) — "앞으로 항상 X" / "절대 X 금지" / "invariant" / "DO-NOT" 같은 영구화 의도, 새로 발견한 사실, stale 표기, user 가 명시적으로 강조한 결정. boundary 안에 conversation 이 없으면 (a) 만 사용.

**입력 (c) — 옵션 slash 인자**: user 가 호출 시 자유 텍스트로 (b) 를 추가 강조 가능 (예: `/omniverse-docs-sweep "Phase H 완료 + stdin DEVNULL invariant 명시화"`).

- (a) + (b) 둘 다 비어 있음 → 정상 종료 ("nothing to sweep" sign-off variant).
- 비어있지 않음 → 변경 파일 목록 + 라인 단위 diff + (b) 추출 결과 보존, 계속.

### Step 2 — L1 매핑 (변경 파급 매트릭스)

root `CLAUDE.md` 의 "변경 파급 매트릭스" 표를 Read + parse. 각 행은 `| 변경 대상 | 함께 수정 |` 형식. Step 1 의 변경 파일을 매트릭스 행과 매칭해 *함께 갱신해야 할 후보 docs* 추출.

매트릭스 표를 찾을 수 없거나 형식 변형이 의심되면 **STOP** (I5 — skill stale 신호). skill 내부에 룰을 절대 hard-code 하지 말 것.

Output: `{변경된 파일: [함께 갱신해야 할 파일들]}` 매핑.

### Step 3 — L2 tactical 후보 도출

- **(3a) 카운터**:
  - tool 수: `grep -c '@mcp.tool()' src/isaacsim_mcp/tools/*.py` 합산 → root `CLAUDE.md` / `docs/tools-roadmap.md` Implementation Status 섹션의 수치 확인
  - test 수: `pytest --collect-only -q` 마지막 줄
  - 라인 수: `wc -l` 로 각 CLAUDE.md / invariants / runbooks
- **(3b) Pointer**: 모든 sub-CLAUDE.md / invariants / runbooks 의 cross-ref (`docs/...`, `../...`) 추출 → 파일 존재 검증. 깨진 pointer 중 *단순 rename / path drift* 만 후보 (의미 변형 동반은 L3).
- **(3c) 표 항목 누락**: sub-CLAUDE.md "파일 구조" 표 / root CLAUDE.md "문서 맵" 표 / pull-doc 표 에 Step 1 의 신규 파일이 누락됐는지 검증.

각 후보를 `{file, before, after, 사유}` 로 기록.

### Step 4 — L3 후보 식별

Step 1 (b) 의 conversation 추출 결과 + git commit msg + git status 신호를 종합 (적용 안 함, 후보만):
- 영구화 의도 키워드 (Step 1 (b) 에서 추출 + commit msg 에서 동일 검색): "앞으로 항상", "절대 X 금지", "이 룰은", "invariant", "DO-NOT", "stale", "deprecated"
- 신규 디렉토리 untracked (`git status --porcelain | grep '^?? .*/$'`)
- 신규 sub-CLAUDE.md untracked
- `lessons-learned.md` 에 영구 규칙 추가 시도 검출 (메타 룰 위반 — incident log only)
- root CLAUDE.md 메타 룰 `삭제는 stale 한정` 위반 가능성 검출
- root CLAUDE.md "변경 파급 매트릭스" 자체 수정 후보

후보를 Sign-off 의 "L3 candidates" 섹션으로 보존.

### Step 5 — Self-review A (자동 게이트)

각 L1+L2 후보를 *in-memory* 적용한 결과로:
- **라인캡**: 루트 `CLAUDE.md` ≤100 / sub-CLAUDE.md ≤150 / `docs/invariants/*.md` ≤200 / `docs/runbooks/*.md` ≤300 — 하나라도 초과 시 후보 폐기
- **매트릭스 잔여**: L1 매핑이 요구한 "함께 갱신해야 할 파일" 이 후보에 모두 포함되어 있는지
- **Broken pointer**: 후보 적용 후 *새로* 깨지는 cross-ref 가 없는지
- **DO-NOT-EDIT 침범**: 후보의 편집 라인 범위가 `<!-- DO-NOT-EDIT-START -->` … `<!-- DO-NOT-EDIT-END -->` 블록 내부 또는 inline `<!-- ⛔ DO-NOT-EDIT ... -->` 마커 행과 겹치는지 — 겹치면 폐기 (I6)

폐기된 후보를 Sign-off "Discarded — Self-review A" 섹션에 사유와 함께 기록.

### Step 6 — Self-review B (LLM)

Step 5 통과 후보를 다시 읽으며:
- **중복**: 이미 같은 의미의 항목이 있는가?
- **메타 룰 위반**:
  - `lessons-learned.md` 에 영구 규칙 추가? (root CLAUDE.md 메타 — incident log only)
  - sub-CLAUDE.md 에 cross-cutting 룰 추가? (sub 는 디렉토리 고유 룰만)
  - stale 한정이 아닌 삭제?
- **톤 일치**: 기존 행과 같은 markdown 패턴인가? 한국어/영어 톤 일치?

폐기된 후보를 Sign-off "Discarded — Self-review B" 섹션에 사유와 함께 기록.

### Step 7 — L1+L2 적용

각 통과 후보를 `Edit` 도구로 실제 편집. 한 파일에 여러 후보가 있으면 변경을 합쳐 가능한 1 Edit 호출로 처리. **L3 후보는 적용하지 않음** — Sign-off 보고만.

### Step 8 — 사후 검증

```bash
.venv/Scripts/python.exe -m pytest tests/unit/test_doc_integrity.py -q
.venv/Scripts/python.exe -m pytest tests/unit/ -q
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
```

모두 green → Step 9 진행. 하나라도 fail → Step 9 skip + Sign-off "Verification fail" variant. **변경은 working tree 에 그대로 — auto-revert 안 함** (user 의 in-progress 작업 충돌 위험).

### Step 9 — Auto-stage + Sign-off

```bash
git add <변경된 파일들>
```

`git commit` / `git push` 절대 호출하지 말 것 (Auto-stage only — user 가 의미 단위로 commit). 그리고 아래 Sign-off 출력.

## Stop Conditions

STOP and report on any:
- Step 1: `git diff HEAD` + `git status` 둘 다 비어 있음 → 정상 종료 ("nothing to sweep") — error 가 아님
- Step 2: 매트릭스 parse fail → STOP (root CLAUDE.md schema 변형 의심, skill 코드 수정 필요 가능성)
- Step 5: 모든 L1+L2 후보가 라인캡 / DO-NOT-EDIT 침범 / 매트릭스 잔여로 폐기 → STOP + 보고 (사람 판단 필요 — 이관 / 분할 / 압축)
- Step 6: 모든 후보가 메타 룰 위반으로 폐기 → STOP + 보고
- Step 8: 사후 검증 fail → Step 9 skip + 보고
- I1–I6 위반 → STOP

## Never Do

- ❌ Auto-generated (`docs/tool-catalog.md`) / 불변 history (`docs/phase-*-validation-report.md`) / testbed-snapshot 편집
- ❌ 다른 skill 영역 (`docs/references/extensions.json` / `extensions-catalog.md`, `isaac_course/docs/assets/*.md` / `asset_inventory.md`) 편집
- ❌ L3 후보 silent 자동 적용 — 항상 dry-run report 로만
- ❌ Step 8 fail 시 `git add` (stage 안 함)
- ❌ Step 8 fail 후 변경 auto-revert (user 의 in-progress 작업 손상 위험)
- ❌ `git commit` / `git push` (Auto-stage only)
- ❌ root `CLAUDE.md` "변경 파급 매트릭스" 자체 자동 수정 (매트릭스 자체 변경은 L3)
- ❌ `lessons-learned.md` 영구 규칙 추가 (incident log only)
- ❌ stale 한정이 아닌 삭제
- ❌ DO-NOT-EDIT 보호 블록 내부 / inline `⛔ DO-NOT-EDIT` 마커 행 편집 (G1-G7 가드)

## Sign-off

### Standard (happy path)

```
🧹 omniverse-docs-sweep complete

L1+L2 applied (auto-edit, staged):
- <file>: <change 요약>
- ...

L3 candidates (dry-run, 미적용 — user 승인 시 다음 호출에서 처리):
- [1] <후보 종류>: <대상 위치>
       근거: <commit msg / conversation 키워드 / git status 신호>
- ...

Discarded (시뮬레이션 폐기 — debugging 투명성):
- <file>: <폐기 사유 — 라인캡 / 매트릭스 잔여 / DO-NOT-EDIT 침범 / 메타 룰 / 중복> [Self-review A|B]
- ...

Verification (Step 8):
- pytest tests/unit/test_doc_integrity.py: <N> passed
- pytest tests/unit/: <N> passed
- scripts/verify_mcp_sync.py: OK
- Cap: root <X>/100, sub max <X>/150, invariants max <X>/200, runbooks max <X>/300

Staged (commit/push pending — user 결정):
- M <file>
- ...

Next: user 가 의미 단위로 git commit. L3 후보 처리는 "L3 1번 적용" / "L3 무시" 로 지시.
```

### Variant — No-op (Step 1 stop)

```
🧹 omniverse-docs-sweep complete — nothing to sweep
git diff HEAD: empty
```

### Variant — 사후 검증 fail (Step 8 stop)

```
🧹 omniverse-docs-sweep complete (사후 검증 fail — stage 하지 않음)

L1+L2 applied:
- ... (변경은 working tree 에 그대로 — auto-revert 안 함)

Verification fail:
- <pytest / verify_mcp_sync 중 fail 한 항목> (<실측 vs 캡 / drift 내용>)

Action 필요: <원인 요약> — user 가 처리 (이관 / 압축 / 분할 / drift 정정) 후 다시 호출.
```

## References (background only — do not read inline)

- root `CLAUDE.md` — "변경 파급 매트릭스" (SoT) + 메타 룰 (라인 하드캡, 이관/삭제 룰, lessons-learned incident log) + DO-NOT-EDIT 보호 G1-G7
- `docs/CLAUDE.md` — docs 디렉토리 각 파일의 역할 + 업데이트 규칙
- `tests/unit/test_doc_integrity.py` — 라인캡 / cross-ref / G1-G7 가드
- `scripts/verify_mcp_sync.py` — MCP catalog drift 가드
- `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md` — 동형 patterns reference
- `.claude/skills/omniverse-asset-inventory-sync/SKILL.md` — 동형 patterns reference

Answer in the same language as the question.
