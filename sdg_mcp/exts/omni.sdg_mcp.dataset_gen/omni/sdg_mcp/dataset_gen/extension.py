"""SDG Dataset Generator extension.

on_startup builds the labeled scene; "Generate Dataset" runs omni.replicator.core
to emit an annotated dataset. UI strings are ASCII only (Kit font atlas). The
Replicator path is LIVE-only (not exercised headless) — confirm/adjust in a
workspaces/isaac session per mcp-upgrade/make_progress/sdg_make.md.
"""
from __future__ import annotations

import os

import carb
import omni.ext
import omni.ui as ui
import omni.usd

from . import config, replicator_spec, scene_builder


class SdgDatasetGenExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._built = False
        self._window = ui.Window("SDG Dataset Generator", width=360, height=200)
        with self._window.frame:
            with ui.VStack(spacing=6):
                self._status = ui.Label("Status: idle")
                ui.Button("Build Scene", clicked_fn=lambda *_a: self._on_build())
                ui.Button("Generate Dataset", clicked_fn=lambda *_a: self._on_generate())
        carb.log_info("[sdg] startup")

    def _on_build(self) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            self._status.text = "Status: no stage"
            return
        info = scene_builder.build(stage)
        self._built = True
        self._status.text = f"Status: built ({len(info['props'])} props, {len(info['cameras'])} cams)"
        carb.log_info(f"[sdg] scene built: {info}")

    def _on_generate(self) -> None:
        if not self._built:
            self._status.text = "Status: build scene first"
            return
        try:
            n = self._run_replicator()
            self._status.text = f"Status: generated {n} frames -> {config.OUTPUT_SUBDIR}"
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[sdg] replicator failed: {exc}")
            self._status.text = "Status: replicator error (see console)"

    def _run_replicator(self) -> int:
        """LIVE path: build + run the Replicator graph. omni.replicator.core exists
        only in the Kit runtime. API names are recorded in sdg_make.md as LIVE-confirm
        — adjust here on first live run if a signature drifted."""
        import omni.replicator.core as rep

        stage = omni.usd.get_context().get_stage()
        cam_paths = [
            p.GetPath().pathString
            for p in stage.Traverse()
            if p.GetTypeName() == "Camera"
            and p.GetPath().pathString.startswith(config.CAMERAS_ROOT)
        ]
        spec = replicator_spec.build_spec(cam_paths)

        render_products = [rep.create.render_product(cp, spec.resolution) for cp in spec.camera_paths]

        out_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "scenes", spec.output_subdir
        )
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(
            output_dir=os.path.abspath(out_dir),
            rgb=True,
            distance_to_camera=True,
            semantic_segmentation=True,
            instance_id_segmentation=True,
            bounding_box_2d_tight=True,
            bounding_box_3d=True,
        )
        writer.attach(render_products)

        props = rep.get.prims(path_pattern=f"{config.PROPS_ROOT}/.*/Model")
        with rep.trigger.on_frame(num_frames=spec.frame_count):
            if spec.randomize_pose:
                with props:
                    rep.modify.pose(
                        position=rep.distribution.uniform((-3.0, -3.0, 0.0), (3.0, 3.0, 0.0)),
                        rotation=rep.distribution.uniform((0.0, 0.0, 0.0), (0.0, 0.0, 360.0)),
                    )
            if spec.randomize_lighting:
                light = rep.create.light(light_type="Distant")
                with light:
                    rep.modify.attribute("intensity", rep.distribution.uniform(300.0, 1500.0))

        rep.orchestrator.run()
        return spec.frame_count

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[sdg] shutdown")
