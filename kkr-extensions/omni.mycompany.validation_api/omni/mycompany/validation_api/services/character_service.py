"""Character service — human character load, AnimationGraph binding, nav (Phase C).

Mirrors :mod:`services.robot_service` structure: a thin service facade, lazy
imports for all ``omni.*`` / ``pxr.*`` / ``isaacsim.*`` / ``carb`` modules
(Extension rule #7), and async navigation dispatched to :class:`JobService`.

The algorithm is ported from
``isaac_sim_testbed/src/isaac_sim_testbed/characters.py`` (read-only reference)
but reshaped to the REST/Pydantic boundary: each method takes a plain ``dict``
and returns a ``dict`` that ``rest_router`` serialises.

See ``kkr-extensions/CLAUDE.md`` for HTTP status convention
(``ValueError`` → 400) and the ASYNC Job pattern used by :meth:`navigate_to`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Stage layout — mirror of the Isaac Sim 6.0 Replicator Agent character loader.
_CHARS_ROOT = "/World/Characters"
_MOTION_LIBRARY_PATH = _CHARS_ROOT + "/HumanMotionLibrary"

# Navigation polling knobs (Phase C).
_NAV_POLL_FRAMES = 6  # frames between distance checks inside _navigate_coro
_NAV_ARRIVAL_M = 0.1  # XY distance threshold for "arrived"
_NAV_TIMEOUT_S = 30.0  # hard cap on a single navigate_to job


class CharacterService:
    """USD character load + BehaviorAgent/IRA control + async navigate.

    Stateless: no per-character manager object; each REST call re-resolves the
    SkelRoot via the USD Stage. The only shared state is the injected
    :class:`JobService`, which owns all background navigate tasks.
    """

    def __init__(self, job_service: Any, stage_service: Any = None) -> None:
        self._job_service = job_service
        self._stage_service = stage_service  # optional; used by sit_on_prim
        # Runtime readback can return a raw token-list that stringifies as "[]",
        # so readback cannot always recover the currently-playing clip. Keep a
        # simple authoritative cache of the last Action / Walk speed per SkelRoot
        # path; play/stop write it and get_state prefers it.
        self._last_action: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API (6 methods matching models/character.py)
    # ------------------------------------------------------------------

    async def load(self, request: dict[str, Any]) -> dict[str, Any]:
        """Load a character USD and bind Isaac Sim 6.0 BehaviorAgent/IRA APIs.

        Raises ``ValueError`` if the referenced USD fails to resolve a
        ``SkelRoot`` (S3 404 silent success mitigation — see testbed #16).
        """
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Gf, UsdGeom

        usd_url: str = request["usd_url"].replace("\\", "/")
        requested_prim_path: str | None = request.get("prim_path")
        position: list[float] = list(request.get("position") or [0.0, 0.0, 0.0])
        yaw: float = float(request.get("yaw") or 0.0)

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")

        # 1. Derive a USD-safe character name. ALWAYS run _sanitize_prim_name —
        #    live testing (2026-04-18) showed DH_Characters_Extended UUID paths
        #    like "/World/Characters/02c80685-06e3-..." reach USD-path validation
        #    with hyphens and fail with `"... is not a valid path"`. Sanitising
        #    only when the caller omits prim_path is a pre-Phase-C oversight.
        if requested_prim_path:
            raw_char_name = requested_prim_path.rstrip("/").split("/")[-1]
        else:
            raw_char_name = usd_url.rstrip("/").split("/")[-1]
            if raw_char_name.endswith(".usd"):
                raw_char_name = raw_char_name[: -len(".usd")]
            elif raw_char_name.endswith(".usda"):
                raw_char_name = raw_char_name[: -len(".usda")]
        char_name = _sanitize_prim_name(raw_char_name)

        sanitized_prim_path = f"{_CHARS_ROOT}/{char_name}"

        # 2. Load the skin directly. Isaac Sim 6.0 no longer ships
        #    the IRA 0.x CharacterUtil helper or its public rig setup USD.
        if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
            UsdGeom.Xform.Define(stage, _CHARS_ROOT)
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=omni.usd.get_context(),
            path_to=sanitized_prim_path,
            asset_path=usd_url,
            prim_path=None,
            instanceable=False,
            select_prim=False,
        )
        await _wait_stage_loading()

        character_prim = stage.GetPrimAtPath(sanitized_prim_path)
        if not character_prim.IsValid():
            raise ValueError(
                f"Character payload did not create {sanitized_prim_path} "
                f"(url={usd_url})"
            )

        xf = UsdGeom.Xformable(character_prim)
        t_attr = character_prim.GetAttribute("xformOp:translate")
        if not t_attr.IsValid():
            t_attr = xf.AddTranslateOp()
        t_attr.Set(Gf.Vec3d(float(position[0]), float(position[1]), float(position[2])))
        r_attr = character_prim.GetAttribute("xformOp:rotateXYZ")
        if not r_attr.IsValid():
            r_attr = xf.AddRotateXYZOp()
        r_attr.Set(Gf.Vec3f(0.0, 0.0, yaw))

        # 3. Locate the SkelRoot. DH_Characters_Extended nests it under DHGen —
        #    Usd.PrimRange recursion handles both layouts (testbed #15).
        skel_root_path = _find_skel_root(stage, sanitized_prim_path)
        if skel_root_path is None:
            raise ValueError(
                f"SkelRoot not found under {sanitized_prim_path} — "
                "USD may be missing or malformed (S3 404 silent success?)."
            )

        # 4. Bind the 6.0 motion library + BehaviorAgent / IRA APIs.
        motion_library_path = await _ensure_motion_library(stage)
        await _apply_ira_character_apis(stage, skel_root_path, motion_library_path)

        # Preserve input-vs-actual asymmetry (review finding I6): when the
        # caller supplies a prim_path we echo it verbatim in `prim_path`
        # and return the USD-legal path in `sanitized_prim_path`. Comparing
        # the two reveals whether sanitisation happened. In the auto-derive
        # branch the request had no input path, so both fields mirror the
        # sanitised value.
        response_prim_path = (
            requested_prim_path if requested_prim_path else sanitized_prim_path
        )

        return {
            "ok": True,
            "prim_path": response_prim_path,
            "skel_root_path": skel_root_path,
            "sanitized_prim_path": sanitized_prim_path,
            "has_skeleton": True,
            "anim_graph_bound": True,
            "runtime_backend": "isaacsim.replicator.agent.core.behavior_agent",
        }

    async def play_animation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Set the ``Action`` variable on the bound AnimationGraph.

        For Walk/Run + ``target_position`` we also push a 2-point ``PathPoints``
        (current → target) so the graph steers toward the target instead of
        walking in place.
        """
        import carb  # lazy

        prim_path: str = request["prim_path"]
        animation_name: str = request["animation_name"]
        speed: float = float(request.get("speed", 1.0))
        target_position = request.get("target_position")

        skel_root_path = _assert_skel_root(prim_path)
        graph = await self._ensure_animation_ready(skel_root_path)

        graph.set_variable("Action", animation_name)
        if animation_name in ("Walk", "Run") and target_position is not None:
            if len(target_position) != 3:
                raise ValueError(
                    "target_position must be a 3-element [x, y, z] list"
                )
            cur_p = carb.Float3(0.0, 0.0, 0.0)
            cur_r = carb.Float4(0.0, 0.0, 0.0, 0.0)
            graph.get_world_transform(cur_p, cur_r)
            graph.set_variable(
                "PathPoints",
                [
                    carb.Float3(cur_p.x, cur_p.y, cur_p.z),
                    carb.Float3(
                        float(target_position[0]),
                        float(target_position[1]),
                        float(target_position[2]),
                    ),
                ],
            )
            graph.set_variable("Walk", float(speed))
        elif animation_name in ("Walk", "Run"):
            graph.set_variable("Walk", float(speed))
        else:
            graph.set_variable("Walk", 0.0)

        # L2 fix: persist the server-side authoritative state so get_state can
        # return it instead of relying on unreadable runtime variables.
        walk_speed = float(speed) if animation_name in ("Walk", "Run") else 0.0
        self._last_action[skel_root_path] = {
            "action": animation_name,
            "walk_speed": walk_speed,
        }

        return {
            "ok": True,
            "prim_path": prim_path,
            "action": animation_name,
            "speed": speed,
            "bound_graph": skel_root_path,
        }

    async def set_position(self, request: dict[str, Any]) -> dict[str, Any]:
        """Kinematic world-pose write via :class:`SingleXFormPrim`.

        Uses ``SingleXFormPrim`` (not ``XFormPrim``) — testbed API caveat #9:
        the batch view rejects single-prim args.
        """
        import numpy as np  # lazy
        import omni.usd
        from isaacsim.core.prims import SingleXFormPrim

        prim_path: str = request["prim_path"]
        position = request["position"]
        orientation = request.get("orientation")

        if len(position) != 3:
            raise ValueError("position must be a 3-element [x, y, z] list")

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim not found at {prim_path}")

        xform = SingleXFormPrim(prim_path=prim_path)
        pos_arr = np.array(position, dtype=float)
        if orientation is not None:
            if len(orientation) != 4:
                raise ValueError(
                    "orientation must be a 4-element [qw, qx, qy, qz] quaternion"
                )
            orient_arr = np.array(orientation, dtype=float)
            xform.set_world_pose(position=pos_arr, orientation=orient_arr)
        else:
            xform.set_world_pose(position=pos_arr)

        # Read back the resulting pose — set_world_pose may normalise the
        # quaternion and parent xform composition can shift the effective
        # world pose (review finding C1). Mirror the testbed convention:
        # SingleXFormPrim.get_world_pose returns the quaternion scalar-first
        # [qw, qx, qy, qz], so we pass it through untouched.
        cur_p, cur_q = xform.get_world_pose()
        ret_position = (
            cur_p.tolist() if hasattr(cur_p, "tolist") else list(cur_p)
        )
        ret_position = [float(p) for p in ret_position]
        ret_orient = (
            cur_q.tolist() if hasattr(cur_q, "tolist") else list(cur_q)
        )
        ret_orient = [float(q) for q in ret_orient]

        return {
            "ok": True,
            "prim_path": prim_path,
            "position": ret_position,
            "orientation": ret_orient,
        }

    async def stop_animation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Delegate to :meth:`play_animation` with ``Idle`` + speed 0."""
        prim_path: str = request["prim_path"]
        result = await self.play_animation(
            {
                "prim_path": prim_path,
                "animation_name": "Idle",
                "speed": 0.0,
                "target_position": None,
            }
        )
        return {
            "ok": True,
            "prim_path": prim_path,
            "action": "Idle",
            "speed": 0.0,
            "bound_graph": result["bound_graph"],
        }

    async def navigate_to(self, request: dict[str, Any]) -> dict[str, Any]:
        """Dispatch Walk-to-target as an async Job; return ``job_id``.

        The coroutine polls ``graph.get_world_transform()`` every
        ``_NAV_POLL_FRAMES`` frames and stops (Idle) on arrival or timeout.
        Extension restart loses the job (REST 404); callers should poll
        ``/jobs/{id}`` and retry on 404 if necessary.
        """
        prim_path: str = request["prim_path"]
        target = request["target"]
        speed: float = float(request.get("speed", 1.0))

        if len(target) != 3:
            raise ValueError("target must be a 3-element [x, y, z] list")

        # Validate SkelRoot synchronously so the caller sees a 400 immediately
        # instead of having to poll the job for a failed start.
        _assert_skel_root(prim_path)

        service = self

        def _factory(update_progress):
            return _navigate_coro(
                service, prim_path, list(target), speed, update_progress
            )

        job_id = self._job_service.start_job(_factory)
        return {
            "ok": True,
            "job_id": job_id,
            "prim_path": prim_path,
            "target": [float(v) for v in target],
        }

    async def sit_on_prim(self, request: dict[str, Any]) -> dict[str, Any]:
        """High-level helper: navigate character to a chair/seat prim and play Sit.

        Workflow (asset-aware placement for overlap-free seating):
          1. Compute world bbox + orientation of the chair prim.
          2. Rotate the chair's local forward axis (default +Y) into world → facing vector.
          3. Navigate character to ``chair_center - forward * approach_distance`` (behind chair).
          4. Navigate character to ``(chair_center.x, chair_center.y, 0)`` — this leg's movement
             direction is aligned with chair forward, so the character ends up facing the same
             way the chair faces.
          5. Optional: play ``Sit`` animation.

        Timeline must be playing (character_navigate requirement). All intermediate values
        are echoed back for debugging.
        """
        chair_path: str = request["chair_prim_path"]
        character_prim_path: str = request["character_prim_path"]
        forward_local = request.get("chair_forward_local", [0.0, 1.0, 0.0])
        approach_distance: float = float(request.get("approach_distance", 1.2))
        speed: float = float(request.get("speed", 1.0))
        play_sit: bool = bool(request.get("play_sit", True))
        nav_timeout_s: float = float(request.get("nav_timeout_s", 45.0))

        if len(forward_local) != 3:
            raise ValueError("chair_forward_local must be [x, y, z]")

        # Validate character synchronously
        _assert_skel_root(character_prim_path)
        if self._stage_service is None:
            raise RuntimeError("sit_on_prim requires stage_service injection")

        bbox = await self._stage_service.compute_world_bbox(chair_path)
        if bbox.get("is_empty"):
            raise ValueError(f"Chair prim {chair_path} has no renderable geometry")

        chair_center = bbox["center"]
        orient_wxyz = bbox["world_orient_wxyz"]

        fwd_world = _rotate_vec_by_quat_wxyz(tuple(forward_local), tuple(orient_wxyz))
        # Normalize in case caller passed a non-unit vector
        import math
        flen = math.sqrt(fwd_world[0] ** 2 + fwd_world[1] ** 2 + fwd_world[2] ** 2) or 1.0
        fwd_world = (fwd_world[0] / flen, fwd_world[1] / flen, fwd_world[2] / flen)

        approach_start = [
            chair_center[0] - fwd_world[0] * approach_distance,
            chair_center[1] - fwd_world[1] * approach_distance,
            0.0,
        ]
        sit_target = [chair_center[0], chair_center[1], 0.0]

        def _noop(_: dict[str, Any]) -> None:
            pass

        # Leg 1: approach behind chair (any direction — sets up leg 2)
        await asyncio.wait_for(
            _navigate_coro(self, character_prim_path, approach_start, speed, _noop),
            timeout=nav_timeout_s,
        )
        # Leg 2: move onto chair center — character arrives facing chair-forward
        await asyncio.wait_for(
            _navigate_coro(self, character_prim_path, sit_target, speed, _noop),
            timeout=nav_timeout_s,
        )

        character_usd_url = request.get("character_usd_url")
        sit_result: dict[str, Any] | None = None
        if play_sit:
            # Live-discovered legacy character-runtime quirk: after
            # `_navigate_coro`, the locomotion blend tree can stay "warm" —
            # setting Action=Sit and even explicit stop_animation leaves the
            # character visually standing. Unload + reload at the sit target
            # forces a fresh runtime with no residual locomotion state.
            #
            # The reload path requires knowing the original USD URL. Caller
            # should pass `character_usd_url` for reliable visual Sit; if
            # omitted, we fall back to a stop + play Sit sequence (which
            # transitions the Action variable but may not visually engage the
            # clip after navigate — captured as a known limitation).
            import omni.kit.app  # lazy
            app = omni.kit.app.get_app()

            if character_usd_url:
                import omni.kit.commands  # lazy
                omni.kit.commands.execute(
                    "DeletePrimsCommand", paths=[character_prim_path])
                for _ in range(5):
                    await app.next_update_async()
                await self.load({
                    "usd_url": character_usd_url,
                    "prim_path": character_prim_path,
                    "position": sit_target,
                    "yaw": 0.0,
                })
                for _ in range(15):
                    await app.next_update_async()
            else:
                # Fallback path — stop then Sit
                try:
                    await self.stop_animation({"prim_path": character_prim_path})
                except Exception as exc:  # noqa: BLE001
                    logger.debug("sit_on_prim stop soft-fail: %s", exc)
                for _ in range(10):
                    await app.next_update_async()

            sit_result = await self.play_animation({
                "prim_path": character_prim_path,
                "animation_name": "Sit",
                "speed": 1.0,
            })
            for _ in range(90):  # ~1.5 s @ 60 fps — let Sit clip visibly play
                await app.next_update_async()

        return {
            "ok": True,
            "chair_prim_path": chair_path,
            "character_prim_path": character_prim_path,
            "chair_center": chair_center,
            "chair_size": bbox["size"],
            "chair_forward_world": list(fwd_world),
            "approach_start": approach_start,
            "sit_target": sit_target,
            "approach_distance": approach_distance,
            "played_sit": play_sit,
            "sit_result": sit_result,
        }

    async def play_animation_variant(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Play a BehaviorAgent/legacy-compatible variant (Phase G).

        Maps variant strings to base Action + best-effort style combos:
          - Sit*   → Action=Sit,  sit_style=<tail.lower()>
          - Walk*  → Action=Walk, walk_style=<tail.lower()>, Walk=speed
          - Run*   → Action=Run,  run_style=<tail.lower()>, Walk=speed
          - Idle*  → Action=Idle, idle_style=<tail.lower()>
          - else   → Action=<variant>

        If the style variable is not wired into the character runtime,
        the set_variable call silently no-ops in Kit — we capture the
        attempt in ``variables_set`` so the caller can assert which keys
        were actually wired.
        """
        import carb  # lazy

        prim_path: str = request["prim_path"]
        variant: str = request["variant"]
        speed: float = float(request.get("speed", 1.0))
        target_position = request.get("target_position")

        if not variant:
            raise ValueError("variant must be a non-empty string")

        skel_root_path = _assert_skel_root(prim_path)
        graph = await self._ensure_animation_ready(skel_root_path)

        base, style_var, style_value = _parse_variant(variant)
        variables_set: dict[str, Any] = {"Action": base}
        graph.set_variable("Action", base)

        if base in ("Walk", "Run"):
            graph.set_variable("Walk", float(speed))
            variables_set["Walk"] = float(speed)
            if target_position is not None:
                if len(target_position) != 3:
                    raise ValueError("target_position must be [x, y, z]")
                cur_p = carb.Float3(0.0, 0.0, 0.0)
                cur_r = carb.Float4(0.0, 0.0, 0.0, 0.0)
                graph.get_world_transform(cur_p, cur_r)
                graph.set_variable(
                    "PathPoints",
                    [
                        carb.Float3(cur_p.x, cur_p.y, cur_p.z),
                        carb.Float3(
                            float(target_position[0]),
                            float(target_position[1]),
                            float(target_position[2]),
                        ),
                    ],
                )
                variables_set["PathPoints"] = [
                    [float(cur_p.x), float(cur_p.y), float(cur_p.z)],
                    [float(t) for t in target_position],
                ]

        if style_var:
            try:
                graph.set_variable(style_var, style_value)
                variables_set[style_var] = style_value
            except Exception as exc:
                logger.debug(
                    "variant style variable %s not wired (non-fatal): %s",
                    style_var, exc,
                )

        # Legacy Sit state uses SitWeight as blend weight.
        # 0=stand_idle (서있음), 1=Sit_skelanim (앉음).
        # play_animation_variant("SitIdle") 만 호출하면 Action=Sit + sit_style
        # 만 set 되어 SitWeight 가 0 → 사용자가 본 "서있는 자세" 발생.
        # base=Sit 시 SitWeight=1.0 명시 (2026-04-23 사용자 제보 fix).
        if base == "Sit":
            try:
                graph.set_variable("SitWeight", 1.0)
                variables_set["SitWeight"] = 1.0
            except Exception as exc:
                logger.debug(
                    "SitWeight variable not wired (non-fatal): %s", exc,
                )

        self._last_action[skel_root_path] = {
            "action": base,
            "walk_speed": speed if base in ("Walk", "Run") else 0.0,
        }

        return {
            "ok": True,
            "prim_path": prim_path,
            "variant": variant,
            "base_action": base,
            "speed": speed,
            "variables_set": variables_set,
            "bound_graph": skel_root_path,
        }

    async def load_crowd(
        self, request: dict[str, Any],
    ) -> dict[str, Any]:
        """Batch-load N characters in a grid / line / random layout (Phase G)."""
        from isaacsim.storage.native import get_assets_root_path  # lazy

        count = int(request["count"])
        layout = str(request.get("layout", "grid"))
        spacing = float(request.get("spacing", 2.0))
        base_name = str(request.get("base_name", "Crowd"))
        center = list(request.get("center") or [0.0, 0.0, 0.0])
        if len(center) != 3:
            raise ValueError("center must be [x, y, z]")
        usd_url = request.get("usd_url")

        if count < 1:
            raise ValueError("count must be >= 1")
        if layout not in ("grid", "line", "random"):
            raise ValueError("layout must be grid|line|random")

        if not usd_url:
            assets_root = get_assets_root_path()
            if not assets_root:
                raise RuntimeError(
                    "Isaac Sim assets root not resolved — cannot derive "
                    "default character USD URL for crowd load."
                )
            usd_url = (
                f"{assets_root.rstrip('/')}/Isaac/People/Characters/"
                "F_Business_02/F_Business_02.usd"
            )

        positions = _layout_positions(layout, count, spacing, center)

        loaded: list[dict[str, Any]] = []
        success = 0
        for i, pos in enumerate(positions):
            prim_path = f"{_CHARS_ROOT}/{base_name}_{i:02d}"
            try:
                result = await self.load(
                    {
                        "usd_url": usd_url,
                        "prim_path": prim_path,
                        "position": [float(p) for p in pos],
                        "yaw": 0.0,
                    }
                )
                loaded.append(
                    {
                        "index": i,
                        "prim_path": result.get("sanitized_prim_path") or prim_path,
                        "position": [float(p) for p in pos],
                    }
                )
                success += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("crowd member %d load failed: %s", i, exc)
                loaded.append(
                    {
                        "index": i,
                        "prim_path": None,
                        "position": [float(p) for p in pos],
                        "error": str(exc),
                    }
                )

        return {
            "ok": success > 0,
            "count": count,
            "success_count": success,
            "layout": layout,
            "spacing": spacing,
            "base_name": base_name,
            "center": [float(c) for c in center],
            "usd_url": usd_url,
            "loaded": loaded,
        }

    async def get_state(self, prim_path: str) -> dict[str, Any]:
        """Return position / rotation / current Action / is_navigating.

        Reads the world transform from the AnimationGraph (not the USD
        xform attr) so the value reflects the live simulation step.
        """
        import carb  # lazy

        skel_root_path = _assert_skel_root(prim_path)
        graph = await self._ensure_animation_ready(skel_root_path)

        pos = carb.Float3(0.0, 0.0, 0.0)
        rot = carb.Float4(0.0, 0.0, 0.0, 0.0)
        graph.get_world_transform(pos, rot)

        # L2 fix: prefer the server-authoritative cache populated by
        # play_animation / stop_animation. `graph.get_variable("Action")`
        # returns a token-list that stringifies to "[]" with no
        # reliable way to recover the name, so the cache is the actual
        # source of truth. We fall back to the graph read only when no
        # play_animation has been recorded for this character (freshly
        # loaded; still in the runtime's default Idle state).
        cached = self._last_action.get(skel_root_path)
        if cached is not None:
            action = str(cached["action"])
        else:
            action = "Idle"
            if hasattr(graph, "get_variable"):
                try:
                    v = graph.get_variable("Action")
                    if v is not None and str(v) not in ("[]", ""):
                        action = str(v)
                except Exception as exc:
                    logger.debug("get_variable('Action') failed: %s", exc)
        is_navigating = action in ("Walk", "Run")

        # carb.Float4 stores (x, y, z, w); reorder to the scalar-first
        # quaternion convention used everywhere else in the MCP layer.
        return {
            "ok": True,
            "prim_path": prim_path,
            "position": [float(pos.x), float(pos.y), float(pos.z)],
            "rotation": [float(rot.w), float(rot.x), float(rot.y), float(rot.z)],
            "action": action,
            "is_navigating": is_navigating,
        }

    # ------------------------------------------------------------------
    # Private helpers that need access to ``self._job_service`` stay on
    # the instance; everything pure goes to module-level (below).
    # ------------------------------------------------------------------

    async def _ensure_animation_ready(
        self, skel_root_path: str, max_retries: int = 3
    ) -> Any:
        """Resolve an animation/control handle, warming it if needed.

        Isaac Sim 5.x used ``omni.anim.graph.core.get_character`` handles.
        Isaac Sim 6.0 Replicator Agent 1.x uses BehaviorAgent handles, so the
        fallback returns an adapter exposing the subset this service uses.
        """
        import omni.kit.app
        import omni.timeline

        app = omni.kit.app.get_app()

        try:
            import omni.anim.graph.core as ag

            for attempt in range(max_retries + 1):
                graph = ag.get_character(skel_root_path)
                if graph is not None:
                    return graph

                if attempt >= max_retries:
                    break

                timeline = omni.timeline.get_timeline_interface()
                try:
                    timeline.play()
                    await app.next_update_async()
                    timeline.pause()
                    await app.next_update_async()
                except Exception as exc:
                    logger.debug(
                        "animation graph warm-up failed (attempt %d): %s",
                        attempt,
                        exc,
                    )
        except ImportError:
            logger.debug("omni.anim.graph.core unavailable; trying BehaviorAgent")

        return await _ensure_behavior_agent_ready(skel_root_path, max_retries=30)


class _BehaviorAgentAdapter:
    """Compatibility adapter for Isaac Sim 6.0 BehaviorAgent handles."""

    def __init__(self, bh_agent: Any) -> None:
        self._bh_agent = bh_agent
        self._speed = 1.0
        self._action = "Idle"

    def set_variable(self, name: str, value: Any) -> None:
        import carb  # lazy

        if name == "Walk":
            self._speed = float(value)
            if hasattr(self._bh_agent, "set_speed"):
                self._bh_agent.set_speed(float(value))
            return

        if name == "Action":
            self._action = str(value)
            if self._action == "Idle" and hasattr(self._bh_agent, "idle"):
                self._bh_agent.idle()
            elif self._action not in ("Walk", "Run") and hasattr(
                self._bh_agent, "custom_action"
            ):
                _call_behavior_custom_action(self._bh_agent, self._action)
            return

        if name == "PathPoints":
            points = list(value or [])
            if not points:
                return
            target = points[-1]
            if hasattr(target, "x"):
                x, y, z = float(target.x), float(target.y), float(target.z)
            else:
                x, y, z = float(target[0]), float(target[1]), float(target[2])
            if hasattr(self._bh_agent, "set_speed"):
                self._bh_agent.set_speed(float(self._speed))
            self._bh_agent.move_to(target=carb.Float3(x, y, z))

    def get_variable(self, name: str) -> Any:
        if name != "Action":
            return None
        if hasattr(self._bh_agent, "get_action_task_id") and hasattr(
            self._bh_agent, "get_task_name"
        ):
            try:
                task_id = self._bh_agent.get_action_task_id()
                task_name = self._bh_agent.get_task_name(task_id)
                if task_name:
                    return task_name
            except Exception as exc:
                logger.debug("BehaviorAgent task-name read failed: %s", exc)
        return self._action

    def get_world_transform(self, pos: Any, rot: Any) -> None:
        world_pos = self._bh_agent.get_world_translation()
        world_rot = self._bh_agent.get_world_rotation()
        pos.x = float(world_pos.x)
        pos.y = float(world_pos.y)
        pos.z = float(world_pos.z)
        rot.x = float(world_rot.x)
        rot.y = float(world_rot.y)
        rot.z = float(world_rot.z)
        rot.w = float(world_rot.w)


def _call_behavior_custom_action(bh_agent: Any, action_name: str) -> None:
    """Call BehaviorAgent custom_action across Isaac Sim 6.0/legacy bindings."""
    try:
        bh_agent.custom_action(str(action_name))
    except TypeError:
        bh_agent.custom_action(action_name=str(action_name))


async def _ensure_behavior_agent_ready(
    skel_root_path: str,
    max_retries: int = 30,
) -> _BehaviorAgentAdapter:
    """Resolve an Isaac Sim 6.0 BehaviorAgent for *skel_root_path*."""
    import omni.anim.behavior.core as bh_core  # lazy
    import omni.kit.app
    import omni.timeline

    app = omni.kit.app.get_app()
    behavior = bh_core.acquire_interface()
    timeline = omni.timeline.get_timeline_interface()

    for attempt in range(max_retries + 1):
        bh_agent = behavior.get_agent(skel_root_path)
        if bh_agent is not None:
            return _BehaviorAgentAdapter(bh_agent)

        if attempt >= max_retries:
            break
        try:
            timeline.play()
            await app.next_update_async()
        except Exception as exc:
            logger.debug(
                "BehaviorAgent warm-up failed (attempt %d): %s", attempt, exc
            )

    raise ValueError(
        f"BehaviorAgent handle not available for {skel_root_path} after "
        "warm-up; ensure character_load succeeded and timeline can play."
    )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions; no access to self).
# ---------------------------------------------------------------------------

def _parse_variant(variant: str) -> tuple[str, str | None, str]:
    """Split *variant* into (base_action, style_variable, style_value).

    Examples:
        ``SitReading`` → (``"Sit"``, ``"sit_style"``, ``"reading"``)
        ``WalkFast``   → (``"Walk"``, ``"walk_style"``, ``"fast"``)
        ``Idle``       → (``"Idle"``, None, "")
    """
    for base in ("Sit", "Walk", "Run", "Idle"):
        if variant == base:
            return (base, None, "")
        if variant.startswith(base):
            tail = variant[len(base):]
            if not tail:
                return (base, None, "")
            style_var = f"{base.lower()}_style"
            style_value = tail.lower()
            return (base, style_var, style_value)
    # Unknown prefix — treat variant as bare Action token
    return (variant, None, "")


def _layout_positions(
    layout: str, count: int, spacing: float, center: list[float],
) -> list[list[float]]:
    """Compute per-character positions for a crowd layout."""
    import math
    import random

    cx, cy, cz = (float(center[0]), float(center[1]), float(center[2]))
    positions: list[list[float]] = []

    if layout == "grid":
        cols = max(1, int(math.ceil(math.sqrt(count))))
        for i in range(count):
            row = i // cols
            col = i % cols
            x = cx + (col - (cols - 1) / 2.0) * spacing
            y = cy + (row - (cols - 1) / 2.0) * spacing
            positions.append([x, y, cz])
    elif layout == "line":
        for i in range(count):
            x = cx + (i - (count - 1) / 2.0) * spacing
            positions.append([x, cy, cz])
    elif layout == "random":
        side = spacing * max(1.0, math.sqrt(count))
        rng = random.Random(0)  # deterministic for tests
        for _ in range(count):
            x = cx + rng.uniform(-side / 2.0, side / 2.0)
            y = cy + rng.uniform(-side / 2.0, side / 2.0)
            positions.append([x, y, cz])
    else:
        raise ValueError(f"Unknown layout: {layout}")
    return positions


def _sanitize_prim_name(name: str) -> str:
    """Normalise a raw string (e.g. UUID filename) into a USD-safe prim name.

    USD allows ``[A-Za-z0-9_]`` and forbids a leading digit. Non-alnum chars
    collapse to ``_``; we prepend ``c_`` if the result still starts with a
    digit (testbed #15 — UUID filenames like ``1344c2cb-...``).
    """
    sanitized = "".join(
        c if (c.isalnum() or c == "_") else "_" for c in name
    )
    if sanitized and sanitized[0].isdigit():
        sanitized = "c_" + sanitized
    return sanitized or "character"


def _find_skel_root(stage: Any, root_path: str) -> str | None:
    """Return the first ``SkelRoot`` path under *root_path*, or None.

    ``Usd.PrimRange`` is used so deep layouts (``DHGen/SkelRoot``) resolve
    without a hardcoded path suffix.
    """
    from pxr import Usd  # lazy

    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim.IsValid():
        return None
    for p in Usd.PrimRange(root_prim):
        if p.GetTypeName() == "SkelRoot":
            return str(p.GetPath())
    return None


def _assert_skel_root(prim_path: str) -> str:
    """Raise ``ValueError`` if no ``SkelRoot`` exists at/under *prim_path*.

    Returns the resolved SkelRoot path on success. Mirrors
    :func:`robot_service._assert_articulation` — the silent no-op case
    (prim present but wrong type) is a known source of fake-green tests.
    """
    import omni.usd  # lazy

    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("No USD stage available")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise ValueError(f"Prim not found at {prim_path}")

    if prim.GetTypeName() == "SkelRoot":
        return prim_path

    found = _find_skel_root(stage, prim_path)
    if found is None:
        raise ValueError(
            f"No SkelRoot found at or under {prim_path} — "
            "call character_load first (or pass a SkelRoot prim path)."
        )
    return found


async def _ensure_motion_library(stage: Any) -> str:
    """Create the shared Isaac Sim 6.0 human motion library payload."""
    import omni.kit.commands  # lazy
    import omni.usd
    from pxr import UsdGeom

    if stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        return _MOTION_LIBRARY_PATH

    if not stage.GetPrimAtPath(_CHARS_ROOT).IsValid():
        UsdGeom.Xform.Define(stage, _CHARS_ROOT)

    motion_library_url = _resolve_human_motion_library_url()
    omni.kit.commands.execute(
        "CreatePayloadCommand",
        usd_context=omni.usd.get_context(),
        path_to=_MOTION_LIBRARY_PATH,
        asset_path=motion_library_url,
        prim_path=None,
        instanceable=False,
        select_prim=False,
    )
    await _wait_stage_loading()

    if not stage.GetPrimAtPath(_MOTION_LIBRARY_PATH).IsValid():
        raise RuntimeError(
            f"Human motion library payload failed at {_MOTION_LIBRARY_PATH} "
            f"(url={motion_library_url})"
        )
    return _MOTION_LIBRARY_PATH


def _resolve_human_motion_library_url() -> str:
    """Return the Replicator Agent 1.x default human motion library URL."""
    try:
        from omni.metropolis.utils.carb_util import get_value_by_key

        setting_value = get_value_by_key(
            "/exts/isaacsim.replicator.agent/default_human_motion_library_asset"
        )
        if setting_value:
            return str(setting_value)
    except Exception as exc:
        logger.debug("motion library setting lookup failed: %s", exc)

    from isaacsim.storage.native import get_assets_root_path  # lazy

    assets_root = get_assets_root_path()
    if not assets_root:
        raise RuntimeError(
            "Isaac Sim assets root not resolved — cannot derive "
            "HumanMotionLibrary.usd URL."
        )
    return (
        f"{assets_root.rstrip('/')}/Isaac/People/MotionLibrary/"
        "HumanMotionLibrary.usd"
    )


async def _apply_ira_character_apis(
    stage: Any,
    skel_root_path: str,
    motion_library_path: str,
) -> None:
    """Apply Isaac Sim 6.0 BehaviorAgent + IRA character APIs."""
    import omni.kit.app
    import omni.kit.commands

    skel_prim = stage.GetPrimAtPath(skel_root_path)
    if not skel_prim.IsValid():
        raise ValueError(f"SkelRoot prim is invalid: {skel_root_path}")

    omni.kit.commands.execute(
        "ApplyBehaviorAgentAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
        motion_library_prim_path=motion_library_path,
        motion_library_skeleton_rig="Human",
    )
    await omni.kit.app.get_app().next_update_async()

    omni.kit.commands.execute(
        "ApplyIRACharacterAPICommand",
        skelroot_prim_paths=[skel_prim.GetPath()],
    )
    await omni.kit.app.get_app().next_update_async()


async def _wait_stage_loading(max_frames: int = 300) -> None:
    """Wait until all USD references in the Stage have finished loading."""
    import omni.kit.app  # lazy

    app = omni.kit.app.get_app()
    for _ in range(max_frames):
        await app.next_update_async()
        if not _is_stage_loading():
            return


def _is_stage_loading() -> bool:
    try:
        from isaacsim.core.experimental.utils.stage import is_stage_loading
        return is_stage_loading()
    except ImportError:
        try:
            import omni.usd
            ctx = omni.usd.get_context()
            _, files_loaded, total_files = ctx.get_stage_loading_status()
            return total_files > 0 and files_loaded < total_files
        except Exception:
            return False


def _rotate_vec_by_quat_wxyz(
    v: tuple[float, float, float],
    q_wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    """Rotate vector v by unit quaternion (w, x, y, z). No numpy required."""
    w, x, y, z = q_wxyz
    vx, vy, vz = v
    # t = 2 * (q_xyz × v)
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


async def _navigate_coro(
    service: CharacterService,
    prim_path: str,
    target: list[float],
    speed: float,
    update_progress,
) -> dict[str, Any]:
    """Drive a character to *target* by poking the AnimationGraph + polling.

    Flow:
        1. Issue ``play_animation(Walk, target, speed)`` to push PathPoints
           into the graph.
        2. Loop: every ``_NAV_POLL_FRAMES`` frames read the world transform,
           compute XY distance to target; exit when under ``_NAV_ARRIVAL_M``.
        3. Hard cap at ``_NAV_TIMEOUT_S`` seconds.
        4. Flip back to Idle so the character stops on arrival.
    """
    import carb  # lazy
    import omni.kit.app

    app = omni.kit.app.get_app()

    # Step 1: kick off walking.
    await service.play_animation(
        {
            "prim_path": prim_path,
            "animation_name": "Walk",
            "speed": speed,
            "target_position": list(target),
        }
    )

    # Step 2: poll for arrival.
    skel_root_path = _assert_skel_root(prim_path)
    graph = await service._ensure_animation_ready(skel_root_path)

    start_time = time.monotonic()
    tx, ty = float(target[0]), float(target[1])

    total_dist = None
    frame_count = 0
    final_pos = [0.0, 0.0, 0.0]

    # Seed progress at 0.0 so the "already at target" edge case (review
    # finding C3) still surfaces a valid value even if the loop exits on
    # the very first iteration via the arrival branch.
    update_progress(0.0)

    try:
        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= _NAV_TIMEOUT_S:
                logger.warning(
                    "navigate_to timeout (%.1fs) before reaching target %s",
                    elapsed, target,
                )
                break

            pos = carb.Float3(0.0, 0.0, 0.0)
            rot = carb.Float4(0.0, 0.0, 0.0, 0.0)
            graph.get_world_transform(pos, rot)
            final_pos = [float(pos.x), float(pos.y), float(pos.z)]

            dx = tx - pos.x
            dy = ty - pos.y
            dist = (dx * dx + dy * dy) ** 0.5
            if total_dist is None:
                # Clamp to _NAV_ARRIVAL_M so the progress formula stays
                # defined even for near-zero initial distance (C3).
                total_dist = max(dist, _NAV_ARRIVAL_M)
            if total_dist and total_dist > 0.0:
                update_progress(max(0.0, min(1.0, 1.0 - dist / total_dist)))

            if dist < _NAV_ARRIVAL_M:
                update_progress(1.0)
                break

            # Advance the sim — we'd starve the job_service cleanup task
            # otherwise, and the AnimationGraph wouldn't tick.
            for _ in range(_NAV_POLL_FRAMES):
                await app.next_update_async()
            frame_count += _NAV_POLL_FRAMES

            # Yield once more to let the cancel() path trigger cleanly.
            await asyncio.sleep(0)
    finally:
        # Step 4: stop the character on arrival / timeout / cancel.
        # This MUST run even when asyncio.CancelledError propagates out of
        # the poll loop above (review finding C2) — otherwise the character
        # keeps walking toward the now-stale target. The stop call itself
        # is best-effort: the job is already terminating, so a secondary
        # error here should not mask the original exit reason.
        try:
            await service.stop_animation({"prim_path": prim_path})
        except Exception as exc:
            logger.debug(
                "stop_animation after navigate failed (non-fatal): %s", exc
            )

    return {
        "prim_path": prim_path,
        "final_position": final_pos,
        "target": [float(v) for v in target],
        "elapsed_s": time.monotonic() - start_time,
        "frames": frame_count,
    }
