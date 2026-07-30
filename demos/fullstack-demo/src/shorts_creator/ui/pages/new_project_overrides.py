from typing import Any

from shorts_creator.formats import registry as formats
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
)
from shorts_creator.pipeline.render_config import (
    _DEFAULTS as _PIPELINE_DEFAULTS,
)
from shorts_creator.topics import registry
from shorts_creator.ui.pages.new_project_profile import (
    _as_form_bool,
    _as_form_float,
    _as_str,
    _equals_inherited,
    _override_exists,
)

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


_PHASE2_KEYS = (
    "background_motion",
    "emphasis_style",
    "loudness_target_lufs",
    "audio_normalize",
    "stage_accents",
    "section_holds",
)
_PHASE2_NEUTRAL = {
    "background_motion": "none",
    "emphasis_style": "accent",
    "loudness_target_lufs": -14.0,
    "audio_normalize": True,
    "stage_accents": {},
    "section_holds": {},
}
_PHASE2_CLEARABLE_KEYS = (
    "loudness_target_lufs",
    "audio_normalize",
    "stage_accents",
    "section_holds",
)
_RESERVED_SECTIONS = ("hook", "conclusion", "top_items")
_STAGE_LABELS = {
    "music": "Music",
    "outro": "Outro",
    "watermark": "Watermark",
    "background": "Background",
}


def _fmt_rank(format_name: str | None) -> bool:
    fmt = formats.get(format_name) if format_name else None
    return bool(fmt and "top_items" in (fmt.requires.get("script") or []))


def _data_format(data: dict, profile) -> str | None:
    fmt = data.get("format")
    if fmt:
        return str(fmt)
    if profile is not None:
        setting = getattr(profile, "format_name", None)
        if setting is not None:
            return setting.value
    return None


_WIDGET_DEFAULTS: dict[str, dict[str, Any]] = {
    "style": {
        "chunk_size": 3,
        "caption_font_size": 56,
        "caption_outline_width": 2,
        "uppercase": False,
        "scrim_alpha": 0,
    },
    "layout": {
        "anchor": "center",
        "block_width_pct": 80,
        "numbered_scale": 1.6,
        "pill_per_word": True,
        "watermark_corner": "bottom_right",
        "watermark_size_pct": 10,
        "watermark_opacity": 0.85,
        "music_volume": 0.2,
        "music_fade_seconds": 2.0,
        "fade_out_seconds": 1.0,
    },
    "stages": {
        "music": False,
        "outro": True,
        "watermark": False,
        "background": True,
    },
}


def _palette_round_trip(profile, key: str, default_key: str) -> str:
    """The token the colour widget was prefilled from (profile palette
    composite, else pipeline default — mirroring _style_panel), in the
    ``0xrrggbbFF`` form the composer submits (composer-preview.js:812-814:
    lowercase ``#rrggbb`` widget value becomes ``0x`` + ``FF``)."""
    token = _PIPELINE_DEFAULTS[default_key]
    if profile is not None:
        setting = getattr(profile, "palette", None)
        composite = setting.value if setting is not None else None
        if isinstance(composite, dict) and composite.get(key):
            hex_str = str(composite[key]).removeprefix("0x")
            if len(hex_str) >= 6:
                token = str(composite[key])
    return "0x" + str(token).removeprefix("0x")[:6].lower() + "FF"


def _json_neutral(data: dict, profile, key: str, value) -> bool:
    """True when the submitted composite equals the composer's untouched
    default for the current format/topic (mirrors syncComposerHidden in
    composer-preview.js). syncComposerHidden always submits the full widget
    key set, so style/layout/stages are compared against the widget-default
    composite (the values _style_panel/_layout_panel render into every
    widget) overlaid with the profile-resolved composite the widgets
    prefill — every knob the JS emits is compared exactly, so a change to
    any single knob is never dropped and an untouched submission with a
    custom inherited composite stays neutral. palette neutrality is the
    round-trip form of the token the colour widget was prefilled from.
    sections must match exactly. A setting the project already overrides is
    never neutral: reverting to the default on an overridden project still
    re-persists the override."""
    if profile is not None:
        setting = getattr(profile, key, None)
        if setting is not None and setting.is_overridden:
            return False
    if key == "sections":
        topic_name = data.get("type") or None
        if topic_name is None and profile is not None:
            topic_setting = getattr(profile, "topic", None)
            topic_name = topic_setting.value if topic_setting else None
        topic = registry.get(topic_name) if topic_name else None
        if topic is None:
            return False
        expected = [s for s in topic.structure_sections if s not in _RESERVED_SECTIONS]
        return isinstance(value, list) and value == expected
    fmt_name = _data_format(data, profile)
    if key == "palette":
        return (
            isinstance(value, dict)
            and value.get("highlight_colour")
            == _palette_round_trip(profile, "highlight_colour", "caption_highlight_colour")
            and value.get("pill_bg_colour")
            == _palette_round_trip(profile, "pill_bg_colour", "pill_bg_colour")
        )
    defaults = _WIDGET_DEFAULTS.get(key)
    if defaults is None or not isinstance(value, dict):
        return False
    merged = dict(defaults)
    if profile is not None:
        setting = getattr(profile, key, None)
        composite = setting.value if setting is not None else None
        if isinstance(composite, dict):
            merged.update(composite)
    if key == "stages" and _fmt_rank(fmt_name):
        merged["music"] = True
    return value == merged


_MEDIA_URL_KEYS = {
    "bg_clip": "media_url_bg_clip",
    "music": "media_url_music",
    "outro_clip": "media_url_outro",
    "watermark": "media_url_watermark",
}
_ASSET_URL_KEYS = {
    "asset_music_id": "media_url_music",
    "asset_bg_clip_id": "media_url_bg_clip",
    "asset_outro_clip_id": "media_url_outro",
    "asset_watermark_id": "media_url_watermark",
}


def form_overrides(data: dict, profile: EffectiveProjectProfile | None = None) -> dict:
    """Creative values from the guided form, stored as project profile overrides.

    Values still equal to the resolved inherited default are not persisted:
    the user did not change them, so the field keeps its inherited provenance
    (Topic / Global Default / Built-in) instead of becoming a Project
    override and diverging from what the settings page and renders resolve.
    Composer JSON composites (style/palette/layout/stages/sections) are also
    skipped when they equal the untouched-composer neutral value the JS
    submits unprompted (mirrored in _json_neutral), so an untouched composer
    never fabricates an override. Explicit blank submissions (caption_style,
    hook_text, outro_text, pacing_wps) write "" so the pop-on-empty save
    path removes a stale override.
    """
    import json as _json

    overrides = {}
    format_name = data.get("format")
    if format_name and not _equals_inherited(profile, "format_name", format_name):
        overrides["format_name"] = format_name
    caption_style = data.get("caption_style")
    if caption_style and not _equals_inherited(profile, "caption_style", caption_style):
        overrides["caption_style"] = caption_style
    elif (
        caption_style is not None
        and str(caption_style).strip() == ""
        and _override_exists(profile, "caption_style")
    ):
        overrides["caption_style"] = ""
    duration = _as_form_float(data.get("duration_seconds"))
    if duration is not None and not _equals_inherited(profile, "duration_seconds", duration):
        overrides["duration_seconds"] = duration

    pacing_raw = data.get("pacing_wps")
    pacing = _as_form_float(pacing_raw)
    if pacing is not None and not _equals_inherited(profile, "pacing_wps", pacing):
        overrides["pacing_wps"] = pacing
    elif (
        pacing_raw is not None
        and str(pacing_raw).strip() == ""
        and _override_exists(profile, "pacing_wps")
    ):
        overrides["pacing_wps"] = ""
    hook_text = _as_str(data.get("hook_text"))
    if hook_text is not None and hook_text.strip() != "":
        overrides["hook_text"] = hook_text.strip()
    elif (
        data.get("hook_text") is not None
        and str(data.get("hook_text")).strip() == ""
        and _override_exists(profile, "hook_text")
    ):
        overrides["hook_text"] = ""
    outro_text = _as_str(data.get("outro_text"))
    if outro_text is not None and outro_text.strip() != "":
        overrides["outro_text"] = outro_text.strip()
    elif (
        data.get("outro_text") is not None
        and str(data.get("outro_text")).strip() == ""
        and _override_exists(profile, "outro_text")
    ):
        overrides["outro_text"] = ""
    for key in ("sections", "section_texts", "style", "palette", "layout", "stages"):
        raw = data.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            value = _json.loads(raw)
        except (TypeError, ValueError):
            value = raw
        if (
            value not in (None, {}, [], "")
            and not _json_neutral(data, profile, key, value)
            and not _equals_inherited(profile, key, value)
        ):
            overrides[key] = value
    for key in _PHASE2_KEYS:
        raw = data.get(key)
        if raw is None:
            continue
        if str(raw).strip() == "":
            if key in _PHASE2_CLEARABLE_KEYS and _override_exists(profile, key):
                overrides[key] = ""
            continue
        if key in ("stage_accents", "section_holds"):
            try:
                value = _json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(value, dict) or not value:
                continue
        elif key == "loudness_target_lufs":
            value = _as_form_float(raw)
            if not isinstance(value, (int, float)):
                continue
        elif key == "audio_normalize":
            value = _as_form_bool(raw)
            if value is None:
                continue
        else:
            value = _as_str(raw)
            if value is None:
                continue
        if _equals_inherited(profile, key, value):
            continue
        setting = getattr(profile, key, None) if profile is not None else None
        if (setting is None or setting.value is None) and value == _PHASE2_NEUTRAL[key]:
            continue
        overrides[key] = value
    for asset_key in (
        "asset_music_id",
        "asset_font_id",
        "asset_bg_clip_id",
        "asset_outro_clip_id",
        "asset_watermark_id",
    ):
        raw = data.get(asset_key)
        if raw is None:
            continue
        if str(raw).strip() == "":
            if _override_exists(profile, asset_key):
                overrides[asset_key] = ""
                url_key = _ASSET_URL_KEYS.get(asset_key)
                if url_key:
                    overrides[url_key] = ""
            continue
        value = _as_str(raw)
        if value is not None and not _equals_inherited(profile, asset_key, value):
            overrides[asset_key] = value
    for url_key in (
        "media_url_music",
        "media_url_bg_clip",
        "media_url_outro",
        "media_url_watermark",
    ):
        raw = data.get(url_key)
        if raw is None:
            continue
        if isinstance(raw, str) and raw.strip() == "":
            if profile is not None:
                overrides[url_key] = ""
            continue
        overrides[url_key] = str(raw).strip()
    role_sources = {
        role: data.get(f"media_source_{role}")
        for role in ("bg_clip", "music", "outro_clip", "watermark")
    }
    for role, source in role_sources.items():
        asset_key = f"asset_{role}_id"
        url_key = _MEDIA_URL_KEYS[role]
        form_url_key = f"media_url_{role}"
        if role == "bg_clip" and source in ("url", "assets") and profile is not None:
            overrides["bg_source"] = ""
            overrides["stock_provider"] = ""
        if source == "url" and profile is not None:
            if _as_str(data.get(form_url_key)):
                overrides[url_key] = str(data[form_url_key]).strip()
            else:
                overrides[url_key] = ""  # legacy: cleared-on-empty, still a user decision
            overrides[asset_key] = ""
        elif source == "assets" and profile is not None:
            overrides[url_key] = ""
        elif source == "api" and role == "bg_clip":
            overrides["bg_source"] = "api"
            overrides["stock_provider"] = _as_str(data.get("stock_provider_bg_clip")) or "auto"
            if profile is not None:
                overrides[asset_key] = ""
                overrides[url_key] = ""
    if profile is not None and "bg_mode" in data:
        bg_mode = _as_str(data.get("bg_mode"))
        overrides["bg_mode"] = "image" if bg_mode == "image" else ""
    return overrides
