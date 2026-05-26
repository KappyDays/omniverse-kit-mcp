"""Pure prop -> semantic-class mapping helpers (NO omni / pxr)."""
from __future__ import annotations

from . import config


def prop_label_pairs() -> list[tuple[str, str, str, tuple[float, float, float]]]:
    """(name, url, semantic_class, translate) for each labeled prop."""
    return [(name, url, cls, tuple(tr)) for (name, url, cls, tr) in config.PROPS]


def classes() -> list[str]:
    """Sorted unique semantic classes."""
    return sorted({cls for (_n, _u, cls, _t) in config.PROPS})
