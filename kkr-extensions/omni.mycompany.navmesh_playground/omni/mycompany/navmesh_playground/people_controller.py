"""People controller — Walk→Sit FSM, fully standalone (no validation_api).

Drives an Isaac Sim 6.0 Replicator Agent character via the BehaviorAgent
adapter bound by `usd_loader.safe_spawn_character_sync`. Variable contract
keeps a legacy-compatible variable surface:

  - ``Action`` (token)              — "Walk" / "Sit" / "Idle" / "Run"
  - ``Walk`` (float)                — Walk/Run blend speed (0..1+)
  - ``PathPoints`` (Float3[])       — start + target waypoints; Walk/Run only
  - ``sit_style`` (token, optional) — "idle" / "talk" / "reading" — silently
                                       no-op if the variant is not wired
  - ``SitWeight`` (float, optional) — 0..1 blend; **must be 1.0** when
                                       Action=Sit otherwise the character
                                       stays standing inside the Sit state

Critical: the warm-up loop here NEVER pauses the timeline (the prior
validation_api code path called timeline.play()/pause() to register the
character, which left the user staring at a paused sim after one Go
click — the second click then "worked" because warm-up was already done).
"""
from __future__ import annotations

import asyncio
import math
import random
import time

import carb
import omni.kit.async_engine

from .agent_manager import AgentManager, AgentRecord
from .navmesh_sampler import query_shortest_path


SKIN_POOL = [
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/People/Characters/F_Business_02/F_Business_02.usd",
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/People/Characters/F_Medical_01/F_Medical_01.usd",
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/People/Characters/M_Medical_01/M_Medical_01.usd",
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/People/Characters/male_adult_construction_05_new/male_adult_construction_05_new.usd",
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/People/Characters/male_adult_police_04/male_adult_police_04.usd",
]


class PeopleController:

    def __init__(self, agent_manager: AgentManager) -> None:
        self._agent_manager = agent_manager
        self._tasks: dict[str, asyncio.Task] = {}
        self._rng = random.Random()

    # ------------------------------------------------------------------
    # Lifecycle (panel buttons call these)
    # ------------------------------------------------------------------

    def go(self, agent: AgentRecord) -> None:
        """Start Walk → Sit FSM. Re-click cancels prior task."""
        prior = self._tasks.pop(agent.id, None)
        if prior and not prior.done():
            prior.cancel()
        agent.state = "Walking"
        agent.state_detail = ""
        fut = omni.kit.async_engine.run_coroutine(self._walk_then_sit(agent))
        task = asyncio.ensure_future(asyncio.wrap_future(fut))
        self._tasks[agent.id] = task

    def stop(self, agent: AgentRecord) -> None:
        t = self._tasks.pop(agent.id, None)
        if t and not t.done():
            t.cancel()
        # Switch character to Idle in-place (no timeline pause).
        try:
            char = _get_anim_character(
                agent.skel_root_path or agent.prim_path, max_wait_s=0.2,
            )
            if char is not None:
                char.set_variable("Action", "Idle")
                char.set_variable("Walk", 0.0)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[navmesh_playground] stop_anim soft-fail: {exc}")
        agent.state = "Stopped"

    def remove(self, agent: AgentRecord) -> None:
        self.stop(agent)
        # DeletePrim on the parent payload — cascades to SkelRoot + meshes.
        try:
            import omni.kit.commands
            omni.kit.commands.execute("DeletePrims", paths=[agent.prim_path])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[navmesh_playground] delete_prim failed: {exc}")
        self._agent_manager.remove(agent.id)

    # ------------------------------------------------------------------
    # FSM — Walk → arrival → Sit
    # ------------------------------------------------------------------

    async def _walk_then_sit(self, agent: AgentRecord) -> None:
        try:
            import omni.kit.app
            import omni.timeline
            app = omni.kit.app.get_app()
            tl = omni.timeline.get_timeline_interface()

            # Ensure timeline playing — character runtime only ticks while playing.
            # We deliberately do NOT pause-then-play (the validation_api
            # path's _ensure_animation_ready did that, leaving the timeline
            # paused and forcing the user to click Go twice).
            if not tl.is_playing():
                tl.play()

            target_skel = agent.skel_root_path or agent.prim_path
            char = await _await_anim_character(target_skel, app, max_wait_frames=300)
            if char is None:
                agent.state = "Error"
                agent.state_detail = "Character runtime handle unavailable"
                return

            # Yield several frames so the runtime world transform has
            # populated with the actual character position.
            cur_p = carb.Float3(0.0, 0.0, 0.0)
            cur_r = carb.Float4(0.0, 0.0, 0.0, 0.0)
            for _ in range(10):
                await app.next_update_async()
                char.get_world_transform(cur_p, cur_r)
                if abs(cur_p.x) > 1e-3 or abs(cur_p.y) > 1e-3:
                    break

            start_x = float(cur_p.x) if abs(cur_p.x) > 1e-3 else float(agent.start[0])
            start_y = float(cur_p.y) if abs(cur_p.y) > 1e-3 else float(agent.start[1])
            start_z = float(cur_p.z)

            # Query NavMesh shortest path from current position to goal.
            # PathPoints with only [start, goal] can make legacy character
            # runtimes walk in a straight line, ignoring obstacles like rack /
            # shelving. Pushing the full NavMesh waypoint list teaches the
            # runtime to route around them. Falls back to direct line
            # only if NavMesh has no path (e.g., goal in unreachable area).
            path_pts = _query_navmesh_path(
                (start_x, start_y, start_z),
                (float(agent.goal[0]), float(agent.goal[1]), float(agent.goal[2])),
            )
            if not path_pts:
                # Fallback — Biped walks straight, may pass through props.
                path_pts = [
                    (start_x, start_y, start_z),
                    (float(agent.goal[0]), float(agent.goal[1]), float(agent.goal[2])),
                ]
                carb.log_warn(
                    f"[navmesh_playground] {agent.id}: NavMesh path query "
                    "returned empty; falling back to straight line."
                )

            char.set_variable("Action", "Walk")
            char.set_variable("Walk", 1.0)
            char.set_variable(
                "PathPoints",
                [carb.Float3(p[0], p[1], p[2]) for p in path_pts],
            )

            # Poll character world position until arrival.
            arrival_tol = float(agent.arrival_tol)
            max_seconds = 60.0
            tick_dt = 1.0 / 60.0
            max_ticks = int(max_seconds / tick_dt)
            arrived = False
            last_pos = (0.0, 0.0, 0.0)
            for tick in range(max_ticks):
                await app.next_update_async()
                # Sample every 10 frames (~166 ms) to keep CPU light.
                if tick % 10 != 0:
                    continue
                char.get_world_transform(cur_p, cur_r)
                last_pos = (float(cur_p.x), float(cur_p.y), float(cur_p.z))
                d = math.hypot(
                    agent.goal[0] - last_pos[0], agent.goal[1] - last_pos[1],
                )
                if d < arrival_tol:
                    arrived = True
                    break

            if not arrived:
                agent.state = "Error"
                agent.state_detail = "walk timeout"
                return

            # Sit transition. Order:
            #   Action=Idle (brief stop) → Action=Sit + sit_style + SitWeight=1.0
            char.set_variable("Action", "Idle")
            char.set_variable("Walk", 0.0)
            await asyncio.sleep(0.05)

            base, style_var, style_val = _parse_sit_variant(agent.sit_variant)
            char.set_variable("Action", base)
            if style_var:
                try:
                    char.set_variable(style_var, style_val)
                except Exception as exc:  # noqa: BLE001
                    # Style not wired in this character's runtime — base
                    # action still runs.
                    carb.log_info(
                        f"[navmesh_playground] sit style {style_var}={style_val} "
                        f"not wired (non-fatal): {exc}",
                    )
            if base == "Sit":
                # Without SitWeight=1.0 legacy Sit blend trees
                # stays at standing pose — this is the most common
                # "Sit doesn't visually engage" failure mode.
                try:
                    char.set_variable("SitWeight", 1.0)
                except Exception as exc:  # noqa: BLE001
                    carb.log_info(
                        f"[navmesh_playground] SitWeight not wired (non-fatal): {exc}",
                    )

            agent.state = "Sitting"
            agent.state_detail = agent.sit_variant
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] walk_then_sit failed: {exc}")
            agent.state = "Error"
            agent.state_detail = str(exc)


# ---------------------------------------------------------------------------
# Helpers (module-level)
# ---------------------------------------------------------------------------

class _BehaviorAgentAdapter:
    """Legacy variable-surface adapter over Isaac Sim 6.0 BehaviorAgent."""

    def __init__(self, bh_agent) -> None:
        self._bh_agent = bh_agent
        self._speed = 1.0
        self._action = "Idle"

    def set_variable(self, name: str, value) -> None:
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
                self._bh_agent.custom_action(action_name=self._action)
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

    def get_world_transform(self, pos, rot) -> None:
        world_pos = self._bh_agent.get_world_translation()
        world_rot = self._bh_agent.get_world_rotation()
        pos.x = float(world_pos.x)
        pos.y = float(world_pos.y)
        pos.z = float(world_pos.z)
        rot.x = float(world_rot.x)
        rot.y = float(world_rot.y)
        rot.z = float(world_rot.z)
        rot.w = float(world_rot.w)


def _get_anim_character(skel_root_path: str, max_wait_s: float = 0.0):
    """Return a legacy AnimGraph handle or BehaviorAgent adapter, or None.

    Sync version — used by stop()/remove() where blocking briefly is OK.
    Pass `max_wait_s > 0` to retry with `time.sleep` between probes (does
    not advance Kit frames).
    """
    try:
        import omni.anim.graph.core as ag
    except ImportError:
        ag = None
    char = ag.get_character(skel_root_path) if ag is not None else None
    if char is None:
        char = _get_behavior_agent_adapter(skel_root_path)
    if char is not None or max_wait_s <= 0:
        return char
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        time.sleep(0.05)
        char = ag.get_character(skel_root_path) if ag is not None else None
        if char is None:
            char = _get_behavior_agent_adapter(skel_root_path)
        if char is not None:
            return char
    return None


def _get_behavior_agent_adapter(skel_root_path: str):
    try:
        import omni.anim.behavior.core as bh_core
    except ImportError:
        return None
    bh_agent = bh_core.acquire_interface().get_agent(skel_root_path)
    if bh_agent is None:
        return None
    return _BehaviorAgentAdapter(bh_agent)


async def _await_anim_character(skel_root_path: str, app, max_wait_frames: int = 300):
    """Async wait for a legacy AnimGraph/BehaviorAgent character to register.

    The registration scan only runs while the timeline is ticking. Leave the
    timeline playing for Walk/MoveTo to drive motion.
    """
    try:
        import omni.anim.graph.core as ag
    except ImportError:
        ag = None
    import omni.timeline
    tl = omni.timeline.get_timeline_interface()
    was_playing = tl.is_playing()
    warmup_attempts = 5  # play→pause cycles
    frames_per_poll = max(1, max_wait_frames // (warmup_attempts + 1))
    for attempt in range(warmup_attempts):
        char = ag.get_character(skel_root_path) if ag is not None else None
        if char is None:
            char = _get_behavior_agent_adapter(skel_root_path)
        if char is not None:
            # Restore playing state — caller (caller of caller) wants
            # timeline ticking for the Walk variable to drive motion.
            if was_playing and not tl.is_playing():
                tl.play()
            return char
        # Force a play → 1 tick → pause cycle so the plugin scans new
        # prims with AnimationGraphAPI applied.
        if not tl.is_playing():
            tl.play()
        for _ in range(frames_per_poll):
            await app.next_update_async()
    # Final attempt — and ensure we leave timeline playing for Walk
    char = ag.get_character(skel_root_path) if ag is not None else None
    if char is None:
        char = _get_behavior_agent_adapter(skel_root_path)
    if not tl.is_playing():
        tl.play()
    return char


def _query_navmesh_path(
    start: tuple[float, float, float],
    goal: tuple[float, float, float],
    agent_radius: float = 0.25,
    agent_height: float = 1.0,
) -> list[tuple[float, float, float]]:
    """Return baked-NavMesh shortest-path waypoints between start and goal.

    Returns ``[]`` if NavMesh is not baked, query API is unavailable, or
    no path exists between the points. Caller is expected to substitute
    a straight-line fallback in that case.
    """
    try:
        import omni.anim.navigation.core as nav
    except ImportError:
        return []
    iface = nav.acquire_interface()
    mesh = iface.get_navmesh()
    if mesh is None:
        return []
    try:
        path = query_shortest_path(
            mesh,
            start,
            goal,
            agent_radius=agent_radius,
            agent_height=agent_height,
            straighten=True,
        )
    except Exception as exc:  # noqa: BLE001
        carb.log_warn(f"[navmesh_playground] query_shortest_path: {exc}")
        return []
    if path is None:
        return []
    raw = path.get_points() or []
    return [(float(p.x), float(p.y), float(p.z)) for p in raw]


def _parse_sit_variant(variant: str) -> tuple[str, str | None, str]:
    """Split ``"SitReading"`` → ``("Sit", "sit_style", "reading")``.

    Bare "Sit" → ("Sit", None, ""); unknown prefix → (variant, None, "").
    Mirrors validation_api's _parse_variant but inlined here so this
    extension stays standalone.
    """
    for base in ("Sit", "Walk", "Run", "Idle"):
        if variant == base:
            return (base, None, "")
        if variant.startswith(base):
            tail = variant[len(base):]
            if not tail:
                return (base, None, "")
            return (base, f"{base.lower()}_style", tail.lower())
    return (variant, None, "")
