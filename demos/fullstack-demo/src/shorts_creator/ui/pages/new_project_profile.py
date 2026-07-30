from html import escape

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.services.core import AppConfig
from shorts_creator.ui.components.settings_profile import (
    caption_style_label,
    profile_summary,
    source_badge,
)

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
