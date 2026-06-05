"""Pydantic models for OmniGraph REST endpoints (Phase H)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OmnigraphCreateNodeRequestModel(BaseModel):
    """Create a single node inside a named graph (creates graph if missing)."""

    model_config = ConfigDict(extra="forbid")

    graph_path: str = Field(
        description="USD path for the containing graph (e.g. /ActionGraph)",
    )
    node_type: str = Field(
        description=(
            "Fully-qualified node type, e.g. 'omni.graph.action.OnTick' "
            "or 'isaacsim.ros2.bridge.ROS2PublishImage'"
        ),
    )
    node_name: str | None = Field(
        default=None,
        description="Optional node name; defaults to the last segment of node_type",
    )


class OmnigraphConnectRequestModel(BaseModel):
    """Connect two attributes on the same graph (or across graphs).

    Attribute path grammar follows ``og.Controller.connect`` expectations —
    e.g. ``/ActionGraph/OnTick.outputs:tick`` → ``/ActionGraph/Publish.inputs:execIn``.
    """

    model_config = ConfigDict(extra="forbid")

    src_attr: str = Field(description="Source attribute path")
    dst_attr: str = Field(description="Destination attribute path")


class OmnigraphExecuteRequestModel(BaseModel):
    """Evaluate the graph once (synchronous graph.evaluate call)."""

    model_config = ConfigDict(extra="forbid")

    graph_path: str = Field(description="Graph path to evaluate")


class OmnigraphCreateRos2PublisherRequestModel(BaseModel):
    """Assemble an ActionGraph that publishes a camera image to a ROS2 topic.

    Creates OnTick + IsaacCreateRenderProduct + ROS2PublishImage nodes and
    wires them together. Graph structure alone is useful even when the
    ROS2 runtime is not loaded — response ``ros2_available`` reports
    whether live publishing was likely to succeed.
    """

    model_config = ConfigDict(extra="forbid")

    graph_path: str = Field(description="Graph path (will be created if missing)")
    topic: str = Field(description="ROS2 topic name (e.g. /camera/image_raw)")
    source_prim: str = Field(
        description="Camera prim path that feeds the render product",
    )
    msg_type: str = Field(
        default="sensor_msgs/msg/Image",
        description="ROS2 message type — only sensor_msgs/msg/Image is wired today",
    )


class OmnigraphCreateScriptControllerRequestModel(BaseModel):
    """Create OnPlaybackTick -> ScriptNode and bind a Python script path."""

    model_config = ConfigDict(extra="forbid")

    graph_path: str = Field(
        default="/World/ActionGraph",
        description="Graph path to create/use",
    )
    script_path: str = Field(description="Absolute Python file path for ScriptNode")
    node_name: str = Field(default="ScriptNode")
    tick_node_name: str = Field(default="OnPlaybackTick")
    evaluator: str = Field(default="execution")
    reset_state: bool = Field(
        default=True,
        description="Clear ScriptNode internal cached script/use_path state",
    )
