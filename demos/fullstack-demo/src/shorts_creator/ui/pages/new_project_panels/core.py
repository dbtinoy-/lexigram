import json

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.models.project_profile import EffectiveProjectProfile
from shorts_creator.topics import registry
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.pages.new_project_profile import _fmt_number, _profile_strip

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
