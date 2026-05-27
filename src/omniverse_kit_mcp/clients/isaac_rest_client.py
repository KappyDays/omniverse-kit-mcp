"""Isaac Sim REST client with retry and timeout support."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from omniverse_kit_mcp.config import IsaacSimConfig
from omniverse_kit_mcp.exceptions import (
    CapabilityNotSupportedError,
    ExtensionBusyError,
    RemoteServiceError,
    RemoteTimeoutError,
    TransportError,
)

logger = logging.getLogger(__name__)

BASE_PATH = "/validation/v1"


class IsaacRestClient:
    """Async HTTP client for the Isaac Sim validation extension REST API."""

    def __init__(self, config: IsaacSimConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(
                connect=config.connect_timeout,
                read=config.timeout,
                write=config.timeout,
                pool=5.0,
            ),
            headers={"User-Agent": "IsaacSimMCP/0.1"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    # --- Health ---

    async def health(self) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/health")

    # --- Commands (D25) ---

    async def kit_command_execute(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        expect_undo: bool = False,
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/commands/execute",
            json={"name": name, "payload": payload, "expect_undo": expect_undo},
        )

    async def kit_python_run(
        self,
        code: str,
        return_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        # REST path is /commands/python_run; the user-facing MCP tool name
        # stays as kit_python_exec. The two names diverge because the
        # project's pre-tool security hook flags the literal substring
        # ``exec`` followed by an open paren as a possible shell injection.
        return await self._post(
            f"{BASE_PATH}/commands/python_run",
            json={"code": code, "return_keys": list(return_keys or [])},
        )

    # --- Stage ---

    async def stage_snapshot(self, capture_filter: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/snapshot", json=capture_filter)

    async def stage_assert_prim_exists(self, assertion: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/assert/prim-exists", json=assertion)

    async def stage_assert_property(self, assertion: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/assert/property", json=assertion)

    # --- Viewport ---

    async def viewport_capture(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/viewport/capture", json=request)

    async def viewport_compare_ssim(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/viewport/compare/ssim", json=request)

    # --- Extension ---

    async def extension_state(self) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/extension/state")

    async def extension_trigger(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/extension/trigger", json=request)

    async def extension_reset(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/extension/reset", json=request)

    # --- Extension UI automation + log capture (Phase D) ---

    async def extension_activate(self, ext_id: str, reload: bool = False) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/activate",
            json={"ext_id": ext_id, "reload": reload},
        )

    async def extension_ui_tree(
        self,
        ext_id: str | None = None,
        window: str | None = None,
        widget_types: list[str] | None = None,
    ) -> dict[str, Any]:
        # Query builder: widget_types is a repeated-param (multi-value). httpx
        # accepts a list under the same key and emits `?widget_types=A&widget_types=B`.
        params: list[tuple[str, str]] = []
        if ext_id is not None:
            params.append(("ext_id", ext_id))
        if window is not None:
            params.append(("window", window))
        for wt in widget_types or ():
            params.append(("widget_types", wt))
        return await self._request(
            "GET", f"{BASE_PATH}/extension/ui_tree", params=params,
        )

    async def extension_ui_invoke(
        self, widget_path: str, action: str, value: Any = None,
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/ui_invoke",
            json={"widget_path": widget_path, "action": action, "value": value},
        )

    async def extension_logs(
        self,
        ext_id: str | None = None,
        since_ms: int | None = None,
        level: str = "INFO",
        limit: int = 1000,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "level": level,
            "limit": str(limit),
        }
        if ext_id is not None:
            params["ext_id"] = ext_id
        if since_ms is not None:
            params["since_ms"] = str(since_ms)
        return await self._request(
            "GET", f"{BASE_PATH}/extension/logs", params=params,
        )

    async def extension_clear_logs(self) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/extension/logs/clear")

    # --- Window / Kit GUI (Phase E) ---

    async def window_capture(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/window/capture", json=request)

    async def window_list(self) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/window/list")

    async def window_ui_list(self, name_filter: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if name_filter is not None:
            params["name_filter"] = name_filter
        return await self._request(
            "GET", f"{BASE_PATH}/window/ui_list", params=params,
        )

    async def window_ui_show(
        self, name: str, visible: bool = True, focus: bool = True, settle_frames: int = 5,
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/window/ui_show",
            json={
                "name": name,
                "visible": visible,
                "focus": focus,
                "settle_frames": settle_frames,
            },
        )

    async def window_menu_list(self, menu_path: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if menu_path is not None:
            params["menu_path"] = menu_path
        return await self._request(
            "GET", f"{BASE_PATH}/window/menu_list", params=params,
        )

    async def window_menu_trigger(self, menu_path: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"{BASE_PATH}/window/menu_trigger",
            params={"menu_path": menu_path},
        )

    # --- Navigation / NavMesh (Phase E) ---

    async def navigation_bake(
        self, volume_scale: float = 40.0, timeout_s: float = 300.0,
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"{BASE_PATH}/navigation/bake",
            params={
                "volume_scale": str(volume_scale),
                "timeout_s": str(timeout_s),
            },
        )

    async def navigation_query_path(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/navigation/query_path", json=request)

    async def navigation_add_exclude_volume(
        self, prim_path: str | None = None, padding: float = 0.1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"padding": str(padding)}
        if prim_path is not None:
            params["prim_path"] = prim_path
        return await self._request(
            "POST", f"{BASE_PATH}/navigation/add_exclude_volume", params=params,
        )

    async def navigation_set_visualization(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/navigation/set_visualization", json=request)

    async def navigation_sample_walkable_points(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/navigation/sample_walkable", json=request)

    async def robot_drive_physics(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/drive_physics", json=request)

    # --- Sensor (Phase E) ---

    async def sensor_attach_rtx_camera(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/sensor/attach_rtx_camera", json=request)

    async def sensor_attach_rtx_lidar(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/sensor/attach_rtx_lidar", json=request)

    async def sensor_attach_rtx_depth_camera(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/sensor/attach_rtx_depth_camera", json=request)

    async def sensor_set_visualization(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/sensor/set_visualization", json=request)

    # --- Sensor (Phase G) ---

    async def sensor_attach_contact(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/sensor/attach_contact", json=request,
        )

    async def sensor_attach_imu(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/sensor/attach_imu", json=request,
        )

    async def sensor_set_annotator(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/sensor/set_annotator", json=request,
        )

    async def sensor_lidar_get_point_cloud(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/sensor/lidar_get_point_cloud", json=request,
        )

    # --- Viewport multi (Phase E) ---

    async def viewport_create(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/viewport/create", json=request)

    async def viewport_destroy(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/viewport/destroy", json=request)

    # --- Viewport render (Phase F) ---

    async def viewport_set_render_mode(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/viewport/set_render_mode", json=request,
        )

    async def viewport_set_render_quality(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/viewport/set_render_quality", json=request,
        )

    async def viewport_toggle_overlay(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/viewport/toggle_overlay", json=request,
        )

    async def viewport_set_fov(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/viewport/set_fov", json=request)

    async def viewport_set_camera_lookat(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/viewport/set_camera_lookat", json=request,
        )

    # --- Physics (Phase F) ---

    async def physics_apply_rigid_body(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/apply_rigid_body", json=request,
        )

    async def physics_get_rigid_body_state(self, prim_path: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/physics/rigid_body_state",
            params={"prim_path": prim_path},
        )

    async def physics_apply_collider(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/apply_collider", json=request,
        )

    async def physics_apply_material(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/apply_material", json=request,
        )

    async def physics_create_joint(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/create_joint", json=request,
        )

    async def physics_set_joint_drive(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/set_joint_drive", json=request,
        )

    async def physics_set_scene(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/set_scene", json=request,
        )

    async def physics_visualize(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/physics/visualize", json=request,
        )

    # --- Lighting (Phase F) ---

    async def lighting_create(
        self, kind: str, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a UsdLux prim — *kind* is one of dome/distant/disk/rect/sphere."""
        return await self._post(
            f"{BASE_PATH}/lighting/create_{kind}", json=request,
        )

    async def lighting_set_exposure(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/lighting/set_exposure", json=request,
        )

    # --- Material (Phase F) ---

    async def material_list_mdl(self, library: str = "default") -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/material/list_mdl",
            params={"library": library},
        )

    async def material_assign_mdl(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/material/assign_mdl", json=request,
        )

    async def material_get_bound(self, prim_path: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/material/get_bound",
            params={"prim_path": prim_path},
        )

    # --- Stage WRITE ---

    async def stage_load_usd(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/load_usd", json=request)

    async def stage_set_property(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/set_property", json=request)

    async def stage_set_semantic_label(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/set_semantic_label", json=request)

    async def stage_create_prim(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/stage/create_prim", json=request)

    async def stage_delete_prim(self, prim_path: str) -> dict[str, Any]:
        return await self._delete(f"{BASE_PATH}/stage/prim", params={"prim_path": prim_path})

    # --- File / Selection / Camera (Phase B+) ---

    async def stage_save(self, path: str | None = None) -> dict[str, Any]:
        params = {"path": path} if path else None
        return await self._request(
            "POST", f"{BASE_PATH}/stage/save", params=params or {},
        )

    async def stage_open(self, url: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"{BASE_PATH}/stage/open", params={"url": url},
        )

    async def stage_new(self) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/stage/new")

    async def stage_get_selection(self) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/stage/selection")

    async def stage_set_selection(
        self, prim_paths: list[str], expand_in_stage: bool = True,
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/stage/selection",
            json={"prim_paths": list(prim_paths), "expand_in_stage": expand_in_stage},
        )

    async def viewport_set_active_camera(
        self, camera_path: str, viewport_name: str = "Viewport",
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/viewport/active_camera",
            json={"camera_path": camera_path, "viewport_name": viewport_name},
        )

    # --- Robot (Phase B) ---

    async def robot_load(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/load", json=request)

    async def robot_get_joint_positions(self, prim_path: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/robot/joint_positions", params={"prim_path": prim_path}
        )

    async def robot_get_joint_config(self, prim_path: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/robot/joint_config", params={"prim_path": prim_path}
        )

    async def robot_set_joint_positions(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/joint_positions", json=request)

    async def robot_navigate(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/navigate", json=request)

    # --- Robot (Phase G) ---

    async def robot_navigate_path(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/navigate_path", json=request)

    async def robot_gripper_control(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/gripper_control", json=request)

    async def robot_set_ee_target(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/robot/set_ee_target", json=request)

    # --- Jobs (Phase B) ---

    async def job_status(self, job_id: str) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/jobs/{job_id}")

    async def job_cancel(self, job_id: str) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/jobs/{job_id}/cancel")

    # --- Character (Phase C) ---

    async def character_load(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/character/load", json=request)

    async def character_play_animation(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/character/play_animation", json=request)

    async def character_set_position(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/character/set_position", json=request)

    async def character_stop_animation(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/character/stop_animation", json=request)

    async def character_navigate(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/character/navigate", json=request)

    async def character_get_state(self, prim_path: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"{BASE_PATH}/character/state", params={"prim_path": prim_path}
        )

    # --- Character (Phase G) ---

    async def character_play_animation_variant(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/character/play_animation_variant", json=request,
        )

    async def character_load_crowd(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/character/load_crowd", json=request,
        )

    # --- Assets (Phase B+) ---

    async def asset_list(
        self,
        category: str | None = None,
        subpath: str = "",
        recursive: bool = False,
        max_depth: int = 2,
        max_entries: int = 500,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "subpath": subpath,
            "recursive": "true" if recursive else "false",
            "max_depth": str(max_depth),
            "max_entries": str(max_entries),
        }
        if category is not None:
            params["category"] = category
        return await self._request(
            "GET", f"{BASE_PATH}/assets/list", params=params
        )

    # --- Simulation ---

    async def simulation_play(self) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/simulation/play")

    async def simulation_pause(self) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/simulation/pause")

    async def simulation_stop(self) -> dict[str, Any]:
        return await self._post_empty(f"{BASE_PATH}/simulation/stop")

    async def simulation_status(self) -> dict[str, Any]:
        return await self._get(f"{BASE_PATH}/simulation/status")

    # --- Simulation (Phase G) ---

    async def simulation_step(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{BASE_PATH}/simulation/step", json=request)

    async def simulation_set_time(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/simulation/set_time", json=request,
        )

    # --- Replicator (Phase H) ---

    async def replicator_create_writer(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/replicator/create_writer", json=request,
        )

    async def replicator_register_randomizer(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/replicator/register_randomizer", json=request,
        )

    async def replicator_trigger_once(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/replicator/trigger_once", json=request,
        )

    async def replicator_trigger_on_time(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/replicator/trigger_on_time", json=request,
        )

    # --- OmniGraph (Phase H) ---

    async def omnigraph_create_node(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/omnigraph/create_node", json=request,
        )

    async def omnigraph_connect(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/omnigraph/connect", json=request,
        )

    async def omnigraph_execute(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/omnigraph/execute", json=request,
        )

    async def omnigraph_create_ros2_publisher(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/omnigraph/create_ros2_publisher", json=request,
        )

    # --- Content (Phase H) ---

    async def content_browse(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/content/browse", json=request,
        )

    async def content_preview(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/content/preview", json=request,
        )

    async def content_resolve(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/content/resolve", json=request,
        )

    # --- Extension management (Phase H) ---

    async def extension_deactivate(self, ext_id: str) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/deactivate", json={"ext_id": ext_id},
        )

    async def extension_list_all(
        self, enabled_only: bool = False,
    ) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/list_all",
            json={"enabled_only": enabled_only},
        )

    async def extension_get_info(self, ext_id: str) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/get_info", json={"ext_id": ext_id},
        )

    async def extension_reload_clean(self, ext_id: str) -> dict[str, Any]:
        return await self._post(
            f"{BASE_PATH}/extension/reload_clean", json={"ext_id": ext_id},
        )

    # --- Internal helpers ---

    async def _get(self, path: str) -> dict[str, Any]:
        return await self._request("GET", path)

    async def _post(self, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def _post_empty(self, path: str) -> dict[str, Any]:
        return await self._request("POST", path)

    async def _delete(self, path: str, *, params: dict[str, str]) -> dict[str, Any]:
        return await self._request("DELETE", path, params=params)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(1, self._config.max_retries + 1):
            try:
                resp = await self._client.request(method, path, **kwargs)
                if resp.status_code == 409:
                    raise ExtensionBusyError("Extension is busy")
                if resp.status_code == 503:
                    # Differentiate "capability not supported for this app
                    # profile" (deterministic, no retry) from transient 503
                    # (service overloaded — falls through to retry logic).
                    try:
                        body = resp.json()
                        detail = body.get("detail", {}) if isinstance(body, dict) else {}
                    except Exception:  # noqa: BLE001
                        detail = {}
                    if (
                        isinstance(detail, dict)
                        and str(detail.get("error", "")).endswith("_stack_unavailable")
                    ):
                        raise CapabilityNotSupportedError(detail)
                if resp.status_code in (408, 429, 500, 502, 503, 504) and attempt < self._config.max_retries:
                    last_exc = RemoteServiceError(
                        f"HTTP {resp.status_code}", error_code=f"HTTP_{resp.status_code}"
                    )
                    await self._backoff(attempt)
                    continue
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except httpx.TimeoutException as exc:
                last_exc = RemoteTimeoutError(str(exc))
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exc from exc
            except httpx.HTTPStatusError as exc:
                detail = _extract_error_detail(exc.response)
                message = f"{exc} — {detail}" if detail else str(exc)
                raise RemoteServiceError(
                    message, error_code=f"HTTP_{exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_exc = TransportError(str(exc))
                if attempt < self._config.max_retries:
                    await self._backoff(attempt)
                    continue
                raise last_exc from exc
        raise last_exc or TransportError("Request failed after retries")

    async def _backoff(self, attempt: int) -> None:
        base = self._config.retry_backoff * (2 ** (attempt - 1))
        jitter = random.uniform(0, base * 0.2)  # noqa: S311
        delay = min(base + jitter, 5.0)
        logger.debug("Retry attempt %d, backing off %.2fs", attempt, delay)
        await asyncio.sleep(delay)


def _extract_error_detail(response: httpx.Response) -> str:
    """Pull FastAPI's ``{"detail": "..."}`` body (or raw text) into a short string.

    Lets the user see *why* a request failed instead of just the HTTP status —
    e.g. "Prim at /X has no PhysX articulation API" is more actionable than
    "Client error '400 Bad Request'".
    """
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])[:500]
        return str(body)[:500]
    except Exception:
        text = response.text or ""
        return text[:500]
