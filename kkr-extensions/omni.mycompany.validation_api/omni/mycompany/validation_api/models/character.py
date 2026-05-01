"""Pydantic models for Character REST endpoints (Phase C).

All models mirror the style of :mod:`models.robot` — ``ConfigDict(extra="forbid")``
on request bodies so unknown keys raise ``422`` at the FastAPI boundary, and
scalar-first quaternion convention ``[qw, qx, qy, qz]`` for orientation /
rotation fields (matches the testbed characters.py output contract).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The AnimationGraph shipped with Biped_Setup.usd exposes this fixed set of
# clips via the ``Action`` variable. Keep ``Literal`` — picking something
# outside this set is silently ignored by the graph and produces confusing
# green-but-frozen characters.
AnimationClipName = Literal["Idle", "Walk", "Run", "Sit"]


class CharacterLoadRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usd_url: str = Field(description="Character USD asset URL (S3 or local)")
    prim_path: str | None = Field(
        default=None,
        description=(
            "Target stage prim path. Omit to derive from the USD filename "
            "(UUID-safe sanitize, placed under /World/Characters)."
        ),
    )
    position: list[float] | None = Field(
        default=None, description="[x, y, z] initial world position (metres)"
    )
    yaw: float = Field(
        default=0.0, description="Initial yaw rotation in radians (Z-axis)"
    )


class CharacterLoadResponseModel(BaseModel):
    ok: bool = True
    prim_path: str = Field(
        description=(
            "Prim path as supplied by the caller (echoed verbatim). When the "
            "caller omits prim_path this field equals sanitized_prim_path. "
            "Compare against sanitized_prim_path to detect sanitisation."
        )
    )
    skel_root_path: str
    sanitized_prim_path: str = Field(
        description="USD-legal prim path actually created on stage"
    )
    has_skeleton: bool
    anim_graph_bound: bool


class CharacterPlayAnimationRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    animation_name: AnimationClipName = Field(
        description="Clip name — bound by the Biped_Setup AnimationGraph"
    )
    speed: float = Field(
        default=1.0,
        description="Walk/Run speed multiplier (ignored for Idle/Sit)",
    )
    target_position: list[float] | None = Field(
        default=None,
        description=(
            "[x, y, z] target for Walk/Run. None means play in place "
            "(no PathPoints). Ignored for Idle/Sit."
        ),
    )


class CharacterPlayAnimationResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    action: str
    speed: float
    bound_graph: str


class CharacterSetPositionRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    position: list[float] = Field(description="[x, y, z] world position (metres)")
    orientation: list[float] | None = Field(
        default=None,
        description="Quaternion [qw, qx, qy, qz] scalar-first (None = keep current)",
    )


class CharacterSetPositionResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    position: list[float]
    orientation: list[float]


class CharacterStopAnimationRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str


class CharacterStopAnimationResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    action: str = "Idle"
    speed: float = 0.0


class CharacterNavigateRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prim_path: str
    target: list[float] = Field(description="[x, y, z] navigation target")
    speed: float = Field(default=1.0, description="Walk speed multiplier")


class CharacterNavigateResponseModel(BaseModel):
    ok: bool = True
    job_id: str
    prim_path: str
    target: list[float]


class CharacterSitOnPrimRequestModel(BaseModel):
    """Orchestrated 2-leg nav + Sit animation — asset-aware chair seating."""

    model_config = ConfigDict(extra="forbid")

    character_prim_path: str
    chair_prim_path: str
    character_usd_url: str | None = Field(
        default=None,
        description=(
            "Character USD url used for reload-anchor. When provided, after "
            "navigate completes the character is unloaded + reloaded at the "
            "sit target so Sit clip plays visually (navigate leaves AnimGraph "
            "in a Walk-warm state that blocks Sit visual transition). When "
            "omitted, sit_on_prim falls back to stop+Sit which may not "
            "engage the clip visibly."
        ),
    )
    chair_forward_local: list[float] = Field(
        default_factory=lambda: [0.0, 1.0, 0.0],
        description=(
            "Chair's forward axis in its own local frame. Kit furniture convention is +Y. "
            "Override for SimReady assets that use a different forward."
        ),
    )
    approach_distance: float = Field(
        default=1.2, gt=0.0, le=5.0,
        description="Metres behind the chair for leg-1 target (controls final facing).",
    )
    speed: float = 1.0
    play_sit: bool = True
    nav_timeout_s: float = Field(default=45.0, gt=0.0, le=300.0)


class CharacterStateResponseModel(BaseModel):
    ok: bool = True
    prim_path: str
    position: list[float]
    rotation: list[float] = Field(description="Quaternion [qw, qx, qy, qz]")
    action: str
    is_navigating: bool


class CharacterPlayAnimationVariantRequestModel(BaseModel):
    """Play an AnimationGraph variant (Phase G).

    Extends ``CharacterPlayAnimationRequestModel`` with BlendSpace variable
    access — e.g. ``SitReading`` resolves to ``Action=Sit`` + ``sit_style=reading``.
    When the requested variable is not wired into the AnimGraph, the
    extension logs a warning but still returns ok — only the Action base
    token is guaranteed.
    """

    model_config = ConfigDict(extra="forbid")

    prim_path: str
    variant: str = Field(
        description=(
            "AnimGraph variant name (e.g. SitIdle, SitTalk, SitReading, WalkFast, "
            "RunSlow). Base Action is derived from the prefix (Sit/Walk/Run/Idle)."
        ),
    )
    speed: float = 1.0
    target_position: list[float] | None = Field(
        default=None,
        description="[x, y, z] target for Walk/Run variants (PathPoints steering)",
    )


class CharacterLoadCrowdRequestModel(BaseModel):
    """Batch-load N Biped characters in a layout (Phase G).

    The extension delegates per-character load to ``CharacterService.load``
    using Biped_Setup.usd + derived per-index prim paths. Individual load
    failures are captured in the response rather than aborting the batch.
    """

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1, le=100, description="Number of characters to spawn")
    layout: Literal["grid", "line", "random"] = "grid"
    spacing: float = Field(default=2.0, gt=0.0, le=50.0)
    base_name: str = Field(
        default="Crowd",
        description="Prim name prefix — per-character path is /World/Characters/{base_name}_{i:02d}",
    )
    center: list[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0],
        description="[x, y, z] crowd centroid (all positions offset from here)",
    )
    usd_url: str | None = Field(
        default=None,
        description="Character USD to clone. Defaults to Biped_Setup.usd if omitted.",
    )
