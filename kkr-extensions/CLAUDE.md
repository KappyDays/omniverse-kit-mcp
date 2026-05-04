<!-- Parent: ../CLAUDE.md -->
<!-- Scope: Kit Extension 개발 루트 — 네비게이션 허브 -->

# kkr-extensions — Kit Extension 개발

Isaac Sim GUI (`kit.exe`) 내부에서 실행되는 Kit Extension 들이 모여 있는 루트. 이 파일은 **토픽 문서 (`docs/`) 와 각 Extension 폴더 로 안내하는 nav hub**.

## ⚠️ 작업 전 필독 (invariants)

- Extension `.py` 수정 / reload (fswatcher + zombie cleanup): [`../docs/invariants/ext-reload.md`](../docs/invariants/ext-reload.md)
- USD 로드 4 조건 (MDL deadlock 방어): [`../docs/invariants/usd-load.md`](../docs/invariants/usd-load.md)
- UI automation 시퀀스 (`extension_ui_invoke`): [`../docs/invariants/ui-invoke.md`](../docs/invariants/ui-invoke.md)

## Extension 목록

| 디렉토리 | 역할 |
|---------|------|
| `omni.mycompany.validation_api/` | **REST bridge Extension** — MCP 서버가 Kit SDK 를 원격 조작할 수 있게 하는 FastAPI router (`localhost:8011/validation/v1/**`). 이 프로젝트의 MCP tool 전부가 이 REST 에 의존 |
| `omni.mycompany.isaac_tutorial/` | 학습자용 UI Extension — 4 환경설정 + 4-step 튜토리얼. validation_api 에 **예외적 in-process import** 의존 (이미 만들어진 extension) |
| `omni.mycompany.ui_demo/` | Phase D 최소 UI demo (Button + StringField + Label) — `extension_get_ui_tree` / `extension_ui_invoke` automation target |
| `omni.mycompany.ui_demo_advanced/` | Phase E 확장 demo (CollapsableFrame + ComboBox + Slider + TreeView) — 현실적 위젯 커버리지 |
| `omni.mycompany.navmesh_playground/` | Phase J Extension — `full_warehouse.usd` 위에 People/Robot 을 random walkable 배치 후 NavMesh path 따라 이동. People = AnimGraph Walk→Sit FSM, Robot = DifferentialController 기반 물리 바퀴. **독립 구조** (validation_api 의존 없음). deadlock-recipe 복사. |
| `omni.mycompany.humanoid_pick_place/` | NVIDIA `IsaacSim/Humanoid28` (28-DOF) single-arm pick&place demo. `SingleArticulation` 키프레임 trajectory + cube grasp via kinematic-toggle + RigidBody 추적. **독립 구조**, Phase 2 후보 (Unitree H1 / Fourier GR-1T2) registry 등록 완료. |
| `omni.mycompany.stage_annotator/` | Prim-anchored sticky-note 리뷰 시스템 — 4-단계 status workflow (Open / In Progress / Resolved / Won't Fix), threaded replies, title/body 인라인 편집, status별 색상 3-D Sphere pin 자동 동기, JSON export, customData 영속. **독립 구조** — self-test stamps `/Annotator/SelfTestResult`. |
| `omni.mycompany.stage_compass/` | Stage 탐색용 floating top-down radar HUD — concentric range rings, prim-type 별 colour 도트, 카메라 marker triangle, world-fixed N/E/S/W cardinal labels (heading 회전), wheel-zoom, click-to-teleport, persistent waypoints (rootLayer customData). **독립 구조** — `Y`/`Z`-up 자동 감지. self-test stamps `/Compass/SelfTestResult`. |
| `omni.mycompany.conveyor_pick/` | Phase B Extension — O-loop conveyor + Franka pick-and-place demo. validation_api 의존 (Phase B 시점 작성, 독립 정책 확정 전) |
| `omni.mycompany.usd_composer_input/` | Phase A Composer Extension — Hover highlight + QWEASD camera input for USD Composer. **독립 구조** |
| `omni.mycompany.usd_mouse_interact/` | Composer Extension v0.2 — FPS fly-camera + whitelist prim picker + info overlay (timeline-driven). dev panel 의 manual inject button (yaw / WASD / Force pick) 으로 OS-level input 우회 검증. **독립 구조** — sub-project `usd-mouse-interact/` 에 docs / captures / tests 별도 |
| `omni.userext.pickplace/` | Pick&Place Workshop Extension — Isaac Sim 5.1 위 O자 conveyor loop + 2 Franka arms 가 dynamic cube 추적 → pick → place. v3-v5 NVIDIA refactor (PickPlaceController + ConveyorBelt + KLT bin + ground_snap + REACH_OFFSET budget). **독립 구조** — sub-project `isaac-pick-place/` 에 docs / captures / tests / live_test 별도 |

## 핵심 정책

### 🛑 신규 Extension 은 **독립 구조** (2026-04-22 확정)

- Kit SDK (`omni.kit.commands` / `omni.usd` / `pxr.*` 등) **직접 호출**
- `validation_api` 의존 **금지**
- S3 MDL-heavy asset (office / warehouse / nova_carter / Biped_Setup 등) 로드 필요 시 `docs/usd-load-deadlock-recipe.md` 의 방어 코드를 **복사** (import 아닌)
- 이미 만들어진 Extension (예: `isaac_tutorial`) 만 validation_api 재사용 허용 — 역사적 예외

### 공통 규칙 (상세는 docs/extension-basics.md)

- `__init__.py` 에 `IExt` 서브클래스 import 필수 (없으면 `on_startup` 호출 안 됨)
- 로깅은 `carb.log_warn / log_info / log_error` 만 — Python `logging` / `print` 은 Kit Console 안 보임
- 코드 수정 반영: **로컬 개발은 hot-reload** / `[dependencies]` 변경은 Kit 완전 재시작
- **UI 문자열은 영어만 (hard rule — 예외 없음)** — Kit 107 `omni.ui` font atlas 는 CJK glyph 가 없어 한글/한자 입력 시 글자가 □ 으로 깨진다. DevPanel 라벨 / Button text / hint label / Window title / status text 모두 영어로 author

## 토픽 문서 (`docs/`)

| 문서 | 언제 읽나 |
|------|----------|
| [`docs/extension-basics.md`](docs/extension-basics.md) | **신규 Extension 시작할 때** — IExt / toml / hot-reload / 독립 스켈레톤 copy-paste 템플릿 |
| [`docs/kit-sdk-pitfalls.md`](docs/kit-sdk-pitfalls.md) | 특정 Kit API (USD load / articulation / character / NavMesh / sensor / viewport / UI automation) 쓰다가 막혔을 때 도메인별 실측 함정 검색 |
| [`docs/usd-load-deadlock-recipe.md`](docs/usd-load-deadlock-recipe.md) | S3 MDL-heavy asset 을 독립 Extension 에서 로드할 때 복사할 방어 코드 (log_capture disable + run_coroutine + CreatePayloadCommand instanceable 3-요소) |
| [`docs/validation_api-reuse.md`](docs/validation_api-reuse.md) | **이미 만들어진 Extension 전용** — validation_api 의 rest_router 싱글턴 재사용 방법 + 서비스 호출 규약 (dict/positional/sync-async 주의). 신규 extension 은 불필요 |
| [`docs/lessons-learned.md`](docs/lessons-learned.md) | 과거 구현 실수 + 교훈 누적 로그. 새 작업 시작 전 훑어보면 같은 실수 회피 |

## Extension 별 개별 문서

공통 내용은 `docs/` 에, 각 Extension 고유한 것만 Extension 폴더 내에:

- `omni.mycompany.isaac_tutorial/QA_CHECKLIST.md` — 튜토리얼 Extension 전용 수동 QA 체크리스트

## 관련 경계

- MCP 서버가 `validation_api` 를 어떻게 호출하는지: [`../src/omniverse_kit_mcp/CLAUDE.md`](../src/omniverse_kit_mcp/CLAUDE.md) + [`../src/omniverse_kit_mcp/modules/CLAUDE.md`](../src/omniverse_kit_mcp/modules/CLAUDE.md)
- `validation_api` REST endpoint 전체 목록 SoT: [`omni.mycompany.validation_api/omni/mycompany/validation_api/rest_router.py`](omni.mycompany.validation_api/omni/mycompany/validation_api/rest_router.py) (코드가 SoT)
- Extension 활성화 설치 절차: [`../setup/CLAUDE.md`](../setup/CLAUDE.md)
- Scenario YAML 에서 Extension UI 자동 조작: [`../scenarios/CLAUDE.md`](../scenarios/CLAUDE.md)
