import json

from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get
from markupsafe import Markup

from shorts_creator.services.core import AppConfig
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.project_state import ProjectStateService
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_service import ScriptService
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.components.concept_list_item import ConceptListItem
from shorts_creator.ui.components.pipeline_tracker import PipelineTracker
from shorts_creator.ui.components.script_viewer import ScriptViewer, TimingBar
from shorts_creator.ui.icons import alert, chevron_right, file_text, video_icon, zap
from shorts_creator.ui.shell import AppLayout


class ScriptsController(Controller):
    def __init__(
        self,
        scripts: ScriptService,
        ideas: IdeaService,
        config: AppConfig,
        runs: RunService,
        projects: ProjectService,
    ):
        self.layout = AppLayout()
        self.scripts = scripts
        self.ideas = ideas
        self.config = config
        self.runs = runs
        self.projects = projects
        self.state = ProjectStateService(projects, runs)

    @get("/projects/{id}/scripts")
    async def list_scripts(self, request=None, id: str = "") -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        sort = qp.get("sort", "")
        page = int(qp.get("page", 0)) if qp.get("page", "").isdigit() else 0
        project_id = id
        idea_index_q = qp.get("idea_index")
        idea_index = (
            int(idea_index_q) if idea_index_q is not None and idea_index_q.isdigit() else None
        )

        if not project_id:
            from starlette.responses import RedirectResponse

            return RedirectResponse(url="/projects", status_code=302)

        project = await self.projects.get(project_id)
        if not project:
            from starlette.responses import RedirectResponse

            return RedirectResponse(url="/projects", status_code=302)

        state = await self.state.for_project(project_id)
        ideas_raw = state.ideas if state else []

        cached: list = []
        idea_scripts: dict[int, dict] = {}
        if ideas_raw:
            from shorts_creator.topics.base import Idea

            for d in ideas_raw:
                try:
                    cached.append(Idea.from_dict(d))
                except (TypeError, ValueError):
                    pass
            for i, d in enumerate(ideas_raw):
                sj = d.get("script_json")
                if sj:
                    try:
                        idea_scripts[i] = json.loads(sj)
                    except (json.JSONDecodeError, TypeError):
                        pass

        if sort == "score":
            indexed = list(enumerate(cached))
            indexed.sort(key=lambda x: getattr(x[1], "quotability_score", 0), reverse=True)
            cached = [idea for _, idea in indexed]
            if idea_index is not None:
                for new_i, (orig_i, _) in enumerate(indexed):
                    if orig_i == idea_index:
                        idea_index = new_i
                        break

        script_indices = state.script_indices if state else set()
        rendered_indices = state.rendered_indices if state else set()

        page_size = 10
        offset = page * page_size
        total_ideas = len(cached)
        total_pages = max(1, (total_ideas + page_size - 1) // page_size)
        page_ideas = cached[offset : offset + page_size]

        concept_items = [
            ConceptListItem(
                idea,
                i + 1,
                idea_index=i,
                project_id=project_id,
                selected=(i == idea_index),
                sort=sort,
                has_script=i in script_indices,
                has_video=i in rendered_indices,
                page=page,
            )
            for i, idea in enumerate(page_ideas)
        ]

        render_url = f"/projects/{project_id}/render" + (
            f"?idea_index={idea_index}" if idea_index is not None else ""
        )

        saved_script = idea_scripts.get(idea_index) if idea_index is not None else None
        script_action_buttons = ""

        if saved_script:
            from shorts_creator.topics import ParsedScript, ScriptSection

            sections = [ScriptSection(**s) for s in saved_script.get("sections", [])]
            script_obj = ParsedScript(
                title=saved_script.get("title", ""),
                sections=sections,
                total_duration=saved_script.get("total_duration", 0),
                word_count=saved_script.get("word_count", 0),
                pacing_wps=saved_script.get("pacing_wps", 0),
                emotional_arc=saved_script.get("emotional_arc"),
                metadata=saved_script.get("metadata"),
            )
            timing = TimingBar(script_obj.sections, script_obj.total_duration)
            script_action_buttons = Markup(
                el(
                    "div",
                    ActionButton(
                        "Regenerate Script",
                        icon=zap(),
                        hx_post="/api/scripts/generate",
                        hx_target="#script-output",
                        hx_swap="innerHTML",
                        hx_vals=json.dumps({"idea_index": idea_index, "project_id": project_id}),
                    ),
                    el(
                        "a",
                        video_icon(),
                        el("span", "Proceed to Render", class_="ml-1.5 font-semibold"),
                        chevron_right(),
                        href=render_url,
                        hx_get=render_url,
                        hx_target="#main-content",
                        hx_push_url=render_url,
                        class_="inline-flex items-center text-xs text-primary hover:text-primary "
                        "bg-secondary hover:bg-secondary/80 border border-border/50 "
                        "px-3 py-1.5 rounded-lg transition-all font-mono font-semibold",
                    ),
                    class_="flex items-center gap-2 shrink-0",
                )
            )
            right_content = Markup(
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "h2",
                            script_obj.title,
                            class_="text-lg font-bold text-foreground tracking-tight truncate",
                        ),
                        (
                            el(
                                "span",
                                video_icon(),
                                el("span", "Video Rendered", class_="ml-1"),
                                class_="text-primary text-xs font-semibold inline-flex items-center shrink-0",
                            )
                            if idea_index in rendered_indices
                            else ""
                        ),
                        class_="flex items-center gap-3 mb-3",
                    ),
                    el("div", timing, class_="mb-4"),
                    ScriptViewer(
                        script_obj,
                        project_id=project_id,
                        idea_index=idea_index if idea_index is not None else 0,
                    ),
                )
            )
        elif idea_index is not None and 0 <= idea_index < len(cached):
            selected_idea = cached[idea_index]
            score = getattr(selected_idea, "quotability_score", 5.0)
            hook = getattr(selected_idea, "hook_line", "")
            audience = getattr(selected_idea, "target_audience", "")
            arc = getattr(selected_idea, "emotional_arc", "")
            core_msg = getattr(selected_idea, "core_message", "")
            title = getattr(selected_idea, "title", "Untitled Idea")
            identity = getattr(selected_idea, "identity_signal", "")
            permission = getattr(selected_idea, "permission_given", "")
            share = getattr(selected_idea, "share_trigger", "")
            score_color = (
                "text-success"
                if score >= 8.5
                else "text-warning"
                if score >= 6.5
                else "text-destructive"
            )
            has_script = idea_index in script_indices

            info_rows = []
            if audience:
                info_rows.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Audience",
                            class_="text-muted-foreground text-[10px] font-mono uppercase tracking-wider",
                        ),
                        el("span", audience, class_="text-foreground text-xs ml-2"),
                        class_="flex items-baseline gap-2",
                    )
                )
            if arc:
                info_rows.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Arc",
                            class_="text-muted-foreground text-[10px] font-mono uppercase tracking-wider",
                        ),
                        el("span", arc, class_="text-foreground text-xs ml-2"),
                        class_="flex items-baseline gap-2",
                    )
                )
            if identity:
                info_rows.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Identity",
                            class_="text-muted-foreground text-[10px] font-mono uppercase tracking-wider",
                        ),
                        el("span", identity, class_="text-foreground text-xs ml-2"),
                        class_="flex items-baseline gap-2",
                    )
                )
            if permission:
                info_rows.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Permission",
                            class_="text-muted-foreground text-[10px] font-mono uppercase tracking-wider",
                        ),
                        el("span", permission, class_="text-foreground text-xs ml-2"),
                        class_="flex items-baseline gap-2",
                    )
                )
            if share:
                info_rows.append(
                    el(
                        "div",
                        el(
                            "span",
                            "Share Trigger",
                            class_="text-muted-foreground text-[10px] font-mono uppercase tracking-wider",
                        ),
                        el("span", share, class_="text-foreground text-xs ml-2"),
                        class_="flex items-baseline gap-2",
                    )
                )

            generate_btn = ActionButton(
                "Generate Script",
                icon=zap(),
                hx_post="/api/scripts/generate",
                hx_target="#script-output",
                hx_swap="innerHTML",
                hx_vals=json.dumps({"idea_index": idea_index, "project_id": project_id}),
            )
            status_label = (
                el("span", "Script ready", class_="text-success text-xs font-semibold")
                if has_script
                else el("span", "No script", class_="text-muted-foreground text-xs")
            )
            has_video = idea_index in rendered_indices
            video_label = (
                el(
                    "span",
                    video_icon(),
                    el("span", "Video Rendered", class_="ml-1"),
                    class_="text-primary text-xs font-semibold inline-flex items-center",
                )
                if has_video
                else ""
            )

            right_content = Markup(
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "span",
                            f"#{idea_index + 1:02d}",
                            class_="text-primary text-[11px] font-mono font-semibold mr-2",
                        ),
                        el(
                            "span",
                            f"\u26a1{score:.1f}",
                            class_=f"text-xs font-mono font-bold {score_color}",
                        ),
                        status_label,
                        video_label,
                        class_="flex items-center gap-3 mb-3",
                    ),
                    el("h2", title, class_="text-xl font-bold text-foreground leading-snug mb-4"),
                    (
                        el(
                            "div",
                            el(
                                "span",
                                "Message",
                                class_="text-primary font-semibold uppercase text-[10px] tracking-wider font-mono block mb-1",
                            ),
                            el("p", core_msg, class_="text-foreground text-sm leading-relaxed"),
                            class_="mb-4",
                        )
                        if core_msg
                        else ""
                    ),
                    (
                        el(
                            "div",
                            el(
                                "span",
                                "Hook",
                                class_="text-primary font-semibold uppercase text-[10px] tracking-wider font-mono block mb-1",
                            ),
                            el(
                                "p",
                                f"\u201c{hook}\u201d",
                                class_="text-muted-foreground italic text-sm",
                            ),
                            class_="border border-border/50 rounded-lg p-3 mb-4 leading-relaxed",
                        )
                        if hook
                        else ""
                    ),
                    el("div", *info_rows, class_="space-y-1.5 mb-4 border-b border-border/30 pb-4")
                    if info_rows
                    else "",
                    el(
                        "div",
                        generate_btn,
                        class_="pt-2",
                    ),
                )
            )
        elif cached:
            right_content = Markup(
                el(
                    "div",
                    el(
                        "div",
                        file_text(),
                        class_="w-10 h-10 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-3",
                    ),
                    el(
                        "h3",
                        "Select an Idea to Script",
                        class_="text-sm font-semibold text-foreground mb-1",
                    ),
                    el(
                        "p",
                        "Click an idea from the left panel to see its details and generate a full video script.",
                        class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
                    ),
                    class_="text-center py-16 px-6 rounded-2xl border border-dashed border-border",
                )
            )
        else:
            right_content = Markup(
                el(
                    "div",
                    el(
                        "div",
                        alert(),
                        class_="w-10 h-10 rounded-full bg-warning/40 border border-warning/50 flex items-center justify-center text-warning mx-auto mb-3",
                    ),
                    el(
                        "h3",
                        "No Ideas Available",
                        class_="text-sm font-semibold text-foreground mb-1",
                    ),
                    el(
                        "p",
                        "Generate ideas first using the Generate Ideas button above.",
                        class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
                    ),
                    class_="text-center py-16 px-6 rounded-2xl border border-dashed border-border",
                )
            )

        last_type = ""
        if cached:
            last_type = getattr(cached[0], "topic", "") or ""
        if not last_type:
            from shorts_creator.topics import registry

            last_type = registry.available[0].name if registry.available else "self_improvement"
        sort_default_active = (
            "bg-primary text-primary-foreground border-primary/50"
            if sort != "score"
            else "text-muted-foreground hover:text-foreground bg-card border-border"
        )
        sort_score_active = (
            "bg-primary text-primary-foreground border-primary/50"
            if sort == "score"
            else "text-muted-foreground hover:text-foreground bg-card border-border"
        )
        scripts_base = f"/projects/{project_id}/scripts"
        sort_parts = []
        if idea_index is not None:
            sort_parts.append(f"idea_index={idea_index}")
        if page:
            sort_parts.append(f"page={page}")
        sort_query = "&".join(sort_parts)

        def _page_url(p: int) -> str:
            parts = [f"page={p}"]
            if sort == "score":
                parts.append("sort=score")
            if idea_index is not None:
                parts.append(f"idea_index={idea_index}")
            return f"{scripts_base}?{'&'.join(parts)}"

        pagination_html = ""
        if total_pages > 1:
            prev_btn = (
                (
                    el(
                        "a",
                        "\u2190 Prev",
                        href=_page_url(page - 1),
                        hx_get=_page_url(page - 1),
                        hx_target="#main-content",
                        hx_push_url=_page_url(page - 1),
                        class_="text-xs px-3 py-1 rounded bg-secondary hover:bg-secondary text-foreground font-mono border border-border transition-colors",
                    )
                )
                if page > 0
                else (
                    el(
                        "span",
                        "\u2190 Prev",
                        class_="text-xs px-3 py-1 rounded bg-card text-muted-foreground font-mono border border-border opacity-40",
                    )
                )
            )
            next_btn = (
                (
                    el(
                        "a",
                        "Next \u2192",
                        href=_page_url(page + 1),
                        hx_get=_page_url(page + 1),
                        hx_target="#main-content",
                        hx_push_url=_page_url(page + 1),
                        class_="text-xs px-3 py-1 rounded bg-secondary hover:bg-secondary text-foreground font-mono border border-border transition-colors",
                    )
                )
                if page < total_pages - 1
                else (
                    el(
                        "span",
                        "Next \u2192",
                        class_="text-xs px-3 py-1 rounded bg-card text-muted-foreground font-mono border border-border opacity-40",
                    )
                )
            )
            pagination_html = Markup(
                el(
                    "div",
                    prev_btn,
                    el(
                        "span",
                        f"Page {page + 1} of {total_pages}",
                        class_="text-muted-foreground text-[11px] font-mono",
                    ),
                    next_btn,
                    class_="flex items-center justify-between gap-3 pt-3 border-t border-border/30 mt-2",
                    id="pagination-controls",
                )
            )

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "h1",
                            "Script Studio Workspace",
                            class_="text-2xl font-bold text-foreground tracking-tight",
                        ),
                        el(
                            "p",
                            "Browse ideas on the left, preview and refine scripts on the right",
                            class_="text-muted-foreground text-xs mt-1 font-mono",
                        ),
                    ),
                    PipelineTracker(
                        "script" if idea_index is not None else "ideas",
                        project_id=project_id,
                        stage_state=state.stage_state if state else None,
                    ),
                    class_="flex items-center justify-between gap-4 border-b border-border/80 pb-2 mb-6",
                ),
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "div",
                            el(
                                "h2",
                                "Generated Ideas",
                                class_="text-xs font-bold uppercase tracking-widest text-muted-foreground font-mono",
                            ),
                            ActionButton(
                                "Generate Ideas",
                                icon=zap(),
                                hx_post="/api/ideas/generate",
                                hx_target="#concept-list",
                                hx_swap="afterbegin",
                                hx_vals=json.dumps({"project_id": project_id, "topic": last_type}),
                                class_extra="shrink-0",
                            ),
                            class_="flex items-center justify-between mb-2",
                        ),
                        el(
                            "div",
                            el(
                                "span",
                                "Sort:",
                                class_="text-muted-foreground text-[10px] font-mono mr-1",
                            ),
                            el(
                                "a",
                                "Default",
                                href=f"{scripts_base}?{sort_query}" if sort_query else scripts_base,
                                hx_get=f"{scripts_base}?{sort_query}"
                                if sort_query
                                else scripts_base,
                                hx_target="#main-content",
                                hx_push_url=f"{scripts_base}?{sort_query}"
                                if sort_query
                                else scripts_base,
                                class_=f"text-[10px] px-2 py-0.5 rounded-md font-mono border transition-colors {sort_default_active}",
                            ),
                            el(
                                "a",
                                "\u2191 Score",
                                href=f"{scripts_base}?sort=score"
                                + (f"&{sort_query}" if sort_query else ""),
                                hx_get=f"{scripts_base}?sort=score"
                                + (f"&{sort_query}" if sort_query else ""),
                                hx_target="#main-content",
                                hx_push_url=f"{scripts_base}?sort=score"
                                + (f"&{sort_query}" if sort_query else ""),
                                class_=f"text-[10px] px-2 py-0.5 rounded-md font-mono border transition-colors {sort_score_active}",
                            ),
                            class_="flex items-center gap-1 border-b border-border/30 pb-2 mb-1",
                        ),
                        el(
                            "div",
                            *concept_items
                            if concept_items
                            else [
                                el(
                                    "p",
                                    "No ideas generated yet. Click Generate Ideas to start.",
                                    class_="text-muted-foreground text-xs italic p-3 border border-border text-center",
                                )
                            ],
                            id="concept-list",
                        ),
                        pagination_html,
                        class_="lg:col-span-2 space-y-0",
                    ),
                    el(
                        "div",
                        el(
                            "div",
                            el(
                                "h2",
                                "Active Script Breakdown",
                                class_="text-xs font-bold uppercase tracking-widest text-muted-foreground font-mono",
                            ),
                            script_action_buttons if saved_script else "",
                            class_="flex items-center justify-between mb-3",
                        ),
                        el("div", right_content, id="script-output"),
                        class_="lg:col-span-4 space-y-4",
                    ),
                    class_="grid grid-cols-1 lg:grid-cols-6 gap-8 w-full",
                ),
                class_="w-full space-y-6",
            ),
        )
        html = self.layout.render(content=content, title="Scripts", request=request)
        return HTMLContent(html)
