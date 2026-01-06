"""MorphTo (polymorphic BelongsTo) relation manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.relations.manager_ext import RelationManager

if TYPE_CHECKING:
    from starlette.requests import Request


class MorphToRelationManager(RelationManager):
    """Relation manager for polymorphic BelongsTo relationships.

    Renders a two-tier selector: choose the related type, then
    choose the record within that type.

    Example:
        class CommentableRelationManager(MorphToRelationManager):
            relationship_name = "commentable"
            morph_name = "commentable"
            morph_types = {
                "post": PostResource,
                "video": VideoResource,
            }
    """

    morph_name: str = ""
    morph_types: dict[str, type] = {}

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []

    def __init__(
        self,
        parent_id: Any = None,
        parent: Any = None,
        current_type: str | None = None,
        current_id: str | None = None,
    ):
        super().__init__(parent_id=parent_id, parent=parent)
        self.current_type = current_type
        self.current_id = current_id

    async def get_available_types(self) -> list[dict[str, str]]:
        """Return available morph types as label/value pairs."""
        result: list[dict[str, str]] = []
        for key, resource_cls in self.morph_types.items():
            label = getattr(resource_cls, "name", key.replace("_", " ").title())
            result.append({"value": key, "label": label})
        return result

    async def search_records(
        self, type_key: str, query: str = ""
    ) -> list[dict[str, str]]:
        """Search records of a given morph type."""
        return []

    async def render(self, request: Request, resource_name: str = "") -> str:
        types = await self.get_available_types()
        rel_name = self.get_relationship_name()

        type_options = "".join(
            f'<option value="{t["value"]}" {"selected" if t["value"] == self.current_type else ""}>{t["label"]}</option>'
            for t in types
        )

        current_id_html = ""
        if self.current_id:
            current_id_html = (
                f'<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">'
                f"  Currently: {self.current_type} #{self.current_id}"
                f"</div>"
            )

        return f"""<div class="relation-panel p-4" id="relation-panel-{rel_name}">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type</label>
                <select class="block w-full rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-800 text-sm"
                        name="{rel_name}_type"
                        hx-get="/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/records"
                        hx-target="#{rel_name}-records" hx-trigger="change">
                    <option value="">Select type...</option>
                    {type_options}
                </select>
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Record</label>
                <input type="text" class="block w-full rounded-lg border-gray-300 dark:border-gray-700 dark:bg-gray-800 text-sm mb-2"
                       placeholder="Search records..."
                       hx-trigger="keyup changed delay:300ms"
                       hx-get="/admin/{resource_name}/{self.parent_id}/relations/{rel_name}/records"
                       hx-target="#{rel_name}-records" hx-include="[name='{rel_name}_type']" />
                <div id="{rel_name}-records" class="max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                    {current_id_html}
                </div>
            </div>
        </div>"""

    async def get_selected_record(self) -> Any | None:
        """Return the currently selected record, if any."""
        if not self.current_type or not self.current_id:
            return None
        return {"type": self.current_type, "id": self.current_id}
