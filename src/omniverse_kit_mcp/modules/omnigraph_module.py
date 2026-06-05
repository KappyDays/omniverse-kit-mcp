"""OmniGraph module — node / connect / execute + ROS2 publisher (Phase H)."""

from __future__ import annotations

import logging
import time

from omniverse_kit_mcp.clients.isaac_rest_client import IsaacRestClient
from omniverse_kit_mcp.modules.base import error_result, ok_result
from omniverse_kit_mcp.types.common import ModuleResult, OperationMeta
from omniverse_kit_mcp.types.omnigraph import (
    OmnigraphConnectRequest,
    OmnigraphConnectResult,
    OmnigraphCreateNodeRequest,
    OmnigraphCreateNodeResult,
    OmnigraphCreateRos2PublisherRequest,
    OmnigraphCreateRos2PublisherResult,
    OmnigraphCreateScriptControllerRequest,
    OmnigraphCreateScriptControllerResult,
    OmnigraphEdgeRef,
    OmnigraphExecuteRequest,
    OmnigraphExecuteResult,
    OmnigraphNodeRef,
)

logger = logging.getLogger(__name__)


class OmnigraphModule:
    def __init__(self, client: IsaacRestClient) -> None:
        self._client = client

    async def create_node(
        self, meta: OperationMeta, request: OmnigraphCreateNodeRequest,
    ) -> ModuleResult[OmnigraphCreateNodeResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.omnigraph_create_node({
                "graph_path": request.graph_path,
                "node_type": request.node_type,
                "node_name": request.node_name,
            })
            result = OmnigraphCreateNodeResult(
                ok=bool(raw.get("ok", True)),
                graph_path=str(raw.get("graph_path", request.graph_path)),
                graph_existed=bool(raw.get("graph_existed", False)),
                node_type=str(raw.get("node_type", request.node_type)),
                node_name=str(raw.get("node_name", "")),
                node_path=str(raw.get("node_path", "")),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="OMNIGRAPH_CREATE_NODE_ERROR",
            )

    async def connect(
        self, meta: OperationMeta, request: OmnigraphConnectRequest,
    ) -> ModuleResult[OmnigraphConnectResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.omnigraph_connect({
                "src_attr": request.src_attr,
                "dst_attr": request.dst_attr,
            })
            result = OmnigraphConnectResult(
                ok=bool(raw.get("ok", True)),
                src_attr=str(raw.get("src_attr", request.src_attr)),
                dst_attr=str(raw.get("dst_attr", request.dst_attr)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="OMNIGRAPH_CONNECT_ERROR",
            )

    async def execute(
        self, meta: OperationMeta, request: OmnigraphExecuteRequest,
    ) -> ModuleResult[OmnigraphExecuteResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.omnigraph_execute({
                "graph_path": request.graph_path,
            })
            result = OmnigraphExecuteResult(
                ok=bool(raw.get("ok", True)),
                graph_path=str(raw.get("graph_path", request.graph_path)),
                evaluated=bool(raw.get("evaluated", False)),
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="OMNIGRAPH_EXECUTE_ERROR",
            )

    async def create_ros2_publisher(
        self, meta: OperationMeta,
        request: OmnigraphCreateRos2PublisherRequest,
    ) -> ModuleResult[OmnigraphCreateRos2PublisherResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.omnigraph_create_ros2_publisher({
                "graph_path": request.graph_path,
                "topic": request.topic,
                "source_prim": request.source_prim,
                "msg_type": request.msg_type,
            })
            nodes = tuple(
                OmnigraphNodeRef(
                    name=str(n.get("name", "")),
                    type=str(n.get("type", "")),
                    path=str(n.get("path", "")),
                )
                for n in raw.get("nodes_created") or []
            )
            edges = tuple(
                OmnigraphEdgeRef(
                    src=str(e.get("src", "")),
                    dst=str(e.get("dst", "")),
                )
                for e in raw.get("edges_created") or []
            )
            result = OmnigraphCreateRos2PublisherResult(
                ok=bool(raw.get("ok", True)),
                graph_path=str(raw.get("graph_path", request.graph_path)),
                topic=str(raw.get("topic", request.topic)),
                source_prim=str(raw.get("source_prim", request.source_prim)),
                msg_type=str(raw.get("msg_type", request.msg_type)),
                ros2_available=bool(raw.get("ros2_available", False)),
                nodes_created=nodes,
                edges_created=edges,
                backend=str(raw.get("backend", "")),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="OMNIGRAPH_ROS2_PUBLISHER_ERROR",
            )

    async def create_script_controller(
        self,
        meta: OperationMeta,
        request: OmnigraphCreateScriptControllerRequest,
    ) -> ModuleResult[OmnigraphCreateScriptControllerResult]:
        started = int(time.time() * 1000)
        try:
            raw = await self._client.omnigraph_create_script_controller({
                "graph_path": request.graph_path,
                "script_path": request.script_path,
                "node_name": request.node_name,
                "tick_node_name": request.tick_node_name,
                "evaluator": request.evaluator,
                "reset_state": request.reset_state,
            })
            nodes = tuple(
                OmnigraphNodeRef(
                    name=str(n.get("name", "")),
                    type=str(n.get("type", "")),
                    path=str(n.get("path", "")),
                )
                for n in raw.get("nodes_created") or []
            )
            edges = tuple(
                OmnigraphEdgeRef(
                    src=str(e.get("src", "")),
                    dst=str(e.get("dst", "")),
                )
                for e in raw.get("edges_created") or []
            )
            result = OmnigraphCreateScriptControllerResult(
                ok=bool(raw.get("ok", True)),
                graph_path=str(raw.get("graph_path", request.graph_path)),
                script_path=str(raw.get("script_path", request.script_path)),
                node_path=str(raw.get("node_path", "")),
                tick_node_path=str(raw.get("tick_node_path", "")),
                nodes_created=nodes,
                edges_created=edges,
                backend=str(raw.get("backend", "")),
                reset_state=bool(raw.get("reset_state", request.reset_state)),
            )
            return ok_result(result, started_ms=started)
        except Exception as exc:  # noqa: BLE001
            return error_result(
                str(exc), started_ms=started, exc=exc,
                error_code="OMNIGRAPH_SCRIPT_CONTROLLER_ERROR",
            )
