"""Extended relation manager with inline editing support.

.. experimental::
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.relations.manager import AbstractRelationManager
from lexigram.result import Ok, Result


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

    async def render(self, request: Any, resource_name: str = "") -> str:
        """Render the relation panel as HTML."""
        items = await self.get_query()
        rel_name = self.get_relationship_name()
        parent_id = self.parent_id

        rows_html = ""
        for item in items:
            item_id = getattr(item, "id", str(id(item)))
            row_cells = ""
            cols = self.table()
            if cols:
                for col in cols:
                    value = getattr(item, col.name, "") if hasattr(col, "name") else ""
                    row_cells += f"<td>{value}</td>"
            else:
                row_cells = f"<td>{item}</td>"

            actions_html = ""
            if self.inline_edit:
                edit_url = f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/{item_id}/edit"
                actions_html += f'<a href="{edit_url}" hx-get="{edit_url}" hx-target="closest tr" hx-swap="outerHTML">Edit</a> '
            if self.inline_delete:
                delete_url = (
                    f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/{item_id}"
                )
                actions_html += f'<a href="{delete_url}" hx-delete="{delete_url}" hx-confirm="Delete this record?" hx-target="closest tr" hx-swap="outerHTML">Delete</a>'
            if actions_html:
                row_cells += f"<td>{actions_html}</td>"

            rows_html += f"<tr>{row_cells}</tr>"

        header_html = ""
        if self.inline_create:
            create_url = f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/new"
            header_html = f'<div><a href="{create_url}" hx-get="{create_url}" hx-target="this" hx-swap="outerHTML">+ Add {rel_name}</a></div>'

        return f'<div class="relation-panel" id="relation-panel-{rel_name}">{header_html}<table><tbody>{rows_html}</tbody></table></div>'


__all__ = [
    "RelationManager",
]
