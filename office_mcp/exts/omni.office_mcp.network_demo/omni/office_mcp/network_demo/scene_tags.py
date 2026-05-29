"""customData tag contract between the static scene and the runtime extension.

The scene (``build_scene.py``) authors a nested customData dict on every
interactive prim::

    customData = { dictionary net = { token role = "trigger"; int order = 0 } }

The extension *discovers* those prims by ``net:role`` rather than by hard-coded
path, so the demo stays robust to scene renaming (SPEC §5).

This module is intentionally **Kit-free at import time** — only ``discover()``
touches a live USD stage, and it does so through methods on the passed stage
object (no ``pxr`` import). The pure ``organize()`` helper and the dataclasses
are unit-tested with plain pytest.
"""

from __future__ import annotations

from dataclasses import dataclass

# Nested-dict customData keys. ``prim.GetCustomDataByKey("net:role")`` reads the
# ``role`` entry inside the nested ``net`` dict — the ':' is USD's nested-path
# separator, not a literal key name.
ROLE_KEY = "net:role"
ORDER_KEY = "net:order"

ROLE_TRIGGER = "trigger"
ROLE_CABLE = "cable"
ROLE_SWITCH = "switch"
ROLE_SERVER_LED = "server_led"

ALL_ROLES = (ROLE_TRIGGER, ROLE_CABLE, ROLE_SWITCH, ROLE_SERVER_LED)


@dataclass(frozen=True)
class TaggedPrim:
    path: str
    role: str
    order: int | None = None


@dataclass(frozen=True)
class SceneTags:
    """Grouped discovery result. ``cables`` / ``server_leds`` are order-sorted."""

    trigger: str | None
    switch: str | None
    cables: tuple[TaggedPrim, ...]
    server_leds: tuple[TaggedPrim, ...]

    @property
    def ok(self) -> bool:
        """Minimum viable tag set for the demo to run."""
        return (
            self.trigger is not None
            and len(self.cables) >= 1
            and len(self.server_leds) >= 1
        )

    def missing(self) -> list[str]:
        out: list[str] = []
        if self.trigger is None:
            out.append(ROLE_TRIGGER)
        if not self.cables:
            out.append(ROLE_CABLE)
        if not self.server_leds:
            out.append(ROLE_SERVER_LED)
        return out

    @property
    def cable_paths(self) -> tuple[str, ...]:
        return tuple(c.path for c in self.cables)

    @property
    def server_led_orders(self) -> tuple[int, ...]:
        return tuple(s.order if s.order is not None else 0 for s in self.server_leds)


def organize(tagged: list[TaggedPrim]) -> SceneTags:
    """Pure: group tagged prims by role; sort cable/LED groups by ``order``.

    The first ``trigger`` / ``switch`` encountered wins (the scene authors
    exactly one of each). ``order is None`` sorts as 0 so malformed tags don't
    raise.
    """
    trigger: str | None = None
    switch: str | None = None
    cables: list[TaggedPrim] = []
    server_leds: list[TaggedPrim] = []
    for t in tagged:
        if t.role == ROLE_TRIGGER:
            if trigger is None:
                trigger = t.path
        elif t.role == ROLE_SWITCH:
            if switch is None:
                switch = t.path
        elif t.role == ROLE_CABLE:
            cables.append(t)
        elif t.role == ROLE_SERVER_LED:
            server_leds.append(t)
    cables.sort(key=lambda p: (p.order if p.order is not None else 0, p.path))
    server_leds.sort(key=lambda p: (p.order if p.order is not None else 0, p.path))
    return SceneTags(
        trigger=trigger,
        switch=switch,
        cables=tuple(cables),
        server_leds=tuple(server_leds),
    )


def discover(stage) -> SceneTags:
    """Kit-bound: traverse the live stage, read ``net:role`` / ``net:order``.

    Returns an organized :class:`SceneTags`. Never raises on a malformed tag —
    a prim missing ``net:order`` simply gets ``order=None``.
    """
    tagged: list[TaggedPrim] = []
    for prim in stage.Traverse():
        role = prim.GetCustomDataByKey(ROLE_KEY)
        if not role:
            continue
        order = prim.GetCustomDataByKey(ORDER_KEY)
        try:
            order_i = int(order) if order is not None else None
        except (TypeError, ValueError):
            order_i = None
        tagged.append(
            TaggedPrim(
                path=prim.GetPath().pathString,
                role=str(role),
                order=order_i,
            )
        )
    return organize(tagged)
