from datetime import UTC, datetime

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.ui.components.settings_profile import caption_style_label
from shorts_creator.ui.icons import plus


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _created_label(created_at) -> str:
    if not created_at:
        return ""
    dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    days = (datetime.now(UTC) - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    return str(dt)[:10]


def _card_chips(state) -> str:
    s = state.stats
    chips = []
    if s["ideas"]:
        chips.append(
            el(
                "span",
                _plural(s["ideas"], "idea"),
                class_="text-[10px] font-mono text-primary/80 bg-background/60 border border-border px-1.5 py-0.5 rounded",
            )
        )
    if s["scripts"]:
        chips.append(
            el(
                "span",
                _plural(s["scripts"], "script"),
                class_="text-[10px] font-mono text-primary/80 bg-background/60 border border-border px-1.5 py-0.5 rounded",
            )
        )
    if s["videos"]:
        chips.append(
            el(
                "span",
                _plural(s["videos"], "video"),
                class_="text-[10px] font-mono text-success/80 bg-background/60 border border-border px-1.5 py-0.5 rounded",
            )
        )
    if not chips:
        return ""
    return Markup(str(el("div", *chips, class_="flex items-center gap-1.5")))


def project_header(project, state=None) -> str:
    """Project module header: back button, title, and description chips,
    shared by the Overview / Project Videos / Settings pages."""
    title = getattr(project, "title", None) or "Untitled Project"
    topic = (getattr(project, "topic", "") or "").replace("_", " ").title()
    fmt = getattr(project, "format", "") or ""
    fmt_def = formats.get(fmt)
    fmt_badge = fmt_def.label if fmt_def else fmt
    style_badge = ""
    overrides_fn = getattr(project, "_overrides", None)
    if callable(overrides_fn):
        explicit_style = overrides_fn().get("caption_style") or ""
        style_badge = (caption_style_label(fmt_def, explicit_style) or "") if explicit_style else ""
    focus = getattr(project, "focus", "") or ""
    created_str = _created_label(getattr(project, "created_at", None))
    return Markup(
        str(
            el(
                "div",
                el(
                    "a",
                    "← Projects",
                    href="/projects",
                    hx_get="/projects",
                    hx_target="#main-content",
                    hx_push_url="/projects",
                    class_="text-[11px] font-mono text-primary hover:text-primary transition-colors mb-3 inline-block",
                ),
                el(
                    "div",
                    el("h1", title, class_="text-2xl font-bold text-foreground tracking-tight"),
                    class_="flex items-center gap-3",
                ),
                el(
                    "div",
                    el(
                        "span",
                        topic,
                        class_="text-[11px] font-mono text-primary bg-primary/40 border border-primary/30 px-2 py-0.5 rounded-full",
                    ),
                    *(
                        [
                            el(
                                "span",
                                fmt_badge,
                                class_="text-[11px] font-mono text-primary bg-primary/40 border border-primary/30 px-2 py-0.5 rounded-full",
                            )
                        ]
                        if fmt_badge
                        else []
                    ),
                    *(
                        [
                            el(
                                "span",
                                style_badge,
                                class_="text-[11px] font-mono text-muted-foreground bg-secondary/50 border border-border/40 px-2 py-0.5 rounded-full",
                            )
                        ]
                        if style_badge
                        else []
                    ),
                    *(
                        [
                            el("span", "·", class_="text-muted-foreground mx-1"),
                            el("span", focus, class_="text-xs font-mono text-muted-foreground"),
                        ]
                        if focus
                        else []
                    ),
                    *(
                        [
                            el("span", "·", class_="text-muted-foreground mx-1"),
                            el(
                                "span",
                                f"Created {created_str}",
                                class_="text-xs font-mono text-muted-foreground",
                            ),
                        ]
                        if created_str
                        else []
                    ),
                    (_card_chips(state) if state is not None else ""),
                    class_="flex items-center flex-wrap gap-1 mt-2",
                ),
                class_="mb-6 pb-5 border-b border-border/80",
            )
        )
    )


def project_top_tabs(pid: str, active: str = "") -> str:
    """Top-level project module tabs with the Generate Ideas action pinned
    to the far right. Modules live under ``/projects/<id>/...`` sub-paths so
    new modules can be added without touching the project shell."""
    tab_cls = "px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors "
    active_cls = "bg-primary text-primary-foreground border-primary"
    inactive_cls = "text-muted-foreground border-border hover:text-foreground"

    def tab(label, href, key):
        return el(
            "a",
            label,
            href=href,
            hx_get=href,
            hx_target="#main-content",
            hx_push_url=href,
            class_=tab_cls + (active_cls if active == key else inactive_cls),
        )

    return Markup(
        str(
            el(
                "div",
                tab("Overview", f"/projects/{pid}", "overview"),
                tab("Project Videos", f"/projects/{pid}/videos", "videos"),
                tab("Settings", f"/projects/{pid}/settings", "settings"),
                el(
                    "a",
                    plus(),
                    el("span", "Generate Ideas", class_="ml-1.5 font-semibold"),
                    href=f"/projects/{pid}/scripts",
                    hx_get=f"/projects/{pid}/scripts",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/scripts",
                    class_="ml-auto inline-flex items-center bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-primary-foreground text-xs px-4 py-2 rounded-xl font-semibold transition-all shadow-sm shadow-primary/40",
                ),
                class_="flex items-center gap-2 flex-wrap mt-4 mb-5",
            )
        )
    )
