"""Replicator (SDG) types — writer / randomizer / triggers (Phase H)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True, frozen=True)
class ReplicatorCreateWriterRequest:
    writer_type: Literal["BasicWriter", "KittiWriter", "CocoWriter"]
    output_dir: str
    rgb: bool = True
    depth: bool = False
    semantic_segmentation: bool = False


@dataclass(slots=True, frozen=True)
class ReplicatorCreateWriterResult:
    ok: bool
    writer_id: str
    writer_type: str
    output_dir: str
    channels: dict[str, bool] = field(default_factory=dict)
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ReplicatorRegisterRandomizerRequest:
    type: Literal["position", "rotation", "lighting"]
    target: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ReplicatorRegisterRandomizerResult:
    ok: bool
    randomizer_id: str
    type: str
    target: str
    config: dict[str, Any] = field(default_factory=dict)
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ReplicatorTriggerOnceRequest:
    num_frames: int = 1


@dataclass(slots=True, frozen=True)
class ReplicatorTriggerOnceResult:
    ok: bool
    num_frames: int
    frames_ran: int
    writer_count: int
    randomizer_count: int
    backend: str = ""


@dataclass(slots=True, frozen=True)
class ReplicatorTriggerOnTimeRequest:
    interval_s: float


@dataclass(slots=True, frozen=True)
class ReplicatorTriggerOnTimeResult:
    ok: bool
    trigger_id: str
    interval_s: float
    backend: str = ""
