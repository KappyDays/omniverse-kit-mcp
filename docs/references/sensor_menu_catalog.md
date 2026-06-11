# Isaac Sim 6.0 — Sensor Menu Catalog

**Source of Truth**: `window_menu_list(menu_path="Create")` — Isaac Sim 6.0.0 live merged menu tree.
**Last captured**: 2026-06-11, Isaac Sim 6.0.0 standalone + `omni.mycompany.validation_api` on port 8111.
**Capture scope**: `Create/Sensors/**` plus `Create/Robots/Nova Carter with Sensors` (`84` sensor-related menu entries).

## 사용 목적

- "특정 센서를 사용해달라" 요청 시 이 카탈로그에서 해당 센서 찾기
- `onclick_action` (`ext_id`, `action_id`) 기반으로 `window_menu_trigger(menu_path="...")` 호출
- 실 제조사 preset 이 필요한 경우 Extension 의 generic attach tool 대신 GUI menu action 사용
- Isaac Sim GUI 유저와 동일 경로로 sensor prim/schema/preset 생성

## 경로 규칙

`window_menu_trigger` 는 이 문서의 **실제 `path` 값**을 그대로 받는다. Isaac Sim 6.0 menu introspection 은 일부 표시명을 path segment 로 나눈다.

| 표시명 | 실제 trigger path 예 |
|---|---|
| `Camera and Depth Sensors` | `Create/Sensors/Camera/and/Depth/Sensors/RealSense/Realsense D455` |
| `RTX Lidar` | `Create/Sensors/RTX/Lidar/NVIDIA/Example Rotary` |
| `PhysX Lidar` | `Create/Sensors/PhysX/Lidar/Rotating` |
| `Physics Raycast Sensor` | `Create/Sensors/Physics/Raycast/Sensor/Rotating Physics Raycast Sensor` |
| `LightBeam Sensor` | `Create/Sensors/LightBeam/Sensor/Generic` |

## 센서 카테고리 전체

| Top-level 항목 | 종류 | Leaf 수 | 비고 |
|---|---:|---:|---|
| Asset Browser | Browser shortcut | 1 | sensor 생성 아님 |
| Camera and Depth Sensors | RGB-D / stereo / mono camera | 26 | Orbbec, Leopard Imaging, Luxonis, RealSense, Sensing, SICK, Stereolabs |
| Contact Sensor | Physics contact | 1 | `isaacsim.sensors.physics.ui` |
| Imu Sensor | Physics IMU | 1 | `isaacsim.sensors.physics.ui` |
| Physics Raycast Sensor | Physics raycast | 3 | solid-state / rotating / beam curtain |
| PhysX Lidar | PhysX lidar | 2 | rotating / generic |
| LightBeam Sensor | PhysX light beam | 2 | generic / Tashan TS-F-A |
| RTX Lidar | RTX lidar | 21 | HESAI, NVIDIA, Ouster, SICK, Slamtec, ZVISION |
| RTX Radar | RTX radar | 2 | NVIDIA generic, TI IWRL6432AOP |
| RTX Acoustic | RTX acoustic | 1 | NVIDIA generic |

## Camera and Depth Sensors

Base path: `Create/Sensors/Camera/and/Depth/Sensors/{Vendor}/{Model}`
Action extension: `isaacsim.sensors.camera.ui`

| Vendor | Model path | Action id |
|---|---|---|
| Orbbec | `Orbbec/Orbbec Gemini 2` | `create_camera_orbbec_gemini_2` |
| Orbbec | `Orbbec/Orbbec FemtoMega` | `create_camera_orbbec_femtomega` |
| Orbbec | `Orbbec/Orbbec Gemini 335` | `create_camera_orbbec_gemini_335` |
| Orbbec | `Orbbec/Orbbec Gemini 335L` | `create_camera_orbbec_gemini_335l` |
| Leopard Imaging | `Leopard/Imaging/Hawk` | `create_camera_hawk` |
| Leopard Imaging | `Leopard/Imaging/Owl` | `create_camera_owl` |
| Luxonis | `Luxonis/Luxonis OAK4-D` | `create_camera_luxonis_oak4_d` |
| Luxonis | `Luxonis/Luxonis OAK4-D Wide` | `create_camera_luxonis_oak4_d_wide` |
| Luxonis | `Luxonis/Luxonis OAK-D Pro PoE` | `create_camera_luxonis_oak_d_pro_poe` |
| Luxonis | `Luxonis/Luxonis OAK-D Pro W PoE` | `create_camera_luxonis_oak_d_pro_w_poe` |
| Luxonis | `Luxonis/Luxonis OAK-D ToF` | `create_camera_luxonis_oak_d_tof` |
| RealSense | `RealSense/Realsense D455` | `create_camera_realsense_d455` |
| RealSense | `RealSense/Realsense D457` | `create_camera_realsense_d457` |
| RealSense | `RealSense/Realsense D555` | `create_camera_realsense_d555` |
| Sensing | `Sensing/Sensing SG2-AR0233C-5200-G2A-H100F1A` | `create_camera_sensing_sg2_ar0233c_5200_g2a_h100f1a` |
| Sensing | `Sensing/Sensing SG2-OX03CC-5200-GMSL2-H60YA` | `create_camera_sensing_sg2_ox03cc_5200_gmsl2_h60ya` |
| Sensing | `Sensing/Sensing SG3-ISX031C-GMSL2F-H190XA` | `create_camera_sensing_sg3_isx031c_gmsl2f_h190xa` |
| Sensing | `Sensing/Sensing SG5-IMX490C-5300-GMSL2-H110SA` | `create_camera_sensing_sg5_imx490c_5300_gmsl2_h110sa` |
| Sensing | `Sensing/Sensing SG8S-AR0820C-5300-G2A-H120YA` | `create_camera_sensing_sg8s_ar0820c_5300_g2a_h120ya` |
| Sensing | `Sensing/Sensing SG8S-AR0820C-5300-G2A-H30YA` | `create_camera_sensing_sg8s_ar0820c_5300_g2a_h30ya` |
| Sensing | `Sensing/Sensing SG8S-AR0820C-5300-G2A-H60SA` | `create_camera_sensing_sg8s_ar0820c_5300_g2a_h60sa` |
| SICK | `SICK/Inspector83x` | `create_camera_inspector83x` |
| SICK | `SICK/InspectorP61x` | `create_camera_inspectorp61x` |
| SICK | `SICK/safeVisionary2` | `create_camera_safevisionary2` |
| SICK | `SICK/Visionary-T Mini` | `create_camera_visionary_t_mini` |
| Stereolabs | `Stereolabs/ZED_X` | `create_camera_zed_x` |

예:

```text
window_menu_trigger(menu_path="Create/Sensors/Camera/and/Depth/Sensors/RealSense/Realsense D455")
window_menu_trigger(menu_path="Create/Sensors/Camera/and/Depth/Sensors/Stereolabs/ZED_X")
```

## Physics Sensors

| Sensor | Full path | Onclick action |
|---|---|---|
| Contact Sensor | `Create/Sensors/Contact Sensor` | `["isaacsim.sensors.physics.ui", "create_contact_sensor"]` |
| Imu Sensor | `Create/Sensors/Imu Sensor` | `["isaacsim.sensors.physics.ui", "create_imu_sensor"]` |
| Solid State Physics Raycast Sensor | `Create/Sensors/Physics/Raycast/Sensor/Solid State Physics Raycast Sensor` | `["isaacsim.sensors.physics.ui", "create_solid_state_physics_raycast_sensor"]` |
| Rotating Physics Raycast Sensor | `Create/Sensors/Physics/Raycast/Sensor/Rotating Physics Raycast Sensor` | `["isaacsim.sensors.physics.ui", "create_rotating_physics_raycast_sensor"]` |
| Beam Curtain Physics Raycast Sensor | `Create/Sensors/Physics/Raycast/Sensor/Beam Curtain Physics Raycast Sensor` | `["isaacsim.sensors.physics.ui", "create_beam_curtain_physics_raycast_sensor"]` |

## PhysX Lidar and LightBeam

| Category | Full path | Onclick action |
|---|---|---|
| PhysX Lidar | `Create/Sensors/PhysX/Lidar/Rotating` | `["isaacsim.sensors.physx.ui", "create_physx_lidar_rotating"]` |
| PhysX Lidar | `Create/Sensors/PhysX/Lidar/Generic` | `["isaacsim.sensors.physx.ui", "create_physx_lidar_generic"]` |
| LightBeam Sensor | `Create/Sensors/LightBeam/Sensor/Generic` | `["isaacsim.sensors.physx.ui", "create_lightbeam_generic"]` |
| LightBeam Sensor | `Create/Sensors/LightBeam/Sensor/Tashan TS-F-A` | `["isaacsim.sensors.physx.ui", "create_lightbeam_tashan_ts_f_a"]` |

## RTX Lidar

Base path: `Create/Sensors/RTX/Lidar/{Vendor}/{Model}`
Action extension: `isaacsim.sensors.rtx.ui`

| Vendor | Model | Action id |
|---|---|---|
| HESAI | `XT32 SD10` | `create_lidar_HESAI_XT32_SD10` |
| NVIDIA | `Example Rotary 2D` | `create_lidar_Example_Rotary_2D` |
| NVIDIA | `Example Rotary` | `create_lidar_Example_Rotary` |
| NVIDIA | `Example Solid State` | `create_lidar_Example_Solid_State` |
| NVIDIA | `Simple Example Solid State` | `create_lidar_Simple_Example_Solid_State` |
| Ouster | `OS0` | `create_lidar_OS0` |
| Ouster | `OS1` | `create_lidar_OS1` |
| Ouster | `OS2` | `create_lidar_OS2` |
| Ouster | `VLS 128` | `create_lidar_Ouster_VLS_128` |
| SICK | `LMS4000` | `create_lidar_SICK_LMS4000` |
| SICK | `LMS5xx` | `create_lidar_SICK_LMS5xx` |
| SICK | `LRS4000` | `create_lidar_SICK_LRS4000` |
| SICK | `microScan3` | `create_lidar_SICK_microScan3` |
| SICK | `MRS1000` | `create_lidar_SICK_MRS1000` |
| SICK | `multiScan100` | `create_lidar_SICK_multiScan100` |
| SICK | `nanoScan3` | `create_lidar_SICK_nanoScan3` |
| SICK | `picoScan100` | `create_lidar_SICK_picoScan100` |
| SICK | `TIM781` | `create_lidar_SICK_TIM781` |
| Slamtec | `RPLIDAR S2E` | `create_lidar_Slamtec_RPLIDAR_S2E` |
| ZVISION | `ML30S` | `create_lidar_ZVISION_ML30S` |
| ZVISION | `MLXS` | `create_lidar_ZVISION_MLXS` |

예:

```text
window_menu_trigger(menu_path="Create/Sensors/RTX/Lidar/NVIDIA/Example Rotary")
window_menu_trigger(menu_path="Create/Sensors/RTX/Lidar/Ouster/VLS 128")
```

## RTX Radar and Acoustic

| Category | Full path | Onclick action |
|---|---|---|
| RTX Radar | `Create/Sensors/RTX/Radar/NVIDIA/Generic RTX Radar` | `["isaacsim.sensors.rtx.ui", "create_rtx_radar"]` |
| RTX Radar | `Create/Sensors/RTX/Radar/TexasInstruments/IWRL6432AOP` | `["isaacsim.sensors.rtx.ui", "create_radar_IWRL6432AOP"]` |
| RTX Acoustic | `Create/Sensors/RTX/Acoustic/NVIDIA/Generic RTX Acoustic` | `["isaacsim.sensors.rtx.ui", "create_rtx_acoustic"]` |

## Robot-with-Sensors Preset

`Create/Robots/Nova Carter with Sensors` 는 Nova Carter base + NVIDIA 공식 sensor 배치 preset 을 생성한다.

| Full path | Onclick action |
|---|---|
| `Create/Robots/Nova Carter with Sensors` | `["isaacsim.gui.menu", "create_robot_nova_carter"]` |

## 현 Extension `sensor_service` vs 이 카탈로그

`sensor_service.py` 의 MCP attach tools 는 반복 가능한 programmatic attachment 를 위해 generic prim/schema 를 만든다.

- RTX camera / depth camera: `UsdGeom.Camera` + `customData.validation_api.sensor_type`
- RTX Lidar: Isaac Sim 6.0 `isaacsim.sensors.experimental.rtx.Lidar.create` 경로의 OmniLidar/schema prim + customData tag
- Contact / IMU: physics sensor 생성자 우선, 미활성 시 Xform fallback

제조사별 intrinsics/preset 이 중요한 경우는 이 문서의 GUI menu action 을 호출한다. 반대로 scenario 반복 검증, mount offset 고정, MCP response 기반 assertion 이 중요한 경우는 `sensor_attach_*` tool 이 더 적합하다.

## 재생성 절차

1. Isaac Sim 6.0 기동 (`kit_app_start` 또는 `scripts/run_process_module_standalone.py start`)
2. `window_menu_list(menu_path="Create")` 호출
3. `items[].path` 중 `Create/Sensors` 또는 `Create/Robots/Nova Carter` 로 시작하는 항목만 필터
4. leaf action 의 `onclick_action` tuple 을 보존해 vendor/model table 로 갱신
5. Isaac Sim SDK / sensor extension / validation_api menu introspection 변경 시 재캡처
