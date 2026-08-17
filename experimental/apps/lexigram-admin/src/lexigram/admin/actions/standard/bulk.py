"""Ready-to-use bulk actions (delete, purge, restore).

Part of the ``lexigram.admin.actions.standard`` package.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.base import BulkAction
from lexigram.admin.actions.standard.utils import _extract_id, _resolve_data_source
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
    ConfirmationConfig,
)
from lexigram.result import Err, Ok, Result
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
class PurgeBulkAction(BulkAction):
    """Permanently delete multiple selected records.

    Deletes are issued in chunks via the data source's ``bulk_delete``,
    mirroring Filament's ``chunkSelectedRecords`` behaviour for large
    selections.
    """

    def __init__(
        self,
        name: str = "purge",
        label: str | None = None,
        data_source: Any | None = None,
        chunk_size: int = 200,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Purge Selected",
            icon="trash-2",
            color=ActionColor.DANGER,
        )
        self._data_source = data_source
        self._chunk_size = chunk_size

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk purge confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-purge-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Purge Selected Records",
            message="Are you sure you want to permanently purge the selected "
            "records? This action cannot be undone.",
            style=ActionColor.DANGER,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Purge requires a data source; inject one or set ctx.data_source."
                )
            )
        ids = [
            item_id
            for record in records
            if (item_id := _extract_id(record)) is not None
        ]
        chunk_size = self._chunk_size or len(ids) or 1
        purged = 0
        for start in range(0, len(ids), chunk_size):
            purged += await data_source.bulk_delete(ids[start : start + chunk_size])
        return Ok({"message": f"Purged {purged} record(s)", "purged_count": purged})
class RestoreBulkAction(BulkAction):
    """Restore multiple soft-deleted records."""

    def __init__(
        self,
        name: str = "restore",
        label: str | None = None,
        data_source: Any | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Restore Selected",
            icon="rotate-ccw",
            color=ActionColor.SUCCESS,
        )
        self._data_source = data_source

    def _get_htmx_attrs(
        self, url: str, records: list[Any], ctx: ActionContext
    ) -> dict[str, str]:
        # Open bulk restore confirmation slide-over instead of native hx-confirm
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        confirm_url = f"{prefix}/bulk-restore-confirm"
        return {
            "hx-get": confirm_url,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Restore Selected Records",
            message="Are you sure you want to restore the selected records?",
            style=ActionColor.SUCCESS,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Restore requires a data source; inject one or set ctx.data_source."
                )
            )
        ids = [
            item_id
            for record in records
            if (item_id := _extract_id(record)) is not None
        ]
        restored = 0
        for item_id in ids:
            updated = await data_source.update(item_id, {"deleted_at": None})
            if updated is not None:
                restored += 1
        return Ok(
            {"message": f"Restored {restored} record(s)", "restored_count": restored}
        )
