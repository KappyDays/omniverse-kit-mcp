"""Environment setup panel — B#1 scale / B#2 camera speed / B#3 hide toggle / B#4 WASD spawn.

All strings English-only because Kit 107 omni.ui font atlas lacks CJK glyphs.
"""
from __future__ import annotations

import asyncio

import omni.ui as ui

from ..actions import env_actions
from ..actions.base import run_with_ui_feedback


class EnvSetupPanel:

    _SPEED_OPTIONS = (0.01, 0.05, 0.1, 0.5, 1.0, 2.0)

    def __init__(self, frame, ui_main, state) -> None:
        self._frame = frame
        self._ui_main = ui_main
        self._state = state
        self._hide_button: ui.Button | None = None
        self._hide_count_label: ui.Label | None = None
        self._spawn_wasd_button: ui.Button | None = None
        self._build()

    def _build(self) -> None:
        with self._frame:
            with ui.VStack(spacing=4):
                # B#1: scale
                with ui.HStack(spacing=4, height=28):
                    ui.Button(
                        "Scale selected x10",
                        clicked_fn=lambda: self._spawn(self._scale_up()),
                        tooltip=(
                            "Multiply the scale of the selected prim(s) by 10.\n"
                            "Auto prereq: none.\n"
                            "On failure: check Status label for selection state. "
                            "Ctrl+Z reverts."
                        ),
                        name="scale_up_button",
                    )
                    ui.Button(
                        "Scale selected /10",
                        clicked_fn=lambda: self._spawn(self._scale_down()),
                        tooltip=(
                            "Shrink the selected prim(s) scale to 1/10. Ctrl+Z reverts."
                        ),
                        name="scale_down_button",
                    )
                ui.Button(
                    "Reset scale to 1.0",
                    clicked_fn=lambda: self._spawn(self._reset_scale()),
                    tooltip="Reset selected prim(s) scale to (1, 1, 1).",
                    height=24, name="reset_scale_button",
                )
                ui.Separator(height=2)

                # B#2: camera speed (6 buttons)
                ui.Label("Camera speed:", height=22, name="cam_speed_label")
                with ui.HStack(spacing=4, height=26, name="cam_speed_row"):
                    for spd in self._SPEED_OPTIONS:
                        ui.Button(
                            str(spd),
                            clicked_fn=lambda s=spd: self._spawn(self._set_cam_speed(s)),
                            tooltip=(
                                f"Viewport camera move speed = {spd}. "
                                f"Applies when navigating with RMB + WASD."
                            ),
                            width=50, height=24,
                            name=f"cam_speed_{str(spd).replace('.', '_')}",
                        )
                ui.Separator(height=2)

                # B#3: hide-by-keyword toggle (ceiling / ventilation / cube)
                self._hide_button = ui.Button(
                    "Hide ceilings / vents / cubes",
                    clicked_fn=lambda: self._spawn(self._toggle_hide()),
                    tooltip=(
                        "Hide every prim whose name contains 'ceiling', 'ventilation' "
                        "or 'cube' (case-insensitive). Click again to restore.\n"
                        "Auto prereq: none.\n"
                        "On failure: no matching prim in Stage or office not loaded."
                    ),
                    height=28, name="hide_toggle_button",
                )
                self._hide_count_label = ui.Label(
                    "Matched: 0 prims",
                    height=20, name="hide_count_label",
                )
                ui.Separator(height=2)

                # B#4: WASD Nova Carter spawn
                self._spawn_wasd_button = ui.Button(
                    "Spawn WASD-controllable Nova Carter @(0,0,0)",
                    clicked_fn=lambda: self._spawn(self._spawn_wasd()),
                    tooltip=(
                        "Load Nova Carter and build an OmniGraph so the keyboard "
                        "W/A/S/D/Space drive it.\n"
                        "Auto prereq: Nova Carter will be loaded if absent.\n"
                        "Usage: start simulation Play, then W/S forward/back, "
                        "A/D turn, Space brake. On failure: verify the wheel "
                        "joint names match the Nova Carter URDF in Kit Console."
                    ),
                    height=28, name="spawn_wasd_button",
                )

    # ---------- helpers ----------

    def _spawn(self, coro):
        asyncio.ensure_future(coro)

    @staticmethod
    async def _as_coro(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    async def _scale_up(self):
        await run_with_ui_feedback(
            self._ui_main,
            self._as_coro(env_actions.scale_selected, 10.0),
            label="Scale x10",
        )

    async def _scale_down(self):
        await run_with_ui_feedback(
            self._ui_main,
            self._as_coro(env_actions.scale_selected, 0.1),
            label="Scale /10",
        )

    async def _reset_scale(self):
        await run_with_ui_feedback(
            self._ui_main,
            self._as_coro(env_actions.reset_scale_selected),
            label="Reset scale",
        )

    async def _set_cam_speed(self, speed: float):
        await run_with_ui_feedback(
            self._ui_main,
            self._as_coro(env_actions.set_camera_speed, speed),
            label=f"Camera speed={speed}",
        )
        self._state.camera_speed = speed

    async def _toggle_hide(self):
        await run_with_ui_feedback(
            self._ui_main,
            self._as_coro(env_actions.toggle_hidden_prims, self._state),
            label="Hide toggle",
        )
        if self._state.ceiling_hidden:
            self._hide_button.text = "Show ceilings / vents / cubes"
            self._hide_count_label.text = f"Matched: {len(self._state.ceiling_cache)} prims"
        else:
            self._hide_button.text = "Hide ceilings / vents / cubes"
            self._hide_count_label.text = "Matched: 0 prims"

    async def _spawn_wasd(self):
        from ..bindings.services import get_services
        services = get_services()
        await run_with_ui_feedback(
            self._ui_main,
            env_actions.spawn_wasd_nova_carter(services, self._state),
            label="Spawn WASD Nova Carter",
        )
