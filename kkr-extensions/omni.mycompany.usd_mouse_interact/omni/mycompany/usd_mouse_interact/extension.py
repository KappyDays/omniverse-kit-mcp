"""USD Mouse Interact — Kit Extension entry point.

Lifecycle:
    on_startup  → instantiate InteractionController, subscribe to timeline events.
    on_shutdown → tear everything down idempotently (no zombie ui.Window).
"""

from __future__ import annotations

import carb
import omni.ext

from .interaction_controller import InteractionController

_SOURCE = "omni.mycompany.usd_mouse_interact"


class UsdMouseInteractExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:  # noqa: D401
        carb.log_warn(f"[{_SOURCE}] on_startup ({ext_id})")
        self._controller: InteractionController | None = None
        try:
            self._controller = InteractionController(source=_SOURCE)
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
