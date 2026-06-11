"""Live test for Phase E — WindowModule + NavigationModule + advanced UI demo.

Exercises every new REST endpoint added in Phase E against a running Isaac Sim:

- POST /window/capture                    (window_capture tool)
- GET  /window/list                       (window_list)
- GET  /window/ui_list                    (window_ui_list)
- POST /window/ui_show                    (window_ui_show)
- GET  /window/menu_list                  (window_menu_list)
- POST /window/menu_trigger               (window_menu_trigger)
- POST /extension/logs/clear              (extension_clear_logs)
- GET  /extension/ui_tree?widget_types=…  (expanded _WIDGET_TYPES walk)
- POST /navigation/bake                   (navigation_bake)
- POST /navigation/query_path             (navigation_query_path)
- POST /navigation/add_exclude_volume     (navigation_add_exclude_volume)

And drives the advanced demo extension (`omni.mycompany.ui_demo_advanced`)
through Combo/Slider/CheckBox/Button interactions to prove the expanded
widget enumeration actually walks CollapsableFrame / TreeView / ScrollingFrame.

Every visual artifact is copied into `./docs/artifacts/phase-e/` with a descriptive name.

Usage:
    .venv/Scripts/python.exe scripts/live_test_phase_e.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8111/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_E_DIR = PROJECT_ROOT / "docs/artifacts/phase-e"

DEMO_SIMPLE_EXT = "omni.mycompany.ui_demo"
DEMO_SIMPLE_WINDOW = "UI Demo"
DEMO_ADVANCED_EXT = "omni.mycompany.ui_demo_advanced"
DEMO_ADVANCED_WINDOW = "UI Demo Advanced"


def _post(c: httpx.Client, path: str, *, json=None, params=None, timeout: float = 90.0):
    r = c.post(f"{BASE}{path}", json=json, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get(c: httpx.Client, path: str, *, params=None, timeout: float = 90.0):
    r = c.get(f"{BASE}{path}", params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _copy_capture(src_path: str, dest_name: str) -> str:
    PHASE_E_DIR.mkdir(parents=True, exist_ok=True)
    dest = PHASE_E_DIR / dest_name
    shutil.copy2(src_path, dest)
    return str(dest)


def _save_json(name: str, data) -> str:
    PHASE_E_DIR.mkdir(parents=True, exist_ok=True)
    p = PHASE_E_DIR / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(p)


def _find_widget(widgets: list, predicate) -> dict | None:
    for w in widgets:
        try:
            if predicate(w):
                return w
        except Exception:
            continue
    return None


def _extension_available(c: httpx.Client, ext_id: str) -> bool:
    r = c.post(f"{BASE}/extension/get_info", json={"ext_id": ext_id}, timeout=30.0)
    return r.status_code == 200


def _run_core_without_demo(c: httpx.Client, report: dict, status_ok: bool) -> bool:
    report["steps"]["core_window_list"] = _get(c, "/window/list")
    report["steps"]["core_ui_list_browsers"] = _get(
        c, "/window/ui_list", params={"name_filter": "Browser"},
    )
    report["steps"]["core_menu_list_window"] = _get(
        c, "/window/menu_list", params={"menu_path": "Window"},
    )
    print("[core] window list / ui_list / menu_list captured")

    menu_trigger = _post(c, "/window/menu_trigger", params={
        "menu_path": "Create/Mesh/Cube",
    })
    report["steps"]["core_menu_trigger_cube"] = menu_trigger
    print(f"[core] Create/Mesh/Cube -> created_prims={menu_trigger.get('created_prims')}")

    _post(c, "/simulation/stop")
    _post(c, "/stage/create_prim", json={
        "prim_path": "/World/PhaseE_Chair", "prim_type": "Cube",
        "position": [1.0, 0.0, 0.5],
    })

    bake = _post(
        c, "/navigation/bake",
        params={"volume_scale": "8.0", "timeout_s": "300.0"},
        timeout=360.0,
    )
    report["steps"]["core_nav_bake"] = bake
    print(
        f"[core] navmesh baked: ok={bake.get('ok')} "
        f"area_count={bake.get('area_count')}"
    )
    if not bake.get("ok"):
        print(f"  !! bake not ok: {bake.get('reason')}", file=sys.stderr)
        status_ok = False

    query = _post(
        c, "/navigation/query_path",
        json={
            "start": [0.0, 0.0, 0.0],
            "end": [3.0, 3.0, 0.0],
            "agent_radius": 0.3,
            "agent_height": 1.8,
            "straighten": True,
        },
        timeout=120.0,
    )
    report["steps"]["core_nav_query"] = query
    print(f"[core] query_path ok={query.get('ok')} points={len(query.get('points') or [])}")
    if not query.get("ok"):
        print(f"  !! query_path not ok: {query.get('reason')}", file=sys.stderr)
        status_ok = False

    exclude = _post(
        c, "/navigation/add_exclude_volume",
        params={"prim_path": "/World/PhaseE_Chair", "padding": "0.2"},
        timeout=60.0,
    )
    report["steps"]["core_nav_exclude"] = exclude
    print(
        f"[core] exclude volume -> "
        f"{exclude.get('volume_path') or exclude.get('volume_prim_path')}"
    )
    if not exclude.get("ok"):
        print(f"  !! exclude not ok: {exclude.get('reason')}", file=sys.stderr)
        status_ok = False

    _post(c, "/stage/create_prim", json={
        "prim_path": "/World/PhaseE_Light", "prim_type": "DistantLight",
    })
    _post(c, "/stage/set_property", json={
        "prim_path": "/World/PhaseE_Light",
        "property_name": "inputs:intensity", "value": 3000, "type_hint": "float",
    })
    vp = _post(c, "/viewport/capture", json={
        "viewport_name": "Viewport", "width": 1024, "height": 576,
    })
    dest_vp = _copy_capture(vp["path"], "03_viewport_navmesh_scene.png")
    report["steps"]["core_viewport_snapshot"] = {"artifact": dest_vp}
    print(f"[core] viewport snapshot -> {dest_vp}")

    _post(c, "/extension/logs/clear")
    post_clear = _get(c, "/extension/logs", params={"level": "INFO"})
    report["steps"]["core_post_clear_logs"] = {"count": post_clear.get("count")}
    print(f"[core] post-clear count={post_clear.get('count')}")
    if post_clear.get("count") != 0:
        status_ok = False

    return status_ok


def run() -> int:
    report: dict = {"started_at": time.time(), "steps": {}}
    status_ok = True

    with httpx.Client(timeout=120) as c:
        # 0. Health
        report["steps"]["0_health"] = _get(c, "/health")
        print("[0] health ok")

        # 1. Clear logs — fresh session
        cleared = _post(c, "/extension/logs/clear")
        report["steps"]["1_clear_logs"] = cleared
        print(f"[1] clear_logs removed={cleared.get('removed')}")

        since_ms = int(time.time() * 1000)

        simple_available = _extension_available(c, DEMO_SIMPLE_EXT)
        advanced_available = _extension_available(c, DEMO_ADVANCED_EXT)
        report["steps"]["2_demo_availability"] = {
            DEMO_SIMPLE_EXT: simple_available,
            DEMO_ADVANCED_EXT: advanced_available,
        }
        if not (simple_available and advanced_available):
            print(
                "[2] demo extensions unavailable; skipping demo-only UI steps "
                f"(simple={simple_available}, advanced={advanced_available})",
            )
            status_ok = _run_core_without_demo(c, report, status_ok)
            report["completed_at"] = time.time()
            report["status_ok"] = status_ok
            summary_path = _save_json("phase_e_live_report.json", report)
            print(f"\nSUMMARY -> {summary_path}")
            print(f"Phase E artifacts -> {PHASE_E_DIR}")
            return 0 if status_ok else 1

        # 2. Activate both demo extensions (simple + advanced)
        report["steps"]["2a_activate_simple"] = _post(
            c, "/extension/activate", json={"ext_id": DEMO_SIMPLE_EXT, "reload": False},
        )
        report["steps"]["2b_activate_advanced"] = _post(
            c, "/extension/activate", json={"ext_id": DEMO_ADVANCED_EXT, "reload": False},
        )
        print("[2] activated simple+advanced demo extensions")

        # 3. Show the advanced window and capture a baseline
        shown = _post(c, "/window/ui_show", json={
            "name": DEMO_ADVANCED_WINDOW, "visible": True, "focus": True, "settle_frames": 6,
        })
        report["steps"]["3_ui_show_advanced"] = shown
        print(f"[3] advanced window shown via {shown.get('resolved_via')}")

        cap0 = _post(c, "/window/capture", json={
            "mode": "kit", "settle_frames": 6, "output_format": "png",
        })
        dest0 = _copy_capture(cap0["path"], "01_advanced_initial.png")
        report["steps"]["3_capture_initial"] = {"artifact": dest0}
        print(f"[3] captured advanced initial -> {dest0}")

        # 4. UI tree discovery — expanded _WIDGET_TYPES should find ComboBox,
        # FloatSlider, CheckBox, TreeView, ScrollingFrame, CollapsableFrame, Button, Label
        tree_full = _get(c, "/extension/ui_tree", params={
            "ext_id": DEMO_ADVANCED_EXT, "window": DEMO_ADVANCED_WINDOW,
        })
        report["steps"]["4_ui_tree_full"] = tree_full
        widgets = tree_full.get("widgets") or []
        types_found = sorted({w.get("type") for w in widgets})
        print(f"[4] ui_tree full: {len(widgets)} widgets, types={types_found}")

        for expected_type in (
            "Button", "Label", "ComboBox", "FloatSlider",
            "CheckBox", "TreeView", "ScrollingFrame", "CollapsableFrame",
        ):
            if expected_type not in types_found:
                print(f"  !! missing widget type from full walk: {expected_type}", file=sys.stderr)
                status_ok = False

        # 4b. widget_types override — ask for Button + TreeView only
        tree_override = _get(c, "/extension/ui_tree", params=[
            ("ext_id", DEMO_ADVANCED_EXT),
            ("window", DEMO_ADVANCED_WINDOW),
            ("widget_types", "Button"),
            ("widget_types", "TreeView"),
        ])
        report["steps"]["4b_ui_tree_override"] = tree_override
        override_types = sorted({w.get("type") for w in tree_override.get("widgets", [])})
        print(f"[4b] override types={override_types}")
        if any(t not in {"Button", "TreeView"} for t in override_types):
            print("  !! widget_types override returned unexpected types", file=sys.stderr)
            status_ok = False

        apply_btn = _find_widget(widgets, lambda w: w.get("type") == "Button" and "Apply" in (w.get("label") or ""))
        reset_btn = _find_widget(widgets, lambda w: w.get("type") == "Button" and "Reset" in (w.get("label") or ""))
        mode_combo = _find_widget(widgets, lambda w: w.get("type") == "ComboBox")
        gain_slider = _find_widget(widgets, lambda w: w.get("type") == "FloatSlider")
        enabled_check = _find_widget(widgets, lambda w: w.get("type") == "CheckBox")
        status_label = _find_widget(widgets, lambda w: w.get("type") == "Label" and "Status" in (w.get("label") or ""))

        for name, w in [
            ("Apply button", apply_btn), ("Reset button", reset_btn),
            ("Mode ComboBox", mode_combo), ("Gain FloatSlider", gain_slider),
            ("Enabled CheckBox", enabled_check), ("Status Label", status_label),
        ]:
            if w is None:
                print(f"  !! could not resolve widget: {name}", file=sys.stderr)
                status_ok = False

        # 5. Interact with advanced demo: ComboBox select -> slider move -> uncheck -> apply
        if mode_combo:
            sel = _post(c, "/extension/ui_invoke", json={
                "widget_path": mode_combo["path"], "action": "select", "value": 2,
            })
            report["steps"]["5a_combo_select"] = sel
            print(f"[5a] combo select index=2 -> post value={sel.get('post_state',{}).get('value')}")

        if gain_slider:
            slide = _post(c, "/extension/ui_invoke", json={
                "widget_path": gain_slider["path"], "action": "type", "value": "0.75",
            })
            report["steps"]["5b_slider_type"] = slide
            print(f"[5b] slider gain typed -> post value={slide.get('post_state',{}).get('value')}")

        if enabled_check:
            uncheck = _post(c, "/extension/ui_invoke", json={
                "widget_path": enabled_check["path"], "action": "uncheck",
            })
            report["steps"]["5c_check_uncheck"] = uncheck
            print(f"[5c] checkbox uncheck -> post value={uncheck.get('post_state',{}).get('value')}")

        if apply_btn:
            applied = _post(c, "/extension/ui_invoke", json={
                "widget_path": apply_btn["path"], "action": "click",
            })
            report["steps"]["5d_apply_click"] = applied
            print("[5d] apply clicked")

        cap_after = _post(c, "/window/capture", json={"mode": "kit", "settle_frames": 6})
        dest_after = _copy_capture(cap_after["path"], "02_advanced_after_interactions.png")
        report["steps"]["5_capture_after"] = {"artifact": dest_after}
        print(f"[5] captured advanced after interactions -> {dest_after}")

        # 6. Re-read ui_tree to assert the Status label mutated and the slider value persisted
        tree_final = _get(c, "/extension/ui_tree", params={
            "ext_id": DEMO_ADVANCED_EXT, "window": DEMO_ADVANCED_WINDOW,
        })
        report["steps"]["6_ui_tree_final"] = tree_final
        final_status = _find_widget(
            tree_final.get("widgets", []),
            lambda w: w.get("type") == "Label" and "applied" in (w.get("label") or ""),
        )
        if final_status is None:
            print("  !! Status label did not update after apply", file=sys.stderr)
            status_ok = False
        else:
            print(f"[6] status label -> {final_status.get('label')}")

        # 7. Log capture — assert demo-specific logs are present
        logs = _get(c, "/extension/logs", params={
            "ext_id": DEMO_ADVANCED_EXT, "since_ms": str(since_ms), "level": "INFO",
        })
        report["steps"]["7_capture_logs"] = logs
        log_msgs = [e.get("msg") for e in logs.get("entries", [])]
        print(f"[7] advanced demo logged {logs.get('count')} entries")
        for m in log_msgs[:10]:
            print(f"    - {m}")
        if not any("apply" in m for m in log_msgs):
            print("  !! expected 'apply' entry missing from advanced demo logs", file=sys.stderr)
            status_ok = False

        # 8. Window / menu introspection
        report["steps"]["8_window_list"] = _get(c, "/window/list")
        report["steps"]["8_ui_list_browsers"] = _get(c, "/window/ui_list", params={"name_filter": "Browser"})
        report["steps"]["8_menu_list_window"] = _get(c, "/window/menu_list", params={"menu_path": "Window"})
        print("[8] window list / ui_list / menu_list captured")

        # 9. menu_trigger — create a cube via Create > Mesh > Cube, then snapshot
        menu_trigger = _post(c, "/window/menu_trigger", params={
            "menu_path": "Create/Mesh/Cube",
        })
        report["steps"]["9_menu_trigger_cube"] = menu_trigger
        print(f"[9] Create/Mesh/Cube -> created_prims={menu_trigger.get('created_prims')}")

        # 10. Navigation pipeline — stop timeline, bake (non-blocking polling),
        # query path, add exclude. Since the service now yields to the Kit
        # event loop during `is_navmesh_baking()` polling, the HTTP router
        # stays responsive even for multi-minute bakes.
        _post(c, "/simulation/stop")

        # Create a cube BEFORE bake so the exclude target exists
        _post(c, "/stage/create_prim", json={
            "prim_path": "/World/PhaseE_Chair", "prim_type": "Cube",
            "position": [1.0, 0.0, 0.5],
        })

        bake = _post(
            c, "/navigation/bake",
            params={"volume_scale": "8.0", "timeout_s": "300.0"},
            timeout=360.0,
        )
        report["steps"]["10_nav_bake"] = bake
        print(
            f"[10] navmesh baked: ok={bake.get('ok')} "
            f"area_count={bake.get('area_count')} "
            f"agent_max_radius={bake.get('agent_max_radius')}"
        )
        if not bake.get("ok"):
            print(f"  !! bake not ok: {bake.get('reason')}", file=sys.stderr)
            status_ok = False

        query = _post(
            c, "/navigation/query_path",
            json={
                "start": [0.0, 0.0, 0.0],
                "end": [3.0, 3.0, 0.0],
                "agent_radius": 0.3,
                "agent_height": 1.8,
                "straighten": True,
            },
            timeout=120.0,
        )
        report["steps"]["10_nav_query"] = query
        points = query.get("points") or []
        print(f"[10] query_path ok={query.get('ok')} points={len(points)}")
        if not query.get("ok"):
            print(f"  !! query_path not ok: {query.get('reason')}", file=sys.stderr)
            status_ok = False

        exclude = _post(
            c, "/navigation/add_exclude_volume",
            params={"prim_path": "/World/PhaseE_Chair", "padding": "0.2"},
            timeout=60.0,
        )
        report["steps"]["10_nav_exclude"] = exclude
        print(
            f"[10] exclude volume -> "
            f"{exclude.get('volume_path') or exclude.get('volume_prim_path')}"
        )
        if not exclude.get("ok"):
            print(f"  !! exclude not ok: {exclude.get('reason')}", file=sys.stderr)
            status_ok = False

        # 11. MCP-direct scene viewport snapshot (Phase E)
        _post(c, "/stage/create_prim", json={
            "prim_path": "/World/PhaseE_Light", "prim_type": "DistantLight",
        })
        _post(c, "/stage/set_property", json={
            "prim_path": "/World/PhaseE_Light",
            "property_name": "inputs:intensity", "value": 3000, "type_hint": "float",
        })
        vp = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport", "width": 1024, "height": 576,
        })
        dest_vp = _copy_capture(vp["path"], "03_viewport_navmesh_scene.png")
        report["steps"]["11_viewport_snapshot"] = {"artifact": dest_vp}
        print(f"[11] viewport snapshot -> {dest_vp}")

        # 12. Regression: Phase D simple demo still works end-to-end
        simple_shown = _post(c, "/window/ui_show", json={
            "name": DEMO_SIMPLE_WINDOW, "visible": True, "focus": True, "settle_frames": 4,
        })
        report["steps"]["12a_simple_show"] = simple_shown
        simple_tree = _get(c, "/extension/ui_tree", params={
            "ext_id": DEMO_SIMPLE_EXT, "window": DEMO_SIMPLE_WINDOW,
        })
        simple_types = sorted({w.get("type") for w in simple_tree.get("widgets", [])})
        report["steps"]["12b_simple_types"] = simple_types
        print(f"[12] simple demo types still found: {simple_types}")
        if "Button" not in simple_types or "StringField" not in simple_types:
            print("  !! regression — simple demo widgets not discoverable", file=sys.stderr)
            status_ok = False

        cap_simple = _post(c, "/window/capture", json={"mode": "kit", "settle_frames": 6})
        dest_simple = _copy_capture(cap_simple["path"], "04_simple_demo_regression.png")
        report["steps"]["12_capture_simple"] = {"artifact": dest_simple}

        # 13. Clear logs again — assert 0 entries afterwards for ext-filtered view
        _post(c, "/extension/logs/clear")
        post_clear = _get(c, "/extension/logs", params={
            "ext_id": DEMO_ADVANCED_EXT, "level": "INFO",
        })
        report["steps"]["13_post_clear_logs"] = {"count": post_clear.get("count")}
        print(f"[13] post-clear count={post_clear.get('count')}")
        if post_clear.get("count") != 0:
            print(f"  !! clear_logs did not empty the buffer (count={post_clear.get('count')})",
                  file=sys.stderr)
            status_ok = False

    report["completed_at"] = time.time()
    report["status_ok"] = status_ok

    summary_path = _save_json("phase_e_live_report.json", report)
    print(f"\nSUMMARY -> {summary_path}")
    print(f"Phase E artifacts -> {PHASE_E_DIR}")
    return 0 if status_ok else 1


if __name__ == "__main__":
    sys.exit(run())
