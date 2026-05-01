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

            writer_cls = rep.WriterRegistry.get(writer_type)
            writer = writer_cls()
            # BasicWriter.initialize signature — kwargs differ between
            # KittiWriter/CocoWriter; we pass the common subset + channel toggles.
            init_kwargs: dict[str, Any] = {"output_dir": output_dir}
            if writer_type == "BasicWriter":
                init_kwargs["rgb"] = rgb
                init_kwargs["distance_to_camera"] = depth
                init_kwargs["semantic_segmentation"] = semantic_segmentation
            writer.initialize(**init_kwargs)
            self._writers[writer_id] = {
                "writer": writer,
                "writer_type": writer_type,
                "output_dir": output_dir,
                "rgb": rgb,
                "depth": depth,
                "semantic_segmentation": semantic_segmentation,
            }
        except Exception as exc:  # noqa: BLE001
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
