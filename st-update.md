# 세션 인수인계 — CLAUDE.md Pull-First Restructure

> **이 파일 하나만으로 새 세션이 작업을 이어갈 수 있어야 한다. Read 순서와 제약을 엄격히 따를 것.**

---

## 0. 당신의 미션 (한 문장)

Isaac-sim-MCP 프로젝트의 CLAUDE.md 파일 체계를 **Pull-First Architecture** 로 재구성하여 Claude Code 의 토큰 사용량을 대폭 줄이되, **기존 기능과 서브 폴더 간 상호 관계성을 단 하나도 깨뜨리지 않아야 한다**.

**핵심 수치 목표**:
- 루트 `CLAUDE.md`: 현재 282줄 → **≤ 100줄 하드캡**
- 매 턴 고정비: ~7k → **~2.4k 토큰** (−4.6k/턴)
- 세션 시작 비용: **−19k 토큰** (공통 트리오 해제)
- 50턴 대화 누적: 350k → 120k

---

## 1. 절대 원칙 (위반 금지 — 감지되면 즉시 revert)

### 원칙 1 — Isaac-sim-MCP 기능 불변
- **코드 파일 touch 금지**: `src/**`, `isaac_extension/**`, `scripts/**` 중 기존 파일은 본 재구성과 직접 관련 없으면 수정 금지
- **예외**: Phase 1 에서 아래 신규 파일만 추가 허용
  - `tests/unit/test_doc_integrity.py`
  - `tests/unit/test_doc_references.py`
  - `tests/unit/test_do_not_edit_guards.py`
  - `tests/integration/test_mcp_live_smoke.py`
  - `tests/integration/test_env_sub_config.py`
  - `scripts/compare_test_reports.py`
  - `scripts/compare_pointer_maps.py`
  - `scripts/extract_pointer_map.py`
  - `scripts/run_restructure_tests.sh`
- **기존 test 수정 절대 금지**
- **검증 (매 commit 전)**: `.venv/Scripts/python.exe -m pytest tests/unit/ -q` 가 `357 passed` 유지

### 원칙 2 — 상호 관계성 보존
- 루트 ↔ sub ↔ 자매 CLAUDE.md 간 포인터 네트워크가 단 하나도 깨지면 안 됨
- 파일 이동 시 **양방향 참조 동시 갱신**
- Phase 1 에서 `pointer_map.json` baseline 추출 → Phase 5 에서 비교 → 끊긴 포인터 = 0 필수
- `docs/invariants/` 또는 `docs/runbooks/` 신규 생성 시 루트 CLAUDE.md 문서 맵 즉시 갱신

### 원칙 3 — MCP surface 불변
- MCP tool 이름 frozenset 변경 금지 (`tests/unit/test_tools_registration.py` 의 `EXPECTED_*_TOOLS` 불변)
- `docs/tool-catalog.md` 는 auto-gen 파일 — 재구성 과정에서 diff 가 생기면 code touch 한 것 (회귀) → 즉시 원인 파악
- Extension REST endpoint / rest_router 변경 금지
- 매 commit 은 pre-commit hook (`scripts/verify_mcp_sync.py`) 가 PASS 해야 함 (자동 실행)

---

## 2. 세션 시작 즉시 해야 할 일 (순서 엄수)

### Step 1 — 현재 상태 확인
```bash
git status                                                # working tree clean 확인
git log --oneline -5                                      # HEAD = 9169295 (또는 이후 commit)
git branch -vv                                            # main branch, origin sync
wc -l CLAUDE.md                                           # 282 (baseline) 확인
.venv/Scripts/python.exe -m pytest tests/unit/ -q        # 357 passed
.venv/Scripts/python.exe scripts/verify_mcp_sync.py       # MCP surface OK
```
- 어느 하나라도 이상하면 **작업 시작 금지, 즉시 사용자에게 보고**

### Step 2 — 필수 문서 Read (이 순서대로)
1. `docs/superpowers/plans/2026-04-24-claude-md-restructure-plan.md` — **메인 설계서 (1146줄, 필수 전체 Read)**
   - §0 Status, §1 Background, §2 Architecture, §2.4 Operating Invariants
   - §3 DO-NOT-EDIT 처리 원칙
   - §4 파일 변경 맵
   - §5-§9 Phase 1-5 Task 상세
   - §10 테스트 설계
   - §11 실행 순서 + Gate
   - §12 Acceptance Criteria (15개)
   - §13 Risk Management
2. `CLAUDE.md` — 현재 루트 (282줄, DO-NOT-EDIT 보호 영역 포함)
3. `isaac_extension/docs/lessons-learned.md` — L13-L17 의 근거 (축약 시 보존 필수 항목 확인)
4. `src/isaacsim_mcp/modules/CLAUDE.md` — 258줄, Phase 3 Task 3.1 분리 대상

### Step 3 — Phase 1 Task 1.1 착수
- 대상: `tests/unit/test_doc_integrity.py` 작성
- 설계서 §5 Task 1.1 Step 1-7 을 그대로 따라감
- 작성 → pytest PASS 확인 → commit

---

## 3. 프로젝트 핵심 맥락 (새 세션이 반드시 알아야 할 것)

### 3.1 현재 git 상태 (2026-04-24 베이스라인)
- **브랜치**: `main`
- **HEAD**: `9169295` (plan 문서 commit + push 완료)
- **origin/main 과 sync**
- **이 세션에서 새로 추가될 commit 들은 HEAD 뒤에 쌓임**

### 3.2 파일 크기 baseline (재구성 전)
| 파일 | 줄 수 | 비고 |
|---|---|---|
| `CLAUDE.md` (root) | 282 | 매 턴 auto-load, 목표 ≤100 |
| `docs/tool-catalog.md` | 1785 | auto-gen, touch 금지 |
| `docs/phase-progress.md` | 210 | 공통 트리오 해제 대상 |
| `src/isaacsim_mcp/modules/CLAUDE.md` | 258 | Phase 3 에서 분리 |
| `scenarios/CLAUDE.md` | 176 | 중복 제거 대상 |
| 나머지 sub CLAUDE.md × 11 | 합 663 | 각 ≤150줄 유지 |

### 3.3 Claude Code CLAUDE.md 로드 동작 (실측)
- 루트 `CLAUDE.md`: 세션 시작 **auto-load** (system prompt)
- sub-`CLAUDE.md`: 파일 접근 시 **ancestor chain 전체** lazy-load
  - 예: `isaac_extension/.../agent_manager.py` 접근 → 루트 + `isaac_extension/CLAUDE.md`
- **"공통 트리오" 는 CC 가 자동 로드하지 않음** — 루트 CLAUDE.md 의 **지시문** 이 agent 에게 읽도록 명령하는 self-imposed 비용 → 해제 시 즉시 19k 토큰/세션 절감

### 3.4 최근 디버깅 결과 (Phase 0 에서 이미 완료, 보존 대상)
루트 CLAUDE.md 에 추가된 내용 — 재구성 시 반드시 보존:

| 이슈 | 내용 | 축약 시 필수 보존 |
|---|---|---|
| **L17** (2026-04-24) | `subprocess.Popen(stdin=DEVNULL)` 누락 = MCP 자식 kit.exe cold boot hang | "stdin=subprocess.DEVNULL", "process_module.py::start", 240/13 수치, "extra_ext_ids race 무효" |
| **L14** | pydantic-settings v2 sub-config env_file 전파 안 됨 | 모든 sub-BaseSettings 에 `env_file=".env"` 필수 |
| **L9/L16** | omni.ext fswatcher sys.modules cleanup 안 함 + ui.Window zombie | Kit restart 유일 신뢰, on_shutdown cleanup 패턴 |
| **L15** | ext_ui_invoke float div = panel layout race | `window_ui_show(settle=10)` → `ext_ui_invoke` sequence |
| **L13** | MCP 직접 호출 ≠ UI 버튼 검증 | controller 코드 경로는 UI click 으로만 검증 가능 |

### 3.5 DO-NOT-EDIT 보호 영역 (현재 2개)
1. 루트 CLAUDE.md §"kit.exe cold boot hang — stdin pipe deadlock"
2. `ISAAC_SIM_EXTRA_EXT_IDS` 표 행 inline 마커

**사용자 승인된 처리**: 축약 허용, 단 원문 목적/의도 보존. 상세 본문은 `docs/runbooks/kit-stdin-deadlock.md` 로 이관 + DO-NOT-EDIT 마커 유지. 루트에는 residual 4-5줄만 잔존. `test_do_not_edit_guards.py` (G1-G7) 로 자동 검증.

---

## 4. Phase 별 작업 및 사용자 보고 지점

### Phase 1 — Pre-flight (약 3시간)
- Task 1.1 (정적 테스트 A/F/G + pointer map 추출) → 1시간
- Task 1.2 (live smoke + env 테스트 infra) → 1시간
- Task 1.3 (baseline 캡처) → 30-40분 (Isaac Sim live)
- **사용자 보고**: baseline JSON 결과 요약 (PASS/FAIL 분포)

### Phase 2 — 공통 트리오 해제 + 루트 재작성 (약 4시간)
- Task 2.1 (공통 트리오 지시 제거) → 15분
- Task 2.2 (docs/invariants/ 7개 생성) → 2시간
- Task 2.3 (docs/runbooks/ 4개 생성, DO-NOT-EDIT 이관) → 1시간
- Task 2.4 (루트 CLAUDE.md rewrite ≤100줄) → 45분
- **사용자 보고**: 루트 최종 상태 (줄 수, 주요 섹션)

### Phase 3 — sub-CLAUDE.md 정리 (약 2시간)
- Task 3.1 (modules/CLAUDE.md 분리 → integration-facts.md + process-ops.md) → 1시간
- Task 3.2 (기타 sub 중복 제거) → 45분
- Task 3.3 (lessons-learned 헤더 격하) → 10분
- Task 3.4 (메타룰 강화) → 15분
- **사용자 보고**: sub CLAUDE.md 이전/이후 줄 수 매트릭스

### Phase 4 — Cross-reference 정합성 (약 30분)
- 모든 pointer 유효성 확인
- `docs/CLAUDE.md` 갱신

### Phase 5 — Post-flight (약 1시간)
- Task 5.1 (Isaac Sim 기동) → 5-30분 (cold boot)
- Task 5.2 (전체 테스트 실행) → 25분
- Task 5.3 (4계층 비교: 기능 불변 / 포인터 맵 / live regression / 재구성 목표) → 10분
- **사용자 보고**: regression 비교 결과 — AC #1-#15 전부 PASS 시만 최종 push

### 각 Phase 완료 시 공통 수행 사항
1. **매 Task 완료 시 commit** (설계서의 각 Task 의 "Commit" Step 따름)
2. **Phase 완료 시 push** (중간 롤백 안전망)
3. **사용자 보고 메시지 형식**:
   ```
   [Phase X 완료]
   - 수행 Task: ...
   - Acceptance 체크: AC #N PASS / FAIL
   - 다음 Phase 시작 승인 요청
   ```

---

## 5. 안전망 / Rollback (자율 판단 금지 영역)

### 5.1 매 commit 전 필수 체크
```bash
# 기능 불변
.venv/Scripts/python.exe -m pytest tests/unit/ -q
# MCP surface 불변 (자동으로 pre-commit hook 실행되지만 수동 확인도 OK)
.venv/Scripts/python.exe scripts/verify_mcp_sync.py
# tool-catalog diff empty
git diff docs/tool-catalog.md
```
어느 하나라도 실패 시 **commit 취소** + 원인 분석.

### 5.2 Regression 감지 시
1. 원인 commit 식별 (`git log --oneline HEAD~5..HEAD`)
2. **자율 revert 금지** — 사용자 보고 후 결정
3. 허용되는 중간 조치: uncommitted 변경을 `git stash` 로 옮겨 working tree clean 복구

### 5.3 절대 금지
- `git reset --hard` 에 대한 force push (main)
- `--no-verify` 로 pre-commit hook 우회
- `git commit --amend` 로 push 된 commit 수정
- 코드 파일 수정 (원칙 1 위반)

### 5.4 세션 중단 시
- 모든 중간 변경은 commit + push 된 상태로 종료
- Task 중간 중단 시: `git stash save "wip: Phase X Task Y 중단"` 후 종료
- 이 `st-update.md` 를 **현재 진행 상황 반영해서 갱신**하고 commit (다음 세션이 정확히 이어가도록)

---

## 6. 주요 참조 경로 (자주 쓰는 것)

### 문서
- 메인 설계서: `docs/superpowers/plans/2026-04-24-claude-md-restructure-plan.md`
- 이전 설계서 (superseded): `docs/superpowers/plans/2026-04-23-claude-md-restructure.md`
- Phase 히스토리: `docs/phase-{a..h}-validation-report.md`
- Asset SoT (S3 URL): `isaac_course/docs/asset_inventory.md` + `isaac_course/docs/assets/*.md`
- Lessons learned: `isaac_extension/docs/lessons-learned.md`

### 코드
- MCP tool 등록 SoT: `tests/unit/test_tools_registration.py` (EXPECTED_* frozenset)
- Process module: `src/isaacsim_mcp/modules/process_module.py`
- Config: `src/isaacsim_mcp/config.py`

### Baseline 산출물 (Phase 1 에서 생성)
- `docs/artifacts/restructure-baseline/pre/test_report.json` — 정적 + live 결과
- `docs/artifacts/restructure-baseline/pre/pointer_map.json` — 포인터 그래프
- `docs/artifacts/restructure-baseline/pre/unit_tests.json` — 357 tests baseline
- `docs/artifacts/restructure-baseline/pre/baseline_sha.txt` — git sha

### Scripts
- MCP sync 검증: `scripts/verify_mcp_sync.py`
- Tool catalog regen: `scripts/generate_tool_catalog.py`
- Standalone test: `scripts/run_process_module_standalone.py`

---

## 7. 기억할 Kit 관련 기술 사항

### stdin=DEVNULL 필수 (L17)
- `src/isaacsim_mcp/modules/process_module.py::start()` 의 `subprocess.Popen(...)` 에 `stdin=subprocess.DEVNULL` 명시 — **이미 적용됨** (commit `9f79c98`)
- 재구성 중 이 라인이 사라지면 AC #10 실패 → 즉시 revert

### startup_timeout=120 (default)
- `.env` 에 `ISAAC_SIM_STARTUP_TIMEOUT=600` 설정 시만 cold boot 완주
- Phase 1 Task 1.3 의 baseline 캡처 시 `isaac_sim_start(startup_timeout=600)` 호출

### Isaac Sim 기동 전 확인
- PowerShell `Get-Process -Name kit -ErrorAction SilentlyContinue` — row 없으면 죽음 / row 있으면 alive
- `tasklist //FI` (git bash) **사용 금지** (L7, I3 — false negative 발생)

### Validation Rules (R1-R3, 모든 scenario 저작/테스트에 적용)
- **R1**: primitive (Cube/Sphere) 대체 검증 무효 → 실제 S3 asset 만
- **R1a**: NavMesh bake 는 `simulation.stop` 후에만 유효
- **R2**: Robot 동작은 `simulation.play` 필수
- **R3**: Viewport 캡처 후 `Read` 로 PNG 시각 검증

---

## 8. 확인: 이 파일을 읽은 당신이 대답해야 할 self-check

작업 시작 전 마음속으로 답변:

1. **"이 재구성으로 기존 357 unit tests 중 하나라도 fail 하면 어떻게 하나?"**
   → 즉시 stop, 원인 commit 식별, 사용자 보고, 자율 revert 금지.

2. **"루트 CLAUDE.md 를 90줄로 줄였는데 sub-CLAUDE.md 가 참조하던 §섹션이 사라졌다. 어떻게 처리?"**
   → sub 의 참조를 새 위치 (`docs/invariants/xxx.md` 또는 `docs/runbooks/xxx.md`) 로 동시 갱신. pointer_map.json 비교로 검증.

3. **"DO-NOT-EDIT 섹션을 runbook 으로 이관 중이다. 루트에 아무것도 안 남겨도 되나?"**
   → 안 됨. 축약 residual (⚠️ 디렉티브 1줄 + fix SoT 1줄 + 검증 수치 + 파일 포인터, 총 4-5줄) 필수 보존. G1-G7 테스트가 이를 감시.

4. **"Phase 2 작업 중 `src/isaacsim_mcp/modules/process_module.py` 의 버그를 발견했다. 고쳐도 되나?"**
   → 안 됨. 원칙 1 위반. 사용자 보고 → 재구성 완료 후 별도 commit 으로 처리.

5. **"Isaac Sim live smoke 에서 D14 가 fail 했다. 다른 테스트는 모두 PASS."**
   → D14 pre baseline 이 PASS 였다면 regression → stop + 사용자 보고. pre 에서 이미 FAIL (known-FAIL) 이었다면 post 에서도 FAIL 허용.

5개 답을 모두 기억하고 있다면 작업 시작 OK.

---

## 9. 작업 시작 선언 (실행 시점에 사용자에게 보고)

```
[세션 시작 확인]
- git HEAD: <sha>
- working tree: clean
- 357 unit tests: passed
- MCP sync: OK
- 루트 CLAUDE.md: 282 lines (baseline 일치)

[목표]
CLAUDE.md Pull-First Restructure — 루트 282→≤100줄, 세션 당 −19k 토큰.
Operating Invariants (기능 불변, 관계성 보존, MCP surface 불변) 엄수.

[시작할 작업]
Phase 1 Task 1.1 — tests/unit/test_doc_integrity.py 작성.
설계서 §5 Task 1.1 의 Step 1-7 을 따릅니다.
```

그리고 바로 Task 1.1 착수.

---

## 10. 이 파일의 유지보수

**각 Phase 완료 시** 이 `st-update.md` 를 갱신:
- "현재 Phase" / "다음 시작 Task" 명시
- "Phase 완료 시점의 git sha" 업데이트
- "baseline 대비 현재 상태 요약" 추가

갱신 commit 형식: `chore(st-update): Phase X 완료, 다음 Y Task 시작 지점 기록`

**재구성 완료 (Phase 5 acceptance 전원 PASS) 후**: 이 파일을 삭제하거나 `archive/` 로 이동 — 더 이상 필요 없음.

---

**끝. 이 파일을 끝까지 읽었다면 §2 Step 1 부터 시작하세요.**
