from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.models.run import RunStatus
from shorts_creator.ui.components.project_tabs import _card_chips, _created_label
from shorts_creator.ui.icons import folder, plus


def _stat_chip(value: str, label: str) -> str:
    return Markup(
        str(
            el(
                "div",
                el("span", value, class_="text-foreground font-bold font-mono text-sm"),
                el("span", " " + label, class_="text-muted-foreground text-xs font-mono"),
                class_="bg-card/60 border border-border/60 rounded-lg px-3 py-1.5 inline-flex items-baseline gap-0.5",
            )
        )
    )


def _ProjectCard(p, state=None) -> str:
    pid = getattr(p, "id", "")
    title = getattr(p, "title", "Untitled Project")
    topic = (getattr(p, "topic", "") or "").replace("_", " ").title() or "—"
    focus = getattr(p, "focus", "") or ""
    created_str = _created_label(getattr(p, "created_at", None)) or "—"

    # Framework color accent
    fw_colors = {
        "self improvement": "from-primary/20 to-primary/20 border-primary/30",
        "psychology": "from-info/20 to-success/20 border-info/30",
        "stoic": "from-warning/20 to-warning/20 border-warning/30",
    }
    fw_key = topic.lower()
    fw_gradient = fw_colors.get(fw_key, "from-secondary/40 to-card/40 border-border/30")

    fw_badge_cls_map = {
        "self improvement": "bg-primary/60 text-primary border-primary/50",
        "psychology": "bg-info/60 text-info border-info/50",
        "stoic": "bg-warning/60 text-warning border-warning/50",
    }
    fw_badge_cls = fw_badge_cls_map.get(fw_key, "bg-card text-muted-foreground border-border/50")

    return Markup(
        str(
            el(
                "a",
                # Card header with gradient
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "span",
                            topic,
                            class_=f"text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border {fw_badge_cls}",
                        ),
                        class_="flex items-center mb-3",
                    ),
                    el(
                        "h2",
                        title,
                        class_="text-base font-bold text-foreground leading-snug mb-1 truncate",
                    ),
                    el(
                        "p",
                        focus or "No topic focus set",
                        class_=f"text-xs font-mono truncate {'text-muted-foreground' if focus else 'text-muted-foreground italic'}",
                    ),
                    class_=f"bg-gradient-to-br {fw_gradient} border-b border-border/60 px-4 pt-4 pb-3",
                ),
                # Card footer
                el(
                    "div",
                    el(
                        "div",
                        _run_status_pill(state) if state else "",
                        el(
                            "span",
                            created_str,
                            class_="text-muted-foreground text-[10px] font-mono mr-3",
                        ),
                        el(
                            "span",
                            "Open →",
                            class_="text-primary group-hover:text-primary text-[11px] font-mono font-semibold transition-colors",
                        ),
                        class_="flex items-center",
                    ),
                    _card_chips(state) if state else "",
                    class_="flex items-center justify-between px-4 py-3",
                ),
                href=f"/projects/{pid}",
                hx_get=f"/projects/{pid}",
                hx_target="#main-content",
                hx_push_url=f"/projects/{pid}",
                class_="group block border border-border/60 hover:border-border/80 rounded-2xl overflow-hidden bg-card/40 hover:bg-secondary/40 transition-all duration-200 hover:shadow-lg hover:shadow-background/50 hover:-translate-y-0.5",
            )
        )
    )


def _run_status_pill(state) -> str:
    run = state.active_run or (state.recent_runs[0] if state.recent_runs else None)
    if not run:
        return ""
    style_map = {
        RunStatus.COMPLETED: ("Completed", "bg-success/60 text-success border-success/50"),
        RunStatus.FAILED: ("Failed", "bg-destructive/60 text-destructive border-destructive/50"),
        RunStatus.RENDERING: (
            "Rendering",
            "bg-warning/60 text-warning border-warning/50 animate-pulse",
        ),
        RunStatus.QUEUED: ("Queued", "bg-warning/60 text-warning border-warning/50"),
    }
    label, cls = style_map.get(
        run.status, (run.status.value.title(), "bg-card text-muted-foreground border-border/50")
    )
    return Markup(
        str(
            el(
                "span",
                label,
                class_=f"text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border mr-2 {cls}",
            )
        )
    )


def _empty_projects_state() -> str:
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        folder(),
                        class_="w-16 h-16 rounded-2xl bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-5",
                    ),
                    el("h2", "Create Project", class_="text-lg font-bold text-foreground mb-2"),
                    el(
                        "p",
                        "Turn an idea into a video — set your creation profile, then brainstorm ideas, write scripts, and render.",
                        class_="text-muted-foreground text-sm max-w-sm mx-auto leading-relaxed mb-8",
                    ),
                    el(
                        "a",
                        plus(),
                        el("span", "Create Project", class_="ml-2 font-semibold"),
                        href="/projects/new",
                        hx_get="/projects/new",
                        hx_target="#main-content",
                        hx_push_url="/projects/new",
                        class_="inline-flex items-center gap-1 bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-primary-foreground px-6 py-3 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-primary/50",
                    ),
                    class_="text-center py-24 px-6",
                ),
            )
        )
    )
