from html import escape

from lexigram.ui import RawHTML, el, raw, render_to_string
from lexigram.web import Controller, HTMLContent, get, post

from shorts_creator.formats import registry as formats_registry
from shorts_creator.services.project_profile_service import compatible_formats_by_topic
from shorts_creator.services.topic_profile_service import TopicProfileService
from shorts_creator.topics import registry
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.shell import AppLayout

_INPUT_CLASSES = (
    "w-full bg-background border border-border rounded-lg px-3 py-2 "
    "text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors"
)


def _topic(name: str):
    return registry.get(name)


def _topic_label(name: str) -> str:
    topic = _topic(name)
    return topic.label if topic else name


def _topic_description(name: str) -> str:
    topic = _topic(name)
    return topic.description if topic else ""


def _text_input(key: str, value: str, readonly: bool = False) -> RawHTML:
    readonly_attr = " readonly" if readonly else ""
    return raw(
        f'<input type="text" id="{escape(key)}" name="{escape(key)}" value="{escape(value)}" class="{_INPUT_CLASSES}"{readonly_attr}>'
    )


def _textarea(name: str, value: str) -> RawHTML:
    return raw(
        f'<textarea id="{escape(name)}" name="{escape(name)}" rows="{2 if name == "topic_categories" else 4}" '
        f'class="{_INPUT_CLASSES} resize-y">{escape(value)}</textarea>'
    )


def _safe_topic_name(name: str) -> bool:
    """Only bare names (no slashes, no dot segments) may reach the service."""
    return bool(name) and "/" not in name and "\\" not in name and name not in (".", "..")


class TopicsController(Controller):
    def __init__(self, profile_service: TopicProfileService):
        self.layout = AppLayout()
        self.profile_service = profile_service

    @get("/topics")
    async def list_topics(self, request=None) -> HTMLContent:
        profiles = await self.profile_service.list()
        cards = []
        for profile in profiles:
            overrides = await self.profile_service.count_overrides(profile.name)
            if overrides:
                chip = "text-[11px] font-mono text-warning bg-warning/40 px-1.5 py-0.5 rounded border border-warning/30 mr-2"
            else:
                chip = "text-[11px] font-mono text-muted-foreground px-1.5 py-0.5 rounded border border-border/40 mr-2"
            cards.append(
                str(
                    el(
                        "div",
                        el(
                            "div",
                            el(
                                "h3",
                                _topic_label(profile.name),
                                class_="text-sm font-semibold text-foreground",
                            ),
                            el(
                                "p",
                                _topic_description(profile.name),
                                class_="text-xs text-muted-foreground mt-1",
                            ),
                            el(
                                "div",
                                el(
                                    "span",
                                    f"Structure: {len(profile.structure_sections)} sections",
                                    class_="text-[11px] font-mono text-muted-foreground px-1.5 py-0.5 rounded border border-border/40 mr-2",
                                ),
                                el("span", f"Overrides: {overrides}", class_=chip),
                                class_="flex items-center mt-2 flex-wrap gap-y-1",
                            ),
                            class_="mt-4",
                        ),
                        el(
                            "a",
                            "Edit →",
                            href=f"/topics/{profile.name}",
                            hx_get=f"/topics/{profile.name}",
                            hx_target="#main-content",
                            hx_push_url=f"/topics/{profile.name}",
                            class_="mt-3 inline-block text-primary hover:text-primary text-xs font-semibold transition-colors",
                        ),
                        class_="bg-card/40 border border-border/60 rounded-xl p-4 flex flex-col",
                    )
                )
            )

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el("h1", "Topics", class_="text-2xl font-bold text-foreground tracking-tight"),
                    el(
                        "p",
                        "Content frameworks used to generate ideas & scripts",
                        class_="text-muted-foreground text-xs mt-1 font-mono",
                    ),
                    class_="pb-4 border-b border-border/80",
                ),
                el(
                    "div",
                    *cards,
                    class_="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6",
                ),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title="Topics", request=request)
        return HTMLContent(html)

    @get("/topics/{name}")
    async def edit_topic(self, request=None, name: str = "") -> HTMLContent:
        profile = await self.profile_service.get(name)
        if profile is None:
            return HTMLContent("<div class='text-destructive p-8'>Topic not found</div>")

        topic = _topic(name)
        label = topic.label if topic else name
        description = topic.description if topic else ""

        structure_html = raw(
            "".join(
                str(
                    el(
                        "span",
                        section,
                        class_="text-[11px] font-mono text-foreground bg-secondary/60 px-1.5 py-0.5 rounded border border-border/40 mr-1.5",
                    )
                )
                for section in profile.structure_sections
            )
        )
        pacing_chips = []
        compatible = compatible_formats_by_topic().get(name, [])
        if compatible:
            fmt_def = formats_registry.get(compatible[0])
            if fmt_def:
                lo, hi = fmt_def.duration_range
                wlo, whi = fmt_def.pacing_wps_range
                pacing_chips = [
                    f"Duration: {lo}\u2013{hi}s",
                    f"Pacing: {wlo:.1f}\u2013{whi:.1f} wps",
                    f"via {fmt_def.label}",
                ]
        prompt_blocks = []
        if topic is not None:
            if topic.idea_prompt:
                prompt_blocks.append(("Idea prompt", topic.idea_prompt))
            if topic.script_prompt:
                prompt_blocks.append(("Script prompt", topic.script_prompt))

        content = render_to_string(
            el(
                "div",
                el(
                    "a",
                    "← Back to Topics",
                    href="/topics",
                    hx_get="/topics",
                    hx_target="#main-content",
                    hx_push_url="/topics",
                    class_="text-primary hover:text-primary text-xs font-semibold transition-colors",
                ),
                el(
                    "h1",
                    f"Edit: {label}",
                    class_="text-2xl font-bold text-foreground tracking-tight mt-4",
                ),
                el(
                    "form",
                    el(
                        "div",
                        el(
                            "label",
                            "Label",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="label",
                        ),
                        _text_input("label", label, readonly=True),
                        el(
                            "p",
                            "Managed by the skill file (SKILL.md) \u2014 read-only in the web editor.",
                            class_="text-[11px] text-muted-foreground mt-1",
                        ),
                        class_="mb-4",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Description",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="description",
                        ),
                        _text_input("description", description, readonly=True),
                        class_="mb-4",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Duration & pacing",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                        ),
                        el(
                            "div",
                            *(
                                el(
                                    "span",
                                    chip,
                                    class_="text-[11px] font-mono text-foreground bg-secondary/60 px-1.5 py-0.5 rounded border border-border/40 mr-1.5",
                                )
                                for chip in pacing_chips
                            ),
                            el(
                                "span",
                                "Managed by the format (FORMAT.md) \u2014 read-only in the web editor.",
                                class_="text-[11px] text-muted-foreground mt-1",
                            ),
                            class_="flex items-center flex-wrap",
                        ),
                        class_="mb-4",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Structure",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                        ),
                        el("div", structure_html, class_="flex items-center flex-wrap"),
                        el(
                            "p",
                            "Read-only \u2014 section order is tied to the prompt template.",
                            class_="text-[11px] text-muted-foreground mt-1",
                        ),
                        class_="mb-4",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Topic categories",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="topic_categories",
                        ),
                        _textarea("topic_categories", ", ".join(profile.topic_categories)),
                        el(
                            "p",
                            "Comma-separated. These categories constrain generated idea angles.",
                            class_="text-[11px] text-muted-foreground mt-1",
                        ),
                        class_="mb-4",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Banned phrases",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="banned_phrases",
                        ),
                        _textarea("banned_phrases", ", ".join(profile.banned_phrases)),
                        el(
                            "p",
                            "Comma-separated. These phrases are prohibited from appearing in generated scripts.",
                            class_="text-[11px] text-muted-foreground mt-1",
                        ),
                        class_="mb-4",
                    ),
                    el(
                        "details",
                        el(
                            "summary",
                            "Prompt",
                            class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono cursor-pointer select-none",
                        ),
                        el(
                            "div",
                            "".join(
                                str(
                                    el(
                                        "div",
                                        el(
                                            "span",
                                            label,
                                            class_="text-[11px] font-mono font-semibold uppercase tracking-widest text-muted-foreground mb-1",
                                        ),
                                        el(
                                            "pre",
                                            prompt,
                                            class_="whitespace-pre-wrap text-[11px] font-mono text-muted-foreground bg-background/60 border border-border/60 rounded-lg p-3 max-h-40 overflow-y-auto",
                                        ),
                                        class_="mb-3",
                                    )
                                )
                                for label, prompt in prompt_blocks
                            ),
                            el(
                                "p",
                                "Prompt templates live in the skill file (SKILL.md) and stay read-only here.",
                                class_="text-[11px] text-muted-foreground mt-2",
                            ),
                            class_="mt-3",
                        ),
                        class_="bg-card/40 border border-border/60 rounded-xl p-5",
                    ),
                    ActionButton(
                        "Save",
                        hx_post=f"/topics/{name}/save",
                        hx_target="#save-msg",
                        hx_swap="innerHTML",
                        class_extra="mt-3",
                    ),
                    el("div", id="save-msg", class_="mt-2"),
                    class_="bg-card/40 border border-border/60 rounded-xl p-5 mt-6 space-y-4",
                ),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title=f"Edit {label}", request=request)
        return HTMLContent(html)

    @post("/topics/{name}/save")
    async def save(self, request=None, name: str = "") -> HTMLContent:
        if not _safe_topic_name(name):
            return HTMLContent("<div class='text-destructive p-8'>Topic not found</div>")
        profile = await self.profile_service.get(name)
        if profile is None:
            return HTMLContent("<div class='text-destructive p-8'>Topic not found</div>")
        data = dict(await request.form()) if request else {}
        categories = [p.strip() for p in data.get("topic_categories", "").split(",") if p.strip()]
        banned = [p.strip() for p in data.get("banned_phrases", "").split(",") if p.strip()]
        updates = {}
        if categories or "topic_categories" in data:
            updates["topic_categories"] = categories
        if banned or "banned_phrases" in data:
            updates["banned_phrases"] = banned
        try:
            await self.profile_service.save_overrides(name, updates)
        except ValueError as exc:
            return HTMLContent(
                f'<div class="text-destructive text-xs font-mono p-3 bg-destructive/40 border border-destructive/50 rounded-xl">'
                f"Could not be saved: {escape(str(exc))}</div>"
            )
        from shorts_creator.controllers.api.ideas_api import toast

        return HTMLContent(toast("Topic saved"))
