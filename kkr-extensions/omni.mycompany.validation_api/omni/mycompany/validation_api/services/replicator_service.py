"""Replicator service — SDG writer / randomizer / trigger orchestration (Phase H).

All omni.*/pxr.* imports are lazy inside the methods per API rule #7. The
service keeps a dict of created writers + randomizers by id so callers can
reference them in later triggers. The orchestrator run / step calls are
``async`` wrappers over ``omni.replicator.core.orchestrator`` which in Kit
is itself cooperative (yields via ``omni.kit.app.get_app().next_update_async``).

Design note — MDL resolver deadlock: ``log_capture.start()`` must stay
disabled (root CLAUDE.md) so replicator writer flush doesn't trigger the
carb log callback storm that deadlocks the Kit main loop. The Extension's
``on_startup`` already leaves ``_log_capture=None``.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_VALID_WRITERS = {"BasicWriter", "KittiWriter", "CocoWriter"}
_VALID_RANDOMIZERS = {"position", "rotation", "lighting"}


class ReplicatorService:
    """Wrap omni.replicator.core for MCP-visible SDG control."""

    def __init__(self) -> None:
        # Writer + randomizer registries — lifetime = Extension session
        # Keys: auto-generated ids returned to MCP callers
        self._writers: dict[str, dict[str, Any]] = {}
        self._randomizers: dict[str, dict[str, Any]] = {}
        # on_time trigger handles (for later unregister / introspection)
        self._time_triggers: dict[str, dict[str, Any]] = {}

    async def create_writer(self, request: dict[str, Any]) -> dict[str, Any]:
        writer_type = request.get("writer_type") or "BasicWriter"
        if writer_type not in _VALID_WRITERS:
            raise ValueError(
                f"writer_type must be one of {sorted(_VALID_WRITERS)}; got {writer_type!r}"
            )
        output_dir = request["output_dir"]
        rgb = bool(request.get("rgb", True))
        depth = bool(request.get("depth", False))
        semantic_segmentation = bool(request.get("semantic_segmentation", False))

        os.makedirs(output_dir, exist_ok=True)

        backend = "omni.replicator.core"
        writer_id = f"writer_{uuid.uuid4().hex[:8]}"
        try:
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            # WriterRegistry.get returns a ready writer INSTANCE (not a class) —
            # calling it raises "'BasicWriter' object is not callable".
            writer = rep.WriterRegistry.get(writer_type)
            # BasicWriter.initialize signature — kwargs differ between
            # KittiWriter/CocoWriter; we pass the common subset + channel toggles.
            init_kwargs: dict[str, Any] = {"output_dir": output_dir}
            if writer_type == "BasicWriter":
                init_kwargs["rgb"] = rgb
                init_kwargs["distance_to_camera"] = depth
                init_kwargs["semantic_segmentation"] = semantic_segmentation
            writer.initialize(**init_kwargs)

            # A writer with no render products attached writes nothing — bind it
            # to camera render products so trigger_once actually emits frames.
            # Camera selection: explicit request.camera_paths, else every
            # UsdGeom.Camera under /World/Cameras, else the active viewport
            # camera. Resolution kept modest (default 512x512) to stay within
            # GPU budget (full-res multi-annotator runs have device-lost'd here).
            import omni.usd
            stage = omni.usd.get_context().get_stage()
            cam_paths: list[str] = list(request.get("camera_paths") or [])
            if not cam_paths and stage is not None:
                for prim in stage.Traverse():
                    if (
                        prim.GetTypeName() == "Camera"
                        and prim.GetPath().pathString.startswith("/World/Cameras")
                    ):
                        cam_paths.append(prim.GetPath().pathString)
            if not cam_paths:
                try:
                    from omni.kit.viewport.utility import get_active_viewport
                    vp = get_active_viewport()
                    if vp is not None and vp.camera_path:
                        cam_paths = [str(vp.camera_path)]
                except Exception:  # noqa: BLE001
                    pass
            res = request.get("resolution") or [512, 512]
            res_t = (int(res[0]), int(res[1]))
            render_products = []
            attached_cameras: list[str] = []
            for cp in cam_paths:
                try:
                    render_products.append(rep.create.render_product(cp, res_t))
                    attached_cameras.append(cp)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("render_product(%s) failed: %s", cp, exc)
            if render_products:
                writer.attach(render_products)

            self._writers[writer_id] = {
                "writer": writer,
                "writer_type": writer_type,
                "output_dir": output_dir,
                "rgb": rgb,
                "depth": depth,
                "semantic_segmentation": semantic_segmentation,
                "render_products": render_products,
                "attached_cameras": attached_cameras,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("create_writer failed: %s", exc, exc_info=True)
            backend = f"fallback_metadata:{type(exc).__name__}"
            self._writers[writer_id] = {
                "writer": None,
                "writer_type": writer_type,
                "output_dir": output_dir,
                "rgb": rgb,
                "depth": depth,
                "semantic_segmentation": semantic_segmentation,
                "error": str(exc),
            }

        return {
            "ok": True,
            "writer_id": writer_id,
            "writer_type": writer_type,
            "output_dir": output_dir,
            "channels": {
                "rgb": rgb,
                "depth": depth,
                "semantic_segmentation": semantic_segmentation,
            },
            "attached_cameras": self._writers[writer_id].get("attached_cameras", []),
            "backend": backend,
        }

    async def register_randomizer(self, request: dict[str, Any]) -> dict[str, Any]:
        rand_type = request.get("type")
        if rand_type not in _VALID_RANDOMIZERS:
            raise ValueError(
                f"type must be one of {sorted(_VALID_RANDOMIZERS)}; got {rand_type!r}"
            )
        target = request["target"]
        config = dict(request.get("config") or {})

        randomizer_id = f"rand_{uuid.uuid4().hex[:8]}"
        backend = "omni.replicator.core"
        try:
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            with rep.new_layer():
                if rand_type == "position":
                    volume = config.get("volume") or [[-1, -1, 0], [1, 1, 0]]
                    objs = rep.get.prims(path_pattern=target)
                    with rep.trigger.on_frame():
                        rep.randomizer.scatter_3d(objs, volume=volume)
                elif rand_type == "rotation":
                    min_rot = config.get("min_rot") or [0, 0, 0]
                    max_rot = config.get("max_rot") or [360, 360, 360]
                    objs = rep.get.prims(path_pattern=target)
                    with rep.trigger.on_frame():
                        rep.modify.pose(
                            objs,
                            rotation=rep.distribution.uniform(min_rot, max_rot),
                        )
                elif rand_type == "lighting":
                    min_int = float(config.get("min_int", 500.0))
                    max_int = float(config.get("max_int", 2000.0))
                    lights = rep.get.prims(
                        prim_types=["DomeLight", "DistantLight", "RectLight"],
                    )
                    with rep.trigger.on_frame():
                        rep.modify.attribute(
                            lights, "intensity",
                            rep.distribution.uniform(min_int, max_int),
                        )
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        self._randomizers[randomizer_id] = {
            "type": rand_type,
            "target": target,
            "config": config,
            "backend": backend,
        }
        return {
            "ok": True,
            "randomizer_id": randomizer_id,
            "type": rand_type,
            "target": target,
            "config": config,
            "backend": backend,
        }

    async def trigger_once(self, request: dict[str, Any]) -> dict[str, Any]:
        num_frames = int(request.get("num_frames", 1))
        backend = "omni.replicator.core"
        frames_ran = 0
        try:
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            await rep.orchestrator.run_async(num_frames=num_frames)
            frames_ran = num_frames
        except AttributeError:
            # Some Kit builds ship orchestrator.run (sync) instead of run_async.
            try:
                import omni.replicator.core as rep  # type: ignore[import-not-found]

                rep.orchestrator.run(num_frames=num_frames)
                frames_ran = num_frames
            except Exception as exc:  # noqa: BLE001
                backend = f"fallback_noop:{type(exc).__name__}"
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_noop:{type(exc).__name__}"

        return {
            "ok": True,
            "num_frames": num_frames,
            "frames_ran": frames_ran,
            "backend": backend,
            "writer_count": len(self._writers),
            "randomizer_count": len(self._randomizers),
        }

    async def trigger_on_time(self, request: dict[str, Any]) -> dict[str, Any]:
        interval_s = float(request["interval_s"])
        if interval_s <= 0:
            raise ValueError("interval_s must be > 0")

        trigger_id = f"trig_{uuid.uuid4().hex[:8]}"
        backend = "omni.replicator.core"
        try:
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            with rep.trigger.on_time(interval=interval_s):
                rep.orchestrator.step()
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        self._time_triggers[trigger_id] = {
            "interval_s": interval_s,
            "backend": backend,
        }
        return {
            "ok": True,
            "trigger_id": trigger_id,
            "interval_s": interval_s,
            "backend": backend,
        }
