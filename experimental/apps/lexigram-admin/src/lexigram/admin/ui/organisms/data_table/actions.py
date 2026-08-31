"""Action configuration and management for data table component."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup

from lexigram.admin.actions.standard import (
    CreateAction,
    DeleteAction,
    DeleteBulkAction,
    EditAction,
    ViewAction,
)
from lexigram.admin.actions.types import ActionColor, ActionContext
from lexigram.admin.config import TableConfiguration
from lexigram.ui import Action as OldActionBase

OLD_ACTION_TYPES = (OldActionBase,)


@dataclass
class ActionDescriptor:
    """Normalized action descriptor used for rendering both old and new actions."""

    label: str
    name: str
    icon: str | None = None
    color: str = "primary"
    visible: bool = True
    url: str | None = None
    hx_get: str | None = None
    hx_post: str | None = None
    hx_delete: str | None = None
    hx_target: str | None = None
    hx_swap: str | None = "innerHTML"
    hx_confirm: str | None = None
    hx_include: str | None = None
    is_bulk: bool = False
    variant: str = field(default="ghost")


def _normalize_old_action(action: Any) -> ActionDescriptor:
    """Normalize a deprecated ui.actions action into ActionDescriptor."""
    hx_method = "GET"
    hx_url = getattr(action, "_hx_get", None)
    if hx_url:
        hx_method = "GET"
    elif getattr(action, "_hx_post", None):
        hx_url = action._hx_post
        hx_method = "POST"
    elif getattr(action, "_hx_delete", None):
        hx_url = action._hx_delete
        hx_method = "DELETE"

    confirm = None
    if getattr(action, "_requires_confirmation", False):
        confirm = getattr(action, "_confirmation_message", None) or getattr(
            action, "_confirmation_title", None
        )

    hx_swap = getattr(action, "_hx_swap", "innerHTML")
    hx_target = getattr(action, "_hx_target", None)

    url = None
    if hasattr(action, "get_url"):
        url = action.get_url()

    base_variant = {
        "primary": "primary",
        "danger": "danger",
        "gray": "ghost",
        "success": "secondary",
    }.get(getattr(action, "_color", "primary"), "ghost")

    return ActionDescriptor(
        label=action.label,
        name=action.name,
        icon=getattr(action, "_icon", None),
        color=getattr(action, "_color", "primary"),
        visible=getattr(action, "_visible", True)
        and (not hasattr(action, "is_visible") or action.is_visible()),
        url=url,
        hx_get=hx_url if hx_method == "GET" else None,
        hx_post=hx_url if hx_method == "POST" else None,
        hx_delete=hx_url if hx_method == "DELETE" else None,
        hx_target=hx_target,
        hx_swap=hx_swap,
        hx_confirm=confirm,
        is_bulk=hasattr(action, "_deselect_after"),
        variant=base_variant if not hx_target else "ghost",
    )


def _normalize_new_action(action: Any) -> ActionDescriptor:
    """Normalize a new lexigram.admin.actions action into ActionDescriptor."""
    color_map = {
        ActionColor.GRAY: "gray",
        ActionColor.PRIMARY: "primary",
        ActionColor.SECONDARY: "secondary",
        ActionColor.SUCCESS: "success",
        ActionColor.WARNING: "warning",
        ActionColor.DANGER: "danger",
        ActionColor.INFO: "info",
    }
    action_color = getattr(action, "color", ActionColor.GRAY)
    color_str = color_map.get(action_color, "gray")

    confirm = None
    if hasattr(action, "confirm"):
        cfg = action.confirm()
        if cfg and cfg.message:
            confirm = cfg.message
        elif cfg:
            confirm = cfg.title

    is_bulk = hasattr(action, "task_runner") or "BulkAction" in type(action).__name__

    # URL builders require a real ActionContext. Normalization is also used
    # by tooling where no record exists, so leave row URLs unresolved rather
    # than invoking them with ``None`` and risking a runtime error.
    url = None
    if hasattr(action, "_get_url") and not is_bulk:
        try:
            url = action._get_url(
                None,
                ActionContext(resource_name="", resource_prefix=""),
            )
        except (AttributeError, TypeError, ValueError):
            url = None

    return ActionDescriptor(
        label=action.label or action.name,
        name=action.name,
        icon=action.icon,
        color=color_str,
        url=url,
        hx_confirm=confirm,
        is_bulk=is_bulk,
        variant="ghost",
    )


def normalize_action(action: Any) -> ActionDescriptor:
    """Normalize any action (old or new API) into ActionDescriptor."""
    if isinstance(action, OldActionBase):
        return _normalize_old_action(action)
    return _normalize_new_action(action)


def _adapt_legacy_form_action(action: Any, form_display_mode: str | None) -> Any:
    """Adapt legacy create/edit actions to the resource form mode.

    Legacy actions store HTMX target state on mutable private attributes. Work
    on a copy so a resource declaration remains safe to reuse across requests.
    """
    if form_display_mode not in {"page", "modal", "slider"}:
        return action
    if str(getattr(action, "name", "")).lower() not in {"create", "edit"}:
        return action

    from copy import copy

    from lexigram.ui import Zones

    adapted = copy(action)
    hx_url = getattr(adapted, "_hx_get", None)
    if form_display_mode == "page":
        if hx_url:
            adapted._url = hx_url
            adapted._hx_get = None
            adapted._hx_target = None
            adapted._hx_swap = None
            adapted._hx_push_url = None
        return adapted

    zone = Zones.MODAL if form_display_mode == "modal" else Zones.SLIDE_OVER
    adapted._hx_target = zone.selector
    adapted._hx_swap = zone.swap_mode.value
    adapted._hx_push_url = "false"
    return adapted


def render_action_button(
    action: Any,
    record: dict | Any | None = None,
    user: Any = None,
    resource_name: str | None = None,
    resource_prefix: str | None = None,
    form_display_mode: str | None = None,
) -> Any:
    """Render any action (old or new API) as a button element.

    Handles both old ui.actions and new lexigram.admin.actions.
    """
    if isinstance(action, OldActionBase):
        action = _adapt_legacy_form_action(action, form_display_mode)
        return action.render(record=record, user=user, resource_name=resource_name)

    metadata = {}
    if form_display_mode:
        metadata["form_display_mode"] = form_display_mode
    ctx = ActionContext(
        user=user,
        resource_name=resource_name or "",
        resource_prefix=resource_prefix or f"/{resource_name}" if resource_name else "",
        metadata=metadata,
    )
    rendered = action.render_button(record=record, ctx=ctx)
    # New admin actions return an HTML string for compatibility. Mark it safe
    # only after it was produced by ActionButton; otherwise Element would
    # escape the complete button when it is nested in a row container.
    return Markup(rendered) if rendered else ""


def render_bulk_action_button(
    action: Any,
    *,
    resource_name: str | None = None,
    resource_prefix: str | None = None,
) -> Any:
    """Render a bulk action (old or new API) as a button element.

    Handles the deprecated private-field access pattern for bulk actions.
    """
    action_name = str(getattr(action, "name", ""))
    if action_name in {"export", "export_csv"}:
        export_url = f"{(resource_prefix or '').rstrip('/')}/bulk"
        from lexigram.ui import ActionButton

        label = getattr(action, "label", None) or action_name
        icon = getattr(action, "icon", None)
        if not isinstance(icon, str):
            icon = getattr(action, "_icon", None)
        if hasattr(action, "_color_to_variant"):
            variant = action._color_to_variant()
        else:
            raw_color = getattr(action, "_color", "secondary")
            variant = (
                raw_color
                if raw_color in ("primary", "secondary", "danger", "ghost")
                else "secondary"
            )
        return ActionButton(
            label=label,
            color=variant,
            icon=icon,
            size="md",
            type="button",
            data_bulk_download_url=export_url,
            data_bulk_action=action_name,
            onclick="return window.LexigramDownloadBulk(this);",
        ).render()

    if not isinstance(action, OLD_ACTION_TYPES):
        # New admin bulk actions use the canonical ActionContext/HTMX
        # protocol. Keep this helper compatible with the toolbar path so
        # alternate renderers do not silently drop custom bulk actions.
        if not hasattr(action, "_get_url"):
            return ""

        ctx = ActionContext(
            resource_name=resource_name or "",
            resource_prefix=resource_prefix or f"/{resource_name}"
            if resource_name
            else "",
        )
        # The generic resource bulk route receives the action name in
        # ``hx-vals``. BulkAction._get_url() is an action-specific convention
        # (for example ``/bulk/delete``) and is not the route registered by
        # ResourceHandler, so use the canonical ``/bulk`` endpoint here.
        url = f"{ctx.resource_prefix.rstrip('/')}/bulk"
        attrs = action._get_htmx_attrs(url, [], ctx)
        from lexigram.serialization import dumps_str

        attrs["hx-vals"] = dumps_str({"action": getattr(action, "name", "")})
        from lexigram.ui import ActionButton

        rendered = ActionButton(
            label=getattr(action, "label", None) or getattr(action, "name", ""),
            variant=action._color_to_variant(),
            icon=getattr(action, "icon", None),
            size="md",
            type="button",
            **attrs,
        ).render()
        return Markup(str(rendered)) if rendered else ""

    attrs = {}
    _hx_delete = getattr(action, "_hx_delete", None)
    _hx_post = getattr(action, "_hx_post", None)
    _requires_confirmation = getattr(action, "_requires_confirmation", False)
    _confirmation_message = getattr(action, "_confirmation_message", None)
    _confirmation_title = getattr(action, "_confirmation_title", None)
    _hx_target = getattr(action, "_hx_target", None)
    _color = getattr(action, "_color", None)
    _action_name = getattr(action, "name", "")

    from lexigram.ui import HTMXAttrs

    _method = "DELETE" if _hx_delete else "POST"
    _url = (
        _hx_delete
        or _hx_post
        or (f"{(resource_prefix or '').rstrip('/')}/bulk" if resource_prefix else "")
    )

    bulk_attrs = HTMXAttrs.for_bulk_action(
        url=_url,
        method=_method,
        confirm_message=_confirmation_message or _confirmation_title,
        action_name=_action_name,
    )
    attrs.update(bulk_attrs)

    variant = (
        _color if _color in ("primary", "secondary", "danger", "ghost") else "primary"
    )

    from lexigram.ui import ActionButton

    btn = ActionButton(
        label=action.label,
        color=variant,
        size="md",
        type="button",
        **attrs,  # type: ignore[arg-type]
    )
    return btn.render()


class ActionManager:
    """Manages actions configuration for data table."""

    def __init__(self, config: TableConfiguration, permissions: dict[str, bool]):
        self.config = config
        self.permissions = permissions

    def configure_actions(self) -> None:
        """Configure actions based on permissions and configuration.

        The manager runs against a render-local configuration. It still keeps
        the filtering here, rather than relying on CSS/HTMX visibility, so a
        denied CRUD action is not emitted into the page at all.
        """
        if not self.config.resource_prefix:
            return

        # Fill in missing URLs for existing standard actions
        self._configure_existing_actions()
        self._filter_declared_actions()

        # Add default actions if none provided
        self._add_default_actions()

    def _required_permission(self, action: Any) -> str | None:
        """Return the CRUD permission implied by a standard action name.

        Custom actions are deliberately not guessed: their server-side
        ``authorize`` implementation remains the source of truth.
        """
        name = str(getattr(action, "name", "")).lower().replace("-", "_")
        if name in {"view", "read", "show"}:
            return "can_view"
        if name in {"create", "import"}:
            return "can_create"
        if name in {"edit", "update"}:
            return "can_update"
        if name in {"delete", "destroy", "purge"}:
            return "can_delete"
        if name == "restore":
            return "can_update"
        return None

    def _is_allowed(self, action: Any) -> bool:
        permission = self._required_permission(action)
        return permission is None or self.permissions.get(permission, False)

    def _filter_declared_actions(self) -> None:
        """Remove known-denied actions from the render-local collections."""
        self.config.actions = [
            action for action in self.config.actions if self._is_allowed(action)
        ]
        self.config.header_actions = [
            action for action in self.config.header_actions if self._is_allowed(action)
        ]
        self.config.bulk_actions = [
            action for action in self.config.bulk_actions if self._is_allowed(action)
        ]

    def _configure_existing_actions(self) -> None:
        """Configure URLs for existing standard actions."""
        # Note: New standard actions compute their URLs dynamically via ctx.resource_name,
        # so we don't need to inject `_hx_get` or similar manually here unless they
        # are explicitly OldActionBase.

    def _add_default_actions(self) -> None:
        """Add default actions if none are configured."""
        if not self.permissions.get("can_view", True):
            return

        if not self.config.actions:
            if self.permissions.get("can_view", True):
                self.config.actions.append(ViewAction(label=""))

            if self.permissions.get("can_update", False):
                self.config.actions.append(EditAction(label=""))

            if self.permissions.get("can_delete", False):
                self.config.actions.append(DeleteAction(label=""))

        if not self.config.header_actions and self.permissions.get("can_create", False):
            self.config.header_actions.append(CreateAction(label="Create New"))

        if not self.config.bulk_actions and self.permissions.get("can_delete", False):
            self.config.bulk_actions.append(DeleteBulkAction(label="Delete Selected"))
