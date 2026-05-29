"""Author office_mcp/scenes/office_datacenter.usd with the Kit USD SDK.

Run from a Kit Python context (e.g. via the ``kit_python_run`` MCP tool):

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_scene", r"C:/.../office_mcp/build/build_scene.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    print(m.build())

Design (SPEC §6). Z-up, meters. The whole demo lives in an open floor area of
office.usd at world (x in [-22,-14], y in [27,33], z=0) — verified clear during
asset recon. A partition wall at x=-18 splits the office side (desk + PC) from
the datacenter side (rack + 3 servers + switch). Cables (BasisCurves tubes) run
PC -> switch -> 3 servers in net:order 0..3 and pass through a floor-level gap
in the partition.

CRITICAL: this authors a **standalone** stage opened with ``LoadNone`` and adds
office.usd only as a *payload arc* — its MDL never resolves at build time, so
this is safe to run on the Kit main thread without the office-USD deadlock. The
payload (and its MDL) resolves only when the extension loads the scene through
the deadlock-safe recipe.
"""

from __future__ import annotations

import os

OFFICE_URL = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
    "Assets/Isaac/5.1/Isaac/Environments/Office/office.usd"
)
SIM = (
    "https://omniverse-content-staging.s3.us-west-2.amazonaws.com/"
    "Assets/simready_content/common_assets/props"
)
DESK_URL = f"{SIM}/desk_01/desk_01.usd"
CASE_URL = f"{SIM}/case_a01/case_a01.usd"                       # PC tower + server units
RACK_URL = f"{SIM}/industrialsteelshelving_a01/industrialsteelshelving_a01.usd"  # rack proxy
BOX_URL = f"{SIM}/cubebox_a01/cubebox_a01.usd"                  # switch + dynamic mug


def _default_output() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    office_mcp_root = os.path.dirname(here)
    scenes = os.path.join(office_mcp_root, "scenes")
    os.makedirs(scenes, exist_ok=True)
    return os.path.join(scenes, "office_datacenter.usd").replace("\\", "/")


def build(output_path: str | None = None) -> dict:
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

    out = (output_path or _default_output()).replace("\\", "/")

    # Author on an *anonymous* in-memory layer, then Export to disk. This avoids
    # the Sdf layer-registry / file-lock trap: a previous run leaves the target
    # layer cached in memory, and CreateNew/Open would reuse its stale partial
    # content (observed: leftover xformOps -> AddXformOp collisions). LoadNone so
    # the office payload (and its MDL) is never composed at build time.
    layer = Sdf.Layer.CreateAnonymous("office_datacenter.usd")
    stage = Usd.Stage.Open(layer, load=Usd.Stage.LoadNone)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    # ---- helpers -----------------------------------------------------
    def tag(prim, role, order=None):
        prim.SetCustomDataByKey("net:role", role)
        if order is not None:
            prim.SetCustomDataByKey("net:order", int(order))

    def make_material(path, diffuse, emissive=(0.0, 0.0, 0.0), roughness=0.5, metallic=0.0):
        mat = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + "/Shader")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*diffuse))
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emissive))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mat

    def bind(prim, mat):
        UsdShade.MaterialBindingAPI(prim).Bind(mat)

    def ref_asset(path, url, translate, rotate=None, scale=None):
        # Wrapper Xform holds *our* transform; the reference goes on a child so
        # the asset's own xformOpOrder ([translate, rotateXYZ, scale]) never
        # collides with the ops we author.
        wrapper = UsdGeom.Xform.Define(stage, path)
        xf = UsdGeom.Xformable(wrapper)
        xf.AddTranslateOp().Set(Gf.Vec3d(*translate))
        if rotate is not None:
            xf.AddRotateXYZOp().Set(Gf.Vec3f(*rotate))
        if scale is not None:
            xf.AddScaleOp().Set(Gf.Vec3f(*scale))
        inner = UsdGeom.Xform.Define(stage, path + "/Asset")
        inner.GetPrim().GetReferences().AddReference(url)
        return wrapper.GetPrim()

    def make_box(path, center, half, mat=None, visible=True):
        cube = UsdGeom.Cube.Define(stage, path)
        cube.GetSizeAttr().Set(2.0)  # unit cube spans [-1,1]
        xf = UsdGeom.Xformable(cube)
        xf.AddTranslateOp().Set(Gf.Vec3d(*center))
        xf.AddScaleOp().Set(Gf.Vec3f(*half))
        if not visible:
            UsdGeom.Imageable(cube).CreateVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        if mat is not None:
            bind(cube.GetPrim(), mat)
        return cube.GetPrim()

    def make_cable(path, pts, mat, width=0.05):
        curves = UsdGeom.BasisCurves.Define(stage, path)
        curves.CreateTypeAttr().Set(UsdGeom.Tokens.linear)
        curves.CreatePointsAttr([Gf.Vec3f(*p) for p in pts])
        curves.CreateCurveVertexCountsAttr([len(pts)])
        wa = curves.CreateWidthsAttr([float(width)] * len(pts))
        curves.SetWidthsInterpolation(UsdGeom.Tokens.vertex)
        bind(curves.GetPrim(), mat)
        return curves.GetPrim()

    # ---- /World/Office : payload (instanceable), NOT resolved at build ----
    office = UsdGeom.Xform.Define(stage, "/World/Office")
    office.GetPrim().GetPayloads().AddPayload(OFFICE_URL)
    office.GetPrim().SetInstanceable(True)

    demo = UsdGeom.Xform.Define(stage, "/World/Demo").GetPrim()
    looks = "/World/Demo/Looks"

    # ---- materials ---------------------------------------------------
    cable_mats = [make_material(f"{looks}/CableMat_{i:02d}", (0.08, 0.08, 0.10),
                                roughness=0.35, metallic=0.1) for i in range(4)]
    led_mats = {o: make_material(f"{looks}/LedMat_{o:02d}", (0.04, 0.04, 0.04),
                                 roughness=0.4) for o in (1, 2, 3)}
    btn_mat = make_material(f"{looks}/PowerButtonMat", (0.35, 0.02, 0.02),
                            emissive=(0.5, 0.0, 0.0), roughness=0.3)
    switch_mat = make_material(f"{looks}/SwitchMat", (0.1, 0.12, 0.16), roughness=0.4, metallic=0.3)

    # ---- partition wall (collider) ----------------------------------
    wall_mat = make_material(f"{looks}/WallMat", (0.55, 0.55, 0.58), roughness=0.7)
    # Waist-high divider (z in [0.15, 1.25]) — separates office/datacenter and
    # keeps a 0.15 m floor gap for the cable pass-through, while staying low
    # enough that the review camera sees over it to BOTH sides of the demo.
    wall = make_box("/World/Demo/Partition", center=(-18.0, 30.0, 0.70),
                    half=(0.075, 2.5, 0.55), mat=wall_mat)
    UsdPhysics.CollisionAPI.Apply(wall)

    # ---- office side: desk + PC + power button ----------------------
    ref_asset("/World/Demo/Office_Desk", DESK_URL, translate=(-20.0, 30.0, 0.0))
    pc = ref_asset("/World/Demo/PC", CASE_URL, translate=(-19.9, 30.0, 0.78))

    # Power button: small disc (cylinder, axis along -Y) on the PC front face.
    btn = UsdGeom.Cylinder.Define(stage, "/World/Demo/PC/PowerButton")
    btn.GetAxisAttr().Set(UsdGeom.Tokens.y)
    btn.GetRadiusAttr().Set(0.05)
    btn.GetHeightAttr().Set(0.04)
    bxf = UsdGeom.Xformable(btn)
    # PC ref already moved PC to (-19.9,30,0.78); PowerButton is a child -> local coords.
    bxf.AddTranslateOp().Set(Gf.Vec3d(0.0, -0.2, 0.12))  # front (-Y) of the case, mid height
    bind(btn.GetPrim(), btn_mat)
    tag(btn.GetPrim(), "trigger")

    # ---- datacenter side: rack + 3 servers + switch -----------------
    ref_asset("/World/Demo/DataCenter/Rack", RACK_URL, translate=(-15.3, 30.0, 0.0))

    server_z = {1: 0.40, 2: 0.90, 3: 1.40}
    for o in (1, 2, 3):
        z = server_z[o]
        ref_asset(f"/World/Demo/DataCenter/Server_{o:02d}", CASE_URL,
                  translate=(-15.6, 30.0, z))
        # LED: small emissive cube on the server's front (-Y) face.
        led = make_box(f"/World/Demo/DataCenter/Server_{o:02d}_LED",
                       center=(-15.6, 29.80, z + 0.115), half=(0.05, 0.02, 0.04),
                       mat=led_mats[o])
        tag(led, "server_led", order=o)

    switch = ref_asset("/World/Demo/DataCenter/Switch", BOX_URL, translate=(-16.8, 30.0, 0.0))
    bind(switch, switch_mat)
    tag(switch, "switch")

    # ---- cables (BasisCurves tubes), net:order 0..3 -----------------
    sw = (-16.8, 30.0, 0.13)   # switch top hub point
    make_cable("/World/Demo/Cables/Seg_PC_to_Switch", [
        (-19.9, 29.82, 0.86), (-19.9, 30.02, 0.45), (-19.9, 30.02, 0.08),
        (-18.0, 30.0, 0.07), sw,
    ], cable_mats[0])
    tag(stage.GetPrimAtPath("/World/Demo/Cables/Seg_PC_to_Switch"), "cable", order=0)

    server_cable_end = {1: (-15.85, 29.9, 0.40), 2: (-15.85, 29.9, 0.90), 3: (-15.85, 29.9, 1.40)}
    for o in (1, 2, 3):
        mid_z = 0.2 + 0.35 * o
        make_cable(f"/World/Demo/Cables/Seg_Switch_Server{o:02d}", [
            sw, (-16.2, 30.0, mid_z), server_cable_end[o],
        ], cable_mats[o])
        tag(stage.GetPrimAtPath(f"/World/Demo/Cables/Seg_Switch_Server{o:02d}"),
            "cable", order=o)

    # ---- physics: scene + ground/desk colliders + 1 dynamic prop ----
    scene = UsdPhysics.Scene.Define(stage, "/World/Demo/Physics/PhysicsScene")
    scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr().Set(9.81)

    ground = make_box("/World/Demo/Physics/GroundCollider", center=(-18.0, 30.0, -0.05),
                      half=(8.0, 6.0, 0.05), visible=False)
    UsdPhysics.CollisionAPI.Apply(ground)
    desk_col = make_box("/World/Demo/Physics/DeskCollider", center=(-20.0, 30.0, 0.76),
                        half=(0.34, 0.96, 0.02), visible=False)
    UsdPhysics.CollisionAPI.Apply(desk_col)

    # Dynamic rigid body: a small box prop that drops onto the desk on Play.
    # RigidBodyAPI on the wrapper; collider on the inner referenced geometry
    # (convex hull) — standard SimReady physics pattern.
    mug = ref_asset("/World/Demo/Props/Mug", BOX_URL, translate=(-19.7, 30.35, 0.95))
    UsdPhysics.RigidBodyAPI.Apply(mug)
    mug_inner = stage.GetPrimAtPath("/World/Demo/Props/Mug/Asset")
    UsdPhysics.CollisionAPI.Apply(mug_inner)
    mca = UsdPhysics.MeshCollisionAPI.Apply(mug_inner)
    mca.CreateApproximationAttr().Set(UsdPhysics.Tokens.convexHull)

    # ---- lighting (R3) ----------------------------------------------
    # The demo sits in an interior office space; the office's own lights don't
    # reach it and an overhead dome alone leaves the props' vertical faces black.
    # So: a dome for ambient + sphere lights at prop mid-height between the
    # camera and the props to light their camera-facing sides. Kept well under
    # the ~2.7 m office ceiling so they're not occluded.
    from pxr import UsdLux

    def sphere_light(path, pos, intensity, radius=0.4):
        sl = UsdLux.SphereLight.Define(stage, path)
        sl.CreateIntensityAttr().Set(float(intensity))
        sl.CreateRadiusAttr().Set(float(radius))
        sl.CreateColorAttr().Set(Gf.Vec3f(1.0, 0.98, 0.92))
        UsdGeom.Xformable(sl).AddTranslateOp().Set(Gf.Vec3d(*pos))
        return sl

    dome = UsdLux.DomeLight.Define(stage, "/World/Demo/Lighting/DomeLight")
    dome.CreateIntensityAttr().Set(1500.0)
    # Overhead soft fill.
    rect = UsdLux.RectLight.Define(stage, "/World/Demo/Lighting/Overhead")
    rect.CreateIntensityAttr().Set(4500.0)
    rect.CreateWidthAttr().Set(8.0)
    rect.CreateHeightAttr().Set(6.0)
    UsdGeom.Xformable(rect).AddTranslateOp().Set(Gf.Vec3d(-18.0, 30.0, 2.4))
    # Key/fill sphere lights at prop height, on the camera side (-Y) of the props.
    sphere_light("/World/Demo/Lighting/KeyOffice", (-20.0, 28.2, 1.7), 35000.0, 0.5)
    sphere_light("/World/Demo/Lighting/KeyDataCenter", (-16.0, 28.2, 1.7), 35000.0, 0.5)
    sphere_light("/World/Demo/Lighting/Fill", (-18.0, 27.0, 1.9), 20000.0, 0.5)

    # ---- review cameras (R3 captures) -------------------------------
    # Author transforms as explicit look-at matrices (Z-up) — deterministic vs.
    # a guessed rotateXYZ. Each camera must sit INSIDE the open demo room
    # (clear band x[-22,-14], y[27,33]); a camera at y<27 has an office wall
    # between it and the props. Several angles are authored so the best framing
    # can be picked at capture time. `ReviewCamera` is the primary.
    def review_cam(path, eye, target, focal=18.0):
        cam = UsdGeom.Camera.Define(stage, path)
        view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1))
        UsdGeom.Xformable(cam).AddTransformOp().Set(view.GetInverse())
        cam.CreateFocalLengthAttr().Set(focal)
        cam.CreateClippingRangeAttr().Set(Gf.Vec2f(0.1, 10000.0))
        return cam

    review_cam("/World/Demo/ReviewCamera", (-18.0, 27.3, 2.4), (-18.0, 30.2, 0.95), focal=16.0)
    review_cam("/World/Demo/ReviewCameraB", (-20.8, 27.5, 2.3), (-15.6, 30.2, 0.9), focal=18.0)
    review_cam("/World/Demo/ReviewCameraC", (-18.0, 28.0, 2.6), (-18.0, 30.3, 0.5), focal=14.0)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    layer.Export(out)

    # ---- report ------------------------------------------------------
    tagged = []
    for prim in stage.Traverse():
        role = prim.GetCustomDataByKey("net:role")
        if role:
            tagged.append((prim.GetPath().pathString, role, prim.GetCustomDataByKey("net:order")))
    return {
        "ok": True,
        "output": out,
        "tagged_count": len(tagged),
        "tagged": tagged,
    }


if __name__ == "__main__":
    print(build())
