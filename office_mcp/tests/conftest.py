"""Pytest harness for the office_mcp pure-logic tests.

Inserts the extension's package root onto sys.path so ``omni`` resolves as a
PEP 420 namespace package, then stubs the carb / omni leaf modules that
``extension.py`` imports at top level. After this, importing
``omni.office_mcp.network_demo.<module>`` succeeds in plain Python (no Kit).
"""

import sys
import types
from pathlib import Path

_pkg_root = Path(__file__).resolve().parents[1] / "exts" / "omni.office_mcp.network_demo"
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def _stub(name, **attrs):
    mod = sys.modules.get(name) or types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    if "." in name:
        parent, leaf = name.rsplit(".", 1)
        if parent not in sys.modules:
            __import__(parent)
        setattr(sys.modules[parent], leaf, mod)


class _IExtStub:
    def on_startup(self, ext_id): ...
    def on_shutdown(self): ...


_stub(
    "carb",
    log_warn=lambda *a, **k: None,
    log_info=lambda *a, **k: None,
    log_error=lambda *a, **k: None,
)
_stub("omni.ext", IExt=_IExtStub)
_stub("omni.ui")
