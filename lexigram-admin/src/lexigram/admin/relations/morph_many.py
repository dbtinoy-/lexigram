"""MorphMany (polymorphic HasMany) relation manager."""

from __future__ import annotations

from typing import Any

from lexigram.admin.relations.manager_ext import RelationManager


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
        items = await self.get_query()
        rel_name = self.get_relationship_name()

        rows_html = ""
        for item in items:
            item_id = getattr(item, "id", str(id(item)))
            label = str(getattr(item, "name", item_id))

            actions = ""
            if self.inline_edit:
                edit_url = f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/{item_id}/edit"
                actions += f'<a href="{edit_url}" hx-get="{edit_url}" hx-target="closest tr" hx-swap="outerHTML" class="text-primary-600 hover:text-primary-800 text-sm mr-2">Edit</a>'
            if self.inline_delete:
                delete_url = f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/{item_id}"
                actions += f'<a href="{delete_url}" hx-delete="{delete_url}" hx-confirm="Delete this record?" hx-target="closest tr" hx-swap="outerHTML" class="text-destructive hover:text-destructive/90 text-sm">Delete</a>'

            rows_html += f"""<tr>
                <td class="px-4 py-2 text-sm text-foreground">{label}</td>
                <td class="px-4 py-2 text-sm text-muted-foreground">{item_id}</td>
                <td class="px-4 py-2 text-sm">{actions}</td>
            </tr>"""

        header = ""
        if self.inline_create:
            create_url = (
                f"/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/new"
            )
            header = f"""<div class="mb-3">
                <a href="{create_url}" hx-get="{create_url}" hx-target="#relation-panel-{rel_name}" hx-swap="beforeend"
                   class="inline-flex items-center px-3 py-1.5 text-sm font-medium text-primary-600 bg-primary-50 dark:bg-primary-900/30 dark:text-primary-400 rounded-lg hover:bg-primary-100 transition-colors">
                   + Add {rel_name.replace("_", " ").title()}
                </a>
            </div>"""

        return f"""<div class="relation-panel p-4" id="relation-panel-{rel_name}">
            <h3 class="text-lg font-medium text-foreground mb-4">{rel_name.replace("_", " ").title()}</h3>
            {header}
            <table class="min-w-full divide-y divide-border">
                <thead class="bg-muted dark:bg-card">
                    <tr>
                        <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Record</th>
                        <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                        <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-border">{rows_html}</tbody>
            </table>
            {self._render_empty_state(rows_html)}
        </div>"""

    def _render_empty_state(self, rows_html: str) -> str:
        if rows_html:
            return ""
        return '<p class="text-sm text-muted-foreground italic mt-4">No related records found.</p>'
