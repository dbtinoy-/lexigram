"""Unified Configuration Center controller.

Provides a single entry point for all configuration management with
category-based navigation and spec-level editing.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.settings.panel.layout import ConfigLayout
from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.panel.types import ConfigCategory, get_default_categories
from lexigram.admin.settings.panel.ui import ConfigDashboardUI
from lexigram.contracts.web import get, post

__all__ = ["ConfigController"]


class ConfigController(AdminController):
    """Unified Configuration Center controller.

    Routes:
        GET /admin/config              - Landing page with category overview
        GET /admin/config/{category}   - Category view (redirects to first spec)
        GET /admin/config/{category}/{namespace} - Spec detail/edit view
        POST /admin/config/{category}/{namespace} - Save configuration
    """

    prefix = "/config"

    async def _build_categories(self, request: Request) -> list[ConfigCategory]:
        """Build category list with specs from registry."""
        categories = get_default_categories()

        # Map registry categories to display categories
        # Registry uses: env, admin, app, system
        # Display uses: env, app, system
        category_map = {
            "env": "env",
            "app": "app",
            "system": "system",
        }

        registry = await request.state.resolver.resolve(ConfigRegistry)

        for cat in categories:
            # Get specs for this category from registry
            for registry_cat, target_cat in category_map.items():
                if target_cat == cat.name:
                    specs = registry.get_specs(registry_cat)
                    cat.specs.extend(specs)

        return categories

    def _get_category(
        self,
        categories: list[ConfigCategory],
        name: str,
    ) -> ConfigCategory | None:
        """Find a category by name."""
        return next((c for c in categories if c.name == name), None)

    @get("/")
    async def index(self, request: Request) -> Response:
        """Configuration Center landing page."""
        categories = await self._build_categories(request)

        # Find first category with specs and redirect to first spec
        for cat in sorted(categories, key=lambda c: c.order):
            if cat.specs:
                first_spec = cat.specs[0]
                return RedirectResponse(
                    url=f"/admin/config/{cat.name}/{first_spec.namespace}",
                    status_code=302,
                )

        # No specs registered - show empty state
        layout = ConfigLayout(
            categories=categories,
            active_category=None,
            active_namespace=None,
            content=None,
            title="Configuration",
        )

        return await self.render_admin(request, layout, title="Configuration")

    @get("/{category}")
    async def category_view(self, request: Request) -> Response:
        """Category view - redirects to first spec in category."""
        category_name = request.path_params.get("category", "")
        categories = await self._build_categories(request)

        category = self._get_category(categories, category_name)
        if category and category.specs:
            first_spec = category.specs[0]
            return RedirectResponse(
                url=f"/admin/config/{category_name}/{first_spec.namespace}",
                status_code=302,
            )

        # Category empty or not found - show landing
        return RedirectResponse(url="/admin/config", status_code=302)

    @get("/{category}/{namespace:path}")
    async def spec_view(self, request: Request) -> Response:
        """Spec detail/edit view."""
        category_name = request.path_params.get("category", "")
        namespace = request.path_params.get("namespace", "")

        registry = await request.state.resolver.resolve(ConfigRegistry)

        categories = await self._build_categories(request)
        category = self._get_category(categories, category_name)

        if not category:
            self.flash(f"Category '{category_name}' not found.", "error")
            return RedirectResponse(url="/admin/config", status_code=302)

        # Find spec in category
        spec = next((s for s in category.specs if s.namespace == namespace), None)
        if not spec:
            self.flash(f"Configuration '{namespace}' not found.", "error")
            return RedirectResponse(
                url=f"/admin/config/{category_name}",
                status_code=302,
            )

        # Load current values
        values = await registry.get_values(namespace)

        # Render form
        ui = ConfigDashboardUI()
        form_content = ui.render_config_form(
            spec=spec.to_dict(),
            values=values,
            action=f"/admin/config/{category_name}/{namespace}",
        )

        layout = ConfigLayout(
            categories=categories,
            active_category=category_name,
            active_namespace=namespace,
            content=form_content,
            title="Configuration",
        )

        return await self.render_admin(
            request,
            layout,
            title=f"{spec.label or namespace} - Configuration",
        )

    @post("/{category}/{namespace:path}")
    async def save_spec(self, request: Request) -> Response:
        """Save configuration changes."""
        category_name = request.path_params.get("category", "")
        namespace = request.path_params.get("namespace", "")

        registry = await request.state.resolver.resolve(ConfigRegistry)

        form = await request.form()

        # Extract values (skip internal fields)
        updates = {}
        for key, value in form.items():
            if key.startswith("_"):
                continue
            updates[key] = value

        # Save to registry
        await registry.save_values(namespace, updates)

        if request.headers.get("hx-request") == "true":
            # For HTMX, return updated form + OOB flash message
            from starlette.responses import HTMLResponse

            from lexigram.admin.ui.data.toast import (  # type: ignore[import-untyped]
                Toast,
            )
            from lexigram.ui.core.base import render_to_string

            # Helper to clear flash messages from session since we are consuming them
            self._flash_messages.clear()

            # 1. Prepare Flash OOB
            toast_html = render_to_string(
                Toast("Configuration saved successfully.", type="success"),
            )
            flash_oob = (
                f'<div id="flash-container" hx-swap-oob="true">{toast_html}</div>'
            )

            # 2. Re-render Form
            values = await registry.get_values(namespace)
            categories = await self._build_categories(request)
            category = self._get_category(categories, category_name)
            spec = next((s for s in category.specs if s.namespace == namespace), None)  # type: ignore[union-attr]

            ui = ConfigDashboardUI()
            form_content = ui.render_config_form(
                spec=spec.to_dict(),  # type: ignore[union-attr]
                values=values,
                action=f"/admin/config/{category_name}/{namespace}",
            )
            form_html = render_to_string(form_content)

            return HTMLResponse(flash_oob + form_html)

        self.flash("Configuration saved successfully.", "success")
        return RedirectResponse(
            url=f"/admin/config/{category_name}/{namespace}",
            status_code=302,
        )
