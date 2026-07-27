from lexigram.ui import el
from lexigram.web import Controller, HTMLContent, get

from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService
from shorts_creator.ui.icons import folder, play


class SidebarApiController(Controller):
    def __init__(self, projects: ProjectService, runs: RunService | None = None):
        self.projects = projects
        self.runs = runs

    @get("/api/sidebar/recent-projects")
    async def recent_projects(self, request=None) -> HTMLContent:
        projects = await self.projects.list_recent(5)
        if not projects:
            return HTMLContent(
                str(
                    el(
                        "div",
                        el(
                            "span",
                            "No projects yet",
                            class_="px-3 py-2 text-xs text-muted-foreground",
                        ),
                        class_="space-y-0.5",
                    )
                )
            )

        items = [
            el(
                "a",
                folder(),
                el(
                    "span",
                    (getattr(p, "title", "") or "Untitled Project")[:36],
                    class_="truncate side-label",
                ),
                href=f"/projects/{getattr(p, 'id', '')}",
                hx_get=f"/projects/{getattr(p, 'id', '')}",
                hx_target="#main-content",
                hx_push_url=f"/projects/{getattr(p, 'id', '')}",
                class_="side-icon-link group flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground "
                "hover:text-foreground hover:bg-secondary/60 border border-transparent hover:border-border/50 "
                "transition-all duration-150",
            )
            for p in projects
        ]
        return HTMLContent(str(el("div", *items, class_="space-y-0.5")))

    @get("/api/sidebar/recent-runs")
    async def recent_runs(self, request=None) -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        project_id = qp.get("project_id", "")
        if not project_id:
            return HTMLContent(
                str(
                    el(
                        "div",
                        el(
                            "span",
                            "Select a project to see runs",
                            class_="px-3 py-2 text-xs text-muted-foreground",
                        ),
                        class_="space-y-0.5",
                    )
                )
            )
        if self.runs is None:
            return HTMLContent("")
        runs = await self.runs.list_by_project(project_id, limit=5)
        if not runs:
            return HTMLContent(
                str(
                    el(
                        "div",
                        el("span", "No runs yet", class_="px-3 py-2 text-xs text-muted-foreground"),
                        class_="space-y-0.5",
                    )
                )
            )

        items = [
            el(
                "a",
                play(),
                el(
                    "span",
                    (getattr(r, "title", "") or f"Run {getattr(r, 'id', '')}")[:36],
                    class_="truncate side-label",
                ),
                href=f"/projects/{project_id}/runs/{r.id}",
                hx_get=f"/projects/{project_id}/runs/{r.id}",
                hx_target="#main-content",
                hx_push_url=f"/projects/{project_id}/runs/{r.id}",
                class_="side-icon-link group flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground "
                "hover:text-foreground hover:bg-secondary/60 border border-transparent hover:border-border/50 "
                "transition-all duration-150",
            )
            for r in runs
        ]
        items.append(
            el(
                "a",
                "All runs \u2192",
                href=f"/projects/{project_id}/runs",
                hx_get=f"/projects/{project_id}/runs",
                hx_target="#main-content",
                hx_push_url=f"/projects/{project_id}/runs",
                class_="side-text-only px-3 pt-1.5 text-[10px] font-mono text-muted-foreground hover:text-primary transition-colors inline-block",
            )
        )
        return HTMLContent(str(el("div", *items, class_="space-y-0.5")))
