from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

ANCHORS = ("center", "lower_third")
_WATERMARK_CORNERS = ("bottom_right", "bottom_left", "top_right", "top_left")
_EMPHASIS_STYLES = ("off", "accent", "scale")
_BACKGROUND_MOTIONS = ("none", "pan", "zoom")
_HEX_RE = re.compile(r"^0x[0-9A-Fa-f]{8}$")

# Named stage-accent colours the composer UI offers for per-stage caption
# highlights (stage_accents). Lives outside ui/ so the rendered page can
# present readable names while the pipeline keeps 0xRRGGBBAA colours.
STAGE_ACCENT_PALETTE: dict[str, str] = {
    "violet": "0x7C5CFAFF",
    "cyan": "0x22D3EEFF",
    "emerald": "0x34D399FF",
    "amber": "0xFBBF24FF",
    "rose": "0xFB7185FF",
}

# Built-in defaults — the historical module constants (pipeline.py:380-398,
# RANKED_NUMBER_SCALE at pipeline.py:286, HOOK_LINE_TARGET_SIZE captions.py:2).
_DEFAULTS = {
    "caption_font_size": 56,
    "caption_max_words": 3,
    "caption_highlight_colour": "0x7C5CFAFF",
    "caption_outline_width": 2,
    "hook_min_font_size": 40,
    "hook_max_font_size": 110,
    "hook_char_width_factor": 0.55,
    "hook_line_height_factor": 1.3,
    "hook_block_width_pct": 80,
    "hook_block_height_pct": 70,
    "hook_line_gap_px": 18,
    "hook_line_target_size": 1,
    "ranked_number_scale": 1.6,
    "anchor": "center",
    "pill_bg_colour": "0x000000C0",
    "watermark_size_pct": 10.0,
    "watermark_opacity": 0.85,
    "watermark_margin_px": 48,
    "watermark_corner": "bottom_right",
    "music_volume": 0.2,
    "music_fade_seconds": 2.0,
    "fade_out_seconds": 1.0,
    "caption_uppercase": False,
    "caption_scrim_alpha": 0.0,
}


def colour_is_hex(value: Any) -> bool:
    return isinstance(value, str) and bool(_HEX_RE.match(value))


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class RenderConfig(BaseModel):
    """Validated per-render visual settings.

    Defaults equal the module constants they replace, so a bare
    ``RenderConfig()`` renders exactly like today. Format declarations
    (FORMAT.md ``layout:``/``palette:``) and project overrides are merged
    on top by ``RenderConfig.resolve`` (spec §4).
    """

    model_config = ConfigDict(frozen=True)

    caption_font_size: int = 56
    caption_max_words: int = 3
    caption_highlight_colour: str = "0x7C5CFAFF"
    caption_outline_width: int = 2
    hook_min_font_size: int = 40
    hook_max_font_size: int = 110
    hook_char_width_factor: float = 0.55
    hook_line_height_factor: float = 1.3
    hook_block_width_pct: int = 80
    hook_block_height_pct: int = 70
    hook_line_gap_px: int = 18
    hook_line_target_size: int = 1
    ranked_number_scale: float = 1.6
    anchor: str = "center"
    pill_bg_colour: str = "0x000000C0"
    watermark_size_pct: float = 10.0
    watermark_opacity: float = 0.85
    watermark_margin_px: int = 48
    watermark_corner: str = "bottom_right"
    music_volume: float = 0.2
    music_fade_seconds: float = 2.0
    fade_out_seconds: float = 1.0
    caption_uppercase: bool = False
    caption_scrim_alpha: float = 0.0
    loudness_target_lufs: float = -14.0
    audio_normalize: bool = True
    stage_accents: dict = {}
    section_holds: dict = {}
    emphasis_style: str = "accent"
    background_motion: str = "none"

    @field_validator("anchor")
    @classmethod
    def _anchor_valid(cls, value: str) -> str:
        if value not in ANCHORS:
            raise ValueError(f"unknown anchor {value!r}; valid: {', '.join(ANCHORS)}")
        return value

    @field_validator("watermark_corner")
    @classmethod
    def _corner_valid(cls, value: str) -> str:
        if value not in _WATERMARK_CORNERS:
            raise ValueError(
                f"unknown watermark corner {value!r}; valid: {', '.join(_WATERMARK_CORNERS)}"
            )
        return value

    @field_validator("emphasis_style")
    @classmethod
    def _emphasis_style_valid(cls, value: str) -> str:
        if value not in _EMPHASIS_STYLES:
            raise ValueError(
                f"unknown emphasis_style {value!r}; valid: {', '.join(_EMPHASIS_STYLES)}"
            )
        return value

    @field_validator("background_motion")
    @classmethod
    def _background_motion_valid(cls, value: str) -> str:
        if value not in _BACKGROUND_MOTIONS:
            raise ValueError(
                f"unknown background_motion {value!r}; valid: {', '.join(_BACKGROUND_MOTIONS)}"
            )
        return value

    @field_validator("caption_highlight_colour", "pill_bg_colour")
    @classmethod
    def _colour_valid(cls, value: str) -> str:
        if not colour_is_hex(value):
            raise ValueError(f"{value!r} is not a 0xRRGGBBAA colour")
        return value

    @classmethod
    def from_format(cls, fmt) -> RenderConfig:
        """Merge a format's FORMAT.md ``layout:``/``palette:`` declarations
        over the built-in defaults. Ranges are declaration metadata for the
        UI; only scalar defaults are applied here."""
        layout = dict(getattr(fmt, "layout", {}) or {})
        palette = dict(getattr(fmt, "palette", {}) or {})
        kwargs: dict[str, Any] = {}
        if layout.get("anchor") in ANCHORS:
            kwargs["anchor"] = layout["anchor"]
        if layout.get("pill_per_word") is not None:
            kwargs["hook_line_target_size"] = 1 if layout["pill_per_word"] else 4
        if palette.get("highlight_colour") and colour_is_hex(palette["highlight_colour"]):
            kwargs["caption_highlight_colour"] = palette["highlight_colour"]
        if palette.get("pill_bg_colour") and colour_is_hex(palette["pill_bg_colour"]):
            kwargs["pill_bg_colour"] = palette["pill_bg_colour"]
        return cls(**kwargs)

    @classmethod
    def resolve(cls, fmt=None, overrides: dict | None = None) -> RenderConfig:
        """built-in defaults ← format declarations ← format ``defaults`` ← project overrides.

        Format ``layout``/``palette`` declarations are applied first, then the
        format's per-format ``defaults`` on top (so e.g. ``defaults.anchor``
        overrides ``layout.anchor``); project overrides win over both. Project
        overrides are clamped to the format's declared slider ranges for block
        width and numbered scale; out-of-range values are clamped silently
        (the resolved spec shows the clamped value)."""
        base = cls.from_format(fmt) if fmt is not None else cls()
        if fmt is not None:
            fmt_defaults = {
                k: v
                for k, v in dict(getattr(fmt, "defaults", None) or {}).items()
                if k in cls.model_fields
            }
            if fmt_defaults:
                base = base.model_copy(update=fmt_defaults)
        ov = dict(overrides or {})
        layout = dict(ov.get("layout") or {})
        palette = dict(ov.get("palette") or {})
        style = dict(ov.get("style") or {})
        fmt_layout = dict(getattr(fmt, "layout", {}) or {}) if fmt is not None else {}

        kwargs: dict[str, Any] = {}
        if style.get("chunk_size"):
            kwargs["caption_max_words"] = int(style["chunk_size"])
        if style.get("caption_font_size") is not None:
            kwargs["caption_font_size"] = int(style["caption_font_size"])
        if style.get("caption_outline_width") is not None:
            kwargs["caption_outline_width"] = int(style["caption_outline_width"])
        if palette.get("highlight_colour") and colour_is_hex(palette["highlight_colour"]):
            kwargs["caption_highlight_colour"] = palette["highlight_colour"]
        if palette.get("pill_bg_colour") and colour_is_hex(palette["pill_bg_colour"]):
            kwargs["pill_bg_colour"] = palette["pill_bg_colour"]
        if layout.get("anchor") in ANCHORS:
            kwargs["anchor"] = layout["anchor"]
        if layout.get("pill_per_word") is not None:
            kwargs["hook_line_target_size"] = 1 if layout["pill_per_word"] else 4

        declared = fmt_layout.get("block_width_pct") or []
        if isinstance(declared, (list, tuple)) and len(declared) == 2:
            lo, hi = int(declared[0]), int(declared[1])
            if layout.get("block_width_pct") is not None:
                kwargs["hook_block_width_pct"] = max(lo, min(hi, int(layout["block_width_pct"])))
            else:
                kwargs["hook_block_width_pct"] = base.hook_block_width_pct
        else:
            if layout.get("block_width_pct") is not None:
                kwargs["hook_block_width_pct"] = int(layout["block_width_pct"])

        declared = fmt_layout.get("numbered_scale") or []
        if isinstance(declared, (list, tuple)) and len(declared) == 2:
            f_lo, f_hi = float(declared[0]), float(declared[1])
            if layout.get("numbered_scale") is not None:
                kwargs["ranked_number_scale"] = max(
                    f_lo, min(f_hi, float(layout["numbered_scale"]))
                )
        else:
            if layout.get("numbered_scale") is not None:
                kwargs["ranked_number_scale"] = float(layout["numbered_scale"])

        size_pct = _as_number(layout.get("watermark_size_pct"))
        if size_pct is not None:
            kwargs["watermark_size_pct"] = max(5.0, min(30.0, size_pct))
        opacity = _as_number(layout.get("watermark_opacity"))
        if opacity is not None:
            kwargs["watermark_opacity"] = max(0.1, min(1.0, opacity))
        margin_px = _as_number(layout.get("watermark_margin_px"))
        if margin_px is not None:
            kwargs["watermark_margin_px"] = max(0, min(200, int(margin_px)))
        if layout.get("watermark_corner") in _WATERMARK_CORNERS:
            kwargs["watermark_corner"] = layout["watermark_corner"]
        music_volume = _as_number(layout.get("music_volume"))
        if music_volume is not None:
            kwargs["music_volume"] = max(0.05, min(0.5, music_volume))
        music_fade = _as_number(layout.get("music_fade_seconds"))
        if music_fade is not None:
            kwargs["music_fade_seconds"] = max(0.5, min(6.0, music_fade))
        fade_out = _as_number(layout.get("fade_out_seconds"))
        if fade_out is not None:
            kwargs["fade_out_seconds"] = max(0.0, min(3.0, fade_out))
        if isinstance(style.get("uppercase"), bool):
            kwargs["caption_uppercase"] = style["uppercase"]
        scrim_alpha = _as_number(style.get("scrim_alpha"))
        if scrim_alpha is not None:
            kwargs["caption_scrim_alpha"] = max(0.0, min(1.0, scrim_alpha))

        if isinstance(ov.get("stage_accents"), dict):
            kwargs["stage_accents"] = dict(ov["stage_accents"])

        if isinstance(style.get("stage_accents"), dict):
            kwargs["stage_accents"] = dict(style["stage_accents"])

        motion = style.get("background_motion") or ov.get("background_motion")
        if motion in ("none", "pan", "zoom"):
            kwargs["background_motion"] = motion
        emphasis = style.get("emphasis_style") or ov.get("emphasis_style")
        if emphasis in ("off", "accent", "scale"):
            kwargs["emphasis_style"] = emphasis
        lufs = style.get("loudness_target_lufs")
        if lufs is None:
            lufs = ov.get("loudness_target_lufs")
        lufs = _as_number(lufs)
        if lufs is not None:
            kwargs["loudness_target_lufs"] = max(-30.0, min(0.0, lufs))
        normalize = style.get("audio_normalize")
        if not isinstance(normalize, bool):
            normalize = ov.get("audio_normalize")
        if isinstance(normalize, bool):
            kwargs["audio_normalize"] = normalize
        holds = style.get("section_holds")
        if not isinstance(holds, dict):
            holds = ov.get("section_holds")
        if isinstance(holds, dict):
            # Holds are signed seconds: positive lengthens, negative shortens
            # the on-screen window; non-numeric values (strings, bools) drop.
            kwargs["section_holds"] = {
                k: float(v)
                for k, v in holds.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }

        return base.model_copy(update=kwargs)
