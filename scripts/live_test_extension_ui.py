"""Live test for Phase D Extension UI automation + carb log capture.

Covers the four new REST endpoints exposed as MCP tools:

- POST /extension/activate
- GET  /extension/ui_tree
- POST /extension/ui_invoke
- GET  /extension/logs

Plus cross-checks: window/capture for visual evidence, window/ui_show to
focus the demo window, and window/list so we can see the Kit HWND picked.

Every visual artifact is copied into ./PhaseD/ with a descriptive name so
the MCP agent can re-read them without touching %TEMP%.

Usage:
    .venv/Scripts/python.exe scripts/live_test_extension_ui.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

import httpx

BASE = "http://localhost:8011/validation/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE_D_DIR = PROJECT_ROOT / "PhaseD"
DEMO_EXT_ID = "omni.mycompany.ui_demo"
DEMO_WINDOW = "UI Demo"


def _post(c: httpx.Client, path: str, *, json=None, params=None):
    r = c.post(f"{BASE}{path}", json=json, params=params, timeout=90.0)
    r.raise_for_status()
    return r.json()


def _get(c: httpx.Client, path: str, *, params=None):
    r = c.get(f"{BASE}{path}", params=params, timeout=90.0)
    r.raise_for_status()
    return r.json()


def _copy_capture(src_path: str, dest_name: str) -> str:
    """Copy a capture produced under %TEMP%/validation_api_captures/ into PhaseD/."""
    PHASE_D_DIR.mkdir(parents=True, exist_ok=True)
    dest = PHASE_D_DIR / dest_name
    shutil.copy2(src_path, dest)
    return str(dest)


def _save_json(name: str, data) -> str:
    PHASE_D_DIR.mkdir(parents=True, exist_ok=True)
    p = PHASE_D_DIR / name
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(p)


def run() -> int:
    report: dict = {"started_at": time.time(), "steps": {}}
    status_ok = True

    with httpx.Client(timeout=90) as c:
        # 0. Health
        health = _get(c, "/health")
        report["steps"]["0_health"] = health
        print("[0] health:", health)

        # 1. Activate demo extension (no-op if already enabled)
        activated = _post(c, "/extension/activate", json={
            "ext_id": DEMO_EXT_ID, "reload": False,
        })
        report["steps"]["1_activate"] = activated
        print("[1] activate:", activated)
        if not activated.get("enabled"):
            print("  !! demo extension not enabled", file=sys.stderr)
            status_ok = False

        # 2. Make sure the window is shown and focused — it is newly created,
        # so omni.ui.Workspace likely already has it. ui_show also handles the
        # hidden-then-shown sequence.
        shown = _post(c, "/window/ui_show", json={
            "name": DEMO_WINDOW, "visible": True, "focus": True, "settle_frames": 8,
        })
        report["steps"]["2_ui_show"] = shown
        print("[2] ui_show:", shown.get("found"), "via", shown.get("resolved_via"))

        # 3. Window capture BEFORE any interaction
        cap0 = _post(c, "/window/capture", json={
            "mode": "kit", "settle_frames": 6, "output_format": "png",
        })
        dest0 = _copy_capture(cap0["path"], "01_demo_window_initial.png")
        report["steps"]["3_capture_initial"] = {"artifact": dest0, "source": cap0["path"]}
        print("[3] captured initial ->", dest0)

        # 4. UI tree discovery — expect Button + StringField among widgets
        tree0 = _get(c, "/extension/ui_tree", params={
            "ext_id": DEMO_EXT_ID, "window": DEMO_WINDOW,
        })
        report["steps"]["4_ui_tree_initial"] = tree0
        widgets = tree0.get("widgets") or []
        types = [w.get("type") for w in widgets]
        print(f"[4] ui_tree: {len(widgets)} widgets — types={types[:10]}")

        def _find_widget(filter_fn) -> dict | None:
            for w in widgets:
                if filter_fn(w):
                    return w
            return None

        trigger_btn = _find_widget(lambda w: w.get("type") == "Button" and "Trigger" in (w.get("label") or ""))
        read_btn = _find_widget(lambda w: w.get("type") == "Button" and "Read" in (w.get("label") or ""))
        str_field = _find_widget(lambda w: w.get("type") == "StringField")
        counter_label = _find_widget(lambda w: w.get("type") == "Label" and "Clicked" in (w.get("label") or ""))

        if trigger_btn is None:
            print("  !! Trigger button not found in ui_tree", file=sys.stderr)
            status_ok = False
        if str_field is None:
            print("  !! StringField not found in ui_tree", file=sys.stderr)
            status_ok = False

        # Snapshot timestamp for logs since_ms filter
        since_ms = int(time.time() * 1000)

        # 5. Click the Trigger button twice
        if trigger_btn:
            for i in range(2):
                inv = _post(c, "/extension/ui_invoke", json={
                    "widget_path": trigger_btn["path"],
                    "action": "click",
                    "value": None,
                })
                report["steps"][f"5_click_trigger_{i+1}"] = inv
                print(f"[5.{i+1}] clicked Trigger:", inv.get("post_state", {}).get("label"))

            # Capture after clicks
            cap1 = _post(c, "/window/capture", json={"mode": "kit", "settle_frames": 6})
            dest1 = _copy_capture(cap1["path"], "02_demo_after_trigger_clicks.png")
            report["steps"]["5_capture_after_trigger"] = {"artifact": dest1}
            print("[5] captured after clicks ->", dest1)

        # 6. Type into StringField
        typed_val = "phase-d-live"
        if str_field:
            typed = _post(c, "/extension/ui_invoke", json={
                "widget_path": str_field["path"],
                "action": "type",
                "value": typed_val,
            })
            report["steps"]["6_type_field"] = typed
            print("[6] typed:", typed.get("post_state", {}).get("value"))

            cap2 = _post(c, "/window/capture", json={"mode": "kit", "settle_frames": 6})
            dest2 = _copy_capture(cap2["path"], "03_demo_after_type.png")
            report["steps"]["6_capture_after_type"] = {"artifact": dest2}
            print("[6] captured after type ->", dest2)

        # 7. Click Read → echo label updates
        if read_btn:
            pressed = _post(c, "/extension/ui_invoke", json={
                "widget_path": read_btn["path"], "action": "click", "value": None,
            })
            report["steps"]["7_click_read"] = pressed
            print("[7] clicked Read:", pressed.get("post_state", {}).get("label"))

            cap3 = _post(c, "/window/capture", json={"mode": "kit", "settle_frames": 6})
            dest3 = _copy_capture(cap3["path"], "04_demo_after_read_click.png")
            report["steps"]["7_capture_after_read"] = {"artifact": dest3}
            print("[7] captured after read ->", dest3)

        # 8. Final ui_tree — labels should reflect the clicks and typed value
        tree_final = _get(c, "/extension/ui_tree", params={
            "ext_id": DEMO_EXT_ID, "window": DEMO_WINDOW,
        })
        report["steps"]["8_ui_tree_final"] = tree_final
        final_labels = [w.get("label") for w in tree_final.get("widgets", []) if w.get("type") == "Label"]
        final_values = [w.get("value") for w in tree_final.get("widgets", []) if w.get("type") == "StringField"]
        print("[8] final labels:", final_labels)
        print("[8] final string field value:", final_values)

        # 9. Capture logs since step 5
        logs = _get(c, "/extension/logs", params={
            "ext_id": DEMO_EXT_ID,
            "since_ms": str(since_ms),
            "level": "INFO",
            "limit": "200",
        })
        report["steps"]["9_capture_logs"] = logs
        entry_msgs = [e.get("msg") for e in logs.get("entries", [])]
        print(f"[9] captured {logs.get('count')} log entries")
        for m in entry_msgs[:20]:
            print(f"    - {m}")

        # 10. Capture WARN+ (broader scope, no source filter) — smoke test
        logs_warn = _get(c, "/extension/logs", params={
            "level": "WARN", "limit": "50",
        })
        report["steps"]["10_capture_logs_warn"] = {
            "count": logs_warn.get("count"),
            "sample": [
                {"level": e.get("level"), "source": e.get("source"), "msg": e.get("msg")[:160]}
                for e in logs_warn.get("entries", [])[:10]
            ],
        }
        print(f"[10] WARN+ count={logs_warn.get('count')}")

        # 11. Negative — invalid widget_path → 400
        try:
            _post(c, "/extension/ui_invoke", json={
                "widget_path": "NoSuchWindow//Nothing/Here",
                "action": "click",
            })
            report["steps"]["11_negative_invalid_path"] = {"status": "unexpected 2xx"}
            print("[11] negative: UNEXPECTED success", file=sys.stderr)
            status_ok = False
        except httpx.HTTPStatusError as exc:
            report["steps"]["11_negative_invalid_path"] = {
                "status_code": exc.response.status_code,
                "detail": exc.response.json(),
            }
            print(f"[11] negative: {exc.response.status_code} (expected 400)")

        # 12. Negative — unknown ext id
        try:
            _post(c, "/extension/activate", json={
                "ext_id": "omni.does.not.exist.phase.d", "reload": False,
            })
            report["steps"]["12_negative_unknown_ext"] = {"status": "unexpected 2xx"}
            status_ok = False
        except httpx.HTTPStatusError as exc:
            report["steps"]["12_negative_unknown_ext"] = {
                "status_code": exc.response.status_code,
                "detail": exc.response.json(),
            }
            print(f"[12] negative: {exc.response.status_code} (expected 400)")

        # 13. Viewport capture so PhaseD/ also has a 3D scene snapshot
        vp = _post(c, "/viewport/capture", json={
            "viewport_name": "Viewport", "width": 1024, "height": 576, "output_format": "png",
        })
        dest_vp = _copy_capture(vp["path"], "05_viewport_snapshot.png")
        report["steps"]["13_viewport_snapshot"] = {"artifact": dest_vp}
        print("[13] viewport snapshot ->", dest_vp)

    # Overall status
    expectations = [
        ("trigger_click_increments", any(
            (report["steps"].get("8_ui_tree_final", {}).get("widgets") or [])
            and any("Clicked 2 times" in (w.get("label") or "") for w in report["steps"]["8_ui_tree_final"]["widgets"])
            for _ in [0]
        )),
        ("echo_updated", any(
            any(
                (w.get("type") == "Label" and typed_val in (w.get("label") or ""))
                for w in report["steps"].get("8_ui_tree_final", {}).get("widgets", [])
            )
            for _ in [0]
        )),
        ("field_value_persisted", any(
            (w.get("type") == "StringField" and w.get("value") == typed_val)
            for w in report["steps"].get("8_ui_tree_final", {}).get("widgets", [])
        )),
        ("logs_have_trigger", any(
            "trigger clicked" in (e.get("msg") or "")
            for e in report["steps"].get("9_capture_logs", {}).get("entries", [])
        )),
        ("logs_have_read", any(
            "read field" in (e.get("msg") or "")
            for e in report["steps"].get("9_capture_logs", {}).get("entries", [])
        )),
    ]
    report["expectations"] = {name: bool(ok) for name, ok in expectations}
    if not all(ok for _, ok in expectations):
        print("!! Some expectations failed:", report["expectations"], file=sys.stderr)
        status_ok = False

    report["completed_at"] = time.time()
    report["status_ok"] = status_ok

    summary_path = _save_json("phase_d_live_report.json", report)
    print(f"\nSUMMARY -> {summary_path}")
    print(f"PhaseD artifacts -> {PHASE_D_DIR}")
    return 0 if status_ok else 1


if __name__ == "__main__":
    sys.exit(run())
