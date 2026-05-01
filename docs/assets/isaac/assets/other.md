# IsaacLab · Materials · Samples · Sensors — Isaac Sim 5.1 Asset Catalog

`$ISAAC` = `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac`

---

## IsaacLab

루트: `$ISAAC/IsaacLab/` — 강화학습 · 조작 연구용 에셋.

| 폴더 | 용도 |
|---|---|
| ActuatorNets | 액추에이터 신경망 모델 |
| Arena | RL 아레나 환경 |
| AutoMate | 자동화 조립 태스크 |
| Controllers | 제어기 USD |
| Factory | 공장 환경 (RL) |
| Materials | IsaacLab 전용 재질 |
| Mimic | Mimic 태스크 (Packing 등) |
| Objects | RL 오브젝트 |
| Policies | 사전학습 정책 파일 |
| PretrainedCheckpoints | 체크포인트 |
| Robots | IsaacLab 전용 로봇 |
| TacSL | Tactile Sim-to-Real |
| Tests | 테스트 씬 |

---

## Materials

루트: `$ISAAC/Materials/`

| 폴더 | 용도 |
|---|---|
| AprilTag | AprilTag 마커 재질 |
| Base | 기본 재질 라이브러리 |
| Isaac | Isaac 전용 재질 |
| Textures | 텍스처 파일 |
| vMaterials_2 | NVIDIA vMaterials 2.0 라이브러리 |

---

## Samples

루트: `$ISAAC/Samples/` — 데모·예제 씬.

| 폴더 | 내용 |
|---|---|
| AnimRobot | 애니메이션 로봇 예제 |
| Cortex | Cortex 예제 |
| DR | Domain Randomization 예제 |
| Examples | 일반 예제 씬 |
| Groot | Groot 행동 트리 예제 |
| Leonardo | Leonardo 예제 |
| NvBlox | NvBlox 3D 재구성 예제 |
| OmniGraph | OmniGraph 예제 |
| OmniIsaacGymEnvs | OpenAI Gym 환경 |
| Policies | 정책 예제 |
| ROS2 | ROS2 통합 예제 (`Carter_ROS.usd` 등) |
| Replicator | 데이터 생성 예제 |
| Rigging | 리깅 예제 |
| Scene_Blox | 씬 블록스 |

---

## Sensors

루트: `$ISAAC/Sensors/` — 센서 USD 에셋 (RTX Lidar/Camera 설정 파일).

| 벤더 | 센서 유형 |
|---|---|
| HESAI | RTX Lidar (Pandar series) |
| Intel | RealSense RGB-D 카메라 |
| LeopardImaging | 카메라 모듈 |
| NVIDIA | NVIDIA 센서 |
| Orbbec | RGB-D 카메라 |
| Ouster | RTX Lidar |
| SICK | Lidar · 카메라 |
| Sensing | 카메라 모듈 (SG2 등) |
| Slamtec | 2D Lidar (RPLIDAR) |
| Stereolabs | ZED 스테레오 카메라 |
| Tashan | LightBeam 센서 |
| Velodyne | RTX Lidar |
| ZVISION | RTX Lidar |

> `Create > Sensors` 메뉴 (prim 생성)와 USD 직접 로드 두 방법 모두 가능.  
> `window_menu_trigger` menu_path 전체: `docs/references/sensor_menu_catalog.md`
