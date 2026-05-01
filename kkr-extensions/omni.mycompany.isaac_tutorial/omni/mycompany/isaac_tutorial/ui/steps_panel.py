"""Tutorial steps panel — 4 steps + sub-buttons (walkable viz / sensor attach).

Each step button auto-chains its prerequisites (idempotent):
- step 1 -> no prereq
- step 2 -> step 1 if office not loaded
- step 3 -> steps 1 + 2 if needed, then NavMesh navigate
- step 4 -> step 1 if needed, find chair if unknown, load people + sit

English-only strings because Kit 107 omni.ui font atlas lacks CJK glyphs.
"""
from __future__ import annotations

import asyncio

import omni.ui as ui

from ..actions import step_actions
from ..actions.base import run_with_ui_feedback


_STEP_BASE = {
    "s1": "1. Open office.usd",
    "s2": "2. Load Nova Carter @(0,0,0)",
    "s3": "3. Navigate via NavMesh to nearest Chair",
    "s4": "4. Load People -> walk -> Sit on chair",
}


class StepsPanel:

    def __init__(self, frame, ui_main, state, services_getter) -> None:
        self._frame = frame
        self._ui_main = ui_main
        self._state = state
        self._get_services = services_getter
        self._step_buttons: dict[str, ui.Button] = {}
        self._navmesh_viz_button: ui.Button | None = None
        self._sensor_output_label: ui.Label | None = None
        self._build()

    def _build(self) -> None:
        with self._frame:
            with ui.VStack(spacing=4):
                # Step 1
                self._step_buttons["s1"] = ui.Button(
                    self._label("s1"),
                    clicked_fn=lambda: self._spawn(self._run_step_1()),
                    tooltip=(
                        "Open the official NVIDIA office.usd on the stage.\n"
                        "Auto prereq: none.\n"
                        "On failure: check network and S3 access."
                    ),
                    height=28, name="step_1_button",
                )

                # Step 2
                self._step_buttons["s2"] = ui.Button(
                    self._label("s2"),
                    clicked_fn=lambda: self._spawn(self._run_step_2()),
                    tooltip=(
                        "Load the Nova Carter robot at (0, 0, 0) as a payload.\n"
                        "Auto prereq: [1] open office if not loaded.\n"
                        "On failure: check S3 access."
                    ),
                    height=28, name="step_2_button",
                )

                # Step 3 + sub-buttons
                self._step_buttons["s3"] = ui.Button(
                    self._label("s3"),
                    clicked_fn=lambda: self._spawn(self._run_step_3()),
                    tooltip=(
                        "Drive Nova Carter along the NavMesh walkable area to "
                        "the nearest Chair in the office.\n"
                        "Auto prereq: [1] office -> [2] Nova Carter -> stop -> "
                        "bake -> play -> navigate.\n"
                        "On failure: mesh_signature=None means office missing; "
                        "empty path means the chair is unreachable on the NavMesh."
                    ),
                    height=28, name="step_3_button",
                )
                with ui.HStack(spacing=4, height=24):
                    self._navmesh_viz_button = ui.Button(
                        "Show walkable area",
                        clicked_fn=lambda: self._spawn(self._toggle_navmesh_viz()),
                        tooltip=(
                            "Toggle the NavMesh walkable overlay in the viewport.\n"
                            "Auto prereq: NavMesh must be baked for the overlay "
                            "to show anything."
                        ),
                        name="navmesh_viz_button",
                    )
                    ui.Button(
                        "Attach sensors + start recording",
                        clicked_fn=lambda: self._spawn(self._attach_sensors()),
                        tooltip=(
                            "Attach RTX Camera + Lidar to Nova Carter and start "
                            "recording rgb + depth via BasicWriter under "
                            "%TEMP%/isaac_tutorial/<timestamp>/.\n"
                            "Auto prereq: Nova Carter must be loaded."
                        ),
                        name="attach_sensors_button",
                    )
                self._sensor_output_label = ui.Label(
                    "Sensor output: (not started)",
                    height=20, name="sensor_output_label",
                )

                # Step 4
                self._step_buttons["s4"] = ui.Button(
                    self._label("s4"),
                    clicked_fn=lambda: self._spawn(self._run_step_4()),
                    tooltip=(
                        "Load a Biped_Setup character, walk near the nearest "
                        "chair, then play the Sit animation. Falls back to "
                        "(-10, -15, 0) if no chair is found.\n"
                        "Auto prereq: [1] office + chair search."
                    ),
                    height=28, name="step_4_button",
                )

    # ---------- callbacks ----------

    def _spawn(self, coro):
        asyncio.ensure_future(coro)

    async def _run_step_1(self):
        services = self._get_services()
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.open_office(services, self._state),
            label="Step 1 open office",
        )
        self._refresh_labels()

    async def _run_step_2(self):
        services = self._get_services()
        if not self._state.office_loaded:
            await self._run_step_1()
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.load_nova_carter(services, self._state),
            label="Step 2 load Nova Carter",
        )
        self._refresh_labels()

    async def _run_step_3(self):
        services = self._get_services()
        if not self._state.office_loaded:
            await self._run_step_1()
        if not self._state.nova_carter_loaded:
            await self._run_step_2()
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.navigate_via_navmesh(services, self._state),
            label="Step 3 navigate",
            services=services,
        )
        self._refresh_labels()

    async def _run_step_4(self):
        services = self._get_services()
        if not self._state.office_loaded:
            await self._run_step_1()
        if self._state.chair_anchor_path is None:
            path, _ = await step_actions._find_nearest_chair(services, (0.0, 0.0, 0.0))
            self._state.chair_anchor_path = path or None
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.load_people_and_sit(services, self._state),
            label="Step 4 people sit",
            services=services,
        )
        self._refresh_labels()

    async def _toggle_navmesh_viz(self):
        services = self._get_services()
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.toggle_navmesh_viz(services, self._state),
            label="NavMesh viz toggle",
        )
        self._navmesh_viz_button.text = (
            "Hide walkable area"
            if self._state.navmesh_viz_mode == "walkable"
            else "Show walkable area"
        )

    async def _attach_sensors(self):
        services = self._get_services()
        await run_with_ui_feedback(
            self._ui_main,
            step_actions.attach_sensors_and_record(services, self._state),
            label="Attach sensors",
        )
        if self._state.sensor_output_dir:
            self._sensor_output_label.text = f"Sensor output: {self._state.sensor_output_dir}"

    # ---------- label refresh ----------

    def _label(self, key: str) -> str:
        done_map = {
            "s1": self._state.office_loaded,
            "s2": self._state.nova_carter_loaded,
            "s3": self._state.navigated,
            "s4": self._state.people_loaded,
        }
        base = _STEP_BASE[key]
        return f"[x] {base}" if done_map.get(key) else base

    def _refresh_labels(self) -> None:
        for key, btn in self._step_buttons.items():
            btn.text = self._label(key)
