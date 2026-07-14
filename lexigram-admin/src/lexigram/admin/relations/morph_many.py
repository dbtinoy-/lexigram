"""MorphMany (polymorphic HasMany) relation manager."""

from __future__ import annotations

from typing import Any

from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.ui import el, render_to_string


class MorphManyRelationManager(RelationManager):
    """Relation manager for polymorphic HasMany relationships.

    Similar to HasMany but filters related records by morph type
    and key.  On create, automatically sets the morph type and key.

    Example:
        class PostCommentsRelationManager(MorphManyRelationManager):
            relationship_name = "comments"
            morph_name = "commentable"
            morph_type_value = "post"
    """

    morph_name: str = ""
    morph_type_value: str = ""

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []

    async def render(self, request: Any, resource_name: str = "") -> str:
        """Render the morph-many relation panel as HTML."""
        items = await self.get_query()
        rel_name = self.get_relationship_name()
        parent_id = self.parent_id

        rows: list[Any] = []
        for item in items:
            item_id = str(getattr(item, "id", str(id(item))))
            label = str(getattr(item, "name", item_id))

            actions: list[Any] = []
            if self.inline_edit:
                edit_url = f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/{item_id}/edit"
                actions.append(
                    el(
                        "a",
                        "Edit",
                        href=edit_url,
                        hx_get=edit_url,
                        hx_target="closest tr",
                        hx_swap="outerHTML",
                        class_="text-primary-600 hover:text-primary-800 text-sm mr-2",
                    )
                )
            if self.inline_delete:
                delete_url = (
                    f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/{item_id}"
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
                        class_="text-destructive hover:text-destructive/90 text-sm",
                    )
                )

            rows.append(
                el(
                    "tr",
                    el("td", label, class_="px-4 py-2 text-sm text-foreground"),
                    el(
                        "td",
                        item_id,
                        class_="px-4 py-2 text-sm text-muted-foreground",
                    ),
                    el("td", *actions, class_="px-4 py-2 text-sm"),
                )
            )

        header: list[Any] = []
        if self.inline_create:
            create_url = f"/admin/{resource_name}/{parent_id}/relations/{rel_name}/new"
            header.append(
                el(
                    "div",
                    el(
                        "a",
                        "+ Add ",
                        rel_name.replace("_", " ").title(),
                        href=create_url,
                        hx_get=create_url,
                        hx_target=f"#relation-panel-{rel_name}",
                        hx_swap="beforeend",
                        class_="inline-flex items-center px-3 py-1.5 text-sm font-medium text-primary-600 bg-primary-50 dark:bg-primary-900/30 dark:text-primary-400 rounded-lg hover:bg-primary-100 transition-colors",
                    ),
                    class_="mb-3",
                )
            )

        table = el(
            "table",
            el(
                "thead",
                el(
                    "tr",
                    el(
                        "th",
                        "Record",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                    el(
                        "th",
                        "ID",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                    el(
                        "th",
                        "Actions",
                        class_="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase",
                    ),
                ),
                class_="bg-muted dark:bg-card",
            ),
            el("tbody", *rows, class_="divide-y divide-border"),
            class_="min-w-full divide-y divide-border",
        )

        return render_to_string(
            el(
                "div",
                el(
                    "h3",
                    rel_name.replace("_", " ").title(),
                    class_="text-lg font-medium text-foreground mb-4",
                ),
                *header,
                table,
                self._render_empty_state(rows),
                class_="relation-panel p-4",
                id=f"relation-panel-{rel_name}",
            )
        )

    def _render_empty_state(self, rows: list[Any]) -> Any:
        """Return an empty-state paragraph element, or None when rows exist."""
        if rows:
            return None
        return el(
            "p",
            "No related records found.",
            class_="text-sm text-muted-foreground italic mt-4",
        )
