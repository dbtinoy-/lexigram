import json
import os

from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get, html_response
from markupsafe import Markup

from shorts_creator.controllers.api.render_api import probe_duration
from shorts_creator.services.history_service import HistoryService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_service import ScriptService
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.components.project_tabs import project_header, project_top_tabs
from shorts_creator.ui.components.script_viewer import SeoPanel
from shorts_creator.ui.icons import (
    chevron_right,
    download_icon,
    file_text,
    film_icon,
    folder,
    refresh,
    search,
    video_icon,
    zap,
)
from shorts_creator.ui.shell import AppLayout


class VideosController(Controller):
    def __init__(
        self,
        history: HistoryService,
        scripts: ScriptService,
        runs: RunService,
        projects: ProjectService,
    ):
        self.layout = AppLayout()
        self.history = history
        self.scripts = scripts
        self.runs = runs
        self.projects = projects

    @get("/projects/{id}/videos")
    async def project_videos(self, request=None, id: str = "") -> HTMLContent:
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)
        content = render_to_string(
            el(
                "div",
                project_header(project),
                project_top_tabs(id, "videos"),
                await videos_body_html(self.history, self.runs, self.projects, self.scripts, id),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(
            content=content,
            title="Videos",
            request=request,
        )
        return HTMLContent(html)

    @get("/projects/{id}/videos/version/{run_id}")
    async def version_card(self, request=None, id: str = "", run_id: str = "") -> HTMLContent:
        recent = await self.history.get_recent(100)
        completed = [r for r in recent if r.get("status") == "completed"]
        groups = await _build_groups(completed, self.runs, self.projects)
        for g in groups:
            if g["project_id"] != id:
                continue
            if any(r.get("run_id") == run_id for r in g["versions"]):
                g = dict(g)
                g["active_run_id"] = run_id
                return HTMLContent(_GroupCard(g))
        return html_response("Run not found", status_code=404)


async def videos_body_html(history, runs, projects, scripts, project_id="") -> str:
    recent = await history.get_recent(100)
    completed = [r for r in recent if r.get("status") == "completed"]

    groups = []
    if completed:
        groups = await _build_groups(completed, runs, projects)
        if project_id:
            groups = [g for g in groups if g["project_id"] == project_id]

    if not groups:
        body = _EmptyPage(project_id)
    else:
        total_duration = sum(
            (_active_run(g).get("duration_s", 0) or 0)
            for g in groups
            if isinstance(_active_run(g).get("duration_s"), (int, float))
        )
        stats_bar = el(
            "div",
            el(
                "div",
                el("span", str(len(groups)), class_="text-foreground text-lg font-bold font-mono"),
                el(
                    "span",
                    f" video{'' if len(groups) == 1 else 's'} rendered",
                    class_="text-muted-foreground text-xs font-mono ml-1",
                ),
            ),
            el(
                "div",
                el(
                    "span",
                    f"\u23f1 {total_duration:.0f}s",
                    class_="text-primary text-xs font-mono bg-primary/40 px-2 py-0.5 rounded border border-primary/40",
                ),
                el("span", "total content", class_="text-muted-foreground text-xs font-mono ml-2"),
            ),
            class_=("mt-4 pt-4 border-t border-border/60 " if project_id else "")
            + "pb-3 border-b border-border/30 flex items-center justify-between",
        )

        body = el(
            "div",
            stats_bar,
            _VideosGrid(
                "Ready for Distribution",
                [g for g in groups if g["seo"]],
                "No SEO-ready videos yet",
                "Generate SEO for a video below and it will appear here ready to share.",
            ),
            _VideosGrid(
                "Awaiting SEO",
                [g for g in groups if not g["seo"]],
                "All videos have SEO metadata",
                "Every rendered video now has search metadata and social captions.",
            ),
            class_="space-y-8",
        )

    return Markup(render_to_string(el("div", body, id="videos-content")))


async def _build_groups(completed, runs, projects) -> list[dict]:
    groups: dict[str, dict] = {}
    order: list[str] = []
    idea_index_by_id: dict[str, int] = {}
    idea_lists: dict[str, list] = {}
    for r in completed:
        item = dict(r)
        if not item.get("duration_s") and item.get("output"):
            item["duration_s"] = probe_duration(item["output"])
        item["_project_id"] = None
        item["_idea_id"] = None
        item["_idea_index"] = None
        item["_seo"] = None
        rid = r.get("run_id")
        if rid:
            db_run = await runs.get(rid)
            if db_run:
                item["_project_id"] = getattr(db_run, "project_id", None)
                idea_id = getattr(db_run, "selected_idea_id", None)
                item["_idea_id"] = idea_id
                if item["_project_id"] and idea_id:
                    saved = await projects.get_script(item["_project_id"], idea_id)
                    if saved:
                        item["_seo"] = (saved.get("metadata") or {}).get("seo")
                        if idea_id not in idea_index_by_id:
                            raw = idea_lists.get(item["_project_id"])
                            if raw is None:
                                project = (
                                    await projects.get(item["_project_id"])
                                    if getattr(projects, "get", None)
                                    else None
                                )
                                raw = []
                                if project and project.idea_json:
                                    try:
                                        raw = json.loads(project.idea_json)
                                    except (json.JSONDecodeError, TypeError):
                                        raw = []
                                idea_lists[item["_project_id"]] = raw
                        for idx, idea in enumerate(raw or []):
                            if isinstance(idea, dict) and idea.get("id") == idea_id:
                                idea_index_by_id[idea_id] = idx
                                break
                    item["_idea_index"] = idea_index_by_id.get(idea_id)
        key = item["_idea_id"] or item.get("idea") or "Untitled Idea"
        if key not in groups:
            groups[key] = {
                "key": key,
                "title": item.get("idea", "Untitled Idea"),
                "project_id": item["_project_id"],
                "idea_id": item["_idea_id"],
                "idea_index": item["_idea_index"],
                "seo": item["_seo"],
                "versions": [],
                "active_run_id": rid or item.get("run_id", ""),
            }
            order.append(key)
        g = groups[key]
        g["versions"].append(item)
    result = [groups[k] for k in order]
    for g in result:
        g["versions"].sort(key=lambda r: r.get("created_at") or r.get("date") or "")
    return result


def _active_run(group) -> dict:
    for r in group["versions"]:
        if r.get("run_id") == group["active_run_id"]:
            return r
    return group["versions"][0]


def _VideosGrid(title, groups, empty_text, empty_hint):
    empty = ""
    if not groups:
        empty = el(
            "div",
            el(
                "div",
                film_icon(),
                class_="w-11 h-11 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-3",
            ),
            el("h3", empty_text, class_="text-sm font-semibold text-foreground mb-1"),
            el(
                "p",
                empty_hint,
                class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
            ),
            class_="text-center py-12 px-6 rounded-2xl border border-dashed border-border w-full",
        )
    return el(
        "div",
        el(
            "div",
            el(
                "h2",
                title,
                class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono",
            ),
            el(
                "span",
                str(len(groups)),
                class_="text-muted-foreground text-[11px] font-mono bg-secondary/60 px-2 py-0.5 rounded-full border border-border/50",
            ),
            class_="flex items-center gap-2 mb-3",
        ),
        el(
            "div",
            *(_GroupCard(g) for g in groups),
            empty,
            class_="grid grid-cols-1 xl:grid-cols-2 gap-4",
        ),
    )


def _EmptyPage(project_id):
    ideas_url = f"/projects/{project_id}/scripts" if project_id else "/projects"
    render_url = f"/projects/{project_id}/render" if project_id else "/projects"
    return el(
        "div",
        el(
            "div",
            el(
                "div",
                video_icon(),
                class_="w-14 h-14 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-4",
            ),
            el(
                "h3",
                "No Rendered Videos Yet",
                class_="text-base font-semibold text-foreground mb-2",
            ),
            el(
                "p",
                "Generate a script then launch the Render Engine to create your first video.",
                class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed mb-6",
            ),
            el(
                "div",
                el(
                    "a",
                    zap(),
                    el("span", "Start Creating", class_="ml-1.5 font-semibold"),
                    href=ideas_url,
                    hx_get=ideas_url,
                    hx_target="#main-content",
                    hx_push_url=ideas_url,
                    class_="inline-flex items-center text-xs bg-primary hover:bg-primary text-primary-foreground px-4 py-2.5 rounded-xl font-semibold transition-colors shadow-sm",
                ),
                el(
                    "a",
                    el("span", "Render Engine", class_="font-semibold mr-1"),
                    chevron_right(),
                    href=render_url,
                    hx_get=render_url,
                    hx_target="#main-content",
                    hx_push_url=render_url,
                    class_="inline-flex items-center text-xs text-foreground hover:text-primary-foreground border border-border hover:border-border px-4 py-2.5 rounded-xl font-semibold transition-all bg-card",
                ),
                class_="flex items-center justify-center gap-3",
            ),
            class_="text-center py-20 px-6 rounded-2xl border border-dashed border-border w-full",
        ),
    )


def VideoCard(run, project_id=None, idea_id=None, seo=None):
    group = {
        "key": run.get("idea", "Untitled Idea"),
        "title": run.get("idea", "Untitled Idea"),
        "project_id": project_id,
        "idea_id": idea_id,
        "idea_index": None,
        "seo": seo,
        "versions": [run],
        "active_run_id": run.get("run_id", ""),
    }
    return _GroupCard(group)


def _GroupCard(group, hx_target="#videos-content", card=False):
    title = group["title"]
    title_short = (title[:48] + "\u2026") if len(title) > 48 else title
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h3",
                        title_short,
                        class_="text-foreground font-semibold text-sm leading-snug min-w-0",
                        title=title,
                    ),
                    _VersionChips(group),
                    class_="flex items-center justify-between gap-3 mb-3",
                ),
                el(
                    "div",
                    _VideoColumn(
                        _active_run(group),
                        group["project_id"],
                        group["idea_id"],
                        group.get("idea_index"),
                    ),
                    _SeoSide(
                        group["seo"],
                        group["project_id"],
                        group["idea_id"],
                        hx_target=hx_target,
                        card=card,
                    ),
                    class_="flex gap-4 items-start",
                ),
                class_="rounded-2xl border border-border/60 bg-card/30 p-4",
                id=f"card-{group['key']}",
            )
        )
    )


def _VersionChips(group):
    versions = group["versions"]
    total = len(versions)
    if total < 2 or not group.get("project_id"):
        return ""
    active_idx = next(
        (i for i, r in enumerate(versions) if r.get("run_id") == group["active_run_id"]),
        -1,
    )
    segments = _visible_segments(total, active_idx)
    elements = []
    for si, seg in enumerate(segments):
        if si:
            elements.append(
                el("span", "\u2026", class_="text-muted-foreground text-[11px] font-mono")
            )
        for i in seg:
            run = versions[i]
            rid = run.get("run_id", "")
            active = i == active_idx
            elements.append(
                el(
                    "button",
                    str(i + 1),
                    type="button",
                    hx_get=f"/projects/{group['project_id']}/videos/version/{rid}",
                    hx_target=f"#card-{group['key']}",
                    hx_swap="outerHTML",
                    title=(run.get("created_at") or run.get("date") or "")[:10],
                    class_=(
                        "w-6 h-6 rounded-md text-[11px] font-mono font-semibold flex items-center justify-center "
                        "transition-colors border "
                        + (
                            "bg-primary text-primary-foreground border-primary"
                            if active
                            else "bg-secondary/70 text-foreground border-border/50 hover:bg-secondary/60"
                        )
                    ),
                )
            )
    return el(
        "div",
        el("span", "Ver:", class_="text-muted-foreground text-[11px] font-mono"),
        *elements,
        class_="flex items-center gap-1.5",
    )


def _visible_segments(total: int, active_idx: int) -> list[list[int]]:
    if total <= 6:
        return [list(range(total))]
    first, last = list(range(3)), list(range(total - 3, total))
    if active_idx not in first and active_idx not in last:
        return [first, [active_idx], last]
    indices = first + last
    segments: list[list[int]] = []
    for i in indices:
        if segments and i == segments[-1][-1] + 1:
            segments[-1].append(i)
        else:
            segments.append([i])
    return segments


def _action_link(label, icon, href):
    return el(
        "a",
        icon,
        el("span", label, class_="font-semibold"),
        href=href,
        hx_get=href,
        hx_target="#main-content",
        hx_push_url=href,
        class_="flex items-center justify-center gap-2 w-full text-xs font-mono rounded-lg border border-border/60 bg-card/40 px-3 py-2 text-foreground hover:bg-secondary/50 transition-colors",
    )


def _VideoColumn(run, project_id, idea_id="", idea_index=None):
    run_id = run.get("run_id", "")
    duration = run.get("duration_s")
    output_path = run.get("output", "")
    filename = os.path.basename(output_path) if output_path else ""
    file_exists = bool(output_path and os.path.exists(output_path))
    raw = run.get("created_at", "") or run.get("date", "") or ""
    date = raw[:10] if raw else "\u2014"
    duration_str = (
        f"{duration:.1f}s" if isinstance(duration, (int, float)) and duration else "\u2014"
    )

    poster_src = f"/api/videos/poster/{run_id}"
    video_attrs = {
        "controls": "",
        "preload": "metadata",
        "playsinline": "",
        "poster": poster_src,
        "class_": "w-full aspect-[9/16] object-contain bg-foreground/10 rounded-lg",
    }

    actions = []
    if project_id:
        actions.append(
            _action_link("View Run", chevron_right(), f"/projects/{project_id}/runs/{run_id}")
        )
        if idea_index is not None:
            actions.append(
                _action_link(
                    "Open Script",
                    file_text(),
                    f"/projects/{project_id}/scripts?idea_index={idea_index}",
                )
            )
        actions.append(_action_link("Open Project", folder(), f"/projects/{project_id}"))
    actions.append(
        el(
            "a",
            download_icon(),
            el("span", "Download MP4", class_="ml-1.5 font-semibold"),
            href=f"/api/videos/download/{run_id}" if file_exists else "#",
            class_=(
                "flex items-center justify-center gap-2 w-full text-xs font-mono rounded-lg border border-primary/40 "
                "bg-primary/20 px-3 py-2 text-primary hover:bg-primary/30 transition-colors"
                if file_exists
                else "flex items-center justify-center gap-2 w-full text-xs font-mono rounded-lg border border-border/60 "
                "bg-card/40 px-3 py-2 text-muted-foreground cursor-not-allowed"
            ),
            title="" if file_exists else "Video file not found on disk",
        )
    )

    return el(
        "div",
        el(
            "div",
            el(
                "video",
                el("source", src=f"/api/videos/preview/{run_id}", type="video/mp4"),
                **video_attrs,
            ),
            class_="rounded-xl overflow-hidden border border-border/60 bg-foreground/20",
        ),
        el(
            "div",
            el(
                "span",
                f"\u23f1 {duration_str}",
                class_="text-primary text-[11px] font-mono bg-primary/40 px-2 py-0.5 rounded border border-primary/30",
            ),
            el("span", date, class_="text-muted-foreground text-[11px] font-mono ml-auto"),
            class_="flex items-center gap-2 mt-2",
        ),
        (
            el(
                "p",
                filename,
                class_="text-muted-foreground text-[10px] font-mono mt-1.5 truncate",
                title=filename,
            )
            if filename
            else ""
        ),
        el(
            "div",
            *actions,
            class_="mt-3 flex flex-col gap-1.5",
        ),
        class_="w-64 shrink-0",
    )


def _SeoSide(seo, project_id, idea_id, hx_target="#videos-content", card=False):
    qs = f"project_id={project_id}&idea_id={idea_id}"
    if card:
        qs += "&card=1"
    if seo:
        return el(
            "div",
            SeoPanel(seo, project_id=project_id, idea_id=idea_id),
            ActionButton(
                "Regenerate SEO",
                variant="outline",
                icon=refresh(),
                hx_post=f"/api/render/generate-seo?{qs}",
                hx_target=hx_target,
                hx_swap="innerHTML",
                class_extra="mt-3 w-full",
            ),
            class_="flex-1 min-w-0",
        )

    can_generate = bool(project_id and idea_id)
    message = (
        "Generate YouTube title, description, tags and social captions for this video."
        if can_generate
        else "This run is not linked to a script, so SEO cannot be generated for it."
    )
    button = ""
    if can_generate:
        button = ActionButton(
            "Generate SEO",
            variant="success",
            icon=refresh(),
            hx_post=f"/api/render/generate-seo?{qs}",
            hx_target=hx_target,
            hx_swap="innerHTML",
        )
    return el(
        "div",
        el(
            "div",
            search(),
            class_="w-10 h-10 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-2.5",
        ),
        el("h3", "No SEO metadata", class_="text-sm font-semibold text-foreground mb-1"),
        el(
            "p",
            message,
            class_="text-muted-foreground text-[11px] max-w-xs mx-auto leading-relaxed mb-4",
        ),
        button,
        class_="flex-1 min-w-0 flex flex-col items-center justify-center text-center p-6 rounded-2xl border border-dashed "
        "border-border rounded-xl bg-card/20 min-h-[440px]",
    )
