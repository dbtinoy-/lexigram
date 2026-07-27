import os
from typing import Any

from lexigram.ui import el, raw, render_to_string
from lexigram.web import Controller, HTMLContent, get
from starlette.responses import RedirectResponse

from shorts_creator.models.run import Run
from shorts_creator.services.history_service import HistoryService
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.project_state import ProjectStateService
from shorts_creator.services.run_service import RunService
from shorts_creator.ui.components.run_history import RunHistoryTable
from shorts_creator.ui.icons import clock, lightbulb, video_icon, zap
from shorts_creator.ui.shell import AppLayout

STATUS_FILTERS = ["all", "completed", "failed", "running", "pending", "cancelled"]

STATUS_DOT = {
    "completed": "bg-success",
    "failed": "bg-destructive",
    "running": "bg-primary animate-pulse",
    "pending": "bg-warning",
    "cancelled": "bg-muted-foreground",
}


class HistoryController(Controller):
    def __init__(
        self,
        history: HistoryService,
        runs: RunService,
        projects: ProjectService,
        ideas: IdeaService,
    ):
        self.layout = AppLayout()
        self.history = history
        self.runs = runs
        self.projects = projects
        self.ideas = ideas
        self.state = ProjectStateService(projects, runs)

    @get("/history")
    async def list_history(self, request=None) -> HTMLContent:
        return await self._render_history(request, run_id=None)

    @get("/history/{run_id}")
    async def run_detail(self, request=None, run_id: str = "") -> HTMLContent:
        run = await self.history.get_run(run_id)
        if run:
            db_run = await self.runs.get(run_id)
            if db_run:
                project = await self.projects.get(db_run.project_id)
                if project:
                    return RedirectResponse(
                        url=f"/projects/{project.id}/runs/{run_id}", status_code=302
                    )
        return await self._render_history(request, run_id=run_id)

    async def _render_history(self, request, run_id: str | None = None) -> HTMLContent:
        if run_id:
            run = await self.history.get_run(run_id)
            if run:
                return await self._render_run_detail(request, run)
        runs = await self.history.get_recent(100)
        status_filter = (
            getattr(request, "query_params", {}).get("status", "all") if request else "all"
        )

        db_runs = await self.runs.list_recent(100)
        db_by_id = {r.id: r for r in db_runs}
        seen = set()
        merged: list[tuple[str, dict[str, Any] | None, Run | None]] = []
        for r in runs:
            rid = r.get("run_id", "")
            dr = db_by_id.get(rid)
            if dr is not None:
                seen.add(dr.id)
            merged.append((rid, r, dr))
        for dr in db_runs:
            if dr.id in seen:
                continue
            merged.append((dr.id, None, dr))

        rows = []
        proj_ids = set()
        for rid, snap, dr in merged:
            if snap is not None:
                row = {
                    "run_id": rid,
                    "idea": snap.get("idea") or (dr.title if dr else ""),
                    "status": snap.get("status", "unknown"),
                    "created_at": snap.get("created_at") or snap.get("date") or "",
                    "output": snap.get("output") or "",
                    "duration_s": snap.get("duration_s"),
                    "project_id": dr.project_id if dr else None,
                }
            else:
                if dr is None:
                    continue
                row = {
                    "run_id": rid,
                    "idea": dr.title or "",
                    "status": dr.status.value if hasattr(dr.status, "value") else str(dr.status),
                    "created_at": str(dr.created_at or ""),
                    "output": dr.output_path or "",
                    "duration_s": dr.duration_s,
                    "project_id": dr.project_id,
                }
            if row["project_id"]:
                proj_ids.add(row["project_id"])
            rows.append(row)

        proj_titles = {}
        for pid in proj_ids:
            project = await self.projects.get(pid)
            proj_titles[pid] = project.title if project else pid

        rows.sort(key=lambda r: r["created_at"] or "", reverse=True)
        filtered = (
            [r for r in rows if r.get("status") == status_filter]
            if status_filter != "all"
            else rows
        )
        completed = sum(1 for r in rows if r.get("status") == "completed")

        # Compute status counts for the filter pills
        counts: dict[str, int] = {}
        for r in rows:
            s = r.get("status", "unknown")
            counts[s] = counts.get(s, 0) + 1

        project_list = await self.projects.list_recent(50)
        states = await self.state.for_projects(project_list)
        ideas_count = sum(s.stats["ideas"] for s in states.values())

        stats = el(
            "div",
            _StatTile(
                "Ideas",
                str(ideas_count) if ideas_count else "\u2014",
                lightbulb,
                "text-primary",
                href="/projects",
            ),
            _StatTile(
                "Completed Renders", str(completed), video_icon, "text-primary", href="/projects"
            ),
            _StatTile("Total Runs", str(len(rows)), clock, "text-success", href="/history"),
            _StatTile(
                "Success Rate",
                f"{int((completed / len(rows)) * 100)}%" if rows else "\u2014",
                zap,
                "text-warning",
                href="/history",
            ),
            class_="grid grid-cols-2 xl:grid-cols-4 gap-4 py-5 border-b border-border/80 mb-5",
        )

        empty_msg = (
            f"No runs with status '{status_filter}' found."
            if status_filter != "all"
            else "No pipeline runs recorded yet."
        )

        if filtered:
            count_line = el(
                "span",
                f"{len(filtered)} of {len(rows)} total runs",
                class_="text-muted-foreground text-xs font-mono",
            )
            body = el(
                "div",
                el(
                    "div",
                    count_line,
                    class_="mb-4 flex items-center justify-between border-b border-border/40 px-0 pb-3",
                ),
                stats,
                el(
                    "div",
                    *(
                        _FilterPill(s, status_filter, counts.get(s, 0) if s != "all" else len(runs))
                        for s in STATUS_FILTERS
                    ),
                    class_="flex flex-wrap gap-1.5 mb-4",
                ),
                RunHistoryTable(filtered, expandable=True, projects=proj_titles),
            )
        else:
            body = el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        clock(),
                        class_="w-12 h-12 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-success mx-auto mb-3",
                    ),
                    el(
                        "h3",
                        "No Matching Runs",
                        class_="text-sm font-semibold text-foreground mb-1",
                    ),
                    el(
                        "p",
                        empty_msg,
                        class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
                    ),
                    class_="text-center py-20 px-6 rounded-2xl border border-dashed border-border w-full",
                ),
            )

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h1",
                        "Run History Logs",
                        class_="text-2xl font-bold text-foreground tracking-tight",
                    ),
                    el(
                        "p",
                        "Execution audit trail — all pipeline runs, statuses, durations, and output files",
                        class_="text-muted-foreground text-xs mt-1 font-mono",
                    ),
                    class_="pb-4 border-b border-border/80",
                ),
                body,
                raw('<script src="/static/js/history-table.js"></script>'),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title="History", request=request)
        return HTMLContent(html)

    async def _render_run_detail(self, request, run: dict) -> HTMLContent:
        idea = run.get("idea", "Untitled")
        status = run.get("status", "unknown")
        output_path = run.get("output", "")
        created = (run.get("created_at", "") or "")[:19].replace("T", " ")
        run_id = run.get("run_id", "")
        status_color = STATUS_DOT.get(status, "bg-muted-foreground")

        project = None
        if run_id:
            db_run = await self.runs.get(run_id)
            if db_run:
                project = await self.projects.get(db_run.project_id)

        details = []
        for key, label in [
            ("run_id", "Run ID"),
            ("status", "Status"),
            ("duration_s", "Duration"),
            ("error", "Error"),
        ]:
            val = run.get(key)
            if val is not None:
                if key == "duration_s" and isinstance(val, (int, float)):
                    val = f"{val:.1f}s"
                details.append(
                    el(
                        "div",
                        el(
                            "span",
                            f"{label}: ",
                            class_="text-muted-foreground text-xs font-mono font-semibold uppercase tracking-wide",
                        ),
                        el("span", str(val), class_="text-primary text-xs font-mono"),
                        class_="flex gap-2 items-baseline",
                    )
                )

        if output_path:
            details.append(
                el(
                    "div",
                    el(
                        "span",
                        "Output: ",
                        class_="text-muted-foreground text-xs font-mono font-semibold uppercase tracking-wide",
                    ),
                    el(
                        "span",
                        output_path,
                        class_="text-muted-foreground text-xs font-mono break-all",
                    ),
                    class_="flex gap-2 items-baseline",
                )
            )

        body = el(
            "div",
            el(
                "div",
                el("span", created, class_="text-muted-foreground text-xs font-mono"),
                class_="mb-2",
            ),
            el(
                "div",
                el("span", f"{idea}", class_="text-2xl font-bold text-foreground tracking-tight"),
                el("span", class_=f"inline-block w-2 h-2 rounded-full {status_color} ml-2"),
                el(
                    "a",
                    "\u2190 Back",
                    href="/history",
                    hx_get="/history",
                    hx_target="#main-content",
                    hx_push_url="/history",
                    class_="ml-4 text-xs text-primary hover:text-primary",
                ),
                (
                    el(
                        "a",
                        f"View in Project: {project.title} \u2192",
                        href=f"/projects/{project.id}/runs/{run_id}",
                        hx_get=f"/projects/{project.id}/runs/{run_id}",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{project.id}/runs/{run_id}",
                        class_="ml-4 text-xs text-primary hover:text-primary",
                    )
                    if project
                    else ""
                ),
                class_="flex items-center gap-1 pb-3 border-b border-border/80 mb-4",
            ),
            el(
                "div",
                *details,
                class_="space-y-1.5 mb-6 bg-card/60 rounded-lg border border-border/60 p-4",
            ),
            class_="w-full",
        )

        if output_path and os.path.exists(output_path):
            body.children.append(
                el(
                    "video",
                    el("source", src=f"/api/videos/download/{run_id}", type="video/mp4"),
                    controls="",
                    class_="w-full max-w-sm rounded-lg border border-border/80",
                )
            )

        content = render_to_string(el("div", body, class_="w-full space-y-6"))
        html = self.layout.render(content=content, title=idea, request=request)
        return HTMLContent(html)


def _StatTile(label, value, icon_fn, color, href=None):
    inner = el(
        "div",
        el("div", icon_fn(), class_=f"{color} mb-1.5"),
        el("div", value, class_="text-xl font-bold text-foreground font-mono tracking-tight"),
        el(
            "div",
            label,
            class_="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mt-0.5",
        ),
    )
    if href:
        return raw(
            el(
                "a",
                inner,
                href=href,
                hx_get=href,
                hx_target="#main-content",
                hx_push_url=href,
                class_="block hover:opacity-80 transition-opacity",
            )
        )
    return raw(inner)


def _FilterPill(value: str, current: str, count: int = 0):
    active = value == current
    href = "/history" if value == "all" else f"/history?status={value}"
    dot_color = STATUS_DOT.get(value, "bg-muted-foreground") if value != "all" else ""
    return raw(
        el(
            "a",
            *(
                [el("span", class_=f"inline-block w-1.5 h-1.5 rounded-full {dot_color} mr-1.5")]
                if dot_color
                else []
            ),
            value.title(),
            el("span", str(count), class_="ml-1.5 text-[10px] font-mono font-bold")
            if count
            else "",
            href=href,
            hx_get=href,
            hx_target="#main-content",
            hx_push_url=href,
            class_="px-3 py-1.5 rounded-full text-xs font-mono font-medium border transition-all duration-150 inline-flex items-center "
            + (
                "bg-primary text-primary border-primary/60 shadow-sm"
                if active
                else "text-muted-foreground border-border bg-card hover:text-foreground hover:border-border"
            ),
        )
    )
