import re
from pathlib import Path

import yaml

from shorts_creator.contracts.capabilities import CapabilityVocabularyError, parse_capabilities
from shorts_creator.contracts.errors import FormatContractError
from shorts_creator.contracts.pipeline import PIPELINE_CAPABILITIES
from shorts_creator.formats.base import FormatDefinition

_FORMAT_MD_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

_CONTRACT_KEYS = ("script", "voice", "pipeline", "assets")


def parse_format_md(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")
    match = _FORMAT_MD_PATTERN.match(content)
    if not match:
        raise ValueError(f"Missing YAML frontmatter in {md_path}")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    return frontmatter


def validate_format_contract(frontmatter: dict) -> None:
    """Validate a format's contract declarations against the closed
    vocabulary and the implemented pipeline. Raises CapabilityVocabularyError
    or ValueError on violations, so a bad format can never load silently."""
    requires = frontmatter.get("requires") or {}
    for key, raw in requires.items():
        if key not in _CONTRACT_KEYS:
            raise FormatContractError(
                f"unknown requires key {key!r}; valid keys: {', '.join(_CONTRACT_KEYS)}"
            )
        parse_capabilities(raw, key)
    for name in parse_capabilities(requires.get("pipeline"), "pipeline"):
        if name not in PIPELINE_CAPABILITIES:
            raise FormatContractError(
                f"pipeline does not implement {name!r}; implemented: "
                f"{', '.join(sorted(PIPELINE_CAPABILITIES))}"
            )
    parse_capabilities(frontmatter.get("assets"), "assets")

    layout = frontmatter.get("layout") or {}
    palette = frontmatter.get("palette") or {}
    _validate_layout_palette(layout, palette)
    _validate_defaults(frontmatter.get("defaults") or {})


_LAYOUT_KEYS = {"anchor", "block_width_pct", "numbered_scale", "pill_per_word"}
_ANCHORS = {"center", "lower_third"}
_PALETTE_KEYS = {"highlight_colour", "pill_bg_colour"}
_HEX_RE = re.compile(r"^0x[0-9A-Fa-f]{8}$")

_ALLOWED_DEFAULTS = {
    "caption_font_size",
    "caption_max_words",
    "caption_highlight_colour",
    "caption_outline_width",
    "hook_min_font_size",
    "hook_max_font_size",
    "hook_char_width_factor",
    "hook_line_height_factor",
    "hook_block_width_pct",
    "hook_block_height_pct",
    "hook_line_gap_px",
    "hook_line_target_size",
    "ranked_number_scale",
    "anchor",
    "pill_bg_colour",
    "watermark_size_pct",
    "watermark_opacity",
    "watermark_margin_px",
    "watermark_corner",
    "music_volume",
    "music_fade_seconds",
    "fade_out_seconds",
    "caption_uppercase",
    "caption_scrim_alpha",
    "loudness_target_lufs",
    "audio_normalize",
    "background_motion",
    "emphasis_style",
    "section_holds",
    "stage_accents",
}

_BACKGROUND_MOTIONS = {"none", "pan", "zoom"}
_WATERMARK_CORNERS = {"bottom_right", "bottom_left", "top_right", "top_left"}
_EMPHASIS_STYLES = {"off", "accent", "scale"}
_ENUM_DEFAULTS = {
    "anchor": _ANCHORS,
    "background_motion": _BACKGROUND_MOTIONS,
    "watermark_corner": _WATERMARK_CORNERS,
    "emphasis_style": _EMPHASIS_STYLES,
}
_BOOL_DEFAULTS = {"audio_normalize", "caption_uppercase"}
_COLOUR_DEFAULTS = {"caption_highlight_colour", "pill_bg_colour"}
_NUMERIC_DEFAULTS = {
    "caption_font_size",
    "caption_max_words",
    "caption_outline_width",
    "hook_min_font_size",
    "hook_max_font_size",
    "hook_char_width_factor",
    "hook_line_height_factor",
    "hook_block_width_pct",
    "hook_block_height_pct",
    "hook_line_gap_px",
    "hook_line_target_size",
    "ranked_number_scale",
    "watermark_size_pct",
    "watermark_opacity",
    "watermark_margin_px",
    "music_volume",
    "music_fade_seconds",
    "fade_out_seconds",
    "caption_scrim_alpha",
    "loudness_target_lufs",
}


def _is_hex_colour(value: object) -> bool:
    if isinstance(value, str):
        return bool(_HEX_RE.match(value))
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xFFFFFFFF


def _validate_layout_palette(layout: dict, palette: dict) -> None:
    for key in layout:
        if key not in _LAYOUT_KEYS:
            raise FormatContractError(
                f"unknown layout key {key!r}; valid: {', '.join(sorted(_LAYOUT_KEYS))}"
            )
    if layout.get("anchor") is not None and layout["anchor"] not in _ANCHORS:
        raise FormatContractError(
            f"unknown anchor {layout['anchor']!r}; valid: {', '.join(sorted(_ANCHORS))}"
        )
    for key in ("block_width_pct", "numbered_scale"):
        if key not in layout:
            continue
        value = layout[key]
        if not (isinstance(value, (list, tuple)) and len(value) == 2):
            raise FormatContractError(f"layout.{key} must be a [min, max] list, got {value!r}")
        if not all(isinstance(v, (int, float)) for v in value) or value[0] > value[1]:
            raise FormatContractError(f"layout.{key} must be [min, max] with min <= max")
    if layout.get("pill_per_word") is not None and not isinstance(layout["pill_per_word"], bool):
        raise FormatContractError("layout.pill_per_word must be a boolean")
    for key, value in palette.items():
        if key not in _PALETTE_KEYS:
            raise FormatContractError(
                f"unknown palette key {key!r}; valid: {', '.join(sorted(_PALETTE_KEYS))}"
            )
        if not _is_hex_colour(value):
            raise FormatContractError(f"palette.{key} must be a 0xRRGGBBAA colour")


def _validate_defaults(defaults: dict) -> None:
    for key, value in defaults.items():
        if key not in _ALLOWED_DEFAULTS:
            raise FormatContractError(
                f"unknown defaults key {key!r}; valid: {', '.join(sorted(_ALLOWED_DEFAULTS))}"
            )
        if key in _ENUM_DEFAULTS:
            allowed = _ENUM_DEFAULTS[key]
            if value not in allowed:
                raise FormatContractError(
                    f"defaults.{key} must be one of {', '.join(sorted(allowed))}, got {value!r}"
                )
        elif key in _BOOL_DEFAULTS:
            if not isinstance(value, bool):
                raise FormatContractError(f"defaults.{key} must be a boolean")
        elif key in _COLOUR_DEFAULTS:
            if not _is_hex_colour(value):
                raise FormatContractError(f"defaults.{key} must be a 0xRRGGBBAA colour")
        elif key in _NUMERIC_DEFAULTS:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise FormatContractError(f"defaults.{key} must be a number")
        elif key == "section_holds":
            if not isinstance(value, dict):
                raise FormatContractError("defaults.section_holds must be a mapping")
            for section, hold in value.items():
                if not isinstance(hold, (int, float)) or isinstance(hold, bool):
                    raise FormatContractError(f"defaults.section_holds.{section} must be a number")
        elif key == "stage_accents":
            if not isinstance(value, dict):
                raise FormatContractError("defaults.stage_accents must be a mapping")
            for stage, colour in value.items():
                if not _is_hex_colour(colour):
                    raise FormatContractError(
                        f"defaults.stage_accents.{stage} must be a 0xRRGGBBAA colour"
                    )


def load_format(md_path: Path) -> FormatDefinition:
    frontmatter = parse_format_md(md_path)
    validate_format_contract(frontmatter)
    return FormatDefinition.from_dict(frontmatter)


def is_contract_violation(exc: Exception) -> bool:
    """True for loader failures caused by contract violations (as opposed to
    non-contract breakage like missing frontmatter or bad YAML)."""
    return isinstance(exc, (FormatContractError, CapabilityVocabularyError))
