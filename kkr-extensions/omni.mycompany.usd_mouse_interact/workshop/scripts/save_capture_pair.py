"""Copy a fresh window_capture PNG into kkr-extensions/omni.mycompany.usd_mouse_interact/workshop/captures/<step>_app.png
and crop the central viewport region into <step>_viewport.png.

We avoid omni.replicator (USD Composer doesn't ship it) so window_capture from
the Win32 PrintWindow API is the only path. The viewport is a docked panel so
we don't have a dedicated HWND — the easiest way to "capture only the viewport"
is to crop the docked region by approximate coords.

Usage:
    python save_capture_pair.py <step_name> <source_png>

The crop box is set to roughly the central viewport area. If the viewport
docking changes the box can be tweaked here.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE_DIR = REPO_ROOT / "usd-mouse-interact" / "captures"

# Empirically: KKR USD Composer at 2679x1626 with stock layout has the
# viewport panel filling roughly the central 60% horizontally and 50%
# vertically. We give it a generous margin so a different dock state still
# shows the viewport contents.
VIEWPORT_CROP_FRACTION = (0.20, 0.10, 0.85, 0.65)  # (left, top, right, bottom)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: save_capture_pair.py <step_name> <source_png>", file=sys.stderr)
        return 2
    step = sys.argv[1]
    source = Path(sys.argv[2])
    if not source.is_file():
        print(f"source not found: {source}", file=sys.stderr)
        return 2
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    app_path = CAPTURE_DIR / f"{step}_app.png"
    viewport_path = CAPTURE_DIR / f"{step}_viewport.png"

    shutil.copyfile(source, app_path)

    try:
        from PIL import Image
    except ImportError:
        # Fallback: just copy app PNG into viewport slot too — better than no
        # capture at all.
        shutil.copyfile(source, viewport_path)
        print(f"PIL missing — viewport.png is a duplicate of app.png", file=sys.stderr)
    else:
        img = Image.open(source)
        w, h = img.size
        l = int(w * VIEWPORT_CROP_FRACTION[0])
        t = int(h * VIEWPORT_CROP_FRACTION[1])
        r = int(w * VIEWPORT_CROP_FRACTION[2])
        b = int(h * VIEWPORT_CROP_FRACTION[3])
        img.crop((l, t, r, b)).save(viewport_path)

    print(f"saved: {app_path}")
    print(f"saved: {viewport_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
