from lexigram.web import Controller, HTMLContent, get, html_response, post

from shorts_creator.controllers.settings import (
    render_global_creative_fields,
    render_stock_provider_fields,
)
from shorts_creator.models.project import Project
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.project_profile_service import (
    ProjectProfileService,
    resolve_global_settings,
)
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.ui.components.settings_profile import profile_error_slot


class SettingsApiController(Controller):
    def __init__(
        self,
        config: AppConfig,
        store: SettingsStore,
        asset_service: AssetService | None = None,
        profile_service: ProjectProfileService | None = None,
    ):
        self.config = config
        self.store = store
        self.asset_service = asset_service
        self.profile_service = profile_service

    @get("/api/settings")
    async def get_settings(self, request=None) -> HTMLContent:
        if self.profile_service is not None:
            # Global tier only: a topic-less project matches no profile
            # overrides, so duration resolves from the format / built-ins.
            profile = await self.profile_service.resolve(Project(topic=""))
            duration = (
                profile.duration_seconds.value
                if profile.duration_seconds
                else self.config.default_duration
            )
        else:
            duration = resolve_global_settings(self.config, await self.store.get_global_values())[
                "default_duration"
            ]
        rows = ""
        for key, val in (("default_duration", duration),):
            rows += f'<div class="flex items-center justify-between py-2"><span class="text-muted-foreground">{key}</span><span class="text-primary-foreground font-mono">{val}</span></div>'
        return HTMLContent(f'<div id="settings-content" class="space-y-2">{rows}</div>')

    @post("/api/settings/save")
    async def save_setting(self, request=None) -> HTMLContent:
        data = dict(await request.form()) if request else {}
        rejected = await self.store.save_global_values(data)
        if rejected:
            return HTMLContent(
                "".join(profile_error_slot(key, message) for key, message in rejected.items())
            )
        overrides = await self.store.get_overrides()
        fields = await render_global_creative_fields(self.config, overrides, self.asset_service)
        stock_fields = render_stock_provider_fields(overrides)
        return HTMLContent(
            f'<div id="settings-creative-fields" hx-swap-oob="innerHTML:#settings-creative-fields">{fields}</div>'
            f'<div id="settings-stock-fields" hx-swap-oob="innerHTML:#settings-stock-fields">{stock_fields}</div>'
            '<script>window.showToast("Settings saved","success")</script>'
        )

    @post("/api/settings/reset-override")
    async def reset_override(self, request=None) -> HTMLContent:
        form = dict(await request.form()) if request else {}
        key = str(form.get("key", "")).strip()
        if not key:
            return html_response("key is required", status_code=400)
        await self.store.reset(key)
        overrides = await self.store.get_overrides()
        fields = await render_global_creative_fields(self.config, overrides, self.asset_service)
        stock_fields = render_stock_provider_fields(overrides)
        return HTMLContent(
            f'<div id="settings-creative-fields" hx-swap-oob="innerHTML:#settings-creative-fields">{fields}</div>'
            f'<div id="settings-stock-fields" hx-swap-oob="innerHTML:#settings-stock-fields">{stock_fields}</div>'
            '<script>window.showToast("Override reset","success")</script>'
        )
