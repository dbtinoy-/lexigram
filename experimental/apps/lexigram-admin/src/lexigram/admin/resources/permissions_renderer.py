"""Renderer for the per-user permission editing page.

Serves the direct-permission editor for admin users (the page the legacy
RbacController served at ``/admin/users/{id}/permissions``) through the
Resource handler path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse

from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.admin.rbac.inventory import PermissionInventoryService


def _checkbox(perm: str, checked: bool) -> Any:
    """Build a single permission checkbox input."""
    return el(
        "input",
        type="checkbox",
        name="permissions",
        value=perm,
        checked=checked or None,
        class_="h-4 w-4 rounded border-input text-primary focus:ring-ring bg-background",
    )


class UserPermissionsRenderer:
    """Render the grouped user permission checkboxes inside the admin shell.

    Attributes:
        resource_name: The admin resource name (``users``).
        renderer: The engine renderer used to wrap content in the admin
            shell; overridable for tests.
    """

    def __init__(self, resource_name: str, engine_renderer: Any | None = None) -> None:
        """Initialize the renderer.

        Args:
            resource_name: The admin resource name (``users``).
            engine_renderer: Optional engine renderer; a fresh
                :class:`~lexigram.admin.engine.renderer.AdminRenderer` is
                built when omitted.
        """
        self.resource_name = resource_name
        if engine_renderer is None:
            from lexigram.admin.engine.renderer import (
                AdminRenderer as EngineAdminRenderer,
            )

            engine_renderer = EngineAdminRenderer()
        self._renderer = engine_renderer

    def render_form(
        self,
        request: Any,
        user: Any,
        inventory: PermissionInventoryService,
        item_id: str,
        prefix: str,
    ) -> HTMLResponse:
        """Render the permissions form as a full admin page.

        Args:
            request: The current request (carries the CSRF token in
                ``request.state``).
            user: The admin user being edited (must not be ``None``).
            inventory: Grouped permission inventory ``{resource: [perm]}``.
            item_id: The user id from the URL path.
            prefix: Admin resource prefix (``admin/users``).

        Returns:
            A full-page HTMLResponse wrapped in the admin shell.
        """
        options = inventory.options() or {}
        selected = set(getattr(user, "permissions", None) or [])
        all_options = {p for perms in options.values() for p in perms}
        preserved = [
            el("input", type="hidden", name="permissions", value=perm)
            for perm in sorted(selected - all_options)
        ]

        groups = [
            el(
                "fieldset",
                el("legend", perm_name, class_="font-semibold text-foreground"),
                *[_checkbox(perm, perm in selected) for perm in perms],
                class_="mb-5 border rounded-lg p-4",
            )
            for perm_name, perms in options.items()
        ]

        user_label = (
            f"{getattr(user, 'name', '')} <{getattr(user, 'email', '')}>"
            if user is not None
            else "unknown user"
        )

        form = el(
            "form",
            el(
                "input",
                type="hidden",
                name="csrf_token",
                value=getattr(request.state, "csrf_token", ""),
            ),
            *preserved,
            el("p", user_label, class_="mb-4 text-sm text-foreground"),
            *groups,
            el(
                "button",
                "Save Permissions",
                type="submit",
                class_="mt-4 inline-flex items-center rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90",
            ),
            method="post",
            action=f"/admin/{prefix}/{item_id}/permissions",
        )

        content = el(
            "div",
            el(
                "h1",
                "Edit Permissions",
                class_="text-2xl font-bold text-foreground mb-4",
            ),
            form,
            class_="resource-content bg-card shadow rounded-lg p-6",
        )

        return self._renderer.render_page(
            content,
            request=request,
            title="User Permissions",
            breadcrumbs=[
                {"label": "Dashboard", "url": f"/admin/{prefix}"},
                {"label": "Users", "url": f"/admin/{prefix}"},
                {
                    "label": user_label,
                    "url": f"/admin/{prefix}/{item_id}/permissions",
                },
            ],
        )
