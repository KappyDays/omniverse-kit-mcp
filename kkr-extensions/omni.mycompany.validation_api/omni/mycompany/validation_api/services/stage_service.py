"""Stage service — USD Stage operations (live Isaac Sim environment).

All omni.*/pxr.* imports are lazy (inside functions) per API rule #7.
"""

from __future__ import annotations

import logging
import math
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_world_default_prim(stage) -> None:
    """Ensure `/World` Xform exists and is set as stage default prim.
    2026-04-20 실측: asset load (Reference/Payload) 시 stage 에 /World default prim 이
    없으면 MDL resolver 가 reference target context 를 잡지 못해 OmniPBR.mdl "Disabling
    base URL" 루프에 빠짐. stage_new / stage_open / stage_load_usd 진입 시 공통 호출."""
    from pxr import UsdGeom

    world_path = "/World"
    world_prim = stage.GetPrimAtPath(world_path)
    if not world_prim.IsValid():
        world_prim = UsdGeom.Xform.Define(stage, world_path).GetPrim()
    if stage.GetDefaultPrim() != world_prim:
        stage.SetDefaultPrim(world_prim)


class StageService:
    """Real implementation using omni.usd, omni.kit.commands, pxr."""

    async def compute_world_bbox(
        self,
        prim_path: str,
        include_purposes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return world-space axis-aligned bbox (min/max/center/size) + world
        translate + world orientation (WXYZ quaternion) of *prim_path*.

        Used for asset-aware placement (chair sit target, sensor mount offset, etc.).
        """
        import omni.usd  # lazy
        from pxr import Usd, UsdGeom  # lazy

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")

        purposes_map = {
            "default": UsdGeom.Tokens.default_,
            "proxy": UsdGeom.Tokens.proxy,
            "render": UsdGeom.Tokens.render,
            "guide": UsdGeom.Tokens.guide,
        }
        tokens = [purposes_map[p] for p in (include_purposes or ["default", "render"])
                  if p in purposes_map]
        if not tokens:
            tokens = [UsdGeom.Tokens.default_]

        bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), tokens, useExtentsHint=True)
        world_bbox = bbox_cache.ComputeWorldBound(prim)
        aligned = world_bbox.ComputeAlignedRange()
        mn, mx, ctr, sz = aligned.GetMin(), aligned.GetMax(), aligned.GetMidpoint(), aligned.GetSize()

        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        world_xform = xform_cache.GetLocalToWorldTransform(prim)
        translate = world_xform.ExtractTranslation()
        rot_quat = world_xform.ExtractRotationQuat()
        imag = rot_quat.GetImaginary()

        return {
            "ok": True,
            "prim_path": prim_path,
            "min": [mn[0], mn[1], mn[2]],
            "max": [mx[0], mx[1], mx[2]],
            "center": [ctr[0], ctr[1], ctr[2]],
            "size": [sz[0], sz[1], sz[2]],
            "world_translate": [translate[0], translate[1], translate[2]],
            "world_orient_wxyz": [rot_quat.GetReal(), imag[0], imag[1], imag[2]],
            "is_empty": bool(aligned.IsEmpty()),
        }

    async def capture_snapshot(self, capture_filter: dict[str, Any]) -> dict[str, Any]:
        """Traverse stage and collect prim information."""
        import omni.usd  # lazy import

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        include_patterns = capture_filter.get("include_prim_patterns", ["*"])
        exclude_patterns = capture_filter.get("exclude_prim_patterns", [])
        include_properties = capture_filter.get("include_properties", True)
        include_metadata = capture_filter.get("include_metadata", True)
        max_prim_count = capture_filter.get("max_prim_count", 10000)

        prims: dict[str, Any] = {}
        count = 0
        for prim in stage.Traverse():
            if count >= max_prim_count:
                break

            path = str(prim.GetPath())

            if not _matches_patterns(path, include_patterns, exclude_patterns):
                continue

            prim_data: dict[str, Any] = {
                "type_name": prim.GetTypeName(),
                "active": prim.IsActive(),
                "defined": prim.IsDefined(),
                "instanceable": prim.IsInstanceable(),
            }

            if include_properties:
                attributes: dict[str, Any] = {}
                for attr in prim.GetAttributes():
                    try:
                        val = attr.Get()
                        attributes[attr.GetName()] = {
                            "type_name": str(attr.GetTypeName()),
                            "value": _serialize_usd_value(val),
                        }
                    except Exception:
                        pass
                prim_data["attributes"] = attributes

                relationships: dict[str, list[str]] = {}
                for rel in prim.GetRelationships():
                    targets = rel.GetTargets()
                    relationships[rel.GetName()] = [str(t) for t in targets]
                prim_data["relationships"] = relationships

            if include_metadata:
                metadata: dict[str, Any] = {}
                for key in prim.GetAllMetadata():
                    try:
                        val = prim.GetMetadata(key)
                        metadata[key] = _serialize_usd_value(val)
                    except Exception:
                        pass
                prim_data["metadata"] = metadata

            prims[path] = prim_data
            count += 1

        root_layer = stage.GetRootLayer()
        return {
            "root_layer_identifier": root_layer.identifier if root_layer else "",
            "stage_identifier": root_layer.identifier if root_layer else "",
            "default_prim": (
                stage.GetDefaultPrim().GetName() if stage.HasDefaultPrim() else None
            ),
            "prims": prims,
            "captured_at_epoch_ms": int(time.time() * 1000),
            "capture_filter": capture_filter,
        }

    async def load_usd(self, request: dict[str, Any]) -> dict[str, Any]:
        """Load a USD payload into the stage at *prim_path*.

        2026-04-20 사용자 실증: isaac-sim.bat Kit (Extension 없음) + GUI drag&drop 은
        `CreatePayloadCommand(instanceable=True)` 로 static asset load 성공. 하지만 Extension
        이 load 된 Kit 에서 GUI drag&drop 조차 hang — FastAPI handler 의 event loop 가 Kit
        main event loop 와 분리되어 command 가 main loop 에서 실행되지 못함. 해결:
        `omni.kit.async_engine.run_coroutine()` 으로 coroutine 을 Kit main loop 에 명시적으로
        schedule + `asyncio.wrap_future` 로 async handler 가 await. Robot/articulation load 는
        별도 service 에서 `instanceable=False` 예외를 사용.
        """
        import asyncio
        import omni.kit.async_engine  # lazy
        import omni.kit.commands
        import omni.usd
        from pxr import Gf, Usd, UsdGeom

        usd_url: str = request["usd_url"].replace("\\", "/")  # USD needs forward slashes
        prim_path: str = request["prim_path"]
        position: list[float] | None = request.get("position")
        rotation: list[float] | None = request.get("rotation")

        async def _main_loop_impl():
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()
            if stage is None:
                raise RuntimeError("No USD stage available")

            # GUI drag&drop 동등: Payload 방식 + instanceable=True
            omni.kit.commands.execute(
                "CreatePayloadCommand",
                usd_context=ctx,
                path_to=prim_path,
                asset_path=usd_url,
                instanceable=True,
            )

            # Wait for stage loading — main loop 에서 실행되므로 tick 진행 가능
            await _wait_stage_loading()

            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                raise RuntimeError(f"Prim not found at {prim_path} after loading")
            if prim.HasPayload():
                stage.Load(prim.GetPath(), Usd.LoadWithDescendants)
                await _wait_stage_loading()
                prim = stage.GetPrimAtPath(prim_path)

            load_mode = "payload"
            if not list(prim.GetChildren()) and prim.GetTypeName() in ("", "Xform"):
                stage.RemovePrim(prim.GetPath())
                ref_prim = UsdGeom.Xform.Define(stage, prim_path).GetPrim()
                ref_prim.GetReferences().AddReference(usd_url)
                await _wait_stage_loading()
                prim = stage.GetPrimAtPath(prim_path)
                load_mode = "reference_fallback"

            return prim, load_mode

        # Kit main event loop 에 coroutine schedule → concurrent.futures.Future 반환
        # (non-main thread 에서 호출되므로 run_coroutine_threadsafe 경로)
        future = omni.kit.async_engine.run_coroutine(_main_loop_impl())
        # asyncio 방식 await — FastAPI loop 는 free → Kit main loop 는 자기 tick 진행
        prim, load_mode = await asyncio.wrap_future(future)

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()

        # API 특이사항 #16: 빈 Xform prim 생성 검사 (S3 404 등)
        children = list(prim.GetChildren())
        if not children and prim.GetTypeName() in ("", "Xform"):
            logger.warning(
                "Loaded prim at %s has no children — asset may have failed to resolve: %s",
                prim_path, usd_url,
            )

        # Set transform — use existing xformOps if present
        if position is not None:
            attr = prim.GetAttribute("xformOp:translate")
            if attr.IsValid():
                attr.Set(Gf.Vec3d(*position))
            else:
                UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*position))
            if rotation is not None:
                rot_attr = prim.GetAttribute("xformOp:rotateXYZ")
                if rot_attr.IsValid():
                    rot_attr.Set(Gf.Vec3f(*rotation))
                else:
                    UsdGeom.Xformable(prim).AddRotateXYZOp().Set(Gf.Vec3f(*rotation))

        return {
            "ok": True,
            "prim_path": prim_path,
            "type_name": prim.GetTypeName(),
            "usd_url": usd_url,
            "has_children": len(children) > 0,
            "load_mode": load_mode,
        }

    async def set_property(self, request: dict[str, Any]) -> dict[str, Any]:
        """Set a property value on a prim."""
        import omni.usd  # lazy

        prim_path: str = request["prim_path"]
        property_name: str = request["property_name"]
        value = request["value"]
        type_hint: str | None = request.get("type_hint")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")

        attr = prim.GetAttribute(property_name)
        if not attr.IsValid():
            raise ValueError(f"Attribute '{property_name}' not found on {prim_path}")

        typed_value = _convert_value(value, type_hint, attr)
        attr.Set(typed_value)

        return {
            "ok": True,
            "prim_path": prim_path,
            "property_name": property_name,
            "value": _serialize_usd_value(typed_value),
        }

    async def set_semantic_label(self, request: dict[str, Any]) -> dict[str, Any]:
        """Apply a semantic label to a prim so Replicator annotators classify it.

        Authors the OpenUSD-standard UsdSemantics.LabelsAPI
        (``semantics:labels:<label_type>``) and, best-effort, the legacy
        ``Semantics.SemanticsAPI`` that older Replicator builds read — so the
        label is picked up regardless of which schema the annotator honors.
        """
        import omni.usd  # lazy
        from pxr import UsdSemantics

        prim_path: str = request["prim_path"]
        label_class: str = request["label_class"]
        label_type: str = request.get("label_type", "class")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")

        applied: list[str] = []
        api = UsdSemantics.LabelsAPI.Apply(prim, label_type)
        api.CreateLabelsAttr([label_class])
        applied.append(f"SemanticsLabelsAPI:{label_type}")

        # Legacy Semantics schema (pre-UsdSemantics Replicator annotators).
        try:
            from pxr import Semantics

            sem = Semantics.SemanticsAPI.Apply(prim, f"Semantics_{label_type}")
            sem.CreateSemanticTypeAttr().Set(label_type)
            sem.CreateSemanticDataAttr().Set(label_class)
            applied.append("legacy_Semantics")
        except Exception:  # noqa: BLE001
            pass

        return {
            "ok": True,
            "prim_path": prim_path,
            "label_type": label_type,
            "label_class": label_class,
            "applied_schemas": applied,
        }

    async def create_prim(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create a new prim in the stage."""
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf, UsdGeom

        prim_path: str = request["prim_path"]
        prim_type: str = request.get("prim_type", "Xform")
        position: list[float] | None = request.get("position")

        omni.kit.commands.execute(
            "CreatePrimWithDefaultXformCommand",
            prim_path=prim_path,
            prim_type=prim_type,
        )

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise RuntimeError(f"Failed to create prim at {prim_path}")

        if position is not None:
            # CreatePrimWithDefaultXformCommand already adds xformOps —
            # set the existing attribute instead of adding a duplicate op.
            attr = prim.GetAttribute("xformOp:translate")
            if attr.IsValid():
                attr.Set(Gf.Vec3d(*position))
            else:
                UsdGeom.Xformable(prim).AddTranslateOp().Set(Gf.Vec3d(*position))

        return {
            "ok": True,
            "prim_path": prim_path,
            "prim_type": prim_type,
        }

    async def delete_prim(self, prim_path: str) -> dict[str, Any]:
        """Delete a prim from the stage."""
        import omni.kit.commands  # lazy
        import omni.usd

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")

        omni.kit.commands.execute("DeletePrimsCommand", paths=[prim_path])

        return {"ok": True, "prim_path": prim_path}

    # ------------------------------------------------------------------
    # File / Selection / Camera — GUI-equivalent operations (Phase B+)
    # ------------------------------------------------------------------

    async def save_stage(self, path: str | None = None) -> dict[str, Any]:
        """Save the current stage (File → Save / Save As)."""
        import omni.usd  # lazy

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            raise RuntimeError("No USD stage to save")

        if path:
            normalized = path.replace("\\", "/")
            result = ctx.save_as_stage(normalized)
            return {
                "ok": bool(result),
                "path": normalized,
                "mode": "save_as",
            }
        result = ctx.save_stage()
        return {
            "ok": bool(result),
            "path": stage.GetRootLayer().identifier if stage.GetRootLayer() else None,
            "mode": "save",
        }

    async def open_stage(self, url: str) -> dict[str, Any]:
        """Open a USD stage (File → Open). Waits for the stage to finish loading."""
        import omni.usd  # lazy

        normalized = url.replace("\\", "/")
        ctx = omni.usd.get_context()
        result, error = await ctx.open_stage_async(normalized)
        if not result:
            raise RuntimeError(
                f"Failed to open stage {normalized}: {error or 'unknown error'}"
            )
        await _wait_stage_loading()
        stage = ctx.get_stage()
        return {
            "ok": True,
            "url": normalized,
            "root_layer": stage.GetRootLayer().identifier if stage and stage.GetRootLayer() else None,
        }

    async def new_stage(self) -> dict[str, Any]:
        """Create a new empty stage (File → New)."""
        import omni.usd  # lazy

        ctx = omni.usd.get_context()
        ok = ctx.new_stage()
        stage = ctx.get_stage()
        if stage is not None:
            _ensure_world_default_prim(stage)
        return {
            "ok": bool(ok),
            "root_layer": stage.GetRootLayer().identifier if stage and stage.GetRootLayer() else None,
        }

    async def get_selection(self) -> dict[str, Any]:
        """Return the current Stage panel selection (prim paths)."""
        import omni.usd  # lazy

        ctx = omni.usd.get_context()
        sel = ctx.get_selection()
        paths = list(sel.get_selected_prim_paths() or [])
        return {"ok": True, "selected_prim_paths": paths, "count": len(paths)}

    async def set_selection(
        self,
        prim_paths: list[str],
        expand_in_stage: bool = True,
    ) -> dict[str, Any]:
        """Replace the Stage panel selection with *prim_paths*."""
        import omni.usd  # lazy

        ctx = omni.usd.get_context()
        sel = ctx.get_selection()
        sel.set_selected_prim_paths(list(prim_paths), expand_in_stage)
        return {
            "ok": True,
            "selected_prim_paths": list(prim_paths),
            "count": len(prim_paths),
        }

    async def assert_prim_exists(self, assertion: dict[str, Any]) -> dict[str, Any]:
        """Check if a prim exists with expected properties."""
        import omni.usd  # lazy

        prim_path: str = assertion["prim_path"]
        should_exist: bool = assertion.get("should_exist", True)
        expected_type: str | None = assertion.get("expected_type_name")
        expected_active: bool | None = assertion.get("expected_active")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return {
                "passed": False,
                "failures": [{"code": "NO_STAGE", "message": "No USD stage available"}],
                "checked_count": 0,
            }

        prim = stage.GetPrimAtPath(prim_path)
        exists = prim.IsValid()
        failures: list[dict[str, Any]] = []

        if should_exist and not exists:
            failures.append({
                "code": "PRIM_NOT_FOUND",
                "message": f"Prim {prim_path} does not exist",
                "prim_path": prim_path,
            })
        elif not should_exist and exists:
            failures.append({
                "code": "PRIM_EXISTS",
                "message": f"Prim {prim_path} exists but should not",
                "prim_path": prim_path,
            })
        elif exists:
            if expected_type and prim.GetTypeName() != expected_type:
                failures.append({
                    "code": "TYPE_MISMATCH",
                    "message": f"Expected type '{expected_type}', got '{prim.GetTypeName()}'",
                    "prim_path": prim_path,
                    "actual": {"type_name": "string", "value": prim.GetTypeName()},
                    "expected": {"type_name": "string", "value": expected_type},
                })
            if expected_active is not None and prim.IsActive() != expected_active:
                failures.append({
                    "code": "ACTIVE_MISMATCH",
                    "message": f"Expected active={expected_active}, got {prim.IsActive()}",
                    "prim_path": prim_path,
                    "actual": {"type_name": "bool", "value": prim.IsActive()},
                    "expected": {"type_name": "bool", "value": expected_active},
                })

        return {"passed": len(failures) == 0, "failures": failures, "checked_count": 1}

    async def assert_property(self, assertion: dict[str, Any]) -> dict[str, Any]:
        """Assert property value on a prim."""
        import omni.usd  # lazy

        prim_path: str = assertion["prim_path"]
        property_name: str = assertion["property_name"]
        property_type: str = assertion.get("property_type", "attribute")
        comparator: str = assertion.get("comparator", "equals")
        expected_value = assertion.get("expected_value")
        expected_type_name: str | None = assertion.get("expected_type_name")
        tolerance: float | None = assertion.get("tolerance")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return {
                "passed": False,
                "failures": [{"code": "NO_STAGE", "message": "No USD stage available"}],
                "checked_count": 0,
            }

        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return {
                "passed": False,
                "failures": [{
                    "code": "PRIM_NOT_FOUND",
                    "message": f"Prim not found at {prim_path}",
                    "prim_path": prim_path,
                }],
                "checked_count": 0,
            }

        failures: list[dict[str, Any]] = []

        if property_type == "relationship":
            failures = _assert_relationship(prim, prim_path, property_name, comparator, expected_value)
        else:
            failures = _assert_attribute(
                prim, prim_path, property_name, comparator,
                expected_value, expected_type_name, tolerance,
            )

        return {"passed": len(failures) == 0, "failures": failures, "checked_count": 1}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _wait_stage_loading(max_frames: int = 600) -> None:
    """Wait until all USD assets have finished loading."""
    import omni.kit.app  # lazy

    app = omni.kit.app.get_app()
    for _ in range(max_frames):
        await app.next_update_async()
        if not _is_stage_loading():
            return


def _is_stage_loading() -> bool:
    try:
        from isaacsim.core.experimental.utils.stage import is_stage_loading
        return is_stage_loading()
    except ImportError:
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            _, files_loaded, total_files = ctx.get_stage_loading_status()
            return total_files > 0 and files_loaded < total_files
        except Exception:
            return False


def _matches_patterns(
    path: str,
    include: list[str],
    exclude: list[str],
) -> bool:
    """Check if *path* matches include patterns and does not match exclude."""
    import fnmatch

    included = any(fnmatch.fnmatch(path, p) for p in include) if include else True
    excluded = any(fnmatch.fnmatch(path, p) for p in exclude) if exclude else False
    return included and not excluded


def _serialize_usd_value(val: Any) -> Any:
    """Convert a USD/Gf/Vt value to a JSON-serialisable Python object."""
    if val is None:
        return None

    # Python primitives
    if isinstance(val, (bool, int, float, str)):
        return val

    # numpy arrays
    if hasattr(val, "tolist"):
        return val.tolist()

    # Gf.Vec*, Gf.Quatd/f/h, Gf.Matrix* — they support len() and []
    type_name = type(val).__name__
    if type_name.startswith(("Vec", "Quat", "Matrix")):
        try:
            if type_name.startswith("Quat"):
                # Quaternions: (real, imaginary) — expose as [w, x, y, z]
                return [float(val.GetReal()), *[float(v) for v in val.GetImaginary()]]
            return [float(val[i]) for i in range(len(val))]
        except Exception:
            return str(val)

    # Sdf.AssetPath
    if "AssetPath" in type_name:
        return str(val.path) if hasattr(val, "path") else str(val)

    # VtArray, list, tuple
    if isinstance(val, (list, tuple)):
        return [_serialize_usd_value(v) for v in val]
    if hasattr(val, "__iter__") and hasattr(val, "__len__"):
        try:
            return [_serialize_usd_value(v) for v in val]
        except Exception:
            pass

    # dict-like
    if isinstance(val, dict):
        return {str(k): _serialize_usd_value(v) for k, v in val.items()}

    return str(val)


def _convert_value(value: Any, type_hint: str | None, attr: Any) -> Any:
    """Convert a JSON value to the appropriate USD type for *attr*.

    *type_hint* can be e.g. ``"Vec3d"``, ``"Vec3f"``, ``"Quatd"``,
    ``"float"``, ``"double"``, ``"int"``, ``"bool"``, ``"string"``,
    ``"asset"``, or ``None`` (auto-detect from *attr*).
    """
    from pxr import Gf, Sdf

    # If type_hint given, use it
    if type_hint:
        return _convert_by_hint(value, type_hint)

    # Auto-detect from attribute's current type
    attr_type = str(attr.GetTypeName())

    # Common mappings
    if "float3" in attr_type or "double3" in attr_type or "point3" in attr_type:
        if isinstance(value, (list, tuple)) and len(value) == 3:
            if "float" in attr_type:
                return Gf.Vec3f(*value)
            return Gf.Vec3d(*value)
    if "float2" in attr_type or "double2" in attr_type:
        if isinstance(value, (list, tuple)) and len(value) == 2:
            if "float" in attr_type:
                return Gf.Vec2f(*value)
            return Gf.Vec2d(*value)
    if "quatd" in attr_type or "quatf" in attr_type:
        if isinstance(value, (list, tuple)) and len(value) == 4:
            if "quatf" in attr_type:
                return Gf.Quatf(value[0], value[1], value[2], value[3])
            return Gf.Quatd(value[0], value[1], value[2], value[3])
    if "asset" in attr_type:
        return Sdf.AssetPath(str(value))
    if "bool" in attr_type:
        return bool(value)
    if "int" in attr_type:
        return int(value)
    if "string" in attr_type or "token" in attr_type:
        return str(value)
    if "float" in attr_type or "double" in attr_type:
        return float(value)

    # Fallback — return as-is and let USD try
    return value


def _convert_by_hint(value: Any, hint: str) -> Any:
    """Convert *value* according to explicit *hint*."""
    from pxr import Gf, Sdf

    h = hint.lower()
    if h in ("vec3d", "point3d", "double3"):
        return Gf.Vec3d(*value)
    if h in ("vec3f", "float3", "point3f"):
        return Gf.Vec3f(*value)
    if h in ("vec2d", "double2"):
        return Gf.Vec2d(*value)
    if h in ("vec2f", "float2"):
        return Gf.Vec2f(*value)
    if h in ("vec4d", "double4"):
        return Gf.Vec4d(*value)
    if h in ("vec4f", "float4"):
        return Gf.Vec4f(*value)
    if h in ("quatd",):
        return Gf.Quatd(value[0], value[1], value[2], value[3])
    if h in ("quatf",):
        return Gf.Quatf(value[0], value[1], value[2], value[3])
    if h in ("matrix4d",):
        return Gf.Matrix4d(*value)
    if h in ("asset", "assetpath"):
        return Sdf.AssetPath(str(value))
    if h in ("bool",):
        return bool(value)
    if h in ("int",):
        return int(value)
    if h in ("float", "double"):
        return float(value)
    if h in ("string", "token"):
        return str(value)
    return value


# -- Assertion helpers -------------------------------------------------------

def _assert_relationship(
    prim: Any,
    prim_path: str,
    property_name: str,
    comparator: str,
    expected_value: Any,
) -> list[dict[str, Any]]:
    rel = prim.GetRelationship(property_name)
    if not rel.IsValid():
        if comparator == "exists":
            return [{
                "code": "RELATIONSHIP_NOT_FOUND",
                "message": f"Relationship '{property_name}' not found",
                "prim_path": prim_path,
                "property_name": property_name,
            }]
        return [{
            "code": "RELATIONSHIP_NOT_FOUND",
            "message": f"Relationship '{property_name}' not found",
            "prim_path": prim_path,
            "property_name": property_name,
        }]

    actual_val = [str(t) for t in rel.GetTargets()]
    if comparator == "exists":
        return []
    if comparator == "equals" and actual_val != expected_value:
        return [{
            "code": "VALUE_MISMATCH",
            "message": f"Expected {expected_value}, got {actual_val}",
            "prim_path": prim_path,
            "property_name": property_name,
            "actual": {"type_name": "rel_targets", "value": actual_val},
            "expected": {"type_name": "rel_targets", "value": expected_value},
        }]
    return []


def _assert_attribute(
    prim: Any,
    prim_path: str,
    property_name: str,
    comparator: str,
    expected_value: Any,
    expected_type_name: str | None,
    tolerance: float | None,
) -> list[dict[str, Any]]:
    attr = prim.GetAttribute(property_name)
    if not attr.IsValid():
        return [{
            "code": "ATTR_NOT_FOUND",
            "message": f"Attribute '{property_name}' not found on {prim_path}",
            "prim_path": prim_path,
            "property_name": property_name,
        }]

    if comparator == "exists":
        return []

    actual_raw = attr.Get()
    actual_val = _serialize_usd_value(actual_raw)
    actual_type = str(attr.GetTypeName())

    def _fail(code: str, msg: str) -> list[dict[str, Any]]:
        return [{
            "code": code,
            "message": msg,
            "prim_path": prim_path,
            "property_name": property_name,
            "actual": {"type_name": actual_type, "value": actual_val},
            "expected": {"type_name": expected_type_name or actual_type, "value": expected_value},
        }]

    if comparator == "equals":
        if actual_val != expected_value:
            return _fail("VALUE_MISMATCH", f"Expected {expected_value}, got {actual_val}")
    elif comparator == "not_equals":
        if actual_val == expected_value:
            return _fail("VALUE_EQUALS", f"Expected value to differ from {expected_value}")
    elif comparator == "approx":
        tol = tolerance if tolerance is not None else 0.001
        if not _approx_equal(actual_val, expected_value, tol):
            return _fail("VALUE_NOT_APPROX", f"Expected ~{expected_value} (+-{tol}), got {actual_val}")
    elif comparator in ("gt", "gte", "lt", "lte"):
        threshold_failure = _numeric_threshold_failure(comparator, actual_val, expected_value)
        if threshold_failure is not None:
            return _fail(threshold_failure[0], threshold_failure[1])
    elif comparator == "contains":
        if not _contains(actual_val, expected_value):
            return _fail("VALUE_NOT_CONTAINS", f"Expected {actual_val} to contain {expected_value}")
    elif comparator == "regex":
        if not re.search(str(expected_value), str(actual_val)):
            return _fail("REGEX_MISMATCH", f"'{actual_val}' !~ /{expected_value}/")

    return []


def _approx_equal(actual: Any, expected: Any, tol: float) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(actual, expected, abs_tol=tol)
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        return all(_approx_equal(a, e, tol) for a, e in zip(actual, expected))
    return actual == expected


def _numeric_threshold_failure(
    comparator: str,
    actual: Any,
    expected: Any,
) -> tuple[str, str] | None:
    actual_num = _as_plain_number(actual)
    expected_num = _as_plain_number(expected)
    if actual_num is None or expected_num is None:
        return (
            "VALUE_NOT_NUMERIC",
            f"Expected numeric comparison {comparator} {expected}, got {actual}",
        )
    if comparator == "gt" and not actual_num > expected_num:
        return ("VALUE_AT_OR_BELOW_MIN", f"Expected > {expected}, got {actual}")
    if comparator == "gte" and not actual_num >= expected_num:
        return ("VALUE_BELOW_MIN", f"Expected >= {expected}, got {actual}")
    if comparator == "lt" and not actual_num < expected_num:
        return ("VALUE_AT_OR_ABOVE_MAX", f"Expected < {expected}, got {actual}")
    if comparator == "lte" and not actual_num <= expected_num:
        return ("VALUE_ABOVE_MAX", f"Expected <= {expected}, got {actual}")
    return None


def _as_plain_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return expected in actual
    if isinstance(actual, (list, tuple)):
        return expected in actual
    return False
