from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.topics import ParsedScript
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.icons import check, copy_icon


def _section_color(name):
    palette = {
        "hook": "var(--primary)",
        "message": "var(--color-info)",
        "metaphor": "var(--chart-1)",
        "conclusion": "var(--color-success)",
        "context": "var(--chart-2)",
        "explanation": "var(--destructive)",
        "application": "var(--chart-3)",
        "reflection": "var(--color-warning)",
    }
    return palette.get(name.lower().strip(), "var(--muted-foreground)")


def TimingBar(sections, total_duration):
    if total_duration <= 0:
        return ""
    bars = []
    for sec in sections:
        pct = max(sec.duration_seconds / total_duration * 100, 1)
        bars.append(
            el(
                "div",
                title=f"{sec.name}: {sec.duration_seconds:.1f}s",
                class_="h-2 rounded-full transition-all duration-300 hover:opacity-80",
                style=f"width: {pct}%; background-color: {_section_color(sec.name)};",
            )
        )
    return Markup(
        str(
            el(
                "div",
                *bars,
                class_="flex gap-1 overflow-hidden rounded-full bg-background p-0.5 border border-border/80 shadow-inner",
                style="height: 12px;",
            )
        )
    )


def _section_body(label, text, secs, raw_name, project_id, idea_index):
    editable = raw_name in ("hook", "message") and bool(project_id)
    if not editable:
        return el("p", text, class_="text-foreground text-sm mt-2 leading-relaxed copy-section")
    kid = f"sec-{raw_name}-{idea_index}"
    return Markup(
        str(
            el(
                "div",
                el(
                    "textarea",
                    text,
                    id=kid,
                    class_="w-full text-foreground text-sm mt-2 leading-relaxed bg-background/80 border border-border/60 rounded-lg p-2 focus:outline-none focus:border-primary/60 font-sans resize-y min-h-[60px]",
                    rows=3,
                ),
                id=f"sec-wrapper-{raw_name}-{idea_index}",
            )
        )
    )


def ScriptViewer(script: ParsedScript, project_id: str = "", idea_index: int = 0) -> str:
    section_labels = {
        "hook": "Hook",
        "message": "Message",
        "metaphor": "Metaphor",
        "conclusion": "Conclusion",
        "context": "Context",
        "explanation": "Explanation",
        "application": "Application",
        "reflection": "Reflection",
    }
    sections = [
        (section_labels.get(s.name, s.name.title()), s.text, s.duration_seconds, s.name)
        for s in script.sections
    ]

    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "span",
                            f"⏱️ {script.total_duration:.1f}s",
                            class_="text-xs font-mono font-medium text-primary bg-primary/15 px-2 py-0.5 rounded border border-primary/30",
                        ),
                        el(
                            "span",
                            f"📝 {script.word_count} words",
                            class_="text-xs font-mono text-foreground bg-secondary px-2 py-0.5 rounded border border-border/50",
                        ),
                        el(
                            "span",
                            f"⚡ {script.pacing_wps} w/s",
                            class_="text-xs font-mono text-muted-foreground bg-secondary px-2 py-0.5 rounded border border-border/50",
                        ),
                        class_="flex flex-wrap gap-2 items-center",
                    ),
                    (
                        script.emotional_arc
                        and el(
                            "div",
                            el(
                                "span",
                                "Emotional Arc: ",
                                class_="text-muted-foreground text-xs font-mono uppercase tracking-wider",
                            ),
                            el(
                                "span",
                                " → ".join(script.emotional_arc),
                                class_="text-primary text-xs font-medium",
                            ),
                            class_="mt-2.5 px-3 py-1.5 rounded-lg bg-card/60 border border-border/60 inline-block",
                        )
                    ),
                    class_="mb-5 pb-4 border-b border-border/80",
                ),
                *(
                    el(
                        "div",
                        el(
                            "div",
                            el(
                                "span",
                                label,
                                class_="font-bold text-xs uppercase tracking-wider font-mono",
                                style=f"color: {_section_color(raw_name)};",
                            ),
                            el(
                                "span",
                                f"[{secs:.1f}s]",
                                class_="text-muted-foreground text-xs font-mono ml-2",
                            ),
                            el(
                                "button",
                                copy_icon(),
                                onclick=f"copySection('{label}')",
                                title=f"Copy {label}",
                                class_="ml-auto text-muted-foreground hover:text-foreground transition-colors p-1 hover:bg-secondary rounded cursor-pointer",
                            ),
                            (
                                ActionButton(
                                    "",
                                    icon=check(),
                                    title=f"Save {label}",
                                    hx_post="/api/scripts/section/update",
                                    hx_target=f"#sec-wrapper-{raw_name}-{idea_index}",
                                    hx_swap="outerHTML",
                                    hx_vals=f'js:{{"project_id":"{project_id}","idea_index":{idea_index},"section_name":"{raw_name}","text":document.getElementById("sec-{raw_name}-{idea_index}").value}}',
                                    class_extra="px-2",
                                )
                                if raw_name in ("hook", "message") and project_id
                                else ""
                            ),
                            class_="flex items-center pb-1.5 border-b border-border/40",
                        ),
                        _section_body(label, text, secs, raw_name, project_id, idea_index),
                    )
                    for label, text, secs, raw_name in sections
                ),
                class_="space-y-3",
            )
        )
    )


def seo_field_wrapper(
    key: str, label: str, value: str, project_id: str = "", idea_id: str = ""
) -> str:
    editable = bool(project_id and idea_id)
    kid = f"seo-{key}-{idea_id}"
    save_btn = ""
    if editable:
        save_btn = ActionButton(
            "",
            icon=check(),
            title="Save",
            hx_post="/api/scripts/seo/update",
            hx_target=f"#seo-wrapper-{key}-{idea_id}",
            hx_swap="outerHTML",
            hx_vals=(
                f'js:{{"project_id":"{project_id}","idea_id":"{idea_id}","key":"{key}",'
                f'"text":document.getElementById("{kid}").value}}'
            ),
            class_extra="px-2",
        )
    label_row = el(
        "div",
        el("span", label, class_="text-foreground text-xs font-medium"),
        el(
            "span",
            f"{len(value)} chars",
            class_="text-muted-foreground text-[11px] font-mono ml-auto bg-background px-2 py-0.5 rounded border border-border",
        ),
        save_btn,
        class_="flex items-center gap-2 pb-1",
    )
    if not editable:
        body = el(
            "p",
            value,
            class_="text-foreground text-xs mt-1.5 whitespace-pre-wrap font-mono leading-relaxed copy-section",
        )
    else:
        body = el(
            "textarea",
            value,
            id=kid,
            class_="w-full text-foreground text-xs mt-1.5 whitespace-pre-wrap font-mono bg-background/80 border border-border/60 rounded-lg p-2 focus:outline-none focus:border-primary/60 resize-y leading-relaxed",
            rows=(2 if key == "youtube_title" else 3 if key == "youtube_tags" else 5),
        )
    return Markup(
        str(
            el(
                "div",
                label_row,
                body,
                id=(f"seo-wrapper-{key}-{idea_id}" if editable else None),
                class_="mb-4",
            )
        )
    )


def SeoPanel(
    metadata: dict | None, timing_bar: str = "", project_id: str = "", idea_id: str = ""
) -> str:
    if not metadata:
        return Markup(
            str(
                el(
                    "div",
                    el(
                        "p",
                        "No SEO metadata generated yet.",
                        class_="text-muted-foreground text-sm italic",
                    ),
                    class_="p-4 bg-card/40 rounded-xl border border-border/60 text-center",
                )
            )
        )
    heading = el(
        "h2",
        "SEO & Social Distribution",
        class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono",
    )
    items = [
        ("youtube_title", "YouTube Title", metadata.get("youtube_title", "")),
        ("youtube_description", "YouTube Description", metadata.get("youtube_description", "")),
        ("youtube_tags", "YouTube Tags", metadata.get("youtube_tags", "")),
        ("facebook_caption", "Facebook Caption", metadata.get("facebook_caption", "")),
    ]
    return Markup(
        str(
            el(
                "div",
                el("div", heading, class_="mb-3"),
                *(
                    seo_field_wrapper(key, label, value, project_id, idea_id)
                    for key, label, value in items
                ),
            )
        )
    )
