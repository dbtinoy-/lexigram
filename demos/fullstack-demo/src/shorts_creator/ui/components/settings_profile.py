"""Reusable profile settings UI primitives.

Shared by the project profile editor (composer-driven, see
`ui/pages/new_project.project_settings_form`) and the global settings
surface. Settings rendered here treat every value as a resolved setting so
callers can show provenance without re-implementing the source tiers.
"""

from html import escape
from typing import Any

from markupsafe import Markup

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)

INPUT_CLASSES = (
    "w-full bg-background border border-border rounded-lg px-3 py-2 "
    "text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors"
)

SOURCE_LABELS = {
    ProfileSource.PROJECT: "Project override",
    ProfileSource.FORMAT: "Format",
    ProfileSource.GLOBAL: "Global Default",
    ProfileSource.BUILT_IN: "Built-in",
}

CAPTION_STYLE_LABELS = {
    "highlight": "Highlight (word-by-word)",
    "plain": "Plain (static lines)",
    "list": "List",
}


def caption_style_label(fmt, value: str | None) -> str | None:
    """Human label for a caption-style value in a format context.

    Ranked formats (style-less with top_items) call the empty value
    "Per-item screens"; style-less formats without ranked items render no
    captions and yield None. Unknown values pass through unchanged.
    """
    if value:
        return CAPTION_STYLE_LABELS.get(value, value)
    if fmt is None:
        return None
    styles = list(fmt.caption_styles)
    if "top_items" in (fmt.requires.get("script") or []):
        return "Per-item screens"
    if styles:
        return CAPTION_STYLE_LABELS.get(styles[0], styles[0])
    return None


SOURCE_COLORS = {
    ProfileSource.PROJECT: "bg-success/70 text-success border border-success/40",
    ProfileSource.FORMAT: "bg-info/70 text-info border border-info/40",
    ProfileSource.GLOBAL: "bg-warning/70 text-warning border border-warning/40",
    ProfileSource.BUILT_IN: "bg-secondary/70 text-muted-foreground border border-border/40",
}

_COUNTABLE_FIELDS = (
    "duration_seconds",
    "caption_style",
    "format_name",
    "asset_music_id",
    "asset_font_id",
    "asset_bg_clip_id",
    "asset_outro_clip_id",
    "asset_watermark_id",
)


def source_badge(setting: ResolvedSetting[Any]) -> str:
    label = SOURCE_LABELS.get(setting.source, setting.source.value)
    color = SOURCE_COLORS.get(setting.source, SOURCE_COLORS[ProfileSource.BUILT_IN])
    return (
        f'<span data-source="{escape(setting.source.value)}" class="inline-block text-[10px] font-mono '
        f'px-1.5 py-0.5 rounded {color}">{escape(label)}</span>'
    )


def _override_reset(key: str, reset_url: str = "") -> str:
    url_attr = f' data-reset-url="{escape(reset_url)}"' if reset_url else ""
    return (
        f'<button type="button" data-override-toggle data-key="{escape(key)}"{url_attr} '
        f'class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/60 '
        f'text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors cursor-pointer" '
        f'title="Reset this field">Reset</button>'
    )


def _field_block(
    key: str,
    label: str,
    input_html: str,
    setting: ResolvedSetting,
    help_text: str = "",
    reset_url: str = "",
) -> str:
    meta = source_badge(setting)
    if setting.is_overridden:
        meta += _override_reset(key, reset_url)
    help_html = (
        f'<p class="text-[11px] text-muted-foreground mt-1">{escape(help_text)}</p>'
        if help_text
        else ""
    )
    return (
        f'<div data-profile-field="{escape(key)}" id="profile-field-{escape(key)}" class="mb-4">'
        f'<label for="{escape(key)}" class="block text-foreground text-xs font-semibold mb-1.5">{escape(label)}</label>'
        f"{input_html}"
        f'<div id="profile-field-error-{escape(key)}" class="profile-error-slot"></div>'
        f'{help_html}<div class="flex items-center gap-1.5 mt-1.5 flex-wrap">{meta}</div>'
        f"</div>"
    )


def profile_field(
    key: str,
    label: str,
    setting: ResolvedSetting[object],
    input_html: str,
    help_text: str = "",
    reset_url: str = "",
) -> str:
    return _field_block(key, label, input_html, setting, help_text, reset_url)


def profile_summary(profile: EffectiveProjectProfile) -> str:
    customized = sum(
        1
        for name in _COUNTABLE_FIELDS
        if (setting := getattr(profile, name)) is not None
        and setting.value is not None
        and setting.source is ProfileSource.PROJECT
    )
    inherited = sum(
        1
        for name in _COUNTABLE_FIELDS
        if (setting := getattr(profile, name)) is not None
        and setting.value is not None
        and setting.source is not ProfileSource.PROJECT
    )
    return Markup(
        f'<span id="profile-summary" class="text-xs font-mono text-muted-foreground">'
        f'<span class="text-success">Customized: {customized}</span>'
        f'<span class="mx-2 text-muted-foreground">|</span>'
        f'<span class="text-foreground">Inherited: {inherited}</span></span>'
    )


def profile_error_slot(key: str, message: str) -> str:
    """Inline per-field error annotation, out-of-band swapped next to the input."""
    return (
        f'<div id="profile-field-error-{escape(key)}" '
        f'hx-swap-oob="innerHTML:#profile-field-error-{escape(key)}" '
        f'class="text-destructive text-[11px] font-mono mt-1">{escape(message)}</div>'
    )


def profile_error_feedback(
    errors: dict[str, str],
    headline: str = "Could not save — fix the values below",
) -> str:
    """Inline error fragment: summary box plus per-field out-of-band annotations.

    The response is targeted at an in-form feedback container (the caller's
    ``hx-target``), so the surrounding form and the entered values survive;
    each ``profile_error_slot`` node swaps into the matching
    ``profile-field-error-*`` slot inside the form's field blocks.
    """
    rows = "".join(
        f'<div class="flex items-baseline gap-2"><span class="font-mono text-destructive">{escape(k)}</span>'
        f'<span class="text-destructive">{escape(v)}</span></div>'
        for k, v in errors.items()
    )
    field_errors = "".join(profile_error_slot(k, v) for k, v in errors.items())
    return (
        f'<div class="p-3 rounded-xl border border-destructive/50 bg-destructive/40 text-destructive text-xs">'
        f'<div class="font-semibold mb-1">{escape(headline)}</div>' + rows + "</div>" + field_errors
    )


def _number_input(key: str, value: str) -> str:
    return f'<input type="number" step="any" id="{escape(key)}" name="{escape(key)}" value="{escape(value)}" class="{INPUT_CLASSES}">'
