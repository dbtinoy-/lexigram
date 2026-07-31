from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get, html_response, post
from starlette.responses import Response

from shorts_creator.controllers.projects.cards import (
    _empty_projects_state,
    _ProjectCard,
    _stat_chip,
)
from shorts_creator.controllers.projects.dashboard import _project_dashboard
from shorts_creator.formats import registry as formats
from shorts_creator.models.project import Project
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProjectProfileOverrides,
    validate_profile,
)
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
from shorts_creator.ui.components.settings_profile import profile_error_feedback
from shorts_creator.ui.icons import plus
from shorts_creator.ui.pages.new_project import fallback_profile, form_overrides, new_project_form
from shorts_creator.ui.shell import AppLayout

_ASSET_OPTIONS_ROLES = {
    "bg_clip": ("clip", "bg_clip"),
    "music": ("music", None),
    "font": ("font", None),
    "outro_clip": ("clip", "outro_clip"),
    "watermark": ("watermark", None),
}


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
