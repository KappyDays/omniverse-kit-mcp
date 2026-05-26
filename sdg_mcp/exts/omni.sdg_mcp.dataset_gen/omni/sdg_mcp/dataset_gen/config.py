"""Pure constants for the SDG dataset generator (NO omni / pxr imports).

Importable anywhere (Kit, headless, tests). All asset URLs are real Isaac Sim 5.1
catalog assets (R1) resolved during RECON — see mcp-upgrade/make_progress/sdg_make.md.
"""
from __future__ import annotations

ISAAC = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac"

ENVIRONMENT_URL = f"{ISAAC}/Environments/Simple_Warehouse/warehouse.usd"

# Stage prim paths (managed roots are cleared on rebuild for idempotency).
WORLD = "/World"
ENV_PRIM = "/World/Environment"
PROPS_ROOT = "/World/Props"
CAMERAS_ROOT = "/World/Cameras"

# Labeled real props: (name, url, semantic_class, translate)
PROPS = (
    ("Forklift", f"{ISAAC}/Props/Forklift/forklift.usd", "forklift", (3.0, 0.0, 0.0)),
    ("Bin", f"{ISAAC}/Props/KLT_Bin/small_KLT.usd", "bin", (0.0, 0.0, 0.0)),
    ("Pallet", f"{ISAAC}/Props/Pallet/pallet.usd", "pallet", (-2.0, 1.0, 0.0)),
)

# Semantics
SEMANTIC_LABEL_TYPE = "class"  # UsdSemantics.LabelsAPI instance name -> semantics:labels:class

# Camera ring
CAMERA_COUNT = 3
CAMERA_RING_RADIUS = 6.0
CAMERA_HEIGHT = 3.0
CAMERA_TARGET = (0.0, 0.0, 0.5)
CAMERA_FOCAL_LENGTH = 24.0

# Replicator / dataset
RESOLUTION = (1280, 720)
FRAME_COUNT = 12
ANNOTATORS = (
    "rgb",
    "distance_to_camera",
    "semantic_segmentation",
    "instance_id_segmentation",
    "bounding_box_2d_tight",
    "bounding_box_3d",
)
OUTPUT_SUBDIR = "dataset"
