"""Metadata and selection helpers for the MCP tool surface."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

PROFILE_FULL = "full"
PROFILE_CORE = "core"
PROFILE_APP = "app"
PROFILE_CUSTOM = "custom"
VALID_TOOL_PROFILES = frozenset({
    PROFILE_FULL,
    PROFILE_CORE,
    PROFILE_APP,
    PROFILE_CUSTOM,
})

APP_ISAAC_SIM = "isaac-sim"
APP_USD_COMPOSER = "usd-composer"
APP_ALL = frozenset({APP_ISAAC_SIM, APP_USD_COMPOSER})
APP_ISAAC_ONLY = frozenset({APP_ISAAC_SIM})

ALWAYS_INCLUDED_TOOLS = frozenset({"mcp_runtime_info"})


@dataclass(slots=True, frozen=True)
class ToolMeta:
    """Classification for one public MCP tool name."""

    name: str
    group: str
    domain: str
    default_profiles: frozenset[str]
    app_profiles: frozenset[str]
    workflow_tags: frozenset[str]
    risk_level: str = "normal"


@dataclass(slots=True, frozen=True)
class ToolGroup:
    """Definition used to expand repeated metadata into ToolMeta rows."""

    title: str
    domain: str
    tools: tuple[str, ...]
    core_tools: frozenset[str] = frozenset()
    app_profiles: frozenset[str] = APP_ALL
    workflow_tags: frozenset[str] = frozenset()
    risk_level: str = "normal"


@dataclass(slots=True, frozen=True)
class ToolSelection:
    """Resolved profile selection for one MCP server instance."""

    profile: str
    app_profile: str
    included_tools: frozenset[str]
    omitted_tools: frozenset[str]
    include_tokens: frozenset[str]
    exclude_tokens: frozenset[str]

    def includes(self, tool_name: str) -> bool:
        return tool_name in self.included_tools

    @property
    def registered_tool_count(self) -> int:
        return len(self.included_tools)

    @property
    def omitted_tool_count(self) -> int:
        return len(self.omitted_tools)

    def included_group_counts(self) -> dict[str, int]:
        return _group_counts(self.included_tools)

    def omitted_group_counts(self) -> dict[str, int]:
        return _group_counts(self.omitted_tools)

    def as_runtime_payload(self) -> dict[str, Any]:
        return {
            "tool_profile": self.profile,
            "app_profile": self.app_profile,
            "registered_tool_count": self.registered_tool_count,
            "omitted_tool_count": self.omitted_tool_count,
            "included_groups": self.included_group_counts(),
            "omitted_groups": self.omitted_group_counts(),
            "omitted_tools": sorted(self.omitted_tools),
            "custom_include_tokens": sorted(self.include_tokens),
            "custom_exclude_tokens": sorted(self.exclude_tokens),
        }


TOOL_GROUPS: tuple[ToolGroup, ...] = (
    ToolGroup(
        title="Process - MCP / Kit app lifecycle",
        domain="process",
        tools=(
            "mcp_runtime_info",
            "kit_app_start",
            "kit_app_stop",
            "kit_app_restart",
            "process_list_kit_instances",
        ),
        core_tools=frozenset({
            "mcp_runtime_info",
            "kit_app_start",
            "kit_app_stop",
            "process_list_kit_instances",
        }),
        workflow_tags=frozenset({"startup", "diagnostics", "lifecycle"}),
    ),
    ToolGroup(
        title="Stage - READ / ASSERT",
        domain="stage",
        tools=(
            "stage_capture_snapshot",
            "stage_diff_snapshots",
            "stage_compute_world_bbox",
            "stage_visual_alignment_report",
            "stage_placement_validation_report",
            "stage_assert_prim_exists",
            "stage_assert_property",
        ),
        core_tools=frozenset({
            "stage_capture_snapshot",
            "stage_diff_snapshots",
            "stage_compute_world_bbox",
            "stage_visual_alignment_report",
            "stage_placement_validation_report",
            "stage_assert_prim_exists",
            "stage_assert_property",
        }),
        workflow_tags=frozenset({"stage", "readback", "assert"}),
    ),
    ToolGroup(
        title="Stage - WRITE / file / selection",
        domain="stage",
        tools=(
            "stage_load_usd",
            "stage_set_property",
            "stage_set_semantic_label",
            "stage_create_prim",
            "stage_delete_prim",
            "stage_save",
            "stage_open",
            "stage_new",
            "stage_get_selection",
            "stage_set_selection",
        ),
        core_tools=frozenset({
            "stage_load_usd",
            "stage_set_property",
            "stage_set_semantic_label",
            "stage_create_prim",
            "stage_delete_prim",
            "stage_open",
            "stage_new",
            "stage_get_selection",
            "stage_set_selection",
        }),
        workflow_tags=frozenset({"stage", "authoring", "usd"}),
    ),
    ToolGroup(
        title="Simulation - timeline",
        domain="simulation",
        tools=(
            "simulation_play",
            "simulation_pause",
            "simulation_stop",
            "simulation_get_status",
            "simulation_step",
            "simulation_step_observe",
            "simulation_wait_until",
            "simulation_set_time",
        ),
        core_tools=frozenset({
            "simulation_play",
            "simulation_pause",
            "simulation_stop",
            "simulation_get_status",
            "simulation_step",
        }),
        workflow_tags=frozenset({"simulation", "timeline"}),
    ),
    ToolGroup(
        title="Viewport - capture / camera / render",
        domain="viewport",
        tools=(
            "viewport_capture",
            "viewport_compare_ssim",
            "viewport_set_active_camera",
            "viewport_set_camera_lookat",
            "viewport_focus_prim",
            "viewport_create",
            "viewport_destroy",
            "viewport_set_render_mode",
            "viewport_set_render_quality",
            "viewport_toggle_overlay",
            "viewport_set_fov",
            "viewport_project_points",
            "viewport_frame_prims",
            "viewport_capture_assert",
        ),
        core_tools=frozenset({
            "viewport_capture",
            "viewport_compare_ssim",
            "viewport_set_active_camera",
            "viewport_set_camera_lookat",
            "viewport_focus_prim",
            "viewport_set_render_mode",
            "viewport_set_render_quality",
            "viewport_project_points",
            "viewport_frame_prims",
            "viewport_capture_assert",
        }),
        workflow_tags=frozenset({"viewport", "visual-validation", "camera"}),
    ),
    ToolGroup(
        title="Window - Kit GUI / menus / omni.ui",
        domain="window",
        tools=(
            "window_capture",
            "window_capture_sequence",
            "window_list",
            "window_ui_list",
            "window_ui_show",
            "window_menu_list",
            "window_menu_trigger",
        ),
        core_tools=frozenset({
            "window_capture",
            "window_list",
            "window_menu_list",
            "window_menu_trigger",
        }),
        workflow_tags=frozenset({"gui", "window", "menus"}),
    ),
    ToolGroup(
        title="Extension - lifecycle / UI automation / logs / catalog",
        domain="extension",
        tools=(
            "extension_trigger",
            "extension_get_state",
            "extension_activate",
            "extension_reload",
            "extension_get_ui_tree",
            "extension_ui_invoke",
            "extension_ui_run_and_wait",
            "extension_capture_logs",
            "extension_clear_logs",
            "extension_deactivate",
            "extension_list_all",
            "extension_get_info",
            "extension_search",
        ),
        core_tools=frozenset({
            "extension_get_state",
            "extension_activate",
            "extension_reload",
            "extension_capture_logs",
            "extension_clear_logs",
            "extension_search",
        }),
        workflow_tags=frozenset({"extension", "logs", "diagnostics"}),
    ),
    ToolGroup(
        title="Lakehouse - query-only",
        domain="lakehouse",
        tools=("lakehouse_query",),
        core_tools=frozenset({"lakehouse_query"}),
        workflow_tags=frozenset({"data", "query"}),
    ),
    ToolGroup(
        title="Asset - catalog browsing / official assets",
        domain="asset",
        tools=(
            "asset_list",
            "asset_search",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_get",
            "official_asset_sync_status",
            "official_asset_verify",
            "external_asset_search",
            "external_asset_download",
            "external_asset_convert",
        ),
        core_tools=frozenset({
            "asset_list",
            "asset_search",
            "official_asset_search",
            "official_asset_resolve",
            "official_asset_get",
            "official_asset_sync_status",
            "official_asset_verify",
        }),
        workflow_tags=frozenset({"assets", "official-assets", "discovery"}),
    ),
    ToolGroup(
        title="Content - browser / preview / inspect / resolve",
        domain="content",
        tools=(
            "content_browse",
            "content_preview",
            "content_inspect",
            "content_resolve",
        ),
        core_tools=frozenset({
            "content_browse",
            "content_preview",
            "content_inspect",
            "content_resolve",
        }),
        workflow_tags=frozenset({"content", "asset-browser"}),
    ),
    ToolGroup(
        title="Navigation - NavMesh",
        domain="navigation",
        tools=(
            "navigation_bake",
            "navigation_query_path",
            "navigation_add_exclude_volume",
            "navigation_set_visualization",
            "navigation_sample_walkable_points",
        ),
        core_tools=frozenset({
            "navigation_bake",
            "navigation_query_path",
            "navigation_add_exclude_volume",
        }),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"navmesh", "pathing"}),
    ),
    ToolGroup(
        title="Robot - articulation / navigation / manipulation",
        domain="robot",
        tools=(
            "robot_load",
            "robot_list_arm_profiles",
            "robot_probe_arm_profile",
            "robot_probe_arm_profiles",
            "robot_get_joint_positions",
            "robot_get_joint_config",
            "robot_get_joint_config_static",
            "robot_set_joint_positions",
            "robot_navigate_to",
            "robot_navigate_path",
            "robot_gripper_control",
            "robot_set_ee_target",
            "robot_get_ee_pose",
            "robot_run_franka_pick_place",
            "robot_install_franka_pick_place_playback_demo",
            "robot_install_pick_place_playback_demo",
            "robot_reset_pick_place_demo",
            "robot_get_pick_place_demo_status",
            "robot_drive_physics",
        ),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"robot", "manipulation", "navigation"}),
    ),
    ToolGroup(
        title="Job - async polling / cancel",
        domain="job",
        tools=("job_status", "job_cancel"),
        core_tools=frozenset({"job_status"}),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"async", "jobs"}),
    ),
    ToolGroup(
        title="Character - animation / crowd / navigation",
        domain="character",
        tools=(
            "character_load",
            "character_play_animation",
            "character_set_position",
            "character_stop_animation",
            "character_navigate_to",
            "character_get_state",
            "character_play_animation_variant",
            "character_load_crowd",
        ),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"character", "animation", "navigation"}),
    ),
    ToolGroup(
        title="Sensor - RTX / contact / IMU / annotators",
        domain="sensor",
        tools=(
            "sensor_attach_rtx_camera",
            "sensor_attach_rtx_lidar",
            "sensor_lidar_get_point_cloud",
            "sensor_attach_rtx_depth_camera",
            "sensor_set_visualization",
            "sensor_attach_contact",
            "sensor_attach_imu",
            "sensor_set_annotator",
        ),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"sensors", "sdg"}),
    ),
    ToolGroup(
        title="Physics - bodies / colliders / joints / scene",
        domain="physics",
        tools=(
            "physics_apply_rigid_body",
            "physics_get_rigid_body_state",
            "physics_apply_collider",
            "physics_apply_material",
            "physics_create_joint",
            "physics_set_joint_drive",
            "physics_set_scene",
            "physics_visualize",
        ),
        core_tools=frozenset({
            "physics_apply_rigid_body",
            "physics_get_rigid_body_state",
            "physics_apply_collider",
            "physics_apply_material",
            "physics_set_scene",
        }),
        workflow_tags=frozenset({"physics", "authoring"}),
    ),
    ToolGroup(
        title="Lighting - UsdLux / exposure",
        domain="lighting",
        tools=(
            "lighting_create_dome",
            "lighting_create_distant",
            "lighting_create_disk",
            "lighting_create_rect",
            "lighting_create_sphere",
            "lighting_set_exposure",
        ),
        core_tools=frozenset({
            "lighting_create_dome",
            "lighting_create_distant",
            "lighting_create_disk",
            "lighting_create_rect",
            "lighting_create_sphere",
            "lighting_set_exposure",
        }),
        workflow_tags=frozenset({"lighting", "authoring"}),
    ),
    ToolGroup(
        title="Material - MDL list / assign / bound",
        domain="material",
        tools=(
            "material_list_mdl",
            "material_assign_mdl",
            "material_get_bound",
        ),
        core_tools=frozenset({
            "material_list_mdl",
            "material_assign_mdl",
            "material_get_bound",
        }),
        workflow_tags=frozenset({"materials", "authoring"}),
    ),
    ToolGroup(
        title="Replicator - writers / randomizers / triggers",
        domain="replicator",
        tools=(
            "replicator_create_writer",
            "replicator_register_randomizer",
            "replicator_trigger_once",
            "replicator_trigger_on_time",
        ),
        app_profiles=APP_ISAAC_ONLY,
        workflow_tags=frozenset({"replicator", "sdg"}),
    ),
    ToolGroup(
        title="OmniGraph - nodes / execution / ROS2",
        domain="omnigraph",
        tools=(
            "omnigraph_create_node",
            "omnigraph_connect",
            "omnigraph_execute",
            "omnigraph_create_ros2_publisher",
            "omnigraph_create_script_controller",
        ),
        app_profiles=APP_ALL,
        workflow_tags=frozenset({"omnigraph", "automation"}),
    ),
    ToolGroup(
        title="Scenario - YAML validation runner",
        domain="scenario",
        tools=(
            "scenario_validate",
            "scenario_plan",
            "scenario_last_report",
        ),
        core_tools=frozenset({
            "scenario_validate",
            "scenario_plan",
            "scenario_last_report",
        }),
        workflow_tags=frozenset({"scenario", "validation"}),
    ),
    ToolGroup(
        title="Kit commands - command registry / Python runner",
        domain="kit_command",
        tools=(
            "kit_command_execute",
            "kit_python_run",
        ),
        core_tools=frozenset({"kit_command_execute"}),
        workflow_tags=frozenset({"kit-command", "diagnostics"}),
        risk_level="elevated",
    ),
)

_APP_EXCLUDED_TOOLS = frozenset({
    "external_asset_search",
    "external_asset_download",
    "external_asset_convert",
    "kit_python_run",
})

_APP_PROFILE_OVERRIDES: dict[str, frozenset[str]] = {
    "omnigraph_create_ros2_publisher": APP_ISAAC_ONLY,
}

_CORE_EXCLUDED_TOOLS = frozenset({
    "external_asset_search",
    "external_asset_download",
    "external_asset_convert",
    "kit_python_run",
})


def _build_tool_metadata() -> dict[str, ToolMeta]:
    metadata: dict[str, ToolMeta] = {}
    for group in TOOL_GROUPS:
        for name in group.tools:
            profiles = {PROFILE_FULL}
            if name in group.core_tools and name not in _CORE_EXCLUDED_TOOLS:
                profiles.add(PROFILE_CORE)
            if name not in _APP_EXCLUDED_TOOLS and group.app_profiles:
                profiles.add(PROFILE_APP)

            app_profiles = _APP_PROFILE_OVERRIDES.get(name, group.app_profiles)
            metadata[name] = ToolMeta(
                name=name,
                group=group.title,
                domain=group.domain,
                default_profiles=frozenset(profiles),
                app_profiles=app_profiles,
                workflow_tags=group.workflow_tags,
                risk_level=group.risk_level,
            )
    return metadata


TOOL_METADATA: dict[str, ToolMeta] = _build_tool_metadata()
CATALOG_GROUPS: tuple[str, ...] = tuple(group.title for group in TOOL_GROUPS)


def parse_tool_csv(value: str | Iterable[str] | None) -> frozenset[str]:
    """Parse comma-separated tool/group tokens from env-friendly values."""
    if value is None:
        return frozenset()
    if isinstance(value, str):
        raw = value.split(",")
    else:
        raw = value
    return frozenset(token.strip() for token in raw if token and token.strip())


def normalize_tool_profile(value: str) -> str:
    profile = value.strip().lower()
    if profile not in VALID_TOOL_PROFILES:
        known = ", ".join(sorted(VALID_TOOL_PROFILES))
        raise ValueError(f"Unknown MCP tool profile {value!r}. Known profiles: {known}")
    return profile


def build_tool_selection(
    *,
    profile: str = PROFILE_FULL,
    app_profile: str = APP_ISAAC_SIM,
    include: str | Iterable[str] | None = None,
    exclude: str | Iterable[str] | None = None,
) -> ToolSelection:
    """Resolve the names that should be registered for one server instance."""
    normalized_profile = normalize_tool_profile(profile)
    include_tokens = parse_tool_csv(include)
    exclude_tokens = parse_tool_csv(exclude)

    if normalized_profile == PROFILE_FULL:
        selected = set(TOOL_METADATA)
    elif normalized_profile == PROFILE_CORE:
        selected = {
            name
            for name, meta in TOOL_METADATA.items()
            if PROFILE_CORE in meta.default_profiles
        }
    elif normalized_profile == PROFILE_APP:
        selected = {
            name
            for name, meta in TOOL_METADATA.items()
            if PROFILE_APP in meta.default_profiles and app_profile in meta.app_profiles
        }
    else:
        selected = {
            name
            for name, meta in TOOL_METADATA.items()
            if PROFILE_CORE in meta.default_profiles
        }
        selected.update(_resolve_tokens(include_tokens))
        selected.difference_update(_resolve_tokens(exclude_tokens))

    selected.update(ALWAYS_INCLUDED_TOOLS)
    omitted = set(TOOL_METADATA) - selected
    return ToolSelection(
        profile=normalized_profile,
        app_profile=app_profile,
        included_tools=frozenset(selected),
        omitted_tools=frozenset(omitted),
        include_tokens=include_tokens,
        exclude_tokens=exclude_tokens,
    )


def selected_tool_decorator(
    mcp: FastMCP,
    selection: ToolSelection,
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """Return an @tool decorator that skips functions outside the selection."""

    def tool(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
            if selection.includes(fn.__name__):
                return mcp.tool(*args, **kwargs)(fn)
            return fn

        return decorate

    return tool


def tool_catalog_group(name: str) -> str:
    meta = TOOL_METADATA.get(name)
    return meta.group if meta is not None else "Unclassified"


def validate_tool_metadata(expected_tool_names: Iterable[str]) -> None:
    expected = frozenset(expected_tool_names)
    actual = frozenset(TOOL_METADATA)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ValueError(
            "Tool metadata drift: "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )


def _group_counts(tool_names: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in sorted(tool_names):
        group = tool_catalog_group(name)
        counts[group] = counts.get(group, 0) + 1
    return counts


def _resolve_tokens(tokens: Iterable[str]) -> set[str]:
    resolved: set[str] = set()
    unknown: list[str] = []
    for token in tokens:
        matches = _tools_for_token(token)
        if matches:
            resolved.update(matches)
        else:
            unknown.append(token)
    if unknown:
        known_groups = ", ".join(sorted({meta.domain for meta in TOOL_METADATA.values()}))
        raise ValueError(
            "Unknown MCP custom tool token(s): "
            f"{', '.join(sorted(unknown))}. Use tool names or group domains: {known_groups}"
        )
    return resolved


def _tools_for_token(token: str) -> set[str]:
    normalized = token.strip().lower()
    if not normalized:
        return set()
    if normalized in TOOL_METADATA:
        return {normalized}
    return {
        name
        for name, meta in TOOL_METADATA.items()
        if meta.domain.lower() == normalized
        or _normalize_label(meta.group) == _normalize_label(normalized)
        or normalized in {tag.lower() for tag in meta.workflow_tags}
    }


def _normalize_label(value: str) -> str:
    return " ".join(value.replace("-", " ").replace("/", " ").lower().split())
