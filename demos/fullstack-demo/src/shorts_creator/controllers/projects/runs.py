from html import escape

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.models.run import RunStatus
from shorts_creator.ui.icons import plus


def _dashboard_runs(project, state) -> str:
    pid = project.id
    idea_titles = {d.get("id"): d.get("title", "") for d in state.ideas if d.get("id")}

    active_banner = ""
    if state.active_run:
        active_banner = Markup(
            el(
                "div",
                el(
                    "span",
                    "Render in progress",
                    class_="text-[11px] font-mono font-semibold text-warning bg-warning/30 border border-warning/40 px-2.5 py-1 rounded-full",
                ),
                el(
                    "span",
                    f"Run {state.active_run.id}",
                    class_="text-[11px] font-mono text-muted-foreground",
                ),
                class_="flex items-center gap-2",
            )
        )

    runs_header = el(
        "div",
        el("h2", "RUNS", class_="text-[11px] font-mono font-semibold text-muted-foreground"),
        el(
            "span",
            f"({len(state.recent_runs)})",
            class_="text-[10px] font-mono text-muted-foreground",
        ),
        class_="flex items-center gap-2",
    )

    if state.recent_runs:
        run_rows = [
            el(
                "div",
                el(
                    "a",
                    el("div", *_run_dots(run, bool(state.ideas)), class_="flex items-center gap-1"),
                    el(
                        "span",
                        _run_title(run, idea_titles),
                        class_="text-xs font-semibold text-foreground truncate",
                    ),
                    el(
                        "span",
                        run.status.value if hasattr(run.status, "value") else str(run.status),
                        class_="font-mono text-[10px] px-1.5 py-0.5 rounded bg-secondary/60 border border-border/40 text-foreground",
                    ),
                    el(
                        "span",
                        (run.created_at.strftime("%b %d, %H:%M") if run.created_at else "—"),
                        class_="text-[10px] font-mono text-muted-foreground ml-auto shrink-0",
                    ),
                    el(
                        "span",
                        "Open →",
                        class_="text-primary text-[11px] font-mono font-semibold shrink-0",
                    ),
                    href=f"/projects/{pid}/runs/{run.id}",
                    hx_get=f"/projects/{pid}/runs/{run.id}",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/runs/{run.id}",
                    class_="flex items-center gap-3 py-2.5 px-3 group",
                ),
                *(
                    [
                        el(
                            "p",
                            "Error encountered: ",
                            escape(run.error[:160]),
                            class_="text-[11px] font-mono text-destructive/80 px-3 pb-2",
                        )
                    ]
                    if run.status == RunStatus.FAILED and run.error
                    else []
                ),
                class_="w-full rounded-lg border border-border/60 bg-card/40 hover:border-border/70 transition-all",
            )
            for run in state.recent_runs[:10]
        ]
        runs_section = el(
            "div",
            runs_header,
            el("div", *run_rows, class_="space-y-1.5"),
            class_="mt-4",
        )
    else:
        runs_section = Markup(
            el(
                "div",
                runs_header,
                el(
                    "div",
                    el("h3", "No runs yet", class_="text-sm font-semibold text-foreground mb-1"),
                    el(
                        "p",
                        "Create a run to start working on this project.",
                        class_="text-xs text-muted-foreground mb-4",
                    ),
                    el(
                        "a",
                        plus(),
                        el("span", "New Run", class_="ml-1.5 font-semibold"),
                        href=f"/projects/{pid}/scripts",
                        hx_get=f"/projects/{pid}/scripts",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{pid}/scripts",
                        class_="inline-flex items-center text-xs bg-secondary hover:bg-secondary/80 border border-border/60 "
                        "text-foreground px-4 py-2 rounded-lg font-semibold transition-all",
                    ),
                    class_="text-center py-10 px-6",
                ),
                class_="rounded-2xl border border-dashed border-border mt-3",
            )
        )

    body = el(
        "div",
        active_banner,
        runs_section,
        class_="w-full",
    )

    if state.active_run:
        body = el(
            "div",
            body,
            hx_get=f"/projects/{pid}",
            hx_trigger="every 20s",
            hx_target="this",
            hx_swap="outerHTML",
            class_="w-full",
        )

    return Markup(str(body))


def _run_title(run, idea_titles) -> str:
    """Run display title: the selected idea's title when the run is linked to
    one (runs otherwise carry generic names like \"Render Run\")."""
    if run.selected_idea_id and idea_titles.get(run.selected_idea_id):
        return idea_titles[run.selected_idea_id]
    return run.title or f"Run {run.id}"


def _run_dots(run, has_ideas) -> list:
    status = run.status
    done_ideas = has_ideas
    done_script = status in (
        RunStatus.SCRIPT_READY,
        RunStatus.QUEUED,
        RunStatus.RENDERING,
        RunStatus.COMPLETED,
    )
    done_render = status == RunStatus.COMPLETED
    return [
        el("span", class_=f"w-1.5 h-1.5 rounded-full {'bg-success/80' if done else 'bg-secondary'}")
        for done in (done_ideas, done_script, done_render)
    ]
