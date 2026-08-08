from html import escape

from lexigram.web import Controller, HTMLContent, get, html_response, post

from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ProjectProfileOverrides,
)
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import (
    ProjectProfileService,
    pair_block_message,
    resolve_global_settings,
)
from shorts_creator.services.project_service import ProfileValidationError, ProjectService
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.ui.components.project_tabs import project_header, project_top_tabs
from shorts_creator.ui.components.settings_profile import profile_error_feedback
from shorts_creator.ui.pages.new_project import form_overrides, project_settings_form
from shorts_creator.ui.shell import AppLayout

ASSET_ROLES = {
    "asset_music_id": ("music", ""),
    "asset_font_id": ("font", ""),
    "asset_bg_clip_id": ("clip", "background"),
    "asset_outro_clip_id": ("clip", "outro"),
    "asset_watermark_id": ("watermark", ""),
}

_NUMERIC_OVERRIDE_KEYS = frozenset(
    {
        "duration_seconds",
        "pacing_wps",
        "hook_lead_in_seconds",
        "loudness_target_lufs",
    }
)


def _as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolved(value, source: ProfileSource):
    from shorts_creator.models.project_profile import ResolvedSetting

    return ResolvedSetting(
        value=value, source=source, is_overridden=source is ProfileSource.PROJECT
    )


def _legacy_profile(project, config: AppConfig, global_values: dict) -> EffectiveProjectProfile:
    """Best-effort profile for tests/back-compat when no profile service is wired."""
    import json

    try:
        overrides = json.loads(project.profile_overrides_json or "{}")
    except (TypeError, ValueError):
        overrides = {}
    if not isinstance(overrides, dict):
        overrides = {}
    global_ = resolve_global_settings(config, global_values or {})

    def is_global(key: str) -> bool:
        return global_values.get(key) not in (None, "")

    def override_or(key: str, global_key: str, fallback):
        overridden = key in overrides and overrides[key] is not None
        source = (
            ProfileSource.PROJECT
            if overridden
            else (ProfileSource.GLOBAL if is_global(global_key) else ProfileSource.BUILT_IN)
        )
        value = (
            overrides[key]
            if overridden
            else (global_.get(global_key, fallback) if is_global(global_key) else fallback)
        )
        return _resolved(value, source)

    duration_raw = overrides.get("duration_seconds")
    if duration_raw is not None:
        duration, duration_src = duration_raw, ProfileSource.PROJECT
    elif is_global("default_duration"):
        duration, duration_src = (
            _as_float(global_values.get("default_duration")) or config.default_duration,
            ProfileSource.GLOBAL,
        )
    else:
        duration, duration_src = config.default_duration, ProfileSource.BUILT_IN

    assets = {}
    for key in ASSET_ROLES:
        global_key = f"asset_default_{key.removeprefix('asset_')}"
        assets[key] = override_or(key, global_key, None)

    return EffectiveProjectProfile(
        duration_seconds=_resolved(duration, duration_src),
        caption_style=override_or("caption_style", "default_caption_style", "highlight"),
        format_name=override_or("format_name", "format_name", "narrated"),
        topic=_resolved(project.topic, ProfileSource.PROJECT),
        reel_width=_resolved(config.reel_width, ProfileSource.BUILT_IN),
        reel_height=_resolved(config.reel_height, ProfileSource.BUILT_IN),
        **assets,
    )


def _success_feedback(msg: str = "Profile saved") -> str:
    return f'<script>window.showToast("{msg}","success")</script>'


class ProjectSettingsController(Controller):
    def __init__(
        self,
        config: AppConfig,
        projects: ProjectService,
        store: SettingsStore,
        asset_service: AssetService | None = None,
        profile_service: ProjectProfileService | None = None,
    ):
        self.layout = AppLayout()
        self._config = config
        self.projects = projects
        self.store = store
        self.asset_service = asset_service
        self.profile_service = profile_service

    async def _resolve(self, project) -> EffectiveProjectProfile:
        if self.profile_service is not None:
            return await self.profile_service.resolve(project)
        global_values = await self._global_values()
        return _legacy_profile(project, self._config, global_values)

    async def _resolve_builtin(self, project) -> EffectiveProjectProfile:
        """Effective profile with the project's overrides suppressed (the
        same resolution call with an empty override store), mirroring what
        the settings-page reset buttons restore: global → format → builtin.
        Feeds the composer knobs' data_builtin reset targets."""
        bare = project.model_copy(update={"profile_overrides_json": "{}"})
        if self.profile_service is not None:
            return await self.profile_service.resolve(bare)
        global_values = await self._global_values()
        return _legacy_profile(bare, self._config, global_values)

    async def _global_values(self) -> dict:
        if self.store is None:
            return {}
        try:
            return await self.store.get_overrides()
        except Exception:  # noqa: BLE001 — legacy store is optional
            return {}

    async def _media_options(self) -> dict[str, list[tuple[str, str]]]:
        """Selectable assets per composer media role for the settings panels;
        empty when no asset service is wired."""
        if self.asset_service is None:
            return {}
        options = {}
        for key, (asset_type, role) in ASSET_ROLES.items():
            assets = await self.asset_service.list_by_type(asset_type, role or None)
            role_key = key.removeprefix("asset_").removesuffix("_id")
            options[role_key] = [(a.id, a.name) for a in assets]
        return options

    async def _configured_stock_providers(self) -> list[str]:
        if self.store is None:
            return []
        try:
            return await self.store.configured_providers()
        except Exception:  # noqa: BLE001 — optional store
            return []

    @get("/projects/{id}/settings")
    async def project_settings(self, request=None, id: str = "") -> HTMLContent:
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)

        profile = await self._resolve(project)
        builtin_profile = await self._resolve_builtin(project)
        asset_options = await self._media_options()
        stock_providers = await self._configured_stock_providers()
        pair_banner = ""
        if self.profile_service is not None:
            issues = await self.profile_service.validate_pair_for_project(project)
            if issues:
                lines = "".join(
                    f'<li><span class="font-mono font-bold">{escape(issue.code)}</span> '
                    f"- {escape(issue.message)}</li>"
                    for issue in issues
                )
                pair_banner = (
                    '<div class="mb-4 rounded-xl border border-warning/50 bg-warning/30 '
                    'px-4 py-3 text-warning">'
                    '<p class="text-[11px] font-mono font-semibold uppercase tracking-widest mb-1">'
                    "Topic/format contract</p>"
                    f'<ul class="text-xs space-y-1">{lines}</ul></div>'
                )
        content = (
            f"{project_header(project)}"
            f"{project_top_tabs(project.id, 'settings')}"
            '<div class="mt-4 pt-4 border-t border-border/60">'
            f"{pair_banner}"
            f"{project_settings_form(project, profile, asset_options, stock_providers, builtin_profile=builtin_profile)}"
            "</div>"
        )
        return HTMLContent(
            self.layout.render(
                content=content, title=f"Settings: {project.title or 'Project'}", request=request
            )
        )

    @post("/api/projects/{id}/settings")
    async def save_project_settings(self, request=None, id: str = "") -> HTMLContent:
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)
        data: dict = {}
        if request:
            try:
                data = await request.json()
            except (AttributeError, TypeError, ValueError):
                try:
                    data = dict(await request.form())
                except (AttributeError, TypeError, ValueError):
                    data = {}
        profile = await self._resolve(project)
        overrides = form_overrides(data, profile)
        blank_numeric = [key for key in _NUMERIC_OVERRIDE_KEYS if overrides.get(key) == ""]
        for key in blank_numeric:
            overrides.pop(key, None)

        candidate_format = overrides.get("format_name") or (
            profile.format_name.value if profile.format_name else None
        )
        blocked = pair_block_message(project.topic, candidate_format)
        if blocked:
            return HTMLContent(
                profile_error_feedback(
                    {"format_name": blocked},
                    "Could not save — the topic does not support this format",
                )
            )

        try:
            await self.projects.save_profile_overrides(id, ProjectProfileOverrides(**overrides))
        except ProfileValidationError as exc:
            return HTMLContent(profile_error_feedback(exc.errors))
        for key in blank_numeric:
            await self.projects.reset_profile_override(id, key)
        return HTMLContent(_success_feedback())

    @post("/api/projects/{id}/reset-override")
    async def reset_override(self, request=None, id: str = "") -> HTMLContent:
        project = await self.projects.get(id)
        if not project:
            return html_response("Project not found", status_code=404)
        form = dict(await request.form()) if request else {}
        key = str(form.get("key", "")).strip()
        if not key:
            return html_response("key is required", status_code=400)
        await self.projects.reset_profile_override(id, key)
        return HTMLContent(_success_feedback("Override reset"))
