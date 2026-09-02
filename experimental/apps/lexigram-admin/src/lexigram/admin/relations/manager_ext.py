"""Extended relation manager with inline editing support.

.. experimental::
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.relations.manager import AbstractRelationManager
from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url
from lexigram.result import Ok, Result
from lexigram.ui import el, render_to_string


class RelationManager(AbstractRelationManager):
    """Relation manager with inline create/edit/delete support.

    Extends AbstractRelationManager with inline editing methods,
    permission predicates, and HTMX route handlers.

    Example:
        class UserPetsRelationManager(RelationManager):
            relationship_name = "pets"

            @classmethod
            def table(cls, table_config=None):
                return []

            async def get_query(self):
                return []
    """

    # Inline editing policy
    inline_create: bool = True
    inline_edit: bool = True
    inline_delete: bool = True
    inline_detach: bool = False

    def create_form(self) -> str | None:
        """Return the HTML for a create form.

        Override to provide a custom form. Returns None by default.
        """
        return None

    def edit_form(self, record: Any) -> str | None:
        """Return the HTML for an edit form pre-filled with the given record.

        Override to provide a custom form. Returns None by default.
        """
        return None

    def can_create(
        self, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        """Check whether the user can create related records."""
        return Ok(None)

    def can_edit(
        self, record: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        """Check whether the user can edit the given related record."""
        return Ok(None)

    def can_delete(
        self, record: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        """Check whether the user can delete the given related record."""
        return Ok(None)

    def can_detach(
        self, record: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        """Check whether the user can detach the given related record."""
        return Ok(None)

    async def create_record(self, data: dict[str, Any]) -> Any:
        """Persist a new related record (B32).

        Default: delegate to the attached data source's ``create``.
        Override for custom persistence.

        Args:
            data: Submitted form data (``csrf_token`` already stripped).

        Returns:
            The created record.

        Raises:
            NotImplementedError: When no persistence is available.
        """
        data_source = self._data_source
        if data_source is not None and hasattr(data_source, "create"):
            return await data_source.create(dict(data))
        raise NotImplementedError(
            "Inline create is not supported for this relation; attach a data "
            "source or override create_record()."
        )

    async def update_record(self, record_id: str, data: dict[str, Any]) -> Any:
        """Persist changes to a related record (B32).

        Default: delegate to the attached data source's ``update``.

        Args:
            record_id: ID of the related record.
            data: Submitted form data (``csrf_token`` already stripped).

        Returns:
            The updated record.

        Raises:
            NotImplementedError: When no persistence is available.
        """
        data_source = self._data_source
        if data_source is not None and hasattr(data_source, "update"):
            return await data_source.update(record_id, dict(data))
        raise NotImplementedError(
            "Inline update is not supported for this relation; attach a data "
            "source or override update_record()."
        )

    async def delete_record(self, record_id: str) -> Any:
        """Delete a related record (B32).

        Default: delegate to the attached data source's ``delete`` (or
        ``bulk_delete`` fallback).

        Args:
            record_id: ID of the related record.

        Raises:
            NotImplementedError: When no persistence is available.
        """
        data_source = self._data_source
        if data_source is not None:
            if hasattr(data_source, "delete"):
                return await data_source.delete(record_id)
            if hasattr(data_source, "bulk_delete"):
                return await data_source.bulk_delete([record_id])
        raise NotImplementedError(
            "Inline delete is not supported for this relation; attach a data "
            "source or override delete_record()."
        )

    async def render(self, request: Any, resource_name: str = "") -> str:
        """Render the relation panel as HTML."""
        items = await self.get_query()
        rel_name = self.get_relationship_name()
        parent_id = self.parent_id
        admin_prefix = admin_prefix_from_request(request)

        rows: list[Any] = []
        for item in items:
            # B26: dict-aware row access — SQL data sources return dicts.
            raw_id = self._row_id(item)
            item_id = str(raw_id) if raw_id is not None else str(id(item))
            cells: list[Any] = []
            cols = self.table()
            if cols:
                for col in cols:
                    value = (
                        self._row_value(item, col.name) if hasattr(col, "name") else ""
                    )
                    cells.append(el("td", "" if value is None else value))
            else:
                cells.append(el("td", item))

            actions: list[Any] = []
            if self.inline_edit:
                edit_url = admin_url(
                    admin_prefix,
                    resource_name,
                    f"{parent_id}/relations/{rel_name}/{item_id}/edit",
                )
                actions.append(
                    el(
                        "a",
                        "Edit",
                        href=edit_url,
                        hx_get=edit_url,
                        hx_target="closest tr",
                        hx_swap="outerHTML",
                    )
                )
                actions.append(" ")
            if self.inline_delete:
                delete_url = admin_url(
                    admin_prefix,
                    resource_name,
                    f"{parent_id}/relations/{rel_name}/{item_id}",
                )
                actions.append(
                    el(
                        "a",
                        "Delete",
                        href=delete_url,
                        hx_delete=delete_url,
                        hx_confirm="Delete this record?",
                        hx_target="closest tr",
                        hx_swap="outerHTML",
                    )
                )
            if actions:
                cells.append(el("td", *actions))

            rows.append(el("tr", *cells))

        header: list[Any] = []
        if self.inline_create:
            create_url = admin_url(
                admin_prefix,
                resource_name,
                f"{parent_id}/relations/{rel_name}/new",
            )
            header.append(
                el(
                    "div",
                    el(
                        "a",
                        "+ Add ",
                        rel_name,
                        href=create_url,
                        hx_get=create_url,
                        hx_target="this",
                        hx_swap="outerHTML",
                    ),
                )
            )

        return render_to_string(
            el(
                "div",
                *header,
                el("table", el("tbody", *rows)),
                class_="relation-panel",
                id=f"relation-panel-{rel_name}",
            )
        )


__all__ = [
    "RelationManager",
]
