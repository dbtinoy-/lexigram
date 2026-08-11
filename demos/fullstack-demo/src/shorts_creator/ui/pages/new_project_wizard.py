import json

from lexigram.ui import Element, el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
)
from shorts_creator.ui.pages.new_project_profile import _fmt_number

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


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
