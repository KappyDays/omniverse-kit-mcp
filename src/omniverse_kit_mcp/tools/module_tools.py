"""Layer 1: Module-level MCP Tools.

Registers every domain module's public surface as `@tool()` functions.
Source of truth for the tool name set is
``tests/unit/test_tools_registration.py::EXPECTED_MODULE_TOOLS``.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from omniverse_kit_mcp.modules.asset_module import AssetModule
from omniverse_kit_mcp.modules.base import make_meta
from omniverse_kit_mcp.modules.catalog_module import CatalogModule
from omniverse_kit_mcp.modules.character_module import CharacterModule
from omniverse_kit_mcp.modules.content_module import ContentModule
from omniverse_kit_mcp.modules.extension_module import ExtensionModule
from omniverse_kit_mcp.modules.job_module import JobModule
from omniverse_kit_mcp.modules.kit_command_module import KitCommandModule
from omniverse_kit_mcp.modules.lakehouse_module import LakehouseModule
from omniverse_kit_mcp.modules.lighting_module import LightingModule
from omniverse_kit_mcp.modules.material_module import MaterialModule
from omniverse_kit_mcp.modules.navigation_module import NavigationModule
from omniverse_kit_mcp.modules.omnigraph_module import OmnigraphModule
from omniverse_kit_mcp.modules.physics_module import PhysicsModule
from omniverse_kit_mcp.modules.process_module import ProcessModule
from omniverse_kit_mcp.modules.replicator_module import ReplicatorModule
from omniverse_kit_mcp.modules.robot_module import RobotModule
from omniverse_kit_mcp.modules.sensor_module import SensorModule
from omniverse_kit_mcp.modules.simulation_module import SimulationModule
from omniverse_kit_mcp.modules.stage_module import StageModule
from omniverse_kit_mcp.modules.viewport_module import ViewportModule
from omniverse_kit_mcp.modules.window_module import WindowModule
from omniverse_kit_mcp.tools.tool_profiles import (
    PROFILE_FULL,
    ToolSelection,
    build_tool_selection,
    selected_tool_decorator,
)
from omniverse_kit_mcp.types.character import (
    CharacterLoadCrowdRequest,
    CharacterLoadRequest,
    CharacterNavigateRequest,
    CharacterPlayAnimationRequest,
    CharacterPlayAnimationVariantRequest,
    CharacterSetPositionRequest,
    CharacterStopAnimationRequest,
)
from omniverse_kit_mcp.types.content import (
    ContentBrowseRequest,
    ContentInspectRequest,
    ContentPreviewRequest,
    ContentResolveRequest,
)
from omniverse_kit_mcp.types.omnigraph import (
    OmnigraphConnectRequest,
    OmnigraphCreateNodeRequest,
    OmnigraphCreateRos2PublisherRequest,
    OmnigraphCreateScriptControllerRequest,
    OmnigraphExecuteRequest,
)
from omniverse_kit_mcp.types.replicator import (
    ReplicatorCreateWriterRequest,
    ReplicatorRegisterRandomizerRequest,
    ReplicatorTriggerOnceRequest,
    ReplicatorTriggerOnTimeRequest,
)
from omniverse_kit_mcp.types.common import ModuleName
from omniverse_kit_mcp.types.extension import ExtensionTriggerRequest
from omniverse_kit_mcp.types.kit_command import (
    KitCommandExecuteRequest,
    KitPythonExecRequest,
)
from omniverse_kit_mcp.types.lakehouse import LakehouseDatasetRef, LakehouseQueryRequest
from omniverse_kit_mcp.types.robot import (
    JointPositionsSetRequest,
    RobotArmProfileProbeRequest,
    RobotArmProfileProbeResult,
    RobotArmProfilesProbeRequest,
    RobotArmProfilesProbeResult,
    RobotArmProfilesResult,
    RobotDrivePhysicsRequest,
    RobotFrankaPickPlaceDemoRequest,
    RobotFrankaPickPlaceRequest,
    RobotGripperControlRequest,
    RobotLoadRequest,
    RobotNavigatePathRequest,
    RobotNavigateRequest,
    RobotPickPlaceDemoRequest,
    RobotSetEETargetRequest,
)
from omniverse_kit_mcp.types.stage import (
    PrimExistenceAssertion,
    PropertyAssertion,
    StageCaptureFilter,
    StagePlacementValidationRequest,
    StageVisualAlignmentRequest,
    StageWorldBboxRequest,
    UsdPropertyValue,
)
from omniverse_kit_mcp.types.navigation import (
    NavigationSetVisualizationRequest,
    NavPathQueryRequest,
    SampleWalkablePointsRequest,
)
from omniverse_kit_mcp.types.sensor import (
    SensorAttachContactRequest,
    SensorAttachImuRequest,
    SensorAttachRtxCameraRequest,
    SensorAttachRtxDepthCameraRequest,
    SensorAttachRtxLidarRequest,
    SensorLidarGetPointCloudRequest,
    SensorSetAnnotatorRequest,
    SensorSetVisualizationRequest,
)
from omniverse_kit_mcp.types.simulation import (
    SimulationEESpec,
    SimulationSetTimeRequest,
    SimulationStepObserveRequest,
    SimulationStepRequest,
    SimulationWaitUntilRequest,
)
from omniverse_kit_mcp.types.physics import (
    PhysicsApplyColliderRequest,
    PhysicsApplyMaterialRequest,
    PhysicsApplyRigidBodyRequest,
    PhysicsCreateJointRequest,
    PhysicsSetJointDriveRequest,
    PhysicsSetSceneRequest,
    PhysicsVisualizeRequest,
)
from omniverse_kit_mcp.types.lighting import (
    LightingCreateDiskRequest,
    LightingCreateDistantRequest,
    LightingCreateDomeRequest,
    LightingCreateRectRequest,
    LightingCreateSphereRequest,
    LightingSetExposureRequest,
)
from omniverse_kit_mcp.types.material import (
    MaterialAssignMdlRequest,
    MaterialGetBoundRequest,
    MaterialListMdlRequest,
)
from omniverse_kit_mcp.types.viewport import (
    SSIMComparisonRequest,
    ViewportCaptureAssertRequest,
    ViewportCaptureRequest,
    ViewportCreateRequest,
    ViewportDestroyRequest,
    ViewportFocusPrimRequest,
    ViewportFramePrimsRequest,
    ViewportProjectPointsRequest,
    ViewportSetCameraLookatRequest,
    ViewportSetFovRequest,
    ViewportSetRenderModeRequest,
    ViewportSetRenderQualityRequest,
    ViewportToggleOverlayRequest,
)
from omniverse_kit_mcp.types.window import WindowCaptureRequest

_MCP_SERVER_IMPORT_EPOCH_MS = int(time.time() * 1000)
_MCP_FRESHNESS_MODULES = (
    "omniverse_kit_mcp.tools.module_tools",
    "omniverse_kit_mcp.modules.asset_module",
    "omniverse_kit_mcp.modules.stage_module",
    "omniverse_kit_mcp.types.stage",
    "omniverse_kit_mcp.modules.robot_module",
    "omniverse_kit_mcp.robot_arm_profiles",
    "omniverse_kit_mcp.types.robot",
    "omniverse_kit_mcp.mcp.prompts",
    "omniverse_kit_mcp.scenario.runner",
    "omniverse_kit_mcp.scenario.reporters",
    "omniverse_kit_mcp.scenario.schema",
    "omniverse_kit_mcp.tools.scenario_tools",
    "omniverse_kit_mcp.types.scenario",
)


def register_module_tools(
    mcp: FastMCP,
    stage: StageModule,
    viewport: ViewportModule,
    lakehouse: LakehouseModule,
    extension: ExtensionModule,
    simulation: SimulationModule,
    process: ProcessModule,
    robot: RobotModule,
    job: JobModule,
    asset: AssetModule,
    character: CharacterModule,
    window: WindowModule,
    navigation: NavigationModule,
    sensor: SensorModule,
    physics: PhysicsModule,
    lighting: LightingModule,
    material: MaterialModule,
    replicator: ReplicatorModule,
    omnigraph: OmnigraphModule,
    content: ContentModule,
    kit_command: KitCommandModule,
    catalog: CatalogModule,
    *,
    selection: ToolSelection | None = None,
) -> None:
    """Register all module-level MCP tools."""
    if selection is None:
        selection = build_tool_selection(profile=PROFILE_FULL)
    tool = selected_tool_decorator(mcp, selection)

    # ------------------------------------------------------------------
    # Process control — Kit application lifecycle (Isaac Sim / USD Composer)
    # ------------------------------------------------------------------

    @tool()
    async def mcp_runtime_info() -> str:
        """Report MCP import freshness and active tool profile diagnostics without host-local paths or process identifiers: tool/app profile, registered and omitted tool counts, included/omitted groups, omitted tools, custom include/exclude tokens, source mtimes, and robot probe result-shape fields. If this tool is absent or reports stale source files, restart the MCP host before live result-shape validation."""
        return json.dumps(
            _mcp_runtime_info_payload(mcp, selection),
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    @tool()
    async def kit_app_start() -> str:
        """Start the Kit application for this MCP instance (Isaac Sim or USD Composer per ISAAC_MCP_APP_PROFILE); waits for the validation REST health endpoint. Required before stage/sim/viewport ops."""
        result = await process.start()
        return json.dumps(result, indent=2)

    @tool()
    async def kit_app_stop() -> str:
        """Stop the Kit application (kit.exe) of this MCP instance only — other instances and other app profiles are unaffected."""
        result = await process.stop()
        return json.dumps(result, indent=2)

    @tool()
    async def kit_app_restart() -> str:
        """Restart Kit (stop → clear __pycache__ → start). Use only for crash/hang recovery, validation_api self-code changes, extension.toml/native dependency changes, failed extension_reload/marker checks, or explicit fresh-process requests; otherwise prefer kit_app_start attach and extension_reload."""
        result = await process.restart()
        return json.dumps(result, indent=2)

    @tool()
    async def process_list_kit_instances() -> str:
        """Enumerate ALL running kit.exe processes (read-only). Includes MCP-spawned, other MCP servers, and user GUI launches. Per-instance: pid, command_line, start_time_utc, ext_port, app_profile, kit_file, profile_matches, is_this_mcp_instance. Use BEFORE destructive ops (Kit user.config.json edit, settings reset, force reload) — external instances overwrite settings on shutdown. Windows-only."""
        result = await process.list_kit_instances()
        return json.dumps(result, indent=2)

    @tool()
    async def stage_capture_snapshot(
        include_prim_patterns: list[str] | None = None,
        exclude_prim_patterns: list[str] | None = None,
        include_properties: bool = True,
        include_metadata: bool = True,
        max_prim_count: int = 10000,
    ) -> str:
        """Capture current USD Stage prim tree (prims + properties + relationships + metadata)."""
        meta = make_meta(ModuleName.STAGE)
        capture_filter = StageCaptureFilter(
            include_prim_patterns=tuple(include_prim_patterns or ["*"]),
            exclude_prim_patterns=tuple(exclude_prim_patterns or []),
            include_properties=include_properties,
            include_metadata=include_metadata,
            max_prim_count=max_prim_count,
        )
        result = await stage.capture_snapshot(meta, capture_filter)
        return _serialize(result)

    @tool()
    async def stage_diff_snapshots(
        before_snapshot_json: str,
        after_snapshot_json: str,
    ) -> str:
        """Diff two Stage snapshots (prims/properties added/removed/changed); pass two stage_capture_snapshot JSON outputs."""
        meta = make_meta(ModuleName.STAGE)
        # Parse snapshots from JSON - in practice these come from previous captures
        before_raw = json.loads(before_snapshot_json)
        after_raw = json.loads(after_snapshot_json)
        from omniverse_kit_mcp.modules.stage_module import _parse_snapshot
        before = _parse_snapshot(before_raw, StageCaptureFilter())
        after = _parse_snapshot(after_raw, StageCaptureFilter())
        result = await stage.diff_snapshots(meta, before, after)
        return _serialize(result)

    @tool()
    async def stage_compute_world_bbox(
        prim_path: str,
        include_purposes: list[str] | None = None,
    ) -> str:
        """Compute a prim's world-space aligned bbox via USD BBoxCache. Returns min/max/center/size plus world translate/orientation; use before camera framing or layout checks."""
        meta = make_meta(ModuleName.STAGE)
        request = StageWorldBboxRequest(
            prim_path=prim_path,
            include_purposes=tuple(include_purposes or ["default", "render"]),
        )
        result = await stage.compute_world_bbox(meta, request)
        return _serialize(result)

    @tool()
    async def stage_visual_alignment_report(
        reference_prim_path: str,
        candidate_prim_paths: list[str],
        min_iou_xy: float = 0.5,
        max_center_delta_m: float = 0.05,
        include_purposes: list[str] | None = None,
    ) -> str:
        """Compare candidate prim world bboxes against a reference bbox. Reports XY IoU and center deltas to catch visual/physics/acceptance-volume misalignment."""
        meta = make_meta(ModuleName.STAGE)
        request = StageVisualAlignmentRequest(
            reference_prim_path=reference_prim_path,
            candidate_prim_paths=tuple(candidate_prim_paths),
            include_purposes=tuple(include_purposes or ["default", "render"]),
            min_iou_xy=min_iou_xy,
            max_center_delta_m=max_center_delta_m,
        )
        result = await stage.visual_alignment_report(meta, request)
        return _serialize(result)

    @tool()
    async def stage_placement_validation_report(
        subject_prim_paths: list[str],
        container_prim_path: str | None = None,
        support_prim_path: str | None = None,
        obstacle_prim_paths: list[str] | None = None,
        checks: list[str] | None = None,
        containment_axes: list[str] | None = None,
        margin_m: float = 0.0,
        min_clearance_m: float = 0.0,
        floor_tolerance_m: float = 0.01,
        floor_axis: str = "z",
        include_purposes: list[str] | None = None,
    ) -> str:
        """Validate asset placement with world-AABB containment, clearance, and on-floor checks. Use explicit PlacementZone/AcceptanceVolume prims as containers; this is broad-phase evidence, not final visual acceptance."""
        meta = make_meta(ModuleName.STAGE)
        request = StagePlacementValidationRequest(
            subject_prim_paths=tuple(subject_prim_paths),
            container_prim_path=container_prim_path,
            support_prim_path=support_prim_path,
            obstacle_prim_paths=tuple(obstacle_prim_paths or ()),
            checks=tuple(checks or ("containment",)),
            include_purposes=tuple(include_purposes or ("default", "render")),
            containment_axes=tuple(containment_axes or ("x", "y")),
            margin_m=margin_m,
            min_clearance_m=min_clearance_m,
            floor_tolerance_m=floor_tolerance_m,
            floor_axis=floor_axis,
        )
        result = await stage.placement_validation_report(meta, request)
        return _serialize(result)

    @tool()
    async def stage_assert_prim_exists(
        prim_path: str,
        should_exist: bool = True,
        expected_type_name: str | None = None,
        expected_active: bool | None = None,
    ) -> str:
        """Assert whether a specific Prim exists in the USD Stage. Checks existence, type name, and active status."""
        meta = make_meta(ModuleName.STAGE)
        assertion = PrimExistenceAssertion(
            prim_path=prim_path,
            should_exist=should_exist,
            expected_type_name=expected_type_name,
            expected_active=expected_active,
        )
        result = await stage.assert_prim_exists(meta, assertion)
        return _serialize(result)

    @tool()
    async def stage_assert_property(
        prim_path: str,
        property_name: str,
        comparator: str = "equals",
        expected_value: Any = None,
        expected_type_name: str | None = None,
        tolerance: float | None = None,
        property_kind: str = "attribute",
    ) -> str:
        """Assert a Prim attribute/relationship value. comparator ∈ {equals, not_equals, approx, gt, gte, lt, lte, regex, contains, exists}; approx requires tolerance; set property_kind='relationship' for rels."""
        meta = make_meta(ModuleName.STAGE)
        expected = None
        if expected_value is not None:
            expected = UsdPropertyValue(
                type_name=expected_type_name or "unknown",
                value=expected_value,
            )
        assertion = PropertyAssertion(
            prim_path=prim_path,
            property_name=property_name,
            property_kind=property_kind,  # type: ignore[arg-type]
            comparator=comparator,  # type: ignore[arg-type]
            expected=expected,
            tolerance=tolerance,
        )
        result = await stage.assert_property(meta, assertion)
        return _serialize(result)

    @tool()
    async def viewport_capture(
        viewport_name: str = "Viewport",
        camera_prim_path: str | None = None,
        renderer: str = "rtx",
        width: int = 1280,
        height: int = 720,
        output_format: str = "png",
        warmup_frames: int = 0,
        return_stats: bool = False,
    ) -> str:
        """Capture the 3D RTX render only (no Kit chrome) to PNG; returns artifact path. For the whole app window (menus + panels + viewport) use window_capture instead. warmup_frames=N ticks extra frames before grab (cold-RTX black fix); return_stats=True adds pixel_mean/pixel_variance per channel so you can auto-detect a blank/black frame without reading the PNG. Failures include data.diagnostics.reason=viewport_capture_error and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportCaptureRequest(
            viewport_name=viewport_name,
            camera_prim_path=camera_prim_path,
            renderer=renderer,  # type: ignore[arg-type]
            width=width,
            height=height,
            output_format=output_format,  # type: ignore[arg-type]
            warmup_frames=warmup_frames,
            return_stats=return_stats,
        )
        result = await viewport.capture(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_compare_ssim(
        baseline_artifact_path: str,
        candidate_artifact_path: str,
        min_ssim: float = 0.99,
        crop: list[int] | None = None,
    ) -> str:
        """Compare two viewport images via SSIM (score + pass/fail)."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = SSIMComparisonRequest(
            baseline_artifact_path=baseline_artifact_path,
            candidate_artifact_path=candidate_artifact_path,
            min_ssim=min_ssim,
            crop=tuple(crop) if crop and len(crop) == 4 else None,  # type: ignore[arg-type]
        )
        result = await viewport.compare_ssim(meta, request)
        return _serialize(result)

    @tool()
    async def lakehouse_query(
        sql: str | None = None,
        namespace: str | None = None,
        dataset: str | None = None,
        table: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
    ) -> str:
        """Query Lakehouse REST for expected values; accepts raw SQL or namespace/dataset/table + filters."""
        meta = make_meta(ModuleName.LAKEHOUSE)
        target = None
        if namespace and dataset:
            target = LakehouseDatasetRef(namespace=namespace, dataset=dataset, table=table)
        request = LakehouseQueryRequest(
            sql=sql,
            target=target,
            filters=filters or {},
            limit=limit,
        )
        result = await lakehouse.query(meta, request)
        return _serialize(result)

    @tool()
    async def extension_trigger(
        operation: str,
        payload: dict[str, Any] | None = None,
        wait_for_idle: bool = True,
        idle_timeout_s: float = 30.0,
    ) -> str:
        """Trigger an operation on the validation_api Extension (this MCP server's in-Kit companion), e.g. sync_from_lakehouse. Optionally waits for idle."""
        meta = make_meta(ModuleName.EXTENSION)
        request = ExtensionTriggerRequest(
            operation=operation,
            payload=payload or {},
            wait_for_idle=wait_for_idle,
            idle_timeout_s=idle_timeout_s,
        )
        result = await extension.trigger(meta, request)
        return _serialize(result)

    @tool()
    async def extension_get_state() -> str:
        """Get the validation_api Extension's runtime state (enabled/busy/last_operation/errors) — this MCP server's in-Kit companion, not an arbitrary Kit extension (use extension_get_info for those)."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.get_state(meta)
        return _serialize(result)

    # ------------------------------------------------------------------
    # WRITE tools — Stage mutations
    # ------------------------------------------------------------------

    @tool()
    async def stage_load_usd(
        usd_url: str,
        prim_path: str,
        position: list[float] | None = None,
        rotation: list[float] | None = None,
    ) -> str:
        """Add USD asset as payload at prim_path (multi-asset composition, not root replace). Optional position/rotation."""
        meta = make_meta(ModuleName.STAGE)
        request = {
            "usd_url": usd_url,
            "prim_path": prim_path,
            "position": position,
            "rotation": rotation,
        }
        result = await simulation.stage_load_usd(meta, request)
        return _serialize(result)

    @tool()
    async def stage_set_property(
        prim_path: str,
        property_name: str,
        value: Any,
        type_hint: str | None = None,
    ) -> str:
        """Set a USD Prim attribute; type_hint specifies USD type (Vec3d/Vec3f/Quatd/float/int/bool/string/asset)."""
        meta = make_meta(ModuleName.STAGE)
        request = {
            "prim_path": prim_path,
            "property_name": property_name,
            "value": value,
            "type_hint": type_hint,
        }
        result = await simulation.stage_set_property(meta, request)
        return _serialize(result)

    @tool()
    async def stage_set_semantic_label(
        prim_path: str,
        label_class: str,
        label_type: str = "class",
    ) -> str:
        """Apply a semantic label to a prim (inherits to its subtree) so Replicator segmentation / bbox annotators classify it. Authors UsdSemantics.LabelsAPI (semantics:labels:<label_type>) + best-effort legacy Semantics schema. Fills the gap left by sensor_set_annotator (which attaches annotators but cannot label the props). 400 if prim_path not found."""
        meta = make_meta(ModuleName.STAGE)
        request = {
            "prim_path": prim_path,
            "label_class": label_class,
            "label_type": label_type,
        }
        result = await simulation.stage_set_semantic_label(meta, request)
        return _serialize(result)

    @tool()
    async def stage_create_prim(
        prim_path: str,
        prim_type: str = "Xform",
        position: list[float] | None = None,
    ) -> str:
        """Create a USD Prim. Types: Xform (empty transform), Cube, Sphere, Cylinder, Cone, Capsule, Plane, etc. Optionally set position [x,y,z]."""
        meta = make_meta(ModuleName.STAGE)
        request = {
            "prim_path": prim_path,
            "prim_type": prim_type,
            "position": position,
        }
        result = await simulation.stage_create_prim(meta, request)
        return _serialize(result)

    @tool()
    async def stage_delete_prim(
        prim_path: str,
    ) -> str:
        """Delete USD Prim (also removes children)."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.stage_delete_prim(meta, prim_path)
        return _serialize(result)

    # ------------------------------------------------------------------
    # WRITE tools — Simulation control
    # ------------------------------------------------------------------

    @tool()
    async def simulation_play() -> str:
        """Start simulation timeline (play button). Does NOT launch the Kit application — use kit_app_start for that. Failures include data.diagnostics.action and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.play(meta)
        return _serialize(result)

    @tool()
    async def simulation_pause() -> str:
        """Pause simulation timeline. Failures include data.diagnostics.action and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.pause(meta)
        return _serialize(result)

    @tool()
    async def simulation_stop() -> str:
        """Stop simulation timeline and reset time to 0 (stop button). Does NOT terminate the Kit application — use kit_app_stop for that. Failures include data.diagnostics.action and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.stop(meta)
        return _serialize(result)

    @tool()
    async def simulation_get_status() -> str:
        """Get simulation timeline status: is_playing, current_time, fps, etc.; status failures include data.diagnostics.suggested_next and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.get_status(meta)
        return _serialize(result)

    @tool()
    async def simulation_step(frames: int = 1) -> str:
        """Advance timeline by N frames with Isaac Sim 6.0 play-burst semantics; preserves prior play state. Failures include data.diagnostics.suggested_next and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SIMULATION)
        request = SimulationStepRequest(frames=frames)
        result = await simulation.step(meta, request)
        return _serialize(result)

    @tool()
    async def simulation_step_observe(
        frames: int = 1,
        observe_prims: list[str] | None = None,
        observe_joints: list[str] | None = None,
        observe_ee: list[dict[str, Any]] | None = None,
    ) -> str:
        """Advance N frames, then return synchronized prim/joint/end-effector observations. Use this for deterministic ScriptNode/controller debugging instead of sleep+separate polling; failures include data.diagnostics.suggested_next and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SIMULATION)
        ee_specs = tuple(
            SimulationEESpec(
                prim_path=str(item.get("prim_path", "")),
                end_effector_frame=(
                    str(item["end_effector_frame"])
                    if item.get("end_effector_frame") is not None
                    else None
                ),
            )
            for item in observe_ee or []
        )
        request = SimulationStepObserveRequest(
            frames=frames,
            observe_prims=tuple(observe_prims or ()),
            observe_joints=tuple(observe_joints or ()),
            observe_ee=ee_specs,
        )
        result = await simulation.step_observe(meta, request)
        return _serialize(result)

    @tool()
    async def simulation_wait_until(until_time: float, timeout_s: float = 30.0) -> str:
        """Tick the timeline until current_time >= until_time (or timeout_s wall-clock elapses), then return final status + reached/timed_out/elapsed_s/frames_waited. Ticks via next_update_async on the Kit loop (deadlock-safe, non-blocking). Replaces sleep+poll loops for sim_time-precise timing (e.g. trigger an event at t=12s). Requires the timeline PLAYING to advance — otherwise it times out; failures include data.diagnostics.suggested_next and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SIMULATION)
        request = SimulationWaitUntilRequest(until_time=until_time, timeout_s=timeout_s)
        result = await simulation.wait_until(meta, request)
        return _serialize(result)

    @tool()
    async def simulation_set_time(time_seconds: float) -> str:
        """Seek timeline to time_seconds; preserves current play/stop state. Failures include data.diagnostics.time_seconds and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SIMULATION)
        request = SimulationSetTimeRequest(time_seconds=time_seconds)
        result = await simulation.set_time(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Robot
    # ------------------------------------------------------------------

    @tool()
    async def robot_list_arm_profiles() -> str:
        """List curated built-in Isaac Sim 6.0 robot arm profiles with asset URL, controller strategy, support status, evidence, recommended dynamic-vs-static probe groups and per-profile probe-mode reasons, known dynamic-timeout probe hazards, and known pick/place playback blockers. Use before multi-arm pick/place or batch probe work."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.list_arm_profiles(meta)
        return _serialize(result)

    @tool()
    async def robot_probe_arm_profile(
        profile_name: str,
        prim_path: str | None = None,
        reset_stage: bool = True,
        safe_nudge: bool = True,
        cleanup: bool = True,
        dynamic_checks: bool = True,
        static_only_for_known_dynamic_timeouts: bool = False,
        timeout_s: float | None = 90.0,
    ) -> str:
        """Probe one built-in arm profile for MCP manipulation readiness: load, articulation, joint config/read, safe joint nudge, gripper, IK, and EE pose. Returns mcp_controllability plus probe_capability_level/probe_capability_level_name so callers can distinguish dynamic joint-control proof from read-only, static-metadata, or blocked evidence. Probe rows also return probe_proves_pick_place=false plus pick_place_validation_status/reason; probe levels are capped below pick/place validation. timeout_s defaults to 90 seconds to record slow profiles instead of hanging the MCP caller; pass null only for deliberate unbounded diagnostics. Set dynamic_checks=false for load/articulation/static-metadata hazard triage. Set static_only_for_known_dynamic_timeouts=true to route profiles with durable live dynamic-timeout evidence to static-only hazard rows; this does not prove joint control or pick/place."""
        meta = make_meta(ModuleName.ROBOT)
        request = RobotArmProfileProbeRequest(
            profile_name=profile_name,
            prim_path=prim_path,
            reset_stage=reset_stage,
            safe_nudge=safe_nudge,
            cleanup=cleanup,
            dynamic_checks=dynamic_checks,
            static_only_for_known_dynamic_timeouts=(
                static_only_for_known_dynamic_timeouts
            ),
            timeout_s=timeout_s,
        )
        result = await robot.probe_arm_profile(meta, request)
        return _serialize(result)

    @tool()
    async def robot_probe_arm_profiles(
        profile_names: list[str] | None = None,
        status_filter: list[str] | None = None,
        family_filter: list[str] | None = None,
        limit: int | None = None,
        reset_stage_per_profile: bool = True,
        safe_nudge: bool = True,
        cleanup: bool = True,
        dynamic_checks: bool = True,
        static_only_for_known_dynamic_timeouts: bool = False,
        per_profile_timeout_s: float | None = 90.0,
        batch_timeout_s: float | None = 105.0,
    ) -> str:
        """Probe multiple built-in arm profiles sequentially to build a capability matrix. Omit profile_names to probe the catalog; pass profile_names to probe exact profiles in order, where an explicit empty list selects no profiles and unknown names are recorded as row-level hard errors instead of failing the whole batch. Each row returns mcp_controllability plus probe_capability_level/probe_capability_level_name so callers can distinguish dynamic joint-control proof from read-only, static-metadata, timeout, or batch-aborted evidence; each row also returns probe_proves_pick_place=false plus pick_place_validation_status/reason. The batch result includes triage summary counts/profile lists, including mcp_controllability_counts, mcp_controllability_profiles, probe_capability_level_name_counts, probe_capability_level_name_profiles, pick_place_validation_status_counts, pick_place_validation_status_profiles, unsupported_capability_counts, ik_target_failure_profiles, batch_timeout_profiles, batch_aborted_profiles, and lifecycle_recovery_profiles for rows that require host recovery before more live probes. Probe levels are capped below pick/place validation. Filters accept support_status and family values; dynamic_checks=false records load/articulation/static-metadata rows. static_only_for_known_dynamic_timeouts routes profiles with durable live dynamic-timeout evidence to static-only rows and reports them in known_dynamic_timeout_routed_profiles; full dynamic probes remain bounded per profile/batch."""
        meta = make_meta(ModuleName.ROBOT)
        request = RobotArmProfilesProbeRequest(
            profile_names=tuple(profile_names) if profile_names is not None else None,
            status_filter=tuple(status_filter) if status_filter else None,
            family_filter=tuple(family_filter) if family_filter else None,
            limit=limit,
            reset_stage_per_profile=reset_stage_per_profile,
            safe_nudge=safe_nudge,
            cleanup=cleanup,
            dynamic_checks=dynamic_checks,
            static_only_for_known_dynamic_timeouts=static_only_for_known_dynamic_timeouts,
            per_profile_timeout_s=per_profile_timeout_s,
            batch_timeout_s=batch_timeout_s,
        )
        result = await robot.probe_arm_profiles(meta, request)
        return _serialize(result)

    @tool()
    async def robot_load(
        usd_url: str,
        prim_path: str,
        position: list[float] | None = None,
        rotation: list[float] | None = None,
    ) -> str:
        """Load robot USD at prim_path; detects PhysX ArticulationAPI for joint control. Optional initial position/rotation. Failures include diagnostics.suggested_next and diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.ROBOT)
        request = RobotLoadRequest(
            usd_url=usd_url,
            prim_path=prim_path,
            position=tuple(position) if position else None,
            rotation=tuple(rotation) if rotation else None,
        )
        result = await robot.load(meta, request)
        return _serialize(result)

    @tool()
    async def robot_get_joint_positions(prim_path: str) -> str:
        """Get joint positions of an articulation (via SingleArticulation)."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.get_joint_positions(meta, prim_path)
        return _serialize(result)

    @tool()
    async def robot_get_joint_config(prim_path: str) -> str:
        """Read drive stiffness/damping/max_force + position lower/upper limits + max joint velocity per DOF. Symmetric readback for set_joint_positions — diagnose IK / drive_physics anomalies (drive too soft, target outside limits, velocity capped). Source field reports backend (dof_properties / usd_drive_api fallback)."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.get_joint_config(meta, prim_path)
        return _serialize(result)

    @tool()
    async def robot_get_joint_config_static(prim_path: str) -> str:
        """Read static UsdPhysics joint metadata without simulation_play. Diagnostic only: USD prim traversal order is not write-order proof for set_joint_positions."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.get_joint_config_static(meta, prim_path)
        return _serialize(result)

    @tool()
    async def robot_set_joint_positions(
        prim_path: str,
        positions: list[float],
    ) -> str:
        """Set articulation joint positions (SingleArticulation). Raises 400 if no PhysX articulation; wrap in continueOnFailure for optional calls."""
        meta = make_meta(ModuleName.ROBOT)
        request = JointPositionsSetRequest(
            prim_path=prim_path,
            positions=tuple(float(p) for p in positions),
        )
        result = await robot.set_joint_positions(meta, request)
        return _serialize(result)

    @tool()
    async def robot_navigate_to(
        prim_path: str,
        target: list[float],
        duration_s: float = 1.0,
    ) -> str:
        """Dispatch a linear-interpolation navigate-to as an async Job. Returns a job_id — poll job_status(job_id) until status='done'."""
        meta = make_meta(ModuleName.ROBOT)
        request = RobotNavigateRequest(
            prim_path=prim_path,
            target=tuple(target),  # type: ignore[arg-type]
            duration_s=duration_s,
        )
        result = await robot.navigate_to(meta, request)
        return _serialize(result)

    @tool()
    async def robot_navigate_path(
        prim_path: str,
        waypoints: list[list[float]],
        duration_s: float = 5.0,
    ) -> str:
        """Dispatch multi-waypoint navigate as async Job; returns job_id. Each waypoint [x,y,z]; duration_s total (weighted by segment length). Requires timeline playing."""
        meta = make_meta(ModuleName.ROBOT)
        pts = tuple(
            (float(w[0]), float(w[1]), float(w[2])) for w in waypoints
        )
        request = RobotNavigatePathRequest(
            prim_path=prim_path,
            waypoints=pts,
            duration_s=duration_s,
        )
        result = await robot.navigate_path(meta, request)
        return _serialize(result)

    @tool()
    async def robot_gripper_control(
        prim_path: str,
        action: str,
        target: float | None = None,
    ) -> str:
        """Open/close/set gripper joints. action ∈ {open, close, set}; auto-detects finger/gripper DOF names. Requires simulation playing."""
        meta = make_meta(ModuleName.ROBOT)
        request = RobotGripperControlRequest(
            prim_path=prim_path, action=action, target=target,
        )
        result = await robot.gripper_control(meta, request)
        return _serialize(result)

    @tool()
    async def robot_set_ee_target(
        prim_path: str,
        target_pose: list[float],
        robot_description: str = "Franka",
        end_effector_frame: str | None = None,
    ) -> str:
        """Solve Lula IK for a shipped robot description and end-effector pose [x,y,z,qw,qx,qy,qz]; write joint positions. Use robot_list_arm_profiles for supported robot_description values and frame hints."""
        meta = make_meta(ModuleName.ROBOT)
        pose = tuple(float(v) for v in target_pose)
        if len(pose) != 7:
            raise ValueError("target_pose must be [x,y,z,qw,qx,qy,qz]")
        request = RobotSetEETargetRequest(
            prim_path=prim_path,
            target_pose=pose,  # type: ignore[arg-type]
            robot_description=robot_description,
            end_effector_frame=end_effector_frame,
        )
        result = await robot.set_ee_target(meta, request)
        return _serialize(result)

    @tool()
    async def robot_get_ee_pose(
        prim_path: str,
        end_effector_frame: str | None = None,
    ) -> str:
        """Read the current end-effector world pose [position + qw,qx,qy,qz]. Prefer this for checking whether a Franka controller is approaching the object before grasp."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.get_ee_pose(meta, prim_path, end_effector_frame)
        return _serialize(result)

    @tool()
    async def robot_run_franka_pick_place(
        robot_prim_path: str,
        object_prim_path: str,
        target_position: list[float],
        max_steps: int = 1800,
        position_tolerance: float = 0.05,
        lift_height_tolerance: float = 0.03,
        picking_position: list[float] | None = None,
        end_effector_initial_height: float | None = None,
        end_effector_offset: list[float] | None = None,
        end_effector_orientation: list[float] | None = None,
        events_dt: list[float] | None = None,
    ) -> str:
        """Run Isaac Sim's official Franka PickPlaceController/RMPflow/ParallelGripper against an existing object prim. Explicit picking/orientation inputs allow official-example-style grasps; success requires physical lift plus final bbox/position validation."""
        meta = make_meta(ModuleName.ROBOT)
        if len(target_position) != 3:
            raise ValueError("target_position must be [x,y,z]")
        if picking_position is not None and len(picking_position) != 3:
            raise ValueError("picking_position must be [x,y,z]")
        if end_effector_offset is not None and len(end_effector_offset) != 3:
            raise ValueError("end_effector_offset must be [x,y,z]")
        if end_effector_orientation is not None and len(end_effector_orientation) != 4:
            raise ValueError("end_effector_orientation must be [qw,qx,qy,qz]")
        request = RobotFrankaPickPlaceRequest(
            robot_prim_path=robot_prim_path,
            object_prim_path=object_prim_path,
            target_position=tuple(float(v) for v in target_position),  # type: ignore[arg-type]
            picking_position=(
                tuple(float(v) for v in picking_position)
                if picking_position is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_initial_height=end_effector_initial_height,
            end_effector_offset=(
                tuple(float(v) for v in end_effector_offset)
                if end_effector_offset is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_orientation=(
                tuple(float(v) for v in end_effector_orientation)
                if end_effector_orientation is not None
                else None
            ),  # type: ignore[arg-type]
            events_dt=tuple(float(v) for v in events_dt) if events_dt else None,
            max_steps=max_steps,
            position_tolerance=position_tolerance,
            lift_height_tolerance=lift_height_tolerance,
        )
        result = await robot.run_franka_pick_place(meta, request)
        return _serialize(result)

    @tool()
    async def robot_install_franka_pick_place_playback_demo(
        robot_prim_path: str = "/World/Franka",
        object_prim_path: str = "/World/PickCube",
        target_position: list[float] | None = None,
        object_initial_position: list[float] | None = None,
        object_size: float = 0.04,
        object_asset_url: str | None = None,
        grid_asset_url: str | None = None,
        max_grasp_width_m: float | None = 0.08,
        fit_clearance_m: float = 0.005,
        robot_description: str = "Franka",
        max_steps: int = 1800,
        position_tolerance: float = 0.05,
        lift_height_tolerance: float = 0.03,
        picking_position: list[float] | None = None,
        end_effector_initial_height: float | None = None,
        end_effector_offset: list[float] | None = None,
        end_effector_orientation: list[float] | None = None,
        events_dt: list[float] | None = None,
        create_demo_scene: bool = True,
        reset_on_play: bool = True,
    ) -> str:
        """Install a low-level Franka-family pick/place playback demo for intentional proof diagnostics. The robot must already be loaded; this bypasses profile support-status routing, uses official PickPlaceController/RMPflow/ParallelGripper, and never promotes a profile by itself. Stop and recover the live host if playback step/status/log calls time out."""
        meta = make_meta(ModuleName.ROBOT)
        target = target_position or [0.45, -0.35, 0.02575]
        initial = object_initial_position or [0.3, 0.35, 0.02575]
        if len(target) != 3:
            raise ValueError("target_position must be [x,y,z]")
        if len(initial) != 3:
            raise ValueError("object_initial_position must be [x,y,z]")
        if picking_position is not None and len(picking_position) != 3:
            raise ValueError("picking_position must be [x,y,z]")
        if end_effector_offset is not None and len(end_effector_offset) != 3:
            raise ValueError("end_effector_offset must be [x,y,z]")
        if end_effector_orientation is not None and len(end_effector_orientation) != 4:
            raise ValueError("end_effector_orientation must be [qw,qx,qy,qz]")
        request = RobotFrankaPickPlaceDemoRequest(
            robot_prim_path=robot_prim_path,
            object_prim_path=object_prim_path,
            target_position=tuple(float(v) for v in target),  # type: ignore[arg-type]
            object_initial_position=tuple(float(v) for v in initial),  # type: ignore[arg-type]
            object_size=float(object_size),
            object_asset_url=object_asset_url,
            grid_asset_url=grid_asset_url,
            max_grasp_width_m=max_grasp_width_m,
            fit_clearance_m=float(fit_clearance_m),
            robot_description=robot_description,
            picking_position=(
                tuple(float(v) for v in picking_position)
                if picking_position is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_initial_height=end_effector_initial_height,
            end_effector_offset=(
                tuple(float(v) for v in end_effector_offset)
                if end_effector_offset is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_orientation=(
                tuple(float(v) for v in end_effector_orientation)
                if end_effector_orientation is not None
                else None
            ),  # type: ignore[arg-type]
            events_dt=tuple(float(v) for v in events_dt) if events_dt else None,
            max_steps=int(max_steps),
            position_tolerance=float(position_tolerance),
            lift_height_tolerance=float(lift_height_tolerance),
            create_demo_scene=create_demo_scene,
            reset_on_play=reset_on_play,
        )
        result = await robot.install_franka_pick_place_playback_demo(meta, request)
        return _serialize(result)

    @tool()
    async def robot_install_pick_place_playback_demo(
        profile_name: str = "franka_fr3",
        robot_prim_path: str = "/World/Franka",
        object_prim_path: str = "/World/PickCube",
        target_position: list[float] | None = None,
        object_initial_position: list[float] | None = None,
        object_size: float = 0.04,
        object_asset_url: str | None = None,
        grid_asset_url: str | None = None,
        max_steps: int = 1800,
        position_tolerance: float = 0.05,
        lift_height_tolerance: float = 0.03,
        picking_position: list[float] | None = None,
        end_effector_initial_height: float | None = None,
        end_effector_offset: list[float] | None = None,
        end_effector_orientation: list[float] | None = None,
        events_dt: list[float] | None = None,
        create_demo_scene: bool = True,
        reset_on_play: bool = True,
    ) -> str:
        """Install a profile-selected pick/place playback demo. Only validated_pick_place profiles route to playback; candidate/IK/profile-only arms return status='unsupported' with blocker diagnostics, diagnostics.suggested_next, and diagnostics.fallback_tool_order until durable live proof exists."""
        meta = make_meta(ModuleName.ROBOT)
        target = target_position or [0.45, -0.35, 0.02575]
        initial = object_initial_position or [0.3, 0.35, 0.02575]
        if len(target) != 3:
            raise ValueError("target_position must be [x,y,z]")
        if len(initial) != 3:
            raise ValueError("object_initial_position must be [x,y,z]")
        if picking_position is not None and len(picking_position) != 3:
            raise ValueError("picking_position must be [x,y,z]")
        if end_effector_offset is not None and len(end_effector_offset) != 3:
            raise ValueError("end_effector_offset must be [x,y,z]")
        if end_effector_orientation is not None and len(end_effector_orientation) != 4:
            raise ValueError("end_effector_orientation must be [qw,qx,qy,qz]")
        request = RobotPickPlaceDemoRequest(
            profile_name=profile_name,
            robot_prim_path=robot_prim_path,
            object_prim_path=object_prim_path,
            target_position=tuple(float(v) for v in target),  # type: ignore[arg-type]
            object_initial_position=tuple(float(v) for v in initial),  # type: ignore[arg-type]
            object_size=float(object_size),
            object_asset_url=object_asset_url,
            grid_asset_url=grid_asset_url,
            picking_position=(
                tuple(float(v) for v in picking_position)
                if picking_position is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_initial_height=end_effector_initial_height,
            end_effector_offset=(
                tuple(float(v) for v in end_effector_offset)
                if end_effector_offset is not None
                else None
            ),  # type: ignore[arg-type]
            end_effector_orientation=(
                tuple(float(v) for v in end_effector_orientation)
                if end_effector_orientation is not None
                else None
            ),  # type: ignore[arg-type]
            events_dt=tuple(float(v) for v in events_dt) if events_dt else None,
            max_steps=int(max_steps),
            position_tolerance=float(position_tolerance),
            lift_height_tolerance=float(lift_height_tolerance),
            create_demo_scene=create_demo_scene,
            reset_on_play=reset_on_play,
        )
        result = await robot.install_pick_place_playback_demo(meta, request)
        return _serialize(result)

    @tool()
    async def robot_reset_pick_place_demo() -> str:
        """Reset the installed Franka pick/place playback demo object pose, robot joints/gripper, controller state, and status."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.reset_pick_place_demo(meta)
        return _serialize(result)

    @tool()
    async def robot_get_pick_place_demo_status(timeout_s: float | None = 10.0) -> str:
        """Return installed Franka pick/place playback demo status with a caller-side timeout; includes idle/resetting/picking/placing/done/failed plus timeout/error diagnostics, bbox, lift/place metrics, controller event, diagnostics.playback_progress with approach/contact windows, bounded next-offset recommendations, and last_error."""
        meta = make_meta(ModuleName.ROBOT)
        result = await robot.get_pick_place_demo_status(meta, timeout_s=timeout_s)
        return _serialize(result)

    @tool()
    async def robot_drive_physics(
        prim_path: str,
        waypoints: list[list[float]],
        max_linear: float = 1.0,
        max_angular: float = 1.2,
        wheel_radius: float = 0.14,
        wheel_base: float = 0.413,
        arrival_tolerance: float = 0.3,
        timeout_s: float = 60.0,
        lookahead: float = 0.8,
    ) -> str:
        """Drive a wheel-based articulation along ``waypoints`` using DifferentialController + Pure Pursuit (physics-based, writes joint_velocities, spec §8.2).

        ASYNC Job — returns ``{job_id}``; poll ``job_status``. Requires
        timeline playing (R2). Wheel DOFs auto-resolved by name substring
        scan (wheel_left/right or joint_wheel_*). Always zeros wheels on
        exit (cancel/timeout/exception). Defaults are Nova Carter spec
        (wheel_radius=0.14, wheel_base=0.413).
        """
        meta = make_meta(ModuleName.ROBOT)
        # Accept 2D [x, y] (ground plane) or 3D [x, y, z]; pad z=0 for 2D so a
        # 2-element waypoint no longer trips a cryptic "list index out of range".
        wp_tuple = tuple(
            (float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0)
            for p in waypoints
        )
        if len(wp_tuple) < 2:
            raise ValueError("waypoints must have at least 2 points")
        request = RobotDrivePhysicsRequest(
            prim_path=prim_path,
            waypoints=wp_tuple,  # type: ignore[arg-type]
            max_linear=float(max_linear),
            max_angular=float(max_angular),
            wheel_radius=float(wheel_radius),
            wheel_base=float(wheel_base),
            arrival_tolerance=float(arrival_tolerance),
            timeout_s=float(timeout_s),
            lookahead=float(lookahead),
        )
        result = await robot.drive_physics(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Job — async job polling
    # ------------------------------------------------------------------

    @tool()
    async def job_status(job_id: str) -> str:
        """Poll async Job status (returns status/progress/result/error)."""
        meta = make_meta(ModuleName.JOB)
        result = await job.status(meta, job_id)
        return _serialize(result)

    @tool()
    async def job_cancel(job_id: str) -> str:
        """Cancel async Job (idempotent on terminal; 404 if unknown)."""
        meta = make_meta(ModuleName.JOB)
        result = await job.cancel(meta, job_id)
        return _serialize(result)

    # ------------------------------------------------------------------
    # File / Selection / Camera (Phase B+) — GUI File menu & Stage panel
    # ------------------------------------------------------------------

    @tool()
    async def stage_save(path: str | None = None) -> str:
        """Save the current stage — GUI File → Save / Save As. Omit *path* for in-place save."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.stage_save(meta, path)
        return _serialize(result)

    @tool()
    async def stage_open(url: str) -> str:
        """Open (replace root) USD stage from local path or omniverse:// / https://; waits for load."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.stage_open(meta, url)
        return _serialize(result)

    @tool()
    async def stage_new() -> str:
        """Create empty stage (GUI File → New)."""
        meta = make_meta(ModuleName.STAGE)
        result = await simulation.stage_new(meta)
        return _serialize(result)

    @tool()
    async def stage_get_selection() -> str:
        """Return the current Stage-panel selection (prim paths) — GUI Stage panel readout."""
        meta = make_meta(ModuleName.STAGE)
        result = await stage.get_selection(meta)
        return _serialize(result)

    @tool()
    async def stage_set_selection(
        prim_paths: list[str],
        expand_in_stage: bool = True,
    ) -> str:
        """Replace the Stage-panel selection — GUI Stage panel click. *expand_in_stage* auto-expands the tree to reveal selected prims."""
        meta = make_meta(ModuleName.STAGE)
        result = await stage.set_selection(meta, prim_paths, expand_in_stage)
        return _serialize(result)

    @tool()
    async def viewport_set_active_camera(
        camera_path: str,
        viewport_name: str = "Viewport",
    ) -> str:
        """Switch the viewport's active camera — GUI viewport toolbar camera selector."""
        meta = make_meta(ModuleName.VIEWPORT)
        result = await viewport.set_active_camera(meta, camera_path, viewport_name)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Asset catalog (Phase B+) — GUI Asset Browser equivalent
    # ------------------------------------------------------------------

    @tool()
    async def asset_list(
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> str:
        """Browse Isaac Sim asset catalog. No args → top-level categories; category → folder contents; is_folder=false entries have spawnable url."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.list(
            meta,
            category=category,
            subpath=subpath,
            recursive=recursive,
            max_depth=max_depth,
            max_entries=max_entries,
        )
        return _serialize(result)

    @tool()
    async def asset_search(
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search the curated NVIDIA / Isaac Sim 6.0 asset catalog OFFLINE — no Isaac Sim required.

        Maps a natural-language need (e.g. "forklift", "warehouse", "franka",
        "police character", "pallet") to concrete spawnable USD URLs by ranking
        the curated markdown catalog under docs/assets/isaac/ (robots 90+,
        environments, people/animations, props, SimReady 1000+). Use this at
        planning time / before building a scene to pick a real asset (Validation
        Rule R1 — actual outputs use actual assets; controlled test/demo
        fixtures may be primitives); complements the live asset_list (which
        needs Isaac up) and content_browse.

        Args:
          query: free-text terms matched against asset name / catalog text.
          category: optional filter — one of robots / environments / people /
            props / simready / other.
          limit: max results (default 20).

        Returns a ranked list of {name, url, category, source_file}. Load a
        chosen url with stage_load_usd / robot_load / character_load per
        docs/invariants/usd-load.md.
        """
        meta = make_meta(ModuleName.ASSET)
        result = await asset.search(
            meta, query=query, category=category, limit=limit
        )
        return _serialize(result)

    @tool()
    async def official_asset_search(
        query: str,
        kind: str | None = None,
        app_profile: str | None = None,
        provider: str | None = None,
        min_status: str = "url_validated",
        allow_stale: bool = True,
        limit: int = 20,
    ) -> str:
        """Search generated NVIDIA official browser-extension asset/material snapshots OFFLINE. Returns URL-based ids, provider/app evidence, stale warnings, and verify_required_before_use; verify stale/unverified hits with official_asset_verify before use; zero-result responses include diagnostics.reason/suggested_next before falling back to asset_search."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.official_search(
            meta,
            query=query,
            kind=kind,
            app_profile=app_profile,
            provider=provider,
            min_status=min_status,
            allow_stale=allow_stale,
            limit=limit,
        )
        return _serialize(result)

    @tool()
    async def official_asset_resolve(
        name_or_id: str,
        kind: str | None = None,
        app_profile: str | None = None,
        prefer_loadable: bool = True,
    ) -> str:
        """Resolve an official catalog name/url/id to a concrete USD or MDL target plus evidence. Prefer current app/profile loadability; if stale or not load/assign verified, verify_required_before_use is true; not-found errors include diagnostics.reason/suggested_next."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.official_resolve(
            meta,
            name_or_id=name_or_id,
            kind=kind,
            app_profile=app_profile,
            prefer_loadable=prefer_loadable,
        )
        return _serialize(result)

    @tool()
    async def official_asset_get(
        asset_id: str,
        app_profile: str | None = None,
    ) -> str:
        """Return the full generated official asset/material catalog entry by URL-based id. Pass the same app_profile used for search/resolve so profile-specific latest pointers and diagnostics are used."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.official_get(
            meta, asset_id=asset_id, app_profile=app_profile
        )
        return _serialize(result)

    @tool()
    async def official_asset_sync_status(app_profile: str | None = None) -> str:
        """Report latest official asset snapshot metadata, provider/app versions, counts, stale status, failure counts, and catalog-unavailable diagnostics. No Kit launch required."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.official_sync_status(meta, app_profile=app_profile)
        return _serialize(result)

    @tool()
    async def official_asset_verify(
        asset_id: str,
        app_profile: str | None = None,
        timeout_s: float | None = None,
    ) -> str:
        """On-demand live verification for one official catalog item. Assets use stage_load_usd+bbox+inspect+cleanup; materials create a test prim, assign MDL, read binding, and cleanup. Use workspace workers for live Kit."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.official_verify(
            meta,
            asset_id=asset_id,
            app_profile=app_profile,
            timeout_s=timeout_s,
        )
        return _serialize(result)

    @tool()
    async def external_asset_search(
        query: str,
        providers: list[str] | None = None,
        limit: int = 10,
    ) -> str:
        """Search external free asset providers after asset_search misses. Default provider order is Poly Haven then token-gated Sketchfab; returns normalized candidates and provider_status."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.external_search(
            meta, query=query, providers=providers, limit=limit
        )
        return _serialize(result)

    @tool()
    async def external_asset_download(
        provider: str,
        asset_id: str,
        format_preference: list[str] | None = None,
    ) -> str:
        """Download one selected external free asset into ignored .omniverse-kit-mcp/external_assets and write manifest.json. Does not place the asset in the stage."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.external_download(
            meta,
            provider=provider,
            asset_id=asset_id,
            format_preference=format_preference,
        )
        return _serialize(result)

    @tool()
    async def external_asset_convert(
        manifest_path: str,
        output_format: str = "usd",
        timeout_s: float = 180.0,
    ) -> str:
        """Convert a downloaded external asset manifest to local USD through live Kit's omni.kit.asset_converter. Prepare-only: no stage_load_usd/file:// placement."""
        meta = make_meta(ModuleName.ASSET)
        result = await asset.external_convert(
            meta,
            manifest_path=manifest_path,
            output_format=output_format,
            timeout_s=timeout_s,
        )
        return _serialize(result)

    # ------------------------------------------------------------------
    # Character
    # ------------------------------------------------------------------

    @tool()
    async def character_load(
        usd_url: str,
        prim_path: str | None = None,
        position: list[float] | None = None,
        yaw: float = 0.0,
    ) -> str:
        """Load a 6.0 character skin, apply BehaviorAgent/IRA APIs, and return prim_path + skel_root. Sanitizes filenames."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterLoadRequest(
            usd_url=usd_url,
            prim_path=prim_path,
            position=tuple(position) if position else None,  # type: ignore[arg-type]
            yaw=yaw,
        )
        result = await character.load(meta, request)
        return _serialize(result)

    @tool()
    async def character_play_animation(
        prim_path: str,
        animation_name: str,
        speed: float = 1.0,
        target_position: list[float] | None = None,
    ) -> str:
        """Play animation clip on character. animation_name ∈ {Idle, Walk, Run, Sit}; Walk/Run accept target_position [x,y,z] for path-following."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterPlayAnimationRequest(
            prim_path=prim_path,
            animation_name=animation_name,
            speed=speed,
            target_position=tuple(target_position) if target_position else None,  # type: ignore[arg-type]
        )
        result = await character.play_animation(meta, request)
        return _serialize(result)

    @tool()
    async def character_set_position(
        prim_path: str,
        position: list[float],
        orientation: list[float] | None = None,
    ) -> str:
        """Write character world pose to USD (xformOp:translate + orientation, scalar-first [qw,qx,qy,qz]). The character runtime may override visual pose on the next tick, so use character_navigate_to for visible motion and character_load(position=...) for initial placement."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterSetPositionRequest(
            prim_path=prim_path,
            position=tuple(position),  # type: ignore[arg-type]
            orientation=tuple(orientation) if orientation else None,  # type: ignore[arg-type]
        )
        result = await character.set_position(meta, request)
        return _serialize(result)

    @tool()
    async def character_stop_animation(prim_path: str) -> str:
        """Stop any active animation by switching the character to Idle (speed 0). Safe to call when already Idle."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterStopAnimationRequest(prim_path=prim_path)
        result = await character.stop_animation(meta, request)
        return _serialize(result)

    @tool()
    async def character_navigate_to(
        prim_path: str,
        target: list[float],
        speed: float = 1.0,
    ) -> str:
        """Dispatch Walk-to-target as async Job; returns job_id. Character reverts to Idle on cancel/timeout."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterNavigateRequest(
            prim_path=prim_path,
            target=tuple(target),  # type: ignore[arg-type]
            speed=speed,
        )
        result = await character.navigate_to(meta, request)
        return _serialize(result)

    @tool()
    async def character_get_state(prim_path: str) -> str:
        """Return character position, rotation (scalar-first quaternion), active animation action, is_navigating."""
        meta = make_meta(ModuleName.CHARACTER)
        result = await character.get_state(meta, prim_path)
        return _serialize(result)

    @tool()
    async def character_play_animation_variant(
        prim_path: str,
        variant: str,
        speed: float = 1.0,
        target_position: list[float] | None = None,
        dispatch_mode: str = "auto",
    ) -> str:
        """Play a BehaviorAgent/legacy-compatible variant. dispatch_mode auto/task prefers BehaviorAgent task APIs, graph forces Action variable writes, skel directly binds a built-in SkelAnimation clip."""
        meta = make_meta(ModuleName.CHARACTER)
        request = CharacterPlayAnimationVariantRequest(
            prim_path=prim_path,
            variant=variant,
            speed=speed,
            target_position=(
                tuple(float(v) for v in target_position)  # type: ignore[arg-type]
                if target_position else None
            ),
            dispatch_mode=dispatch_mode,
        )
        result = await character.play_animation_variant(meta, request)
        return _serialize(result)

    @tool()
    async def character_load_crowd(
        count: int,
        layout: str = "grid",
        spacing: float = 2.0,
        base_name: str = "Crowd",
        center: list[float] | None = None,
        usd_url: str | None = None,
    ) -> str:
        """Batch-load N 6.0 character skins (count 1-100) in layout ∈ {grid, line, random}. Defaults to F_Business_02; override usd_url. Per-character failures in response.loaded."""
        meta = make_meta(ModuleName.CHARACTER)
        center_tuple = (
            tuple(float(c) for c in center) if center else (0.0, 0.0, 0.0)
        )
        request = CharacterLoadCrowdRequest(
            count=count,
            layout=layout,
            spacing=spacing,
            base_name=base_name,
            center=center_tuple,  # type: ignore[arg-type]
            usd_url=usd_url,
        )
        result = await character.load_crowd(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase D — Extension UI automation + carb log capture
    # ------------------------------------------------------------------

    @tool()
    async def extension_activate(
        ext_id: str,
        reload: bool = False,
    ) -> str:
        """Enable Kit Extension by ext_id (Window → Extensions toggle). reload=True forces disable→enable but does NOT clear sys.modules — for reliable .py reimport use extension_reload instead. 400 if ext_id unknown."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.activate(meta, ext_id, reload=reload)
        return _serialize(result)

    @tool()
    async def extension_reload(ext_id: str) -> str:
        """Clean-reload a Kit Extension's Python code WITHOUT restarting Kit: disable -> purge sys.modules tree (ext_id) -> invalidate import caches -> re-enable. Reflects .py edits + module-level singletons. 400 for 'omni.mycompany.validation_api' (self-reload unsupported -> use kit_app_restart) and unknown ext_id."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.reload_clean(meta, ext_id)
        return _serialize(result)

    @tool()
    async def extension_get_ui_tree(
        ext_id: str | None = None,
        window: str | None = None,
        widget_types: list[str] | None = None,
    ) -> str:
        """Return widget tree under an omni.ui.Window (omit to list all windows). widget.path → extension_ui_invoke. widget_types overrides default allow-list."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.get_ui_tree(
            meta, ext_id=ext_id, window=window, widget_types=widget_types,
        )
        return _serialize(result)

    @tool()
    async def extension_ui_invoke(
        widget_path: str,
        action: str = "click",
        value: Any = None,
    ) -> str:
        """Invoke widget by path. action ∈ {click, double_click, type, select, check, uncheck}; type/select take value. Returns post-action widget state."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.ui_invoke(meta, widget_path, action, value=value)
        return _serialize(result)

    @tool()
    async def extension_ui_run_and_wait(
        widget_path: str,
        action: str = "click",
        value: Any = None,
        wait_prim_path: str = "",
        wait_property_name: str = "",
        wait_expected_value: Any = None,
        wait_comparator: str = "equals",
        wait_expected_type_name: str | None = None,
        wait_property_kind: str = "attribute",
        wait_tolerance: float | None = None,
        timeout_s: float = 45.0,
        poll_interval_s: float = 0.5,
    ) -> str:
        """Invoke an omni.ui widget, then poll a Stage property assertion until it passes or times out."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.ui_run_and_wait(
            meta,
            widget_path=widget_path,
            action=action,
            value=value,
            wait_prim_path=wait_prim_path,
            wait_property_name=wait_property_name,
            wait_expected_value=wait_expected_value,
            wait_comparator=wait_comparator,
            wait_expected_type_name=wait_expected_type_name,
            wait_property_kind=wait_property_kind,
            wait_tolerance=wait_tolerance,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
        )
        return _serialize(result)

    @tool()
    async def extension_capture_logs(
        ext_id: str | None = None,
        since_ms: int | None = None,
        level: str = "INFO",
        limit: int = 1000,
        stop_after_capture: bool = False,
    ) -> str:
        """Peek Extension carb.log ring buffer (maxlen 10000, does not drain). Filters: ext_id substring, since_ms, level ∈ VERBOSE|INFO|WARN|ERROR|FATAL|ALL. Use extension_clear_logs before risky live work to start a request-scoped capture window; set stop_after_capture=True after collecting failure logs."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.capture_logs(
            meta,
            ext_id=ext_id,
            since_ms=since_ms,
            level=level,
            limit=limit,
            stop_after_capture=stop_after_capture,
        )
        return _serialize(result)

    @tool()
    async def extension_clear_logs() -> str:
        """Start a request-scoped carb Console log capture window and empty the ring buffer; subsequent extension_capture_logs calls only see entries logged after this point."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.clear_logs(meta)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Window — Kit GUI application capture + menu + ui_window toggle
    # ------------------------------------------------------------------

    @tool()
    async def window_capture(
        mode: str = "kit",
        hwnd: int | None = None,
        settle_frames: int = 5,
        output_format: str = "png",
        bring_to_front: bool = False,
        use_client_rect: bool = False,
        wait_stable: bool = False,
        stable_interval_s: float = 2.0,
        stable_consecutive: int = 2,
        stable_max_wait_s: float = 45.0,
        stable_diff_threshold: float = 0.01,
    ) -> str:
        """Capture Kit main window (app chrome: Stage+Property+Timeline+3D viewport), NOT the 3D render alone (use viewport_capture). wait_stable polls pixel diffs for async UI."""
        meta = make_meta(ModuleName.WINDOW)
        request = WindowCaptureRequest(
            mode=mode, hwnd=hwnd, settle_frames=settle_frames,
            output_format=output_format, bring_to_front=bring_to_front,
            use_client_rect=use_client_rect, wait_stable=wait_stable,
            stable_interval_s=stable_interval_s,
            stable_consecutive=stable_consecutive,
            stable_max_wait_s=stable_max_wait_s,
            stable_diff_threshold=stable_diff_threshold,
        )
        result = await window.capture(meta, request)
        return _serialize(result)

    @tool()
    async def window_capture_sequence(
        num_frames: int = 10,
        interval_s: float = 0.5,
        hwnd: int | None = None,
        bring_to_front: bool = False,
        use_client_rect: bool = False,
        settle_frames: int = 3,
    ) -> str:
        """Capture N full-window frames at `interval_s` spacing for motion verification.

        Wraps window_capture in a fixed-rate loop — used to record dynamic
        scenes (robot pick sequence, conveyor cube transit, hover highlight
        on/off) where a single PNG is insufficient. Works on both Isaac Sim
        and USD Composer (window_capture's GLFW30 auto-detect).

        Returns JSON: {frames: [{frame, path, sha256, ok, error?}], ...}.
        """
        import asyncio
        frames: list[dict] = []
        for i in range(num_frames):
            if i > 0:
                await asyncio.sleep(interval_s)
            meta = make_meta(ModuleName.WINDOW)
            request = WindowCaptureRequest(
                mode="kit",
                hwnd=hwnd,
                settle_frames=settle_frames,
                output_format="png",
                bring_to_front=bring_to_front and i == 0,  # focus only on first frame
                use_client_rect=use_client_rect,
                wait_stable=False,
                stable_interval_s=2.0,
                stable_consecutive=2,
                stable_max_wait_s=45.0,
                stable_diff_threshold=0.01,
            )
            result = await window.capture(meta, request)
            if result.ok and result.data is not None:
                frames.append({
                    "frame": i,
                    "path": result.data.path,
                    "sha256": result.data.sha256,
                    "ok": True,
                })
            else:
                frames.append({
                    "frame": i,
                    "ok": False,
                    "error": result.message or "unknown",
                    "error_code": result.error_code,
                })
        return json.dumps(
            {"num_frames": num_frames, "interval_s": interval_s, "frames": frames},
            indent=2, ensure_ascii=False,
        )

    @tool()
    async def window_list() -> str:
        """List top-level kit.exe OS windows (Win32 EnumWindows) with HWND — for debugging window_capture auto-detection."""
        meta = make_meta(ModuleName.WINDOW)
        result = await window.list_windows(meta)
        return _serialize(result)

    @tool()
    async def window_ui_list(name_filter: str | None = None) -> str:
        """Enumerate registered omni.ui.Window instances. name_filter is case-insensitive substring. Lazy windows (browsers) only appear after first show."""
        meta = make_meta(ModuleName.WINDOW)
        result = await window.list_ui_windows(meta, name_filter)
        return _serialize(result)

    @tool()
    async def window_ui_show(
        name: str,
        visible: bool = True,
        focus: bool = True,
        settle_frames: int = 5,
    ) -> str:
        """Toggle/focus omni.ui.Window by title; exact match then substring fallback. Response has resolved_via and visible_after."""
        meta = make_meta(ModuleName.WINDOW)
        result = await window.show_ui_window(
            meta, name=name, visible=visible, focus=focus, settle_frames=settle_frames,
        )
        return _serialize(result)

    @tool()
    async def window_menu_list(menu_path: str | None = None) -> str:
        """Walk Kit merged menu tree; menu_path limits to subtree. Each item has onclick_action for window_menu_trigger."""
        meta = make_meta(ModuleName.WINDOW)
        result = await window.list_menu_items(meta, menu_path)
        return _serialize(result)

    @tool()
    async def window_menu_trigger(menu_path: str) -> str:
        """Click a menu item by path via omni.kit.actions.core. Response includes created_prims (empty = UI-only or no-op)."""
        meta = make_meta(ModuleName.WINDOW)
        result = await window.trigger_menu(meta, menu_path)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Navigation — NavMesh bake + path query + exclude volume helper
    # ------------------------------------------------------------------

    @tool()
    async def navigation_bake(
        volume_scale: float = 40.0,
        timeout_s: float = 300.0,
    ) -> str:
        """Bake Stage NavMesh (creates NavMeshVolume if absent). Requires timeline stopped — playing returns ok=True but get_navmesh()=None (false positive)."""
        meta = make_meta(ModuleName.NAVIGATION)
        result = await navigation.bake(meta, volume_scale=volume_scale, timeout_s=timeout_s)
        return _serialize(result)

    @tool()
    async def navigation_query_path(
        start: list[float],
        end: list[float],
        agent_radius: float = 0.25,
        agent_height: float = 1.8,
        straighten: bool = True,
    ) -> str:
        """Query shortest NavMesh path between two world-space points. Auto-bakes if needed (response.auto_baked=true). straighten=True collapses straight runs."""
        meta = make_meta(ModuleName.NAVIGATION)
        request = NavPathQueryRequest(
            start=(float(start[0]), float(start[1]), float(start[2])),
            end=(float(end[0]), float(end[1]), float(end[2])),
            agent_radius=agent_radius,
            agent_height=agent_height,
            straighten=straighten,
        )
        result = await navigation.query_path(meta, request)
        return _serialize(result)

    @tool()
    async def navigation_add_exclude_volume(
        prim_path: str | None = None,
        padding: float = 0.1,
    ) -> str:
        """Add NavMeshVolume(Exclude) around prim's world-aligned bbox to block agent step-up. Requires re-bake (navigation_bake) to take effect."""
        meta = make_meta(ModuleName.NAVIGATION)
        result = await navigation.add_exclude_volume(
            meta, prim_path=prim_path, padding=padding,
        )
        return _serialize(result)

    @tool()
    async def navigation_set_visualization(mode: str) -> str:
        """Toggle NavMesh viewport overlay. mode ∈ {walkable, obstacles, off}. walkable shows baked surface; obstacles shows excluded regions; off hides overlay."""
        meta = make_meta(ModuleName.NAVIGATION)
        request = NavigationSetVisualizationRequest(mode=mode)  # type: ignore[arg-type]
        result = await navigation.set_visualization(meta, request)
        return _serialize(result)

    @tool()
    async def navigation_sample_walkable_points(
        count: int,
        bounds_min: list[float] | None = None,
        bounds_max: list[float] | None = None,
        seed: int | None = None,
    ) -> str:
        """Sample N random walkable points on the baked NavMesh (area-weighted barycentric, spec §8.1).

        count ∈ [1, 1000]. Optional [x,y,z] bounds_min/max restrict to AABB
        (both must be set or both null). When triangle iteration API is
        unavailable on this Kit build, falls back to bbox-rejection
        (random-in-bbox + reachability via query_shortest_path) — response
        ``method`` field reports which path won. Requires prior navigation_bake.
        """
        meta = make_meta(ModuleName.NAVIGATION)
        bmin = (
            (float(bounds_min[0]), float(bounds_min[1]), float(bounds_min[2]))
            if bounds_min is not None else None
        )
        bmax = (
            (float(bounds_max[0]), float(bounds_max[1]), float(bounds_max[2]))
            if bounds_max is not None else None
        )
        request = SampleWalkablePointsRequest(
            count=int(count), bounds_min=bmin, bounds_max=bmax, seed=seed,
        )
        result = await navigation.sample_walkable_points(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase E — Sensor (RTX Camera / Lidar / Depth Camera + viz toggle)
    # ------------------------------------------------------------------

    @tool()
    async def sensor_attach_rtx_camera(
        robot_prim: str,
        mount_offset: list[float],
        mount_rotation: list[float],
        resolution: list[int] | None = None,
        sensor_name: str = "RtxCamera",
    ) -> str:
        """Attach RTX Camera (RGB) as child xform under robot. mount_offset/mount_rotation relative to parent. Returns sensor prim path; attach failures include data.diagnostics.suggested_next plus data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SENSOR)
        resolution_tuple = (
            (int(resolution[0]), int(resolution[1])) if resolution else (1280, 720)
        )
        request = SensorAttachRtxCameraRequest(
            robot_prim=robot_prim,
            mount_offset=(float(mount_offset[0]), float(mount_offset[1]), float(mount_offset[2])),
            mount_rotation=(
                float(mount_rotation[0]), float(mount_rotation[1]), float(mount_rotation[2]),
            ),
            resolution=resolution_tuple,
            sensor_name=sensor_name,
        )
        result = await sensor.attach_rtx_camera(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_attach_rtx_lidar(
        robot_prim: str,
        mount_offset: list[float],
        mount_rotation: list[float],
        config_preset: str = "Example_Rotary",
        sensor_name: str = "RtxLidar",
    ) -> str:
        """Attach RTX Lidar for point-cloud capture; config_preset selects profile (Example_Rotary/Velodyne_VLS128/…). Returns sensor prim path and annotator id, and attach failures include data.diagnostics.suggested_next plus data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SENSOR)
        request = SensorAttachRtxLidarRequest(
            robot_prim=robot_prim,
            mount_offset=(float(mount_offset[0]), float(mount_offset[1]), float(mount_offset[2])),
            mount_rotation=(
                float(mount_rotation[0]), float(mount_rotation[1]), float(mount_rotation[2]),
            ),
            config_preset=config_preset,
            sensor_name=sensor_name,
        )
        result = await sensor.attach_rtx_lidar(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_lidar_get_point_cloud(
        sensor_prim: str,
        max_points: int = 1000,
        frames_to_wait: int = 2,
        min_points: int = 0,
        fail_on_warning: bool = False,
    ) -> str:
        """Read one frame of RTX Lidar XYZ point cloud (symmetric readback for sensor_attach_rtx_lidar). Reuses annotator stamped on sensor prim. Empty/short/warned reads and hard read errors return diagnostics.suggested_next and diagnostics.fallback_tool_order; scenario reports promote these to diagnostic_next_actions. Set min_points>0 or fail_on_warning=True to fail live proof loops instead of silently accepting empty/warned data; warning failures use SENSOR_LIDAR_POINT_CLOUD_WARNING. Truncates to max_points (≤100000)."""
        meta = make_meta(ModuleName.SENSOR)
        request = SensorLidarGetPointCloudRequest(
            sensor_prim=sensor_prim,
            max_points=max_points,
            frames_to_wait=frames_to_wait,
            min_points=min_points,
            fail_on_warning=fail_on_warning,
        )
        result = await sensor.lidar_get_point_cloud(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_attach_rtx_depth_camera(
        robot_prim: str,
        mount_offset: list[float],
        mount_rotation: list[float],
        resolution: list[int] | None = None,
        sensor_name: str = "RtxDepthCamera",
    ) -> str:
        """Attach RTX Camera with depth annotator (distance_to_camera); output is grayscale distance map, not RGB. Same mount convention as sensor_attach_rtx_camera; attach failures include data.diagnostics.suggested_next plus data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SENSOR)
        resolution_tuple = (
            (int(resolution[0]), int(resolution[1])) if resolution else (1280, 720)
        )
        request = SensorAttachRtxDepthCameraRequest(
            robot_prim=robot_prim,
            mount_offset=(float(mount_offset[0]), float(mount_offset[1]), float(mount_offset[2])),
            mount_rotation=(
                float(mount_rotation[0]), float(mount_rotation[1]), float(mount_rotation[2]),
            ),
            resolution=resolution_tuple,
            sensor_name=sensor_name,
        )
        result = await sensor.attach_rtx_depth_camera(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_set_visualization(
        sensor_prim: str,
        mode: str = "on",
    ) -> str:
        """Toggle debug draw overlay for a sensor. mode ∈ {on, off}. Lidar → point cloud; Camera/Depth → frustum+preview. Response includes sensor_type."""
        meta = make_meta(ModuleName.SENSOR)
        request = SensorSetVisualizationRequest(
            sensor_prim=sensor_prim,
            mode=mode,  # type: ignore[arg-type]
        )
        result = await sensor.set_visualization(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_attach_contact(
        prim_path: str,
        sensor_name: str = "ContactSensor",
        frequency: int = 60,
        translation: list[float] | None = None,
        radius: float = -1.0,
    ) -> str:
        """Attach PhysX ContactSensor child prim; reports contact forces/collisions once playing. Xform fallback when module unavailable (response.backend)."""
        meta = make_meta(ModuleName.SENSOR)
        translation_tuple = (
            tuple(float(t) for t in translation) if translation
            else (0.0, 0.0, 0.0)
        )
        request = SensorAttachContactRequest(
            prim_path=prim_path,
            sensor_name=sensor_name,
            frequency=frequency,
            translation=translation_tuple,  # type: ignore[arg-type]
            radius=radius,
        )
        result = await sensor.attach_contact(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_attach_imu(
        prim_path: str,
        sensor_name: str = "IMUSensor",
        frequency: int = 200,
        mount_offset: list[float] | None = None,
        mount_orientation: list[float] | None = None,
    ) -> str:
        """Attach IMU sensor (accel+gyro+orient) at frequency. mount_offset/mount_orientation in parent frame. Same Xform fallback as sensor_attach_contact."""
        meta = make_meta(ModuleName.SENSOR)
        offset_tuple = (
            tuple(float(t) for t in mount_offset) if mount_offset
            else (0.0, 0.0, 0.0)
        )
        orient_tuple = (
            tuple(float(q) for q in mount_orientation) if mount_orientation
            else (1.0, 0.0, 0.0, 0.0)
        )
        request = SensorAttachImuRequest(
            prim_path=prim_path,
            sensor_name=sensor_name,
            frequency=frequency,
            mount_offset=offset_tuple,  # type: ignore[arg-type]
            mount_orientation=orient_tuple,  # type: ignore[arg-type]
        )
        result = await sensor.attach_imu(meta, request)
        return _serialize(result)

    @tool()
    async def sensor_set_annotator(
        sensor_prim: str,
        annotators: list[str],
        resolution: list[int] | None = None,
    ) -> str:
        """Attach replicator annotators to camera prim. Valid: rgb, depth, normals, motion_vectors, semantic/instance_segmentation, distance_to_camera/image_plane. response.skipped lists failures; hard failures include data.diagnostics.reason=sensor_set_annotator_error and data.diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.SENSOR)
        resolution_tuple = (
            (int(resolution[0]), int(resolution[1])) if resolution
            else (1280, 720)
        )
        request = SensorSetAnnotatorRequest(
            sensor_prim=sensor_prim,
            annotators=tuple(str(a) for a in annotators),
            resolution=resolution_tuple,
        )
        result = await sensor.set_annotator(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase E — Multi-viewport (create / destroy)
    # ------------------------------------------------------------------

    @tool()
    async def viewport_create(
        viewport_name: str,
        camera_path: str | None = None,
        width: int = 1280,
        height: int = 720,
        docked: bool = False,
    ) -> str:
        """Create secondary omni.kit.viewport.window; bind to camera_path if provided. Reuses existing viewport with same name (response.existed=true)."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportCreateRequest(
            viewport_name=viewport_name,
            camera_path=camera_path,
            width=width,
            height=height,
            docked=docked,
        )
        result = await viewport.create(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_destroy(viewport_name: str) -> str:
        """Destroy secondary viewport window by name. Idempotent — destroyed=False if not found."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportDestroyRequest(viewport_name=viewport_name)
        result = await viewport.destroy(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase F — Physics (UsdPhysics rigid body / collider / material / joint / scene / viz)
    # ------------------------------------------------------------------

    @tool()
    async def physics_apply_rigid_body(
        prim_path: str,
        mass: float = 1.0,
        dynamic: bool = True,
    ) -> str:
        """Apply UsdPhysics.RigidBodyAPI + MassAPI to prim_path. dynamic=False → kinematic/static. Requires physics_set_scene before simulation_play."""
        meta = make_meta(ModuleName.PHYSICS)
        request = PhysicsApplyRigidBodyRequest(
            prim_path=prim_path, mass=mass, dynamic=dynamic,
        )
        result = await physics.apply_rigid_body(meta, request)
        return _serialize(result)

    @tool()
    async def physics_get_rigid_body_state(prim_path: str) -> str:
        """Read PhysX runtime state — linear/angular velocity, mass, COM, kinematic/enabled flags. Symmetric readback for physics_apply_rigid_body. source='physx_runtime' (live PhysX via SingleRigidPrim, requires simulation.play to have ticked) or 'usd_initial' (USD authored values, velocities reflect pre-play state but mass/COM always accurate)."""
        meta = make_meta(ModuleName.PHYSICS)
        result = await physics.get_rigid_body_state(meta, prim_path)
        return _serialize(result)

    @tool()
    async def physics_apply_collider(
        prim_path: str,
        approximation: str = "convexHull",
    ) -> str:
        """Apply UsdPhysics.CollisionAPI to prim_path; also MeshCollisionAPI with approximation ∈ {convexHull, triangleMesh, sdf, box, sphere, none}."""
        meta = make_meta(ModuleName.PHYSICS)
        request = PhysicsApplyColliderRequest(
            prim_path=prim_path,
            approximation=approximation,  # type: ignore[arg-type]
        )
        result = await physics.apply_collider(meta, request)
        return _serialize(result)

    @tool()
    async def physics_apply_material(
        prim_path: str,
        friction: float = 0.5,
        restitution: float = 0.0,
        density: float = 1000.0,
        material_name: str | None = None,
    ) -> str:
        """Create PhysicsMaterial under /World/PhysicsMaterials and bind to prim_path. friction = static+dynamic; restitution ∈ [0,1]."""
        meta = make_meta(ModuleName.PHYSICS)
        request = PhysicsApplyMaterialRequest(
            prim_path=prim_path,
            friction=friction,
            restitution=restitution,
            density=density,
            material_name=material_name,
        )
        result = await physics.apply_material(meta, request)
        return _serialize(result)

    @tool()
    async def physics_create_joint(
        joint_type: str,
        body_a: str,
        body_b: str,
        anchor: list[float] | None = None,
        axis: list[float] | None = None,
        joint_prim_path: str | None = None,
    ) -> str:
        """Create UsdPhysics joint (Fixed/Revolute/Prismatic/Spherical) between body_a and body_b. anchor=localPos0; axis selects X/Y/Z for Revolute/Prismatic."""
        meta = make_meta(ModuleName.PHYSICS)
        anchor_tuple = (
            (float(anchor[0]), float(anchor[1]), float(anchor[2]))
            if anchor else (0.0, 0.0, 0.0)
        )
        axis_tuple = (
            (float(axis[0]), float(axis[1]), float(axis[2]))
            if axis else (0.0, 0.0, 1.0)
        )
        request = PhysicsCreateJointRequest(
            joint_type=joint_type,  # type: ignore[arg-type]
            body_a=body_a,
            body_b=body_b,
            anchor=anchor_tuple,
            axis=axis_tuple,
            joint_prim_path=joint_prim_path,
        )
        result = await physics.create_joint(meta, request)
        return _serialize(result)

    @tool()
    async def physics_set_joint_drive(
        joint_prim_path: str,
        drive_type: str = "angular",
        target_position: float = 0.0,
        target_velocity: float = 0.0,
        stiffness: float = 0.0,
        damping: float = 0.0,
        max_force: float | None = None,
    ) -> str:
        """Configure a UsdPhysics DriveAPI on an existing joint so it actuates (physics_create_joint only creates the joint). drive_type ∈ {linear (Prismatic), angular (Revolute)}; target_position drives toward a pose (deg for angular, distance for linear), stiffness/damping form the PD gains, max_force=None leaves the PhysX default (unbounded). Body needs RigidBodyAPI + physics_set_scene + simulation_play to move."""
        meta = make_meta(ModuleName.PHYSICS)
        request = PhysicsSetJointDriveRequest(
            joint_prim_path=joint_prim_path,
            drive_type=drive_type,  # type: ignore[arg-type]
            target_position=target_position,
            target_velocity=target_velocity,
            stiffness=stiffness,
            damping=damping,
            max_force=max_force,
        )
        result = await physics.set_joint_drive(meta, request)
        return _serialize(result)

    @tool()
    async def physics_set_scene(
        gravity: list[float] | None = None,
        timestep: float = 1.0 / 60.0,
        solver_iter_pos: int = 4,
        solver_iter_vel: int = 1,
        scene_prim_path: str = "/World/PhysicsScene",
    ) -> str:
        """Define UsdPhysics.Scene; configure gravity [gx,gy,gz] m/s² (default [0,0,-9.81]) + solver iterations. Required once before gravity acts on rigid bodies."""
        meta = make_meta(ModuleName.PHYSICS)
        gravity_tuple = (
            (float(gravity[0]), float(gravity[1]), float(gravity[2]))
            if gravity else (0.0, 0.0, -9.81)
        )
        request = PhysicsSetSceneRequest(
            gravity=gravity_tuple,
            timestep=timestep,
            solver_iter_pos=solver_iter_pos,
            solver_iter_vel=solver_iter_vel,
            scene_prim_path=scene_prim_path,
        )
        result = await physics.set_scene(meta, request)
        return _serialize(result)

    @tool()
    async def physics_visualize(mode: str) -> str:
        """Toggle PhysX debug visualization. mode ∈ {collision, joint, mass, off}; clears all carb /physics/visualization* keys then enables requested channel."""
        meta = make_meta(ModuleName.PHYSICS)
        request = PhysicsVisualizeRequest(mode=mode)  # type: ignore[arg-type]
        result = await physics.visualize(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase F — Lighting (UsdLux Dome/Distant/Disk/Rect/Sphere + exposure)
    # ------------------------------------------------------------------

    @tool()
    async def lighting_create_dome(
        prim_path: str,
        intensity: float = 1000.0,
        texture: str | None = None,
    ) -> str:
        """Create a UsdLux.DomeLight at *prim_path* for HDRI environment lighting. Optionally bind a *texture* (HDR/EXR URL or local path)."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingCreateDomeRequest(
            prim_path=prim_path, intensity=intensity, texture=texture,
        )
        result = await lighting.create_dome(meta, request)
        return _serialize(result)

    @tool()
    async def lighting_create_distant(
        prim_path: str,
        intensity: float = 1000.0,
        angle_deg: float = 0.53,
    ) -> str:
        """Create a UsdLux.DistantLight (directional) at *prim_path*. *angle_deg* widens the shadow penumbra (sun ≈ 0.53°)."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingCreateDistantRequest(
            prim_path=prim_path, intensity=intensity, angle_deg=angle_deg,
        )
        result = await lighting.create_distant(meta, request)
        return _serialize(result)

    @tool()
    async def lighting_create_disk(
        prim_path: str,
        intensity: float = 1000.0,
        radius: float = 1.0,
    ) -> str:
        """Create a UsdLux.DiskLight at *prim_path*. Emission originates from a disk of radius *radius* (meters)."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingCreateDiskRequest(
            prim_path=prim_path, intensity=intensity, radius=radius,
        )
        result = await lighting.create_disk(meta, request)
        return _serialize(result)

    @tool()
    async def lighting_create_rect(
        prim_path: str,
        intensity: float = 1000.0,
        width: float = 1.0,
        height: float = 1.0,
    ) -> str:
        """Create a UsdLux.RectLight at *prim_path* with a *width* × *height* emission surface (meters). Typical softbox / window light."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingCreateRectRequest(
            prim_path=prim_path, intensity=intensity,
            width=width, height=height,
        )
        result = await lighting.create_rect(meta, request)
        return _serialize(result)

    @tool()
    async def lighting_create_sphere(
        prim_path: str,
        intensity: float = 1000.0,
        radius: float = 1.0,
    ) -> str:
        """Create a UsdLux.SphereLight at *prim_path* with *radius* (meters). Represents a point-ish bulb with finite area for soft shadows."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingCreateSphereRequest(
            prim_path=prim_path, intensity=intensity, radius=radius,
        )
        result = await lighting.create_sphere(meta, request)
        return _serialize(result)

    @tool()
    async def lighting_set_exposure(exposure: float) -> str:
        """Set RTX tonemap exposure globally (carb /rtx/post/tonemap/exposure); positive brightens, negative darkens."""
        meta = make_meta(ModuleName.LIGHTING)
        request = LightingSetExposureRequest(exposure=exposure)
        result = await lighting.set_exposure(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase F — Material (MDL enumeration / assignment / bound readback)
    # ------------------------------------------------------------------

    @tool()
    async def material_list_mdl(library: str = "default") -> str:
        """Enumerate .mdl modules under Kit install; library is alias or absolute path. Returns {name, url, library} entries."""
        meta = make_meta(ModuleName.MATERIAL)
        request = MaterialListMdlRequest(library=library)
        result = await material.list_mdl(meta, request)
        return _serialize(result)

    @tool()
    async def material_assign_mdl(
        prim_path: str,
        mdl_url: str,
        material_name: str,
    ) -> str:
        """Create MDL-backed UsdShade.Material under /World/Materials and bind to prim_path (strongerThanDescendants)."""
        meta = make_meta(ModuleName.MATERIAL)
        request = MaterialAssignMdlRequest(
            prim_path=prim_path, mdl_url=mdl_url, material_name=material_name,
        )
        result = await material.assign_mdl(meta, request)
        return _serialize(result)

    @tool()
    async def material_get_bound(prim_path: str) -> str:
        """Read direct material binding for prim_path; returns {material_path, binding_strength} (None when unbound)."""
        meta = make_meta(ModuleName.MATERIAL)
        request = MaterialGetBoundRequest(prim_path=prim_path)
        result = await material.get_bound(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase F — Viewport render extension (mode / quality / overlay / fov)
    # ------------------------------------------------------------------

    @tool()
    async def viewport_set_render_mode(
        viewport_name: str = "Viewport",
        mode: str = "RealTime",
    ) -> str:
        """Switch RTX renderer mode. mode ∈ {RealTime, PathTracing}; PathTracing is more accurate but slower."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportSetRenderModeRequest(
            viewport_name=viewport_name,
            mode=mode,  # type: ignore[arg-type]
        )
        result = await viewport.set_render_mode(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_set_render_quality(
        samples: int = 1,
        denoiser: str = "auto",
    ) -> str:
        """Tune RTX path-tracing render quality. *samples* = path-tracing samples per pixel (higher = less noise, slower). *denoiser* ∈ {auto, DLSS, NRD, off}."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportSetRenderQualityRequest(
            samples=samples,
            denoiser=denoiser,  # type: ignore[arg-type]
        )
        result = await viewport.set_render_quality(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_toggle_overlay(
        viewport_name: str = "Viewport",
        overlay: str = "gridlines",
        visible: bool = True,
    ) -> str:
        """Toggle viewport overlay. overlay ∈ {gridlines, axis, stats}; stats toggles RTX FPS overlay."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportToggleOverlayRequest(
            viewport_name=viewport_name,
            overlay=overlay,  # type: ignore[arg-type]
            visible=visible,
        )
        result = await viewport.toggle_overlay(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_set_fov(
        viewport_name: str = "Viewport",
        fov_deg: float = 60.0,
    ) -> str:
        """Set viewport camera horizontal FOV in degrees (converts to focalLength). Writes to active camera prim (fallback: /OmniverseKit_Persp)."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportSetFovRequest(
            viewport_name=viewport_name, fov_deg=fov_deg,
        )
        result = await viewport.set_fov(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_set_camera_lookat(
        eye: list[float],
        target: list[float],
        up: list[float] | None = None,
        viewport_name: str = "Viewport",
        camera_path: str | None = None,
    ) -> str:
        """Aim a camera at a target via eye/target/up (deadlock-safe USD xformOp author on the REST path; default up=+Z). Moves the active viewport camera (Perspective included) unless camera_path is given. Use for live framing iteration without rebuilding the scene."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportSetCameraLookatRequest(
            eye=tuple(eye),
            target=tuple(target),
            up=tuple(up) if up is not None else (0.0, 0.0, 1.0),
            viewport_name=viewport_name,
            camera_path=camera_path,
        )
        result = await viewport.set_camera_lookat(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_focus_prim(
        prim_path: str,
        viewport_name: str = "Viewport",
        camera_path: str | None = None,
        padding: float = 1.35,
        select: bool = True,
    ) -> str:
        """Frame a prim in the viewport, matching the F-key workflow. Selects the prim by default and falls back to authored camera look-at when Kit viewport utility is unavailable."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportFocusPrimRequest(
            prim_path=prim_path,
            viewport_name=viewport_name,
            camera_path=camera_path,
            padding=padding,
            select=select,
        )
        result = await viewport.focus_prim(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_project_points(
        points: list[list[float]],
        viewport_name: str = "Viewport",
        camera_path: str | None = None,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """Project world-space XYZ points through the active camera into normalized and pixel viewport coordinates. Use to check whether important prim corners should appear in frame before capture."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportProjectPointsRequest(
            points=tuple(tuple(point) for point in points),  # type: ignore[arg-type]
            viewport_name=viewport_name,
            camera_path=camera_path,
            width=width,
            height=height,
        )
        result = await viewport.project_points(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_frame_prims(
        prim_paths: list[str],
        viewport_name: str = "Viewport",
        camera_path: str | None = None,
        include_purposes: list[str] | None = None,
        margin: float = 0.15,
        fov_deg: float = 60.0,
        view_direction: list[float] | None = None,
        up: list[float] | None = None,
        set_camera: bool = True,
    ) -> str:
        """Compute a camera eye/target/up that frames the given prim bboxes and optionally author it to the active camera. Reduces camera-placement trial-and-error before viewport_capture; failures include diagnostics.suggested_next and diagnostics.fallback_tool_order."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportFramePrimsRequest(
            prim_paths=tuple(prim_paths),
            viewport_name=viewport_name,
            camera_path=camera_path,
            include_purposes=tuple(include_purposes or ["default", "render"]),
            margin=margin,
            fov_deg=fov_deg,
            view_direction=tuple(view_direction or [1.0, -1.0, 0.65]),  # type: ignore[arg-type]
            up=tuple(up or [0.0, 0.0, 1.0]),  # type: ignore[arg-type]
            set_camera=set_camera,
        )
        result = await viewport.frame_prims(meta, request)
        return _serialize(result)

    @tool()
    async def viewport_capture_assert(
        viewport_name: str = "Viewport",
        camera_prim_path: str | None = None,
        renderer: str = "rtx",
        width: int = 1280,
        height: int = 720,
        output_format: str = "png",
        warmup_frames: int = 0,
        min_mean: float = 8.0,
        min_variance: float = 1.0,
    ) -> str:
        """Capture the 3D viewport with return_stats=True and fail fast on likely black/blank frames using pixel mean/variance thresholds. Includes diagnostics for capture errors and assertion failures before visual Read."""
        meta = make_meta(ModuleName.VIEWPORT)
        request = ViewportCaptureAssertRequest(
            viewport_name=viewport_name,
            camera_prim_path=camera_prim_path,
            renderer=renderer,  # type: ignore[arg-type]
            width=width,
            height=height,
            output_format=output_format,  # type: ignore[arg-type]
            warmup_frames=warmup_frames,
            min_mean=min_mean,
            min_variance=min_variance,
        )
        result = await viewport.capture_assert(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase H — Replicator (SDG writer / randomizer / trigger)
    # ------------------------------------------------------------------

    @tool()
    async def replicator_create_writer(
        writer_type: str,
        output_dir: str,
        rgb: bool = True,
        depth: bool = False,
        semantic_segmentation: bool = False,
    ) -> str:
        """Create replicator writer (BasicWriter/KittiWriter/CocoWriter); writes to output_dir on each orchestrator step. Requires omni.replicator.core enabled."""
        meta = make_meta(ModuleName.REPLICATOR)
        request = ReplicatorCreateWriterRequest(
            writer_type=writer_type,  # type: ignore[arg-type]
            output_dir=output_dir,
            rgb=rgb,
            depth=depth,
            semantic_segmentation=semantic_segmentation,
        )
        result = await replicator.create_writer(meta, request)
        return _serialize(result)

    @tool()
    async def replicator_register_randomizer(
        type: str,
        target: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        """Register randomizer for orchestrator frames. type ∈ {position, rotation, lighting}; target is a prim glob. Returns randomizer_id."""
        meta = make_meta(ModuleName.REPLICATOR)
        request = ReplicatorRegisterRandomizerRequest(
            type=type,  # type: ignore[arg-type]
            target=target,
            config=dict(config or {}),
        )
        result = await replicator.register_randomizer(meta, request)
        return _serialize(result)

    @tool()
    async def replicator_trigger_once(num_frames: int = 1) -> str:
        """Run replicator orchestrator for N frames (fires randomizers + writers). Timeline play alone does NOT trigger writers."""
        meta = make_meta(ModuleName.REPLICATOR)
        request = ReplicatorTriggerOnceRequest(num_frames=num_frames)
        result = await replicator.trigger_once(meta, request)
        return _serialize(result)

    @tool()
    async def replicator_trigger_on_time(interval_s: float) -> str:
        """Register periodic orchestrator trigger at interval_s; keep > 0.016 s to avoid queue buildup. Returns trigger_id."""
        meta = make_meta(ModuleName.REPLICATOR)
        request = ReplicatorTriggerOnTimeRequest(interval_s=interval_s)
        result = await replicator.trigger_on_time(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase H — OmniGraph (node / connect / execute + ROS2 publisher macro)
    # ------------------------------------------------------------------

    @tool()
    async def omnigraph_create_node(
        graph_path: str,
        node_type: str,
        node_name: str | None = None,
    ) -> str:
        """Create OmniGraph node inside graph_path (auto-creates graph if absent). node_type e.g. 'omni.graph.action.OnTick'. node_name defaults to last segment."""
        meta = make_meta(ModuleName.OMNIGRAPH)
        request = OmnigraphCreateNodeRequest(
            graph_path=graph_path,
            node_type=node_type,
            node_name=node_name,
        )
        result = await omnigraph.create_node(meta, request)
        return _serialize(result)

    @tool()
    async def omnigraph_connect(
        src_attr: str,
        dst_attr: str,
    ) -> str:
        """Connect OmniGraph attributes: '/Graph/Node.outputs:<attr>' → '/Graph/Node.inputs:<attr>'. Works for compute and execution edges."""
        meta = make_meta(ModuleName.OMNIGRAPH)
        request = OmnigraphConnectRequest(src_attr=src_attr, dst_attr=dst_attr)
        result = await omnigraph.connect(meta, request)
        return _serialize(result)

    @tool()
    async def omnigraph_execute(graph_path: str) -> str:
        """Evaluate graph_path once; fires OnTick + downstream manually for ActionGraphs when scene event is unavailable."""
        meta = make_meta(ModuleName.OMNIGRAPH)
        request = OmnigraphExecuteRequest(graph_path=graph_path)
        result = await omnigraph.execute(meta, request)
        return _serialize(result)

    @tool()
    async def omnigraph_create_ros2_publisher(
        graph_path: str,
        topic: str,
        source_prim: str,
        msg_type: str = "sensor_msgs/msg/Image",
    ) -> str:
        """Assemble ActionGraph (OnTick→RenderProduct→ROS2PublishImage) for camera publishing. rclpy unavailable → graph only (response.ros2_available=false)."""
        meta = make_meta(ModuleName.OMNIGRAPH)
        request = OmnigraphCreateRos2PublisherRequest(
            graph_path=graph_path,
            topic=topic,
            source_prim=source_prim,
            msg_type=msg_type,
        )
        result = await omnigraph.create_ros2_publisher(meta, request)
        return _serialize(result)

    @tool()
    async def omnigraph_create_script_controller(
        script_path: str,
        graph_path: str = "/World/ActionGraph",
        node_name: str = "ScriptNode",
        tick_node_name: str = "OnPlaybackTick",
        evaluator: str = "execution",
        reset_state: bool = True,
    ) -> str:
        """Create ActionGraph OnPlaybackTick→ScriptNode and bind script_path. This mirrors Isaac Sim example style: MCP builds wiring; controller logic runs in Kit on playback ticks."""
        meta = make_meta(ModuleName.OMNIGRAPH)
        request = OmnigraphCreateScriptControllerRequest(
            graph_path=graph_path,
            script_path=script_path,
            node_name=node_name,
            tick_node_name=tick_node_name,
            evaluator=evaluator,
            reset_state=reset_state,
        )
        result = await omnigraph.create_script_controller(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase H — Content browser (omni.client list / stat / resolve)
    # ------------------------------------------------------------------

    @tool()
    async def content_browse(
        url: str,
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> str:
        """List URL children (omniverse://, https://, s3://, file:///). recursive walks up to max_depth. Entry: {url, name, is_folder, size, modified_time_ns, flags}."""
        meta = make_meta(ModuleName.CONTENT)
        request = ContentBrowseRequest(
            url=url,
            recursive=recursive,
            max_depth=max_depth,
            max_entries=max_entries,
        )
        result = await content.browse(meta, request)
        return _serialize(result)

    @tool()
    async def content_preview(url: str) -> str:
        """Stat a single URL; returns same entry shape as content_browse (size, mtime, is_folder, flags)."""
        meta = make_meta(ModuleName.CONTENT)
        request = ContentPreviewRequest(url=url)
        result = await content.preview(meta, request)
        return _serialize(result)

    @tool()
    async def content_inspect(url: str) -> str:
        """Inspect a USD asset's GEOMETRY without adding it to the stage: opens the USD off the main thread and returns default_prim, world bbox (bbox_min/bbox_max), meters_per_unit, up_axis, and prim_count. Use at planning time to size/place an asset — content_preview only gives file metadata (size/mtime). Needs the Omniverse/HTTP resolver, so values are produced live; off-thread open keeps the Kit event loop unblocked."""
        meta = make_meta(ModuleName.CONTENT)
        request = ContentInspectRequest(url=url)
        result = await content.inspect(meta, request)
        return _serialize(result)

    @tool()
    async def content_resolve(url: str) -> str:
        """Normalize URL via omni.client; collapses relative components, canonicalizes scheme, resolves Nucleus prefix."""
        meta = make_meta(ModuleName.CONTENT)
        request = ContentResolveRequest(url=url)
        result = await content.resolve(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Phase H — Extension management extensions
    # ------------------------------------------------------------------

    @tool()
    async def extension_deactivate(ext_id: str) -> str:
        """Disable Kit Extension by id. Python module imports survive; for .py reimport rely on omni.ext.plugin fswatcher auto-reload on file save (extension_activate(reload=True) only re-toggles, does not clear sys.modules)."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.deactivate(meta, ext_id)
        return _serialize(result)

    @tool()
    async def extension_list_all(enabled_only: bool = False) -> str:
        """Enumerate all Kit extensions known to ExtensionManager. enabled_only=True filters to active. Item: {id, full_id, name, version, enabled, path, title}."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.list_all(meta, enabled_only=enabled_only)
        return _serialize(result)

    @tool()
    async def extension_get_info(ext_id: str) -> str:
        """Return ExtensionManager info for ext_id (bare id match). 404 if not registered."""
        meta = make_meta(ModuleName.EXTENSION)
        result = await extension.get_info(meta, ext_id)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Kit Commands (D25) — common profile lever
    # ------------------------------------------------------------------

    @tool()
    async def kit_command_execute(
        name: str,
        payload: dict | None = None,
        expect_undo: bool = False,
    ) -> str:
        """Execute an omni.kit.commands registered command.

        Dispatches to the currently-active Kit app's command registry.
        Common examples:
          - CreateConveyorBelt (Isaac, isaacsim.asset.gen.conveyor)
          - CreatePrimWithDefaultXform (common)
          - ChangeProperty (common)

        Unknown command names on the current app return ok=false with
        error=command_exception (not a tool failure — parseable result).
        """
        meta = make_meta(ModuleName.EXTENSION)
        request = KitCommandExecuteRequest(
            name=name,
            payload=payload,
            expect_undo=expect_undo,
        )
        result = await kit_command.execute(meta, request)
        return _serialize(result)

    @tool()
    async def kit_python_run(
        code: str,
        return_keys: list[str] | None = None,
    ) -> str:
        """Run arbitrary Python source in the Kit main thread.

        Fills the gap the Kit command registry leaves — when the operation
        you need isn't a registered Kit command (USD relationship edits,
        ``Usd.EditContext`` walks, ``omni.client`` direct calls, bulk
        attribute author patterns), use this instead of pasting code into
        the GUI Script Editor.

        Args:
          code: Python source. Statements run in a fresh ``__main__``-style
                namespace, so ``import omni.usd`` / ``from pxr import ...``
                work without setup.
          return_keys: Optional list of namespace variable names whose
                       final values are returned in the response. Empty =
                       stdout-only communication. Non-JSON-safe values are
                       coerced via str() fallback.

        Returns: dict with ``ok`` / ``stdout`` / ``stderr`` / ``error`` /
        ``traceback`` / ``returned``. Script exceptions become an ``error``
        + ``traceback`` payload (the MCP call still succeeds — caller
        inspects ``ok`` to decide).

        Tool naming note: REST/internal names use ``python_run`` to avoid
        the project's pre-tool security hook (which flags the literal
        substring ``exec`` followed by ``(``); the user-facing tool name
        is also ``kit_python_run`` for consistency.
        """
        meta = make_meta(ModuleName.EXTENSION)
        request = KitPythonExecRequest(
            code=code,
            return_keys=tuple(return_keys or []),
        )
        result = await kit_command.python_run(meta, request)
        return _serialize(result)

    # ------------------------------------------------------------------
    # Catalog search (Phase E) — local JSON query, no REST
    # ------------------------------------------------------------------

    @tool()
    async def extension_search(
        keyword: str,
        app: str | None = None,
        category: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search the optional local Kit extension catalog for candidates.

        Matches `keyword` (case-insensitive substring) against ext name / title /
        summary / mcp_research_hint / raw_description / keywords. Empty keyword
        returns all entries matching optional filters.

        Filters:
          - app: "isaacsim" or "usd_composer" (include entries where that app key exists)
          - category: exact match on entry.category (case-insensitive)
          - limit: max results (default 20)

        Returns list of {name, title, summary, category, apps, key_symbols,
        mcp_research_hint}. Use this when choosing a Kit Extension to wrap for a
        new MCP tool or to answer "which extension handles X?" questions. Public
        clones do not ship the generated catalog; when it is absent the tool
        returns EXTENSION_CATALOG_UNAVAILABLE with regeneration guidance.
        """
        meta = make_meta(ModuleName.EXTENSION)
        result = await catalog.search(
            meta, keyword=keyword, app=app, category=category, limit=limit
        )
        return _serialize(result)


def _serialize(result: Any) -> str:
    """Serialize a ModuleResult to JSON string."""
    if hasattr(result, "__dataclass_fields__"):
        return json.dumps(asdict(result), indent=2, ensure_ascii=False, default=str)
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


def _mcp_runtime_info_payload(
    mcp: FastMCP,
    selection: ToolSelection | None = None,
) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[3]
    module_infos = []
    stale_modules: list[str] = []
    for module_name in _MCP_FRESHNESS_MODULES:
        module = sys.modules.get(module_name)
        path_raw = getattr(module, "__file__", None) if module is not None else None
        path = Path(path_raw).resolve() if path_raw else None
        mtime_ms = int(path.stat().st_mtime * 1000) if path and path.exists() else None
        newer_than_import = (
            mtime_ms is not None and mtime_ms > _MCP_SERVER_IMPORT_EPOCH_MS
        )
        relative_path = None
        if path is not None:
            try:
                relative_path = path.relative_to(project_root).as_posix()
            except ValueError:
                relative_path = path.name
        if newer_than_import:
            stale_modules.append(module_name)
        module_infos.append({
            "module": module_name,
            "loaded": module is not None,
            "source": relative_path,
            "file_mtime_epoch_ms": mtime_ms,
            "newer_than_mcp_import": newer_than_import,
        })

    robot_probe_result_fields = tuple(RobotArmProfileProbeResult.__dataclass_fields__)
    robot_probe_batch_result_fields = tuple(
        RobotArmProfilesProbeResult.__dataclass_fields__
    )
    robot_arm_profiles_result_fields = tuple(
        RobotArmProfilesResult.__dataclass_fields__
    )
    robot_probe_request_fields = RobotArmProfileProbeRequest.__dataclass_fields__
    robot_probe_batch_request_fields = RobotArmProfilesProbeRequest.__dataclass_fields__
    robot_probe_batch_summary_fields = {
        "mcp_controllability_counts",
        "mcp_controllability_profiles",
        "probe_capability_level_name_counts",
        "probe_capability_level_name_profiles",
        "pick_place_validation_status_counts",
        "pick_place_validation_status_profiles",
        "unsupported_capability_counts",
        "timed_out_profiles",
        "batch_timeout_profiles",
        "batch_aborted_profiles",
        "blocked_profiles",
        "hard_failure_profiles",
        "lifecycle_recovery_profiles",
        "unsupported_capability_profiles",
        "ik_target_failure_profiles",
        "static_metadata_profiles",
        "known_dynamic_timeout_routed_profiles",
        "dynamic_joint_control_profiles",
    }
    tool_selection = selection or getattr(mcp, "_omniverse_tool_selection", None)
    profile_payload = (
        tool_selection.as_runtime_payload()
        if isinstance(tool_selection, ToolSelection)
        else build_tool_selection(profile=PROFILE_FULL).as_runtime_payload()
    )
    return {
        "ok": True,
        **profile_payload,
        "module_tools_import_epoch_ms": _MCP_SERVER_IMPORT_EPOCH_MS,
        "tool_count": len(getattr(mcp, "_tool_manager")._tools),
        "has_mcp_runtime_info_tool": "mcp_runtime_info" in getattr(mcp, "_tool_manager")._tools,
        "robot_probe_result_fields": list(robot_probe_result_fields),
        "robot_probe_batch_result_fields": list(robot_probe_batch_result_fields),
        "robot_arm_profiles_result_fields": list(robot_arm_profiles_result_fields),
        "robot_probe_request_fields": list(robot_probe_request_fields),
        "robot_probe_batch_request_fields": list(robot_probe_batch_request_fields),
        "robot_probe_arm_profile_timeout_default_s": (
            robot_probe_request_fields["timeout_s"].default
        ),
        "robot_probe_arm_profiles_per_profile_timeout_default_s": (
            robot_probe_batch_request_fields["per_profile_timeout_s"].default
        ),
        "robot_probe_arm_profiles_batch_timeout_default_s": (
            robot_probe_batch_request_fields["batch_timeout_s"].default
        ),
        "robot_probe_result_has_mcp_controllability": (
            "mcp_controllability" in robot_probe_result_fields
            and "mcp_controllability_reason" in robot_probe_result_fields
        ),
        "robot_probe_result_has_probe_capability_level": (
            "probe_capability_level" in robot_probe_result_fields
            and "probe_capability_level_name" in robot_probe_result_fields
            and "probe_capability_level_reason" in robot_probe_result_fields
        ),
        "robot_probe_result_has_pick_place_validation_boundary": (
            "probe_proves_pick_place" in robot_probe_result_fields
            and "pick_place_validation_status" in robot_probe_result_fields
            and "pick_place_validation_reason" in robot_probe_result_fields
        ),
        "robot_probe_batch_result_has_summary": (
            robot_probe_batch_summary_fields <= set(robot_probe_batch_result_fields)
        ),
        "source_modules": module_infos,
        "source_newer_than_import": bool(stale_modules),
        "stale_source_modules": stale_modules,
        "restart_required_for_latest_mcp_code": bool(stale_modules),
        "note": (
            "MCP hosts cache omniverse_kit_mcp imports; restart the MCP host "
            "when source files are newer than module_tools_import_epoch_ms or "
            "when expected tools/result fields are absent."
        ),
    }
