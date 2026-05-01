"""Material service — MDL enumeration / MDL material assign / bound readback (Phase F).

``list_mdl`` scans the Kit install tree for ``.mdl`` modules (falling back to
``$OMNIVERSE_ROOT`` if the Kit runtime does not expose a cache). ``assign_mdl``
drives ``omni.kit.commands`` with ``CreateMdlMaterialPrimCommand`` +
``BindMaterialCommand`` (same path GUI Material menu takes). ``get_bound``
reads back the direct binding via ``UsdShade.MaterialBindingAPI``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_DEFAULT_LIBRARY_ENV = (
    "OMNIVERSE_ROOT",
    "ISAAC_SIM_ROOT",
    "CARB_APP_PATH",
)

# Default search roots if no env variables provide a hint. Kit installs
# typically ship MDL under ``kit/mdl`` or ``kit-sdk/python/.../omni.kit.material.library``.
_DEFAULT_ROOTS: tuple[str, ...] = (
    "kit/mdl",
    "apps/mdl",
    "exts/omni.mdl.neuraylib/mdl",
    "exts/omni.kit.material.library/mdl",
)


class MaterialService:
    """Enumerate, assign, and inspect MDL materials on the active Stage."""

    async def list_mdl(self, library: str = "default") -> dict[str, Any]:
        roots = _resolve_search_roots(library)
        entries: list[dict[str, str]] = []
        seen: set[str] = set()
        for root in roots:
            root_path = Path(root)
            if not root_path.exists():
                continue
            for mdl in root_path.rglob("*.mdl"):
                key = str(mdl.resolve())
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    {
                        "name": mdl.stem,
                        "url": key.replace("\\", "/"),
                        "library": root_path.name,
                    }
                )
                if len(entries) >= 5000:
                    break
            if len(entries) >= 5000:
                break

        entries.sort(key=lambda e: e["name"].lower())
        return {
            "ok": True,
            "library": library,
            "count": len(entries),
            "entries": entries,
        }

    async def assign_mdl(self, request: dict[str, Any]) -> dict[str, Any]:
        import omni.kit.commands  # lazy
        import omni.usd
        from pxr import Sdf, UsdShade

        prim_path = request["prim_path"]
        mdl_url = request["mdl_url"]
        material_name = request["material_name"]

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        if not stage.GetPrimAtPath(prim_path).IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")

        stage.DefinePrim("/World/Materials", "Scope")
        material_prim_path = f"/World/Materials/{_sanitize(material_name)}"

        omni.kit.commands.execute(
            "CreateMdlMaterialPrimCommand",
            mtl_url=mdl_url,
            mtl_name=material_name,
            mtl_path=material_prim_path,
        )

        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=prim_path,
            material_path=material_prim_path,
            strength=UsdShade.Tokens.strongerThanDescendants,
        )

        return {
            "ok": True,
            "prim_path": prim_path,
            "material_prim_path": material_prim_path,
            "mdl_url": mdl_url,
            "material_name": material_name,
        }

    async def get_bound(self, prim_path: str) -> dict[str, Any]:
        import omni.usd
        from pxr import UsdShade

        stage = omni.usd.get_context().get_stage()
        if stage is None:
            raise RuntimeError("No USD stage available")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            raise ValueError(f"Prim {prim_path!r} not found")

        binding = UsdShade.MaterialBindingAPI(prim)
        direct = binding.GetDirectBinding()
        material_path: str | None
        binding_strength: str | None
        if direct and direct.GetMaterialPath():
            material_path = str(direct.GetMaterialPath())
            # DirectBinding only exposes the binding rel; strength is read via
            # the static MaterialBindingAPI.GetMaterialBindingStrength(rel).
            rel = direct.GetBindingRel()
            try:
                binding_strength = str(
                    UsdShade.MaterialBindingAPI.GetMaterialBindingStrength(rel)
                )
            except Exception:  # noqa: BLE001
                binding_strength = None
        else:
            material_path = None
            binding_strength = None
        return {
            "ok": True,
            "prim_path": prim_path,
            "material_path": material_path,
            "binding_strength": binding_strength,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_search_roots(library: str) -> list[str]:
    if library and library != "default" and os.path.isabs(library):
        return [library]
    roots: list[str] = []
    for env_var in _DEFAULT_LIBRARY_ENV:
        base = os.environ.get(env_var)
        if not base:
            continue
        for sub in _DEFAULT_ROOTS:
            roots.append(os.path.join(base, sub))
    # Also look at Kit app location inferred from the running executable when
    # env vars are unset (falls back silently if the process is not Kit).
    try:
        import sys

        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        for sub in _DEFAULT_ROOTS:
            roots.append(os.path.join(exe_dir, "..", sub))
    except Exception:  # noqa: BLE001
        pass
    return roots


def _sanitize(name: str) -> str:
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in name)
    if not out:
        out = "Material"
    if out[0].isdigit():
        out = f"m_{out}"
    return out
