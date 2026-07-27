import json
import random
from html import escape
from pathlib import Path
from typing import Any

from lexigram.ui import Element, el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.pipeline.render_config import (
    _DEFAULTS as _PIPELINE_DEFAULTS,
)
from shorts_creator.pipeline.render_config import (
    STAGE_ACCENT_PALETTE,
)
from shorts_creator.services.asset_service import ASSETS_ROOT
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import compatible_formats_by_topic
from shorts_creator.services.settings_store import PROVIDER_LABELS
from shorts_creator.topics import registry
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.components.settings_profile import (
    caption_style_label,
    profile_summary,
    source_badge,
)
from shorts_creator.ui.icons import plus

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


def _resolved(value, source: ProfileSource) -> ResolvedSetting:
    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def fallback_profile(config: AppConfig | None = None) -> EffectiveProjectProfile:
    """Resolver-less effective profile (unit tests / un-wired controller), keeping
    the same shape the real ProjectProfileService.resolve returns."""
    config = config or AppConfig()
    return EffectiveProjectProfile(
        duration_seconds=_resolved(float(config.default_duration or 30.0), ProfileSource.BUILT_IN),
        caption_style=_resolved("highlight", ProfileSource.BUILT_IN),
        format_name=_resolved("narrated", ProfileSource.BUILT_IN),
        topic=_resolved("self_improvement", ProfileSource.PROJECT),
        reel_width=_resolved(config.reel_width, ProfileSource.BUILT_IN),
        reel_height=_resolved(config.reel_height, ProfileSource.BUILT_IN),
    )


def _as_form_float(value) -> float | str | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _as_form_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return {
            "true": True,
            "1": True,
            "on": True,
            "false": False,
            "0": False,
            "off": False,
        }.get(value.strip().lower())
    return None


def _equals_inherited(profile: EffectiveProjectProfile | None, key: str, value) -> bool:
    if profile is None:
        return False
    setting = getattr(profile, key, None)
    if setting is None or setting.value is None or setting.is_overridden:
        return False
    return value == setting.value


def _override_exists(profile: EffectiveProjectProfile | None, key: str) -> bool:
    if profile is None:
        return False
    setting = getattr(profile, key, None)
    return setting is not None and setting.is_overridden


def _as_str(value) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return str(value)


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


def _fmt_number(value) -> str:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(num)) if num.is_integer() else str(num)


def _format_label(name: str) -> str:
    fmt = formats.get(name)
    return fmt.label if fmt else name


def _profile_strip(profile: EffectiveProjectProfile, reset_url: str = "") -> str:
    rows = ""
    fmt_def = formats.get(profile.format_name.value) if profile.format_name else None
    for key, label, value, setting in (
        (
            "duration_seconds",
            "Duration",
            f"{_fmt_number(profile.duration_seconds.value)}s" if profile.duration_seconds else None,
            profile.duration_seconds,
        ),
        (
            "format_name",
            "Format",
            _format_label(profile.format_name.value) if profile.format_name else None,
            profile.format_name,
        ),
        (
            "caption_style",
            "Caption style",
            caption_style_label(
                fmt_def,
                profile.caption_style.value if profile.caption_style else None,
            ),
            profile.caption_style,
        ),
    ):
        if setting is None or value is None:
            continue
        meta = source_badge(setting)
        if setting.is_overridden and reset_url:
            meta += (
                f'<button type="button" data-override-toggle data-key="{escape(key)}" '
                f'data-reset-url="{escape(reset_url)}" '
                f'class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/60 '
                f'text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors cursor-pointer" '
                f'title="Reset to inherited default">Reset</button>'
            )
        rows += (
            '<div class="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0">'
            f'<span class="text-xs font-mono text-muted-foreground">{escape(label)}</span>'
            '<span class="flex items-center gap-2 text-xs font-mono text-foreground">'
            f"<span>{escape(str(value))}</span>{meta}</span></div>"
        )
    return Markup(
        '<div class="rounded-xl border border-border/60 bg-background/50 px-4 py-3">'
        '<div class="flex items-center justify-between mb-2">'
        '<span class="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest">Effective profile</span>'
        + str(profile_summary(profile))
        + "</div>"
        + rows
        + "</div>"
    )


def _field_section(title: str, body) -> str:
    return Markup(
        str(
            el(
                "div",
                el("h2", title, class_="text-sm font-semibold text-foreground mb-3"),
                body,
                class_="mb-5",
            )
        )
    )


_WIZARD_INPUT_CLS = "w-full bg-card/80 border border-border/80 rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-secondary focus:outline-none focus:border-primary/60 transition-all duration-200"
_WIZARD_LABEL_CLS = "block text-xs font-semibold text-foreground mb-1.5 font-mono"
_WIZARD_HELP_CLS = "text-muted-foreground text-[11px] mt-1.5 font-mono"
_FMT_BTN_ACTIVE = (
    "bg-gradient-to-br from-primary to-primary border-primary text-primary-foreground shadow-md"
)
_FMT_BTN_CLS = (
    "shrink-0 fmt-btn flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold "
    "transition-all duration-200 border cursor-pointer select-none "
)


def _wizard_globals_js(
    active_classes: dict[str, list[str]], compatible: dict[str, list[str]] | None
) -> str:
    return Markup(
        f"<script>window.__ACTIVE_CLASSES__ = {json.dumps(active_classes)}; "
        f"window.__COMPATIBLE_JSON__ = {json.dumps(compatible or {})}; "
        f"window.__FORMAT_UI_JSON__ = {json.dumps({f.name: _caption_field_data(f) for f in formats.available})};</script>"
        '<script src="/static/js/project-form.js"></script>'
    )


def _caption_field_data(fmt) -> dict | None:
    """Per-format caption-style knob data, shared by the server-rendered
    wizard field and the client-side rebuild on format switch. Ranked
    formats (style-less with top_items, e.g. topn) get the per-item/list
    options; style-less formats without ranked items render no captions
    (None); the rest offer highlight/plain."""
    styles = list(fmt.caption_styles)
    ranked = "top_items" in (fmt.requires.get("script") or [])
    if ranked and not styles:
        return {
            "options": [["", "Per-item screens"], ["list", "List"]],
            "help": "Per-item screens show one ranked item at a time; List shows the whole top n on one screen",
        }
    if not styles:
        return None
    return {
        "options": [["highlight", "Highlight (word-by-word)"], ["plain", "Plain (static lines)"]],
        "help": "Highlight tracks each spoken word; Plain keeps the whole line visible",
    }


def _wizard_format_field(profile: EffectiveProjectProfile | None) -> Element:
    selected_format = profile.format_name.value if profile and profile.format_name else "narrated"
    fmt_buttons = []
    for f in formats.available:
        fmt_buttons.append(
            el(
                "div",
                f.label,
                id=f"format-btn-{f.name}",
                class_=_FMT_BTN_CLS
                + (
                    _FMT_BTN_ACTIVE
                    if f.name == selected_format
                    else "bg-card/60 border-border text-muted-foreground"
                ),
                onclick=f"setFormat('{f.name}')",
                data_format=f.name,
            )
        )
    return el(
        "div",
        el("label", "Format", for_="new-project-format", class_=_WIZARD_LABEL_CLS),
        el(
            "select",
            *(
                el("option", f.label, value=f.name, selected=(f.name == selected_format))
                for f in formats.available
            ),
            id="new-project-format",
            name="format",
            class_="hidden",
        ),
        el("div", *fmt_buttons, class_="flex gap-2 overflow-x-auto pb-1"),
        el("div", id="profile-field-error-format_name", class_="profile-error-slot"),
        el("p", "How the video presents its script on screen", class_=_WIZARD_HELP_CLS),
        class_="mb-5",
    )


def _wizard_duration_field(profile: EffectiveProjectProfile | None) -> Element:
    selected_format = profile.format_name.value if profile and profile.format_name else "narrated"
    selected_fmt = formats.get(selected_format) if selected_format else None
    duration_value = (
        _fmt_number(profile.duration_seconds.value) if profile and profile.duration_seconds else ""
    )
    return el(
        "div",
        el("label", "Duration (seconds)", for_="new-project-duration", class_=_WIZARD_LABEL_CLS),
        el(
            "input",
            type="number",
            min="1",
            step="any",
            id="new-project-duration",
            name="duration_seconds",
            value=duration_value,
            class_=_WIZARD_INPUT_CLS,
        ),
        el("div", id="profile-field-error-duration_seconds", class_="profile-error-slot"),
        el("p", "Desired video length; the topic may refine it", class_=_WIZARD_HELP_CLS),
        el(
            "p",
            f"{selected_fmt.label if selected_fmt else 'Narrated'} renders "
            f"{selected_fmt.duration_range[0] if selected_fmt else 30}\u2013"
            f"{selected_fmt.duration_range[1] if selected_fmt else 60}s",
            id="duration-range-hint",
            class_=_WIZARD_HELP_CLS,
        ),
        class_="mb-5",
    )


def _wizard_caption_field(profile: EffectiveProjectProfile | None) -> Element:
    selected_format = profile.format_name.value if profile and profile.format_name else "narrated"
    selected_fmt = formats.get(selected_format) if selected_format else None
    field = _caption_field_data(selected_fmt) if selected_fmt else None
    if field is None:
        return el(
            "div",
            el(
                "p",
                "This format renders without captions - narration over full-bleed video",
                class_=_WIZARD_HELP_CLS,
            ),
            el("input", type="hidden", name="caption_style", value=""),
            class_="mb-5",
        )
    profile_style = profile.caption_style.value if profile and profile.caption_style else ""
    if not any(value == profile_style for value, _ in field["options"]):
        profile_style = ""
    default_style = profile_style or field["options"][0][0]
    cap_btn_cls = (
        "shrink-0 cap-btn flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold "
        "transition-all duration-200 border cursor-pointer select-none "
    )
    cap_buttons = [
        el(
            "div",
            label,
            id=f"cap-btn-{value or 'none'}",
            class_=cap_btn_cls
            + (
                _FMT_BTN_ACTIVE
                if default_style == value
                else "bg-card/60 border-border text-muted-foreground"
            ),
            onclick=f"setCaptionStyle('{value}')",
            data_style=value,
        )
        for value, label in field["options"]
    ]
    return el(
        "div",
        el("label", "Caption Style", for_="new-project-caption-style", class_=_WIZARD_LABEL_CLS),
        el(
            "select",
            *(
                el("option", label, value=value, selected=default_style == value)
                for value, label in field["options"]
            ),
            id="new-project-caption-style",
            name="caption_style",
            class_="hidden",
        ),
        el("div", *cap_buttons, class_="flex gap-2 overflow-x-auto pb-1"),
        el("div", id="profile-field-error-caption_style", class_="profile-error-slot"),
        el("p", field["help"], class_=_WIZARD_HELP_CLS),
        class_="mb-5",
    )


_SKELETONS = {
    "topn": [
        {"label": "Hook", "text": "The hook that stops the scroll", "num": ""},
        {"label": "", "text": "First practice, kept concrete", "num": "1"},
        {"label": "", "text": "Second practice, kept concrete", "num": "2"},
        {"label": "", "text": "Third practice, kept concrete", "num": "3"},
        {"label": "", "text": "Fourth practice, kept concrete", "num": "4"},
        {"label": "", "text": "Fifth practice, kept concrete", "num": "5"},
        {"label": "Conclusion", "text": "The takeaway that lands", "num": ""},
    ],
    "narrated": [
        {"label": "Hook", "text": "The hook that stops the scroll", "num": ""},
        {"label": "", "text": "First practice, kept concrete", "num": ""},
        {"label": "", "text": "Second practice, kept concrete", "num": ""},
        {"label": "", "text": "Third practice, kept concrete", "num": ""},
        {"label": "", "text": "Fourth practice, kept concrete", "num": ""},
        {"label": "", "text": "Fifth practice, kept concrete", "num": ""},
        {"label": "Conclusion", "text": "The takeaway that lands", "num": ""},
    ],
}


def _skeleton_rows(format_name: str, skeleton_id: str, sections: list[str] | None = None) -> str:
    """Rows for the Story pane. Narrated rows are labeled from the topic's own
    structure_sections (the real reel is scripted section by section, e.g.
    hook -> context/explanation/... -> conclusion); topn keeps its numbered
    item rows which ARE the top_items section."""
    skeleton = _SKELETONS.get(format_name, _SKELETONS["narrated"])
    mid_sections = [s for s in (sections or []) if s not in ("hook", "conclusion", "top_items")]
    rows = []
    for idx, item in enumerate(skeleton):
        label = item["label"]
        if not label and idx > 0 and idx < len(skeleton) - 1 and idx - 1 < len(mid_sections):
            label = mid_sections[idx - 1]
        mid_cls = " skel-mid-label" if idx > 0 and idx < len(skeleton) - 1 else ""
        num_chip = (
            (
                f'<span class="w-5 h-5 rounded-full bg-secondary/60 text-foreground '
                f'grid place-items-center text-[10px] font-bold shrink-0">{item["num"]}</span>'
            )
            if item["num"]
            else ""
        )
        label_span = (
            (
                f'<span class="text-[10px] font-mono uppercase tracking-widest text-muted-foreground '
                f'w-16 shrink-0{mid_cls}">{label}</span>'
            )
            if label
            else (f'<span class="w-16 shrink-0{mid_cls}"></span>')
        )
        rows.append(
            f'<div class="flex items-center gap-2 py-1.5 border-b border-border/30 last:border-0">'
            f"{label_span}{num_chip}"
            f'<span class="text-xs text-foreground leading-snug">{item["text"]}</span></div>'
        )
    return Markup(f'<div id="{skeleton_id}" class="preview-skeleton">' + "".join(rows) + "</div>")


def _pick_preview_background() -> tuple[str, str]:
    """Local nature clip whenever bundled footage exists, stock-style image only
    as a last resort (the real pipeline is always nature clips, so random
    subject images would misrepresent the final reel)."""
    clips = sorted(Path(ASSETS_ROOT, "clip").glob("*.mp4"))
    if clips:
        return "video", "/api/preview/clip"
    return "image", f"https://picsum.photos/seed/{random.randrange(10**9)}/540/960"


# Text styling mirrors the render pipeline exactly (pipeline.py / compose.py
# constants), scaled from the 1080x1920 reel down to the 360px preview screen.
_PREVIEW_SCALE = 360.0 / 1080.0
_CAPTION_FONT_PX = round(56 * _PREVIEW_SCALE, 2)  # CAPTION_FONT_SIZE
_CAPTION_STROKE_PX = round(2 * _PREVIEW_SCALE, 2)  # CAPTION_OUTLINE_WIDTH
_CAPTION_PILL_COLOR = (
    "#" + str(_PIPELINE_DEFAULTS["caption_highlight_colour"])[2:-2]
)  # CAPTION_HIGHLIGHT_COLOUR
_CAPTION_PILL_PAD_PX = round(8 * _PREVIEW_SCALE, 2)  # _HIGHLIGHT_PAD_PX
_HOOK_PILL_COLOR = (
    "rgba(0,0,0," + f"{int(str(_PIPELINE_DEFAULTS['pill_bg_colour'])[-2:], 16) / 255:.2f}" + ")"
)  # pill 0x000000C0
_HOOK_PILL_PAD_PX = round(12 * _PREVIEW_SCALE, 2)  # _draw_pill pad
_HOOK_GAP_PX = round(18 * _PREVIEW_SCALE, 2)  # HOOK_LINE_GAP_PX


def _preview_hook_font_px(texts: list[str]) -> float:
    """Same fit as compose.hook_font_size, scaled for the preview screen."""
    max_chars = max(len(t) for t in texts)
    width_fit = (0.80 * 1080) / (max_chars * 0.55)
    height_fit = (0.70 * 1920) / (len(texts) * 1.3)
    size = max(40, min(110, width_fit, height_fit))
    return round(size * _PREVIEW_SCALE, 2)


def _hook_pills(text: str, style: str) -> list:
    """One pill per hook word, mirroring the real hook screen: the pipeline
    chunks the hook line with HOOK_LINE_TARGET_SIZE = 1 so every word is its
    own row (pipeline.py _render_hook_clip / captions.group_for_hook_display)."""
    return [el("span", word, class_="pv-hook block", style_=style) for word in text.split()]


preview_styles = f"""
<style>
@font-face {{
  font-family: 'PreviewDejaVu';
  src: url('/api/preview/font') format('truetype');
}}
.pv-font {{ font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif; }}
.pv-hook {{
  display: inline-block;
  font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif;
  font-weight: 800;
  color: #fff;
  background: {_HOOK_PILL_COLOR};
  border-radius: {_HOOK_PILL_PAD_PX}px;
  padding: {_HOOK_PILL_PAD_PX}px;
  line-height: 1.3;
}}
.pv-cap {{
  font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif;
  color: #fff;
  font-size: {_CAPTION_FONT_PX}px;
  line-height: 1.3;
  white-space: nowrap;
  -webkit-text-stroke: {_CAPTION_STROKE_PX}px #000;
  text-shadow: -0.5px 0 0 #000, 0.5px 0 0 #000, 0 -0.5px 0 #000, 0 0.5px 0 #000;
}}
.pv-pill {{
  background: {_CAPTION_PILL_COLOR};
  border-radius: {_CAPTION_PILL_PAD_PX}px;
  padding: {_CAPTION_PILL_PAD_PX}px;
}}
</style>
"""


def _picker_fallback_chip() -> str:
    """Tiny hint under the phone when the preview runs the fallback clip."""
    return Markup(
        str(
            el(
                "button",
                el(
                    "span",
                    "i",
                    class_="w-3.5 h-3.5 grid place-items-center rounded-full bg-foreground/10 text-[8px] font-bold",
                ),
                el("span", "Fallback clip — set your background in Composer · Media"),
                type="button",
                onclick=(
                    "switchCreateTab('composer');"
                    "var el=document.getElementById('composer-media-panel-wrapper');"
                    "if (el) el.scrollIntoView({behavior:'smooth', block:'start'});"
                ),
                class_=(
                    "mt-2 inline-flex items-center gap-1.5 text-[10px] font-mono "
                    "text-muted-foreground/70 bg-secondary/40 border border-border/60 "
                    "rounded-full px-3 py-1 hover:text-foreground hover:border-border transition-colors"
                ),
            )
        )
    )


def _preview_phone(active_classes=None, background_src=None) -> str:
    """9:16 phone mockup with live mirrors of the form fields.

    `background_src` switches the phone into playback mode: the rendered
    video fills the screen with native controls, and the preview
    overlays/buttons are omitted so both states share the same frame.
    """
    playback = bool(background_src)
    if playback:
        kind, src = "video", background_src
    else:
        kind, src = _pick_preview_background()
    hook_text = _SKELETONS["narrated"][0]["text"]
    hook_style = f"font-size:{_preview_hook_font_px(hook_text.split())}px"
    hook_pills = _hook_pills(hook_text, hook_style)
    background = (
        el(
            "video",
            src=src,
            id="preview-bg-video",
            class_="absolute inset-0 w-full h-full object-cover",
            autoplay=True,
            muted=True,
            loop=True,
            playsinline=True,
            preload="metadata",
            controls=playback,
        )
        if kind == "video"
        else el(
            "img",
            src=src,
            alt="",
            class_="absolute inset-0 w-full h-full object-cover",
            loading="lazy",
        )
    )
    top_row = (
        [
            el(
                "div",
                el(
                    "span",
                    id="preview-topic-dot",
                    class_="w-2.5 h-2.5 rounded-full bg-secondary inline-block",
                ),
                el(
                    "span",
                    "PREVIEW",
                    class_="text-[9px] font-mono tracking-[0.2em] text-muted-foreground",
                ),
                el(
                    "div",
                    *(
                        el(
                            "button",
                            label,
                            type="button",
                            data_preview_section=name,
                            onclick=f"setPreviewSection('{name}')",
                            aria_pressed="true" if name == "full" else "false",
                            class_="px-2 py-1 rounded-full text-[9px] font-mono tracking-wider uppercase transition-colors "
                            + (
                                "bg-primary text-primary-foreground"
                                if name == "full"
                                else "bg-secondary/80 text-muted-foreground hover:bg-secondary"
                            ),
                        )
                        for name, label in (
                            ("intro", "Intro"),
                            ("mid", "Mid"),
                            ("outro", "Outro"),
                            ("full", "Full"),
                        )
                    ),
                    id="preview-section-tabs",
                    class_="flex items-center gap-1 ml-2",
                ),
                class_="flex items-center gap-2",
            ),
        ]
        if not playback
        else []
    )
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    *top_row,
                    el(
                        "div",
                        el(
                            "div",
                            class_="absolute -left-[3px] top-24 w-[3px] h-8 bg-foreground/5 rounded-l-md",
                        ),
                        el(
                            "div",
                            class_="absolute -left-[3px] top-36 w-[3px] h-14 bg-foreground/5 rounded-l-md",
                        ),
                        el(
                            "div",
                            class_="absolute -right-[3px] top-28 w-[3px] h-16 bg-foreground/5 rounded-r-md",
                        ),
                        el(
                            "div",
                            class_="absolute -right-[3px] top-52 w-[3px] h-10 bg-foreground/5 rounded-r-md",
                        ),
                        el(
                            "div",
                            el(
                                "div",
                                background,
                                el("div", class_="absolute inset-0 bg-foreground/20")
                                if not playback
                                else None,
                                id="preview-bg-layer",
                                class_="absolute inset-0",
                            ),
                            el(
                                "div",
                                el(
                                    "span",
                                    "Thanks for watching",
                                    id="preview-outro-text",
                                    class_="pv-font absolute inset-0 flex items-center justify-center text-primary-foreground text-[32px]",
                                ),
                                id="preview-outro",
                                style_="display:none;background:#0a0a32",
                                class_="absolute inset-0",
                            )
                            if not playback
                            else None,
                            el(
                                "div",
                                el(
                                    "div",
                                    el(
                                        "span",
                                        "9:41",
                                        class_="text-[8px] font-mono text-muted-foreground",
                                    ),
                                    el("div", class_="w-24 h-6 bg-card rounded-full"),
                                    el(
                                        "span",
                                        el("span", class_="w-full h-full bg-muted rounded-[1px]"),
                                        class_="w-4 h-2 rounded-[2px] border border-border flex items-end p-[1px]",
                                    ),
                                    class_="flex items-center justify-between px-2 pt-1.5",
                                ),
                                el(
                                    "div",
                                    el(
                                        "div",
                                        *hook_pills,
                                        id="preview-hook-block",
                                        class_="text-center",
                                    ),
                                    el(
                                        "div",
                                        el(
                                            "div",
                                            el(
                                                "div",
                                                el("span", "First", class_="pv-cap"),
                                                el("span", "practice,", class_="pv-cap pv-pill"),
                                                el("span", "kept", class_="pv-cap"),
                                                el("span", "concrete", class_="pv-cap"),
                                                id="preview-caption-highlight",
                                                class_="text-center",
                                            ),
                                            el(
                                                "div",
                                                "First practice, kept concrete",
                                                id="preview-caption-plain",
                                                class_="pv-cap text-center",
                                            ),
                                            id="preview-caption",
                                            class_="flex flex-col justify-center gap-1",
                                        ),
                                        el(
                                            "div",
                                            id="preview-ranking-block",
                                            class_="text-center flex flex-col items-center justify-center gap-1",
                                            style_="display:none",
                                        ),
                                        id="preview-mid-block",
                                        class_="flex flex-col justify-center",
                                    ),
                                    class_="flex-1 flex flex-col justify-center gap-8 px-1",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    el(
                                        "div",
                                        id="preview-duration-fill",
                                        class_="h-1 rounded-full bg-gradient-to-r from-muted to-foreground",
                                    ),
                                    el(
                                        "div",
                                        el(
                                            "div", class_="absolute inset-y-0 w-px bg-foreground/50"
                                        ),
                                        el(
                                            "div", class_="absolute inset-y-0 w-px bg-foreground/50"
                                        ),
                                        id="preview-timeline-ticks",
                                        class_="absolute inset-0",
                                    ),
                                    id="preview-duration-bar",
                                    class_="relative h-1 rounded-full bg-secondary overflow-hidden",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    el(
                                        "span",
                                        "0:00 / 0:30",
                                        id="preview-position-display",
                                        class_="text-[10px] text-muted-foreground/60 tabular-nums",
                                    ),
                                    class_="w-full flex justify-end",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    class_="w-24 h-1 bg-secondary/80 rounded-full mx-auto mt-3 mb-1",
                                )
                                if not playback
                                else None,
                                class_="relative z-10 flex-1 flex flex-col",
                            ),
                            el(
                                "button",
                                el(
                                    "span",
                                    el(
                                        "svg",
                                        el("path", d="M8 5v14l11-7z"),
                                        viewBox="0 0 24 24",
                                        fill="white",
                                        class_="w-5 h-5 ml-0.5",
                                    ),
                                    id="preview-play-icon",
                                ),
                                el(
                                    "span",
                                    el(
                                        "svg",
                                        el("rect", x="6", y="5", width="4", height="14"),
                                        el("rect", x="14", y="5", width="4", height="14"),
                                        viewBox="0 0 24 24",
                                        fill="white",
                                        class_="w-5 h-5",
                                    ),
                                    id="preview-pause-icon",
                                    style_="display:none",
                                ),
                                id="preview-play-btn",
                                type="button",
                                onclick="togglePreviewPlay()",
                                aria_label="Play or pause preview",
                                class_="absolute inset-0 m-auto z-30 w-14 h-14 rounded-full bg-foreground/20 text-primary-foreground grid place-items-center",
                            )
                            if not playback
                            else None,
                            el(
                                "div",
                                class_="absolute inset-0 rounded-[2.8rem] pointer-events-none bg-gradient-to-b from-white/5 via-transparent to-transparent",
                            ),
                            class_="relative w-[360px] h-full min-h-[700px] bg-foreground/5 rounded-[2.8rem] overflow-hidden px-4 pb-5 pt-2 flex flex-col",
                        ),
                        id="preview-phone-frame",
                        class_="relative flex-1 w-fit rounded-[3.4rem] bg-foreground/5 border-4 border-foreground/10 p-3.5 shadow-2xl",
                        data_topic_accents="true",
                    ),
                    _picker_fallback_chip() if not playback else None,
                    class_="w-full h-full flex flex-col items-center gap-3",
                ),
                id="new-project-preview-phone",
                class_="flex items-start justify-center max-h-[740px]",
            )
        )
    )


def _details_pane(
    skeleton_topn: str,
    skeleton_narrated: str,
    profile: EffectiveProjectProfile,
) -> str:
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h3",
                        "Story",
                        class_="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest mb-2",
                    ),
                    skeleton_topn,
                    skeleton_narrated,
                    class_="rounded-xl border border-border/60 bg-background/50 px-4 py-3",
                ),
                el("div", _profile_strip(profile), class_="mt-4"),
                class_="md:col-span-1",
            )
        )
    )


_ACTIVE_BASE = ("bg-gradient-to-br", "text-primary-foreground", "shadow-md")
_TYPE_INFO = {
    "self_improvement": {
        "emoji": "🧠",
        "desc": "Habit-building & mindset",
        "color_active": "from-primary to-primary border-primary shadow-primary/40",
        "color_inactive": "border-border hover:border-border",
    },
    "psychology": {
        "emoji": "🔬",
        "desc": "Research-grounded psychology explainers",
        "color_active": "from-info to-success border-info shadow-info/40",
        "color_inactive": "border-border hover:border-border",
    },
    "stoic": {
        "emoji": "🏛️",
        "desc": "Timeless Stoic philosophy for modern life",
        "color_active": "from-warning to-warning border-warning shadow-warning/40",
        "color_inactive": "border-border hover:border-border",
    },
}


def _type_meta(name: str) -> dict:
    return _TYPE_INFO.get(
        name,
        {
            "emoji": "📁",
            "desc": "",
            "color_active": "from-primary to-primary border-primary",
            "color_inactive": "border-border",
        },
    )


def _active_classes() -> dict[str, list[str]]:
    return {
        t.name: list(_ACTIVE_BASE) + _type_meta(t.name)["color_active"].split()
        for t in registry.available
    }


def _panel(title: str, body, panel_id: str, class_extra: str = "", open_default: bool = True):
    return el(
        "details",
        el("summary", title, class_="cursor-pointer text-xs font-semibold text-foreground"),
        el("div", body, class_="mt-3 space-y-3"),
        id=panel_id,
        open=open_default,
        class_="rounded-xl border border-border/80 bg-card/50 px-4 py-3" + class_extra,
    )


def _composer_value(profile, key, default=None):
    if profile is None:
        return default
    setting = getattr(profile, key, None)
    if setting is None or setting.value is None:
        return default
    return setting.value


def _content_panel(profile=None):
    pacing = _fmt_number(_composer_value(profile, "pacing_wps", 2.5))
    hook = _composer_value(profile, "hook_text", "")
    outro = _composer_value(profile, "outro_text", "")
    sections = _composer_value(profile, "sections")
    return _panel(
        "Content — script wording, pacing, sections",
        el(
            "div",
            el("label", "Speaking pace", class_="block text-[11px] text-muted-foreground mb-1"),
            el(
                "input",
                id="new-project-pacing",
                name="pacing_wps",
                type="range",
                min="2.0",
                max="3.0",
                step="0.1",
                value=pacing,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Hook text override",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-hook-text",
                name="hook_text",
                type="text",
                placeholder="Hook override (optional)",
                value=hook,
                class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            ),
            el("label", "Outro text", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "input",
                id="new-project-outro-text",
                name="outro_text",
                type="text",
                placeholder="Thanks for watching (leave empty for default)",
                value=outro,
                class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            ),
            el(
                "label",
                "Sections to include",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el("div", id="section-toggle-row", class_="flex flex-wrap gap-2"),
            el(
                "input",
                id="new-project-sections",
                name="sections",
                type="hidden",
                value=json.dumps(sections) if sections else "",
            ),
        ),
        "composer-content-panel",
    )


def _style_panel(profile=None):
    style = _composer_value(profile, "style", {})
    chunk = style.get("chunk_size", 3) if isinstance(style, dict) else 3
    caption_size = style.get("caption_font_size", 56) if isinstance(style, dict) else 56
    outline = style.get("caption_outline_width", 2) if isinstance(style, dict) else 2
    uppercase = style.get("uppercase", False) if isinstance(style, dict) else False
    scrim = style.get("scrim_alpha", 0) if isinstance(style, dict) else 0
    palette = _composer_value(profile, "palette", {})
    colour = (
        "#" + str(_PIPELINE_DEFAULTS["caption_highlight_colour"]).removeprefix("0x")[:6].lower()
    )
    if isinstance(palette, dict) and palette.get("highlight_colour"):
        hex_str = str(palette["highlight_colour"]).removeprefix("0x")
        if len(hex_str) >= 6:
            colour = "#" + hex_str[:6].lower()
    pill_colour = "#" + str(_PIPELINE_DEFAULTS["pill_bg_colour"]).removeprefix("0x")[:6].lower()
    if isinstance(palette, dict) and palette.get("pill_bg_colour"):
        hex_str = str(palette["pill_bg_colour"]).removeprefix("0x")
        if len(hex_str) >= 6:
            pill_colour = "#" + hex_str[:6].lower()
    return _panel(
        "Style — captions, chunking, palette",
        el(
            "div",
            el(
                "label",
                "Caption chunk size (words)",
                class_="block text-[11px] text-muted-foreground mb-1",
            ),
            el(
                "input",
                id="new-project-chunk-size",
                type="range",
                min="1",
                max="6",
                step="1",
                value=chunk,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Caption font size",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-caption-size",
                type="range",
                min="32",
                max="80",
                step="2",
                value=caption_size,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Caption outline width (px)",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-outline-width",
                type="range",
                min="0",
                max="8",
                step="1",
                value=outline,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Highlight colour",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "div",
                el(
                    "input",
                    id="new-project-highlight-colour",
                    type="color",
                    value=colour,
                    class_="w-10 h-8 rounded border border-border",
                ),
                el(
                    "input",
                    id="new-project-pill-colour",
                    type="color",
                    value=pill_colour,
                    class_="w-10 h-8 rounded border border-border ml-2",
                    title="Hook pill background",
                ),
                class_="flex items-center",
            ),
            el(
                "label",
                el(
                    "input",
                    id="new-project-uppercase",
                    type="checkbox",
                    checked=uppercase,
                    class_="accent-primary",
                ),
                el("span", "Uppercase captions", class_="text-xs text-foreground"),
                class_="flex items-center gap-2 mt-3",
            ),
            el(
                "label",
                "Caption scrim alpha",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-scrim",
                type="range",
                min="0",
                max="1",
                step="0.05",
                value=scrim,
                class_="w-full accent-primary",
            ),
        ),
        "composer-style-panel",
        open_default=False,
    )


def _placement_panel(profile=None):
    layout = _composer_value(profile, "layout", {})
    layout = layout if isinstance(layout, dict) else {}
    anchor = layout.get("anchor", "center")
    block_width = layout.get("block_width_pct", 80)
    numbered_scale = layout.get("numbered_scale", 1.6)
    pill_per_word = layout.get("pill_per_word", True)
    watermark_corner = layout.get("watermark_corner", "bottom_right")
    watermark_size = layout.get("watermark_size_pct", 10)
    watermark_opacity = layout.get("watermark_opacity", 0.85)
    music_volume = layout.get("music_volume", 0.2)
    music_fade = layout.get("music_fade_seconds", 2.0)
    fade_out = layout.get("fade_out_seconds", 1.0)

    def anchor_btn(name: str, label: str):
        active = anchor == name
        cls = "anchor-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_anchor=name, class_=cls)

    return _panel(
        "Placement — anchor, block size, numbered screens",
        el(
            "div",
            el("label", "Anchor", class_="block text-[11px] text-muted-foreground mb-1"),
            el(
                "div",
                anchor_btn("center", "Center"),
                anchor_btn("lower_third", "Lower third"),
                id="new-project-anchor",
                class_="flex gap-2",
            ),
            el(
                "label", "Block width %", class_="block text-[11px] text-muted-foreground mb-1 mt-3"
            ),
            el(
                "input",
                id="new-project-block-width",
                type="range",
                min="40",
                max="100",
                step="5",
                value=block_width,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Numbered screen scale",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-numbered-scale",
                type="range",
                min="1.2",
                max="2.5",
                step="0.1",
                value=numbered_scale,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                el(
                    "input",
                    id="new-project-pill-mode",
                    type="checkbox",
                    checked=pill_per_word,
                    class_="accent-primary",
                ),
                el("span", "One word per pill (hook)", class_="text-xs text-foreground"),
                class_="flex items-center gap-2 mt-3",
            ),
            el(
                "label",
                "Watermark corner",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "select",
                el(
                    "option",
                    "Bottom right",
                    value="bottom_right",
                    selected=watermark_corner == "bottom_right",
                ),
                el(
                    "option",
                    "Bottom left",
                    value="bottom_left",
                    selected=watermark_corner == "bottom_left",
                ),
                el(
                    "option",
                    "Top right",
                    value="top_right",
                    selected=watermark_corner == "top_right",
                ),
                el("option", "Top left", value="top_left", selected=watermark_corner == "top_left"),
                id="new-project-watermark-corner",
                class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            ),
            el(
                "label",
                "Watermark size %",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-watermark-size",
                type="range",
                min="5",
                max="30",
                step="1",
                value=watermark_size,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Watermark opacity",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-watermark-opacity",
                type="range",
                min="0.1",
                max="1",
                step="0.05",
                value=watermark_opacity,
                class_="w-full accent-primary",
            ),
            el("label", "Music volume", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "input",
                id="new-project-music-volume",
                type="range",
                min="0.05",
                max="0.5",
                step="0.05",
                value=music_volume,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Music fade (s)",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-music-fade",
                type="range",
                min="0.5",
                max="6",
                step="0.5",
                value=_fmt_number(music_fade),
                class_="w-full accent-primary",
            ),
            el("label", "Fade out (s)", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "input",
                id="new-project-fade-out",
                type="range",
                min="0",
                max="3",
                step="0.1",
                value=_fmt_number(fade_out),
                class_="w-full accent-primary",
            ),
            el("input", id="new-project-layout-json", type="hidden", name="layout", value=""),
        ),
        "composer-placement-panel",
        open_default=False,
    )


def _phase2_panel(profile=None, builtin_profile=None):
    holds = _composer_value(profile, "section_holds", {})
    holds = holds if isinstance(holds, dict) else {}
    builtin_holds = _composer_value(builtin_profile, "section_holds", {})
    builtin_holds = builtin_holds if isinstance(builtin_holds, dict) else {}
    accents = _composer_value(profile, "stage_accents", {})
    accents = accents if isinstance(accents, dict) else {}
    motion = _composer_value(profile, "background_motion", "none")
    emphasis = _composer_value(profile, "emphasis_style", "accent")
    lufs = _fmt_number(_composer_value(profile, "loudness_target_lufs", -14.0))
    normalize = _composer_value(profile, "audio_normalize", True)
    hook_hold = _fmt_number(holds.get("hook", 0.0))
    message_pacing = _fmt_number(float(holds.get("message", 0.0)) + 1.0)
    conclusion_hold = _fmt_number(holds.get("conclusion", 0.0))
    hook_hold_builtin = _fmt_number(builtin_holds.get("hook", 0.0))
    message_pacing_builtin = _fmt_number(float(builtin_holds.get("message", 0.0)) + 1.0)
    conclusion_hold_builtin = _fmt_number(builtin_holds.get("conclusion", 0.0))
    audio_non_default = lufs != "-14" or normalize is not True

    def group_heading(title: str):
        return el(
            "h3",
            title,
            class_="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest",
        )

    def knob(
        label: str,
        widget_id: str,
        widget_type: str,
        min_value: str,
        max_value: str,
        step: str,
        value: str,
        unit: str,
        input_class: str = "w-full accent-primary",
        data_builtin: str | None = None,
    ):
        input_attrs = {
            "id": widget_id,
            "type": widget_type,
            "min": min_value,
            "max": max_value,
            "step": step,
            "value": value,
            "data_default": value,
            "class_": input_class,
        }
        if data_builtin is not None:
            input_attrs["data_builtin"] = data_builtin
        return el(
            "div",
            el(
                "div",
                el("label", label, class_="text-[11px] text-muted-foreground"),
                el(
                    "span",
                    el("span", f"{value} {unit}", id=f"{widget_id}-readout", class_="text-primary"),
                    el(
                        "button",
                        "reset",
                        type="button",
                        onclick=f"resetComposerKnob('{widget_id}')",
                        title=f"Reset {label} to default",
                        class_="underline underline-offset-2 hover:text-primary",
                    ),
                    class_="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5",
                ),
                class_="flex items-center justify-between mb-1",
            ),
            el("input", **input_attrs),
        )

    def motion_btn(name: str, label: str):
        active = motion == name
        cls = "motion-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_motion=name, class_=cls)

    def emphasis_btn(name: str, label: str):
        active = emphasis == name
        cls = "emphasis-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_emphasis=name, class_=cls)

    def accent_chips(stage: str):
        current = accents.get(stage, "")
        chips = [
            el(
                "button",
                "\u2014",
                type="button",
                title="None",
                class_="accent-chip w-7 h-7 rounded-full cursor-pointer transition-colors "
                "bg-secondary grid place-items-center text-[10px] font-mono text-foreground "
                + ("ring-2 ring-primary ring-offset-1" if not current else "ring-1 ring-border"),
            )
        ]
        for name, colour in STAGE_ACCENT_PALETTE.items():
            active = str(current) == colour
            cls = "accent-chip w-7 h-7 rounded-full cursor-pointer transition-colors " + (
                "ring-2 ring-primary ring-offset-1" if active else "ring-1 ring-border"
            )
            chips.append(
                el(
                    "button",
                    type="button",
                    data_accent=name,
                    data_colour=colour,
                    style_=f"background:{colour}",
                    title=name.title(),
                    aria_label=name.title(),
                    class_=cls,
                )
            )
        return el(
            "div",
            *chips,
            id=f"new-project-stage-accent-{stage}",
            role="group",
            aria_label=f"{stage.title()} accent",
            class_="flex flex-wrap gap-1.5",
        )

    return _panel(
        "Pacing & Motion — reel feel",
        el(
            "div",
            group_heading("Pacing"),
            knob(
                "Hook hold (s)",
                "new-project-hold-hook",
                "range",
                "0",
                "1",
                "0.1",
                hook_hold,
                "s",
                data_builtin=hook_hold_builtin,
            ),
            knob(
                "Message pacing (s/line)",
                "new-project-message-pacing",
                "range",
                "0.5",
                "3",
                "0.1",
                message_pacing,
                "s/line",
                data_builtin=message_pacing_builtin,
            ),
            knob(
                "Conclusion hold (s)",
                "new-project-hold-conclusion",
                "range",
                "0",
                "2",
                "0.1",
                conclusion_hold,
                "s",
                data_builtin=conclusion_hold_builtin,
            ),
            group_heading("Motion"),
            el(
                "div",
                motion_btn("none", "None"),
                motion_btn("pan", "Pan"),
                motion_btn("zoom", "Zoom"),
                id="new-project-motion",
                class_="flex gap-2",
            ),
            group_heading("Emphasis"),
            el(
                "div",
                emphasis_btn("off", "Off"),
                emphasis_btn("accent", "Accent"),
                emphasis_btn("scale", "Scale"),
                id="new-project-emphasis",
                class_="flex gap-2",
            ),
            el(
                "details",
                el(
                    "summary",
                    "Audio",
                    class_="cursor-pointer text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest",
                ),
                el(
                    "div",
                    knob(
                        "Loudness target (LUFS)",
                        "new-project-loudness",
                        "number",
                        "-20",
                        "-8",
                        "0.5",
                        lufs,
                        "LUFS",
                        input_class="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                    ),
                    el(
                        "label",
                        el(
                            "input",
                            id="new-project-audio-normalize",
                            type="checkbox",
                            checked=normalize,
                            class_="accent-primary",
                        ),
                        el("span", "Normalize audio (loudnorm)", class_="text-xs text-foreground"),
                        class_="flex items-center gap-2",
                    ),
                    class_="mt-2 space-y-3",
                ),
                open=audio_non_default,
                class_="rounded-lg border border-border/60 px-3 py-2",
            ),
            group_heading("Stage accents"),
            el(
                "div",
                *[
                    el(
                        "div",
                        el(
                            "span",
                            f"{stage.title()} accent",
                            class_="block text-[10px] font-mono text-muted-foreground mb-1",
                        ),
                        accent_chips(stage),
                        class_="mb-2",
                    )
                    for stage in ("hook", "message", "metaphor", "conclusion")
                ],
            ),
            el(
                "input",
                id="new-project-background-motion-json",
                type="hidden",
                name="background_motion",
                value=motion,
            ),
            el(
                "input",
                id="new-project-emphasis-json",
                type="hidden",
                name="emphasis_style",
                value=emphasis,
            ),
            el(
                "input",
                id="new-project-loudness-json",
                type="hidden",
                name="loudness_target_lufs",
                value=lufs if lufs != "-14" else "",
            ),
            el(
                "input",
                id="new-project-audio-normalize-json",
                type="hidden",
                name="audio_normalize",
                value="" if normalize is True else "false",
            ),
            el(
                "input",
                id="new-project-section-holds-json",
                type="hidden",
                name="section_holds",
                value=json.dumps(holds) if any(v for v in holds.values()) else "",
            ),
            el(
                "input",
                id="new-project-stage-accents-json",
                type="hidden",
                name="stage_accents",
                value=json.dumps(accents) if any(v for v in accents.values()) else "",
            ),
            class_="space-y-3",
        ),
        "composer-phase2-panel",
        open_default=False,
    )


def _media_panel(
    asset_options: dict,
    current: dict | None = None,
    stages_json: str = "",
    stock_providers: list[str] | None = None,
    format_name: str | None = None,
    bg_mode: str = "",
):
    current = current or {}
    stock_providers = stock_providers or []
    stages_attrs = {"value": stages_json}
    if stages_json:
        stages_attrs["data_stages"] = stages_json

    stage_toggles = dict(_WIDGET_DEFAULTS["stages"])
    if stages_json:
        try:
            declared_stages = json.loads(stages_json)
        except (ValueError, TypeError):
            declared_stages = None
        if isinstance(declared_stages, dict):
            stage_toggles.update(declared_stages)
    if _fmt_rank(format_name):
        stage_toggles["music"] = True

    def picker(role: str, label: str, allow_url: bool = True, allow_api: bool = False):
        options = asset_options.get(role) or []
        selected = current.get(role)
        current_url = current.get(f"{role}_url") or "" if allow_url else ""
        source_value = current.get(f"{role}_source") or ""
        opts = [el("option", "Auto (default)", value="")]
        for a_id, name in options:
            attrs = {"value": a_id}
            if selected and str(a_id) == str(selected):
                attrs["selected"] = True
            opts.append(el("option", name, **attrs))
        url_attrs = {"value": current_url} if current_url else {}
        source_id = f"new-project-asset-{role}-source"
        asset_id = f"new-project-asset-{role}"
        url_id = f"new-project-asset-{role}-url"
        provider_id = f"new-project-asset-{role}-provider"
        if not allow_url and not allow_api:
            return [
                el(
                    "div",
                    el("label", label, class_="block text-[11px] text-muted-foreground mb-1"),
                    el(
                        "select",
                        *opts,
                        id=asset_id,
                        name=f"asset_{role}_id",
                        class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                    ),
                    class_="col-span-2",
                )
            ]
        source_opts = [el("option", "Assets", value="assets")]
        if allow_url:
            source_opts.append(
                el(
                    "option",
                    "Public URL",
                    value="url",
                    selected=source_value == "url" or (not source_value and bool(current_url)),
                )
            )
        if allow_api:
            source_opts.append(
                el("option", "Stock clip", value="api", selected=source_value == "api")
            )
        provider_select = None
        if allow_api:
            provider_opts = [el("option", "Auto", value="auto")]
            current_provider = current.get(f"{role}_provider") or ""
            for name in stock_providers:
                provider_opts.append(
                    el(
                        "option",
                        PROVIDER_LABELS.get(name, name.title()),
                        value=name,
                        selected=current_provider == name,
                    )
                )
            provider_select = el(
                "select",
                *provider_opts,
                id=provider_id,
                name=f"stock_provider_{role}",
                class_="w-40 flex-1 hidden rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            )
        return [
            el("label", label, class_="col-span-2 block text-[11px] text-muted-foreground"),
            el(
                "select",
                *source_opts,
                id=source_id,
                name=f"media_source_{role}",
                class_="w-32 rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                onchange="toggleMediaSource(this)",
            ),
            el(
                "div",
                el(
                    "select",
                    *opts,
                    id=asset_id,
                    name=f"asset_{role}_id",
                    class_="w-full flex-1 rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                ),
                el(
                    "input",
                    type="url",
                    id=url_id,
                    name=f"media_url_{role}",
                    placeholder="https://...  (public MP3/MP4 link)",
                    class_="w-full flex-1 hidden rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60",
                    **url_attrs,
                ),
                *([provider_select] if provider_select is not None else []),
                class_="flex items-center gap-2",
            ),
        ]

    bg_mode_value = "image" if bg_mode == "image" else "video"
    bg_mode_control = el(
        "div",
        el("label", "Background", class_="block text-[11px] text-muted-foreground mb-1"),
        el(
            "div",
            el(
                "label",
                el(
                    "input",
                    type="radio",
                    name="bg_mode",
                    value="video",
                    checked=bg_mode_value == "video",
                    onchange="toggleBgMode(this)",
                    class_="accent-primary",
                ),
                el("span", "Video", class_="text-xs text-foreground"),
                class_="flex items-center gap-1.5 cursor-pointer",
            ),
            el(
                "label",
                el(
                    "input",
                    type="radio",
                    name="bg_mode",
                    value="image",
                    checked=bg_mode_value == "image",
                    onchange="toggleBgMode(this)",
                    class_="accent-primary",
                ),
                el("span", "Image", class_="text-xs text-foreground"),
                class_="flex items-center gap-1.5 cursor-pointer",
            ),
            class_="flex items-center gap-4",
        ),
        class_="mb-3",
    )

    return _panel(
        "Media & extras — background, music, outro, watermark",
        el(
            "div",
            bg_mode_control,
            el(
                "div",
                *picker(
                    "bg_clip",
                    "Background image" if bg_mode_value == "image" else "Background clip",
                    allow_api=bg_mode_value != "image",
                ),
                *picker("music", "Music track"),
                *picker("outro_clip", "Outro clip"),
                *picker("watermark", "Watermark image"),
                *picker("font", "Font", allow_url=False),
                id="bg-clip-picker-wrapper",
                class_="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-2 items-center",
            ),
            el("label", "Include in reel", class_="block text-[11px] text-muted-foreground mb-1"),
            el(
                "div",
                *[
                    el(
                        "label",
                        el(
                            "input",
                            type="checkbox",
                            data_stage=key,
                            checked=on,
                            class_="accent-primary stage-toggle",
                        ),
                        el("span", _STAGE_LABELS[key], class_="text-xs text-foreground"),
                        class_="flex items-center gap-1.5 text-[11px] text-foreground",
                    )
                    for key, on in stage_toggles.items()
                ],
                id="new-project-stages",
                class_="flex flex-wrap gap-2",
            ),
            el("input", id="new-project-stages-json", type="hidden", name="stages", **stages_attrs),
            el(
                "script",
                """
                function toggleMediaSource(sel) {
                    var role = sel.id.replace('new-project-asset-', '').replace('-source', '');
                    var urlField = document.getElementById('new-project-asset-' + role + '-url');
                    var assetField = document.getElementById('new-project-asset-' + role);
                    var providerField = document.getElementById('new-project-asset-' + role + '-provider');
                    var isUrl = sel.value === 'url';
                    var isApi = sel.value === 'api';
                    if (urlField) {
                        urlField.classList.toggle('hidden', !isUrl);
                        urlField.disabled = !isUrl;
                    }
                    if (assetField) {
                        assetField.classList.toggle('hidden', isUrl || isApi);
                        assetField.disabled = isUrl || isApi;
                    }
                    if (providerField) {
                        providerField.classList.toggle('hidden', !isApi);
                        providerField.disabled = !isApi;
                    }
                }
                document.querySelectorAll('[id$="-source"]').forEach(toggleMediaSource);
                """,
            ),
            id="composer-media-panel",
        ),
        "composer-media-panel-wrapper",
    )


def _spec_panel():
    return _panel(
        "Live summary",
        el(
            "div",
            el(
                "div",
                id="composer-summary",
                class_="text-[11px] text-foreground bg-secondary/40 rounded-lg px-3 py-2",
            ),
            el(
                "details",
                el(
                    "summary",
                    "Structured spec",
                    class_="cursor-pointer text-[11px] font-mono font-semibold text-muted-foreground",
                ),
                el("div", id="spec-structured", class_="text-[11px] font-mono text-foreground"),
                class_="rounded-lg border border-border/60 px-3 py-2",
            ),
            el(
                "details",
                el(
                    "summary",
                    "Raw spec",
                    class_="cursor-pointer text-[11px] font-mono font-semibold text-muted-foreground",
                ),
                el(
                    "pre",
                    id="spec-json",
                    class_="whitespace-pre-wrap break-all font-mono text-[10px] text-muted-foreground max-h-64 overflow-auto",
                ),
                class_="rounded-lg border border-border/60 px-3 py-2",
            ),
            class_="space-y-2",
        ),
        "composer-spec-panel",
        open_default=False,
    )


def _presets_panel():
    return _panel(
        "Presets — save & apply composition bundles",
        el(
            "div",
            el(
                "label",
                "Start from a bundle",
                class_="block text-[11px] text-muted-foreground mb-1",
            ),
            el("div", id="preset-chips", class_="flex flex-wrap gap-1.5"),
            el("label", "Saved preset", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "select",
                id="preset-select",
                class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            ),
            el(
                "div",
                ActionButton("Apply", onclick="applyPreset()", class_extra="flex-1"),
                ActionButton(
                    "Save current", onclick="savePreset()", variant="ghost", class_extra="flex-1"
                ),
                ActionButton(
                    "Delete", onclick="deletePreset()", variant="danger", class_extra="flex-1"
                ),
                class_="flex gap-2 mt-3",
            ),
            el(
                "p",
                "Bundles the current knob values; Apply re-sets every knob from a saved spec.",
                class_="text-[10px] font-mono text-muted-foreground mt-2",
            ),
        ),
        "composer-presets-panel",
        class_extra=" md:col-span-2",
    )


def _composer_preview_json() -> dict:
    """Live-preview payload shared by the create page and the compose
    page: format + topic declarations only (profile-independent)."""
    active_classes = _active_classes()
    return {
        "formats": {
            f.name: {
                "label": f.label,
                "skeleton": _SKELETONS.get(f.name, _SKELETONS["narrated"]),
                "duration_range": list(f.duration_range),
                "caption_styles": list(f.caption_styles),
                "rank": "top_items" in (f.requires.get("script") or []),
                "layout": {
                    "anchor": (f.layout or {}).get("anchor", "center"),
                    "block_width_pct": (f.layout or {}).get("block_width_pct", [60, 95]),
                    "numbered_scale": (f.layout or {}).get("numbered_scale", [1.2, 2.5]),
                    "pill_per_word": (f.layout or {}).get("pill_per_word", True),
                },
                "palette": {
                    "highlight_colour": (f.palette or {}).get(
                        "highlight_colour", str(_PIPELINE_DEFAULTS["caption_highlight_colour"])
                    ),
                    "pill_bg_colour": (f.palette or {}).get(
                        "pill_bg_colour", str(_PIPELINE_DEFAULTS["pill_bg_colour"])
                    ),
                },
                "pacing_wps_range": list(f.pacing_wps_range),
            }
            for f in formats.available
        },
        "topics": {
            t.name: {
                "emoji": _type_meta(t.name)["emoji"],
                "active_classes": active_classes.get(t.name, []),
                "sections": list(t.structure_sections),
            }
            for t in registry.available
        },
    }


def composer_preview_js() -> str:
    """Phone-preview + composer-knob JS shared by the create page and the
    compose page (widgets are initialized from the resolved profile)."""
    payload = json.dumps(_composer_preview_json())
    return Markup(
        f"<script>window.__PREVIEW_JSON__ = {payload}; "
        f"window.__PREVIEW_DATA_OBJ__ = window.__PREVIEW_JSON__;</script>"
        '<script src="/static/js/composer-preview.js"></script>'
    )


def new_project_form(
    config: AppConfig | None = None,
    profile: EffectiveProjectProfile | None = None,
    compatible: dict[str, list[str]] | None = None,
    asset_options: dict[str, list[tuple[str, str]]] | None = None,
    stock_providers: list[str] | None = None,
):
    profile = profile or fallback_profile(config)
    topic = registry.get(profile.topic.value) if profile.topic else None
    topic_sections = list(topic.structure_sections) if topic else None
    selected_topic = profile.topic.value if profile.topic else "self_improvement"
    type_buttons = []
    active_classes = _active_classes()

    for t in registry.available:
        meta = _type_meta(t.name)
        is_default = t.name == selected_topic
        cls = (
            "shrink-0 type-btn flex items-center gap-2.5 px-4 py-3 rounded-xl text-xs font-semibold "
            "transition-all duration-200 border cursor-pointer select-none "
            + (
                " ".join(active_classes[t.name])
                if is_default
                else "bg-card/60 " + meta["color_inactive"] + " text-muted-foreground"
            )
        )
        type_buttons.append(
            el(
                "div",
                el("span", meta["emoji"], class_="text-xl"),
                el(
                    "div",
                    el("div", t.label, class_="font-semibold leading-none text-[11px]"),
                    el("div", meta["desc"], class_="text-[10px] opacity-60 font-normal mt-0.5"),
                    class_="text-left",
                ),
                id=f"type-btn-{t.name}",
                class_=cls,
                onclick=f"selectFramework('{t.name}')",
                data_type=t.name,
            )
        )

    magic_js = _wizard_globals_js(active_classes, compatible)

    input_cls = "w-full bg-card/80 border border-border/80 rounded-xl px-4 py-2.5 text-sm text-foreground placeholder-secondary focus:outline-none focus:border-primary/60 transition-all duration-200"
    label_cls = "block text-xs font-semibold text-foreground mb-1.5 font-mono"
    help_cls = "text-muted-foreground text-[11px] mt-1.5 font-mono"

    title_field = el(
        "div",
        el("label", "Project Title", for_="new-project-title", class_=label_cls),
        el(
            "input",
            type="text",
            id="new-project-title",
            name="title",
            placeholder="e.g. Monday Motivation",
            value="",
            autocomplete="off",
            class_=input_cls,
        ),
        class_="mb-5",
    )

    type_field = el(
        "div",
        el("div", *type_buttons, class_="flex gap-2 overflow-x-auto pb-1"),
        el("input", type="hidden", id="new-project-type", name="topic", value=selected_topic),
    )

    focus_field = el(
        "div",
        el("label", "Focus", for_="new-project-focus", class_=label_cls),
        el(
            "input",
            type="text",
            id="new-project-focus",
            name="focus",
            placeholder="e.g. morning routine, productivity, mindset",
            value="",
            autocomplete="off",
            class_=input_cls,
        ),
        el("p", "Seeds AI idea generation and SEO keyword research", class_=help_cls),
        class_="mb-5",
    )

    format_field = _wizard_format_field(profile)
    duration_field = _wizard_duration_field(profile)
    caption_field = _wizard_caption_field(profile)

    header = el(
        "div",
        el(
            "a",
            "\u2190 Projects",
            href="/projects",
            hx_get="/projects",
            hx_target="#main-content",
            hx_push_url="/projects",
            class_="text-[11px] font-mono text-primary hover:text-primary transition-colors mb-3 inline-block",
        ),
        el("h1", "Create Project", class_="text-2xl font-bold text-foreground tracking-tight"),
        el(
            "p",
            "Turn an idea into a video — choose a topic and set your creative defaults.",
            class_="text-muted-foreground text-xs mt-1 font-mono",
        ),
        class_="pb-5 border-b border-border/80 mb-6",
    )

    wizard_tab = el(
        "div",
        el(
            "div",
            el(
                "div",
                _field_section(
                    "Project",
                    el(
                        "div",
                        title_field,
                    ),
                ),
                _field_section(
                    "Content",
                    el(
                        "div",
                        format_field,
                        duration_field,
                    ),
                ),
                _field_section(
                    "Topic",
                    el(
                        "div",
                        type_field,
                        focus_field,
                    ),
                ),
                _field_section(
                    "Style",
                    el(
                        "div",
                        el("div", caption_field, id="new-project-caption-field"),
                    ),
                ),
            ),
            el(
                "div",
                _details_pane(
                    _skeleton_rows("topn", "preview-skeleton-topn"),
                    _skeleton_rows("narrated", "preview-skeleton-narrated", topic_sections),
                    profile,
                ),
            ),
            class_="grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        id="create-wizard-tab",
        data_create_tab="form",
        class_="create-tab-panel",
    )

    panels = [
        _presets_panel(),
        _content_panel(),
        _style_panel(),
        _placement_panel(),
        _phase2_panel(),
        _media_panel(
            asset_options or {},
            stock_providers=stock_providers,
            format_name=profile.format_name.value if profile.format_name else None,
            bg_mode=_composer_value(profile, "bg_mode") or "",
        ),
        _spec_panel(),
    ]

    knobs_tab = el(
        "div",
        el(
            "div",
            *panels,
            id="composer-panels",
            class_="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4",
        ),
        id="composer-knobs-tab",
        data_create_tab="composer",
        class_="create-tab-panel hidden",
    )

    tab_btn_active = (
        "px-4 py-2 text-xs font-semibold font-mono rounded-t-lg border-b-2 transition-colors cursor-pointer "
        "text-primary border-primary bg-card/60"
    )
    tab_btn_inactive = (
        "px-4 py-2 text-xs font-semibold font-mono rounded-t-lg border-b-2 transition-colors cursor-pointer "
        "text-muted-foreground border-transparent hover:text-foreground hover:border-border"
    )

    return el(
        "div",
        header,
        _compose_steps_strip(),
        el(
            "div",
            el(
                "form",
                el(
                    "div",
                    el(
                        "button",
                        "Form",
                        type="button",
                        data_create_tab="form",
                        onclick="switchCreateTab('form')",
                        class_=tab_btn_active,
                    ),
                    el(
                        "button",
                        "Composer",
                        type="button",
                        data_create_tab="composer",
                        onclick="switchCreateTab('composer')",
                        class_=tab_btn_inactive,
                    ),
                    id="create-tabs",
                    class_="flex items-center gap-0 border-b border-border/60 mb-4",
                ),
                el("div", id="create-project-feedback", class_="mb-4"),
                wizard_tab,
                knobs_tab,
                Markup(preview_styles),
                Markup(composer_preview_js()),
                magic_js,
                id="create-project-form",
                method="post",
                action="/api/projects/upsert",
                hx_post="/api/projects/upsert",
                hx_target="#create-project-feedback",
                hx_swap="innerHTML",
                class_="md:col-span-2",
            ),
            el(
                "div",
                Markup(_preview_phone(active_classes)),
                ActionButton(
                    "Create Project",
                    icon=plus(),
                    size="lg",
                    type="submit",
                    form="create-project-form",
                    class_extra="w-full",
                ),
                class_="md:col-span-1 space-y-6 md:sticky md:top-6 md:self-start",
            ),
            class_="grid grid-cols-1 md:grid-cols-3 gap-6",
        ),
    )


def _compose_steps_strip() -> str:
    """Four numbered guide chips above the composer.

    Steps 1/3/4 jump to the relevant tab or control. Step 2 is a hint —
    scripts are generated on the runs page after the project is saved.
    """

    arrow = el("span", "→", class_="text-muted-foreground/40 text-[10px]")

    def chip(num: str, label: str, onclick: str | None = None, hint: str | None = None):
        inner = el(
            "span",
            el(
                "span",
                num,
                class_="w-4 h-4 grid place-items-center rounded-full bg-primary/15 text-primary text-[9px] font-bold shrink-0",
            ),
            el("span", label, class_="whitespace-nowrap"),
            class_="flex items-center gap-1.5",
        )
        if onclick:
            return el(
                "button",
                inner,
                type="button",
                onclick=onclick,
                title=hint or "",
                class_=(
                    "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-mono cursor-pointer "
                    "text-foreground/85 border border-border/60 bg-card/50 "
                    "hover:border-primary/40 hover:text-primary transition-colors"
                ),
            )
        return el(
            "div",
            inner,
            title=hint or "",
            class_=(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-mono "
                "text-muted-foreground/70 border border-dashed border-border/50 bg-background/40"
            ),
        )

    return Markup(
        str(
            el(
                "div",
                chip(
                    "1",
                    "Topic & format",
                    onclick="switchCreateTab('form'); window.scrollTo({top:0,behavior:'smooth'});",
                    hint="Pick topic, format and duration",
                ),
                arrow,
                chip("2", "Script", hint="Scripts are generated on the runs page after saving"),
                arrow,
                chip(
                    "3",
                    "Media & visuals",
                    onclick="switchCreateTab('composer'); var el=document.getElementById('composer-media-panel-wrapper'); if(el) el.scrollIntoView({behavior:'smooth'});",
                    hint="Background, music, outro, watermark, captions",
                ),
                arrow,
                chip(
                    "4",
                    "Save",
                    onclick="var el=document.querySelector('#create-project-form button[type=submit]'); if(el) el.scrollIntoView({behavior:'smooth'});",
                    hint="Create the project — rendering starts on its runs page",
                ),
                id="compose-steps-strip",
                class_="flex flex-wrap items-center gap-2 mb-5 pt-1",
            )
        )
    )


def project_settings_form(
    project,
    profile: EffectiveProjectProfile,
    asset_options: dict[str, list[tuple[str, str]]] | None = None,
    stock_providers: list[str] | None = None,
    builtin_profile: EffectiveProjectProfile | None = None,
):
    """Composer-driven settings editor for an existing project.

    Reuses the same composer panels + live phone preview as the create page,
    plus the editable wizard fields (format/duration/caption style).
    The profile-driven hidden inputs carry no `name`, so they never affect the
    save payload; untouched knobs keep inherited provenance instead of being
    persisted as project overrides. Rendered in the project shell by the
    ProjectSettingsController (header + Settings tab).
    builtin_profile is the same resolution with the project's overrides
    suppressed; it seeds the pacing knobs' data_builtin (reset target)."""
    active_classes = _active_classes()
    topic = registry.get(profile.topic.value) if profile.topic else None

    hidden_inputs = []
    composites = [
        ("new-project-type", profile.topic.value if profile.topic else "self_improvement"),
        ("new-project-title", getattr(project, "title", "") or ""),
    ]
    for el_id, value in composites:
        attrs = {"type": "hidden", "id": el_id, "value": value}
        hidden_inputs.append(el("input", **attrs))

    stored_sections = _composer_value(profile, "sections")
    if not stored_sections and topic is not None:
        stored_sections = list(topic.structure_sections)
    stages = _composer_value(profile, "stages")
    stages_json = json.dumps(stages) if stages else ""

    current_assets = {}
    for role, pkey in (
        ("bg_clip", "asset_bg_clip_id"),
        ("music", "asset_music_id"),
        ("outro_clip", "asset_outro_clip_id"),
        ("font", "asset_font_id"),
        ("watermark", "asset_watermark_id"),
    ):
        value = _composer_value(profile, pkey)
        if value:
            current_assets[role] = value
    for role, url_key in (
        ("bg_clip", "media_url_bg_clip"),
        ("music", "media_url_music"),
        ("outro_clip", "media_url_outro"),
        ("watermark", "media_url_watermark"),
    ):
        value = _composer_value(profile, url_key)
        if value:
            current_assets[f"{role}_url"] = value
    if _composer_value(profile, "bg_source") == "api":
        current_assets["bg_clip_source"] = "api"
        current_assets["bg_clip_provider"] = _composer_value(profile, "stock_provider") or "auto"

    return el(
        "div",
        el(
            "form",
            *hidden_inputs,
            el("div", id="project-settings-feedback", class_="mb-4"),
            el(
                "div",
                _wizard_format_field(profile),
                _wizard_duration_field(profile),
                el("div", _wizard_caption_field(profile), id="new-project-caption-field"),
                class_="mb-6",
            ),
            el(
                "div",
                _presets_panel(),
                _content_panel(profile),
                _style_panel(profile),
                _placement_panel(profile),
                _phase2_panel(profile, builtin_profile),
                _media_panel(
                    asset_options or {},
                    current=current_assets,
                    stages_json=stages_json,
                    stock_providers=stock_providers,
                    format_name=profile.format_name.value if profile.format_name else None,
                    bg_mode=_composer_value(profile, "bg_mode") or "",
                ),
                _spec_panel(),
                id="composer-panels",
                class_="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4",
            ),
            Markup(preview_styles),
            Markup(composer_preview_js()),
            _wizard_globals_js(active_classes, compatible_formats_by_topic()),
            id="project-profile-form",
            method="post",
            action=f"/api/projects/{project.id}/settings",
            hx_post=f"/api/projects/{project.id}/settings",
            hx_target="#project-settings-feedback",
            hx_swap="innerHTML",
            hx_indicator="#profile-save-indicator",
            data_dirty="false",
            class_="md:col-span-2",
        ),
        el(
            "div",
            Markup(_preview_phone(active_classes)),
            el(
                "div",
                _profile_strip(
                    profile,
                    reset_url=f"/api/projects/{project.id}/reset-override",
                ),
                el(
                    "span",
                    "Saving\u2026",
                    id="profile-save-indicator",
                    class_="htmx-indicator text-xs text-primary",
                ),
                ActionButton(
                    "Save Settings",
                    size="lg",
                    type="submit",
                    id="profile-save-btn",
                    form="project-profile-form",
                    class_extra="w-full",
                ),
                class_="space-y-3",
            ),
            class_="md:col-span-1 space-y-6 md:sticky md:top-6 md:self-start",
        ),
        class_="grid grid-cols-1 md:grid-cols-3 gap-6",
    )
