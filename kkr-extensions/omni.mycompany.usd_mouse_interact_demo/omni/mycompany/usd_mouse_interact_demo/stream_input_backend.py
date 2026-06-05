"""Kit message-bus backend for streamed FPS input packets."""

from __future__ import annotations

import time
from typing import Any

from .fps_input_router import FpsInputSample
from .input_packet import StreamInputAggregator, parse_stream_payload

SOURCE = "omni.mycompany.usd_mouse_interact_demo.stream_input_backend"
EVENT_NAME = "usdMouseInteractDemo.input"


def _log_warn(message: str) -> None:
    try:
        import carb

        carb.log_warn(message)
    except Exception:  # noqa: BLE001
        pass


class StreamMessageBackend:
    name = "stream-message"

    def __init__(self) -> None:
        self._aggregator = StreamInputAggregator()
        self._bus = None
        self._sub = None
        self._active = False

    def activate(self) -> None:
        try:
            import carb.events
            import omni.kit.app

            app = omni.kit.app.get_app()
            self._bus = app.get_message_bus_event_stream()
            event_type = carb.events.type_from_string(EVENT_NAME)
            try:
                self._sub = self._bus.create_subscription_to_pop_by_type(
                    event_type,
                    self._on_event,
                    name=f"{SOURCE}.input",
                )
            except TypeError:
                self._sub = self._bus.create_subscription_to_pop_by_type(
                    event_type,
                    self._on_event,
                )
            self._active = True
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{SOURCE}] message bus subscribe failed: {exc!r}")
            self.deactivate()

    def deactivate(self) -> None:
        self._sub = None
        self._bus = None
        self._active = False
        self._aggregator.release()

    def sample(
        self, center: tuple[float, float] | None, now_s: float
    ) -> FpsInputSample | None:
        del center
        if not self._active:
            return None

        sample = self._aggregator.consume(now_s)
        if not sample.active:
            return None
        return FpsInputSample(
            dx=sample.dx,
            dy=sample.dy,
            keys=sample.keys,
            backend_name=self.name,
            active=True,
        )

    def _on_event(self, event: Any) -> None:
        payload = self._payload_dict(event)
        if payload is None:
            _log_warn(f"[{SOURCE}] invalid stream input payload ignored")
            return

        try:
            packet = parse_stream_payload(payload)
        except Exception as exc:  # noqa: BLE001
            _log_warn(f"[{SOURCE}] invalid stream input payload ignored: {exc!r}")
            return

        self._aggregator.push(packet, time.monotonic())

    @staticmethod
    def _payload_dict(event: Any) -> dict[str, Any] | None:
        payload = getattr(event, "payload", None)
        if isinstance(payload, dict):
            return payload
        try:
            payload_dict = payload.get_dict()
        except Exception:  # noqa: BLE001
            return None
        return payload_dict if isinstance(payload_dict, dict) else None
