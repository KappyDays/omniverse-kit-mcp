"""Conservative carb mouse polling backend stub.

The backend only probes availability for now. It does not feed live camera
movement, preserving the existing cursor-warp FPS behavior.
"""

from __future__ import annotations

from .fps_input_router import FpsInputSample


class CarbMousePollBackend:
    name = "carb-mouse"

    def __init__(self) -> None:
        self._input = None
        self._available = False

    def activate(self) -> None:
        try:
            import carb.input

            self._input = carb.input.acquire_input_interface()
            self._available = self._input is not None
        except Exception:  # noqa: BLE001
            self._input = None
            self._available = False

    def deactivate(self) -> None:
        self._input = None
        self._available = False

    def sample(
        self, center: tuple[float, float] | None, now_s: float
    ) -> FpsInputSample | None:
        del center, now_s
        return None
