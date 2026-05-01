# Isaac Sim Tutorial Extension — 수동 QA Checklist

학생 PC 재현용. 각 항목 실패 시 실패 원인을 notes 컬럼에 기록.

## 선행 조건

- [O] Isaac Sim 5.1 kit.exe 기동 성공
- [O] `omni.mycompany.validation_api` 활성화 확인
- [O] `omni.mycompany.isaac_tutorial` 활성화 확인 (Extension Manager 또는 `extension_list_all` MCP tool)

## UI 표시
- 수정 필요: 한글은 전부 깨져보임. 한글이 깨지지 않도록 하거나 영어로 작성해야 함.
- [o] "Isaac Sim Tutorial" 창 자동 표시 (560 × 640)
- [o] 창 상단에 빨간 "Reset all (stage_new)" 버튼
- [x] Status label "Status: (idle)" 표시
- [o] "환경 설정" CollapsableFrame 확장된 상태로 표시
- [o] "튜토리얼 스탭" CollapsableFrame 확장된 상태로 표시
- [ ] Progress bar frame 은 hidden (async job 없을 때)

## 환경 설정 (B#1~B#4)

### B#1 — Scale
- [O] Stage 에서 Cube 생성 → 선택 → "Scale selected ×10" 클릭 → 10배 확대
- [O] Ctrl+Z → 원래 크기로 복원
- [O] "Scale selected ÷10" → 1/10 축소
- [O] "Reset scale → 1.0" → (1, 1, 1) 복원
- [O] 아무 prim 선택 안 한 상태로 Scale 버튼 클릭 → status label 에 "✗ ValueError: 선택된 prim 이 없습니다" + notification popup

### B#2 — Camera speed
- [O] 6 개 속도 버튼 각각 클릭 → Viewport 에서 RMB + WASD 이동 속도 변화 체감
- [O] 클릭 후 `carb.settings.get_settings().get("/persistent/app/viewport/camMoveVelocity")` 값이 바뀜 (Kit Console 에서 확인)

### B#3 — Ceiling toggle
- [O] 스탭 1 로 office 로드 후 "Hide all Ceiling prims" 클릭 → 천장 메시 사라짐 + "Matched: N prims" 표시 
- [ ] Ventilation, Cube Prim들도 전부 숨겨야함
- [O] 버튼 라벨이 "Show all Ceiling prims" 로 변경
- [O] 재클릭 → 복원 + 라벨 다시 "Hide..." + "Matched: 0 prims"

### B#4 — WASD Nova Carter
- [ ] "Spawn WASD-controllable Nova Carter @(0,0,0)" 클릭 → Nova Carter 로드 + `/World/nova_carter/WASDGraph` 생성 (Stage 패널에서 확인)
- [ ] 시뮬레이션 Play → W 키 → 전진 / S → 후진 / A → 좌회전 / D → 우회전 / Space → 정지
- [ ] WASDGraph 내 DifferentialController 노드의 wheel joint 이름이 실제 Nova Carter articulation 의 joint 이름과 일치 (실패 시 `robot_get_joint_positions("/World/nova_carter")` 로 실측 → `spawn_wasd_nova_carter` 호출부 override)

## 튜토리얼 스탭 (auto-chain + idempotency)

### 기본 순서 실행
- [ ] 스탭 1 → office.usd 로드 (viewport 에 office 환경 표시)
- [ ] 스탭 2 → Nova Carter 로드 (origin 에 로봇 표시)
- [ ] 스탭 3 → NavMesh bake 후 Nova Carter 가 가장 가까운 Chair 방향으로 주행. Progress bar 0→1 애니메이션 + "Navigating..." 상태
- [ ] 스탭 4 → Biped 로드 + chair 로 이동 + Sit 애니메이션 재생 (공중 아님)

### Sub-buttons
- [ ] "Show walkable area" → NavMesh 녹색 오버레이 표시, 라벨 "Hide walkable area" 로 변경
- [ ] 재클릭 → 오버레이 사라짐 + 라벨 복원
- [ ] "Attach sensors + start recording" → label 에 `C:/Users/<user>/AppData/Local/Temp/isaac_tutorial/<timestamp>/` 표시
- [ ] Windows 탐색기에서 해당 경로에 `.png` (RGB) / `.npy` (depth) 파일이 쌓이는지 확인

### Auto-chain prereq
- [ ] Reset All → clean stage → **스탭 3 을 바로 클릭**. status label 에 "Step 1 open office" → "Step 2 load Nova Carter" → "Step 3 navigate" 순차 표시 + 최종적으로 Nova Carter 가 chair 방향으로 이동

### Idempotency
- [ ] 스탭 1 재클릭 → "Office already loaded (skipped)" status
- [ ] 스탭 2 재클릭 → "Nova Carter already loaded (skipped)" status

## Reset All (2-click confirm)

- [ ] Reset 1회 클릭 → "Click Reset again within 3 seconds to confirm." notification (stage 변경 없음)
- [ ] 3 초 내 Reset 2회 클릭 → stage new + 모든 state 초기화 (스탭 라벨에서 ✓ 사라짐, Nova Carter / office / Biped 삭제됨)
- [ ] 3 초 경과 후 Reset 다시 클릭 → 다시 notification (cold restart 준비)

## ASYNC + Cancel

- [ ] 스탭 3 진행 중 Progress bar 가 0 → 1 로 움직임
- [ ] Progress label 에 "running (N%)" 형태 표시
- [ ] Cancel 버튼 클릭 → Nova Carter 주행 중단 + progress frame 숨김 + status "canceled"

---
실패한 항목은 `docs/implementation_issues.md` 에 재현 절차 + 오류 메시지 + Kit Console 출력 3 종 기록 후 수정.
