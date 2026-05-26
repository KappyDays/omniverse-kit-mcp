"""Pure declarative spec of the Replicator graph to wire up live (NO omni).

The live extension reads this to build the omni.replicator.core graph. Keeping it
as data makes the randomization/annotator plan unit-testable headless.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class ReplicatorSpec:
    camera_paths: tuple[str, ...]
    resolution: tuple[int, int]
    frame_count: int
    annotators: tuple[str, ...]
    randomize_pose: bool
    randomize_materials: bool
    randomize_lighting: bool
    output_subdir: str


def build_spec(camera_paths) -> ReplicatorSpec:
    return ReplicatorSpec(
        camera_paths=tuple(camera_paths),
        resolution=config.RESOLUTION,
        frame_count=config.FRAME_COUNT,
        annotators=config.ANNOTATORS,
        randomize_pose=True,
        randomize_materials=True,
        randomize_lighting=True,
        output_subdir=config.OUTPUT_SUBDIR,
    )
