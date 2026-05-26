"""Author the SDG scene into a USD stage. Idempotent. pxr lazy-imported.

Authors: warehouse env reference + labeled real props (parent-identity Xform +
/Model child reference, the office bug#2 double-offset-avoidance pattern) + a
camera ring. Semantic labels via UsdSemantics.LabelsAPI (OpenUSD-standard). Works
headless (usd-core) — remote references are authored as arcs, not resolved.
"""
from __future__ import annotations

from . import config, labels, sensor_rig

_MANAGED = (config.ENV_PRIM, config.PROPS_ROOT, config.CAMERAS_ROOT)


def clear(stage) -> None:
    """Remove managed roots so a rebuild is idempotent (no accumulation)."""
    for path in _MANAGED:
        if stage.GetPrimAtPath(path):
            stage.RemovePrim(path)


def _author_label(prim, label_class: str) -> None:
    from pxr import UsdSemantics

    api = UsdSemantics.LabelsAPI.Apply(prim, config.SEMANTIC_LABEL_TYPE)
    api.CreateLabelsAttr([label_class])


def build(stage) -> dict:
    """Build /World (env + labeled props + camera ring). Returns authored paths."""
    from pxr import UsdGeom, Gf

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, config.WORLD)
    stage.SetDefaultPrim(world.GetPrim())

    clear(stage)

    # Environment (referenced; identity parent Xform).
    env = UsdGeom.Xform.Define(stage, config.ENV_PRIM)
    env.GetPrim().GetReferences().AddReference(config.ENVIRONMENT_URL)

    # Props: parent Xform carries translate + semantic label; /Model child holds
    # the reference (keeps the asset's own transform from double-offsetting).
    UsdGeom.Xform.Define(stage, config.PROPS_ROOT)
    prop_paths: list[str] = []
    for name, url, label_class, translate in labels.prop_label_pairs():
        parent_path = f"{config.PROPS_ROOT}/{name}"
        parent = UsdGeom.Xform.Define(stage, parent_path)
        parent.AddTranslateOp().Set(Gf.Vec3d(*translate))
        _author_label(parent.GetPrim(), label_class)
        model = UsdGeom.Xform.Define(stage, f"{parent_path}/Model")
        model.GetPrim().GetReferences().AddReference(url)
        prop_paths.append(parent_path)

    # Camera ring.
    UsdGeom.Xform.Define(stage, config.CAMERAS_ROOT)
    cam_paths: list[str] = []
    eyes = sensor_rig.ring_camera_eyes(
        config.CAMERA_COUNT, config.CAMERA_RING_RADIUS, config.CAMERA_HEIGHT
    )
    for i, eye in enumerate(eyes):
        cam_path = f"{config.CAMERAS_ROOT}/Cam_{i:02d}"
        cam = UsdGeom.Camera.Define(stage, cam_path)
        cam.CreateFocalLengthAttr(config.CAMERA_FOCAL_LENGTH)
        m = sensor_rig.compute_lookat_matrix(eye, config.CAMERA_TARGET)
        cam.AddTransformOp().Set(Gf.Matrix4d(*m))
        cam_paths.append(cam_path)

    return {"env": config.ENV_PRIM, "props": prop_paths, "cameras": cam_paths}
