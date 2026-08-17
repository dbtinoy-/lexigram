"""In-memory data source adapter for Lexigram Admin."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from lexigram.admin.data.data_source import IDataSource, QueryResult
from lexigram.admin.data.query import FilterOperator, QuerySpec
from lexigram.di.decorators import inject

T = TypeVar("T")


@inject
class InMemoryDataSource(IDataSource[T], Generic[T]):
    """Data source for in-memory collections of dictionaries.

    This is useful for testing, mocking, or displaying static data
    using the Admin UI components.
    """

    returns_result: bool = False  # Marker: this adapter returns QueryResult, not Result

    def __init__(self, data: list[T]) -> None:
        """Initialize with a list of data items.

        Args:
            data: List of dictionary-like objects.
        """
        self._items = list(data)

    async def find_one(self, item_id: Any) -> T | None:
        """Find a single item by its 'id' field."""
        for item in self._items:
            # We assume items are dicts or have an .id attribute
            item_identifier = (
                item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            )
            if str(item_identifier) == str(item_id):
                return item
        return None

    async def find_many(self, query: QuerySpec) -> QueryResult[T]:
        """Filter, sort, and paginate in-memory items."""
        filtered_items = self._apply_filters(self._items, query)

        # Search
        if query.search and query.search_fields:
            term = query.search.lower()
            searched = []
            for item in filtered_items:
                match = False
                for field in query.search_fields:
                    val = (
                        item.get(field)
                        if isinstance(item, dict)
                        else getattr(item, field, None)
                    )
                    if val and term in str(val).lower():
                        match = True
                        break
                if match:
                    searched.append(item)
            filtered_items = searched

        # Sort
        if query.sort_by:
            field = query.sort_by
            reverse = query.sort_order == "desc"

            def get_val(x: Any) -> Any:
                val = x.get(field) if isinstance(x, dict) else getattr(x, field, None)
                return "" if val is None else val

            filtered_items.sort(key=get_val, reverse=reverse)

        total = len(filtered_items)

        # Paginate
        start = (query.page - 1) * query.per_page
        end = start + query.per_page
        paginated_items = filtered_items[start:end]

        return QueryResult(
            items=paginated_items,
            total=total,
            page=query.page,
            per_page=query.per_page,
            has_next=end < total,
            has_prev=query.page > 1,
        )

    async def count(self, query: QuerySpec) -> int:
        """Count items matching the query."""
        filtered_items = self._apply_filters(self._items, query)
        return len(filtered_items)

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new item in memory."""
        # Check if it has an id, if not generate one (naive)
        if "id" not in data:
            data = dict(data)
            data["id"] = len(self._items) + 1

        # In a real generic implementation, we'd need to cast to T
        new_item = data
        self._items.append(new_item)  # type: ignore[arg-type]
        return new_item  # type: ignore[return-value]

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        """Update an item in memory."""
        for i, item in enumerate(self._items):
            item_identifier = (
                item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            )
            if str(item_identifier) == str(item_id):
                if isinstance(item, dict):
                    updated_item: Any = {**item, **data, "id": item_id}
                    self._items[i] = updated_item
                    return self._items[i]
                for k, v in data.items():
                    setattr(item, k, v)
                return item
        raise ValueError(f"Item with id {item_id} not found")

    async def delete(self, item_id: Any) -> bool:
        """Delete an item from memory."""
        initial_len = len(self._items)
        self._items = [
            item
            for item in self._items
            if str(
                item.get("id") if isinstance(item, dict) else getattr(item, "id", None),
            )
            != str(item_id)
        ]
        return len(self._items) < initial_len

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        """Bulk create items in memory."""
        results = []
        for item_data in items:
            results.append(await self.create(item_data))
        return results

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        """Bulk update items in memory."""
        count = 0
        for id_ in ids:
            try:
                await self.update(id_, data)
                count += 1
            except ValueError:
                continue
        return count

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Bulk delete items in memory."""
        count = 0
        ids_to_delete = list(map(str, ids))

        new_items = []
        for item in self._items:
            item_id = (
                item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
            )
            if str(item_id) in ids_to_delete:
                count += 1
            else:
                new_items.append(item)

        self._items = new_items
        return count

    def _apply_filters(self, items: list[T], query: QuerySpec) -> list[T]:
        """Apply all specified filters to the item list."""
        conditions = query.filter_conditions
        if not conditions:
            return list(items)

        filtered = list(items)
        for condition in conditions:
            field = condition.field
            op_type = condition.operator
            val = condition.value

            # Map operator
            filtered = [
                item for item in filtered if self._matches(item, field, op_type, val)
            ]

        return filtered

    def _matches(
        self,
        item: Any,
        field: str,
        op_type: FilterOperator,
        target_val: Any,
    ) -> bool:
        """Check if an item matches a specific filter condition."""
        # Get item value
        item_val = (
            item.get(field) if isinstance(item, dict) else getattr(item, field, None)
        )

        if op_type == FilterOperator.EQ:
            return item_val == target_val
        if op_type == FilterOperator.NEQ:
            return item_val != target_val
        if op_type == FilterOperator.GT:
            return item_val > target_val
        if op_type == FilterOperator.GTE:
            return item_val >= target_val
        if op_type == FilterOperator.LT:
            return item_val < target_val
        if op_type == FilterOperator.LTE:
            return item_val <= target_val
        if op_type == FilterOperator.IN:
            return item_val in target_val
        if op_type == FilterOperator.NOT_IN:
            return item_val not in target_val
        if op_type == FilterOperator.CONTAINS:
            return target_val.lower() in str(item_val).lower()
        if op_type == FilterOperator.ICONTAINS:
            return target_val.lower() in str(item_val).lower()
        if op_type == FilterOperator.IS_NULL:
            return item_val is None
        if op_type == FilterOperator.BETWEEN:
            min_v, max_v = target_val
            return min_v <= item_val <= max_v

        return False
