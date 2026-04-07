"""Standard action implementations for lexigram-admin.

Provides ready-to-use RowAction, BulkAction, and HeaderAction subclasses
that wrap common data-source operations such as edit, view, delete, create,
and bulk delete. Each action comes with sensible defaults for name, label,
icon, and color.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.base import BulkAction, HeaderAction, RowAction
from lexigram.admin.actions.types import ActionColor, ActionContext, ConfirmationConfig
from lexigram.result import Ok, Result
from lexigram.ui import Zones


class EditAction(RowAction):
    """Edit a single record."""

    def __init__(
        self,
        name: str = "edit",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Edit",
            icon="pencil",
            color=ActionColor.PRIMARY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/edit"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
        }

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Edited {record}"})


class ViewAction(RowAction):
    """View a single record."""

    def __init__(
        self,
        name: str = "view",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "View",
            icon="eye",
            color=ActionColor.GRAY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Viewed {record}"})


class DeleteAction(RowAction):
    """Delete a single record with confirmation."""

    def __init__(
        self,
        name: str = "delete",
        label: str | None = None,
        confirm_title: str = "Delete Record",
        confirm_message: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Delete",
            icon="trash",
            color=ActionColor.DANGER,
        )
        self._confirm_title = confirm_title
        self._confirm_message = confirm_message or (
            "Are you sure you want to delete this record? This action cannot be undone."
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/delete-confirm"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
            "hx-push-url": "false",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title=self._confirm_title,
            message=self._confirm_message,
            style=ActionColor.DANGER,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Deleted {record}", "deleted": True})


class CreateAction(HeaderAction):
    """Create a new record."""

    def __init__(
        self,
        name: str = "create",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Create",
            icon="plus",
            color=ActionColor.PRIMARY,
        )

    def _get_htmx_attrs(
        self, url: str, record: None, ctx: ActionContext
    ) -> dict[str, str]:
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
        }

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": "Created new record"})


class DeleteBulkAction(BulkAction):
    """Delete multiple selected records."""

    def __init__(
        self,
        name: str = "delete",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Delete Selected",
            icon="trash",
            color=ActionColor.DANGER,
        )

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk delete confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-delete-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Delete Selected Records",
            message="Are you sure you want to delete the selected records? "
            "This action cannot be undone.",
            style=ActionColor.DANGER,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        count = len(records)
        return Ok({"message": f"Deleted {count} record(s)", "deleted_count": count})


class CloneAction(RowAction):
    """Clone a single record."""

    def __init__(
        self,
        name: str = "clone",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Clone",
            icon="copy",
            color=ActionColor.SECONDARY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/clone"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Cloned {record}"})


class RestoreAction(RowAction):
    """Restore a single soft-deleted record."""

    def __init__(
        self,
        name: str = "restore",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Restore",
            icon="rotate-ccw",
            color=ActionColor.SUCCESS,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/restore"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Restored {record}"})


class PurgeAction(RowAction):
    """Permanently delete a soft-deleted record."""

    def __init__(
        self,
        name: str = "purge",
        label: str | None = None,
        confirm_title: str = "Permanently Delete Record",
        confirm_message: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Purge",
            icon="trash-2",
            color=ActionColor.DANGER,
        )
        self._confirm_title = confirm_title
        self._confirm_message = confirm_message or (
            "Are you sure you want to permanently delete this record? "
            "This action cannot be undone."
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/purge"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        attrs: dict[str, str] = {
            "hx-delete": url,
            "hx-target": "#table-data",
            "hx-swap": "innerHTML",
        }
        confirmation = self.confirm()
        if confirmation and confirmation.message:
            attrs["hx-confirm"] = confirmation.message
        return attrs

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title=self._confirm_title,
            message=self._confirm_message,
            style=ActionColor.DANGER,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Purged {record}", "purged": True})


class ExportAction(RowAction):
    """Export a single record."""

    def __init__(
        self,
        name: str = "export",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Export",
            icon="download",
            color=ActionColor.GRAY,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Exported {record}"})


class ExportBulkAction(BulkAction):
    """Export multiple selected records."""

    def __init__(
        self,
        name: str = "export",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Export Selected",
            icon="download",
            color=ActionColor.GRAY,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        count = len(records)
        return Ok({"message": f"Exported {count} record(s)", "exported_count": count})


__all__ = [
    "CloneAction",
    "CreateAction",
    "DeleteAction",
    "DeleteBulkAction",
    "EditAction",
    "ExportAction",
    "ExportBulkAction",
    "PurgeAction",
    "RestoreAction",
    "ViewAction",
]
