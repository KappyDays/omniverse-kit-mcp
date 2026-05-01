"""Spawn dynamic red cubes on Belt_N at fixed interval (USD API direct)."""

from __future__ import annotations

import asyncio
import carb
import omni.kit.app
import omni.usd
from pxr import Gf, Sdf, UsdGeom, UsdPhysics

CUBES_PARENT = "/World/Cubes"
SPAWN_POSITION = (-0.5, 1.0, 0.7)
CUBE_SIZE = 0.05
SPAWN_INTERVAL_S = 3.0


class CubeSpawner:
    def __init__(self):
        self._stop = False
        self._count = 0

    def stop(self) -> None:
        self._stop = True

    def count(self) -> int:
        return self._count

    async def run(self) -> None:
        try:
            stage = omni.usd.get_context().get_stage()
            if stage is not None and not stage.GetPrimAtPath(CUBES_PARENT).IsValid():
                UsdGeom.Xform.Define(stage, Sdf.Path(CUBES_PARENT))
        except Exception as exc:
            carb.log_warn(f"[conveyor_pick] CUBES_PARENT create error: {exc}")
        while not self._stop:
            self._spawn_one()
            self._count += 1
            t0 = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - t0) < SPAWN_INTERVAL_S:
                if self._stop:
                    return
                await omni.kit.app.get_app().next_update_async()

    def _spawn_one(self) -> None:
        path = f"{CUBES_PARENT}/Cube_{self._count:04d}"
        try:
            stage = omni.usd.get_context().get_stage()
            if stage is None:
                carb.log_warn("[conveyor_pick] no stage in spawner")
                return
            cube = UsdGeom.Cube.Define(stage, Sdf.Path(path))
            cube.GetSizeAttr().Set(CUBE_SIZE)
            prim = cube.GetPrim()
            xform = UsdGeom.Xformable(prim)
            xform.ClearXformOpOrder()
            xform.AddTranslateOp().Set(Gf.Vec3d(*SPAWN_POSITION))
            cube.GetDisplayColorAttr().Set([Gf.Vec3f(1.0, 0.0, 0.0)])
            UsdPhysics.RigidBodyAPI.Apply(prim)
            UsdPhysics.CollisionAPI.Apply(prim)
            mass_api = UsdPhysics.MassAPI.Apply(prim)
            mass_api.GetMassAttr().Set(0.05)
            carb.log_info(f"[conveyor_pick] spawned cube {path}")
        except Exception as exc:
            carb.log_warn(f"[conveyor_pick] cube spawn error: {exc}")
