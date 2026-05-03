"""Integration tests for ``.env`` → sub-config propagation (L14 regression guard).

Context
-------
pydantic-settings v2 does NOT propagate the parent's ``env_file`` to
sub-``BaseSettings`` instances created via ``Field(default_factory=…)``.
Without each sub-config declaring its own ``env_file=".env"``, every
``.env`` override for ``ISAAC_SIM_*`` / ``LAKEHOUSE_*`` / ``MCP_SERVER_*`` /
``SCENARIO_*`` was silently ignored — only OS env vars took effect.
See ``src/omniverse_kit_mcp/config.py`` docstring and lessons-learned L14.

These tests prove two things:

1. A scalar override (``ISAAC_SIM_STARTUP_TIMEOUT``) in a tmp ``.env``
   actually reaches ``IsaacSimProcessConfig.startup_timeout`` (E14-1).
2. A JSON-array override (``ISAAC_SIM_EXTRA_EXT_IDS``) reaches
   ``IsaacSimProcessConfig.extra_ext_ids`` (E14-2).
3. An AST guard on ``config.py`` catches any future ``BaseSettings``
   subclass that forgets ``env_file='.env'`` (E14-3).
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
CONFIG_PY = PROJECT / "src" / "omniverse_kit_mcp" / "config.py"

# Env vars that must not leak in from the outer shell — .env is the
# authoritative source under test.
_ENV_VARS_TO_CLEAR = (
    "ISAAC_SIM_STARTUP_TIMEOUT",
    "ISAAC_SIM_EXTRA_EXT_IDS",
    "ISAAC_SIM_BASE_URL",
    "LAKEHOUSE_BASE_URL",
    "MCP_SERVER_PORT",
    "SCENARIOS_DIR",
    "SCENARIO_DEFAULT_TIMEOUT",
)


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Move cwd into tmp_path and wipe known overrides so only tmp/.env counts."""
    monkeypatch.chdir(tmp_path)
    for var in _ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def _fresh_app_config():
    """Re-import config so pydantic-settings reads the current cwd's .env.

    ``BaseSettings`` evaluates ``env_file`` at instantiation time, so a
    simple ``AppConfig()`` is enough without reloading the module — but
    reloading keeps the test resilient against any future module-level
    caching.
    """
    import omniverse_kit_mcp.config as cfg
    importlib.reload(cfg)
    return cfg.AppConfig()


def test_e14_1_startup_timeout_override(isolated_env: Path):
    """tmp .env `ISAAC_SIM_STARTUP_TIMEOUT=99.0` must reach sub-config."""
    (isolated_env / ".env").write_text(
        "ISAAC_SIM_STARTUP_TIMEOUT=99.0\n", encoding="utf-8"
    )
    ac = _fresh_app_config()
    assert ac.isaac_sim_process.startup_timeout == 99.0, (
        f"L14 regression — startup_timeout override dropped: "
        f"got {ac.isaac_sim_process.startup_timeout}"
    )


def test_e14_2_extra_ext_ids_override(isolated_env: Path):
    """JSON-array override in .env must materialise as a tuple/list of ext ids."""
    payload = '["omni.a", "omni.b", "omni.c"]'
    (isolated_env / ".env").write_text(
        f"ISAAC_SIM_EXTRA_EXT_IDS={payload}\n", encoding="utf-8"
    )
    ac = _fresh_app_config()
    got = list(ac.isaac_sim_process.extra_ext_ids)
    assert got == ["omni.a", "omni.b", "omni.c"], (
        f"L14 regression — extra_ext_ids override dropped: got {got}"
    )


def test_e14_3_all_base_settings_declare_env_file():
    """Every ``BaseSettings`` subclass in config.py must set ``env_file='.env'``.

    AST-based guard so a missing declaration fails *at test time* instead of
    leaking through silently at runtime.
    """
    tree = ast.parse(CONFIG_PY.read_text(encoding="utf-8"))
    problems: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Class inherits BaseSettings (directly or via alias).
        inherits_basesettings = any(
            (isinstance(b, ast.Name) and b.id == "BaseSettings")
            or (isinstance(b, ast.Attribute) and b.attr == "BaseSettings")
            for b in node.bases
        )
        if not inherits_basesettings:
            continue

        env_file_value: str | None = None
        for item in node.body:
            if isinstance(item, ast.Assign):
                targets: list[ast.expr] = list(item.targets)
                value: ast.expr | None = item.value
            elif isinstance(item, ast.AnnAssign) and item.value is not None:
                targets = [item.target]
                value = item.value
            else:
                continue
            if not any(
                isinstance(t, ast.Name) and t.id == "model_config" for t in targets
            ):
                continue
            if isinstance(value, ast.Call):
                for kw in value.keywords:
                    if kw.arg == "env_file" and isinstance(kw.value, ast.Constant):
                        env_file_value = kw.value.value
            break

        if env_file_value != ".env":
            problems.append(f"{node.name}: env_file={env_file_value!r}")

    assert not problems, (
        "BaseSettings subclass(es) missing env_file='.env' (L14 regression risk):\n  "
        + "\n  ".join(problems)
    )
