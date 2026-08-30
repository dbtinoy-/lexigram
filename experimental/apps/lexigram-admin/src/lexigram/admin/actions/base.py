"""Action base classes for lexigram-admin.

.. stability:: stable

Defines the abstract Action hierarchy with RowAction, BulkAction,
and HeaderAction specializations. Each action is a frozen dataclass
with lifecycle hooks for visibility, authorization, confirmation,
and rendering.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from lexigram.admin.actions.exceptions import ActionError, PermissionDenied
from lexigram.admin.actions.types import ActionColor, ActionContext, ConfirmationConfig
from lexigram.result import Ok, Result

R = TypeVar("R")
Outcome = TypeVar("Outcome")


@dataclass(frozen=True, kw_only=True)
class Action(ABC, Generic[R, Outcome]):
    """Abstract base for all admin actions.

    Type parameters:
        R: The record type this action operates on.
        Outcome: The outcome type returned by execute().

    Attributes:
        name: Unique action identifier.
        label: Human-readable display text.
        icon: Optional icon identifier.
        color: Visual color variant for UI rendering.
        keyboard_shortcut: Optional keyboard shortcut (e.g. "Ctrl+E").
    """

    name: str
    label: str | None = None
    icon: str | None = None
    color: ActionColor = ActionColor.GRAY
    keyboard_shortcut: str | None = None

    @abstractmethod
    async def execute(
        self, record_or_records: R, ctx: ActionContext
    ) -> Result[Outcome, ActionError]:
        """Execute the action against the given record(s).

        Args:
            record_or_records: The target record (or list of records
                for BulkAction).
            ctx: Action execution context.

        Returns:
            Ok(outcome) on success, Err(action_error) on failure.
        """
        ...

    def visible_for(self, record: R, user: Any | None = None) -> bool:
        """Determine whether this action is visible for the given record.

        Override to implement visibility logic. Defaults to True.
        """
        return True

    def is_visible(
        self, user: Any = None, resource_name: str | None = None, record: Any = None
    ) -> bool:
        """Determine whether this action is visible in the current context.

        Compatibility accessor used by table/header rendering paths. Defaults
        to True; subclasses like HeaderAction override this directly.
        """
        return self.visible_for(record, user)

    def authorize(
        self, record: R, user: Any | None = None
    ) -> Result[None, PermissionDenied]:
        """Check whether the user is authorized to execute this action.

        Override to implement authorization logic. Defaults to Ok(None).
        """
        return Ok(None)

    def form(self) -> Any | None:
        """Return an optional form schema for parameter collection.

        Override to return a form definition that the UI will render
        before executing the action. Returns None by default.
        """
        return None

    def confirm(self) -> ConfirmationConfig | None:
        """Return optional confirmation dialog configuration.

        Override to return a ConfirmationConfig that the UI will
        display before executing the action. Returns None by default.
        """
        return None

    # -- Button rendering --

    def _color_to_variant(
        self,
    ) -> Literal["primary", "secondary", "danger", "ghost", "link"]:
        """Map ActionColor to ActionButton variant string."""
        mapping = {
            ActionColor.GRAY: "ghost",
            ActionColor.PRIMARY: "primary",
            ActionColor.SECONDARY: "secondary",
            ActionColor.SUCCESS: "secondary",
            ActionColor.WARNING: "warning",
            ActionColor.DANGER: "danger",
            ActionColor.INFO: "secondary",
        }
        return mapping[self.color]  # type: ignore[return-value]

    def _get_url(self, record: R, ctx: ActionContext) -> str | None:
        """Build the endpoint URL for this action.

        Override in subclasses to provide action-specific URL patterns.
        Returns None if the URL cannot be determined (button hidden).
        """
        return None

    def get_url(self, record: Any = None) -> str | None:
        """Public URL accessor used by table rendering paths.

        Delegates to _get_url with a minimal ActionContext when called
        from non-framework rendering paths.
        """
        return None

    def _get_htmx_attrs(
        self, url: str, record: R, ctx: ActionContext
    ) -> dict[str, str]:
        """Build HTMX attributes for the action button.

        Override in subclasses to customize HTMX behavior.
        """
        from lexigram.ui import Zones

        return {
            "hx-get": url,
            "hx-target": Zones.DATA.selector,
            "hx-swap": Zones.DATA.swap_mode.value,
        }

    def render_button(self, record: R, ctx: ActionContext) -> str:
        """Render the action as an HTML button string.

        Args:
            record: The target record context for rendering.
            ctx: Action context.

        Returns:
            HTML string for the button element, or empty string if
            the action is not visible or cannot be resolved.
        """
        if not self.visible_for(record, ctx.user):
            return ""

        url = self._get_url(record, ctx)
        if not url:
            return ""

        variant = self._color_to_variant()
        htmx_attrs = self._get_htmx_attrs(url, record, ctx)

        from lexigram.ui import ActionButton

        button = ActionButton(
            label=self.label or self.name,
            variant=variant,
            icon=self.icon,
            size="sm",
            **htmx_attrs,  # type: ignore[arg-type]
        )
        result = button.render()
        return str(result) if result else ""


class RowAction(Action[Any, Any]):
    """Action that operates on a single record.

    Example use: View, Edit, Delete, Duplicate for a table row.
    """

    @staticmethod
    def _get_record_id(record: Any) -> str:
        """Extract a record identifier from dict or object."""
        if record is None:
            return ""
        if isinstance(record, dict):
            return str(record.get("id", ""))
        if hasattr(record, "id"):
            return str(record.id)
        return ""

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/{self.name}"


class BulkAction(Action[list[Any], Any]):
    """Action that operates on multiple records at once.

    Example use: Bulk delete, bulk status change, bulk assign.

    When *task_runner* is set and the record count equals or exceeds the
    configured ``bulk_threshold`` (from ``TasksIntegrationConfig``), execution
    is dispatched through the tasks integration instead of running inline.
    """

    task_runner: str | None = None
    """Name of the task runner to use when dispatching via lexigram-tasks."""

    def _get_url(self, records: list[Any], ctx: ActionContext) -> str | None:
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/bulk/{self.name}"

    def _get_htmx_attrs(
        self,
        url: str,
        records: list[Any],
        ctx: ActionContext,
    ) -> dict[str, str]:
        """Submit through the mounted generic bulk route.

        Bulk routes are registered at ``/{resource}/bulk`` and dispatch the
        action from the request's ``action`` value; the action-specific URL
        returned by ``_get_url`` is not a mounted route.
        """
        from lexigram.ui import HTMXAttrs

        confirmation = self.confirm()
        confirm_message = (
            confirmation.message or confirmation.title
            if confirmation is not None
            else None
        )
        if confirm_message is None and getattr(self, "_requires_confirmation", False):
            confirm_message = getattr(self, "_confirmation_message", None) or getattr(
                self, "_confirmation_title", None
            )
        return HTMXAttrs.for_bulk_action(
            url=url,
            method="POST",
            action_name=self.name,
            confirm_message=confirm_message,
        )


class HeaderAction(Action[None, Any]):
    """Action with no record context, rendered in header areas.

    Example use: Export all, settings, global create.
    """

    def _get_url(self, record: None, ctx: ActionContext) -> str | None:
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{self.name}"


__all__ = [
    "Action",
    "BulkAction",
    "HeaderAction",
    "RowAction",
]
