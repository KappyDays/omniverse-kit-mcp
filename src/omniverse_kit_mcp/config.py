"""Typed configuration via pydantic-settings.

CRITICAL (2026-04-23): each sub-config carries its own `env_file=".env"`.
pydantic-settings v2 does NOT propagate the parent `AppConfig`'s env_file to
sub-models created via `default_factory` — each sub-`BaseSettings` instance
loads its own sources independently. Without `env_file` here, every
`ISAAC_SIM_* / LAKEHOUSE_* / MCP_SERVER_* / SCENARIO_*` value in `.env` was
silently ignored (only OS env vars were honored). Symptom: `.env` set
`ISAAC_SIM_STARTUP_TIMEOUT=600` but the running server kept using the
hardcoded 240s default.

Multi-app layer (2026-04-25): ISAAC_MCP_INSTANCE_ID + ISAAC_MCP_APP_PROFILE
drive port / kit.exe / ROS env derivation. See `types/profile.py`.
"""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from omniverse_kit_mcp.types.profile import KitAppProfile, get_profile


class IsaacSimConfig(BaseSettings):
    """HTTP client config for the Kit REST bridge.

    `base_url` is a derived value by default — AppConfig's validator fills it
    from the profile's ext_port when unset. Explicit ISAAC_SIM_BASE_URL env
    var overrides derivation (backward compat with single-instance users).
    """
    model_config = SettingsConfigDict(env_prefix="ISAAC_SIM_", env_file=".env", extra="ignore")

    base_url: str | None = None
    timeout: float = 30.0
    connect_timeout: float = 5.0
    max_retries: int = 3
    retry_backoff: float = 0.5


class LakehouseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LAKEHOUSE_", env_file=".env", extra="ignore")

    base_url: str = "http://localhost:9000"
    timeout: float = 30.0
    connect_timeout: float = 5.0
    max_retries: int = 3


class MCPServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_SERVER_", env_file=".env", extra="ignore")

    name: str = "isaacsim-validation-mcp"
    host: str = "0.0.0.0"
    port: int = 8080


class IsaacSimProcessConfig(BaseSettings):
    """Kit app launch config — profile-aware.

    The historic name is retained for backward compatibility but this now
    drives *any* Kit app (isaac-sim, usd-composer). The `app_profile` field
    is resolved post-validation from the `ISAAC_MCP_APP_PROFILE` env var
    and determines kit_exe / kit_file / ROS env / ext_port base.

    Legacy env vars (ISAAC_SIM_KIT_EXE, ISAAC_SIM_KIT_FILE) still override
    the profile's defaults — useful for operators who relocate their Isaac
    Sim install.
    """
    model_config = SettingsConfigDict(env_prefix="ISAAC_SIM_", env_file=".env", extra="ignore")

    kit_exe: str | None = None
    kit_file: str | None = None

    ext_folder: str = "C:/Users/<you>/workspace/omniverse-kit-mcp/kkr-extensions"
    ext_id: str = "omni.mycompany.validation_api"
    # 120 s = "fail-fast diagnostic window" (user-confirmed 2026-04-23). Cold
    # boot can legitimately take 5-10 min for GPU shader cache rebuild — that
    # path is NOT a failure of this timeout: when the timer expires the runtime
    # checks whether kit.exe is still alive. Alive → returns
    # `{status: "still_loading", process_alive: true}` so the caller can decide
    # to keep polling (call kit_app_start again — second call detects the
    # running process and resumes health polling without re-spawning). Dead →
    # returns `{status: "crashed", log_tail: [...]}` for immediate triage.
    startup_timeout: float = 120.0

    instance_id: int = Field(default=1, ge=1, le=2, alias="ISAAC_MCP_INSTANCE_ID")
    app_profile_name: str = Field(default="isaac-sim", alias="ISAAC_MCP_APP_PROFILE")
    ext_base_port: int | None = Field(default=None, ge=1024, le=65535)

    health_url: str | None = None

    extra_ext_ids: tuple[str, ...] = ()

    # Out-of-tree extension folders (e.g. office_mcp/exts) registered via an
    # additional --ext-folder each. JSON array only (pydantic-settings v2):
    # ISAAC_SIM_EXTRA_EXT_FOLDERS='["C:/Users/<you>/workspace/omniverse-kit-mcp/office_mcp/exts"]'
    extra_ext_folders: tuple[str, ...] = ()

    app_profile: KitAppProfile = Field(default_factory=lambda: get_profile("isaac-sim"))

    @property
    def ext_port(self) -> int:
        """Final Extension REST port for this (profile, instance) combo."""
        base = self.ext_base_port if self.ext_base_port is not None else self.app_profile.default_ext_port
        return base + (self.instance_id - 1)

    @property
    def effective_kit_exe(self) -> str:
        """kit_exe override (env) > profile default."""
        return self.kit_exe or self.app_profile.kit_exe

    @property
    def effective_kit_file(self) -> str:
        """kit_file override (env) > profile default."""
        return self.kit_file or self.app_profile.kit_file

    @model_validator(mode="after")
    def _resolve_profile_and_derived_fields(self) -> "IsaacSimProcessConfig":
        resolved = get_profile(self.app_profile_name)
        object.__setattr__(self, "app_profile", resolved)

        # extra_ext_ids is a legacy Isaac-specific env knob (ISAAC_SIM_EXTRA_EXT_IDS
        # typically lists isaacsim.sensors.rtx / isaacsim.replicator.agent.core /
        # omni.anim.* — all Isaac-only). Leaking those into USD Composer causes
        # "Failed to resolve extension dependencies" crash during kit boot.
        # So: env override applies ONLY to isaac-sim profile. Other profiles use
        # their own curated list from the KitAppProfile.
        if resolved.name == "isaac-sim" and self.extra_ext_ids:
            pass  # env value honored for Isaac only
        else:
            object.__setattr__(self, "extra_ext_ids", resolved.extra_ext_ids)

        if self.health_url is None:
            object.__setattr__(
                self, "health_url",
                f"http://localhost:{self.ext_port}/validation/v1/health",
            )
        return self


class ScenarioConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCENARIO_", env_file=".env", extra="ignore")

    scenarios_dir: str = Field(default="scenarios", alias="SCENARIOS_DIR")
    default_timeout: float = Field(default=600.0, alias="SCENARIO_DEFAULT_TIMEOUT")
    default_step_timeout: float = 60.0
    default_fail_fast: bool = True


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    isaac_sim: IsaacSimConfig = Field(default_factory=IsaacSimConfig)
    isaac_sim_process: IsaacSimProcessConfig = Field(default_factory=IsaacSimProcessConfig)
    lakehouse: LakehouseConfig = Field(default_factory=LakehouseConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    scenario: ScenarioConfig = Field(default_factory=ScenarioConfig)

    @model_validator(mode="after")
    def _propagate_ext_port_to_base_url(self) -> "AppConfig":
        """If no explicit ISAAC_SIM_BASE_URL, derive from process ext_port.

        This is what ties the instance_id + app_profile layer together with
        the HTTP client that talks to Extension REST.
        """
        if self.isaac_sim.base_url is None:
            derived = f"http://localhost:{self.isaac_sim_process.ext_port}"
            object.__setattr__(self.isaac_sim, "base_url", derived)
        return self


def load_config() -> AppConfig:
    return AppConfig()
