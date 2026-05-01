"""omni.mycompany.usd_mouse_interact — FPS-style viewport camera control.

Re-exports the IExt subclass so Kit picks it up via the extension module loader.
Outside Kit (plain pytest) the carb / omni.ext / pxr imports are missing —
the try/except keeps the carb-free sub-modules importable for unit tests.
"""

import sys as _sys

try:
    from .extension import UsdMouseInteractExtension  # noqa: F401
except Exception as _exc:  # noqa: BLE001
    print(
        f"[omni.mycompany.usd_mouse_interact] __init__ import failed: {_exc!r}",
        file=_sys.stderr,
        flush=True,
    )
    try:
        import carb as _carb  # noqa: WPS433

        _carb.log_error(
            f"[omni.mycompany.usd_mouse_interact] __init__ import failed: {_exc!r}"
        )
    except Exception:  # noqa: BLE001
        pass
    UsdMouseInteractExtension = None  # type: ignore[assignment]
