from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

from shorts_creator.formats import registry

T = TypeVar("T")


class ProfileSource(str, Enum):
    PROJECT = "project"
    FORMAT = "format"
    GLOBAL = "global"
    BUILT_IN = "built_in"


class ProjectProfileOverrides(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    duration_seconds: float | None = None
    caption_style: str | None = None
    format_name: str | None = None
    asset_music_id: str | None = None
    asset_font_id: str | None = None
    asset_bg_clip_id: str | None = None
    asset_outro_clip_id: str | None = None
    asset_watermark_id: str | None = None
    media_url_music: str | None = None
    media_url_bg_clip: str | None = None
    media_url_outro: str | None = None
    media_url_watermark: str | None = None
    bg_source: str | None = None
    bg_mode: str | None = None
    stock_provider: str | None = None
    pacing_wps: float | None = None
    hook_text: str | None = None
    outro_text: str | None = None
    audience_persona: str | None = None
    banned_topics: list[str] | None = None
    tone_rules: list[str] | None = None
    voice_preset: str | None = None
    hook_lead_in_seconds: float | None = None
    sections: list[str] | None = None
    section_texts: dict[str, str] | None = None
    style: dict | None = None
    palette: dict | None = None
    layout: dict | None = None
    stages: dict | None = None
    stage_accents: dict | None = None
    section_holds: dict | None = None
    background_motion: str | None = None
    loudness_target_lufs: float | None = None
    audio_normalize: bool | None = None
    emphasis_style: str | None = None


class ResolvedSetting(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    value: T
    source: ProfileSource
    is_overridden: bool

    def __init__(self, value: T, source: ProfileSource, is_overridden: bool):
        super().__init__(value=value, source=source, is_overridden=is_overridden)


PROFILE_FIELD_NAMES = (
    "duration_seconds",
    "caption_style",
    "format_name",
    "asset_music_id",
    "asset_font_id",
    "asset_bg_clip_id",
    "asset_outro_clip_id",
    "asset_watermark_id",
    "media_url_music",
    "media_url_bg_clip",
    "media_url_outro",
    "media_url_watermark",
    "bg_source",
    "bg_mode",
    "stock_provider",
    "topic",
    "reel_width",
    "reel_height",
    "pacing_wps",
    "hook_text",
    "outro_text",
    "audience_persona",
    "banned_topics",
    "tone_rules",
    "voice_preset",
    "hook_lead_in_seconds",
    "sections",
    "section_texts",
    "style",
    "palette",
    "layout",
    "stages",
    "stage_accents",
    "section_holds",
    "background_motion",
    "loudness_target_lufs",
    "audio_normalize",
    "emphasis_style",
)


_SOURCE_ALIASES = {
    "duration_seconds": "duration_source",
}

_COMPOSER_SNAPSHOT_FIELDS = (
    "pacing_wps",
    "hook_text",
    "outro_text",
    "audience_persona",
    "banned_topics",
    "tone_rules",
    "voice_preset",
    "hook_lead_in_seconds",
    "sections",
    "section_texts",
    "style",
    "palette",
    "layout",
    "stages",
    "stage_accents",
    "section_holds",
    "background_motion",
    "loudness_target_lufs",
    "audio_normalize",
    "emphasis_style",
)


class EffectiveProjectProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    duration_seconds: ResolvedSetting[float] | None = None
    caption_style: ResolvedSetting[str] | None = None
    format_name: ResolvedSetting[str] | None = None
    asset_music_id: ResolvedSetting[str | None] | None = None
    asset_font_id: ResolvedSetting[str | None] | None = None
    asset_bg_clip_id: ResolvedSetting[str | None] | None = None
    asset_outro_clip_id: ResolvedSetting[str | None] | None = None
    asset_watermark_id: ResolvedSetting[str | None] | None = None
    media_url_music: ResolvedSetting[str | None] | None = None
    media_url_bg_clip: ResolvedSetting[str | None] | None = None
    media_url_outro: ResolvedSetting[str | None] | None = None
    media_url_watermark: ResolvedSetting[str | None] | None = None
    bg_source: ResolvedSetting[str | None] | None = None
    bg_mode: ResolvedSetting[str | None] | None = None
    stock_provider: ResolvedSetting[str | None] | None = None
    topic: ResolvedSetting[str] | None = None
    reel_width: ResolvedSetting[int] | None = None
    reel_height: ResolvedSetting[int] | None = None
    pacing_wps: ResolvedSetting[float | None] | None = None
    hook_text: ResolvedSetting[str | None] | None = None
    outro_text: ResolvedSetting[str | None] | None = None
    audience_persona: ResolvedSetting[str | None] | None = None
    banned_topics: ResolvedSetting[list[str] | None] | None = None
    tone_rules: ResolvedSetting[list[str] | None] | None = None
    voice_preset: ResolvedSetting[str | None] | None = None
    hook_lead_in_seconds: ResolvedSetting[float | None] | None = None
    sections: ResolvedSetting[list[str] | None] | None = None
    section_texts: ResolvedSetting[dict[str, str] | None] | None = None
    style: ResolvedSetting[dict | None] | None = None
    palette: ResolvedSetting[dict | None] | None = None
    layout: ResolvedSetting[dict | None] | None = None
    stages: ResolvedSetting[dict | None] | None = None
    stage_accents: ResolvedSetting[dict | None] | None = None
    section_holds: ResolvedSetting[dict | None] | None = None
    background_motion: ResolvedSetting[str | None] | None = None
    loudness_target_lufs: ResolvedSetting[float | None] | None = None
    audio_normalize: ResolvedSetting[bool | None] | None = None
    emphasis_style: ResolvedSetting[str | None] | None = None

    @model_validator(mode="before")
    @classmethod
    def _attach_sources(cls, data):
        if not isinstance(data, dict):
            return data
        for name in PROFILE_FIELD_NAMES:
            value = data.get(name)
            if value is None or isinstance(value, ResolvedSetting):
                continue
            source = data.pop(f"{name}_source", None)
            if source is None:
                source = data.pop(_SOURCE_ALIASES.get(name, ""), None)
            source = ProfileSource(source) if source else ProfileSource.BUILT_IN
            data[name] = ResolvedSetting(
                value=value,
                source=source,
                is_overridden=source is ProfileSource.PROJECT,
            )
        return data

    def snapshot_dict(self) -> dict[str, object]:
        # Task 4 will retain per-field provenance/source in the snapshot;
        # its shape is intentionally unchanged here.
        snapshot = {}
        for name in PROFILE_FIELD_NAMES:
            setting = getattr(self, name)
            value = setting.value if setting is not None else None
            if name in _COMPOSER_SNAPSHOT_FIELDS and value in (None, "", {}, []):
                continue
            snapshot[name] = value
        return snapshot

    @property
    def duration_source(self) -> ProfileSource | None:
        return self.duration_seconds.source if self.duration_seconds else None

    @property
    def caption_style_source(self) -> ProfileSource | None:
        return self.caption_style.source if self.caption_style else None

    @property
    def format_name_source(self) -> ProfileSource | None:
        return self.format_name.source if self.format_name else None

    @property
    def asset_music_id_source(self) -> ProfileSource | None:
        return self.asset_music_id.source if self.asset_music_id else None

    @property
    def asset_font_id_source(self) -> ProfileSource | None:
        return self.asset_font_id.source if self.asset_font_id else None

    @property
    def asset_bg_clip_id_source(self) -> ProfileSource | None:
        return self.asset_bg_clip_id.source if self.asset_bg_clip_id else None

    @property
    def asset_outro_clip_id_source(self) -> ProfileSource | None:
        return self.asset_outro_clip_id.source if self.asset_outro_clip_id else None

    @property
    def asset_watermark_id_source(self) -> ProfileSource | None:
        return self.asset_watermark_id.source if self.asset_watermark_id else None

    @property
    def topic_source(self) -> ProfileSource | None:
        return self.topic.source if self.topic else None

    @property
    def reel_width_source(self) -> ProfileSource | None:
        return self.reel_width.source if self.reel_width else None

    @property
    def reel_height_source(self) -> ProfileSource | None:
        return self.reel_height.source if self.reel_height else None

    @property
    def pacing_wps_source(self) -> ProfileSource | None:
        return self.pacing_wps.source if self.pacing_wps else None

    @property
    def hook_text_source(self) -> ProfileSource | None:
        return self.hook_text.source if self.hook_text else None

    @property
    def outro_text_source(self) -> ProfileSource | None:
        return self.outro_text.source if self.outro_text else None

    @property
    def audience_persona_source(self) -> ProfileSource | None:
        return self.audience_persona.source if self.audience_persona else None

    @property
    def banned_topics_source(self) -> ProfileSource | None:
        return self.banned_topics.source if self.banned_topics else None

    @property
    def tone_rules_source(self) -> ProfileSource | None:
        return self.tone_rules.source if self.tone_rules else None

    @property
    def voice_preset_source(self) -> ProfileSource | None:
        return self.voice_preset.source if self.voice_preset else None

    @property
    def hook_lead_in_seconds_source(self) -> ProfileSource | None:
        return self.hook_lead_in_seconds.source if self.hook_lead_in_seconds else None

    @property
    def sections_source(self) -> ProfileSource | None:
        return self.sections.source if self.sections else None

    @property
    def section_texts_source(self) -> ProfileSource | None:
        return self.section_texts.source if self.section_texts else None

    @property
    def style_source(self) -> ProfileSource | None:
        return self.style.source if self.style else None

    @property
    def palette_source(self) -> ProfileSource | None:
        return self.palette.source if self.palette else None

    @property
    def layout_source(self) -> ProfileSource | None:
        return self.layout.source if self.layout else None

    @property
    def stages_source(self) -> ProfileSource | None:
        return self.stages.source if self.stages else None


SUPPORTED_CAPTION_STYLES = ("highlight", "plain", "list")
SUPPORTED_BG_MODES = frozenset({"", "video", "image"})
SUPPORTED_STOCK_PROVIDERS = frozenset({"auto", "pexels", "pixabay"})


def validate_profile(values: dict) -> dict[str, str]:
    errors: dict[str, str] = {}

    duration = _as_float(values.get("duration_seconds"))
    if "duration_seconds" in values:
        if duration is None:
            errors["duration_seconds"] = "must be a number"
        elif duration <= 0:
            errors["duration_seconds"] = "must be greater than zero"

    caption_style = values.get("caption_style")
    if caption_style and caption_style not in SUPPORTED_CAPTION_STYLES:
        errors["caption_style"] = "unsupported caption style"

    format_name = values.get("format_name")
    if format_name is not None and not registry.has(format_name):
        errors["format_name"] = "unsupported format name"

    stock_provider = values.get("stock_provider")
    if stock_provider and stock_provider not in SUPPORTED_STOCK_PROVIDERS:
        errors["stock_provider"] = "unsupported stock provider"

    bg_mode = values.get("bg_mode")
    if bg_mode and bg_mode not in SUPPORTED_BG_MODES:
        errors["bg_mode"] = "unsupported background mode"

    pacing = _as_float(values.get("pacing_wps"))
    if "pacing_wps" in values:
        if pacing is None:
            errors["pacing_wps"] = "must be a number"
        elif pacing <= 0:
            errors["pacing_wps"] = "must be greater than zero"

    sections = values.get("sections")
    if sections is not None and (
        not isinstance(sections, list) or not all(isinstance(s, str) for s in sections)
    ):
        errors["sections"] = "must be a list of section names"

    section_texts = values.get("section_texts")
    if section_texts is not None and (
        not isinstance(section_texts, dict)
        or not all(isinstance(k, str) and isinstance(v, str) for k, v in section_texts.items())
    ):
        errors["section_texts"] = "must be a map of section name to text"

    outro_text = values.get("outro_text")
    if outro_text is not None and not isinstance(outro_text, str):
        errors["outro_text"] = "must be text"

    voice_preset = values.get("voice_preset")
    if voice_preset is not None and voice_preset not in ("natural", "dramatic", "energetic"):
        errors["voice_preset"] = "voice_preset must be one of natural, dramatic, energetic"

    lead_in = _as_float(values.get("hook_lead_in_seconds"))
    if "hook_lead_in_seconds" in values and (lead_in is None or not 0 <= lead_in <= 3):
        errors["hook_lead_in_seconds"] = "hook_lead_in_seconds must be between 0 and 3"

    for name in ("banned_topics", "tone_rules"):
        items = values.get(name)
        if items is not None and (
            not isinstance(items, list) or not all(isinstance(s, str) for s in items)
        ):
            errors[name] = "must be a list of strings"

    audience_persona = values.get("audience_persona")
    if audience_persona is not None and not isinstance(audience_persona, str):
        errors["audience_persona"] = "must be text"

    style = values.get("style")
    if style is not None:
        if not isinstance(style, dict):
            errors["style"] = "must be a map"
        else:
            chunk = style.get("chunk_size")
            if chunk is not None and (not isinstance(chunk, int) or not 1 <= chunk <= 10):
                errors["style"] = "chunk_size must be an integer between 1 and 10"
            if "uppercase" in style and not isinstance(style["uppercase"], bool):
                errors["style"] = "uppercase must be a boolean"
            scrim_alpha = _as_float(style.get("scrim_alpha"))
            if "scrim_alpha" in style and (scrim_alpha is None or not 0 <= scrim_alpha <= 1):
                errors["style"] = "scrim_alpha must be between 0 and 1"

    palette = values.get("palette")
    if palette is not None:
        if not isinstance(palette, dict):
            errors["palette"] = "must be a map"
        else:
            for key, value in palette.items():
                if key not in ("highlight_colour", "pill_bg_colour"):
                    errors["palette"] = f"unknown key {key!r}"
                elif not (isinstance(value, str) and len(value) == 10 and value.startswith("0x")):
                    errors["palette"] = f"{key} must be a 0xRRGGBBAA colour"

    layout = values.get("layout")
    if layout is not None:
        if not isinstance(layout, dict):
            errors["layout"] = "must be a map"
        else:
            problems: list[str] = []
            anchor = layout.get("anchor")
            if anchor is not None and anchor not in ("center", "lower_third"):
                problems.append("anchor must be center or lower_third")
            width = layout.get("block_width_pct")
            if width is not None and not (isinstance(width, int) and 20 <= width <= 100):
                problems.append("block_width_pct must be an integer between 20 and 100")
            scale = layout.get("numbered_scale")
            if scale is not None and not (isinstance(scale, (int, float)) and 0.8 <= scale <= 4.0):
                problems.append("numbered_scale must be between 0.8 and 4.0")
            corner = layout.get("watermark_corner")
            if corner is not None and corner not in (
                "bottom_right",
                "bottom_left",
                "top_right",
                "top_left",
            ):
                problems.append(
                    "watermark_corner must be one of bottom_right, bottom_left, top_right, top_left"
                )
            size_pct = _as_float(layout.get("watermark_size_pct"))
            if "watermark_size_pct" in layout and (size_pct is None or not 5 <= size_pct <= 30):
                problems.append("watermark_size_pct must be between 5 and 30")
            opacity = _as_float(layout.get("watermark_opacity"))
            if "watermark_opacity" in layout and (opacity is None or not 0.1 <= opacity <= 1):
                problems.append("watermark_opacity must be between 0.1 and 1")
            margin_px = _as_float(layout.get("watermark_margin_px"))
            if "watermark_margin_px" in layout and (margin_px is None or not 0 <= margin_px <= 200):
                problems.append("watermark_margin_px must be between 0 and 200")
            music_volume = _as_float(layout.get("music_volume"))
            if "music_volume" in layout and (
                music_volume is None or not 0.05 <= music_volume <= 0.5
            ):
                problems.append("music_volume must be between 0.05 and 0.5")
            music_fade = _as_float(layout.get("music_fade_seconds"))
            if "music_fade_seconds" in layout and (
                music_fade is None or not 0.5 <= music_fade <= 6
            ):
                problems.append("music_fade_seconds must be between 0.5 and 6")
            fade_out = _as_float(layout.get("fade_out_seconds"))
            if "fade_out_seconds" in layout and (fade_out is None or not 0 <= fade_out <= 3):
                problems.append("fade_out_seconds must be between 0 and 3")
            if problems:
                errors["layout"] = "; ".join(problems)

    stages = values.get("stages")
    if stages is not None:
        valid = {"music", "outro", "watermark", "background"}
        if not isinstance(stages, dict):
            errors["stages"] = "must be a map"
        else:
            for key, value in stages.items():
                if key not in valid:
                    errors["stages"] = f"unknown stage {key!r}"
                elif not isinstance(value, bool):
                    errors["stages"] = f"{key} must be a boolean"

    return errors


def _as_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
