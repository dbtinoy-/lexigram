import json
from html import escape

from lexigram.ui import el
from markupsafe import Markup


def _scripts_block(pid: str, state) -> str:
    entries = []
    for i, idea in enumerate(state.ideas):
        sj = idea.get("script_json")
        if not sj:
            continue
        try:
            script = json.loads(sj)
        except (json.JSONDecodeError, TypeError):
            continue
        duration = f"{script.get('total_duration', 0):.0f}s"
        word_count = f"{script.get('word_count', 0)} words"
        entries.append((i, idea, script, duration, word_count))
    if not entries:
        return ""
    rows = [
        el(
            "a",
            el(
                "span",
                escape(idea.get("title") or script.get("title") or "Untitled script"),
                class_="text-xs font-semibold text-foreground truncate",
            ),
            el(
                "span",
                f"{word_count} · {duration}",
                class_="font-mono text-[10px] text-muted-foreground ml-auto shrink-0",
            ),
            el(
                "span",
                "Open →",
                class_="text-primary text-[11px] font-mono font-semibold shrink-0 ml-3",
            ),
            href=f"/projects/{pid}/scripts?idea_index={i}",
            hx_get=f"/projects/{pid}/scripts?idea_index={i}",
            hx_target="#main-content",
            hx_push_url=f"/projects/{pid}/scripts?idea_index={i}",
            class_="flex items-center gap-3 py-2.5 px-3 rounded-lg border border-border/60 bg-card/40 hover:bg-secondary/50 hover:border-border/70 transition-all",
        )
        for i, idea, script, duration, word_count in entries
    ]
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "SCRIPTS",
                        class_="text-[11px] font-mono font-semibold text-muted-foreground",
                    ),
                    el(
                        "span",
                        f"({len(entries)})",
                        class_="text-[10px] font-mono text-muted-foreground",
                    ),
                    class_="flex items-center gap-2 mb-3",
                ),
                el("div", *rows, class_="space-y-1.5"),
                class_="rounded-2xl border border-border/60 bg-card/40 p-4",
            )
        )
    )
