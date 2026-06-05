# usd-mouse-interact (v0.2.1)

Kit Extension verified against the locally-built **KKR USD Composer 0.1.1**
(`apps/kkr_usd_composer.kit`, kit-app-template build, Kit
`110.1.0+main.0.c98fc5cb.local`). Turns the active viewport into an FPS-style
whitelist-picker while the timeline is playing:

- **Mouse-look** — moving the mouse rotates the active camera (yaw + pitch).
  Win32 `user32.GetCursorPos` / `SetCursorPos` 를 ctypes 로 직접 호출 → Isaac Sim
  과 USD Composer 양쪽에서 동작 (Kit appwindow 의 cursor API 노출 여부와 무관).
  Linux / macOS 빌드는 carb.windowing → appwindow API → 0-delta guard 순으로
  fallback.
- **WASD + Q/E** — translates the camera (forward / strafe / vertical).
- **Circular crosshair** — a small white `omni.ui.Circle` (10 px) pinned to the
  viewport centre.
- **Whitelist pick highlight** — `customLayerData["usdMouseInteract"]
  .allowed_prims` 안의 prim 만 hover 시 USD selection 으로 표시.
- **Top-left info panel** — `customLayerData["usdMouseInteract"].descriptions`
  의 사용자 텍스트가 우선, 없으면 prim metadata fallback (kind / displayName).
- **Timeline play / stop** — toggles the whole feature on and off.
- **ESC** — soft-disengage (mouse + key capture stop) without stopping the
  timeline. Re-engage by stopping and replaying the timeline.

This folder holds the **workshop / verification material** (design notes,
tests, captures, helper scripts) for the parent Kit Extension at
`kkr-extensions/omni.mycompany.usd_mouse_interact/`.

## Folder layout

```
kkr-extensions/omni.mycompany.usd_mouse_interact/
├── config/                         — Kit extension manifest
├── omni/mycompany/usd_mouse_interact/
│                                   — extension source
└── workshop/                       — workshop material
    ├── README.md                   — this file
    ├── docs/
    │   ├── design.md               — architecture, components, decisions
    │   └── verification-report.md  — live + unit-test verification results
    ├── tests/
    │   ├── conftest.py
    │   ├── test_camera_math.py
    │   ├── test_input_state.py
    │   ├── test_interaction_state_machine.py
    │   └── test_metadata_store.py
    ├── scripts/
    │   └── save_capture_pair.py    — split window_capture into app + viewport
    └── captures/                   — verification screenshots (4 steps x 2)
```

## Install / enable inside USD Composer

The extension already lives under `kkr-extensions/`, which is passed as a Kit
`--ext-folder` by the default workspace launchers in this repo.

After USD Composer is running you can:

```python
# via MCP (this repo's tools)
extension_activate(ext_id="omni.mycompany.usd_mouse_interact")
```

or, in the Kit UI, **Window → Extensions → Third Party →
omni.mycompany.usd_mouse_interact** → toggle on.

## Quickstart

1. **Dev panel 띄우기** — Extension 활성화 후 `Window → USD Mouse Interact`
   (없으면 `Window → Extensions` 에서 토글). 패널 한 번 뜨면 dock 가능.
2. **Whitelist 작성** — Stage panel 에서 prim 선택 → dev panel **Add** →
   **Save** (3장 *Whitelist 편집* 참조).
3. **Play** — 타임라인 ▶ 누르면 viewport 중앙에 흰 crosshair 출력 + 카메라 캡처
   시작. 이때부터 마우스 이동 → yaw/pitch, **W/A/S/D** → forward/strafe,
   **E/Q** → up/down.
4. **Hover** — whitelist 등록된 prim 위에 crosshair 가 닿으면 (a) USD selection
   에 표시 + (b) viewport 좌상단에 InfoOverlay (제목 + 설명) 출력.
5. **해제** — **Stop** (▪) 또는 **Esc**. ▪ 누르면 카메라가 Play 직전 위치로
   자동 복원되고, **Esc** 만 누르면 입력 캡처만 풀리고 카메라는 현재 위치
   유지 (다시 잠그려면 ▪ → ▶).

## Camera controls (Play 중에만 활성)

| 입력 | 동작 |
|------|------|
| Mouse 이동 | yaw + pitch (Win32 `SetCursorPos` 로 매 프레임 화면 중앙 복귀) |
| `W` / `S` | forward / backward |
| `A` / `D` | strafe left / right |
| `E` / `Q` | up / down (월드 up-axis 기준) |
| `Esc` | 입력 캡처만 해제 (카메라 위치 유지) |
| Stop (▪) | 캡처 해제 + 카메라 위치 복원 + crosshair / InfoOverlay 제거 |

이동 속도와 마우스 민감도는 dev panel **Tuning** 섹션에서 실시간 조절.

> **알려진 한계 — fly mode 중 텍스트 입력**
> Fly mode active 중에는 `W A S D Q E R` 키가 viewport gizmo 단축키 토글
> (W=Translate, E=Rotate, R=Scale, Q=Select) 을 막기 위해 *consume* 됩니다.
> 부작용으로 dev panel 의 Edit description modal / Stage panel 검색창 /
> Property field 등 다른 widget 에 focus 가 있어도 이 키들은 typing 으로
> 전달되지 않습니다. 텍스트 입력이 필요하면 **Stop** (▪) 또는 **Esc** 로
> fly mode 를 먼저 해제하세요. ESC 자체는 host modal dialog (Save confirm
> 등) 와의 충돌을 피하려 propagate 됩니다.

## Whitelist 편집 (Add / Remove / Clear / Save)

Whitelist 는 *어떤 prim 이 hover 시 highlight + InfoOverlay 대상이 되는지* 를
결정하는 prim path 집합. dev panel 상단 4 버튼으로 관리:

| 버튼 | 동작 | 영향 |
|------|------|------|
| **Add** | Stage 에서 *현재 선택된* prim 들을 whitelist 에 합침 | in-memory 즉시 + Stage 즉시 반영 (controller `reload_metadata` 호출) |
| **Remove** | 선택된 prim 들을 whitelist 에서 제외 + 그 prim 의 description 도 삭제 | 동일 |
| **Clear** | whitelist 와 description 전부 비움 | 동일 |
| **Save** | 현재 in-memory 상태를 다시 한 번 layer customLayerData 에 쓰기 | (보통 Add/Remove 가 자동 저장하므로 명시적 동기화용) |

### 새 prim 을 target 으로 등록하는 표준 흐름

1. **Stage panel** (왼쪽) 에서 target prim 을 클릭. 다중 선택 (Ctrl/Shift) 지원.
2. **dev panel** 의 **Add** 클릭. 패널 중간 status 라벨이
   `1 prim(s) -- 0 described` 식으로 갱신되고, 아래 스크롤 영역에 prim path
   행이 추가됨.
3. *(선택)* 그 행의 **Edit** 버튼으로 description 작성 (다음 절).
4. USD 파일 자체에 영구 저장하려면 USD Composer 의 **File → Save** (Ctrl+S).
   whitelist 는 layer 의 `customLayerData` 안에 같이 직렬화되므로 별도 export
   불필요. (dev panel 의 **Save** 버튼은 layer in-memory 동기화일 뿐 — 디스크
   저장은 Kit 의 File Save 가 맡음.)

### 자손 prim 자동 매칭

화이트리스트 엔트리는 *조상 매칭* 룰을 따른다. 예를 들어
`/World/Robot` 만 등록해도 그 하위의 `/World/Robot/Joint1/Mesh` 에 hover
하면 `/World/Robot` 으로 hit 처리됨 (longest-ancestor 우선). 따라서 큰 그룹은
group prim 하나만 등록하는 것이 효율적.

## Description 편집 (좌상단 InfoOverlay 텍스트)

InfoOverlay 의 `desc` 영역은 다음 우선순위로 결정됨:

1. **사용자 description** — `customLayerData["usdMouseInteract"]
   .descriptions[<hit_path>]` (정확/가장 긴 조상 매칭).
2. **prim metadata fallback** — 위 항목이 비어있으면
   `f"{typeName} — under {parent_path}"` (예: `Cube — under /World`).
3. **invalid prim** — `(unknown prim)`.

### dev panel 에서 description 수정하기

1. dev panel 의 **Whitelist + Descriptions** 섹션에 prim 한 줄당 행이 있음
   (`/World/TestCube`  `Test cu...efault...`  `Edit`).
2. **Edit** 버튼 클릭 → 별도 modal Window (`Edit description -- /<path>`)
   가 뜸.
3. 가운데 multiline `StringField` 에 텍스트 입력. Latin (ASCII) + ASCII
   punctuation 만 정상 렌더링됨 (Kit 110 omni.ui 의 알려진 제약 — 한글/CJK
   는 `?` 박스로 표시되니 영어로 작성 권장).
4. **OK** 누르면 in-memory 와 layer customLayerData 에 즉시 반영. **Cancel**
   은 변경 폐기.
5. 다시 hover → InfoOverlay 의 `desc` 가 즉시 새 텍스트로 갱신됨.

### prim 자체 metadata 만 보여주고 싶을 때

description 을 비워둔 채 (또는 입력 후 빈 문자열로 OK) 두면 fallback 룰이
발동. 이 경우 `Cube — under /World` 같은 자동 라벨이 출력. 빈 문자열을
저장하면 `descriptions` dict 에서 해당 키가 제거됨 (스토리지 절약).

### 직접 USD 편집

에디터에서 customLayerData 를 손으로 쓰는 것도 가능. layer root 에:

```usda
customLayerData = {
    dictionary usdMouseInteract = {
        string[] allowed_prims = ["/World/TestCube", "/World/Robot"]
        dictionary descriptions = {
            string "/World/TestCube" = "Test target cube."
            string "/World/Robot"    = "Franka arm group."
        }
    }
}
```

저장 후 dev panel 에서 **extension 재활성화** (deactivate → activate) 또는
USD Composer 재시작하면 패널이 새 데이터로 다시 로드됨.

## Tuning (Speed / Sensitivity)

dev panel 하단 **Tuning** 섹션의 슬라이더 두 개로 카메라 응답을 즉시 조정:

| 슬라이더 | 범위 | 단위 / 의미 | 기본값 |
|----------|-----|-------------|-------|
| **Speed** | 50 ~ 5000 | translation 속도 (units/sec, USD up-axis 기준) | 500 |
| **Sensitivity** | 1 ~ 100 | 마우스 회전 배율 (내부적으로 `× 0.0001` → 라디안/픽셀) | 25 |

값 변경은 다음 frame 부터 적용 — Stop / Play 사이클 불필요. 메타 룰: USD
Composer / Isaac Sim 양쪽 viewport 가 1 단위 = 1 cm (`metersPerUnit = 0.01`)
씬에서는 Speed 500 ≈ 5 m/s 로 체감되며, 멀리 있는 환경 시연용으로는 1500 ~
3000, 가까운 디테일 검사용으로는 200 ~ 500 정도가 무난.

> 슬라이더는 *세션 내* 값. USD 파일에 저장되지 않으므로 다음 세션에서는
> 기본값 (500 / 25) 으로 다시 시작.

## 데이터 저장 위치

모든 whitelist + description 은 **현재 active stage 의 root layer** 의
`customLayerData["usdMouseInteract"]` 에 저장됨:

```
customLayerData
└── usdMouseInteract
    ├── allowed_prims  : Vt.StringArray  (정렬된 path 리스트)
    └── descriptions   : dict[str, str]  (path → 사용자 텍스트)
```

핵심 규칙:

- **Stage 별 종속** — 다른 USD 파일을 열면 그 파일의 customLayerData 만
  읽음. extension global 저장소가 따로 있는 게 아님.
- **Sublayer / reference 무시** — root layer 만 본다. Sublayer 에 있는
  customLayerData 는 무시되니 sublayer 작업 시 주의.
- **저장 == File Save** — dev panel 의 **Save** 는 in-memory layer 갱신용.
  실제 디스크 저장은 USD Composer 의 **File → Save** (Ctrl+S) 또는
  **Save As** 가 맡음. 저장 안 한 채 종료하면 잃는다.

## Development

### Run unit tests

```powershell
.venv/Scripts/python.exe -m pytest kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/tests -v
```

### Reload after editing

`.py` changes are picked up by Kit's fswatcher within a few seconds. If a
reload doesn't take effect (Python sys.modules cache), call
`extension_activate(ext_id="omni.mycompany.usd_mouse_interact", reload=True)`.

### Why `omni.mycompany.*`?

USD Composer (Kit-app-template build) only mounts already-registered top-level
namespaces; `omni.kappy.*` and bare `kappy_*` were silently ignored even when
the manifest was found. This is documented in the verification report.
