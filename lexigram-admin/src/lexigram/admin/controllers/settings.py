from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.admin.services.settings_service import (
    DEFAULT_SETTINGS,
    AdminSettingsService,
)
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger

logger = get_logger(__name__)


_SETTINGS_FORM = """\
<div class="max-w-2xl mx-auto py-8 px-4">
  <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Settings</h1>
  <form method="post" action="/admin/settings" class="space-y-6">
    <input type="hidden" name="csrf_token" value="{csrf_token}">
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">Branding</h2>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Site Name</label>
        <input type="text" name="site_name" value="{site_name}"
               class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
               placeholder="My Admin">
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Primary Color</label>
        <div class="flex items-center gap-3">
          <input type="color" name="primary_color" value="{primary_color}"
                 class="w-10 h-10 rounded cursor-pointer border border-gray-300 dark:border-gray-600 p-0.5"
                 oninput="this.nextElementSibling.value=this.value">
          <input type="text" name="primary_color_text" value="{primary_color}"
                 class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                 placeholder="#6b7280" pattern="^#[0-9a-fA-F]{{6}}$"
                 oninput="this.previousElementSibling.value=this.value">
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Hex color code (e.g. #6b7280)</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Logo URL</label>
        <input type="url" name="logo_url" value="{logo_url}"
               class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
               placeholder="https://example.com/logo.png">
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Favicon URL</label>
        <input type="url" name="favicon_url" value="{favicon_url}"
               class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
               placeholder="https://example.com/favicon.ico">
      </div>

      <h2 class="text-lg font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2 pt-4">Appearance</h2>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Default Theme</label>
        <select name="dark_mode"
                class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
          <option value="system" {system_sel}>System</option>
          <option value="light" {light_sel}>Light</option>
          <option value="dark" {dark_sel}>Dark</option>
        </select>
      </div>
    </div>

    <div class="flex justify-end gap-3">
      <a href="/admin/"
         class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
        Cancel
      </a>
      <button type="submit"
              class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors focus:ring-2 focus:ring-primary-500">
        Save Settings
      </button>
    </div>
  </form>
</div>"""


def _render_settings_form(
    settings: dict[str, Any], csrf_token: str = "", message: str = ""
) -> str:
    def _sel(v: str) -> str:
        return 'selected="selected"' if settings.get("dark_mode") == v else ""

    html = _SETTINGS_FORM.format(
        csrf_token=csrf_token,
        site_name=settings.get("site_name", ""),
        primary_color=settings.get("primary_color", "#6b7280"),
        logo_url=settings.get("logo_url", ""),
        favicon_url=settings.get("favicon_url", ""),
        system_sel=_sel("system"),
        light_sel=_sel("light"),
        dark_sel=_sel("dark"),
    )
    if message:
        banner_class = (
            "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 "
            "text-green-800 dark:text-green-300"
        )
        html = (
            f'<div class="{banner_class} border rounded-lg px-4 py-3 mb-4 text-sm">{message}</div>'
            + html
        )
    return html


class SettingsController(AdminController):
    prefix = "/settings"

    def __init__(
        self,
        renderer: AdminRenderer,
        settings_service: AdminSettingsService | None = None,
        csrf_service: AdminCsrfServiceProtocol | None = None,
    ) -> None:
        super().__init__(renderer=renderer)
        self._settings_service = settings_service
        self._csrf_service = csrf_service

    async def _get_tenant(self, request: Request) -> str:
        return await resolve_tenant_id(request, default="default")

    def _get_csrf_token(self, request: Request) -> str:
        if not self._csrf_service:
            return ""
        session = getattr(request, "session", {})
        session_id: str = session.get("admin_user_id", "anonymous")
        return self._csrf_service.generate_token(session_id)

    @get("/")
    async def index(self, request: Request) -> HTMLResponse:
        tenant = await self._get_tenant(request)
        settings = DEFAULT_SETTINGS.copy()
        if self._settings_service:
            overrides = await self._settings_service.get_all(tenant)
            settings.update(overrides)
        content = _render_settings_form(
            settings, csrf_token=self._get_csrf_token(request)
        )
        return await self.render_admin(request, content, title="Settings")

    @post("/")
    async def save(self, request: Request) -> HTMLResponse:
        tenant = await self._get_tenant(request)
        logger.debug(
            "settings.save_called",
            tenant=tenant,
            csrf_service=self._csrf_service is not None,
        )
        body_scope = request.scope.get("admin_form_data")
        if body_scope is not None:
            form = body_scope
        else:
            form = await request.form()

        primary_color = str(form.get("primary_color", "")).strip()
        if not primary_color:
            primary_color = str(form.get("primary_color_text", "#6b7280")).strip()

        settings = {
            "site_name": str(form.get("site_name", "")).strip(),
            "primary_color": primary_color,
            "logo_url": str(form.get("logo_url", "")).strip(),
            "favicon_url": str(form.get("favicon_url", "")).strip(),
            "dark_mode": str(form.get("dark_mode", "system")).strip(),
        }

        if self._settings_service:
            await self._settings_service.set_all(tenant, settings)

        settings = dict(DEFAULT_SETTINGS, **settings)
        content = _render_settings_form(
            settings,
            csrf_token=self._get_csrf_token(request),
            message="Settings saved successfully.",
        )
        return await self.render_admin(request, content, title="Settings")


__all__ = ["SettingsController"]
