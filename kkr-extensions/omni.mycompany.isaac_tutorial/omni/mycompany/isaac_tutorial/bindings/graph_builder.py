"""WASD Action Graph 프로그래머틱 구축 — Nova Carter 텔레오퍼레이션.

Keyboard input nodes (W/A/S/D/SPACE) 이 linearVel / angularVel variables 를
갱신 → DifferentialController 가 wheel velocities 로 변환 → ArticulationController
가 Nova Carter 의 좌/우 wheel joint 에 velocity command 전달.

참고 패턴: omni.physx.cct/scripts/scenes/actiongraph.usd — CCT 의 Character Controller
대신 isaacsim.wheeled_robots.DifferentialController 말단 사용.
"""
from __future__ import annotations


def build_wasd_graph(
    graph_path: str,
    robot_prim: str,
    left_joint: str = "joint_wheel_left",
    right_joint: str = "joint_wheel_right",
    wheel_base: float = 0.413,
    wheel_radius: float = 0.14,
    linear_speed: float = 1.0,
    angular_speed: float = 1.5,
) -> str:
    """Create an ActionGraph at graph_path that maps WASD+SPACE to wheel joints.

    Returns the graph_path (echo) so callers can record it in TutorialState.
    """
    import omni.graph.core as og

    # Per-key target (linearVel, angularVel) pair
    keys = {
        "W": (linear_speed, 0.0),
        "S": (-linear_speed, 0.0),
        "A": (0.0, angular_speed),
        "D": (0.0, -angular_speed),
        "SPACE": (0.0, 0.0),  # emergency brake
    }

    create_nodes: list[tuple] = [
        ("OnTick", "omni.graph.action.OnPlaybackTick"),
        *[(f"Key_{k}", "omni.graph.action.OnKeyboardInput") for k in keys],
        *[(f"Write_{k}", "omni.graph.core.WriteVariable") for k in keys],
        ("ReadLin", "omni.graph.core.ReadVariable"),
        ("ReadAng", "omni.graph.core.ReadVariable"),
        ("DiffCtrl", "isaacsim.wheeled_robots.DifferentialController"),
        ("ArtCtrl", "isaacsim.core.nodes.IsaacArticulationController"),
    ]

    set_values: list[tuple] = [
        *[(f"Key_{k}.inputs:keyIn", k) for k in keys],
        *[
            (f"Write_{k}.inputs:value", [keys[k][0], keys[k][1]])
            for k in keys
        ],
        ("ReadLin.inputs:variableName", "linearVel"),
        ("ReadAng.inputs:variableName", "angularVel"),
        ("DiffCtrl.inputs:wheelDistance", wheel_base),
        ("DiffCtrl.inputs:wheelRadius", wheel_radius),
        ("ArtCtrl.inputs:targetPrim", [robot_prim]),
        ("ArtCtrl.inputs:jointNames", [left_joint, right_joint]),
    ]

    connect: list[tuple] = [
        ("OnTick.outputs:tick", "DiffCtrl.inputs:execIn"),
        ("DiffCtrl.outputs:velocityCommand", "ArtCtrl.inputs:velocityCommand"),
        ("ReadLin.outputs:value", "DiffCtrl.inputs:linearVelocity"),
        ("ReadAng.outputs:value", "DiffCtrl.inputs:angularVelocity"),
        *[
            (f"Key_{k}.outputs:pressed", f"Write_{k}.inputs:execIn")
            for k in keys
        ],
    ]

    og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            og.Controller.Keys.CREATE_NODES: create_nodes,
            og.Controller.Keys.SET_VALUES: set_values,
            og.Controller.Keys.CONNECT: connect,
        },
    )
    return graph_path
