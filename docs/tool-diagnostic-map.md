<!-- Parent: ../CLAUDE.md -->
<!-- Scope: 에러/실패 발생 시 코드 수정 전에 가설을 read-only MCP tool 로 검증 — 디버깅 첫 read -->
# Tool Diagnostic Map

에러 / 예상외 동작 발생 시 **수정 → 시도 cycle 전에** 이 문서 read.
같은 가설로 코드 수정 + 시도가 2회 fail 하면 → 가설 재검토 강제 (반복 시도 금지).

## 진단 워크플로 (5초 cycle vs 10분 cycle)

1. **Grep error message**: project source + Kit source (`C:/workspace/isaac-sim-standalone-*/exts/`) — 발생 line 식별, 가설 좁히기
2. **MCP read-only 진단 tool 호출** (각 ~5초) — 아래 표로 가설 검증
3. **환경 의존성 의심** 시: `extension_search/activate` (lazy install) + `content_browse` (URL 검증) + filesystem 직접
4. **가설 확정 후에만** 코드 수정 시도. 같은 가설 2회 fail = 가설 폐기

## 의문 → MCP tool 역색인

| 의문 | 1차 MCP tool | 응답 필드 / 검증 method |
|------|------------|---------------------|
| 이 prim 이 articulation? | `robot_load(usd_url, prim_path)` | `has_articulation` |
| 이 USD URL 실존? | `content_browse(parent_dir)` | `entries[]` 안 항목 (S3 catalog) |
| Ext 등록? | `extension_search(keyword)` | result count > 0 |
| Ext 활성화? | `extension_get_info(ext_id)` | `info.enabled` / `info.path` |
| Ext lazy install + 활성화? | `extension_activate(ext_id)` | `was_enabled` / `enabled` |
| Widget 클릭 effect? | `extension_ui_invoke` post-state + `extension_get_ui_tree` 의 label change |
| Prim 존재? | `stage_assert_prim_exists(prim_path)` | `passed` |
| Prim attribute 값? | `stage_assert_property(prim_path, property_name)` (expected 생략) | `actual.value` |
| Stage 전체 prim? | `stage_capture_snapshot` → `data.prims` dict (응답 큼 — Bash + jq/python 권장) |
| Timeline state? | `simulation_get_status` | `is_playing` / `current_time` |
| Window 존재? | `window_list` | `windows[].class_name=GLFW30` |
| Window UI tree? | `extension_get_ui_tree(window=)` | `widgets[]` (USD Composer 는 `omni.kit.ui_test` 부재 → 0 widgets + walk_error) |
| Visual 상태? | `viewport_capture` / `window_capture` + `Read` tool | PNG (R3) |
| Kit menu 항목? | `window_menu_list` / `window_menu_trigger` | `items[]` |
| MDL deadlock? | `simulation_get_status` 92s timeout | → `runbooks/kit-stdin-deadlock.md` |

## Extension 내부 진행 stamping 패턴

`extension_capture_logs` 가 no-op (`invariants/usd-load.md`) 인 환경에서 ext 내부
진행을 외부 polling 하려면 USD attribute stamp:

```python
# extension code (진행 단계마다)
from pxr import Sdf, UsdGeom
prim = UsdGeom.Xform.Define(stage, Sdf.Path("/World/MyExtStatus")).GetPrim()
prim.CreateAttribute("stage", Sdf.ValueTypeNames.String).Set("step_5_done")
prim.CreateAttribute("last_error", Sdf.ValueTypeNames.String).Set(str(exc))
```

```python
# MCP polling (외부)
stage_assert_property(prim_path="/World/MyExtStatus", property_name="stage")
# response.actual.value 로 현재 단계 read
```

## Self-test pattern (UI automation 없는 환경)

USD Composer 등 `omni.kit.ui_test` 부재 → `extension_ui_invoke` widget click 불가
(`extension_get_ui_tree` widgets=0 + walk_error 로 표면화).

대안: extension `on_startup` 에서 self-test coroutine schedule, 결과를
`/World/<Ext>SelfTestResult` prim attribute 로 stamp → MCP `stage_assert_property`
read. Side-effect (예: highlight 후 restore) 와 검증 race 회피 위해 stamp 직후
검증 state 분리 (highlighted_path = None 으로 reset 등).

## 가설 검증 비용 비교

| 동작 | 시간 |
|------|------|
| MCP read-only 호출 1회 | ~5 s |
| Grep (project / Kit source) | ~5 s |
| Standalone python 검증 (`scripts/run_*_standalone.py`) | ~10 s |
| Kit restart + build + play + start cycle | ~10 min |

→ 코드 수정 전 read-only 검증 1회로 cycle 1회 절약. 4-5회 시도 누적 1시간 vs 25 s.

## 관련 경계

- 전체 MCP tool signature: `tool-catalog.md` (auto-generated, signature 위주)
- Process lifecycle / hang: `invariants/process-lifecycle.md` + `runbooks/cold-boot-timeout.md`
- USD load 함정 (S3 URL / MDL deadlock): `invariants/usd-load.md`
- Ext reload (sys.modules cleanup 한계): `invariants/ext-reload.md`
- Multi-app port / profile: `invariants/multi-app.md`
- Kit SDK domain 함정: `../kkr-extensions/docs/kit-sdk-pitfalls.md`
