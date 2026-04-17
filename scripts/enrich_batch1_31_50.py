import json
import datetime as dt
from pathlib import Path

p = Path("docs/references/extensions.json")
d = json.loads(p.read_text(encoding="utf-8"))
NOW = dt.datetime.now(dt.UTC).isoformat()

def fe(name):
    for e in d["extensions"]:
        if e["name"] == name:
            return e
    return None

# Entry 31: isaacsim.core.nodes
e = fe("isaacsim.core.nodes")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 공통 OmniGraph 노드 모음 — ArticulationController, 오도메트리, 카메라 파라미터, Transform 노드를 제공한다."
e["key_symbols"] = [
    {"name": "BaseResetNode", "kind": "class", "desc": "시뮬레이션 리셋 시 호출되는 OmniGraph 노드 기본 클래스"},
    {"name": "BaseWriterNode", "kind": "class", "desc": "데이터 기록용 OmniGraph 노드 기본 클래스"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions"]
e["mcp_extension_idea"] = "N/A — OmniGraph 노드 라이브러리, 간접적으로 robot_control tool에서 활용"
e["enriched_at"] = NOW

# Entry 32: isaacsim.core.prims
e = fe("isaacsim.core.prims")
e["enrichment_status"] = "enriched"
e["summary"] = "USD Prim 상태를 읽고 쓰는 저수준 API — RigidPrim, Articulation, SingleArticulation, GeometryPrim 등 안정적 Prim 래퍼를 제공한다."
e["key_symbols"] = [
    {"name": "SingleArticulation", "kind": "class", "desc": "단일 관절 로봇 Prim 래퍼 — 관절 위치/속도/힘 읽기/쓰기"},
    {"name": "RigidPrim", "kind": "class", "desc": "리짓 바디 Prim 배치용 래퍼 (배치 연산)"},
    {"name": "SingleRigidPrim", "kind": "class", "desc": "단일 리짓 바디 Prim 래퍼"},
]
e["testbed_refs"] = [
    "testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions",
    "testbed-snapshot/03-api-patterns.md#62-articulation"
]
e["mcp_extension_idea"] = "N/A — Phase B 로봇 제어 MCP tool의 핵심 의존 라이브러리 (SingleArticulation 래핑)"
e["enriched_at"] = NOW

# Entry 33: isaacsim.core.simulation_manager
e = fe("isaacsim.core.simulation_manager")
e["enrichment_status"] = "enriched"
e["summary"] = "시뮬레이션 상태 제어/질의, 프레임 콜백 등록, 물리 스텝 관리를 담당하는 핵심 Extension."
e["key_symbols"] = [
    {"name": "SimulationManager", "kind": "class", "desc": "시뮬레이션 실행 상태 제어 및 콜백 관리 싱글톤"},
    {"name": "IsaacEvents", "kind": "class", "desc": "Isaac Sim 이벤트 상수 정의 (physics_step, simulation_step 등)"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions"]
e["mcp_extension_idea"] = "N/A — already covered by simulation_play, simulation_pause, simulation_stop, simulation_get_status"
e["enriched_at"] = NOW

# Entry 34: isaacsim.core.throttling
e = fe("isaacsim.core.throttling")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim의 물리/렌더링 루프 스로틀링 동작을 제어하는 Extension — 비동기 및 수동 모드 전환을 지원한다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions"]
e["mcp_extension_idea"] = "sim_set_throttle(mode) — 시뮬레이션 스로틀링 모드(async/manual/normal)를 전환하는 MCP tool"
e["enriched_at"] = NOW

# Entry 35: isaacsim.core.utils
e = fe("isaacsim.core.utils")
e["enrichment_status"] = "enriched"
e["summary"] = "USD Stage, Prim, 수학(회전/행렬), 물리, 렌더링, carb 설정 등 Isaac Sim 전반의 유틸리티 함수를 제공하는 Extension."
e["key_symbols"] = [
    {"name": "stage", "kind": "submodule", "desc": "add_reference_to_stage, is_stage_loading 등 Stage 조작 함수"},
    {"name": "numpy.rotations", "kind": "submodule", "desc": "쿼터니언/오일러/회전 행렬 변환 유틸"},
    {"name": "extensions", "kind": "submodule", "desc": "enable_extension, get_extension_path 유틸 함수"},
]
e["testbed_refs"] = [
    "testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions",
    "testbed-snapshot/03-api-patterns.md#1-essential-import-pattern"
]
e["mcp_extension_idea"] = "N/A — 유틸리티 라이브러리, stage_load_usd 등 기존 tool에서 활용 중"
e["enriched_at"] = NOW

# Entry 36: isaacsim.core.version
e = fe("isaacsim.core.version")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 버전 정보 및 빌드 메타데이터를 질의하는 Extension."
e["key_symbols"] = [
    {"name": "get_version", "kind": "function", "desc": "Isaac Sim 버전 튜플(major, minor, patch, build 등) 반환"},
    {"name": "parse_version", "kind": "function", "desc": "버전 문자열을 Version 객체로 파싱"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#core-foundation-11-extensions"]
e["mcp_extension_idea"] = "isaac_get_version() — 실행 중인 Isaac Sim의 버전 정보를 반환하는 MCP tool"
e["enriched_at"] = NOW

# Entry 37: isaacsim.cortex.behaviors
e = fe("isaacsim.cortex.behaviors")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Cortex 핵심 예제용 행동 라이브러리 — 픽앤플레이스, 빈 채우기 등 샘플 로봇 행동 스크립트를 제공한다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#cortex-framework-2-extensions"]
e["mcp_extension_idea"] = "cortex_behavior_run(behavior_name, robot_prim) — Cortex 행동 스크립트를 실행하는 MCP tool (Phase C)"
e["enriched_at"] = NOW

# Entry 38: isaacsim.cortex.framework
e = fe("isaacsim.cortex.framework")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Cortex 로봇 행동 프레임워크 — Commander, CortexWorld, MotionCommander, DecisionFramework를 통해 반응적 행동 트리를 구현한다."
e["key_symbols"] = [
    {"name": "CortexWorld", "kind": "class", "desc": "Cortex 행동 로봇을 위한 World 확장 클래스"},
    {"name": "MotionCommander", "kind": "class", "desc": "로봇 암 동작 명령(IK, 경로) 실행기"},
    {"name": "Robot", "kind": "class", "desc": "Cortex 프레임워크 내 로봇 에이전트 기본 클래스"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#cortex-framework-2-extensions"]
e["mcp_extension_idea"] = "cortex_execute_behavior(cortex_script_path, robot_prim) — Cortex 행동 스크립트를 Isaac Sim에서 실행하는 MCP tool (Phase C)"
e["enriched_at"] = NOW

# Entry 39: isaacsim.examples.browser
e = fe("isaacsim.examples.browser")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 공식 예제를 탐색하고 로드하는 브라우저 UI Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#examples-4-extensions"]
e["mcp_extension_idea"] = "N/A — 예제 탐색 UI 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 40: isaacsim.examples.extension
e = fe("isaacsim.examples.extension")
e["enrichment_status"] = "enriched"
e["summary"] = "다양한 개발 워크플로우(Standalone, Extension, OmniGraph)용 Extension 템플릿 생성 UI 도구."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#examples-4-extensions"]
e["mcp_extension_idea"] = "N/A — Extension 템플릿 생성 UI 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 41: isaacsim.examples.interactive
e = fe("isaacsim.examples.interactive")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 대화형 예제 모음 — Franka 픽앤플레이스, Kaya 게임패드, 경로 계획, 사족보행 등 21개 인터랙티브 시나리오를 제공한다."
e["key_symbols"] = [
    {"name": "hello_world", "kind": "submodule", "desc": "Hello World 기본 예제"},
    {"name": "franka", "kind": "submodule", "desc": "Franka 로봇 팔 픽앤플레이스 예제"},
    {"name": "pick_place", "kind": "submodule", "desc": "범용 픽앤플레이스 예제"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#examples-4-extensions"]
e["mcp_extension_idea"] = "example_run(example_name) — 인터랙티브 예제를 Isaac Sim에서 실행하고 결과를 캡처하는 MCP tool"
e["enriched_at"] = NOW

# Entry 42: isaacsim.examples.ui
e = fe("isaacsim.examples.ui")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim UI 컴포넌트 사용법을 보여주는 예제 Extension — 슬라이더, 버튼, 그래프 등 Core UI 요소 데모를 포함한다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#examples-4-extensions"]
e["mcp_extension_idea"] = "N/A — UI 예제 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 43: isaacsim.gui.components
e = fe("isaacsim.gui.components")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim UI 개발을 위한 핵심 UI 컴포넌트 라이브러리 — Button, CheckBox, DropDown, FloatField 등 래퍼 위젯과 스크린 출력 유틸을 제공한다."
e["key_symbols"] = [
    {"name": "UIWidgetWrapper", "kind": "class", "desc": "모든 UI 위젯 래퍼의 추상 기본 클래스"},
    {"name": "Button", "kind": "class", "desc": "클릭 콜백을 지원하는 버튼 위젯 래퍼"},
    {"name": "DropDown", "kind": "class", "desc": "선택 목록 드롭다운 위젯 래퍼"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#gui-ui-5-extensions"]
e["mcp_extension_idea"] = "N/A — UI 컴포넌트 라이브러리, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 44: isaacsim.gui.content_browser
e = fe("isaacsim.gui.content_browser")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 콘텐츠(USD, 텍스처, 로봇) 파일을 로컬/원격에서 탐색하는 콘텐츠 브라우저 UI Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#gui-ui-5-extensions"]
e["mcp_extension_idea"] = "N/A — 콘텐츠 브라우저 UI 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 45: isaacsim.gui.menu
e = fe("isaacsim.gui.menu")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 메뉴 시스템 — Create, Sensors, Replicator 등 Isaac 전용 메뉴 항목을 등록하고 관리하는 Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#gui-ui-5-extensions"]
e["mcp_extension_idea"] = "N/A — 메뉴 시스템 내부, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 46: isaacsim.gui.property
e = fe("isaacsim.gui.property")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 전용 속성 패널 UI 유틸 — Prim 속성 뷰어에 Isaac 전용 위젯 및 헬퍼를 추가하는 Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#gui-ui-5-extensions"]
e["mcp_extension_idea"] = "N/A — 속성 패널 UI 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 47: isaacsim.gui.sensors.icon
e = fe("isaacsim.gui.sensors.icon")
e["enrichment_status"] = "enriched"
e["summary"] = "Viewport에서 센서 Prim을 시각적 아이콘으로 표시하는 GUI Extension — 카메라, LiDAR 등 센서 위치를 직관적으로 파악할 수 있다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#gui-ui-5-extensions"]
e["mcp_extension_idea"] = "N/A — 센서 아이콘 시각화 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 48: isaacsim.replicator.agent.core
e = fe("isaacsim.replicator.agent.core")
e["enrichment_status"] = "enriched"
e["summary"] = "액터(캐릭터/로봇) 시뮬레이션 및 합성 데이터 생성의 핵심 Extension — AgentManager를 통해 캐릭터/로봇을 스크립트로 제어하고 SDG를 수행한다."
e["key_symbols"] = [
    {"name": "AgentData", "kind": "class", "desc": "캐릭터 레이블, prim 경로, 메타데이터를 매핑하는 에이전트 데이터 컨테이너"},
    {"name": "AgentManager", "kind": "class", "desc": "씬 내 에이전트(캐릭터/로봇) 생명주기 및 시뮬레이션 제어"},
]
e["testbed_refs"] = []
e["mcp_extension_idea"] = "agent_spawn(character_label, prim_path, command_file) — 액터를 씬에 생성하고 명령 파일로 제어하는 MCP tool (Phase C)"
e["enriched_at"] = NOW

# Entry 49: isaacsim.replicator.agent.ui
e = fe("isaacsim.replicator.agent.ui")
e["enrichment_status"] = "enriched"
e["summary"] = "액터 시뮬레이션 및 합성 데이터 생성(SDG) 설정을 위한 UI Extension."
e["key_symbols"] = []
e["testbed_refs"] = []
e["mcp_extension_idea"] = "N/A — UI 래퍼 전용; 핵심 기능은 isaacsim.replicator.agent.core에 있음"
e["enriched_at"] = NOW

# Entry 50: isaacsim.replicator.behavior
e = fe("isaacsim.replicator.behavior")
e["enrichment_status"] = "enriched"
e["summary"] = "합성 데이터 생성(SDG)용 랜덤화 및 이벤트 행동 스크립트 라이브러리 — LightRandomizer, LocationRandomizer, TextureRandomizer 등을 제공한다."
e["key_symbols"] = [
    {"name": "LightRandomizer", "kind": "class", "desc": "조명 색상/강도를 SDG 프레임마다 무작위 변경"},
    {"name": "LocationRandomizer", "kind": "class", "desc": "오브젝트 위치를 지정 범위 내에서 무작위 배치"},
    {"name": "TextureRandomizer", "kind": "class", "desc": "머티리얼 텍스처를 프레임마다 무작위 교체"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#replicator-synthetic-data-11-extensions"]
e["mcp_extension_idea"] = "sdg_randomize(scene_prim, behaviors, frame_count) — 랜덤화 행동 스크립트를 적용하여 합성 데이터를 생성하는 MCP tool"
e["enriched_at"] = NOW

print("Entries 31-50 done")
p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
print("Saved extensions.json")
