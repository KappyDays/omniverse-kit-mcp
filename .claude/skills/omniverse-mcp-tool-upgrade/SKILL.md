---
name: omniverse-mcp-tool-upgrade
description: Invoke after or during a Claude Code or Codex session that performed omniverse work, to retrospectively analyze that session's work (conversation — MCP tools called, workarounds, repeated friction — plus git diff), identify where MCP tools were missing or insufficient, then add new or upgrade existing MCP tools (7-place edit), verify (registration/drift in-session; behavioral only after host restart + ext reload), and sync tool-only docs. Autonomous with 3 distributed self-reviews (necessity, adversarial-correctness, integration). Input is the session's actual performed work, not an external task spec — it automates the manual harvesting that fills docs/mcp-enhance.md. Not for executing omniverse tasks, broad CLAUDE.md sync (use omniverse-docs-sweep), Kit extension catalog sync (omniverse-kit-extension-catalog-sync), or asset URL/inventory (omniverse-asset-inventory-sync).
user-invocable: true
disable-model-invocation: true
metadata:
  version: "1.0.0"
---

# omniverse-mcp-tool-upgrade: Session-Retrospective MCP Surface Upgrade

Prefix your first line with 🔧 inline.

**목표**: **이번 Claude Code / Codex 세션에서 수행된 omniverse 작업(구현 내용·호출한 MCP tool·우회/수동 단계·반복 마찰)을 상세 분석**해, MCP 표면의 gap 을 식별하고 — **신규 tool 추가 또는 기존 tool 업그레이드**가 필요하면 — 7곳 구현 + 등록/drift 검증 + tool 전용 docs sync 까지 자율 완료한다. **입력은 세션의 실제 작업(conversation + git diff)이지 외부에서 주어진 task 명세가 아니다** — `docs/mcp-enhance.md` 를 수동으로 채우던 회고형 harvest 의 자동화. 절차의 SoT 는 기존 invariant 문서이며 이 skill 은 *가리키기*만 한다 (hard-code 금지).

## When to Use

**세션 작업 회고가 트리거.** User says "이번 세션 omniverse 작업 분석해서 MCP 업그레이드해줘", "방금 작업하면서 불편했던 거 / 우회했던 거 MCP tool 로 만들어줘", "이번 세션에서 부족했던 MCP 기능 보강", "기존 tool 업그레이드 필요" 등. **Skip** for:
- 분석 대상 omniverse 작업의 재실행/시각검증 (이 skill 은 MCP 표면 확장까지만)
- 기존 tool 로 이미 가능한 작업 (Phase 1 에서 발견 시 early-exit)
- 광범위 CLAUDE.md 계층 동기화 → `omniverse-docs-sweep`
- Kit Extension catalog 갱신 → `omniverse-kit-extension-catalog-sync`
- USD asset URL / inventory → `omniverse-asset-inventory-sync`

## Invariants (Never Violate)

| ID | Rule |
|----|------|
| I1 | 절차 hard-code 금지 — 7곳/research/module 절차의 SoT 는 각 invariant 문서. skill 은 가리키기만 |
| I2 | 재구성 작업 중에는 tool 추가 금지 (`docs/invariants/mcp-tool-add.md` §재구성 중 금지) — MCP surface 불변 |
| I3 | 셀프 리뷰 ②/③ 미통과 시 STOP + 보고. green 위장 금지 |
| I4 | import-cache + ext-reload 사실대로 — 같은 세션 live REST 동작 불가. 세션 내 검증은 등록/drift(fresh subprocess)만, 동작 검증은 MCP host 재시작 + ext reload (`docs/invariants/ext-reload.md`) 후 |
| I5 | "있으면 좋겠다" gap 구현 금지 (리뷰 ①) — 직접 경험/예상되는 분 단위 pain 만 |
| I6 | 구현/검증 실패 시 7곳 부분 수정으로 drift-fail 트리 방치 금지 — 해당 gap 은 완결(leave-clean) 또는 revert. 반쪽 상태 종료 금지 |

Breaking any → STOP and report.

## 진입 시 필수 Read (자율 모드 — sub-CLAUDE.md 자동로드 안 함)

- `docs/references/CLAUDE.md` — research flow 0~6단계 (중복확인 → 카탈로그 → hint → API → 예제 → 소스 → 문서)
- `docs/invariants/mcp-tool-add.md` — 새 tool 7곳 동시 수정 + verify_mcp_sync + drift
- `docs/invariants/module-add.md` — 새 module / scenario action
- `docs/invariants/ext-reload.md` — extension `.py` 수정 후 reload (P4 동작 검증 전제)
- `docs/mcp-enhance.md` — 선분석된 gap backlog (E1~E15, S1~S2) — 재사용
- `docs/tool-diagnostic-map.md` — 진단 역색인
- (**live stage 를 동기 편집·순회·render-query 하는 tool 구현 시 — 읽기/traverse 포함**) `docs/invariants/usd-load.md` + `kkr-extensions/docs/usd-load-deadlock-recipe.md` — deadlock-safe baseline: 동기 MDL stage 편집/순회/render-query 는 freeze(deadlock) 유발. 해당 문서의 deadlock-safe 패턴 따를 것

## Workflow

All Python invocations use `.venv/Scripts/python.exe`.

### Phase 1 — 세션 작업 분석 + research (세션당 1회)

1. **세션 작업 분석 (hybrid 입력 — `omniverse-docs-sweep` 와 동일 모델)**:
   - (a) **conversation (primary)**: 이번 세션에 수행한 omniverse 작업 — 호출한 MCP tool, 사용한 **우회/수동 단계**, **반복된 마찰**, "이 tool 있었으면" 순간, 기존 tool 의 한계를 만난 지점. retry·우회·수동 단계는 주로 여기 드러남.
   - (b) **git (corroboration)**: omniverse 관련 코드/extension/scenario 변경. **uncommitted `git diff HEAD` 만 보면 누락** — 이 프로젝트는 세션 중 커밋이 잦으므로 `git log --oneline <세션-base>..HEAD` 로 **세션 중 커밋된 작업까지** 포함 (base 불명 시 conversation 시작 시점 추정). conversation 이 빈약/compacted 면 git 이 주도.
   → 각 마찰점을 **gap 후보**로 추출 (어떤 기존 tool 이 부족했나 / 아예 없었나).
2. gap 후보마다 `docs/tool-catalog.md` 검색 (research step 0). **기존 tool 로 충분히 커버되면** gap 아님 (마찰이 단순 사용법 문제였을 수 있음 → 제거).
3. 남은 gap **잠정 분류** (확정은 step 4 research 후):
   - `(a)` **신규 MCP tool** (Kit command/API wrap) → `docs/invariants/mcp-tool-add.md` 7곳
   - `(b)` **기존 tool 업그레이드** (시그니처 확장·파라미터 추가·반환 보강) → 해당 tool 의 service/client/module/tool 함수 수정 (예: mcp-enhance E5 `viewport_capture` + warmup/stats). frozenset 불변 시 catalog regen 만, 변경 시 7곳 동일
   - `(c)` 새 module / scenario action → `docs/invariants/module-add.md`
   - `(d)` MCP resource → `src/omniverse_kit_mcp/mcp/resources.py` + `tests/unit/test_resources_paths.py`
   - `(e)` MCP 영역 밖 = validation_api 가 in-process 로 도달 불가 (예: host app `.kit` 재빌드 필요) → blocker 보고만. **"어렵다" ≠ "영역 밖"** (carb.input wrap 가능한 OS-input 류는 (a)). 분류 기준 예시 = `docs/mcp-enhance.md` Skip 섹션(영역 밖) vs E#/S# 항목(구현 대상). **(e) 확정은 step 4 research(step 1~4) 후에만 — in-process 경로 미발견을 확인. 미research 채 (e) 분류 금지 (false blocker 방지).**
4. gap 마다 research flow (`docs/references/CLAUDE.md` step 1~6) 실행 → 감쌀 ext/API 확정. `docs/mcp-enhance.md` 에 선분석 항목(E#/S#) 있으면 그 스펙 재사용. research 로 in-process 경로 발견 시 잠정 (e) → (a)/(b) 재분류; 경로 부재 확인 시에만 (e) 확정.
5. 출력: **우선순위 매겨진 gap 리스트** (mcp-enhance 기준 = 이번 세션에서 직접 겪은 분 단위 pain + 우회비용).

> **🔍 셀프 리뷰 ① — 필요성·재사용** (코드 쓰기 *전*. 모자: 사용자/낭비 방지)
> - 이 gap 이 **이번 세션에서 실제로 분 단위 마찰**이었나, 아니면 단순 사용법 문제 / "있으면 좋겠다"인가 (I5)?
> - 기존 tool 조합(`kit_command_execute` / `extension_search` / `window_menu_trigger`)으로 우회 가능했나?
> - `tool-catalog.md` 에 동등 tool 이미 없나 (step 2 재확인)?
> 통과 못한 gap 제거. TodoWrite 에 관점별 pass/fail 기록.

### Phase 2~5 — gap 마다 반복 (우선순위 순)

- **P2 설계**: 이름 / 시그니처 / params / return `@dataclass(slots=True, frozen=True)` / 7곳 매핑(or module-add·resource 경로) / mock 동작 스펙 (→ `mcp-tool-add.md` 7곳 item 5: conftest MockIsaacRestClient).
- **P3 구현**: `docs/invariants/mcp-tool-add.md` 7곳 인라인 실행 (분류 (c)면 `module-add.md`, (d)면 resource 절차). Type boundary: 내부 dataclass, **MCP 서버 Pydantic 금지**. app-specific ext 면 `ISAAC_MCP_APP_PROFILE` 차원 반영 (research step1 `apps`). **7곳에는 EXPECTED frozenset(item 6) + tool group caveat(item 7) 포함 — P4-(i) verify_mcp_sync 의 drift 검사가 frozenset 일치를 요구하므로 P4 前 완료 필수.**

  > **🔍 셀프 리뷰 ② — 적대적 정확성** (구현 직후, 검증 *전*. 모자: 공격자)
  > - 고른 Kit API 실존+시그니처 맞나 — 실소스(`standalone_examples/` · ext source)로 확인했나, 추측인가?
  > - side-effect 는? (예: `CreateConveyorBelt({})` 가 default prim 오염 — mcp-enhance E3)
  > - R1 false-positive 가드: mock 이 항상 성공만 반환하지 않나? mock 충실도는 세션 내 live 확인 불가 → extension REST endpoint 의 **문서화된 계약** 기준으로 판정 (live 확인은 P4-(ii)).
  > - deadlock-safe: 새 동작이 live(MDL) stage 를 동기 편집/순회/render-query 하지 않나? 하면 `docs/invariants/usd-load.md` 의 deadlock-safe baseline 따랐나 (sync write → freeze landmine)?
  > 미통과 시 STOP (I3). TodoWrite pass/fail.

- **P4 검증 — 두 층 분리**:
  - **(i) 등록/drift (세션 내, 필수 게이트)**: `.venv/Scripts/python.exe scripts/verify_mcp_sync.py` — fresh subprocess 로 코드 재import → catalog regen + drift pytest. import-cache 무관하게 green 확인 가능.
  - **(ii) 동작 (세션 밖)**: 실 REST 왕복은 live Isaac + MCP host 재시작 + ext reload 필요. 세션 내 standalone(`scripts/run_process_module_standalone.py` / `scripts/run_scenario_standalone.py`)은 mock 경유 — 실 endpoint 동작 증명 아님. 보고에 명시.
- **P5 docs (tool 전용)**: tool-catalog regen 은 P4-(i) `verify_mcp_sync` 에 포함됨 (그룹 caveat·frozenset 은 P3 의 7곳에서 이미 완료). P5 고유 작업 = 새로 발견한 gap 을 `docs/mcp-enhance.md` 에 append + 변경 파급 매트릭스상 추가 갱신분 확인. 광범위 CLAUDE.md 계층 동기화는 `omniverse-docs-sweep` 핸드오프.

### 종료

모든 gap 의 P2~5 반복이 끝나면, 완료 선언 전에 1회:

> **🔍 셀프 리뷰 ③ — 정합성·완결성** (완료 선언 *전*. 모자: 유지보수자)
> - `mcp-tool-add.md` 7곳 전부? `verify_mcp_sync` green + drift pass? `git status` 생성파일 unchanged?
> - type boundary 위반 없나 (MCP 서버 Pydantic 금지)? 그룹 naming 일관?
> - 재시작/reload 정직성: "live 호출됨" 위장 금지. "등록/drift green + (host 재시작 + ext reload) 후 동작 가능". standalone 이 mock 경유임을 숨기지 않았나 (I4)?
> - clean tree: 실패한 gap 의 부분 수정 잔존 없나 (I6)?
> 미통과 시 STOP (I3). TodoWrite pass/fail.

## Stop Conditions

STOP and report on any:
- Phase 1: 모든 gap 후보가 기존 tool 로 커버됨(단순 사용법 문제 포함) → **early-exit ("업그레이드 불필요")** — error 아님.
- Phase 1: 모든 gap 이 (e) MCP 영역 밖 → 구조적 blocker 목록 보고 — error 아님.
- 셀프 리뷰 ②/③ 미통과 → STOP + 보고 (I3).
- P4 (i) verify_mcp_sync / drift fail → 해당 gap leave-clean 또는 revert (I6), STOP + 보고.
- I1–I6 위반 → STOP.

## Never Do

- ❌ 절차를 skill 안에 hard-code (7곳/research/module 의 SoT 는 invariant 문서)
- ❌ 분석 대상 omniverse 작업의 재실행/시각검증 (범위 밖)
- ❌ "있으면 좋겠다" gap 구현 (리뷰 ①·I5)
- ❌ MCP 서버 코드에 Pydantic (type boundary)
- ❌ 7곳 부분 수정으로 drift-fail 트리 방치 (I6)
- ❌ standalone(mock) 통과를 실 endpoint 동작 검증으로 보고 (I4)
- ❌ 광범위 CLAUDE.md 동기화 (→ docs-sweep), catalog/asset 영역 침범
- ❌ 재구성 작업 중 tool 추가 (I2)

## Sign-off

### Standard (happy path)

```
🔧 omniverse-mcp-tool-upgrade complete

세션 작업 요약: <이번 세션에 수행한 omniverse 작업>
Gaps (세션 마찰에서 도출, 우선순위 순):
- [신규] <tool> (a) — <감쌀 ext/API> ← 마찰: <무엇이 없었나> [mcp-enhance <E#/S#>]
- [업그레이드] <기존 tool> (b) — <보강 내용> ← 마찰: <기존 한계>
- [재사용] <기존 tool> — <마찰이 단순 사용법이었음>
- [blocker(e)] <capability> — <도달 불가 사유>

구현 결과 (gap 별):
- <tool>: 7곳 수정 완료 / 셀프리뷰 ①✓ ②✓ ③✓

검증:
- verify_mcp_sync.py (등록/drift): OK
- tool-catalog.md regen: synced
- ⚠️ 동작(실 REST) 검증: MCP host 재시작 + ext reload 후라야 가능 (세션 내 미수행)

docs:
- 변경 파급 매트릭스 / 그룹 caveat / EXPECTED frozenset 갱신
- mcp-enhance.md append: <새 gap 있으면>

Next:
1. MCP host (Claude Code / Codex CLI) 재시작 → 새 tool live 등록
2. extension reload (`docs/invariants/ext-reload.md`) → 새 REST endpoint live
3. 그 후 새 tool 로 후속 작업 / 광범위 docs 는 /omniverse-docs-sweep
```

### Variant — Early-exit (업그레이드 불필요)

```
🔧 omniverse-mcp-tool-upgrade — 업그레이드 불필요
모든 capability 가 기존 tool 로 커버:
- <capability> → <기존 tool>
원래 작업을 바로 진행 가능.
```

### Variant — Blocker (모두 (e) 영역 밖)

```
🔧 omniverse-mcp-tool-upgrade — 구조적 blocker
MCP in-process 로 도달 불가:
- <capability> — <사유 (예: host app .kit 재빌드 필요)>
권고: <대안 (host app 빌드 수정 / 별도 접근)>
```

### Variant — 검증 fail (P4 (i) stop)

```
🔧 omniverse-mcp-tool-upgrade (검증 fail — 해당 gap revert/leave-clean)
- <tool>: verify_mcp_sync / drift fail — <내용>
- 조치: <revert 또는 부분 완결> (I6 — drift-fail 트리 방치 안 함)
Action 필요: <원인> 해결 후 재호출.
```

## References (background only — do not read inline)

- `.claude/skills/omniverse-docs-sweep/SKILL.md`, `.claude/skills/omniverse-kit-extension-catalog-sync/SKILL.md` — 동형 skill 구조 patterns reference

(SoT 절차 문서는 위 "진입 시 필수 Read" 참조.)

Answer in the same language as the question.
