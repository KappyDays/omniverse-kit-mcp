# 프로젝트 정리 대상 — 사용자 검토용

> 이번 세션에서 확인한 **불필요 / 임시 / 의미 없는** 파일 목록. 삭제 시 영향 분석 포함.
> **삭제 전 사용자 승인 필요**. 항목별 동의/거부 회신 부탁드립니다.

---

## A. 확실히 삭제 권장 (재생성 가능, 중복/의미 없음)

### A1. `isaac_course/cache_usd/` (빈 폴더)
- 상태: 빈 디렉토리
- 이유: 세션 2 에서 폐기 확정된 `file:///` 로컬 캐시 정책. 루트 CLAUDE.md 에 재생성 금지 명시
- 조치: `rmdir isaac_course/cache_usd`
- 영향: 없음

### A2. `isaac_course/scripts/__pycache__/`
- 상태: Python bytecode cache
- 이유: capture_helpers.py 가 다른 스크립트에서 import 되며 생성된 cache. 재생성 가능
- 조치: `rm -r isaac_course/scripts/__pycache__`
- 영향: 없음 (다음 import 시 자동 재생성)

### A3. `isaac_course/captures/test/` (smoke test)
- 상태: Task 3 smoke test 결과 `99_smoke_viewport.png` (6,108 B) + `99_smoke_app.png` (274,038 B)
- 이유: 파이프라인 검증용 1 회성 산출물. PPTX 에서 미사용
- 조치: `rm -r isaac_course/captures/test`
- 영향: 없음. smoke test 재실행 시 `capture_helpers.py __main__` 으로 재생성 가능

### A4. `isaac_course/baselines/{twin1,twin2,twin3}/` (빈 폴더 3개)
- 상태: SSIM baseline 저장소로 예약된 빈 디렉토리
- 이유: 현재 SSIM baseline 미사용. `.gitignore` 에 등재됨
- 조치: 유지 권장 (재사용 가능 구조). 또는 `.gitkeep` 추가해 명시적 유지
- 영향: 없음

---

## B. 사용자 재검토 필요 (용량 크지만 재생성 비용 있음)

### B1. `isaac_course/scripts/node_modules/` (19 packages)
- 상태: npm install 결과 (pptxgenjs + 의존성)
- 이유: `package.json` + `package-lock.json` 으로 재생성 가능. `.gitignore` 에 넣어 git 에서 제외하는 게 표준
- 조치 옵션:
  - (a) `rm -r node_modules` + `.gitignore` 에 `node_modules/` 추가 → 재실행 시 `npm install` 필요
  - (b) 유지 (용량 ~몇 MB)
- 권장: (a) — node_modules 는 보통 commit 대상 아님

### B2. `isaac_course/captures/slide_renders/` (28 PNG)
- 상태: PowerPoint COM 으로 렌더된 28 슬라이드 PNG (총 ~15 MB)
- 이유: `render_slides.py` 재실행으로 재생성 가능. QA 검수 후 pptx 에 반영된 상태라 재사용 이점 없음
- 조치 옵션:
  - (a) 삭제 → 재QA 시 `render_slides.py` 재실행
  - (b) 유지 → 미래 QA 참조
- 권장: (a) — pptx 파일 자체가 SoT

### B3. `isaac_course/scripts/` placeholder 스크립트 6 개
- 상태:
  - `capture_ui_and_browsers.py` (171 lines) — Task 4 실제 실행 사용
  - `capture_categories.py` (289 lines) — placeholder 기반 (폐기 판정)
  - `capture_categories_7_9.py` (181 lines) — placeholder 전용
  - `capture_asset_sampler.py` (107 lines) — 스캐폴드 (실제로는 MCP tool 로 수행)
  - `capture_recipe_elements.py` (180 lines) — 스캐폴드
  - `build_twin1.py` (277 lines) — 스캐폴드
- 이유: 세션 3 실제 PPTX 제작은 Claude Code MCP tool 직접 호출로 수행. 이 스크립트들은 초안 상태에서 사용되지 않음
- 조치 옵션:
  - (a) **전부 삭제** → 재현성은 MCP tool 호출 기록 + render_pptx.js 로 충분
  - (b) **placeholder 만 삭제**: `capture_categories_7_9.py` 삭제, 나머지는 유지
  - (c) 유지 (미래 참조)
- 권장: (b) — `capture_categories_7_9.py` 는 폐기 판정 확정. 나머지는 pattern reference 로 유지 가능

---

## C. 유지 (PPTX 산출물 / 재사용 가능)

### 유지 대상
- `isaac_course/scripts/capture_helpers.py` — dual capture 공통 헬퍼
- `isaac_course/scripts/composite_multi_panel.py` — PIL 합성 (이번 세션 작성)
- `isaac_course/scripts/render_pptx.js` — PPTX 렌더러 (이번 세션 작성)
- `isaac_course/scripts/render_slides.py` — PowerPoint COM 미리보기 (이번 세션 작성)
- `isaac_course/scripts/package.json` + `package-lock.json`
- `isaac_course/slides/Isaac_Sim_Digital_Twin_Tutorial.pptx` (최종 산출물)
- `isaac_course/usd/*.usd` 4 파일 (Twin 1/2/3 + asset_sampler)
- `isaac_course/captures/{ui,browsers,examples,categories,sampler,recipe,twin1,twin2,twin3,save_reuse,comparison}/` — PPTX 참조 이미지 전량
- `isaac_course/pre-test/` — 세션 2 S3 multi-asset load 검증 16/16 성공 기록. 재검증 시 재사용
- `isaac_course/docs/` 4 파일 (asset_inventory · build_log · implementation_issues · user_asset_check · navmesh_viz_research)

### 프로젝트 루트 유지
- `temp-user-claude.md` — 세션 CLAUDE.md 업데이트 후보 (사용자 검토 후 적용)
- `temp-cleanup-review.md` — 이 파일 (검토 후 삭제)
- 기타 CLAUDE.md / .env / scripts/ 등 코어 프로젝트 파일

---

## 정리 실행 방법 (사용자 승인 후)

승인 결과를 받으면 다음 형태로 실행:

```bash
# A 섹션 (확실한 삭제)
rm -r isaac_course/cache_usd
rm -r isaac_course/scripts/__pycache__
rm -r isaac_course/captures/test

# B 섹션 (승인 항목만)
rm -r isaac_course/scripts/node_modules         # B1 승인 시
echo "node_modules/" >> isaac_course/.gitignore  # B1 승인 시
rm -r isaac_course/captures/slide_renders      # B2 승인 시
rm isaac_course/scripts/capture_categories_7_9.py  # B3 승인 시 (b 옵션)
```

---

## 사용자 회신 형식 예

```
A1 ok / A2 ok / A3 ok / A4 keep
B1 (a) / B2 (a) / B3 (b)
```

또는 원하시는 항목만 선택해서 알려주세요.
