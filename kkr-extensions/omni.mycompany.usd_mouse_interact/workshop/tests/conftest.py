"""pytest config — make the extension package importable for unit tests.

The extension is laid out under
    kkr-extensions/omni.mycompany.usd_mouse_interact/omni/mycompany/usd_mouse_interact/

so we add the inner ``omni.mycompany.usd_mouse_interact`` package's parent to
``sys.path`` and the carb-free modules become importable as
``omni.mycompany.usd_mouse_interact.camera_math`` etc.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXT_PYROOT = HERE.parent.parent

if str(EXT_PYROOT) not in sys.path:
    sys.path.insert(0, str(EXT_PYROOT))
