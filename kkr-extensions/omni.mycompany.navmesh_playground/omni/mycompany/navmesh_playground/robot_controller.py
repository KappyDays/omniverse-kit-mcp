"""Robot controller — NavMesh path query + DifferentialController drive.

Fully standalone — no validation_api import. Uses Kit / Isaac Sim 5.1
SDK directly:

  - ``omni.anim.navigation.core``                — NavMesh path query
  - ``isaacsim.robot.wheeled_robots.controllers``
        ``.differential_controller.DifferentialController`` — wheel kinematics
  - ``isaacsim.core.prims.SingleArticulation``   — joint velocity write
  - ``isaacsim.core.utils.types.ArticulationAction``

S-curve fix (2026-04-23 user-reported): previous tuning had
``lookahead=0.8`` m on a Nova Carter (wheel_base=0.413 m) which is too
short — Pure Pursuit oversteers and the robot weaves. New defaults:

  - ``lookahead = max(1.5, wheel_base * 4)`` — at least 4 wheelbases ahead
  - Yaw deadzone (3°) — small heading errors do not steer
  - Tiered linear/angular damping with smooth transitions (no `2*yaw`
    jump at 0° that caused the fan-shape oscillation)
"""
from __future__ import annotations

import asyncio
import math
import random
import time

import carb
import omni.kit.async_engine

from .agent_manager import AgentManager, AgentRecord


ROBOT_POOL = [
    # (display name, S3 URL, wheel_radius, wheel_base) — Nova Carter spec defaults
    ("NovaCarter",
     "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/Robots/NVIDIA/NovaCarter/nova_carter.usd",
     0.14, 0.413),
    ("Jetbot",
     "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd",
     0.03, 0.1),
]


class RobotController:

    def __init__(self, agent_manager: AgentManager) -> None:
        self._agent_manager = agent_manager
        self._tasks: dict[str, asyncio.Task] = {}
        self._rng = random.Random()

    # ------------------------------------------------------------------
    # Lifecycle (panel buttons call these)
    # ------------------------------------------------------------------

    def go(self, agent: AgentRecord) -> None:
        prior = self._tasks.pop(agent.id, None)
        if prior and not prior.done():
            prior.cancel()
        agent.state = "Driving"
        agent.state_detail = ""
        fut = omni.kit.async_engine.run_coroutine(self._drive(agent))
        task = asyncio.ensure_future(asyncio.wrap_future(fut))
        self._tasks[agent.id] = task

    def stop(self, agent: AgentRecord) -> None:
        t = self._tasks.pop(agent.id, None)
        if t and not t.done():
            t.cancel()
        agent.state = "Stopped"
        # Brake wheels via direct articulation write (best-effort).
        try:
            self._brake_wheels(agent.prim_path)
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[navmesh_playground] brake_wheels soft-fail: {exc}")

    def remove(self, agent: AgentRecord) -> None:
        self.stop(agent)
        try:
            import omni.kit.commands
            omni.kit.commands.execute("DeletePrims", paths=[agent.prim_path])
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[navmesh_playground] delete_prim failed: {exc}")
        self._agent_manager.remove(agent.id)

    # ------------------------------------------------------------------
    # Drive coroutine
    # ------------------------------------------------------------------

    async def _drive(self, agent: AgentRecord) -> None:
        try:
            import omni.kit.app
            import omni.timeline
            app = omni.kit.app.get_app()
            tl = omni.timeline.get_timeline_interface()

            if not tl.is_playing():
                tl.play()
                # Articulation initialisation needs at least one PhysX
                # step after play() — yield a few frames so PhysX can
                # populate the view.
                for _ in range(10):
                    await app.next_update_async()

            # 1. Query NavMesh path (omni.anim.navigation.core direct).
            waypoints = self._query_path(agent)
            user_goal_xy = (float(agent.goal[0]), float(agent.goal[1]))
            path_truncation_m = 0.0
            if len(waypoints) < 2:
                # Straight-line fallback (NavMesh unbaked or unreachable).
                waypoints = [list(agent.start), list(agent.goal)]
                carb.log_warn(
                    f"[navmesh_playground] {agent.id}: NavMesh path empty, "
                    "falling back to straight line (may collide)."
                )
            else:
                # NavMesh may have truncated the path at the closest reachable
                # point. If the user's goal is far from the last waypoint,
                # the robot will appear to "stop in the middle". Append the
                # user goal so Pure Pursuit drives all the way through, but
                # also log the truncation for diagnostics.
                last = waypoints[-1]
                path_truncation_m = math.hypot(
                    user_goal_xy[0] - float(last[0]),
                    user_goal_xy[1] - float(last[1]),
                )
                if path_truncation_m > float(agent.arrival_tol):
                    waypoints.append(
                        [user_goal_xy[0], user_goal_xy[1], float(last[2])],
                    )
                    carb.log_warn(
                        f"[navmesh_playground] {agent.id}: NavMesh path ends "
                        f"{path_truncation_m:.2f} m short of user goal — "
                        "extending with straight segment to user goal."
                    )

            # 2. Init articulation + DifferentialController.
            try:
                from isaacsim.robot.wheeled_robots.controllers.differential_controller import (
                    DifferentialController,
                )
            except ImportError:
                from omni.isaac.wheeled_robots.controllers.differential_controller import (  # type: ignore
                    DifferentialController,
                )
            try:
                from isaacsim.core.utils.types import ArticulationAction
            except ImportError:
                from omni.isaac.core.utils.types import ArticulationAction  # type: ignore
            from isaacsim.core.prims import SingleArticulation

            art = SingleArticulation(agent.prim_path)
            try:
                art.initialize()
            except Exception as exc:  # noqa: BLE001
                # Re-init is harmless; bare init may already have run.
                carb.log_info(
                    f"[navmesh_playground] art.initialize() soft-fail (likely "
                    f"already inited): {exc}",
                )

            dof_names = list(art.dof_names or [])
            left_idx, right_idx = _resolve_wheel_dofs(dof_names)
            if left_idx is None or right_idx is None:
                agent.state = "Error"
                agent.state_detail = (
                    f"wheel DOF not resolved (dof_names={dof_names})"
                )
                return
            num_dof = int(art.num_dof)

            ctrl = DifferentialController(
                name=f"navmesh_drive_{agent.id}",
                wheel_radius=float(agent.wheel_radius),
                wheel_base=float(agent.wheel_base),
            )

            path_2d = [(float(p[0]), float(p[1])) for p in waypoints]
            # Lookahead: at minimum 1.5 m, scaled with wheel_base. Short
            # lookahead → Pure Pursuit oversteers → S-curve / fan motion
            # (the user-reported regression).
            lookahead = max(1.5, float(agent.wheel_base) * 4.0)
            yaw_deadzone = math.radians(3.0)

            import numpy as np  # lazy

            start_t = time.monotonic()
            # Estimate timeout from path length / v_max with 3x safety margin —
            # warehouse paths up to ~30 m + Jetbot at 0.3 m/s would otherwise
            # exceed the prior fixed 60 s cap.
            est_path_len = sum(
                math.hypot(
                    float(waypoints[i + 1][0]) - float(waypoints[i][0]),
                    float(waypoints[i + 1][1]) - float(waypoints[i][1]),
                )
                for i in range(len(waypoints) - 1)
            )
            timeout_s = max(60.0, 3.0 * est_path_len / max(0.05, float(agent.v_max)))
            arrival_tol = float(agent.arrival_tol)
            ticks = 0
            reached = False
            final_distance = float("inf")

            try:
                while time.monotonic() - start_t < timeout_s:
                    pos, orient = art.get_world_pose()
                    pos_xy = (float(pos[0]), float(pos[1]))
                    goal_xy = path_2d[-1]
                    d_goal = math.hypot(
                        goal_xy[0] - pos_xy[0], goal_xy[1] - pos_xy[1],
                    )
                    final_distance = d_goal
                    if d_goal < arrival_tol:
                        reached = True
                        break

                    tx, ty = _pure_pursuit_target(pos_xy, path_2d, lookahead)
                    yaw = _quat_yaw_wxyz(orient)
                    yaw_e = _wrap_pi(
                        math.atan2(ty - pos_xy[1], tx - pos_xy[0]) - yaw,
                    )
                    yaw_abs = abs(yaw_e)

                    # Tiered controller — designed to avoid the previous
                    # `ang = 2 * yaw_e` discontinuity that caused S-curve
                    # weaving when crossing the heading axis.
                    if yaw_abs < yaw_deadzone:
                        ang = 0.0
                        lin = float(agent.v_max)
                    elif yaw_abs < math.radians(15):
                        ang = yaw_e * 1.0
                        lin = float(agent.v_max)
                    elif yaw_abs < math.radians(45):
                        ang = yaw_e * 1.5
                        lin = float(agent.v_max) * 0.7
                    elif yaw_abs < math.radians(90):
                        ang = yaw_e * 2.0
                        lin = float(agent.v_max) * 0.35
                    else:
                        # Beyond 90°: rotate in place + creep forward.
                        ang = math.copysign(float(agent.w_max), yaw_e)
                        lin = 0.15

                    ang = float(np.clip(ang, -float(agent.w_max), float(agent.w_max)))

                    wv = ctrl.forward([lin, ang])
                    if hasattr(wv, "joint_velocities") and wv.joint_velocities is not None:
                        jv = np.asarray(wv.joint_velocities, dtype=np.float32)
                    else:
                        jv = np.asarray(wv, dtype=np.float32)
                    vels = np.zeros(num_dof, dtype=np.float32)
                    vels[left_idx] = float(jv.flat[0])
                    vels[right_idx] = float(jv.flat[1])
                    art.apply_action(ArticulationAction(joint_velocities=vels))

                    ticks += 1
                    await app.next_update_async()
            finally:
                # Always brake on exit (cancel / timeout / arrival / except).
                try:
                    zeros = np.zeros(num_dof, dtype=np.float32)
                    art.apply_action(ArticulationAction(joint_velocities=zeros))
                except Exception as exc:  # noqa: BLE001
                    carb.log_warn(
                        f"[navmesh_playground] zero-on-exit failed: {exc}",
                    )

            agent.state = "Idle"
            if reached:
                # Distinguish "reached the user goal" from "reached the
                # NavMesh-truncated path end" so the user knows whether
                # the requested destination was actually achieved.
                d_user = math.hypot(
                    user_goal_xy[0] - pos_xy[0], user_goal_xy[1] - pos_xy[1],
                )
                if d_user < arrival_tol:
                    agent.state_detail = "arrived"
                else:
                    agent.state_detail = (
                        f"reached path end (NavMesh truncated "
                        f"{path_truncation_m:.2f}m short of user goal; "
                        f"current distance to goal {d_user:.2f}m)"
                    )
            else:
                agent.state_detail = (
                    f"timeout {timeout_s:.0f}s (final distance to path end "
                    f"{final_distance:.2f}m, {ticks} ticks, "
                    f"path_len {est_path_len:.1f}m, v_max {agent.v_max} m/s)"
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[navmesh_playground] _drive failed: {exc}")
            agent.state = "Error"
            agent.state_detail = str(exc)

    # ------------------------------------------------------------------
    # Helpers (instance-level — depend on agent state)
    # ------------------------------------------------------------------

    def _query_path(self, agent: AgentRecord) -> list[list[float]]:
        """Query NavMesh shortest path. Returns [] on failure."""
        try:
            import omni.anim.navigation.core as nav
        except ImportError:
            return []
        iface = nav.acquire_interface()
        mesh = iface.get_navmesh()
        if mesh is None:
            return []
        try:
            path = mesh.query_shortest_path(
                carb.Float3(*agent.start),
                carb.Float3(*agent.goal),
                agent_radius=0.25,
                agent_height=1.0,
                straighten=True,
            )
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[navmesh_playground] query_shortest_path: {exc}")
            return []
        if path is None:
            return []
        raw = path.get_points() or []
        return [[float(p.x), float(p.y), float(p.z)] for p in raw]

    def _brake_wheels(self, prim_path: str) -> None:
        """Zero the wheel velocities — best-effort. Used by stop()."""
        try:
            from isaacsim.core.prims import SingleArticulation
            try:
                from isaacsim.core.utils.types import ArticulationAction
            except ImportError:
                from omni.isaac.core.utils.types import ArticulationAction  # type: ignore
            import numpy as np
            art = SingleArticulation(prim_path)
            try:
                art.initialize()
            except Exception:  # noqa: BLE001 — already initialised
                pass
            n = int(art.num_dof)
            art.apply_action(ArticulationAction(
                joint_velocities=np.zeros(n, dtype=np.float32),
            ))
        except Exception:  # noqa: BLE001 — silent best-effort
            pass


# ---------------------------------------------------------------------------
# Helpers (module-level, pure functions)
# ---------------------------------------------------------------------------


def _resolve_wheel_dofs(dof_names: list[str]) -> tuple[int | None, int | None]:
    """Match left / right wheel indices by name substring scan.

    Nova Carter / Jetbot use names like 'joint_wheel_left' or
    'wheel_left_joint'. Unknown chassis → returns (None, None) and the
    caller surfaces an error.
    """
    low = [n.lower() for n in dof_names]

    def _find(patterns: list[str]) -> int | None:
        for p in patterns:
            for i, n in enumerate(low):
                if p in n:
                    return i
        return None

    return (
        _find(["wheel_left", "left_wheel", "joint_wheel_left"]),
        _find(["wheel_right", "right_wheel", "joint_wheel_right"]),
    )


def _pure_pursuit_target(
    pos_xy: tuple[float, float],
    path_2d: list[tuple[float, float]],
    lookahead: float,
) -> tuple[float, float]:
    """Find a point ~`lookahead` metres ahead of `pos_xy` on `path_2d`."""
    if len(path_2d) < 2:
        return path_2d[-1]

    # Nearest segment to current position.
    best_i, best_d = 0, float("inf")
    for i in range(len(path_2d) - 1):
        d = _seg_dist(pos_xy, path_2d[i], path_2d[i + 1])
        if d < best_d:
            best_d, best_i = d, i

    # Walk forward from nearest segment until cumulative reach == lookahead.
    remaining = lookahead
    cur = pos_xy
    for j in range(best_i, len(path_2d) - 1):
        ax, ay = path_2d[j]
        bx, by = path_2d[j + 1]
        sx, sy = bx - ax, by - ay
        seg_len = math.hypot(sx, sy)
        if seg_len < 1e-6:
            continue
        ux, uy = sx / seg_len, sy / seg_len
        if remaining <= seg_len:
            sx0, sy0 = (cur[0], cur[1]) if j == best_i else (ax, ay)
            return (sx0 + ux * remaining, sy0 + uy * remaining)
        remaining -= seg_len
        cur = (bx, by)
    return path_2d[-1]


def _seg_dist(p: tuple[float, float],
              a: tuple[float, float],
              b: tuple[float, float]) -> float:
    """Distance from point p to segment ab."""
    ax, ay = a; bx, by = b; px, py = p
    abx, aby = bx - ax, by - ay
    ab_sq = abx * abx + aby * aby
    if ab_sq < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / ab_sq))
    cx, cy = ax + t * abx, ay + t * aby
    return math.hypot(px - cx, py - cy)


def _quat_yaw_wxyz(q) -> float:
    """Extract yaw from quaternion. Accepts [w,x,y,z] tuple/array/Gf.Quat."""
    w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
    siny = 2.0 * (w * z + x * y)
    cosy = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny, cosy)


def _wrap_pi(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi
