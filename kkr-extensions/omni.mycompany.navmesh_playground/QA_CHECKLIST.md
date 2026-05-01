<!-- Parent: ../CLAUDE.md → docs/extension-basics.md -->
<!-- Scope: NavMesh Playground 사용자 워크플로우 + 수동 QA 체크리스트 -->

# NavMesh Playground — User Workflow + QA Checklist

이 Extension 은 **Isaac Sim 단독 환경 (Isaac-sim-MCP 없이)** 에서도 동작합니다.
모든 callback 은 Kit SDK 직접 호출 (`omni.kit.commands` / `omni.usd` /
`omni.anim.graph.core` / `omni.anim.navigation.core` / `pxr.*` 등) — `omni.mycompany.validation_api` 의존 0.

## 사용자 워크플로우 (5 단계)

NavMesh Playground 패널 열기 (`Window > NavMesh Playground` 또는 Extension 활성화 시 자동) 후:

| # | 동작 | 결과 / 주의 |
|---|------|-------------|
| 1 | **Stage > Load Warehouse** 클릭 | `/World/Warehouse` 에 Simple_Warehouse 로드 (~17-20s S3) |
| 2 | **NavMesh > Bake** — 3가지 중 하나 선택: | |
|   | • **Bake (Stage)** — 기존 NavMeshVolume 사용 | |
|   | • **Bake (New)** — 30m Include volume 신규 생성 + bake. **빠른 시작용** | |
|   | • **Bake (Only Warehouse)** — 사용자 hand-authored 한 stage volume 들의 Transform/Scale/Type 그대로 보존하여 bake. 각 volume 의 properties 가 Status Log 에 출력. **권장: Stage 에 직접 Include + Exclude 배치 후 사용** | |
| 3 | **Spawn > Type / Sit / Count 설정 → Spawn @ Random Walkable** | NavMesh walkable area 에서 random N개 사람 또는 로봇 생성 |
|   | **Agents 패널 → 각 Agent의 Start/Goal 옆 "Set Cur" 클릭** | 현재 위치를 Start (또는 Goal) 좌표로 설정. Goal 은 직접 입력도 가능 |
| 4 | **Sim Play (Space 키 또는 패널 Sim Play 버튼) — 선택사항** | 미실행 시 Step 5 의 Go 가 자동 timeline.play() 호출. 미리 play 해두면 AnimGraph register 빨라져서 첫 Go 응답이 즉각 |
| 5 | **각 Agent의 "Go" 버튼 클릭** | People → Walk→Sit FSM. Robot → DifferentialController + Pure Pursuit. Stop 으로 중단, Remove 로 stage 에서 삭제 |

## NavMesh Volume 직접 편집 (선택)

특정 영역을 walkable 에서 제외하려면:
1. Stage 패널 우클릭 → Create > NavMeshVolume → "Exclude" 타입
2. xformOp:translate / scale 로 제외 영역 위치 + 크기 지정
3. 패널의 **Bake (New-Warehouse)** 또는 **Bake (Stage)** 재클릭 → Include + Exclude 모두 적용

`Bake (New-Warehouse)` 는 stage 의 모든 NavMeshVolume 자동 인식 — Include/Exclude 비율 status log 에 표시.

## 수동 QA 체크리스트

UI 위젯 동작은 Kit GUI 환경에서만 검증 가능 (pytest 단위 테스트 범위 밖). 사용자 시연 전 다음 항목을 마우스 직접 클릭으로 확인:

### 기본 시나리오
- [ ] 패널이 `Window > NavMesh Playground` 메뉴에 표시되고 클릭 시 열림
- [ ] **Load Warehouse** 클릭 → Status Log 에 "Warehouse loaded: /World/Warehouse" + Stage 패널에 `/World/Warehouse` Xform 추가
- [ ] **Bake (New-Warehouse)** 클릭 → Triangles 라벨이 0 이상 (실측: warehouse 면적의 베이크 결과 ≥ 100)
- [ ] **Toggle Overlay** 클릭 → viewport 에 cyan walkable 영역 토글
- [ ] Spawn type=People, count=1, **Spawn @ Random Walkable** 클릭 → Agents 섹션에 People-01 추가 + viewport 에 사람 표시
- [ ] Agent 패널의 Start `Set Cur` 클릭 → Start 좌표 필드가 현재 위치로 갱신
- [ ] Agent 패널의 Goal `Set Cur` 클릭 → 동일 (별도 좌표 입력도 OK)
- [ ] **Sim Play** (또는 Space 키) → timeline 재생 시작
- [ ] Agent 의 **Go** 클릭 → 캐릭터가 Goal 방향으로 walk 애니메이션 시작 (timeline 미재생 시 자동 play)
- [ ] Goal 도달 시 Sit pose 로 전환 (SitIdle / SitTalk / SitReading 중 spawn 시 선택한 variant)
- [ ] **Stop** → 캐릭터 정지 (state=Stopped)
- [ ] **Remove** → stage 에서 prim 완전 삭제 (parent + 자식 SkelRoot 모두)

### Robot 시나리오
- [ ] Spawn type=Robot, count=1, **Spawn @ Random Walkable** → Robots 섹션에 Robot-01 (NovaCarter or Jetbot) 추가
- [ ] Start/Goal `Set Cur` + **Go** → 로봇이 NavMesh path 따라 wheel rotation 으로 주행 (S-curve 없이 부드럽게)
- [ ] Goal 도달 또는 timeout 시 wheel velocity 0 으로 정지
- [ ] Remove → stage 에서 articulation 완전 제거

### Multi-Agent
- [ ] count=3 으로 Spawn People → 서로 다른 walkable point 3 곳에 배치
- [ ] count=2 로 Spawn Robot 추가 → 사람과 로봇 5개 동시 동작 가능
- [ ] **Reset All Agents** → 모든 agent 일괄 정리

### NavMesh Volume 편집
- [ ] Stage 패널에서 NavMeshVolume(Exclude) 직접 추가 + Bake (New-Warehouse) 재클릭 → Status Log 에 "1 Include + 1 Exclude" 표시 + Exclude 영역에는 random walkable point 가 spawn 안 됨

## 알려진 한계

- **Mismatched units carb.log_warn**: Biped_Setup (cm) ↔ stage (m) 단위 차이로 USD 가 informational warning 1회 출력. 무해 — USD 가 자동으로 `xformOp:scale:unitsResolve=(100,100,100)` 보상. 무시 가능
- **Bake (New) UI button 의 Triangle count = 0 표시**: NavMesh 자체는 정상 baked (sample_walkable_points 작동 검증). UI 의 `iface.get_navmesh().get_triangle_count()` 호출 timing 문제로 표시값만 0. 실제 동작에 영향 없음
- **Panel state="Walking" 이 "Sitting" 으로 자동 전환 안 됨 (간헐적)**: AnimGraph world transform 폴링이 매우 가까운 arrival 을 가끔 놓침. 캐릭터 자체는 정상 도달 + Sit 자세. UI label 만의 진단 버그
- **Mouse 클릭만 안정 (Claude MCP `extension_ui_invoke` 도 가능하지만 첫 호출은 layout settle 1초 필요)** — 자동화 테스트는 `validation_api/services/ui_service.py::ui_invoke` 의 auto-show 가 자동 처리

## 관련 경계

- 코드 경로: `omni/mycompany/navmesh_playground/{ui_panel,people_controller,robot_controller,usd_loader,navmesh_sampler,agent_manager,extension}.py`
- 자동 검증 시나리오: `scenarios/smoke/navmesh_playground_e2e.yaml` (MCP scenario_validate 로 실행)
- ext_ui_invoke 사용 가이드: `docs/lessons-learned.md` L15
