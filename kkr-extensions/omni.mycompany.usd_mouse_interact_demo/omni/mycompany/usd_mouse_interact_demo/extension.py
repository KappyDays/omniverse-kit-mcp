"""USD Mouse Interact Demo — Kit Extension entry point.

Lifecycle:
    on_startup  → instantiate ModeCoordinator, subscribe to runtime events.
    on_shutdown → tear everything down idempotently (no zombie ui.Window).
"""

from __future__ import annotations

import carb
import omni.ext

from .mode_coordinator import ModeCoordinator

_SOURCE = "omni.mycompany.usd_mouse_interact_demo"


class UsdMouseInteractExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:  # noqa: D401
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._controller: ModeCoordinator | None = None
        try:
            self._controller = ModeCoordinator(source=_SOURCE)
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] init failed: {exc!r}")
            self._controller = None
            return
        try:
            self._controller.start()
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{_SOURCE}] start failed: {exc!r}")

    def on_shutdown(self) -> None:
        carb.log_warn(f"[{_SOURCE}] on_shutdown")
        if self._controller is not None:
            try:
                self._controller.stop()
            except Exception as exc:  # noqa: BLE001
                carb.log_error(f"[{_SOURCE}] shutdown failed: {exc!r}")
            finally:
                self._controller = None
