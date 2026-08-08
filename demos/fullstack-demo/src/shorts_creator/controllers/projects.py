import json
from html import escape

from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get, html_response, post
from markupsafe import Markup
from starlette.responses import Response

from shorts_creator.formats import registry as formats
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProjectProfileOverrides,
    validate_profile,
)
from shorts_creator.models.run import RunStatus
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import (
    ProjectProfileService,
    compatible_formats_by_topic,
    pair_block_message,
)
from shorts_creator.services.project_service import ProfileValidationError, ProjectService
from shorts_creator.services.project_state import ProjectStateService
from shorts_creator.services.run_service import RunService
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.ui.components.project_tabs import (
    _card_chips,
    _created_label,
    project_header,
    project_top_tabs,
)
from shorts_creator.ui.components.settings_profile import (
    caption_style_label,
    profile_error_feedback,
    source_badge,
)
from shorts_creator.ui.icons import folder, plus, zap
from shorts_creator.ui.pages.new_project import (
    fallback_profile,
    form_overrides,
    new_project_form,
)
from shorts_creator.ui.shell import AppLayout

_ASSET_OPTIONS_ROLES = {
    "bg_clip": ("clip", "bg_clip"),
    "music": ("music", None),
    "font": ("font", None),
    "outro_clip": ("clip", "outro_clip"),
    "watermark": ("watermark", None),
}

# ──────────────────────────────────────────────
# Controller
# ──────────────────────────────────────────────


class ProjectsController(Controller):
    def __init__(
        self,
        projects: ProjectService,
        runs: RunService | None = None,
        config: AppConfig | None = None,
        profile_service: ProjectProfileService | None = None,
        asset_service: AssetService | None = None,
        store: SettingsStore | None = None,
    ):
        self.layout = AppLayout()
        self.projects = projects
        self.config = config
        self.profile_service = profile_service
        self.asset_service = asset_service
        self.store = store
        self.state = ProjectStateService(projects, runs)

    async def _resolve_creation_profile(self, topic: str) -> EffectiveProjectProfile:
        """Effective profile the guided create form previews and compares form
        values against: the same ProjectProfileService.resolve call the settings
        page uses, falling back to config/built-ins when the service is absent."""
        if self.profile_service is not None:
            return await self.profile_service.resolve(Project(topic=topic))
        return fallback_profile(self.config)

    async def _resolve_project_profile(self, project) -> EffectiveProjectProfile:
        """Effective profile of an EXISTING project (its saved overrides
        included), like the settings page resolves; fallback when absent."""
        if self.profile_service is not None:
            return await self.profile_service.resolve(project)
        return fallback_profile(self.config)

    async def _asset_options(self) -> dict[str, list[tuple[str, str]]]:
        """Selectable assets per composer media role, mirroring the settings
        page selector pattern; empty when the service is absent."""
        if self.asset_service is None:
            return {}
        options = {}
        for key, (asset_type, role) in _ASSET_OPTIONS_ROLES.items():
            assets = await self.asset_service.list_by_type(asset_type, role or None)
            options[key] = [(a.id, a.name) for a in assets]
        return options

    async def _configured_stock_providers(self) -> list[str]:
        """Stock providers the pipeline can actually use (stored keys then
        environment variables); empty when no settings store is wired."""
        if self.store is None:
            return []
        return await self.store.configured_providers()

    @get("/projects")
    async def list_projects(self, request=None) -> HTMLContent:
        project_list = await self.projects.list_recent(50)
        states = await self.state.for_projects(project_list)

        if project_list:
            cards = [_ProjectCard(p, states.get(p.id)) for p in project_list]

            total = len(project_list)
            stats = el(
                "div",
                _stat_chip(str(total), "Project" + ("s" if total != 1 else "")),
                class_="flex items-center gap-3 mb-6",
            )

            body = el(
                "div",
                stats,
                el(
                    "div",
                    *cards,
                    class_="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4",
                ),
            )
        else:
            body = _empty_projects_state()

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "h1",
                            "Project Workspaces",
                            class_="text-2xl font-bold text-foreground tracking-tight",
                        ),
                        el(
                            "p",
                            "Your AI video creation hubs — each project holds ideas, scripts, and rendered videos",
                            class_="text-muted-foreground text-xs mt-1 font-mono",
                        ),
                    ),
                    class_="pb-5 border-b border-border/80 mb-6",
                ),
                body,
                class_="w-full",
            )
        )
        html = self.layout.render(content=content, title="Projects", request=request)
        return HTMLContent(html)

    @get("/projects/new")
    async def new_project_page(self, request=None) -> HTMLContent:
        profile = await self._resolve_creation_profile("self_improvement")
        asset_options = await self._asset_options()
        stock_providers = await self._configured_stock_providers()
        content = render_to_string(
            new_project_form(
                self.config,
                profile,
                compatible_formats_by_topic(),
                asset_options=asset_options,
                stock_providers=stock_providers,
            )
        )
        html = self.layout.render(content=content, title="Create Project", request=request)
        return HTMLContent(html)

    async def _read_form(self, request=None) -> dict:
        """Form/JSON payload as a plain dict; the POST handlers share this."""
        data: dict = {}
        if request:
            try:
                data = await request.json()
            except (AttributeError, TypeError, ValueError):
                try:
                    data = dict(await request.form())
                except (AttributeError, TypeError, ValueError):
                    data = {}
        return data

    @post("/api/projects/upsert")
    async def upsert_project(self, request=None) -> HTMLContent:
        data = await self._read_form(request)
        title = data.get("title") or "Untitled Project"
        topic = data.get("topic") or "self_improvement"
        focus = data.get("focus") or ""
        resolved = await self._resolve_creation_profile(topic)

        overrides = form_overrides(data, resolved)
        blocked = pair_block_message(
            topic,
            overrides.get("format_name")
            or (resolved.format_name.value if resolved.format_name else "narrated"),
        )
        if blocked:
            return HTMLContent(
                profile_error_feedback(
                    {"format_name": blocked},
                    "Could not save — the topic does not support this format",
                )
            )
        errors = validate_profile(overrides)
        if errors:
            return HTMLContent(
                profile_error_feedback(errors, "Could not save — fix the values below")
            )

        try:
            created = await self.projects.create_project(
                title=title,
                topic=topic,
                focus=focus,
                overrides=overrides,
            )
        except ProfileValidationError as exc:
            return HTMLContent(
                profile_error_feedback(exc.errors, "Could not save — fix the values below")
            )

        return Response(
            status_code=200,
            headers={"HX-Redirect": f"/projects/{created.id}"},
        )

    @get("/projects/{id}")
    async def project_detail(self, request=None, id: str = "") -> HTMLContent:
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)

        state = await self.state.for_project(id)
        issues = None
        if self.profile_service is not None:
            issues = await self.profile_service.validate_pair_for_project(project)
        profile = await self._resolve_project_profile(project)
        asset_options = await self._asset_options()
        body = _project_dashboard(project, state, issues, profile, asset_options)
        html = self.layout.render(
            content=body,
            title=f"{project.title}",
            request=request,
            extra_nav=el(
                "a",
                plus(),
                el("span", "New Run", class_="ml-1.5 font-semibold"),
                href=f"/projects/{id}/scripts",
                hx_get=f"/projects/{id}/scripts",
                hx_target="#main-content",
                hx_push_url=f"/projects/{id}/scripts",
                class_="bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-primary-foreground text-xs px-4 py-2 rounded-xl font-semibold inline-flex items-center transition-all shadow-sm shadow-primary/40",
            ),
        )
        return HTMLContent(html)

    @post("/api/projects/{id}/format/remap")
    async def remap_project_format(self, request=None, id: str = "") -> HTMLContent:
        """Re-map a project's saved format override to a format the registry
        actually loads (fixes FORMAT_NOT_LOADED contract warnings in place)."""
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)
        data: dict = {}
        if request:
            try:
                data = dict(await request.form())
            except (AttributeError, TypeError, ValueError):
                data = {}
        fmt_name = str(data.get("format_name", "")).strip()
        if not fmt_name or not formats.has(fmt_name):
            return HTMLContent(
                profile_error_feedback(
                    {"format_name": "Pick a format from the registry"},
                    "Could not re-map format",
                )
            )
        blocked = pair_block_message(project.topic, fmt_name)
        if blocked:
            return HTMLContent(
                profile_error_feedback(
                    {"format_name": blocked},
                    "Could not re-map format — the topic does not support this format",
                )
            )
        try:
            await self.projects.save_profile_overrides(
                id, ProjectProfileOverrides(format_name=fmt_name)
            )
        except ProfileValidationError as exc:
            return HTMLContent(
                profile_error_feedback(exc.errors, "Could not re-map format — fix the values below")
            )
        return HTMLContent("<script>window.location.reload()</script>")


# ──────────────────────────────────────────────
# Project Card (grid view)
# ──────────────────────────────────────────────


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


# ──────────────────────────────────────────────
# Project Dashboard (/projects/{id})
# ──────────────────────────────────────────────


def _project_dashboard(project, state, issues=None, profile=None, asset_options=None) -> str:
    pid = project.id

    pair_banner = ""
    if issues:
        issue_list = el(
            "ul",
            *(
                el(
                    "li",
                    el("span", escape(issue.code), class_="font-mono font-bold"),
                    " — ",
                    escape(issue.message),
                )
                for issue in issues
            ),
            class_="text-xs space-y-1",
        )
        remap_form = ""
        if formats.available:
            fmt_options = [el("option", escape(f.label), value=f.name) for f in formats.available]
            remap_form = str(
                el(
                    "form",
                    el(
                        "select",
                        *fmt_options,
                        name="format_name",
                        class_="bg-background/80 border border-warning/50 rounded-lg px-2 py-1 text-xs font-mono text-warning focus:outline-none focus:border-warning/60",
                    ),
                    el(
                        "button",
                        "Re-map →",
                        type="submit",
                        class_="text-xs font-mono font-semibold text-warning-foreground bg-warning hover:bg-warning/90 px-3 py-1.5 rounded-lg transition-colors cursor-pointer",
                    ),
                    hx_post=f"/api/projects/{pid}/format/remap",
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    class_="flex items-center gap-2",
                )
            )
        pair_banner = Markup(
            '<div class="mb-4 rounded-xl border border-warning/50 bg-warning/30 '
            'px-4 py-3 text-warning">'
            '<p class="text-[11px] font-mono font-semibold uppercase tracking-widest mb-1">'
            "Topic/format contract</p>"
            f"{issue_list}"
            f"{remap_form}</div>"
        )

    # Header
    header = project_header(project, state)

    if not state.ideas:
        section = _dashboard_start(pid)
    else:
        left_cols = [
            _latest_render_card(pid, state),
            _profile_card(project, profile, asset_options or {}),
            _ideas_strip(pid, state),
            _scripts_block(pid, state),
        ]
        section = el(
            "div",
            _dashboard_stats(state),
            el(
                "div",
                el("div", *left_cols, class_="lg:col-span-2 space-y-6"),
                el("div", _dashboard_runs(project, state), class_="space-y-6"),
                class_="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6",
            ),
            class_="w-full",
        )

    content = render_to_string(
        el("div", pair_banner, header, project_top_tabs(pid, "overview"), section, class_="w-full")
    )
    return content


def _dashboard_start(pid) -> str:
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    zap(),
                    class_="w-10 h-10 rounded-xl bg-secondary/60 border border-border/40 flex items-center justify-center text-primary mx-auto mb-3",
                ),
                el("p", "Start Creating", class_="text-sm font-semibold text-foreground mb-1"),
                el(
                    "p",
                    "Generate ideas, write scripts, and render videos — all from one workspace.",
                    class_="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed mb-5",
                ),
                el(
                    "a",
                    plus(),
                    el("span", "Ideas & Scripts", class_="ml-1.5 font-semibold"),
                    href=f"/projects/{pid}/scripts",
                    hx_get=f"/projects/{pid}/scripts",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/scripts",
                    class_="inline-flex items-center bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-primary-foreground text-xs px-5 py-2.5 rounded-xl font-semibold transition-all shadow-md shadow-primary/40",
                ),
                class_="text-center py-14 px-6 rounded-2xl border border-dashed border-border rounded-2xl",
            )
        )
    )


def _dashboard_stats(state) -> str:
    s = state.stats
    return Markup(
        str(
            el(
                "div",
                _proj_stat(str(s["ideas"]), "Ideas", "text-primary"),
                _proj_stat(str(s["scripts"]), "Scripts", "text-primary"),
                _proj_stat(
                    str(s["videos"]),
                    "Videos",
                    "text-success" if s["videos"] else "text-muted-foreground",
                ),
                _proj_stat(str(s["runs"]), "Runs", "text-muted-foreground"),
                class_="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border/60",
            )
        )
    )


def _latest_render_card(pid: str, state) -> str:
    completed = [r for r in state.recent_runs if r.status == RunStatus.COMPLETED and r.output_path]
    if not completed:
        return ""
    run = completed[0]
    idea_id = run.selected_idea_id or ""
    idea_index = None
    seo = None
    for i, idea in enumerate(state.ideas):
        if isinstance(idea, dict) and idea.get("id") == idea_id:
            idea_index = i
            sj = idea.get("script_json")
            if sj:
                try:
                    seo = (json.loads(sj).get("metadata") or {}).get("seo")
                except (json.JSONDecodeError, TypeError):
                    seo = None
            break
    group = {
        "key": idea_id or run.title or "Untitled Idea",
        "title": run.title or "Untitled Idea",
        "project_id": pid,
        "idea_id": idea_id,
        "idea_index": idea_index,
        "seo": seo,
        "versions": [
            {
                "run_id": run.id,
                "idea": run.title,
                "duration_s": run.duration_s,
                "output": run.output_path,
                "created_at": run.created_at.isoformat() if run.created_at else "",
            }
        ],
        "active_run_id": run.id,
    }
    from shorts_creator.controllers.videos import _GroupCard

    return Markup(
        f'<div id="latest-render">'
        f'<div class="flex items-center justify-between mb-3">'
        f'<h2 class="text-[11px] font-mono font-semibold text-muted-foreground">LATEST RENDER</h2>'
        f'<a href="/projects/{pid}/videos" hx-get="/projects/{pid}/videos" hx-target="#main-content" hx-push-url="/projects/{pid}/videos" '
        f'class="text-xs font-mono text-muted-foreground hover:text-primary transition-colors">View all \u2192</a>'
        f"</div>"
        f"{_GroupCard(group, hx_target='#latest-render', card=True)}"
        f"</div>"
    )


def _card_row(label: str, value: str, key: str, setting, reset_url: str) -> str:
    meta = source_badge(setting)
    if setting.is_overridden:
        meta += (
            f'<button type="button" data-override-toggle data-key="{escape(key)}" '
            f'data-reset-url="{escape(reset_url)}" '
            f'class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/60 '
            f'text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors cursor-pointer" '
            f'title="Reset to inherited default">Reset</button>'
        )
    return (
        '<div class="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0">'
        f'<span class="text-xs font-mono text-muted-foreground">{escape(label)}</span>'
        '<span class="flex items-center gap-2 text-xs font-mono text-foreground">'
        f'<span class="truncate">{escape(value)}</span>{meta}</span></div>'
    )


def _profile_card(project, profile, asset_options) -> str:
    if profile is None:
        return ""
    reset_url = f"/api/projects/{project.id}/reset-override"
    rows = []
    for label, value in (
        (
            "Duration",
            f"{profile.duration_seconds.value:.0f}s" if profile.duration_seconds else None,
        ),
        (
            "Format",
            profile.format_name.value if profile.format_name else None,
        ),
        (
            "Caption style",
            caption_style_label(
                formats.get(profile.format_name.value) if profile.format_name else None,
                profile.caption_style.value if profile.caption_style else None,
            ),
        ),
        (
            "Reel",
            f"{profile.reel_width.value}×{profile.reel_height.value}"
            if profile.reel_width and profile.reel_height
            else None,
        ),
    ):
        if value is None:
            continue
        rows.append(
            '<div class="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0">'
            f'<span class="text-xs font-mono text-muted-foreground">{escape(label)}</span>'
            f'<span class="text-xs font-mono text-foreground">{escape(str(value))}</span></div>'
        )
    for label, key, role in (
        ("Music", "asset_music_id", "music"),
        ("Font", "asset_font_id", "font"),
        ("Background clip", "asset_bg_clip_id", "bg_clip"),
        ("Outro clip", "asset_outro_clip_id", "outro_clip"),
        ("Watermark", "asset_watermark_id", "watermark"),
    ):
        setting = getattr(profile, key, None)
        if setting is None or not setting.value:
            continue
        name = dict(asset_options.get(role, [])).get(setting.value, setting.value)
        rows.append(_card_row(label, str(name), key, setting, reset_url))
    for label, key, display in (
        ("Stage accents", "stage_accents", lambda v: json.dumps(v)),
        ("Section holds", "section_holds", lambda v: json.dumps(v)),
        ("Loudness target (LUFS)", "loudness_target_lufs", str),
        ("Audio normalize", "audio_normalize", str),
    ):
        setting = getattr(profile, key, None)
        if setting is None or setting.value is None:
            continue
        if isinstance(setting.value, dict) and not setting.value:
            continue
        rows.append(_card_row(label, display(setting.value), key, setting, reset_url))
    if not rows:
        return ""
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "EFFECTIVE PROFILE",
                        class_="text-[11px] font-mono font-semibold text-muted-foreground",
                    ),
                    el(
                        "a",
                        "Edit Settings →",
                        href=f"/projects/{project.id}/settings",
                        hx_get=f"/projects/{project.id}/settings",
                        hx_target="#main-content",
                        hx_push_url=f"/projects/{project.id}/settings",
                        class_="text-[11px] font-mono font-semibold text-primary hover:text-primary",
                    ),
                    class_="flex items-center justify-between mb-2",
                ),
                el(
                    "div",
                    Markup("".join(rows)),
                    class_="rounded-xl border border-border/60 bg-background/50 px-4 py-3",
                ),
                class_="rounded-2xl border border-border/60 bg-card/40 p-4",
            )
        )
    )


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


def _proj_stat(value: str, label: str, color: str) -> str:
    return Markup(
        str(
            el(
                "div",
                el("span", value, class_=f"text-lg font-bold font-mono {color}"),
                el("span", label, class_="text-[10px] font-mono text-muted-foreground block"),
                class_="flex flex-col items-start",
            )
        )
    )
