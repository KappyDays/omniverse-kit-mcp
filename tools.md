# Isaac-sim-MCP — Tool Roadmap (미래 추가 기능)

> 현재 서피스: **107 MCP tools + 3 resources** (2026-04-21 기준). 이 문서는 **다음에 추가될 도구 후보** 를 필수 / 추천 / 비추천으로 분류. 결정 시 참고 자료:
>
> - `docs/references/extensions-catalog.md` — Isaac Sim 5.1 전체 ext 카탈로그 (624 ext)
> - `docs/references/testbed-snapshot/` — NVIDIA 공식 문서 스냅샷 + API 패턴
> - Isaac Sim 5.1.0 공식 docs: https://docs.isaacsim.omniverse.nvidia.com/5.1.0/

분류 기준:
- **필수 (Must-Have)** — 현재 MCP 가 Isaac Sim GUI 를 "자연어로 완전 조작" 하기 위해 **구멍이 있는** 기능. 이 도구가 없으면 특정 사용자 질의를 MCP tool 조합만으로 수행 불가
- **추천 (Recommended)** — 필수는 아니지만 생산성 / 토큰 효율 / 고급 기능 관점에서 가치 있음
- **비추천 (Not Recommended)** — 복잡도 대비 효용 낮음 or 프로젝트 범위 밖

---

## 1. 필수 (Must-Have)

### 1.1 USD Composition Arc 제어
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `stage_create_reference(prim_path, usd_url, position?, rotation?)` | `omni.kit.commands.CreateReferenceCommand` wrap | 현재 `stage_load_usd` 는 Payload 만 생성. Reference arc 는 다름 (strong vs weak opinion) |
| `stage_create_variant(prim_path, variant_set, variant_name)` | UsdShade variant 선택 | SimReady / Nova Carter 같은 multi-variant USD 제어 |
| `stage_add_sublayer(layer_path, position="end")` | `UsdStage.GetRootLayer().subLayerPaths` | Scene layering (override vs base) — 협업 에셋 build 에 필수 |
| `stage_flatten_to_usd(output_path)` | `UsdStage.Flatten()` | Composite scene 을 single-file USD 로 export |

**왜 필수**: 3 Twin PPTX 작업 시 `stage_load_usd` 만 있어서 composition 제어가 불가능했고, SimReady variant 선택을 수동 post-edit 로 처리. Reference / Variant 제어 없이는 "chair 의 spec 을 variant 로 전환해줘" 같은 질의 응답 불가.

### 1.2 고품질 렌더 캡처
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `viewport_capture_pathtracing(spp_target, timeout_s, ...)` | PathTracing 활성 → spp 목표치까지 `rep.capture.render_product` 대기 → capture | 현재 `viewport_capture` 는 단일 프레임 snap. PathTracing 은 수렴까지 N 프레임 필요 |
| `viewport_bind_camera_from_xform(camera_path, target_xform)` | 카메라를 특정 prim 바라보도록 LookAt 자동 | 현재 `viewport_set_active_camera` 는 바인딩만, 방향 설정 수동 필요 |

**왜 필수**: PPTX 작업 시 PathTracing 캡처 수렴 대기 로직을 사용자 코드에서 직접 구현. MCP 가 제공해야 Claude 가 고품질 렌더를 요청 가능.

### 1.3 Timeline / Animation Recording
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `animation_record_start(target_prim, end_frame, fps)` | `omni.kit.commands.SetAnimCurveKeysCommand` → stop key-frame 자동 저장 | 사용자가 "로봇 이동 녹화" 요청 시 timeline 기록 불가 |
| `animation_record_stop()` / `animation_bake_to_usd(output_path)` | 녹화 종료 + USD 에 keyframe 저장 |  |

**왜 필수**: Scenario replay / Digital Twin 시연 영상 생성 시 timeline keyframe 저장 필수. Kit 에 `omni.anim.clip` 있으나 MCP 미노출.

### 1.4 IK — Franka 외 로봇 지원
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `robot_set_ee_target(prim_path, target_pose, robot_description, rmpflow_config)` (확장) | 현재 Franka 전용 → UR10 / Kinova / Kuka RMPflow config 지원 | 현재 비Franka 는 400 skip-candidate |
| `robot_list_rmpflow_configs()` | `isaacsim.robot_motion.motion_generation.load_supported_robot_motion_policy_configs` enumerate | Claude 가 "어느 로봇 IK 가능?" 질의 응답 |

**왜 필수**: NVIDIA 공식으로 Franka / UR10 / Kinova / Kuka 등 여러 RMPflow config 제공. 현재 MCP 는 Franka 만 지원. 다른 로봇 요청 시 "skip-candidate" 응답만 가능.

### 1.5 Stage Units / Up Axis
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `stage_get_units()` / `stage_set_units(meters_per_unit)` | `UsdGeomSetStageMetersPerUnit` | Asset mixing 시 scale 충돌 해결 |
| `stage_get_up_axis()` / `stage_set_up_axis(axis="Z")` | `UsdGeom.SetStageUpAxis` | Y-up vs Z-up asset 혼용 시 필수 |

**왜 필수**: 사용자 asset 이 cm unit / Y-up 이고 Isaac Sim 기본이 m / Z-up 이면 transform 계산 혼란. 현재 MCP 는 이 메타데이터 검사/설정 불가.

---

## 2. 추천 (Recommended)

### 2.1 MCP 레벨 efficiency
| 제안 도구 | 동작 | 예상 효과 |
|---|---|---|
| `tool_batch(calls: list[{tool, args}])` | 여러 tool 을 단일 round-trip 으로 순차 실행 | Claude Code ↔ MCP 왕복 감소 → 토큰 절감 + latency 감소 |
| `scenario_generate_template(workflow_type, output_path)` | "warehouse + robot + sensor + navigate" 같은 pattern 을 YAML 자동 생성 | 사용자가 자주 쓰는 시퀀스를 매 세션 재작성할 필요 없음 |

### 2.2 Replicator / SDG 확장
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `replicator_writer_status(writer_id)` | 출력 파일 수 / 마지막 flush 시각 query | 현재는 file system 직접 조회만 가능 |
| `replicator_domain_randomization(preset, targets)` | `isaacsim.replicator.domain_randomization` 표준 preset (illumination / materials / physics) | Domain gap 테스트 자동화 |
| `replicator_behavior_attach(prim_path, behavior_type)` | `isaacsim.replicator.behavior.ui` wrap — 객체에 frequency + range 설정 | Phase H randomizer 의 GUI 친화 version |

### 2.3 OmniGraph 고급
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `omnigraph_list_nodes(graph_path)` | 현재 graph 의 노드/엣지 목록 introspect | 디버깅 필수 |
| `omnigraph_get_attribute(attr_path)` / `omnigraph_set_attribute(attr_path, value)` | 노드 attribute 값 read/write | OnTick + Counter → Counter 값 읽기 등 |
| `omnigraph_create_ros2_subscriber(topic, msg_type, output_prim)` | ROS2 → Kit 방향 subscription (현재는 publisher 만) | Digital Twin ↔ 실제 로봇 양방향 |

### 2.4 Physics tensors (Isaac Lab 연동 기반)
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `physics_batch_articulation_read(prims, attr="joint_positions")` | `omni.physics.tensors` batched GPU readback | 여러 로봇 동시 제어 시 필수 |
| `physics_batch_articulation_write(prims, attr, values)` | batched write | 동일 |

### 2.5 Content / Asset
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `content_search(query, scope="s3")` | omni.client search index | 현재 browse 만, search 없음 |
| `asset_inspect_usd(url)` | USD 파일의 prim tree + metadata peek (load 없이) | 무거운 asset 을 load 전 검증 |

### 2.6 Isaac Lab 통합 (장기)
| 제안 도구 | 동작 | 근거 |
|---|---|---|
| `isaaclab_run_task(task_name, num_envs)` | Isaac Lab RL task 실행 | 강화학습 training 자동화 |

---

## 3. 비추천 (Not Recommended)

| 도구 후보 | 비추천 사유 |
|---|---|
| **Nucleus server 관리** (`nucleus_create_project`, `nucleus_set_permission`) | 인프라 관리는 별도 Nucleus admin UI 대역. MCP 범위 밖 |
| **VR / AR HMD 제어** (`vr_attach_headset`, `xr_set_pose`) | 사용 케이스 좁음 (교육 용도 제한). 장비 의존 높음 |
| **Docker / Linux container 통합** | 현재 Windows-only 프로젝트 범위. cross-platform 전환 시 재고 |
| **Custom USD Schema 등록** (`usd_register_schema`) | 매우 고급. 일반 사용자 use-case 거의 없음. Kit extension 직접 작성 권장 |
| **DLSS 3.5 고급 설정** (`rtx_set_dlss_quality`, `rtx_set_ray_tracing_bounces`) | 현재 `viewport_set_render_quality` 의 `denoiser` 파라미터로 충분. 세밀 제어 필요시 per-user carb.settings 수동 편집 |
| **Nucleus Live Layer Sync** (`live_layer_join`, `live_layer_broadcast`) | 협업 기능. MCP 를 통한 자연어 조작 시나리오와 mismatch. 수동 UI 가 더 직관적 |
| **Cloud Rendering / Streaming** (`livestream_start`, `cloud_render_submit`) | 별도 인프라 의존. 로컬 Kit 기동이 주 use case |
| **Audio / Voice 입출력** (`audio_play`, `voice_trigger`) | Isaac Sim core 기능과 거리 |
| **Particle System 전용 tool** (`particles_emitter_create`) | omni.particle 미포함 실험적 ext. 지원 불안정 |

---

## 4. 우선순위 제안

Phase I 후보 (다음 세션 ~ 1 주 단위):

1. **Composition arc 제어 (1.1)** + **Stage units (1.5)** → 7 tool. 무거운 asset composition + cross-unit 에셋 mixing 필수
2. **`tool_batch` meta-tool (2.1)** — 단일 tool 추가로 전체 token 효율 개선
3. **고품질 캡처 (1.2)** → 2 tool. PPTX 후속 작업 / 고품질 영상 프리셋 제공

Phase J+ 후보 (중장기):

4. **IK 확장 (1.4)** — RMPflow config 추가 + enumerate tool
5. **Timeline recording (1.3)** — Scenario replay / 시연 영상
6. **OmniGraph introspection (2.3)** — 디버깅 품질 향상
7. **Physics tensors (2.4)** — Isaac Lab 통합 기반

---

## 5. 참고 Extension 카탈로그

각 도구가 의존할 수 있는 Kit extension (from `docs/references/extensions-catalog.md`):

| 도구 그룹 | 대상 extension |
|---|---|
| Composition / USD | `omni.kit.commands`, `omni.usd` (기본) |
| Rendering | `omni.rtx.*` , `omni.kit.viewport.*`, `omni.kit.capture.viewport` |
| Timeline / Anim | `omni.anim.clip`, `omni.anim.graph.core`, `omni.kit.timeline` |
| IK / Motion | `isaacsim.robot_motion.motion_generation`, `isaacsim.robot_motion.lula` |
| Replicator | `isaacsim.replicator.agent.core`, `isaacsim.replicator.behavior.ui`, `omni.replicator.core` |
| OmniGraph | `omni.graph.core`, `omni.graph.action`, `omni.graph.ui` |
| Physics tensors | `omni.physics.tensors`, `isaacsim.core.api` (World) |
| ROS2 | `isaacsim.ros2.bridge` |

---

## 6. 도구 추가 시 따라야 할 체크리스트

새 도구 추가 절차는 root CLAUDE.md 의 "변경 파급 매트릭스" 엔트리 "새 MCP tool (`tools/`)" 행 참조. 요약:

1. Extension REST endpoint (`isaac_extension/.../services/*.py`, `rest_router.py`)
2. MCP client (`src/isaacsim_mcp/clients/isaac_rest_client.py`)
3. Typed request/result (`src/isaacsim_mcp/types/*.py`)
4. Module method (`src/isaacsim_mcp/modules/*_module.py`)
5. `@mcp.tool()` 데코레이터 (`src/isaacsim_mcp/tools/module_tools.py`)
6. Mock client (`tests/conftest.py`)
7. `EXPECTED_*_TOOLS` frozenset 업데이트 (`tests/unit/test_tools_registration.py`)
8. `scripts/verify_mcp_sync.py` 실행 → catalog regen

---

**작성일**: 2026-04-21
**참고 자료**: `docs/references/extensions-catalog.md` · `docs/references/testbed-snapshot/*.md` · Isaac Sim 5.1.0 공식 문서
