"""NavMesh Playground — spawn People/Robot on baked NavMesh and drive them.

Independent extension. Kit SDK direct calls only (no validation_api import).
Spec: docs/superpowers/specs/2026-04-23-navmesh-playground-design.md
"""
from __future__ import annotations

import carb
import omni.ext

from .agent_manager import AgentManager
from .people_controller import PeopleController
from .robot_controller import RobotController
from .ui_panel import NavMeshPlaygroundPanel, WAREHOUSE_URL
from .usd_loader import safe_load_usd


_SOURCE = "omni.mycompany.navmesh_playground"


class NavMeshPlaygroundExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._ext_id = ext_id
        # CRITICAL (T0.2): never enable log_capture inside an extension that
        # also loads MDL-heavy S3 assets. Keep this sentinel explicit.
        self._log_capture = None
        self._agent_manager = AgentManager()
        self._people_controller = PeopleController(self._agent_manager)
        self._robot_controller = RobotController(self._agent_manager)
        self._panel = NavMeshPlaygroundPanel(
            agent_manager=self._agent_manager,
            people_controller=self._people_controller,
            robot_controller=self._robot_controller,
            load_warehouse_cb=self._load_warehouse,
        )
        self._window = self._panel.build()

    async def _load_warehouse(self):
        """Load Simple_Warehouse if not already present at /World/Warehouse."""
        import omni.usd
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No stage")
        existing = stage.GetPrimAtPath("/World/Warehouse")
        if existing and existing.IsValid():
            return {"prim_path": "/World/Warehouse", "already_loaded": True}
        return await safe_load_usd(
            usd_url=WAREHOUSE_URL, prim_path="/World/Warehouse",
            position=[0.0, 0.0, 0.0],
        )

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        if self._window is not None:
            try:
                # visible=False forces Workspace deregister before destroy;
                # destroy() alone leaves a zombie window when fswatcher reloads
                # quickly (next on_startup creates a duplicate "NavMesh Playground"
                # entry — omni.ui_query then warns "found 2 windows...").
                self._window.visible = False
                self._window.destroy()
            except Exception as exc:
                carb.log_warn(f"[{_SOURCE}] window destroy failed: {exc}")
            self._window = None
