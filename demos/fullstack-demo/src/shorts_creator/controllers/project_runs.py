from __future__ import annotations

import json

from lexigram.ui import el, raw, render_to_string
from lexigram.web import Controller, HTMLContent, get, html_response
from markupsafe import Markup

from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.project_state import parse_idea_json
from shorts_creator.services.run_service import RunService
from shorts_creator.ui.components.pipeline_tracker import PipelineTracker
from shorts_creator.ui.components.project_tabs import project_header, project_top_tabs
from shorts_creator.ui.components.run_history import RunHistoryTable
from shorts_creator.ui.icons import (
    check,
    chevron_right,
    file_text,
    lightbulb,
    play,
    video_icon,
    zap,
)
from shorts_creator.ui.shell import AppLayout


class ProjectRunsController(Controller):
    def __init__(self, projects: ProjectService, runs: RunService):
        self.layout = AppLayout()
        self.projects = projects
        self.runs = runs

    @get("/projects/{pid}/runs")
    async def run_list(self, request=None, pid: str = "") -> HTMLContent:
        project = await self.projects.get(pid)
        if not project:
            return html_response("Project not found", status_code=404)
        runs = await self.runs.list_by_project(pid, limit=50)
        rows = [
            {
                "run_id": r.id,
                "idea": r.title or f"Run {r.id}",
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "created_at": str(r.created_at or ""),
                "output": r.output_path or "",
                "duration_s": r.duration_s,
                "project_id": r.project_id,
            }
            for r in runs
        ]
        body = self.layout.render(
            content=_runs_list(project, rows),
            title="Runs",
            request=request,
        )
        return HTMLContent(body)

    @get("/projects/{pid}/runs/{rid}")
    async def run_detail(self, request=None, pid: str = "", rid: str = "") -> HTMLContent:
        project = await self.projects.get(pid)
        if not project:
            return html_response("Project not found", status_code=404)
        run = await self.runs.get(rid)
        if not run or run.project_id != pid:
            return html_response("Run not found", status_code=404)

        qp = getattr(request, "query_params", {}) if request else {}
        if qp.get("partial") == "1":
            return HTMLContent(_run_panel(project, run))
        body = self.layout.render(
            content=_run_dashboard(project, run),
            title=f"{run.title or f'Run {run.id}'}",
            request=request,
        )
        return HTMLContent(body)


def _run_dashboard(project, run) -> str:
    """Full-page run dashboard: back link, run identity, and the shared
    pipeline tracker above the run-specific action sections."""
    pid = project.id
    status = run.status.value if hasattr(run.status, "value") else str(run.status)
    return render_to_string(
        el(
            "div",
            el(
                "div",
                el(
                    "div",
                    el(
                        "a",
                        "← Project",
                        href=f"/projects/{pid}",
                        hx_get=f"/projects/{pid}",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{pid}",
                        class_="text-[11px] font-mono text-primary hover:text-primary transition-colors inline-block",
                    ),
                    el(
                        "a",
                        "History →",
                        href=f"/history/{run.id}",
                        hx_get=f"/history/{run.id}",
                        hx_target="#main-content",
                        hx_push_url=f"/history/{run.id}",
                        class_="text-[11px] font-mono text-muted-foreground hover:text-primary transition-colors inline-block",
                    ),
                    class_="flex items-center justify-between mb-3",
                ),
                el(
                    "div",
                    el(
                        "h1",
                        run.title or f"Run {run.id}",
                        class_="text-2xl font-bold text-foreground tracking-tight",
                    ),
                    el(
                        "span",
                        status.replace("_", " ").title(),
                        class_="text-[11px] font-mono px-2 py-0.5 rounded-full border border-border/50 bg-secondary/60 text-foreground ml-3",
                    ),
                    class_="flex items-center gap-2",
                ),
                el(
                    "p",
                    f"{project.title or 'Untitled Project'} · created "
                    + (run.created_at.strftime("%b %d, %H:%M") if run.created_at else "—"),
                    class_="text-xs font-mono text-muted-foreground mt-1",
                ),
                class_="pb-5 border-b border-border/80 mb-6",
            ),
            Markup(_run_panel(project, run)),
            class_="w-full space-y-6",
        )
    )


# ─── Data helpers ───────────────────────────────────────────────────────────


def _runs_list(project, rows) -> str:
    """Full-page project runs list: shared project header/tabs above the same
    RunHistoryTable rows the history page renders."""
    pid = project.id
    title = project.title or "Untitled Project"

    if rows:
        body = el(
            "div",
            el(
                "div",
                el(
                    "span",
                    "All Runs",
                    class_="text-sm font-bold uppercase tracking-wider text-muted-foreground font-mono",
                ),
                el(
                    "span",
                    f"{len(rows)} run{'s' if len(rows) != 1 else ''}",
                    class_="text-muted-foreground text-xs font-mono",
                ),
                class_="mb-4 flex items-center justify-between border-b border-border/40 pb-3",
            ),
            RunHistoryTable(rows, expandable=True, projects={pid: title}),
        )
    else:
        body = el(
            "div",
            el("h3", "No runs yet", class_="text-sm font-semibold text-foreground mb-1"),
            el(
                "p",
                "Launch a render from the Render Engine and it will appear here.",
                class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
            ),
            class_="text-center py-12 px-6 rounded-2xl border border-dashed border-border w-full bg-card/30",
        )

    return render_to_string(
        el(
            "div",
            project_header(project),
            project_top_tabs(pid),
            body,
            raw('<script src="/static/js/history-table.js"></script>'),
            class_="w-full space-y-6",
        )
    )


def _pipeline_status(status, ideas, script, run, pid: str = "") -> list[dict]:
    done_ideas = ideas is not None
    done_script = script is not None
    done_render = status in ("completed",)
    active_render = status in ("script_ready", "queued", "rendering", "failed")
    return [
        {
            "key": "ideas",
            "label": "Ideas",
            "done": done_ideas,
            "active": not done_ideas,
            "preview": f"{len(ideas)} idea{'s' if len(ideas) != 1 else ''}" if ideas else "",
            "summary": f"Best: {ideas[0].get('title', '')[:55]}" if ideas else "",
            "icon": lightbulb,
            "href": f"/projects/{pid}/scripts",
            "action_label": "Generate Ideas" if not done_ideas else "View Ideas",
        },
        {
            "key": "script",
            "label": "Script",
            "done": done_script,
            "active": done_ideas and not done_script,
            "preview": f"{script.get('total_duration', 0):.0f}s · {script.get('word_count', 0)} words"
            if script
            else "",
            "summary": script.get("title", "")[:55] if script else "",
            "icon": file_text,
            "href": f"/projects/{pid}/scripts",
            "action_label": "Write Script" if done_ideas else "Waiting for Ideas",
        },
        {
            "key": "render",
            "label": "Render",
            "done": done_render,
            "active": active_render,
            "preview": f"{run.duration_s:.1f}s video" if done_render and run.duration_s else "",
            "summary": run.output_path.split("/")[-1] if run.output_path else "",
            "icon": video_icon,
            "href": f"/projects/{pid}/render",
            "action_label": "Start Render" if done_script else "Waiting for Script",
        },
    ]


# ─── Run expanded panel ──────────────────────────────────────────────────────


def _run_panel(project, run) -> str:
    """Renders the lazy-loaded panel inside the run accordion."""
    pid = project.id
    ideas = parse_idea_json(project.idea_json) or None
    script = None
    if ideas:
        for idea in ideas:
            sj = idea.get("script_json")
            if sj:
                try:
                    script = json.loads(sj)
                except (json.JSONDecodeError, TypeError):
                    pass
                if script:
                    break
    status = run.status.value if hasattr(run.status, "value") else str(run.status)

    stages = _pipeline_status(status, ideas, script, run, pid=pid)

    sections = [
        _ideas_section(stages[0], ideas, pid),
        _script_section(stages[1], script, pid),
        _render_section(stages[2], run, pid, status),
    ]

    created = run.created_at.strftime("%b %d, %H:%M") if run.created_at else ""
    updated = run.updated_at.strftime("%b %d, %H:%M") if run.updated_at else ""
    duration_str = f"{run.duration_s:.1f}s" if run.duration_s else "—"

    # Meta bar
    meta_bar = el(
        "div",
        el("span", f"Created {created}", class_="text-[10px] font-mono text-muted-foreground")
        if created
        else "",
        el("span", " · ", class_="text-muted-foreground mx-1") if created and updated else "",
        el("span", f"Updated {updated}", class_="text-[10px] font-mono text-muted-foreground")
        if updated
        else "",
        *(
            [
                el("span", " · ", class_="text-muted-foreground mx-1"),
                el(
                    "span",
                    f"Duration: {duration_str}",
                    class_="text-[10px] font-mono text-muted-foreground",
                ),
            ]
            if run.duration_s
            else []
        ),
        class_="flex items-center flex-wrap px-4 pt-3 pb-0",
    )

    # Horizontal pipeline tracker
    pipeline_bar = PipelineTracker(
        current="script",
        project_id=pid,
        density="full",
        stage_state=[
            {"done": s["done"], "active": s["active"], "preview": s["preview"]} for s in stages
        ],
    )

    return render_to_string(
        el(
            "div",
            meta_bar,
            pipeline_bar,
            el("div", class_="h-px bg-secondary/50 mx-4"),
            el("div", *sections, class_="divide-y divide-secondary/40 px-4"),
            class_="w-full bg-background/20",
        )
    )


def _ideas_section(stage: dict, ideas, pid: str) -> str:
    if not ideas:
        return _empty_section(
            stage=stage,
            msg="Generate video ideas from your project topic focus.",
            pid=pid,
            enabled=True,
        )

    top = ideas[0]
    total = len(ideas)
    avg_score = sum(i.get("quotability_score", 0) for i in ideas) / total if total else 0

    return Markup(
        el(
            "div",
            el(
                "div",
                _dot_check(True),
                el(
                    "span",
                    "Ideas Generated",
                    class_="text-[10px] font-bold font-mono uppercase tracking-widest text-success",
                ),
                el(
                    "span",
                    f"{total} ideas",
                    class_="text-[10px] font-mono text-muted-foreground ml-1.5",
                ),
                class_="flex items-center gap-2 mb-2.5",
            ),
            el(
                "div",
                el(
                    "span", top.get("title", "Untitled"), class_="text-sm font-bold text-foreground"
                ),
                class_="mb-1",
            ),
            el(
                "p",
                top.get("core_message", ""),
                class_="text-xs text-muted-foreground leading-relaxed mb-2 max-w-xl",
            ),
            el(
                "div",
                el(
                    "span",
                    f"Avg score: {avg_score:.1f}",
                    class_="text-[10px] font-mono text-primary bg-primary/15 border border-primary/30 px-1.5 py-0.5 rounded mr-2",
                ),
                el(
                    "span",
                    f"Audience: {top.get('target_audience', '')[:45]}",
                    class_="text-[10px] font-mono text-muted-foreground",
                ),
                class_="flex items-center flex-wrap mb-3",
            ),
            el(
                "a",
                el("span", "View All Ideas", class_="text-[11px] font-semibold font-mono"),
                chevron_right(),
                href=f"/projects/{pid}/scripts",
                hx_get=f"/projects/{pid}/scripts",
                hx_target="#main-content",
                hx_push_url=f"/projects/{pid}/scripts",
                class_="inline-flex items-center gap-0.5 text-primary hover:text-primary transition-colors",
            ),
            class_="py-4",
        )
    )


def _script_section(stage: dict, script, pid: str) -> str:
    if not script:
        enabled = stage["active"]
        return _empty_section(
            stage=stage, msg="Turn a chosen idea into a full script.", pid=pid, enabled=enabled
        )

    sections_list = script.get("sections", [])
    sections_str = " → ".join(s.get("name", "") for s in sections_list) if sections_list else ""

    return Markup(
        el(
            "div",
            el(
                "div",
                _dot_check(True),
                el(
                    "span",
                    "Script Ready",
                    class_="text-[10px] font-bold font-mono uppercase tracking-widest text-success",
                ),
                class_="flex items-center gap-2 mb-2.5",
            ),
            el(
                "div",
                el(
                    "span",
                    script.get("title", "Untitled"),
                    class_="text-sm font-bold text-foreground",
                ),
                class_="mb-1.5",
            ),
            el(
                "div",
                el(
                    "span",
                    f"{script.get('total_duration', 0):.0f}s",
                    class_="text-[10px] font-mono text-primary bg-primary/15 border border-primary/30 px-1.5 py-0.5 rounded",
                ),
                el(
                    "span",
                    f"{script.get('word_count', 0)} words",
                    class_="text-[10px] font-mono text-muted-foreground ml-2",
                ),
                el(
                    "span",
                    f"{script.get('pacing_wps', 0):.1f} w/s",
                    class_="text-[10px] font-mono text-muted-foreground ml-2",
                ),
                class_="flex items-center flex-wrap gap-1 mb-1.5",
            ),
            el("p", sections_str, class_="text-[10px] font-mono text-muted-foreground mb-3")
            if sections_str
            else "",
            el(
                "a",
                el("span", "Edit Script", class_="text-[11px] font-semibold font-mono"),
                chevron_right(),
                href=f"/projects/{pid}/scripts",
                hx_get=f"/projects/{pid}/scripts",
                hx_target="#main-content",
                hx_push_url=f"/projects/{pid}/scripts",
                class_="inline-flex items-center gap-0.5 text-primary hover:text-primary transition-colors",
            ),
            class_="py-4",
        )
    )


def _render_section(stage: dict, run, pid: str, status: str) -> str:
    if status == "completed":
        fname = run.output_path.split("/")[-1] if run.output_path else ""
        dur = f"{run.duration_s:.1f}s" if run.duration_s else ""
        return Markup(
            el(
                "div",
                el(
                    "div",
                    _dot_check(True),
                    el(
                        "span",
                        "Render Complete",
                        class_="text-[10px] font-bold font-mono uppercase tracking-widest text-success",
                    ),
                    class_="flex items-center gap-2 mb-2.5",
                ),
                el(
                    "div",
                    el("span", fname, class_="text-xs font-mono text-foreground break-all"),
                    *(
                        [
                            el(
                                "span",
                                f"  ·  {dur}",
                                class_="text-[10px] font-mono text-primary ml-2",
                            )
                        ]
                        if dur
                        else []
                    ),
                    class_="flex items-center flex-wrap mb-3",
                ),
                el(
                    "a",
                    play(),
                    el("span", "View Video", class_="ml-1.5 font-semibold"),
                    href=f"/projects/{pid}/render",
                    hx_get=f"/projects/{pid}/render",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/render",
                    class_="inline-flex items-center text-[11px] font-mono font-semibold text-primary hover:text-primary transition-colors",
                ),
                class_="py-4",
            )
        )

    if status == "failed":
        return Markup(
            el(
                "div",
                el(
                    "div",
                    el("div", class_="w-2.5 h-2.5 rounded-full bg-destructive shrink-0"),
                    el(
                        "span",
                        "Render Failed",
                        class_="text-[10px] font-bold font-mono uppercase tracking-widest text-destructive",
                    ),
                    class_="flex items-center gap-2 mb-2",
                ),
                el(
                    "p",
                    run.error or "Unknown error",
                    class_="text-xs text-destructive/70 font-mono mb-3 max-w-xl",
                ),
                el(
                    "a",
                    zap(),
                    el("span", "Retry Render", class_="ml-1.5 font-semibold"),
                    href=f"/projects/{pid}/render",
                    hx_get=f"/projects/{pid}/render",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/render",
                    class_="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold text-destructive-foreground bg-destructive hover:bg-destructive/90 transition-all cursor-pointer",
                ),
                class_="py-4",
            )
        )

    enabled = stage["active"]
    return _empty_section(
        stage=stage, msg="Assemble and export the final video.", pid=pid, enabled=enabled
    )


def _empty_section(stage: dict, msg: str, pid: str, enabled: bool) -> str:
    dot_cls = "bg-primary/60 animate-pulse" if enabled else "bg-secondary"
    label_cls = "text-foreground" if enabled else "text-muted-foreground"
    label = stage["label"]
    action = stage["action_label"]
    href = stage["href"]

    if enabled:
        btn = el(
            "a",
            stage["icon"](),
            el("span", action, class_="ml-1.5 font-semibold"),
            href=href,
            hx_get=href,
            hx_target="#main-content",
            hx_push_url=href,
            class_="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold text-primary-foreground bg-gradient-to-r from-primary to-primary hover:opacity-90 transition-all cursor-pointer",
        )
    else:
        btn = el(
            "span",
            action,
            class_="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-semibold text-muted-foreground bg-secondary/40 cursor-not-allowed",
        )

    return Markup(
        el(
            "div",
            el(
                "div",
                el("div", class_=f"w-2.5 h-2.5 rounded-full {dot_cls} shrink-0"),
                el(
                    "span",
                    label,
                    class_=f"text-[10px] font-bold font-mono uppercase tracking-widest {label_cls}",
                ),
                class_="flex items-center gap-2 mb-1.5",
            ),
            el("p", msg, class_="text-xs text-muted-foreground mb-3"),
            btn,
            class_="py-4",
        )
    )


def _dot_check(done: bool) -> str:
    if done:
        return Markup(
            el(
                "div",
                check(),
                class_="w-4 h-4 rounded-full bg-success/20 border border-success/50 flex items-center justify-center text-success",
            )
        )
    return Markup(el("div", class_="w-2.5 h-2.5 rounded-full bg-secondary shrink-0"))
