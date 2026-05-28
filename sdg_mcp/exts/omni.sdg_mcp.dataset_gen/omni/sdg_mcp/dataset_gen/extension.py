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
        """LIVE path: build + run the Replicator graph.

        Renders the static labeled scene from every /World/Cameras/* camera with the
        BasicWriter (rgb + depth + semantic_segmentation). The earlier
        ``rep.modify.pose(...)`` on the referenced ``/Model`` prims corrupted the
        OmniGraph (``OgnWritePrimAttribute: Accessed invalid null prim`` +
        "Invalid xform opType token 'xformOp'") and triggered a GPU device-lost
        (live-observed 2026-05-28: kit crashed mid-orchestrator). Pose randomization
        is dropped; lighting variance is optional and only on the dome light (safe).
        Resolution + annotator set capped to fit GPU budget on this box."""
        import omni.replicator.core as rep

        stage = omni.usd.get_context().get_stage()
        cam_paths = [
            p.GetPath().pathString
            for p in stage.Traverse()
            if p.GetTypeName() == "Camera"
            and p.GetPath().pathString.startswith(config.CAMERAS_ROOT)
        ]
        if not cam_paths:
            raise RuntimeError(
                "no cameras under /World/Cameras — click Build Scene first"
            )
        spec = replicator_spec.build_spec(cam_paths)

        # GPU-safe resolution (1280x720 + 6 annotators previously device-lost'd).
        safe_res = (512, 512)
        render_products = [rep.create.render_product(cp, safe_res) for cp in cam_paths]

        out_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "..",
            "scenes", spec.output_subdir,
        )
        out_dir = os.path.abspath(out_dir)
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(
            output_dir=out_dir,
            rgb=True,
            distance_to_camera=True,
            semantic_segmentation=True,
        )
        writer.attach(render_products)

        # Pure on_frame trigger over the static scene — no pose randomization (broken).
        with rep.trigger.on_frame(num_frames=spec.frame_count):
            pass

        rep.orchestrator.run()
        return spec.frame_count

    def on_shutdown(self) -> None:
        self._window = None
        carb.log_info("[sdg] shutdown")
