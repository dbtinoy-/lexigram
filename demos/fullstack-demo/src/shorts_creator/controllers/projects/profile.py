import json
from html import escape

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.ui.components.settings_profile import caption_style_label, source_badge


def _card_row(label: str, value: str, key: str, setting, reset_url: str) -> str:
    meta = source_badge(setting)
    if setting.is_overridden:
        meta += (
            f'<button type="button" data-override-toggle data-key="{escape(key)}" '
            f'data-reset-url="{escape(reset_url)}" '
            f'class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/60 '
            f'text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors cursor-pointer" '
            f'title="Reset to inherited default">Reset</button>'
        )
    return (
        '<div class="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0">'
        f'<span class="text-xs font-mono text-muted-foreground">{escape(label)}</span>'
        '<span class="flex items-center gap-2 text-xs font-mono text-foreground">'
        f'<span class="truncate">{escape(value)}</span>{meta}</span></div>'
    )


def _profile_card(project, profile, asset_options) -> str:
    if profile is None:
        return ""
    reset_url = f"/api/projects/{project.id}/reset-override"
    rows = []
    for label, value in (
        (
            "Duration",
            f"{profile.duration_seconds.value:.0f}s" if profile.duration_seconds else None,
        ),
        (
            "Format",
            profile.format_name.value if profile.format_name else None,
        ),
        (
            "Caption style",
            caption_style_label(
                formats.get(profile.format_name.value) if profile.format_name else None,
                profile.caption_style.value if profile.caption_style else None,
            ),
        ),
        (
            "Reel",
            f"{profile.reel_width.value}×{profile.reel_height.value}"
            if profile.reel_width and profile.reel_height
            else None,
        ),
    ):
        if value is None:
            continue
        rows.append(
            '<div class="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0">'
            f'<span class="text-xs font-mono text-muted-foreground">{escape(label)}</span>'
            f'<span class="text-xs font-mono text-foreground">{escape(str(value))}</span></div>'
        )
    for label, key, role in (
        ("Music", "asset_music_id", "music"),
        ("Font", "asset_font_id", "font"),
        ("Background clip", "asset_bg_clip_id", "bg_clip"),
        ("Outro clip", "asset_outro_clip_id", "outro_clip"),
        ("Watermark", "asset_watermark_id", "watermark"),
    ):
        setting = getattr(profile, key, None)
        if setting is None or not setting.value:
            continue
        name = dict(asset_options.get(role, [])).get(setting.value, setting.value)
        rows.append(_card_row(label, str(name), key, setting, reset_url))
    for label, key, display in (
        ("Stage accents", "stage_accents", lambda v: json.dumps(v)),
        ("Section holds", "section_holds", lambda v: json.dumps(v)),
        ("Loudness target (LUFS)", "loudness_target_lufs", str),
        ("Audio normalize", "audio_normalize", str),
    ):
        setting = getattr(profile, key, None)
        if setting is None or setting.value is None:
            continue
        if isinstance(setting.value, dict) and not setting.value:
            continue
        rows.append(_card_row(label, display(setting.value), key, setting, reset_url))
    if not rows:
        return ""
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "EFFECTIVE PROFILE",
                        class_="text-[11px] font-mono font-semibold text-muted-foreground",
                    ),
                    el(
                        "a",
                        "Edit Settings →",
                        href=f"/projects/{project.id}/settings",
                        hx_get=f"/projects/{project.id}/settings",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{project.id}/settings",
                        class_="text-[11px] font-mono font-semibold text-primary hover:text-primary",
                    ),
                    class_="flex items-center justify-between mb-2",
                ),
                el(
                    "div",
                    Markup("".join(rows)),
                    class_="rounded-xl border border-border/60 bg-background/50 px-4 py-3",
                ),
                class_="rounded-2xl border border-border/60 bg-card/40 p-4",
            )
        )
    )
