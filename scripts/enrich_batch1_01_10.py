import json
import datetime as dt
from pathlib import Path

p = Path("docs/references/extensions.json")
d = json.loads(p.read_text(encoding="utf-8"))
NOW = "2026-04-17T15:01:29.841442+00:00"  # same timestamp as others for consistency

def fe(name):
    for e in d["extensions"]:
        if e["name"] == name:
            return e
    return None

# Entry 1: carb.audio — skip internal_utility
e = fe("carb.audio")
e["enrichment_status"] = "skipped"
e["skipped_reason"] = "internal_utility"
e["summary"] = "N/A — 저수준 Omniverse 오디오 런타임 플러그인 (내부 유틸)."
e["mcp_extension_idea"] = "N/A — internal utility"
e["enriched_at"] = NOW

# Entry 2: carb.windowing.plugins — skip internal_utility
e = fe("carb.windowing.plugins")
e["enrichment_status"] = "skipped"
e["skipped_reason"] = "internal_utility"
e["summary"] = "N/A — 저수준 Omniverse 윈도잉/입력 플러그인 (내부 유틸)."
e["mcp_extension_idea"] = "N/A — internal utility"
e["enriched_at"] = NOW

# Entry 3: isaacsim.action_and_event_data_generation.setup
e = fe("isaacsim.action_and_event_data_generation.setup")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 액션/이벤트 합성 데이터 생성 앱의 설정 Extension — UI 레이아웃, Quicklayout, 메뉴 초기화를 담당한다."
e["key_symbols"] = [
    {"name": "ActionAndEventDataGenerationSetupExtension", "kind": "class", "desc": "앱 설정 Extension 진입점, 레이아웃 및 메뉴 초기화"}
]
e["testbed_refs"] = []
e["mcp_extension_idea"] = "N/A — 앱 초기화 전용 설정 Extension, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 4: isaacsim.anim.robot
e = fe("isaacsim.anim.robot")
e["enrichment_status"] = "enriched"
e["summary"] = "캡처된 시뮬레이션 모션 데이터를 재생하여 로봇을 사실적으로 애니메이션하는 Extension — 물리 시뮬레이션 없이 정확한 로봇 동작을 재현한다."
e["key_symbols"] = [
    {"name": "DriveBase", "kind": "class", "desc": "모든 드라이브 유형의 추상 기본 클래스"},
    {"name": "OmniDirectionalDrive", "kind": "class", "desc": "전방향(Omni-Directional) 에이전트 드라이브 구현"},
    {"name": "DifferentialDrive", "kind": "class", "desc": "차동 구동(Differential Drive) 에이전트 드라이브 구현"},
]
e["testbed_refs"] = []
e["mcp_extension_idea"] = "robot_play_animation(prim_path, command_file) — isaacsim.anim.robot 모션 파일 재생으로 물리 없이 로봇 애니메이션 제어"
e["enriched_at"] = NOW

# Entry 5: isaacsim.app.about
e = fe("isaacsim.app.about")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim About 다이얼로그 — 앱/빌드 버전 정보를 표시하는 UI Extension이다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#app-infrastructure-3-extensions"]
e["mcp_extension_idea"] = "N/A — About 다이얼로그 전용 UI, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 6: isaacsim.app.compatibility_check
e = fe("isaacsim.app.compatibility_check")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 실행 전 시스템 요구사항(GPU, 드라이버, OS)을 점검하는 호환성 검사 도구 Extension."
e["key_symbols"] = []
e["testbed_refs"] = []
e["mcp_extension_idea"] = "isaac_check_compatibility() — 시스템 호환성 체크 결과를 반환하는 진단용 MCP tool"
e["enriched_at"] = NOW

# Entry 7: isaacsim.app.selector
e = fe("isaacsim.app.selector")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 시작 시 실행할 앱/워크플로우를 선택하는 런처 UI Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#app-infrastructure-3-extensions"]
e["mcp_extension_idea"] = "N/A — 런처 UI 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 8: isaacsim.app.setup
e = fe("isaacsim.app.setup")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 초기 환경 설정(레이아웃, 메뉴, 단축키 등)을 수행하는 앱 설정 Extension."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#app-infrastructure-3-extensions"]
e["mcp_extension_idea"] = "N/A — 앱 초기화 전용, MCP tool 대상 아님"
e["enriched_at"] = NOW

# Entry 9: isaacsim.asset.browser
e = fe("isaacsim.asset.browser")
e["enrichment_status"] = "enriched"
e["summary"] = "Isaac Sim 에셋(로봇, 오브젝트, 환경 USD 파일)을 탐색/미리보기하는 브라우저 UI Extension."
e["key_symbols"] = [
    {"name": "AssetBrowserExtension", "kind": "class", "desc": "에셋 브라우저 Extension 진입점"},
    {"name": "get_instance", "kind": "function", "desc": "AssetBrowserExtension 싱글톤 인스턴스 반환"},
]
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#asset-browsing-generation-5-extensions"]
e["mcp_extension_idea"] = "asset_search(query, category) — 에셋 브라우저에서 로봇/환경 USD 파일 검색 및 경로 반환"
e["enriched_at"] = NOW

# Entry 10: isaacsim.asset.exporter.urdf
e = fe("isaacsim.asset.exporter.urdf")
e["enrichment_status"] = "enriched"
e["summary"] = "USD Stage의 로봇 모델을 URDF 형식으로 내보내는 Export Extension — 관절, 링크, 시각 메시를 변환한다."
e["key_symbols"] = []
e["testbed_refs"] = ["testbed-snapshot/02-extension-catalog.md#asset-importexport-5-extensions"]
e["mcp_extension_idea"] = "urdf_export(usd_prim_path, output_path) — USD 로봇 Prim을 URDF 파일로 내보내는 MCP tool"
e["enriched_at"] = NOW

print("Entries 1-10 done")
p.write_text(json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
print("Saved extensions.json")
