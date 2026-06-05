"""Pure runtime configuration model for USD Mouse Interact Demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VALID_MODES = {"fps", "top_view", "button_mode"}
DEFAULT_RUN_CAMERA_PATH = "/World/kkr_temp_layer/Cams_AX_Living_Lab/s7_top_view"
CAMERA_SET_SIZE = 5
BUTTON_CAMERA_SET_SIZES = {"a": 5, "b": 6}
VALID_BUTTON_SHAPES = {"rect", "circle", "raised", "orb"}


@dataclass(slots=True, frozen=True)
class RuntimeConfig:
    default_mode: str = "button_mode"
    default_camera_path: str = DEFAULT_RUN_CAMERA_PATH
    speed: int = 500
    sensitivity: int = 25
    crosshair_color: int = 0xCC0000FF


@dataclass(slots=True, frozen=True)
class TopViewConfig:
    camera_path: str = ""
    lock_camera: bool = True


@dataclass(slots=True, frozen=True)
class ButtonConfig:
    label: str
    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float
    color: int = 0xEE3A4B5F
    text_color: int = 0xFFFFFFFF
    font_size: int = 0
    shape: str = "rect"
    set_id: str = "main"
    action: str = "capture"
    target_camera: str = ""
    next_set: str = ""


@dataclass(slots=True, frozen=True)
class ButtonModeConfig:
    buttons: dict[str, ButtonConfig]
    camera_sets: dict[str, list[str]]
    exploring_button: ButtonConfig
    dream_ai_button: ButtonConfig
    back_button: ButtonConfig
    final_preview_back_button: ButtonConfig
    button_style: "ButtonStyleConfig"
    preview_grid: "PreviewGridConfig"
    preview_overlay_scale: float = 1.0
    preview_width: int = 640
    preview_height: int = 360
    use_viewport_capture_fallback: bool = False
    tour_camera_hold_seconds: float = 5.0
    tour_final_hold_seconds: float = 5.0
    tour_matrix_hold_seconds: float = 7.0


@dataclass(slots=True, frozen=True)
class ButtonStyleConfig:
    button_color: int = 0xEE3A4B5F
    hover_color: int = 0xEE50667D
    text_color: int = 0xFFFFFFFF
    panel_color: int = 0xCC202020
    overlay_color: int = 0x33000000
    dim_overlay: bool = True
    preview_dim_opacity: float = 0.80
    tile_border_color: int = 0x99FFFFFF
    border_radius: int = 3
    font_size: int = 12


@dataclass(slots=True, frozen=True)
class PreviewGridConfig:
    center_x_pct: float = 0.5
    center_y_pct: float = 0.5


@dataclass(slots=True, frozen=True)
class UsdMouseInteractConfig:
    runtime: RuntimeConfig
    top_view: TopViewConfig
    button_mode: ButtonModeConfig

    @classmethod
    def default(cls) -> "UsdMouseInteractConfig":
        return cls(
            runtime=RuntimeConfig(),
            top_view=TopViewConfig(),
            button_mode=ButtonModeConfig(
                buttons={
                    "a": ButtonConfig(
                    "AX Living Lab",
                    0.13,
                    0.91,
                    0.18,
                    0.06,
                    color=0xFFB7FDFF,
                    text_color=0xFF000000,
                    font_size=33,
                    shape="rect",
                ),
                    "b": ButtonConfig(
                    "Data Center",
                    0.77,
                    0.05,
                    0.17,
                    0.06,
                    color=0xFFB7FDFF,
                    text_color=0xFF000000,
                    font_size=33,
                    shape="rect",
                ),
                },
                camera_sets={
                    "a": [
                        "/World/kkr_temp_layer/Cams_AX_Living_Lab/AX_overview",
                        "/World/kkr_temp_layer/Cams_AX_Living_Lab/AX_DC_rack_pipe2",
                        "/World/kkr_temp_layer/Cams_AX_Living_Lab/AX_DC_full",
                        "/World/kkr_temp_layer/Cams_AX_Living_Lab/AX_overview2",
                        "/World/kkr_temp_layer/Cams_AX_Living_Lab/AX_Rack_front",
                    ],
                    "b": [
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_45",
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_Front",
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_Top",
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_Imgine_AI",
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_Rack_E",
                        "/World/kkr_temp_layer/Cams_Dream_AI_DataCenter/DataCenter_Rack_F",
                    ],
                },
                exploring_button=ButtonConfig(
                    "Start",
                    0.14,
                    0.12,
                    0.10,
                    0.18,
                    font_size=52,
                    shape="orb",
                ),
                dream_ai_button=ButtonConfig(
                    "Dream-AI Space",
                    0.53,
                    0.88,
                    0.26,
                    0.09,
                    color=0xFF39CA2B,
                    text_color=0xFF000000,
                    font_size=42,
                    shape="rect",
                ),
                back_button=ButtonConfig("Back", 0.47, 0.91, 0.06, 0.04),
                final_preview_back_button=ButtonConfig(
                    "Back",
                    0.45,
                    0.85,
                    0.10,
                    0.05,
                    font_size=18,
                    shape="rect",
                ),
                button_style=ButtonStyleConfig(),
                preview_grid=PreviewGridConfig(),
                preview_overlay_scale=1.5,
                preview_width=640,
                preview_height=360,
                use_viewport_capture_fallback=False,
                tour_camera_hold_seconds=5.0,
                tour_final_hold_seconds=5.0,
                tour_matrix_hold_seconds=7.0,
            ),
        )


def config_to_dict(cfg: UsdMouseInteractConfig) -> dict[str, Any]:
    return {
        "runtime": {
            "default_mode": cfg.runtime.default_mode,
            "default_camera_path": cfg.runtime.default_camera_path,
            "speed": cfg.runtime.speed,
            "sensitivity": cfg.runtime.sensitivity,
            "crosshair_color": cfg.runtime.crosshair_color,
        },
        "top_view": {
            "camera_path": cfg.top_view.camera_path,
            "lock_camera": cfg.top_view.lock_camera,
        },
        "button_mode": {
            "buttons": {
                key: {
                    "label": button.label,
                    "x_pct": button.x_pct,
                    "y_pct": button.y_pct,
                    "w_pct": button.w_pct,
                    "h_pct": button.h_pct,
                    "color": button.color,
                    "text_color": button.text_color,
                    "font_size": button.font_size,
                    "shape": button.shape,
                    "set_id": button.set_id,
                    "action": button.action,
                    "target_camera": button.target_camera,
                    "next_set": button.next_set,
                }
                for key, button in cfg.button_mode.buttons.items()
            },
            "camera_sets": {
                key: list(paths)
                for key, paths in cfg.button_mode.camera_sets.items()
            },
            "exploring_button": {
                "label": cfg.button_mode.exploring_button.label,
                "x_pct": cfg.button_mode.exploring_button.x_pct,
                "y_pct": cfg.button_mode.exploring_button.y_pct,
                "w_pct": cfg.button_mode.exploring_button.w_pct,
                "h_pct": cfg.button_mode.exploring_button.h_pct,
                "color": cfg.button_mode.exploring_button.color,
                "text_color": cfg.button_mode.exploring_button.text_color,
                "font_size": cfg.button_mode.exploring_button.font_size,
                "shape": cfg.button_mode.exploring_button.shape,
            },
            "dream_ai_button": {
                "label": cfg.button_mode.dream_ai_button.label,
                "x_pct": cfg.button_mode.dream_ai_button.x_pct,
                "y_pct": cfg.button_mode.dream_ai_button.y_pct,
                "w_pct": cfg.button_mode.dream_ai_button.w_pct,
                "h_pct": cfg.button_mode.dream_ai_button.h_pct,
                "color": cfg.button_mode.dream_ai_button.color,
                "text_color": cfg.button_mode.dream_ai_button.text_color,
                "font_size": cfg.button_mode.dream_ai_button.font_size,
                "shape": cfg.button_mode.dream_ai_button.shape,
            },
            "back_button": {
                "label": cfg.button_mode.back_button.label,
                "x_pct": cfg.button_mode.back_button.x_pct,
                "y_pct": cfg.button_mode.back_button.y_pct,
                "w_pct": cfg.button_mode.back_button.w_pct,
                "h_pct": cfg.button_mode.back_button.h_pct,
                "color": cfg.button_mode.back_button.color,
                "text_color": cfg.button_mode.back_button.text_color,
                "font_size": cfg.button_mode.back_button.font_size,
                "shape": cfg.button_mode.back_button.shape,
            },
            "final_preview_back_button": {
                "label": cfg.button_mode.final_preview_back_button.label,
                "x_pct": cfg.button_mode.final_preview_back_button.x_pct,
                "y_pct": cfg.button_mode.final_preview_back_button.y_pct,
                "w_pct": cfg.button_mode.final_preview_back_button.w_pct,
                "h_pct": cfg.button_mode.final_preview_back_button.h_pct,
                "color": cfg.button_mode.final_preview_back_button.color,
                "text_color": cfg.button_mode.final_preview_back_button.text_color,
                "font_size": cfg.button_mode.final_preview_back_button.font_size,
                "shape": cfg.button_mode.final_preview_back_button.shape,
            },
            "button_style": {
                "button_color": cfg.button_mode.button_style.button_color,
                "hover_color": cfg.button_mode.button_style.hover_color,
                "text_color": cfg.button_mode.button_style.text_color,
                "panel_color": cfg.button_mode.button_style.panel_color,
                "overlay_color": cfg.button_mode.button_style.overlay_color,
                "dim_overlay": cfg.button_mode.button_style.dim_overlay,
                "preview_dim_opacity": cfg.button_mode.button_style.preview_dim_opacity,
                "tile_border_color": cfg.button_mode.button_style.tile_border_color,
                "border_radius": cfg.button_mode.button_style.border_radius,
                "font_size": cfg.button_mode.button_style.font_size,
            },
            "preview_grid": {
                "center_x_pct": cfg.button_mode.preview_grid.center_x_pct,
                "center_y_pct": cfg.button_mode.preview_grid.center_y_pct,
            },
            "preview_overlay_scale": cfg.button_mode.preview_overlay_scale,
            "preview_width": cfg.button_mode.preview_width,
            "preview_height": cfg.button_mode.preview_height,
            "use_viewport_capture_fallback": cfg.button_mode.use_viewport_capture_fallback,
            "tour_camera_hold_seconds": cfg.button_mode.tour_camera_hold_seconds,
            "tour_final_hold_seconds": cfg.button_mode.tour_final_hold_seconds,
            "tour_matrix_hold_seconds": cfg.button_mode.tour_matrix_hold_seconds,
        },
    }


def config_from_dict(raw: Any) -> UsdMouseInteractConfig:
    defaults = UsdMouseInteractConfig.default()
    data = raw if isinstance(raw, dict) else {}

    runtime_raw = _as_dict(data.get("runtime"))
    default_mode = str(runtime_raw.get("default_mode", defaults.runtime.default_mode))
    if default_mode not in VALID_MODES:
        default_mode = defaults.runtime.default_mode
    runtime = RuntimeConfig(
        default_mode=default_mode,
        default_camera_path=str(
            runtime_raw.get("default_camera_path", defaults.runtime.default_camera_path)
        ),
        speed=_clamp_int(runtime_raw.get("speed", defaults.runtime.speed), 1, 100000),
        sensitivity=_clamp_int(
            runtime_raw.get("sensitivity", defaults.runtime.sensitivity),
            1,
            100000,
        ),
        crosshair_color=_clamp_int(
            runtime_raw.get("crosshair_color", defaults.runtime.crosshair_color),
            0,
            0xFFFFFFFF,
        ),
    )

    top_view_raw = _as_dict(data.get("top_view"))
    top_view = TopViewConfig(
        camera_path=str(top_view_raw.get("camera_path", defaults.top_view.camera_path)),
        lock_camera=bool(top_view_raw.get("lock_camera", defaults.top_view.lock_camera)),
    )

    button_mode_raw = _as_dict(data.get("button_mode"))
    buttons_raw = _as_dict(button_mode_raw.get("buttons"))
    buttons = {
        key: _parse_button(buttons_raw.get(key), default_button)
        for key, default_button in defaults.button_mode.buttons.items()
    }
    for raw_key, raw_button in buttons_raw.items():
        key = _normalize_button_key(raw_key)
        if not key or key in buttons:
            continue
        buttons[key] = _parse_button(raw_button, _default_extra_button(key, len(buttons)))

    camera_sets_raw = _as_dict(button_mode_raw.get("camera_sets"))
    camera_sets = {
        key: _parse_camera_set(camera_sets_raw.get(key), default_paths, key=key)
        for key, default_paths in defaults.button_mode.camera_sets.items()
    }
    for key in buttons:
        if key not in camera_sets:
            camera_sets[key] = _parse_camera_set(
                camera_sets_raw.get(key),
                [""] * camera_set_size_for_key(key),
                key=key,
            )
    button_mode = ButtonModeConfig(
        buttons=buttons,
        camera_sets=camera_sets,
        exploring_button=_parse_button(
            button_mode_raw.get("exploring_button"),
            defaults.button_mode.exploring_button,
        ),
        dream_ai_button=_parse_button(
            button_mode_raw.get("dream_ai_button"),
            defaults.button_mode.dream_ai_button,
        ),
        back_button=_parse_button(
            button_mode_raw.get("back_button"),
            defaults.button_mode.back_button,
        ),
        final_preview_back_button=_parse_button(
            button_mode_raw.get("final_preview_back_button"),
            defaults.button_mode.final_preview_back_button,
        ),
        button_style=_parse_button_style(
            button_mode_raw.get("button_style"),
            defaults.button_mode.button_style,
        ),
        preview_grid=_parse_preview_grid(
            button_mode_raw.get("preview_grid"),
            defaults.button_mode.preview_grid,
        ),
        preview_overlay_scale=_clamp_float(
            button_mode_raw.get(
                "preview_overlay_scale",
                defaults.button_mode.preview_overlay_scale,
            ),
            0.5,
            2.0,
        ),
        preview_width=_clamp_int(
            button_mode_raw.get("preview_width", defaults.button_mode.preview_width),
            64,
            4096,
        ),
        preview_height=_clamp_int(
            button_mode_raw.get("preview_height", defaults.button_mode.preview_height),
            64,
            4096,
        ),
        use_viewport_capture_fallback=bool(
            button_mode_raw.get(
                "use_viewport_capture_fallback",
                defaults.button_mode.use_viewport_capture_fallback,
            )
        ),
        tour_camera_hold_seconds=_clamp_float(
            button_mode_raw.get(
                "tour_camera_hold_seconds",
                defaults.button_mode.tour_camera_hold_seconds,
            ),
            0.1,
            120.0,
        ),
        tour_final_hold_seconds=_clamp_float(
            button_mode_raw.get(
                "tour_final_hold_seconds",
                defaults.button_mode.tour_final_hold_seconds,
            ),
            0.1,
            120.0,
        ),
        tour_matrix_hold_seconds=_clamp_float(
            button_mode_raw.get(
                "tour_matrix_hold_seconds",
                defaults.button_mode.tour_matrix_hold_seconds,
            ),
            0.1,
            120.0,
        ),
    )

    return UsdMouseInteractConfig(
        runtime=runtime,
        top_view=top_view,
        button_mode=button_mode,
    )


def _parse_button(raw: Any, default: ButtonConfig) -> ButtonConfig:
    data = _as_dict(raw)
    return ButtonConfig(
        label=str(data.get("label", default.label)),
        x_pct=_clamp_float(data.get("x_pct", default.x_pct), 0.0, 1.0),
        y_pct=_clamp_float(data.get("y_pct", default.y_pct), 0.0, 1.0),
        w_pct=_clamp_float(data.get("w_pct", default.w_pct), 0.01, 1.0),
        h_pct=_clamp_float(data.get("h_pct", default.h_pct), 0.01, 1.0),
        color=_clamp_int(data.get("color", default.color), 0, 0xFFFFFFFF),
        text_color=_clamp_int(data.get("text_color", default.text_color), 0, 0xFFFFFFFF),
        font_size=_clamp_int(data.get("font_size", default.font_size), 0, 96),
        shape=_clean_button_shape(data.get("shape", default.shape)),
        set_id=_clean_set_id(data.get("set_id", default.set_id)),
        action=_clean_button_action(data.get("action", default.action)),
        target_camera=str(data.get("target_camera", default.target_camera)),
        next_set=_clean_set_id(data.get("next_set", default.next_set), allow_empty=True),
    )


def _parse_camera_set(raw: Any, default: list[str], *, key: str = "") -> list[str]:
    try:
        values = list(raw) if raw is not None else list(default)
    except TypeError:
        values = list(default)
    size = camera_set_size_for_key(key, default_size=len(default) or CAMERA_SET_SIZE)
    normalized = [str(value) for value in values[:size]]
    while len(normalized) < size:
        normalized.append("")
    return normalized


def camera_set_size_for_key(key: str, *, default_size: int = CAMERA_SET_SIZE) -> int:
    return int(BUTTON_CAMERA_SET_SIZES.get(str(key).strip().lower(), default_size))


def _normalize_button_key(raw: Any) -> str:
    text = str(raw).strip().lower()
    return text if text else ""


def _default_extra_button(key: str, index: int) -> ButtonConfig:
    column = max(0, index - 2)
    x_pct = min(0.82, 0.08 + column * 0.12)
    y_pct = max(0.05, 0.74 - column * 0.06)
    return ButtonConfig(key.replace("_", " ").title(), x_pct, y_pct, 0.10, 0.045)


def _clean_set_id(raw: Any, allow_empty: bool = False) -> str:
    text = str(raw).strip() if raw is not None else ""
    if not text:
        return "" if allow_empty else "main"
    return text


def _clean_button_action(raw: Any) -> str:
    text = str(raw).strip().lower()
    return text if text in {"capture", "switch"} else "capture"


def _clean_button_shape(raw: Any) -> str:
    text = str(raw).strip().lower()
    return text if text in VALID_BUTTON_SHAPES else "rect"


def _parse_button_style(raw: Any, default: ButtonStyleConfig) -> ButtonStyleConfig:
    data = _as_dict(raw)
    return ButtonStyleConfig(
        button_color=_clamp_int(data.get("button_color", default.button_color), 0, 0xFFFFFFFF),
        hover_color=_clamp_int(data.get("hover_color", default.hover_color), 0, 0xFFFFFFFF),
        text_color=_clamp_int(data.get("text_color", default.text_color), 0, 0xFFFFFFFF),
        panel_color=_clamp_int(data.get("panel_color", default.panel_color), 0, 0xFFFFFFFF),
        overlay_color=_clamp_int(data.get("overlay_color", default.overlay_color), 0, 0xFFFFFFFF),
        dim_overlay=bool(data.get("dim_overlay", default.dim_overlay)),
        preview_dim_opacity=_clamp_float(
            data.get("preview_dim_opacity", default.preview_dim_opacity),
            0.0,
            1.0,
        ),
        tile_border_color=_clamp_int(
            data.get("tile_border_color", default.tile_border_color),
            0,
            0xFFFFFFFF,
        ),
        border_radius=_clamp_int(data.get("border_radius", default.border_radius), 0, 24),
        font_size=_clamp_int(data.get("font_size", default.font_size), 8, 32),
    )


def _parse_preview_grid(raw: Any, default: PreviewGridConfig) -> PreviewGridConfig:
    data = _as_dict(raw)
    return PreviewGridConfig(
        center_x_pct=_clamp_float(
            data.get("center_x_pct", default.center_x_pct),
            0.0,
            1.0,
        ),
        center_y_pct=_clamp_float(
            data.get("center_y_pct", default.center_y_pct),
            0.0,
            1.0,
        ),
    )


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _clamp_int(raw: Any, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = minimum
    return max(minimum, min(maximum, value))


def _clamp_float(raw: Any, minimum: float, maximum: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = minimum
    return max(minimum, min(maximum, value))
