import json

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
)
from shorts_creator.pipeline.render_config import (
    _DEFAULTS as _PIPELINE_DEFAULTS,
)
from shorts_creator.services.core import AppConfig
from shorts_creator.topics import registry
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.icons import plus
from shorts_creator.ui.pages.new_project_panels import (
    _active_classes,
    _composer_value,
    _content_panel,
    _details_pane,
    _media_panel,
    _phase2_panel,
    _placement_panel,
    _presets_panel,
    _spec_panel,
    _style_panel,
    _type_meta,
)
from shorts_creator.ui.pages.new_project_preview import (
    _preview_phone,
    preview_styles,
)
from shorts_creator.ui.pages.new_project_profile import (
    _field_section,
    fallback_profile,
)
from shorts_creator.ui.pages.new_project_wizard import (
    _SKELETONS,
    _skeleton_rows,
    _wizard_caption_field,
    _wizard_duration_field,
    _wizard_format_field,
    _wizard_globals_js,
)

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


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
