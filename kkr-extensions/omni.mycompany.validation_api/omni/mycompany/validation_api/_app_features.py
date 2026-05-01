"""Runtime feature detection — which Kit extensions are live in this app.

Called from rest_router.py route handlers to decide whether to serve the
request (Isaac-specific capabilities) or return HTTP 503 (the extension
that implements this capability is not enabled for the current Kit app).

This is evaluated lazily (per-request) because extensions can be toggled
at runtime via extension_activate / extension_deactivate. Caching would
race with legitimate toggle flows.
"""

from __future__ import annotations

from fastapi import HTTPException


_ROBOT_EXTS = ("isaacsim.robot.manipulators", "isaacsim.core.nodes")
_CHARACTER_EXTS = ("omni.anim.graph.core", "isaacsim.replicator.agent.core")
_NAVIGATION_EXTS = ("omni.anim.navigation.core",)
_SENSOR_RTX_EXTS = ("isaacsim.sensors.rtx",)
_SENSOR_PHYSICS_EXTS = ("isaacsim.sensors.physics",)
_REPLICATOR_EXTS = ("omni.replicator.core",)
_OMNIGRAPH_ROS2_EXTS = ("isaacsim.ros2.bridge",)


def _is_ext_enabled(ext_id_prefix: str) -> bool:
    """True if any enabled extension's id starts with ext_id_prefix.

    Prefix match handles versioned ext ids (omni.anim.graph.core-1.2.3 matches
    prefix "omni.anim.graph.core").
    """
    try:
        import omni.kit.app
        manager = omni.kit.app.get_app().get_extension_manager()
        for ext in manager.get_extensions():
            ext_id = ext.get("id") if isinstance(ext, dict) else ext.id
            if not ext_id:
                continue
            if ext_id.startswith(ext_id_prefix) and (
                (isinstance(ext, dict) and ext.get("enabled"))
                or (not isinstance(ext, dict) and manager.is_extension_enabled(ext_id))
            ):
                return True
    except Exception:  # noqa: BLE001 — Kit not ready or API drift → treat as missing
        pass
    return False


def _any_enabled(prefixes: tuple[str, ...]) -> bool:
    return any(_is_ext_enabled(p) for p in prefixes)


def require_robot_stack() -> None:
    if not _any_enabled(_ROBOT_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "robot_stack_unavailable",
                "message": (
                    "Robot operations require isaacsim.robot.manipulators "
                    "which is not enabled in this Kit app. This route is "
                    "served only by the isaac-sim app profile."
                ),
                "required_extensions": list(_ROBOT_EXTS),
            },
        )


def require_character_stack() -> None:
    if not _any_enabled(_CHARACTER_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "character_stack_unavailable",
                "message": (
                    "Character operations require omni.anim.graph.core / "
                    "isaacsim.replicator.agent.core (Isaac-specific)."
                ),
                "required_extensions": list(_CHARACTER_EXTS),
            },
        )


def require_navigation_stack() -> None:
    if not _any_enabled(_NAVIGATION_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "navigation_stack_unavailable",
                "message": (
                    "NavMesh operations require omni.anim.navigation.core "
                    "(Isaac-specific)."
                ),
                "required_extensions": list(_NAVIGATION_EXTS),
            },
        )


def require_sensor_rtx_stack() -> None:
    if not _any_enabled(_SENSOR_RTX_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "sensor_rtx_stack_unavailable",
                "message": "RTX sensor operations require isaacsim.sensors.rtx.",
                "required_extensions": list(_SENSOR_RTX_EXTS),
            },
        )


def require_sensor_physics_stack() -> None:
    if not _any_enabled(_SENSOR_PHYSICS_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "sensor_physics_stack_unavailable",
                "message": (
                    "Contact / IMU sensors require isaacsim.sensors.physics "
                    "(Isaac-specific)."
                ),
                "required_extensions": list(_SENSOR_PHYSICS_EXTS),
            },
        )


def require_replicator_stack() -> None:
    if not _any_enabled(_REPLICATOR_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "replicator_stack_unavailable",
                "message": "Replicator operations require omni.replicator.core.",
                "required_extensions": list(_REPLICATOR_EXTS),
            },
        )


def require_ros2_bridge() -> None:
    if not _any_enabled(_OMNIGRAPH_ROS2_EXTS):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "ros2_bridge_unavailable",
                "message": "ROS2 publisher requires isaacsim.ros2.bridge.",
                "required_extensions": list(_OMNIGRAPH_ROS2_EXTS),
            },
        )
