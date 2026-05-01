"""OmniGraph service — node / connect / execute + ROS2 image publisher (Phase H)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OmnigraphService:
    """Thin wrapper around ``omni.graph.core.Controller``.

    The service is stateless; all graph state lives in USD (the Stage)
    and in Kit's global ``og.Controller`` registry. ROS2 publisher
    assembly is a composed macro — it still returns the exact nodes it
    created + edges so the MCP caller can assert on the graph shape
    even when the ROS2 runtime is unavailable.
    """

    async def create_node(self, request: dict[str, Any]) -> dict[str, Any]:
        graph_path = request["graph_path"]
        node_type = request["node_type"]
        node_name = request.get("node_name") or node_type.rsplit(".", 1)[-1]

        backend = "omni.graph.core"
        graph_existed = False
        try:
            import omni.graph.core as og  # type: ignore[import-not-found]

            graph = og.get_graph_by_path(graph_path)
            if graph is None:
                result = og.Controller.edit(
                    {"graph_path": graph_path, "evaluator_name": "execution"},
                    {},
                )
                graph = (
                    result[0] if isinstance(result, tuple) else result
                )
            else:
                graph_existed = True

            (edit_result, nodes, _prims, _edges) = og.Controller.edit(
                graph, {og.Controller.Keys.CREATE_NODES: [(node_name, node_type)]},
            )
            node_path = f"{graph_path}/{node_name}"
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"
            node_path = f"{graph_path}/{node_name}"

        return {
            "ok": True,
            "graph_path": graph_path,
            "graph_existed": graph_existed,
            "node_type": node_type,
            "node_name": node_name,
            "node_path": node_path,
            "backend": backend,
        }

    async def connect(self, request: dict[str, Any]) -> dict[str, Any]:
        src_attr = request["src_attr"]
        dst_attr = request["dst_attr"]

        backend = "omni.graph.core"
        try:
            import omni.graph.core as og  # type: ignore[import-not-found]

            og.Controller.connect(src_attr, dst_attr)
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        return {
            "ok": True,
            "src_attr": src_attr,
            "dst_attr": dst_attr,
            "backend": backend,
        }

    async def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        graph_path = request["graph_path"]
        backend = "omni.graph.core"
        evaluated = False
        try:
            import omni.graph.core as og  # type: ignore[import-not-found]

            graph = og.get_graph_by_path(graph_path)
            if graph is None:
                raise ValueError(f"Graph {graph_path!r} not found")
            graph.evaluate()
            evaluated = True
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        return {
            "ok": True,
            "graph_path": graph_path,
            "evaluated": evaluated,
            "backend": backend,
        }

    async def create_ros2_publisher(self, request: dict[str, Any]) -> dict[str, Any]:
        graph_path = request["graph_path"]
        topic = request["topic"]
        source_prim = request["source_prim"]
        msg_type = request.get("msg_type", "sensor_msgs/msg/Image")

        # Detect ROS2 runtime availability (rclpy presence)
        ros2_available = False
        try:
            import rclpy  # type: ignore[import-not-found]  # noqa: F401

            ros2_available = True
        except Exception:  # noqa: BLE001
            ros2_available = False

        nodes_created: list[dict[str, str]] = []
        edges_created: list[dict[str, str]] = []
        backend = "omni.graph.core"

        try:
            import omni.graph.core as og  # type: ignore[import-not-found]

            graph = og.get_graph_by_path(graph_path)
            if graph is None:
                res = og.Controller.edit(
                    {"graph_path": graph_path, "evaluator_name": "execution"},
                    {},
                )
                graph = res[0] if isinstance(res, tuple) else res

            keys = og.Controller.Keys
            node_specs = [
                ("OnTick", "omni.graph.action.OnTick"),
                (
                    "RenderProduct",
                    "isaacsim.core.nodes.IsaacCreateRenderProduct",
                ),
                (
                    "PublishImage",
                    "isaacsim.ros2.bridge.ROS2PublishImage",
                ),
            ]
            og.Controller.edit(graph, {keys.CREATE_NODES: node_specs})
            for name, ntype in node_specs:
                nodes_created.append({"name": name, "type": ntype, "path": f"{graph_path}/{name}"})

            # Attribute connections (execution + data flow)
            connections = [
                (f"{graph_path}/OnTick.outputs:tick", f"{graph_path}/RenderProduct.inputs:execIn"),
                (f"{graph_path}/RenderProduct.outputs:execOut", f"{graph_path}/PublishImage.inputs:execIn"),
                (f"{graph_path}/RenderProduct.outputs:renderProductPath", f"{graph_path}/PublishImage.inputs:renderProductPath"),
            ]
            for src, dst in connections:
                try:
                    og.Controller.connect(src, dst)
                    edges_created.append({"src": src, "dst": dst})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skipped connection %s -> %s: %s", src, dst, exc)

            # Configure topic + source camera via attribute set
            try:
                og.Controller.attribute(
                    f"{graph_path}/PublishImage.inputs:topicName",
                ).set(topic)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not set topic attribute: %s", exc)
            try:
                og.Controller.attribute(
                    f"{graph_path}/RenderProduct.inputs:cameraPrim",
                ).set([source_prim])
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not set cameraPrim attribute: %s", exc)
        except Exception as exc:  # noqa: BLE001
            backend = f"fallback_metadata:{type(exc).__name__}"

        return {
            "ok": True,
            "graph_path": graph_path,
            "topic": topic,
            "source_prim": source_prim,
            "msg_type": msg_type,
            "ros2_available": ros2_available,
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "backend": backend,
        }
