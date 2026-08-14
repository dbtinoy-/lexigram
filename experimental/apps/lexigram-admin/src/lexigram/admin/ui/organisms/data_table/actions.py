"""Action configuration and management for data table component."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.admin.actions.standard import (
    CreateAction,
    DeleteAction,
    DeleteBulkAction,
    EditAction,
    ViewAction,
)
from lexigram.admin.actions.types import ActionColor
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

    return ActionDescriptor(
        label=action.label or action.name,
        name=action.name,
        icon=action.icon,
        color=color_str,
        url=action._get_url(None, None) if hasattr(action, "_get_url") else None,
        hx_confirm=confirm,
        is_bulk=is_bulk,
        variant="ghost",
    )


def normalize_action(action: Any) -> ActionDescriptor:
    """Normalize any action (old or new API) into ActionDescriptor."""
    if isinstance(action, OldActionBase):
        return _normalize_old_action(action)
    return _normalize_new_action(action)


def render_action_button(
    action: Any,
    record: dict | Any | None = None,
    user: Any = None,
    resource_name: str | None = None,
    resource_prefix: str | None = None,
) -> Any:
    """Render any action (old or new API) as a button element.

    Handles both old ui.actions and new lexigram.admin.actions.
    """
    if isinstance(action, OldActionBase):
        return action.render(record=record, user=user, resource_name=resource_name)

    from lexigram.admin.actions.types import ActionContext

    ctx = ActionContext(
        user=user,
        resource_name=resource_name or "",
        resource_prefix=resource_prefix or f"/{resource_name}" if resource_name else "",
    )
    return action.render_button(record=record, ctx=ctx)


def render_bulk_action_button(action: Any) -> Any:
    """Render a bulk action (old or new API) as a button element.

    Handles the deprecated private-field access pattern for bulk actions.
    """
    if not isinstance(action, OLD_ACTION_TYPES):
        return ""

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
    _url = _hx_delete or _hx_post or ""

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
        """Configure actions based on permissions and configuration."""
        if not self.config.resource_prefix:
            return

        # Fill in missing URLs for existing standard actions
        self._configure_existing_actions()

        # Add default actions if none provided
        self._add_default_actions()

    def _configure_existing_actions(self) -> None:
        """Configure URLs for existing standard actions."""
        # Note: New standard actions compute their URLs dynamically via ctx.resource_name,
        # so we don't need to inject `_hx_get` or similar manually here unless they
        # are explicitly OldActionBase.

    def _add_default_actions(self) -> None:
        """Add default actions if none are configured."""
        if not self.config.actions:
            if self.permissions.get("can_view", True):
                self.config.actions.append(ViewAction(label=""))

            if self.permissions["can_update"]:
                self.config.actions.append(EditAction(label=""))

            if self.permissions["can_delete"]:
                self.config.actions.append(DeleteAction(label=""))

        if not self.config.header_actions and self.permissions["can_create"]:
            self.config.header_actions.append(CreateAction(label="Create New"))

        if not self.config.bulk_actions and self.permissions["can_delete"]:
            self.config.bulk_actions.append(DeleteBulkAction(label="Delete Selected"))
