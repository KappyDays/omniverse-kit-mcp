"""Robot Fleet Choreography extension.

on_startup builds the fleet scene; "Choreograph" authors the OmniGraph ActionGraph
skeleton (LIVE-only — omni.graph.* exists only in the Kit runtime). UI is ASCII.
The full waypoint-follow wiring + sim_time formation change are the live integration
points — confirm node types on first run per mcp-upgrade/make_progress/fleet_make.md.
"""
from __future__ import annotations

import carb
import omni.ext
import omni.ui as ui
import omni.usd

from . import config, graph_spec, scene_builder


class FleetChoreographyExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._built = False
        self._window = ui.Window("Robot Fleet Choreography", width=360, height=220)
        with self._window.frame:
            with ui.VStack(spacing=6):
                self._status = ui.Label("Status: idle")
                ui.Button("Build Fleet", clicked_fn=lambda *_a: self._on_build())
                ui.Button("Choreograph", clicked_fn=lambda *_a: self._on_choreograph())
        carb.log_info("[fleet] startup")

    def _on_build(self) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Status: no stage"
            return
        info = scene_builder.build(stage)
        self._built = True
        self._status.text = (
            f"Status: built ({len(info['robots'])} robots, {len(info['waypoints'])} waypoints)"
        )
        carb.log_info(f"[fleet] built {info}")

    def _on_choreograph(self) -> None:
        if not self._built:
            self._status.text = "Status: build fleet first"
            return
        try:
            self._build_graph()
            self._status.text = "Status: graph authored - press Play"
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[fleet] graph failed: {exc}")
            self._status.text = "Status: graph error (see console)"

    def _build_graph(self) -> None:
        """LIVE path: author the ActionGraph skeleton. omni.graph.* only exists in
        the Kit runtime. Node types are LIVE-confirm (fleet_make.md): the per-robot
        DifferentialController + waypoint-follow wiring is added on first live run."""
        import omni.graph.core as og

        stage = omni.usd.get_context().get_stage()
        robot_paths = [
            f"{config.FLEET_ROOT}/{n}"
            for n in config.ROBOT_NAMES
            if stage.GetPrimAtPath(f"{config.FLEET_ROOT}/{n}")
        ]
        spec = graph_spec.build_spec(robot_paths)
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": spec.graph_path, "evaluator_name": "execution"},
            {keys.CREATE_NODES: [("OnTick", spec.tick_node_type)]},
        )
        carb.log_info(
            f"[fleet] graph skeleton at {spec.graph_path} for {len(robot_paths)} robots"
        )

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[fleet] shutdown")
