from html import escape

from lexigram.ui import el
from markupsafe import Markup


def _ideas_strip(pid: str, state) -> str:
    ideas = state.ideas[:3]
    if not ideas:
        return ""
    cards = [
        el(
            "a",
            el(
                "h3",
                escape(idea.get("title", "Untitled idea")),
                class_="text-sm font-semibold text-foreground leading-snug",
            ),
            el(
                "p",
                escape((idea.get("core_message") or "")[:160]),
                class_="text-xs text-muted-foreground mt-1 line-clamp-2",
            ),
            el("span", "Make script →", class_="text-primary text-[11px] font-mono font-semibold"),
            href=f"/projects/{pid}/scripts?idea_index={i}",
            hx_get=f"/projects/{pid}/scripts?idea_index={i}",
            hx_target="#main-content",
            hx_push_url=f"/projects/{pid}/scripts?idea_index={i}",
            class_="block rounded-xl border border-border/60 bg-background/50 px-4 py-3 hover:border-border/70 hover:bg-card/50 transition-all space-y-1.5",
        )
        for i, idea in enumerate(ideas)
    ]
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "TOP IDEAS",
                        class_="text-[11px] font-mono font-semibold text-muted-foreground",
                    ),
                    el(
                        "a",
                        f"All {len(state.ideas)} →",
                        href=f"/projects/{pid}/scripts",
                        hx_get=f"/projects/{pid}/scripts",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{pid}/scripts",
                        class_="text-[11px] font-mono text-primary hover:text-primary",
                    ),
                    class_="flex items-center justify-between mb-3",
                ),
                el("div", *cards, class_="grid grid-cols-1 sm:grid-cols-2 gap-2"),
                class_="rounded-2xl border border-border/60 bg-card/40 p-4",
            )
        )
    )
