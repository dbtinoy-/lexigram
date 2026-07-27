"""RunHistoryTable — displays run execution audit logs in a clean table."""

import os

from lexigram.ui import el
from markupsafe import Markup

STATUS_COLORS = {
    "completed": "text-success bg-success/40 border-success/50",
    "failed": "text-destructive bg-destructive/40 border-destructive/50",
    "running": "text-primary bg-primary/15 border-primary/30",
    "rendering": "text-primary bg-primary/15 border-primary/30",
    "queued": "text-warning bg-warning/40 border-warning/50",
    "pending": "text-warning bg-warning/40 border-warning/50",
    "script_ready": "text-warning bg-warning/30 border-warning/40",
    "idea_selected": "text-warning bg-warning/30 border-warning/40",
    "draft": "text-muted-foreground bg-card/50 border-border/50",
    "cancelled": "text-muted-foreground bg-card/50 border-border/50",
}


def Badge(text):
    colors = STATUS_COLORS.get(text, "text-muted-foreground bg-card border-border/50")
    label = text.replace("_", " ").title()
    return Markup(
        el(
            "span",
            label,
            class_=f"px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium border {colors} inline-block",
        )
    )


def _short_path(path: str) -> str:
    """Return just filename or last 2 path components, not the full FS path."""
    if not path or path == "\u2014":
        return "\u2014"
    base = os.path.basename(path)
    return base if base else path[-40:]


def RunHistoryTable(runs, expandable=False, projects=None):
    """Render run rows. `projects` maps project_id -> title for the Project column."""
    if not runs:
        return ""

    rows = []
    for i, r in enumerate(runs):
        detail_id = f"run-detail-{i}"

        raw = r.get("created_at", "") or r.get("date", "") or ""
        date_val = raw[:16].replace("T", " ") if raw else "\u2014"

        idea_val = r.get("idea", "\u2014")
        status_val = r.get("status", "unknown")
        output_raw = r.get("output", "")
        output_val = _short_path(output_raw) if output_raw else "\u2014"
        duration = r.get("duration_s")
        duration_str = f"{duration:.1f}s" if isinstance(duration, (int, float)) else "\u2014"
        project_id = r.get("project_id") or ""
        project_val = (projects or {}).get(project_id) if project_id else ""

        row_attrs = {}
        if expandable:
            row_attrs.update(
                {
                    "data_expandable_row": "true",
                    "role": "button",
                    "tabindex": "0",
                    "aria_expanded": "false",
                    "aria_controls": f"{detail_id}-content",
                }
            )

        row = el(
            "tr",
            el(
                "td",
                el(
                    "span",
                    "\u203a",
                    class_="chevron-icon text-muted-foreground transition-transform duration-150 inline-block text-base",
                ),
                class_="py-3 pl-4 pr-1 w-6 cursor-pointer",
            )
            if expandable
            else "",
            el(
                "td",
                date_val,
                class_="py-3 px-4 text-[11px] font-mono text-muted-foreground whitespace-nowrap",
            ),
            el(
                "td",
                el(
                    "a",
                    project_val,
                    href=f"/projects/{project_id}",
                    hx_get=f"/projects/{project_id}",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{project_id}",
                    class_="text-[11px] font-mono text-primary/80 hover:text-primary transition-colors",
                )
                if project_id and project_val
                else "\u2014",
                class_="py-3 px-4",
            ),
            el(
                "td",
                el(
                    "span",
                    (idea_val[:55] + "\u2026") if len(idea_val) > 55 else idea_val,
                    class_="text-foreground text-xs font-medium",
                ),
                class_="py-3 px-4 max-w-xs",
            ),
            el("td", Badge(status_val), class_="py-3 px-4"),
            el("td", duration_str, class_="py-3 px-4 text-xs font-mono text-muted-foreground"),
            el(
                "td",
                el(
                    "span",
                    output_val,
                    class_="text-xs font-mono text-primary/80 truncate max-w-[160px] block",
                    title=output_raw,
                ),
                class_="py-3 px-4 max-w-[200px]",
            ),
            id=f"history-row-{i}",
            **row_attrs,
            class_="border-b border-border/60 hover:bg-secondary/40 transition-colors cursor-pointer",
        )
        rows.append(row)

        if expandable:
            rows.append(el("tr", el("td", colspan="7", class_="p-0"), class_="hidden"))
            meta_keys = [
                ("run_id", "Run ID"),
                ("duration_s", "Duration"),
                ("error", "Error"),
                ("pipeline_ran", "Pipeline"),
                ("steps", "Steps"),
            ]
            meta_lines = []
            run_id_val = r.get("run_id", "") or ""
            if run_id_val:
                meta_lines.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Run: ",
                            class_="text-muted-foreground text-[11px] font-mono font-semibold uppercase tracking-wide",
                        ),
                        el(
                            "a",
                            "View Run \u2192",
                            href=f"/history/{run_id_val}",
                            hx_get=f"/history/{run_id_val}",
                            hx_target="#main-content",
                            hx_push_url=f"/history/{run_id_val}",
                            class_="text-primary text-[11px] font-mono hover:text-primary",
                        ),
                        class_="flex gap-2 items-start",
                    )
                )
            for key, label in meta_keys:
                if key in r and r[key] is not None:
                    val = r[key]
                    if key == "duration_s" and isinstance(val, (int, float)):
                        val = f"{val:.1f}s"
                    meta_lines.append(
                        el(
                            "div",
                            el(
                                "span",
                                f"{label}: ",
                                class_="text-muted-foreground text-[11px] font-mono font-semibold uppercase tracking-wide",
                            ),
                            el("span", str(val), class_="text-primary text-[11px] font-mono"),
                            class_="flex gap-2 items-start",
                        )
                    )
            if output_raw:
                meta_lines.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Output Path: ",
                            class_="text-muted-foreground text-[11px] font-mono font-semibold uppercase tracking-wide",
                        ),
                        el(
                            "span",
                            output_raw,
                            class_="text-muted-foreground text-[11px] font-mono break-all",
                        ),
                        class_="flex gap-2 items-start",
                    )
                )
            rows.append(
                el(
                    "tr",
                    el(
                        "td",
                        el(
                            "div",
                            el("div", *meta_lines, class_="space-y-1.5")
                            if meta_lines
                            else el(
                                "p",
                                "No additional metadata recorded.",
                                class_="text-muted-foreground text-xs italic",
                            ),
                            class_="p-5 bg-background/80 border-b border-border/80",
                        ),
                        colspan="7",
                        class_="p-0",
                    ),
                    class_="hidden",
                    id=f"{detail_id}-content",
                )
            )

    return Markup(
        el(
            "div",
            el(
                "table",
                el(
                    "thead",
                    el(
                        "tr",
                        *([el("th", "", class_="py-3 pl-4 pr-1 w-6")] if expandable else []),
                        el(
                            "th",
                            "Date / Time",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        el(
                            "th",
                            "Project",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        el(
                            "th",
                            "Idea",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        el(
                            "th",
                            "Status",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        el(
                            "th",
                            "Duration",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        el(
                            "th",
                            "Output File",
                            class_="text-left py-3 px-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest font-mono",
                        ),
                        class_="border-b border-border/80 bg-background/40",
                    ),
                ),
                el("tbody", *rows),
                class_="w-full border-collapse",
            ),
            class_="bg-card/90 rounded-xl border border-border/80 overflow-hidden shadow-sm overflow-x-auto",
        )
    )
