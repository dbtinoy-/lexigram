"""Ready-to-use row actions (edit, view, delete, clone, restore, purge).

Part of the ``lexigram.admin.actions.standard`` package.
"""

from __future__ import annotations

import inspect
from typing import Any

from lexigram.admin.actions.base import RowAction
from lexigram.admin.actions.standard.utils import _extract_id, _resolve_data_source
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
    ConfirmationConfig,
)
from lexigram.ui import Zones
from lexigram.result import Err, Ok, Result


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


class PermissionsAction(RowAction):
    """Edit a user's direct permissions (users resource only)."""

    def __init__(
        self,
        name: str = "permissions",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Edit Permissions",
            icon="shield",
            color=ActionColor.GRAY,
        )

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/permissions"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Editing permissions for {record}"})


class ImpersonateAction(RowAction):
    """Impersonate a user's session (users resource only).

    Target-role restriction (denying impersonation of another
    super-admin) is enforced server-side only — this action has no
    access to DI/config at render time (``Action`` is a frozen,
    import-time-constructed dataclass), and the row's rendered fields
    don't expose RBAC role membership. See
    ``docs/superpowers/specs/2026-08-19-admin-impersonation-usability-design.md``
    D5 for the full reasoning.
    """

    def __init__(
        self,
        name: str = "impersonate",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Impersonate",
            icon="user-check",
            color=ActionColor.GRAY,
        )

    def visible_for(self, record: Any, user: Any | None = None) -> bool:
        if user is None:
            return True
        record_id = self._get_record_id(record)
        actor_id = str(getattr(user, "id", ""))
        return record_id != actor_id

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        return f"/admin/impersonate/{record_id}"

    def _get_htmx_attrs(
        self, url: str, record: Any, ctx: ActionContext
    ) -> dict[str, str]:
        name = (
            record.get("name", "this user") if isinstance(record, dict) else "this user"
        )
        return {
            "hx-post": url,
            "hx-target": "body",
            "hx-swap": "none",
            "hx-confirm": f"Impersonate {name}?",
        }

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": f"Impersonating {record}"})


class CloneAction(RowAction):
    """Clone a single record through the data source.

    Mirrors Filament's ``Replicate`` action: ``exclude_attributes`` drops
    fields from the copy (``excludeAttributes``), ``mutate_record_data``
    transforms the record data before creation (``mutateRecordDataUsing``),
    and ``before_replica_saved`` runs just before the new record is
    persisted (``beforeReplicaSaved``). The ``id`` field is always stripped
    so a fresh identifier is assigned.
    """

    def __init__(
        self,
        name: str = "clone",
        label: str | None = None,
        data_source: Any | None = None,
        exclude_attributes: list[str] | None = None,
        mutate_record_data: Callable[
            [dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]
        ]
        | None = None,
        before_replica_saved: Callable[[dict[str, Any]], None | Awaitable[None]]
        | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Clone",
            icon="copy",
            color=ActionColor.SECONDARY,
        )
        self._data_source = data_source
        self._exclude_attributes = exclude_attributes or []
        self._mutate_record_data = mutate_record_data
        self._before_replica_saved = before_replica_saved

    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        record_id = self._get_record_id(record)
        if not record_id:
            return None
        prefix = ctx.resource_prefix or f"/{ctx.resource_name}"
        return f"{prefix}/{record_id}/clone"

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        record_id = _extract_id(record)
        if record_id is None:
            return Err(ActionError("Clone requires a record with an id."))
        data_source = _resolve_data_source(ctx, self._data_source)
        if data_source is None:
            return Err(
                ActionError(
                    "Clone requires a data source; inject one or set ctx.data_source."
                )
            )
        original = await data_source.find_one(record_id)
        if original is None:
            return Err(ActionError(f"Record {record_id} not found."))
        data: dict[str, Any] = dict(original) if isinstance(original, dict) else {}
        if not data and hasattr(original, "__dict__"):
            data = dict(vars(original))
        data.pop("id", None)
        for attribute in self._exclude_attributes:
            data.pop(attribute, None)
        if self._mutate_record_data is not None:
            mutated = self._mutate_record_data(data)
            data = await mutated if inspect.isawaitable(mutated) else mutated
        if self._before_replica_saved is not None:
            hook = self._before_replica_saved(data)
            if inspect.isawaitable(hook):
                await hook
        created = await data_source.create(data)
        if created is None:
            return Err(ActionError(f"Failed to clone record {record_id}."))
        return Ok(
            {
                "message": "Cloned record",
                "record": created,
                "cloned_id": _extract_id(created),
            }
        )


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
