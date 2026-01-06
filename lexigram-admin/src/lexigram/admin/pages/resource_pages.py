"""Resource page implementations for lexigram-admin.

Provides concrete Page subclasses for standard CRUD operations:
ListPage, CreatePage, EditPage, and ViewPage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.relations.manager_ext import RelationManager

from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse


class ListPage(Page):
    """Default resource list page — table with search, pagination, actions."""

    title: str = "List"

    def __init__(self, resource_name: str = "", path: str = "") -> None:
        self.resource_name = resource_name
        if path:
            self.path = path

    async def view(self, request: Any) -> PageResponse:
        """Render list page with resource records."""
        return PageResponse(
            content=self._render_list(request),
            title=self.title,
        )

    def _render_list(self, request: Any) -> str:
        """Render the list HTML."""
        return f"<div>List of {self.resource_name}</div>"


class CreatePage(Page):
    """Default resource create page — form for a new record."""

    title: str = "Create"

    def __init__(self, resource_name: str = "", path: str = "") -> None:
        self.resource_name = resource_name
        if path:
            self.path = path

    async def view(self, request: Any) -> PageResponse:
        """Render creation form."""
        return PageResponse(
            content=self._render_form(request),
            title=self.title,
        )

    def _render_form(self, request: Any) -> str:
        """Render the form HTML."""
        return f"<form>Create {self.resource_name}</form>"

    async def post(self, request: Any) -> PageResponse:
        """Handle form submission for creating a record."""
        return PageResponse(
            content=f"<div>Created {self.resource_name}</div>",
            title=self.title,
        )


class EditPage(Page):
    """Default resource edit page — form pre-filled with existing record."""

    title: str = "Edit"

    def __init__(self, resource_name: str = "", path: str = "") -> None:
        self.resource_name = resource_name
        if path:
            self.path = path

    async def view(self, request: Any) -> PageResponse:
        """Render edit form pre-filled with record data."""
        record_id = self._get_record_id(request)
        return PageResponse(
            content=self._render_form(request, record_id),
            title=self.title,
        )

    def _get_record_id(self, request: Any) -> str:
        """Extract record ID from request path/query parameters."""
        return getattr(request, "path_params", {}).get("id", "")

    def _render_form(self, request: Any, record_id: str) -> str:
        """Render the edit form HTML."""
        return f"<form>Edit {self.resource_name} #{record_id}</form>"

    async def post(self, request: Any) -> PageResponse:
        """Handle form submission for updating a record."""
        record_id = self._get_record_id(request)
        return PageResponse(
            content=f"<div>Updated {self.resource_name} #{record_id}</div>",
            title=self.title,
        )


class ViewPage(Page):
    """Default resource view page — read-only detail."""

    title: str = "View"

    def __init__(
        self,
        resource_name: str = "",
        path: str = "",
        relations: list[type[RelationManager]] | None = None,
    ) -> None:
        self.resource_name = resource_name
        self._relations = relations or []
        if path:
            self.path = path

    async def view(self, request: Any) -> PageResponse:
        """Render read-only detail view."""
        record_id = getattr(request, "path_params", {}).get("id", "")
        return PageResponse(
            content=self._render_detail(request, record_id),
            title=self.title,
            breadcrumbs=[
                ("Home", "/admin"),
                (self.resource_name, f"/admin/{self.resource_name}"),
                ("View", ""),
            ],
        )

    def _render_detail(self, request: Any, record_id: str) -> str:
        """Render the detail HTML with optional relation panels."""
        main_content = f"<div>Detail of {self.resource_name} #{record_id}</div>"

        relations_html = ""
        for relation_cls in self._relations:
            rel_name = getattr(relation_cls, "relationship_name", "") or ""
            rel_url = f"/admin/{self.resource_name}/{record_id}/relations/{rel_name}"
            relations_html += (
                f'<div hx-get="{rel_url}" '
                f'hx-trigger="load" '
                f'hx-swap="outerHTML" '
                f'id="relation-{rel_name}">'
                f"Loading {rel_name}..."
                f"</div>"
            )

        return main_content + relations_html


__all__ = [
    "CreatePage",
    "EditPage",
    "ListPage",
    "ViewPage",
]
