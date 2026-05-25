# GOAL — Office–DataCenter Network Demo

> **사용법**: 새 세션에서 아래 "프롬프트" 블록 전체를 복사해 `/goal` 에 붙여넣으세요.
> 전제: Isaac Sim 5.1.0 (Windows 11), omniverse-kit-mcp MCP 서버 연결됨.

---

## 프롬프트 (복사해서 `/goal` 에 사용)

```
omniverse-kit-mcp 프로젝트에서 Isaac Sim 5.1 용 "Office–DataCenter Network Demo" 를 구현한다.
설계는 이미 확정되어 office_mcp/SPEC.md 에 있다. 모든 산출물은 office_mcp/ 폴더 안에 저장한다.

[경로 앵커] 이 프롬프트와 SPEC 의 모든 경로는 repo root 기준이다. 현재 작업 디렉토리가
repo root 가 아니면(예: workspaces/isaac/instance-2 에서 실행 시 root 는 ../../../),
먼저 repo root 를 확정한 뒤 아래 모든 경로를 그 기준으로 해소하라.

## 먼저 읽을 것 (작업 전 필독)
1. office_mcp/SPEC.md  ← 전체 설계 (확정). 이 문서가 source of truth.
2. docs/invariants/usd-load.md  ← USD 로드 4조건
3. kkr-extensions/docs/usd-load-deadlock-recipe.md  ← office.usd(MDL-heavy) 로드 deadlock 방어 (복사용)
4. kkr-extensions/CLAUDE.md  ← 독립 Extension 정책 + 공통 규칙
5. docs/invariants/visual-validation.md  ← viewport_capture/R3 검증 절차
6. docs/invariants/ext-reload.md  ← Extension .py 수정/reload
7. 참고 패턴: kkr-extensions/omni.mycompany.usd_mouse_interact (raycast 클릭),
   omni.mycompany.robot_lidar / stage_annotator (self-test stamp, customData 영속)

## 무엇을 만드나 (SPEC §1 요약)
- Scene 파일 office_mcp/scenes/office_datacenter.usd: 물리 포함 사무실 + 인접 데이터센터.
  PC(전원 버튼 Prim) ── 케이블 ── 벽 관통 ── 스위치 ── 서버 3대.
- Kit Extension omni.office_mcp.network_demo: Load Scene 버튼 + 상태 Label.
  play 중 PC 전원 버튼을 뷰포트에서 클릭 → 케이블이 net:order 순서로 emissive 진행파,
  각 서버 LED 순차 점등. 전송 시각화는 "케이블 진행파 + 서버 LED" 만 (packet 구체 없음).

## 반드시 지킬 제약 (SPEC §3)
- 독립 구조: Kit SDK 직접 호출, validation_api 의존 금지.
- USD 로드 deadlock 방어 3요소 복사 (on_startup add_logger 금지 / run_coroutine+wrap_future
  / new_stage + CreatePayloadCommand(instanceable=True) reference + _wait_stage_loading tick /
  play 중 로드 금지 / forward-slash). open_stage 는 deadlock 안전성 미검증이라 사용 안 함.
- R1 실자산 우선(live 탐색, 없으면 근접 proxy). 케이블만 BasisCurves tube authored (문서화된 예외).
- R2 클릭 trigger 는 timeline play 중에만 동작.
- R3 viewport_capture 후 Read tool 시각 검증 의무 (blank 면 조명·카메라 재조정).
- UI 문자열 영어 only (Kit 107 font atlas CJK 미지원).
- 로깅 carb.log_* 만, __init__.py 에 IExt import 필수, uv 만 사용.

## 자산 조달 (SPEC §2, §6)
- desktop PC / monitor / server rack 은 live 탐색으로 실자산 선택:
  asset_list / content_browse 로 SimReady(s~z 미확인 ~500종) 에서 monitor/computer/server/rack 검색.
  없으면 industrialsteelshelving 등 근접 proxy 로 서버랙 대체.
- office.usd = $ISAAC/Environments/Office/office.usd (payload, instanceable).
- 케이블 = BasisCurves tube. 모든 동적 대상은 customData net:role + net:order 로 태그 (SPEC §5).

## 구현 순서 (SPEC §10)
1. office_mcp/ 스캐폴드 + extension.toml + 최소 윈도우(Load 버튼 + Label) → Kit 로드 확인
   (office_mcp/exts/ 를 ext search path 에 등록 — README 에 절차 명시).
2. build/build_scene.py → scenes/office_datacenter.usd 저작·저장 → R3 시각 검증.
3. scene_loader.py + safe_load.py → Load Scene 정상 오픈 + 태그 발견.
4. click_picker.py → 뷰포트 클릭 raycast → trigger 판정 (play gating).
5. transmission.py + telemetry.py → 진행파 + LED 순차 점등 + Label.
6. 단위 테스트(office_mcp/tests, Kit 무의존) + self-test stamp(/OfficeMcp/SelfTestResult)
   + 최종 R3 3-시점 시각 검증 (idle / mid-transmission / delivered).
7. README.md (ext search path 등록 + 사용법).

## 완료 기준 (Definition of Done)
- Load Scene → 네이티브 Play → PC 전원 버튼 클릭 → 케이블 진행파가 PC→스위치→서버 순차 흐름,
  서버 3대 LED 순차 점등이 viewport_capture + Read 로 시각 확인됨.
- 단위 테스트 통과, self-test stamp green, 모든 제약(독립구조/deadlock/R1/R2/R3/UI영어) 준수.
- 산출물 전부 office_mcp/ 하위.

먼저 office_mcp/SPEC.md 와 위 필독 문서를 읽고, 구현 계획(plan)을 세운 뒤 단계별로 진행하라.
각 단계 후 R3 시각 검증으로 실제 동작을 확인하고, 추측이 아닌 증거로 완료를 주장하라.
```

---

## 참고 — 이 GOAL 의 출처

- 설계 확정 문서: `office_mcp/SPEC.md` (brainstorming 결과, 2026-05-25)
- 핵심 결정 9건 + 제약 + 디렉토리/Scene/Extension 구조 + 데이터 흐름 + 테스트 전략 포함.
- 새 세션은 MCP 서버 캐시가 깨끗하므로, Extension `.py` 변경 반영에 주의 (`docs/invariants/ext-reload.md`).
