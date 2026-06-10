"""KitAppProfile — per-app launch config + supported tool surface.

Single source of truth for the differences between Kit-based apps this MCP
server can drive (Isaac Sim, USD Composer). Adding a new app = adding one
`KitAppProfile` literal below + registering it in `_PROFILES` dict. No other
code change should be needed until you want app-specific behavior beyond
what the profile already exposes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class KitAppProfile:
    """Immutable profile describing how to launch and which tools apply.

    Fields:
      name: Stable identifier used in env var ISAAC_MCP_APP_PROFILE and as
            key in MCP server names (isaacsim-mcp-N vs usdcomposer-mcp-N).
      kit_exe: Absolute path to kit.exe binary.
      kit_file: Absolute path to the .kit launch file.
      default_ext_port: Base port for instance_id=1. instance_id=N binds to
                       default_ext_port + (N - 1). Isaac starts at 8111,
                       USD Composer at 8114, giving each profile a
                       contiguous 3-port window.
      ros_env_required: If true, ProcessModule._prepare_launch_env adds
                        ROS_DISTRO / RMW_IMPLEMENTATION / PATH entries.
                        Isaac needs these (ROS2 bridge). USD Composer does not.
      extra_ext_ids: Kit extensions to --enable in addition to the bridge
                    (omni.mycompany.validation_api).
      supported_module_groups: Tool groups this app supports. "common" is
                              always present. Isaac-specific groups (robot,
                              character, navigation, sensor, replicator) are
                              omitted for usd-composer → REST routes return
                              HTTP 503 when called against this profile.
    """
    name: str
    kit_exe: str
    kit_file: str
    default_ext_port: int
    ros_env_required: bool
    extra_ext_ids: tuple[str, ...]
    supported_module_groups: frozenset[str]


ISAAC_SIM_PROFILE = KitAppProfile(
    name="isaac-sim",
    kit_exe="C:/IsaacSim/kit/kit.exe",
    kit_file="C:/IsaacSim/apps/isaacsim.exp.full.kit",
    default_ext_port=8111,
    ros_env_required=True,
    extra_ext_ids=(
        "omni.anim.graph.bundle",
        "omni.anim.navigation.bundle",
        "isaacsim.replicator.agent.core",
        "omni.kit.ui_test",
    ),
    supported_module_groups=frozenset({
        "common",
        "robot",
        "character",
        "navigation",
        "sensor",
        "replicator",
        "asset",
        "job",
        "omnigraph_ros2",
    }),
)


USD_COMPOSER_PROFILE = KitAppProfile(
    name="usd-composer",
    kit_exe="C:/USDComposer/kit/kit.exe",
    kit_file="C:/USDComposer/apps/kkr_usd_composer.kit",
    default_ext_port=8114,
    ros_env_required=False,
    extra_ext_ids=(),
    supported_module_groups=frozenset({
        "common",
    }),
)


_PROFILES: dict[str, KitAppProfile] = {
    ISAAC_SIM_PROFILE.name: ISAAC_SIM_PROFILE,
    USD_COMPOSER_PROFILE.name: USD_COMPOSER_PROFILE,
}


def get_profile(name: str) -> KitAppProfile:
    """Resolve a profile by name. Raises ValueError for unknown names."""
    try:
        return _PROFILES[name]
    except KeyError as exc:
        known = ", ".join(sorted(_PROFILES))
        raise ValueError(
            f"Unknown app profile {name!r}. Known profiles: {known}"
        ) from exc


def list_profile_names() -> tuple[str, ...]:
    """Stable-ordered tuple of profile names — used by setup scripts to
    enumerate .mcp.json entries."""
    return tuple(sorted(_PROFILES))
