# Historical Isaac Sim 5.1 — Sensor Menu Catalog

**Source of Truth**: `window_menu_list(menu_path="Create")` — Isaac Sim Kit 5.1 merged menu tree.
**Regenerate**: Isaac Sim 기동 상태에서 `mcp__isaacsim-mcp__window_menu_list(menu_path="Create")` 호출 → `Create/Sensors/*` 항목만 추출. Kit SDK / Extension 버전 변경 시 재생성.
**Last captured**: 2026-04-20 (Isaac Sim 5.1.0 + kkr-extensions/validation_api 기동 상태).

## 사용 목적

- "특정 센서를 사용해달라" 요청 시 이 카탈로그에서 해당 센서 찾기
- Onclick action (ext_id + action_id) 으로 `window_menu_trigger(menu_path="Create/Sensors/...")` 호출
- PPTX Twin Build 슬라이드에서 실 센서 prim 생성 (Extension 의 mock `sensor_service` 대신)
- Isaac Sim GUI 유저와 동일 경로로 sensor 생성 — USD schema 정확 (UsdGeom.Camera + proper annotator vs mock)

## 센서 카테고리 전체 (`Create/Sensors/*`)

| Top-level 항목 | 종류 | submenu? | 비고 |
|---|---|---|---|
| **RTX Lidar** | 고해상도 RTX 기반 | ✓ | 6 제조사 × 여러 모델 |
| **RTX Radar** | RTX 기반 radar | — | 단일 action |
| **Camera and Depth Sensors** | RGB-D / stereo / mono camera | ✓ | 6 제조사 × 여러 모델 |
| **Contact Sensor** | Physics 접촉 감지 | — | `isaacsim.sensors.physics.ui` |
| **Imu Sensor** | 관성 측정 (가속도 + 각속도) | — | `isaacsim.sensors.physics.ui` |
| **PhysX Lidar** | PhysX raycast 기반 Lidar | ✓ | Rotating / Generic |
| **LightBeam Sensor** | 광선 감지 (침입/장애물) | ✓ | Generic / Tashan TS-F-A |
| Asset Browser | 단축 메뉴 (sensor asset 브라우저 오픈) | — | 센서 생성 아님 |

## 상세 카탈로그

### 1. RTX Lidar (`Create/Sensors/RTX Lidar/{Vendor}/{Model}`)

6 vendor 에 걸친 RTX lidar 목록. `onclick_action` 은 모두 **`[Create_Sensors_RTX_Lidar_{Vendor}, {Model}]`** 패턴 — Kit 이 내부 dispatch 로 모델별 USD schema + annotator 자동 적용.

| Vendor | Models (menu_path tail) |
|---|---|
| **HESAI** | `XT32 SD10` |
| **NVIDIA** | `Example Rotary 2D` · `Example Rotary` · `Example Solid State` · `Simple Example Solid State` |
| **Ouster** | `OS0` · `OS1` · `OS2` · `VLS 128` (Velodyne 호환) |
| **SICK** | `microScan3` · `multiScan136` · `multiScan165` · `nanoScan3` · `picoScan150` · `TIM781` |
| **Slamtec** | `RPLIDAR S2E` |
| **ZVISION** | `ML30S` · `MLXS` |

**Menu trigger 예**:
```
window_menu_trigger(menu_path="Create/Sensors/RTX/Lidar/NVIDIA/Example Rotary")
window_menu_trigger(menu_path="Create/Sensors/RTX/Lidar/Ouster/VLS 128")
```

**주의**: path 에 공백이 들어간 메뉴 항목은 Kit 이 `_` 로 치환해서 action key 를 만든다 (예: "RTX Lidar" → `Create_Sensors_RTX_Lidar` action prefix). `window_menu_trigger` 는 **실 menu_path 슬래시 버전**을 받는다 (`Create/Sensors/RTX/Lidar/NVIDIA/Example Rotary` — `RTX Lidar` → `RTX/Lidar` 로 나눠진 구조).

### 2. RTX Radar (`Create/Sensors/RTX Radar`)

- 단일 leaf action. `onclick_action = ["Create_Sensors", "RTX Radar"]`
- Menu trigger: `window_menu_trigger(menu_path="Create/Sensors/RTX Radar")`

### 3. Camera and Depth Sensors (`Create/Sensors/Camera and Depth Sensors/{Vendor}/{Model}`)

RGB / depth / stereo / GMSL2 camera 18 개 모델.

| Vendor | Models |
|---|---|
| **Intel** | `Intel Realsense D455` (RGB-D) |
| **Orbbec** | `Orbbec Gemini 2` · `Orbbec FemtoMega` · `Orbbec Gemini 335` · `Orbbec Gemini 335L` |
| **Leopard Imaging** | `Hawk` (stereo) · `Owl` (mono) |
| **Sensing** | `Sensing SG2-AR0233C-5200-G2A-H100F1A` · `Sensing SG2-OX03CC-5200-GMSL2-H60YA` · `Sensing SG3-ISX031C-GMSL2F-H190XA` · `Sensing SG5-IMX490C-5300-GMSL2-H110SA` · `Sensing SG8S-AR0820C-5300-G2A-H120YA` · `Sensing SG8S-AR0820C-5300-G2A-H30YA` · `Sensing SG8S-AR0820C-5300-G2A-H60SA` |
| **SICK** | `Inspector83x` |
| **Stereolabs** | `ZED_X` |

**Menu trigger 예**:
```
window_menu_trigger(menu_path="Create/Sensors/Camera and Depth Sensors/Intel/Intel Realsense D455")
window_menu_trigger(menu_path="Create/Sensors/Camera and Depth Sensors/Stereolabs/ZED_X")
```

### 4. Physics Sensors (Contact / Imu)

- **Contact Sensor**: `onclick_action = ["isaacsim.sensors.physics.ui-0.1.12", "isaacsim.sensors.physics.ui-0.1.12Contact_Sensor"]`. menu_path = `Create/Sensors/Contact Sensor`
- **Imu Sensor**: `onclick_action = ["isaacsim.sensors.physics.ui-0.1.12", "isaacsim.sensors.physics.ui-0.1.12Imu_Sensor"]`. menu_path = `Create/Sensors/Imu Sensor`

둘 다 `isaacsim.sensors.physics` extension 이 enable 되어 있어야 동작 (기본 `isaacsim.exp.full.kit` preset 에 포함).

### 5. PhysX Lidar (`Create/Sensors/PhysX Lidar/{Variant}`)

RTX 가 아닌 PhysX raycast 기반 lidar — compute cheap, 렌더 품질 낮음.

- `Rotating` → rotating laser scan 패턴
- `Generic` → 파라미터 커스텀 가능

Menu trigger 예:
```
window_menu_trigger(menu_path="Create/Sensors/PhysX Lidar/Rotating")
```

### 6. LightBeam Sensor (`Create/Sensors/LightBeam Sensor/{Variant}`)

단일/다중 빔 광센서 (침입 감지 · 안전 존).

- `Generic` → 파라미터 커스텀
- `Tashan TS-F-A` → 상용 제품 프리셋

## Robot-with-Sensors 프리셋 (`Create/Robots`)

**`Create/Robots/Nova Carter with Sensors`** — NovaCarter base + RTX Lidar + Camera + IMU 를 공장 기본 위치에 정확히 mount 한 USD composition. 자체 센서 attach 스크립트 작성 대신 이 menu 를 호출하는 쪽이 "NVIDIA 공식 sensor 배치" 을 얻는 빠른 경로.

Menu trigger:
```
window_menu_trigger(menu_path="Create/Robots/Nova Carter with Sensors")
```

## 호출 규약 (`window_menu_trigger`)

- 경로는 **메뉴 path 의 슬래시 형식** 그대로. 공백은 유지 (e.g. `RTX Lidar`, `Intel Realsense D455`).
- 실제 응답의 `created_prims: [...]` 필드로 어떤 USD prim 이 생성됐는지 확인. `[]` 이면 silent no-op (extension 미활성 등).
- 일부 센서는 viewport 포커스/selection 기반 상대 배치 — 호출 전에 `stage_set_selection(["/World/Robot"])` 로 부모 prim 선택하면 그 아래에 자식으로 생성.

## 현 Extension `sensor_service` vs 이 카탈로그

`kkr-extensions/.../services/sensor_service.py` 의 `attach_rtx_camera` / `attach_rtx_lidar` / `attach_rtx_depth_camera` 는 **UsdGeom.Camera + customData.validation_api.sensor_type tag** 기반 mock 구현. 실제 RTX sensor schema (Lidar scan buffer annotator, Radar sample buffer, HESAI/Ouster-specific intrinsics) 는 이 카탈로그의 menu action 이 생성하는 prim 만 가진다.

**사용 구분**:
- **튜토리얼 · 시각 교육**: mock (sensor_attach_rtx_* MCP tool) — 부착 위치 + Stage hierarchy 시각화만 필요
- **실 점군 / depth map / IMU 데이터**: GUI menu trigger — Phase G/H 에서 `sensor_service` 확장으로 이 카탈로그의 action 호출 통합 예정

## 재생성 절차

1. Isaac Sim 기동 (`kit_app_start` or `scripts/run_process_module_standalone.py start`)
2. `mcp__isaacsim-mcp__window_menu_list(menu_path="Create")` 호출
3. response 의 `items` 중 `path` 가 `Create/Sensors/` 또는 `Create/Robots/Nova Carter` 로 시작하는 항목만 필터
4. 이 문서의 테이블 형식으로 정리 (vendor → model 2-level grouping)
5. 사용자가 제공한 업스트림 Isaac Sim release note 확인하여 빠진/추가된 모델 추적

**재생성 트리거**:
- Isaac Sim SDK 업그레이드 (예: 5.1 → 6.0)
- `isaacsim.sensors.experimental.rtx` / `isaacsim.sensors.experimental.physics` extension 버전 변경
- 사용자가 새 제조사 센서 추가 요청 시 — 실물 확인 후 이 문서에 append
