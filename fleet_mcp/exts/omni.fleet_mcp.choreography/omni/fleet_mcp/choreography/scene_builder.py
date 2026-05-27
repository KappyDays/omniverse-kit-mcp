"""Author the fleet scene into a USD stage. Idempotent. pxr lazy-imported.

Grid env reference + N Carter robots (parent-identity + /Model child reference) at
the triangle start formation + leader-waypoint marker spheres (procedural viz only;
the R1 subject is the robots). Works headless (usd-core).
"""
from __future__ import annotations

from . import config, path_planner

_MANAGED = (config.ENV_PRIM, config.FLEET_ROOT, config.WAYPOINTS_ROOT)


def clear(stage) -> None:
    for path in _MANAGED:
        if stage.GetPrimAtPath(path):
            stage.RemovePrim(path)


def build(stage, formation: str = "triangle") -> dict:
    from pxr import UsdGeom, Gf

    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, config.WORLD)
    stage.SetDefaultPrim(world.GetPrim())

    clear(stage)

    env = UsdGeom.Xform.Define(stage, config.ENV_PRIM)
    env.GetPrim().GetReferences().AddReference(config.ENVIRONMENT_URL)

    UsdGeom.Xform.Define(stage, config.FLEET_ROOT)
    robot_paths: list[str] = []
    for name, (x, y) in zip(config.ROBOT_NAMES, path_planner.start_poses(formation)):
        parent_path = f"{config.FLEET_ROOT}/{name}"
        parent = UsdGeom.Xform.Define(stage, parent_path)
        parent.AddTranslateOp().Set(Gf.Vec3d(x, y, config.ROBOT_START_Z))
        model = UsdGeom.Xform.Define(stage, f"{parent_path}/Model")
        model.GetPrim().GetReferences().AddReference(config.ROBOT_URL)
        robot_paths.append(parent_path)

    UsdGeom.Xform.Define(stage, config.WAYPOINTS_ROOT)
    wp_paths: list[str] = []
    for i, (x, y, _t) in enumerate(path_planner.leader_schedule()):
        wp_path = f"{config.WAYPOINTS_ROOT}/wp_{i:02d}"
        sph = UsdGeom.Sphere.Define(stage, wp_path)
        sph.CreateRadiusAttr(config.MARKER_RADIUS)
        sph.AddTranslateOp().Set(Gf.Vec3d(x, y, 0.1))
        sph.CreateDisplayColorAttr([Gf.Vec3f(0.1, 0.8, 0.2)])
        wp_paths.append(wp_path)

    return {
        "env": config.ENV_PRIM,
        "robots": robot_paths,
        "waypoints": wp_paths,
        "graph_path": config.GRAPH_PATH,
    }
