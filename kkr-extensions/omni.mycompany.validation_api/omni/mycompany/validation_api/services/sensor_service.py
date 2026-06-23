"""Sensor service — RTX Camera / Lidar / Depth Camera prim attachment (Phase E).

Each ``attach_*`` method creates a child xform under ``robot_prim`` carrying
the sensor schema. The *type* is recorded as a USD custom attribute
``validation_api:sensor_type`` (one of ``rtx_camera`` / ``rtx_lidar`` /
``rtx_depth_camera``) so ``set_visualization`` can dispatch the correct
Debug Draw backend without re-parsing the prim kind.

All omni.*/pxr.* imports are lazy inside the methods per API rule #7.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# Custom USD attribute name we stamp on sensor prims so `set_visualization`
# can tell what kind of overlay to toggle without having to inspect the
# underlying Kit sensor instance (which may not be available in headless
# tests). String, stored in the prim custom-data dict.
SENSOR_TYPE_ATTR = "validation_api:sensor_type"

_SUPPORTED_TYPES = {"rtx_camera", "rtx_lidar", "rtx_depth_camera"}


class SensorService:
    """Attach RTX sensor prims under a robot chassis + toggle their overlays."""

    def __init__(self) -> None:
        # Cache live LidarRtx instances by prim path. The RTX lidar's scan
        # buffer is driven by this runtime object's internal render product;
        # if the instance is GC'd the GMO buffer tears down and readback
        # returns 0 points. Keeping it alive (session lifetime) lets
        # lidar_get_point_cloud reuse get_current_frame().
        self._lidar_instances: dict[str, Any] = {}

    async def attach_rtx_camera(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._attach(request, sensor_type="rtx_camera")

    async def attach_rtx_lidar(self, request: dict[str, Any]) -> dict[str, Any]:
        payload = dict(request)
        payload["config_preset"] = request.get("config_preset", "Example_Rotary")
        return await self._attach(payload, sensor_type="rtx_lidar")

    async def attach_rtx_depth_camera(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._attach(request, sensor_type="rtx_depth_camera")

    async def _attach(
        self, request: dict[str, Any], *, sensor_type: str,
    ) -> dict[str, Any]:
        """Schedule sensor USD mutation on the Kit main loop."""
        import asyncio
        import omni.kit.async_engine  # lazy

        async def _main_loop_impl() -> dict[str, Any]:
            return await self._attach_on_main(request, sensor_type=sensor_type)

        future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
        return await asyncio.wrap_future(future)

    async def _attach_on_main(
        self, request: dict[str, Any], *, sensor_type: str,
    ) -> dict[str, Any]:
        """Create a Camera prim child + stamp sensor_type + apply mount transform."""
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf, Sdf, UsdGeom

        robot_prim = request["robot_prim"]
        mount_offset = request["mount_offset"]
        mount_rotation = request["mount_rotation"]
        sensor_name = request.get("sensor_name") or _default_name(sensor_type)
        resolution = request.get("resolution") or [1280, 720]

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        parent = stage.GetPrimAtPath(robot_prim)
        if not parent.IsValid():
            raise ValueError(f"Parent prim {robot_prim!r} not found for sensor attach")

        sensor_path = _safe_child_path(robot_prim, sensor_name)
        if sensor_type == "rtx_lidar":
            # Proper RTX lidar = an OmniLidar prim carrying the
            # OmniSensorGenericLidarCoreAPI schema + a beam config, created via the
            # IsaacSensorCreateRtxLidar command. A bare UsdGeom.Camera prim has NO
            # scan emitter, so the scan-buffer annotator stays empty (0 points) —
            # the original bug. The command applies the schema + config + mount.
            preset = request.get("config_preset", "Example_Rotary")
            try:
                import omni.kit.app
                _mgr = omni.kit.app.get_app().get_extension_manager()
                if not _mgr.is_extension_enabled("isaacsim.sensors.experimental.rtx"):
                    _mgr.set_extension_enabled_immediate("isaacsim.sensors.experimental.rtx", True)
            except Exception as exc:  # noqa: BLE001
                import logging as _lg
                _lg.getLogger(__name__).warning("enable isaacsim.sensors.experimental.rtx failed: %s", exc)
            _child = sensor_path.rsplit("/", 1)[-1]
            lidar_backend = "isaacsim.sensors.experimental.rtx.Lidar.create"
            lidar_authoring = None
            try:
                import numpy as np  # lazy
                from isaacsim.sensors.experimental.rtx import Lidar  # type: ignore[import-not-found]

                lidar_authoring = Lidar.create(
                    path=sensor_path,
                    config=preset,
                    translations=np.array(mount_offset, dtype=float),
                )
            except Exception as exc:  # noqa: BLE001
                lidar_backend = f"legacy_command:{type(exc).__name__}"
                omni.kit.commands.execute(
                    "IsaacSensorCreateRtxLidar",
                    path="/" + _child,
                    parent=robot_prim,
                    config=preset,
                    translation=tuple(float(v) for v in mount_offset),
                    orientation=(1.0, 0.0, 0.0, 0.0),
                )
            sensor_prim = stage.GetPrimAtPath(sensor_path)
            if not sensor_prim.IsValid():
                raise RuntimeError(f"RTX lidar creation failed at {sensor_path}")
            r_attr = sensor_prim.GetAttribute("xformOp:rotateXYZ")
            if r_attr and r_attr.IsValid():
                r_attr.Set(Gf.Vec3f(*mount_rotation))
        else:
            # rtx_camera / rtx_depth_camera ride on a UsdGeom.Camera prim — Kit's
            # viewport binding + Isaac sensor pipelines consume Camera prims; the
            # depth differentiation is driven by the sensor_type custom attr + the
            # annotator configured on capture.
            omni.kit.commands.execute(
                "CreatePrimWithDefaultXformCommand",
                prim_type="Camera",
                prim_path=sensor_path,
            )
            sensor_prim = stage.GetPrimAtPath(sensor_path)
            if not sensor_prim.IsValid():
                raise RuntimeError(f"Sensor prim creation failed at {sensor_path}")
            # Mount transform (relative to parent robot prim via xformOp on child)
            t_attr = sensor_prim.GetAttribute("xformOp:translate")
            if t_attr.IsValid():
                t_attr.Set(Gf.Vec3d(*mount_offset))
            r_attr = sensor_prim.GetAttribute("xformOp:rotateXYZ")
            if r_attr.IsValid():
                r_attr.Set(Gf.Vec3f(*mount_rotation))

        # Resolution + camera defaults
        if sensor_type in {"rtx_camera", "rtx_depth_camera"}:
            horiz_aper = sensor_prim.GetAttribute("horizontalAperture")
            if horiz_aper.IsValid():
                horiz_aper.Set(20.955)
            focal = sensor_prim.GetAttribute("focalLength")
            if focal.IsValid():
                focal.Set(24.0)

        # Stamp sensor_type + resolution + config_preset for later dispatch
        custom = sensor_prim.GetCustomData() or {}
        custom_block = dict(custom.get("validation_api", {}))
        custom_block["sensor_type"] = sensor_type
        custom_block["resolution"] = list(resolution)
        if sensor_type == "rtx_lidar":
            chosen_preset = request.get("config_preset", "Example_Rotary")
            # The OmniLidar prim is already schema+config'd (created above via
            # IsaacSensorCreateRtxLidar). Cache a LidarRtx wrapper + attach the
            # scan-buffer annotator for the get_current_frame readback path.
            try:
                from isaacsim.sensors.experimental.rtx import LidarSensor  # type: ignore[import-not-found]
                lidar_source = lidar_authoring if lidar_authoring is not None else sensor_path
                lidar_rtx = LidarSensor(
                    lidar_source, annotators=["generic-model-output"],
                )
                self._lidar_instances[sensor_path] = lidar_rtx
            except ImportError:
                import logging as _lg
                _lg.getLogger(__name__).warning(
                    "isaacsim.sensors.experimental.rtx.LidarSensor unavailable — annotator-only readback"
                )
            custom_block["config_preset"] = chosen_preset
            custom_block["annotator"] = "IsaacCreateRTXLidarScanBuffer"
            custom_block["backend"] = lidar_backend
        if sensor_type == "rtx_depth_camera":
            custom_block["annotator"] = "distance_to_camera"
        custom["validation_api"] = custom_block
        sensor_prim.SetCustomData(custom)

        response: dict[str, Any] = {
            "ok": True,
            "sensor_prim_path": sensor_path,
            "parent_prim": robot_prim,
            "sensor_type": sensor_type,
            "resolution": list(resolution),
        }
        if sensor_type == "rtx_lidar":
            response["config_preset"] = custom_block["config_preset"]
            response["annotator"] = custom_block["annotator"]
            response["backend"] = custom_block["backend"]
        if sensor_type == "rtx_depth_camera":
            response["annotator"] = custom_block["annotator"]
        return response

    async def attach_contact(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach an ``isaacsim.sensors.experimental.physics.Contact`` child prim (Phase G).

        Falls back to a plain Xform prim carrying ``validation_api:sensor_type=contact``
        when the ``isaacsim.sensors.experimental.physics`` module is not importable
        (headless test harness). Response always reports which path was
        taken via the ``backend`` field.
        """
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf

        parent_prim = request["prim_path"]
        sensor_name = request.get("sensor_name") or "ContactSensor"
        frequency = int(request.get("frequency", 60))
        translation = request.get("translation") or [0.0, 0.0, 0.0]
        radius = float(request.get("radius", -1.0))

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        if not stage.GetPrimAtPath(parent_prim).IsValid():
            raise ValueError(f"Parent prim {parent_prim!r} not found for contact sensor")

        sensor_path = _safe_child_path(parent_prim, sensor_name)
        backend = "isaacsim.sensors.experimental.physics.Contact.create"

        try:
            import numpy as np  # lazy
            from isaacsim.sensors.experimental.physics import Contact  # type: ignore[import-not-found]

            Contact.create(
                sensor_path,
                translations=np.array([translation], dtype=float),
                radius=radius,
            )
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_xform:{type(exc).__name__}"
            omni.kit.commands.execute(
                "CreatePrimWithDefaultXformCommand",
                prim_type="Xform",
                prim_path=sensor_path,
            )
            prim = stage.GetPrimAtPath(sensor_path)
            if prim.IsValid():
                t_attr = prim.GetAttribute("xformOp:translate")
                if t_attr.IsValid():
                    t_attr.Set(Gf.Vec3d(*translation))

        sensor_prim = stage.GetPrimAtPath(sensor_path)
        if sensor_prim.IsValid():
            custom = sensor_prim.GetCustomData() or {}
            block = dict(custom.get("validation_api") or {})
            block["sensor_type"] = "contact"
            block["frequency"] = frequency
            block["radius"] = radius
            block["backend"] = backend
            custom["validation_api"] = block
            sensor_prim.SetCustomData(custom)

        return {
            "ok": True,
            "sensor_prim_path": sensor_path,
            "parent_prim": parent_prim,
            "sensor_type": "contact",
            "frequency": frequency,
            "translation": [float(t) for t in translation],
            "radius": radius,
            "backend": backend,
        }

    async def attach_imu(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach an ``isaacsim.sensors.experimental.physics.IMU`` child prim (Phase G).

        Same fallback pattern as :meth:`attach_contact`.
        """
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf

        parent_prim = request["prim_path"]
        sensor_name = request.get("sensor_name") or "IMUSensor"
        frequency = int(request.get("frequency", 200))
        mount_offset = request.get("mount_offset") or [0.0, 0.0, 0.0]
        mount_orientation = request.get("mount_orientation") or [1.0, 0.0, 0.0, 0.0]

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        if not stage.GetPrimAtPath(parent_prim).IsValid():
            raise ValueError(f"Parent prim {parent_prim!r} not found for IMU sensor")

        sensor_path = _safe_child_path(parent_prim, sensor_name)
        backend = "isaacsim.sensors.experimental.physics.IMU.create"

        try:
            import numpy as np  # lazy
            from isaacsim.sensors.experimental.physics import IMU  # type: ignore[import-not-found]

            IMU.create(
                sensor_path,
                translations=np.array([mount_offset], dtype=float),
                orientations=np.array([mount_orientation], dtype=float),
            )
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_xform:{type(exc).__name__}"
            omni.kit.commands.execute(
                "CreatePrimWithDefaultXformCommand",
                prim_type="Xform",
                prim_path=sensor_path,
            )
            prim = stage.GetPrimAtPath(sensor_path)
            if prim.IsValid():
                t_attr = prim.GetAttribute("xformOp:translate")
                if t_attr.IsValid():
                    t_attr.Set(Gf.Vec3d(*mount_offset))

        sensor_prim = stage.GetPrimAtPath(sensor_path)
        if sensor_prim.IsValid():
            custom = sensor_prim.GetCustomData() or {}
            block = dict(custom.get("validation_api") or {})
            block["sensor_type"] = "imu"
            block["frequency"] = frequency
            block["mount_orientation"] = list(mount_orientation)
            block["backend"] = backend
            custom["validation_api"] = block
            sensor_prim.SetCustomData(custom)

        return {
            "ok": True,
            "sensor_prim_path": sensor_path,
            "parent_prim": parent_prim,
            "sensor_type": "imu",
            "frequency": frequency,
            "mount_offset": [float(t) for t in mount_offset],
            "mount_orientation": [float(q) for q in mount_orientation],
            "backend": backend,
        }

    async def set_annotator(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach replicator annotators to a sensor camera prim (Phase G).

        Creates a render product from the sensor prim and attaches each
        requested annotator via ``AnnotatorRegistry.get_annotator``.
        Unknown annotator names raise HTTP 400; known annotators that
        fail to attach (missing module) are collected into ``skipped``.
        """
        import omni.usd  # lazy

        sensor_prim_path = request["sensor_prim"]
        annotators = list(request.get("annotators") or [])
        resolution = request.get("resolution") or [1280, 720]

        if not annotators:
            raise ValueError("annotators list must not be empty")
        valid_set = {
            "rgb", "depth", "semantic_segmentation", "instance_segmentation",
            "normals", "motion_vectors",
            "distance_to_camera", "distance_to_image_plane",
        }
        unknown = [a for a in annotators if a not in valid_set]
        if unknown:
            raise ValueError(
                f"Unknown annotator(s): {unknown!r}. Valid: {sorted(valid_set)}"
            )

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        sensor_prim = stage.GetPrimAtPath(sensor_prim_path)
        if not sensor_prim.IsValid():
            raise ValueError(f"Sensor prim {sensor_prim_path!r} not found")

        attached: list[str] = []
        skipped: dict[str, str] = {}
        backend = "omni.replicator.core"
        render_product_path: str | None = None

        try:
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            render_product = rep.create.render_product(
                sensor_prim_path, (int(resolution[0]), int(resolution[1])),
            )
            render_product_path = str(render_product)
            for name in annotators:
                try:
                    annot = rep.AnnotatorRegistry.get_annotator(name)
                    annot.attach(render_product)
                    attached.append(name)
                except Exception as exc:  # noqa: BLE001
                    skipped[name] = f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"
            # Record requested annotators on sensor customData only
            for name in annotators:
                attached.append(name)

        # Stamp annotator names on sensor prim metadata (survives capture path)
        custom = sensor_prim.GetCustomData() or {}
        block = dict(custom.get("validation_api") or {})
        block["annotators"] = attached
        block["annotator_resolution"] = [int(resolution[0]), int(resolution[1])]
        if render_product_path:
            block["render_product"] = render_product_path
        custom["validation_api"] = block
        sensor_prim.SetCustomData(custom)

        return {
            "ok": True,
            "sensor_prim": sensor_prim_path,
            "annotators": attached,
            "skipped": skipped,
            "resolution": [int(resolution[0]), int(resolution[1])],
            "backend": backend,
            "render_product": render_product_path,
        }

    async def lidar_get_point_cloud(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Read one frame of RTX Lidar point cloud data.

        Symmetric readback for ``attach_rtx_lidar``. Reuses the annotator
        name stamped on the sensor prim by ``attach_rtx_lidar``
        (``IsaacCreateRTXLidarScanBuffer`` by default), creates
        a render product, attaches the annotator, awaits *frames_to_wait*
        Kit ticks, and reads ``annotator.get_data()``.

        Returns Cartesian XYZ points + intensities (when available),
        truncated to *max_points* if the raw cloud is larger. ``backend``
        field reports which path won (``omni.replicator.core`` or fallback
        with reason). Empty data → ``num_points=0`` with ``warning`` field
        explaining why (typically "no data yet — call simulation_play").
        """
        import omni.usd

        sensor_prim_path = request["sensor_prim"]
        max_points = int(request.get("max_points", 1000))
        frames_to_wait = max(1, int(request.get("frames_to_wait", 2)))

        if max_points <= 0:
            raise ValueError("max_points must be positive")
        if max_points > 100000:
            raise ValueError("max_points capped at 100000 (response size)")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        sensor_prim = stage.GetPrimAtPath(sensor_prim_path)
        if not sensor_prim.IsValid():
            raise ValueError(f"Sensor prim {sensor_prim_path!r} not found")

        custom = sensor_prim.GetCustomData() or {}
        block = dict(custom.get("validation_api") or {})
        sensor_type = block.get("sensor_type")
        if sensor_type != "rtx_lidar":
            raise ValueError(
                f"Sensor at {sensor_prim_path} is not rtx_lidar "
                f"(got sensor_type={sensor_type!r}). "
                "Use sensor_attach_rtx_lidar first."
            )

        annotator_name = block.get(
            "annotator", "IsaacCreateRTXLidarScanBuffer",
        )

        backend = "omni.replicator.core"
        warning: str | None = None
        points: list[list[float]] = []
        intensities: list[float] = []
        raw_keys: list[str] = []
        truncated = False

        # Preferred path: a cached live LidarSensor instance (kept alive from
        # attach) whose internal render product is bound to the GMO scan
        # buffer. Isaac Sim 6.0 exposes readback through get_data().
        # A fresh annotator on a throwaway render product (legacy path below)
        # returns empty because the lidar runtime isn't bound to it.
        cached = self._lidar_instances.get(sensor_prim_path)
        if cached is not None:
            try:
                import omni.kit.app
                from isaacsim.sensors.experimental.rtx import parse_generic_model_output_data  # type: ignore[import-not-found]

                app = omni.kit.app.get_app()
                for _ in range(frames_to_wait):
                    await app.next_update_async()
                frame_raw = cached.get_data("generic-model-output")
                frame = frame_raw
                if isinstance(frame_raw, tuple) and len(frame_raw) == 2:
                    gmo_raw = frame_raw[0]
                    info = frame_raw[1] or {}
                    if gmo_raw is not None:
                        try:
                            gmo = parse_generic_model_output_data(gmo_raw)
                            (
                                points,
                                intensities,
                                raw_keys,
                                truncated,
                            ) = _extract_gmo_points(gmo, max_points)
                            if isinstance(info, dict):
                                (
                                    info_points,
                                    info_intensities,
                                    info_raw_keys,
                                    info_truncated,
                                    info_warning,
                                ) = _extract_scan_dict_points(info, max_points)
                                raw_keys = sorted({*raw_keys, *info_raw_keys})
                                if info_points:
                                    points = info_points
                                    intensities = info_intensities
                                    truncated = info_truncated
                                elif info_warning:
                                    raw_keys.append(f"info_warning:{info_warning}")
                            if points:
                                return {
                                    "ok": True,
                                    "sensor_prim": sensor_prim_path,
                                    "annotator": "generic-model-output",
                                    "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
                                    "num_points": len(points),
                                    "points": points,
                                    "intensities": intensities,
                                    "truncated": truncated,
                                    "frames_waited": frames_to_wait,
                                    "raw_keys": raw_keys,
                                    "warning": None,
                                }
                            warning = (
                                "parsed generic-model-output contained "
                                f"{getattr(gmo, 'numElements', 0)} elements but no "
                                "usable point data"
                            )
                        except Exception as exc:  # noqa: BLE001
                            warning = f"generic-model-output parse failed: {exc}"
                if isinstance(frame_raw, tuple) and len(frame_raw) == 2:
                    frame = {"data": frame_raw[0], **(frame_raw[1] or {})}
                if isinstance(frame, dict):
                    (
                        legacy_points,
                        legacy_intensities,
                        legacy_raw_keys,
                        legacy_truncated,
                        legacy_warning,
                    ) = _extract_scan_dict_points(frame, max_points)
                    raw_keys = sorted({*raw_keys, *legacy_raw_keys})
                    if legacy_points:
                        points = legacy_points
                        intensities = legacy_intensities
                        truncated = legacy_truncated
                    elif legacy_warning and warning is None:
                        warning = legacy_warning
                if points:
                    return {
                        "ok": True,
                        "sensor_prim": sensor_prim_path,
                        "annotator": annotator_name,
                        "backend": "isaacsim.sensors.experimental.rtx.LidarSensor",
                        "num_points": len(points),
                        "points": points,
                        "intensities": intensities,
                        "truncated": truncated,
                        "frames_waited": frames_to_wait,
                        "raw_keys": raw_keys,
                        "warning": None,
                    }
                if warning is None:
                    warning = "cached LidarSensor get_data returned no points yet"
                else:
                    warning = (
                        f"{warning}; cached LidarSensor legacy fallback also "
                        "returned no points"
                    )
            except Exception as exc:  # noqa: BLE001
                warning = f"cached LidarSensor readback failed: {exc}"

        try:
            import omni.kit.app
            import omni.replicator.core as rep  # type: ignore[import-not-found]

            # Render product must be >= 64x64 — a 1x1 product trips
            # "DLSS Skipped: Target resolution below 64x64" and on some RTX
            # setups a device-lost / GPU pagefault. The lidar scan data comes
            # from the sensor GMO buffer, not the product pixels, so a small
            # but valid 128x128 product is enough to drive the render graph.
            # force_new=True is REQUIRED — without it rep.create.render_product
            # reuses the default Replicator hydra texture (the viewport's
            # product) and the lidar's scan emitter is never bound, so
            # data stays empty (live-verified 2026-05-28: force_new=False
            # -> data_shape=[0]; force_new=True -> data_shape=[41180,3]).
            # The annotator must also be attached via [render_product.path] —
            # a LIST containing the path string (matches isaacsim.sensors.experimental.rtx
            # source pattern); passing the object directly does not bind.
            render_product = rep.create.render_product(
                sensor_prim_path, (128, 128), force_new=True,
            )
            annotator = rep.AnnotatorRegistry.get_annotator(annotator_name)
            try:
                annotator.initialize()
            except Exception:  # noqa: BLE001
                pass
            annotator.attach([render_product.path])

            app = omni.kit.app.get_app()
            for _ in range(frames_to_wait):
                await app.next_update_async()

            raw = annotator.get_data()

            # RTX Lidar scan buffer shape varies across Kit builds. Try the
            # common keys: dict with "data" (numpy structured) or with
            # "azimuth"/"elevation"/"distance"/"intensity" arrays.
            if raw is None or (hasattr(raw, "__len__") and len(raw) == 0):
                warning = (
                    "annotator.get_data() returned empty — call simulation_play "
                    "and wait for the lidar to spin, then retry"
                )
            else:
                if isinstance(raw, dict):
                    (
                        points,
                        intensities,
                        raw_keys,
                        truncated,
                        warning,
                    ) = _extract_scan_dict_points(raw, max_points)
                else:
                    raw_keys = ["<non-dict>"]
                    warning = (
                        f"annotator returned {type(raw).__name__} — expected dict; "
                        "Kit build may not be supported"
                    )
                # Dict shape may be present (non-empty key set) but every array
                # inside it can be length 0 — common pre-play / not-yet-spinning
                # case. Outer `len(raw)==0` check above only covers fully-empty
                # payloads; this guard catches dict-with-empty-arrays so the
                # caller still gets the retry hint.
                if not points and warning is None:
                    warning = (
                        "annotator returned dict with no usable point data — "
                        "ensure simulation_play is active and the lidar has spun"
                    )
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_noop:{type(exc).__name__}"
            warning = f"replicator path failed: {exc}"

        return {
            "ok": True,
            "sensor_prim": sensor_prim_path,
            "annotator": annotator_name,
            "backend": backend,
            "num_points": len(points),
            "points": points,
            "intensities": intensities,
            "truncated": truncated,
            "frames_waited": frames_to_wait,
            "raw_keys": raw_keys,
            "warning": warning,
        }

    async def set_visualization(self, request: dict[str, Any]) -> dict[str, Any]:
        """Toggle the Debug Draw overlay for a previously attached sensor.

        Implementation is visibility-based: we flip the sensor prim's
        ``visibility`` token. Richer backends (Lidar point-cloud Debug Draw
        node, Depth preview overlay) are gated on Kit modules that are not
        always loaded — visibility is the common-denominator toggle that
        works headless-or-GUI.
        """
        import omni.usd

        sensor_prim_path = request["sensor_prim"]
        mode = request.get("mode", "on")
        if mode not in ("on", "off"):
            raise ValueError("mode must be 'on' | 'off'")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(sensor_prim_path)
        if not prim.IsValid():
            raise ValueError(f"Sensor prim {sensor_prim_path!r} not found")

        vis_attr = prim.GetAttribute("visibility")
        token = "inherited" if mode == "on" else "invisible"
        if vis_attr.IsValid():
            vis_attr.Set(token)

        custom = prim.GetCustomData() or {}
        sensor_type = (
            (custom.get("validation_api") or {}).get("sensor_type")
        )
        return {
            "ok": True,
            "sensor_prim": sensor_prim_path,
            "mode": mode,
            "sensor_type": sensor_type,
            "visibility": token,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_name(sensor_type: str) -> str:
    if sensor_type not in _SUPPORTED_TYPES:
        raise ValueError(f"Unsupported sensor_type: {sensor_type}")
    return {
        "rtx_camera": "RtxCamera",
        "rtx_lidar": "RtxLidar",
        "rtx_depth_camera": "RtxDepthCamera",
    }[sensor_type]


def _safe_child_path(parent_path: str, child_name: str) -> str:
    """Concatenate parent + child, sanitizing child to USD-legal chars."""
    sanitized = "".join(
        c if (c.isalnum() or c == "_") else "_"
        for c in child_name
    ) or "Sensor"
    if sanitized[0].isdigit():
        sanitized = f"s_{sanitized}"
    parent = parent_path.rstrip("/")
    return f"{parent}/{sanitized}"


def _extract_gmo_points(
    gmo: Any, max_points: int,
) -> tuple[list[list[float]], list[float], list[str], bool]:
    """Extract XYZ points from Isaac Sim GenericModelOutput."""
    num_elements = max(0, int(getattr(gmo, "numElements", 0) or 0))
    coords_type = _enum_token(
        getattr(gmo, "elementsCoordsType", getattr(gmo, "coordsType", "unknown")),
    )
    raw_keys = [
        "generic-model-output",
        f"coords_type:{coords_type}",
        f"num_elements:{num_elements}",
    ]
    if num_elements == 0:
        return [], [], raw_keys, False

    elements = getattr(gmo, "elements", None)
    if elements is None:
        raw_keys.append("missing:elements")
        return [], [], raw_keys, False

    xs = getattr(elements, "x", None)
    ys = getattr(elements, "y", None)
    zs = getattr(elements, "z", None)
    scalars = getattr(elements, "scalar", None)
    n = min(num_elements, max_points)
    truncated = num_elements > max_points
    cartesian = "cartesian" in coords_type.lower()

    points: list[list[float]] = []
    intensities: list[float] = []
    for index in range(n):
        x = _float_at(xs, index)
        y = _float_at(ys, index)
        z = _float_at(zs, index)
        if x is None or y is None or z is None:
            continue
        if cartesian:
            points.append([x, y, z])
        else:
            azimuth = math.radians(x)
            elevation = math.radians(y)
            distance = z
            points.append([
                distance * math.cos(elevation) * math.cos(azimuth),
                distance * math.cos(elevation) * math.sin(azimuth),
                distance * math.sin(elevation),
            ])
        intensity = _float_at(scalars, index)
        if intensity is not None:
            intensities.append(intensity)
    return points, intensities, raw_keys, truncated


def _extract_scan_dict_points(
    raw: dict[str, Any], max_points: int,
) -> tuple[list[list[float]], list[float], list[str], bool, str | None]:
    """Extract point-cloud rows from annotator dict payloads."""
    raw_keys = sorted(str(k) for k in raw.keys())
    points: list[list[float]] = []
    intensities: list[float] = []
    truncated = False
    warning: str | None = None

    if "data" in raw and raw["data"] is not None:
        struct = raw["data"]
        try:
            names = getattr(getattr(struct, "dtype", None), "names", None)
            shape = getattr(struct, "shape", None)
            if (
                names is None and shape is not None
                and len(shape) == 2 and shape[1] == 3
            ):
                n = min(int(shape[0]), max_points)
                truncated = int(shape[0]) > max_points
                for i in range(n):
                    row = struct[i]
                    points.append([float(row[0]), float(row[1]), float(row[2])])
                intensities = _extract_intensities(raw.get("intensity"), n)
            elif names is not None:
                xs = struct["x"] if "x" in names else None
                ys = struct["y"] if "y" in names else None
                zs = struct["z"] if "z" in names else None
                if xs is not None and ys is not None and zs is not None:
                    n = min(len(xs), max_points)
                    truncated = len(xs) > max_points
                    for i in range(n):
                        points.append([float(xs[i]), float(ys[i]), float(zs[i])])
                    ints = struct["intensity"] if "intensity" in names else None
                    intensities = _extract_intensities(ints, n)
        except Exception as exc:  # noqa: BLE001
            warning = f"field extraction failed: {exc}"

    if not points and all(k in raw for k in ("azimuth", "elevation", "distance")):
        az = raw["azimuth"]
        el = raw["elevation"]
        dist = raw["distance"]
        n_total = _min_sequence_length(az, el, dist)
        if n_total is None:
            warning = "polar field extraction failed: missing array length"
        elif n_total == 0:
            warning = "polar arrays contained 0 elements"
        else:
            n = min(n_total, max_points)
            truncated = n_total > max_points
            for i in range(n):
                d = _float_at(dist, i)
                a = _float_at(az, i)
                e = _float_at(el, i)
                if d is None or a is None or e is None:
                    continue
                a_rad = math.radians(a)
                e_rad = math.radians(e)
                points.append([
                    d * math.cos(e_rad) * math.cos(a_rad),
                    d * math.cos(e_rad) * math.sin(a_rad),
                    d * math.sin(e_rad),
                ])
            intensities = _extract_intensities(raw.get("intensity"), len(points))
            if not points and warning is None:
                warning = "polar arrays had no usable numeric point data"

    return points, intensities, raw_keys, truncated, warning


def _enum_token(value: Any) -> str:
    return str(getattr(value, "name", value))


def _min_sequence_length(*values: Any) -> int | None:
    lengths: list[int] = []
    for value in values:
        try:
            lengths.append(len(value))
        except Exception:  # noqa: BLE001
            return None
    return min(lengths)


def _extract_intensities(values: Any, count: int) -> list[float]:
    intensities: list[float] = []
    for index in range(count):
        intensity = _float_at(values, index)
        if intensity is not None:
            intensities.append(intensity)
    return intensities


def _float_at(values: Any, index: int) -> float | None:
    if values is None:
        return None
    try:
        raw = values[index]
    except Exception:  # noqa: BLE001
        return None
    try:
        item = raw.item
    except AttributeError:
        item = None
    if callable(item):
        raw = item()
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
