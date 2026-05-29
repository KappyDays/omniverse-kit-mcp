"""Sequential transmission wave: pure model + Kit-bound emissive driver.

``WaveModel`` is **pure** (no Kit / USD imports) so it is unit-tested with plain
pytest. ``TransmissionController`` binds a model to the discovered cable/LED
shader inputs and advances it from a per-frame update subscription, writing
``emissiveColor`` so the wave is visible in the viewport.

Geometry of the wave
--------------------
The front travels ``0 -> num_cables`` across ``duration`` seconds. Cable at
position ``i`` is lit fractionally as the front passes through it
(``cable_fill(i)``). A server LED with ``order == k`` is fed by the cable at
position ``k`` (``Switch -> Server_k``), so it lights once that cable is fully
lit — i.e. the front has reached the server end. Cable order ``0``
(``PC -> Switch``) feeds no server.
"""

from __future__ import annotations

STATUS_IDLE = "idle"
STATUS_TRANSMITTING = "transmitting"
STATUS_DELIVERED = "delivered"

DEFAULT_DURATION = 3.0

_EPS = 1e-9


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


class WaveModel:
    """Pure progress-wave state machine. No Kit/USD dependencies."""

    def __init__(self, num_cables, server_orders, duration: float = DEFAULT_DURATION):
        self.num_cables = int(num_cables)
        self.server_orders = tuple(sorted(int(o) for o in server_orders))
        self.duration = float(duration) if float(duration) > 0 else DEFAULT_DURATION
        self.progress = 0.0
        self.status = STATUS_IDLE

    # -- lifecycle ------------------------------------------------------
    def start(self) -> None:
        self.progress = 0.0
        self.status = STATUS_TRANSMITTING if self.num_cables > 0 else STATUS_DELIVERED

    def reset(self) -> None:
        self.progress = 0.0
        self.status = STATUS_IDLE

    def advance(self, dt: float) -> None:
        if self.status != STATUS_TRANSMITTING:
            return
        if self.duration <= 0:
            self.progress = 1.0
        else:
            self.progress = min(1.0, self.progress + float(dt) / self.duration)
        if self.progress >= 1.0 - _EPS:
            self.progress = 1.0
            self.status = STATUS_DELIVERED

    # -- derived signals ------------------------------------------------
    @property
    def front(self) -> float:
        return self.progress * self.num_cables

    def cable_fill(self, cable_index: int) -> float:
        """0..1 emissive fraction for the cable at position ``cable_index``."""
        return _clamp(self.front - cable_index, 0.0, 1.0)

    def server_lit(self, server_order: int) -> bool:
        """True once the cable feeding this server (position == order) is full."""
        return self.cable_fill(server_order) >= 1.0 - _EPS

    def lit_count(self) -> int:
        return sum(1 for o in self.server_orders if self.server_lit(o))

    def current_target(self) -> int:
        """1-based number of the server currently being delivered to."""
        n = len(self.server_orders)
        if n == 0:
            return 0
        if self.status == STATUS_DELIVERED:
            return n
        return min(self.lit_count() + 1, n)


# Emissive colours (linear, slightly > 1.0 so RTX bloom makes the wave pop).
_CABLE_GLOW = (0.05, 1.6, 0.6)     # cyan-green wave
_LED_ON = (0.1, 2.2, 0.25)         # bright green "delivered" LED
_OFF = (0.0, 0.0, 0.0)


class TransmissionController:
    """Binds a :class:`WaveModel` to live shader emissive inputs (Kit-bound)."""

    def __init__(self, source: str = "omni.office_mcp.network_demo.transmission") -> None:
        self._source = source
        self.model: WaveModel | None = None
        # Cached UsdShade.Input handles resolved at bind() time, in order.
        self._cable_inputs: list = []   # index i -> emissiveColor input for cable i
        self._led_inputs: list = []     # parallel to model.server_orders
        self._bound = False

    @property
    def bound(self) -> bool:
        return self._bound

    def bind(self, stage, tags) -> bool:
        """Resolve emissive shader inputs for every cable + server LED prim.

        Returns False (and logs) if no usable shader inputs were found.
        """
        import carb

        self._cable_inputs = []
        self._led_inputs = []
        try:
            for cable in tags.cables:
                inp = self._emissive_input(stage, cable.path)
                self._cable_inputs.append(inp)
            for led in tags.server_leds:
                inp = self._emissive_input(stage, led.path)
                self._led_inputs.append(inp)
        except Exception as exc:  # noqa: BLE001
            carb.log_error(f"[{self._source}] bind failed: {exc!r}")
            return False

        self.model = WaveModel(
            num_cables=len(tags.cables),
            server_orders=[s.order if s.order is not None else 0 for s in tags.server_leds],
        )
        self._bound = True
        self._apply()  # reset everything to off
        n_cable = sum(1 for i in self._cable_inputs if i is not None)
        n_led = sum(1 for i in self._led_inputs if i is not None)
        carb.log_warn(
            f"[{self._source}] bound: {n_cable}/{len(self._cable_inputs)} cable "
            f"inputs, {n_led}/{len(self._led_inputs)} LED inputs"
        )
        return n_cable > 0 or n_led > 0

    def unbind(self) -> None:
        self._cable_inputs = []
        self._led_inputs = []
        self.model = None
        self._bound = False

    def start(self) -> None:
        if self.model is not None:
            self.model.start()
            self._apply()

    def reset_visuals(self) -> None:
        """Return the model to idle and turn every cable/LED emissive off."""
        if self.model is not None:
            self.model.reset()
            self._apply()

    def on_update(self, dt: float) -> None:
        if not self._bound or self.model is None:
            return
        if self.model.status != STATUS_TRANSMITTING:
            return
        self.model.advance(dt)
        self._apply()

    # -- internals ------------------------------------------------------
    def _emissive_input(self, stage, prim_path: str):
        """Resolve (or create) the bound surface shader's emissiveColor input."""
        import carb
        from pxr import UsdShade

        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            return None
        try:
            mat, _rel = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            if not mat:
                return None
            shader = mat.ComputeSurfaceSource()[0]
            if not shader:
                return None
            inp = shader.GetInput("emissiveColor")
            if not inp:
                from pxr import Sdf
                inp = shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f)
            return inp
        except Exception as exc:  # noqa: BLE001
            carb.log_warn(f"[{self._source}] emissive input for {prim_path}: {exc!r}")
            return None

    def _apply(self) -> None:
        from pxr import Gf

        model = self.model
        if model is None:
            return
        for i, inp in enumerate(self._cable_inputs):
            if inp is None:
                continue
            f = model.cable_fill(i)
            inp.Set(Gf.Vec3f(_CABLE_GLOW[0] * f, _CABLE_GLOW[1] * f, _CABLE_GLOW[2] * f))
        for inp, order in zip(self._led_inputs, model.server_orders):
            if inp is None:
                continue
            on = model.server_lit(order)
            inp.Set(Gf.Vec3f(*_LED_ON) if on else Gf.Vec3f(*_OFF))
