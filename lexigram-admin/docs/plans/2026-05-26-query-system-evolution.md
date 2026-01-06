# Query System Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace legacy `Query`/`QueryBuilder` with `QuerySpec` across all adapters and consumers, removing `.to_query()` bridge calls.

**Architecture:** 3 legacy adapters (`repository_adapter`, `memory_adapter`, `api_adapter`) switch from `Query` to `QuerySpec`. IDataSource protocol updates its type. 5 bridge points stop calling `.to_query()`. QueryOptimizer switches. `Query`/`QueryBuilder` remain as deprecated re-exports.

**Tech Stack:** Python 3.12, dataclasses, Protocol

---

### Task 1: Add `filter_conditions` property to QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/query.py`
- Test: `lexigram-admin/tests/unit/data/test_query_spec.py`

- [ ] **Step 1: Write the failing test**

```python
# In tests/unit/data/test_query_spec.py

from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestQuerySpecFilterConditions:
    def test_filter_conditions_combines_where_and_filters(self) -> None:
        qs = QuerySpec(
            where=(
                FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),
            ),
            filters={"name": "test"},
        )
        conditions = qs.filter_conditions
        assert len(conditions) == 2
        assert conditions[0].field == "status"
        assert conditions[0].operator == FilterOperator.EQ
        assert conditions[1].field == "name"
        assert conditions[1].operator == FilterOperator.EQ

    def test_filter_conditions_returns_list(self) -> None:
        qs = QuerySpec()
        assert isinstance(qs.filter_conditions, list)
        assert qs.filter_conditions == []

    def test_filter_conditions_where_only(self) -> None:
        qs = QuerySpec(
            where=(FilterCondition(field="age", operator=FilterOperator.GT, value=18),),
        )
        assert len(qs.filter_conditions) == 1
        assert qs.filter_conditions[0].field == "age"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/data/test_query_spec.py -v`
Expected: FAIL — property not defined

- [ ] **Step 3: Add `filter_conditions` property to QuerySpec**

In `lexigram-admin/src/lexigram/admin/data/query.py`, add to the QuerySpec class:

```python
@property
def filter_conditions(self) -> list[FilterCondition]:
    """Combine ``where`` conditions and ``filters`` dict into a single filter list."""
    result = list(self.where)
    for key, value in self.filters.items():
        result.append(FilterCondition(field=key, operator=FilterOperator.EQ, value=value))
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest lexigram-admin/tests/unit/data/test_query_spec.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

---

### Task 2: Update IDataSource protocol to use QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/data_source.py`

- [ ] **Step 1: Change `find_many(self, query: Any)` to `find_many(self, query: QuerySpec)`**

In `data_source.py`, import `QuerySpec` and change:
- Line 54: `async def find_many(self, query: Any) -> QueryResult[T]:` → `async def find_many(self, query: QuerySpec) -> QueryResult[T]:`
- Line 65: `async def count(self, query: Any) -> int:` → `async def count(self, query: QuerySpec) -> int:`
- Update docstrings

Also change `DataSourceBase.find_many(self, query: Any = None, **filters)` → `DataSourceBase.find_many(self, query: QuerySpec | None = None, **filters)`
And `DataSourceBase.count(self, query: Any = None)` → `DataSourceBase.count(self, query: QuerySpec | None = None)`

- [ ] **Step 2: Verify existing tests pass**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All tests pass (no behavioral change, just type annotation)

- [ ] **Step 3: Commit**

---

### Task 3: Update InMemoryDataSource to accept QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/adapters/memory_adapter.py`
- Create: `lexigram-admin/tests/unit/data/adapters/test_memory_adapter.py`

- [ ] **Step 1: Write adapter tests**

```python
# tests/unit/data/adapters/test_memory_adapter.py

from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestInMemoryDataSourceQuerySpec:
    def setup_method(self) -> None:
        self.data = [
            {"id": 1, "name": "Alice", "status": "active"},
            {"id": 2, "name": "Bob", "status": "inactive"},
            {"id": 3, "name": "Charlie", "status": "active"},
        ]
        self.ds = InMemoryDataSource(self.data)

    async def test_find_many_basic(self) -> None:
        qs = QuerySpec()
        result = await self.ds.find_many(qs)
        assert result.total == 3
        assert len(result.items) == 3

    async def test_find_many_with_filter_eq(self) -> None:
        qs = QuerySpec(where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),))
        result = await self.ds.find_many(qs)
        assert result.total == 2
        assert result.items[0]["name"] == "Alice"

    async def test_find_many_with_search(self) -> None:
        qs = QuerySpec(search="alice", search_fields=["name"])
        result = await self.ds.find_many(qs)
        assert result.total == 1
        assert result.items[0]["name"] == "Alice"

    async def test_find_many_with_pagination(self) -> None:
        qs = QuerySpec(page=1, per_page=2)
        result = await self.ds.find_many(qs)
        assert len(result.items) == 2
        assert result.total == 3
        assert result.has_next

    async def test_find_many_with_sort(self) -> None:
        qs = QuerySpec(sort_by="name", sort_order="desc")
        result = await self.ds.find_many(qs)
        assert result.items[0]["name"] == "Charlie"
        assert result.items[-1]["name"] == "Alice"

    async def test_count_with_query(self) -> None:
        qs = QuerySpec(where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),))
        count = await self.ds.count(qs)
        assert count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_memory_adapter.py -v`
Expected: FAIL — `_apply_filters` accesses `query.filters` but `QuerySpec` has `.filter_conditions` property

- [ ] **Step 3: Update InMemoryDataSource**

Change the import from `from lexigram.admin.data.query_builder import FilterOperator, Query` to:
```python
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec
```

Change method signatures:
```python
async def find_many(self, query: QuerySpec) -> QueryResult[T]:
async def count(self, query: QuerySpec) -> int:
```

Update `_apply_filters(self, items, query)`:
```python
def _apply_filters(self, items: list[T], query: QuerySpec) -> list[T]:
    conditions = query.filter_conditions
    if not conditions:
        return list(items)

    filtered = list(items)
    for condition in conditions:
        field = condition.field
        op_type = condition.operator
        val = condition.value
        filtered = [
            item for item in filtered if self._matches(item, field, op_type, val)
        ]
    return filtered
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_memory_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Full regression**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All pass

- [ ] **Step 6: Commit**

---

### Task 4: Update APIDataSource to accept QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/adapters/api_adapter.py`
- Create: `lexigram-admin/tests/unit/data/adapters/test_api_adapter.py`

- [ ] **Step 1: Write adapter tests**

```python
# tests/unit/data/adapters/test_api_adapter.py

from unittest.mock import AsyncMock, patch

from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestAPIDataSourceQuerySpec:
    async def test_find_many_basic(self) -> None:
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("lexigram.admin.data.adapters.api_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            from lexigram.admin.data.adapters.api_adapter import APIDataSource
            ds = APIDataSource(base_url="http://test/api/items")
            qs = QuerySpec(page=1, per_page=20)
            result = await ds.find_many(qs)
            assert len(result.items) == 2
            mock_client.get.assert_awaited_once()

    async def test_find_many_with_filters(self) -> None:
        # Verify _transform_query receives combined filter conditions
        mock_response = AsyncMock()
        mock_response.json.return_value = {"items": [], "total": 0}
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("lexigram.admin.data.adapters.api_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client
            from lexigram.admin.data.adapters.api_adapter import APIDataSource
            ds = APIDataSource(base_url="http://test/api/items")
            qs = QuerySpec(
                where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),),
                filters={"name": "test"},
            )
            result = await ds.find_many(qs)
            # Check that filter params were included
            call_kwargs = mock_client.get.call_args
            params = call_kwargs[1]["params"]
            assert "filter[status][eq]" in params
            assert "filter[name][eq]" in params
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_api_adapter.py -v`
Expected: FAIL — type mismatch or attribute error

- [ ] **Step 3: Update APIDataSource**

Change import:
```python
if TYPE_CHECKING:
    from lexigram.admin.data.query import QuerySpec
```

Change signatures:
```python
async def find_many(self, query: QuerySpec) -> QueryResult[T]:
async def count(self, query: QuerySpec) -> int:
def _transform_query(self, query: QuerySpec) -> dict[str, Any]:
```

Update `_transform_query`:
- `query.select_fields` → `list(query.select_fields)` (tuple → list for join)
- `query.include_relations` → `query.include`
- `query.filters` → `query.filter_conditions` (combined list)

```python
def _transform_query(self, query: QuerySpec) -> dict[str, Any]:
    params: dict[str, Any] = {
        "page": query.page,
        "per_page": query.per_page,
    }

    if query.sort_by:
        params["sort_by"] = query.sort_by
        params["sort_order"] = query.sort_order

    if query.search:
        params["search"] = query.search
        if query.search_fields:
            params["search_fields"] = ",".join(query.search_fields)

    if query.select_fields:
        params["select"] = ",".join(query.select_fields)

    if query.include:
        params["include"] = ",".join(query.include)

    if query.cursor:
        params["cursor"] = query.cursor

    for condition in query.filter_conditions:
        key = f"filter[{condition.field}][{condition.operator.value}]"
        params[key] = condition.value

    return params
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_api_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Full regression**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All pass

- [ ] **Step 6: Commit**

---

### Task 5: Update RepositoryDataSource (repository_adapter.py) to accept QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/adapters/repository_adapter.py`
- Create: `lexigram-admin/tests/unit/data/adapters/test_repository_adapter.py`

- [ ] **Step 1: Write adapter tests**

```python
# tests/unit/data/adapters/test_repository_adapter.py

from unittest.mock import AsyncMock, MagicMock

from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestRepositoryAdapterQuerySpec:
    def setup_method(self) -> None:
        self.repository = MagicMock()
        self.repository.find_many = AsyncMock(return_value=[{"id": 1}])
        self.repository.find_by_id = AsyncMock(return_value={"id": 1})
        self.repository.count = AsyncMock(return_value=1)
        self.repository.table_name = "test"

    async def test_find_many_basic(self) -> None:
        from lexigram.admin.data.adapters.repository_adapter import RepositoryDataSource
        ds = RepositoryDataSource(repository=self.repository, resource_name="test")
        qs = QuerySpec(page=1, per_page=20)
        result = await ds.find_many(qs)
        assert result.total == 1

    async def test_find_many_with_filters(self) -> None:
        from lexigram.admin.data.adapters.repository_adapter import RepositoryDataSource
        ds = RepositoryDataSource(repository=self.repository, resource_name="test")
        qs = QuerySpec(
            where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),),
        )
        result = await ds.find_many(qs)
        assert result.total == 1

    async def test_count_with_query(self) -> None:
        from lexigram.admin.data.adapters.repository_adapter import RepositoryDataSource
        ds = RepositoryDataSource(repository=self.repository, resource_name="test")
        qs = QuerySpec()
        count = await ds.count(qs)
        assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_repository_adapter.py -v`
Expected: FAIL — type mismatch

- [ ] **Step 3: Update RepositoryDataSource**

Change imports:
```python
from lexigram.admin.data.query import FilterOperator, QuerySpec
```

Remove import of `Query` from `query_builder.py` (if no other uses remain in the file).

Change signatures:
```python
async def find_many(self, query: QuerySpec) -> QueryResult[T]:
async def count(self, query: QuerySpec) -> int:
def _transform_filters(self, query: QuerySpec) -> dict[str, Any]:
```

Update `_transform_filters` — combine `where` + `filters`:
```python
def _transform_filters(self, query: QuerySpec) -> dict[str, Any]:
    repo_filters: dict[str, Any] = {}
    conditions = query.filter_conditions
    for condition in conditions:
        field = condition.field
        op = condition.operator
        val = condition.value
        repo_field, repo_val = _filter_mapper_registry.map_filter(field, op, val)
        repo_filters[repo_field] = repo_val

    if self._soft_delete_enabled and not query.include_deleted:
        repo_filters["deleted_at__isnull"] = True

    return repo_filters
```

Important: the `_transform_filters` method also has `getattr(query, "include_deleted", False)`. With `QuerySpec`, this becomes `query.include_deleted` directly (no `getattr` needed).

Also update `find_many` body:
- `query.select_fields` → `query.select_fields` (both iterables, but QuerySpec's is `tuple`, the adapter does `query.select_fields or None` which works for tuples too)

- [ ] **Step 4: Run tests**

Run: `uv run pytest lexigram-admin/tests/unit/data/adapters/test_repository_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Full regression**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All pass

- [ ] **Step 6: Commit**

---

### Task 6: Update QueryOptimizer to accept QuerySpec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/optimizer.py`
- Create: `lexigram-admin/tests/unit/data/test_optimizer.py`

- [ ] **Step 1: Write tests**

```python
# tests/unit/data/test_optimizer.py

from lexigram.admin.data.optimizer import QueryOptimizer
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestQueryOptimizerQuerySpec:
    def setup_method(self) -> None:
        self.optimizer = QueryOptimizer()

    def test_analyze_with_filters(self) -> None:
        qs = QuerySpec(
            where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),),
        )
        analysis = self.optimizer.analyze(qs)
        assert "index" in analysis.suggestions[0].lower()

    def test_analyze_large_offset(self) -> None:
        qs = QuerySpec(page=100, per_page=20)
        analysis = self.optimizer.analyze(qs)
        assert any("cursor" in s for s in analysis.suggestions)

    def test_analyze_select_star(self) -> None:
        qs = QuerySpec()
        analysis = self.optimizer.analyze(qs)
        assert any("select" in s.lower() for s in analysis.suggestions)

    def test_optimize_returns_query(self) -> None:
        qs = QuerySpec(page=1, per_page=20)
        result = self.optimizer.optimize(qs)
        assert isinstance(result, QuerySpec)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/data/test_optimizer.py -v`
Expected: FAIL — `query.filters` attribute mismatch

- [ ] **Step 3: Update QueryOptimizer**

Change import:
```python
from lexigram.admin.data.query import QuerySpec
```

Change signatures:
```python
def analyze(self, query: QuerySpec) -> QueryAnalysis:
def optimize(self, query: QuerySpec) -> QuerySpec:
```

Update `analyze` body:
- `query.filters` → `query.filter_conditions`
- `condition.field` access stays the same
- `query.select_fields` → `list(query.select_fields)` for bool check
- `query.page`, `query.per_page` stay the same

```python
def analyze(self, query: QuerySpec) -> QueryAnalysis:
    suggestions = []
    conditions = query.filter_conditions
    if conditions:
        for condition in conditions:
            field = condition.field
            if not any(field.endswith(s) for s in ["_id", "_at", "status", "slug"]):
                suggestions.append(
                    f"Field '{field}' used in filter may require an index.",
                )

    offset = (query.page - 1) * query.per_page
    if offset > 1000:
        suggestions.append(
            "Large offset detected. Consider cursor-based pagination for better performance.",
        )

    if not query.select_fields:
        suggestions.append(
            "No specific fields selected. Selecting only required fields can reduce data transfer.",
        )

    return QueryAnalysis(
        estimated_rows=100,
        uses_index=True,
        cost=0.5,
        suggestions=suggestions,
        execution_plan="mock execution plan",
    )

def optimize(self, query: QuerySpec) -> QuerySpec:
    return query
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest lexigram-admin/tests/unit/data/test_optimizer.py -v`
Expected: PASS

- [ ] **Step 5: Full regression**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All pass

- [ ] **Step 6: Commit**

---

### Task 7: Remove .to_query() calls from bridge points

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/resources/base.py`
- Modify: `lexigram-admin/src/lexigram/admin/controllers/resource.py`
- Modify: `lexigram-admin/src/lexigram/admin/data/adapters/export_adapter.py`
- Modify: `lexigram-admin/src/lexigram/admin/resources/list_renderer.py`
- Modify: `lexigram-admin/src/lexigram/admin/handlers/admin_command_handlers.py`

In each file, find `.to_query()` calls and pass the `QuerySpec` directly instead. For each file:

1. `resources/base.py`: Lines 174 and 245 — change `qs.to_query()` to `qs` in the `_data_source.find_many()` call
2. `controllers/resource.py`: Line 245 — change `query.to_query()` to `query`
3. `data/adapters/export_adapter.py`: Lines 52 and 63 — change `qs.to_query()` to `qs`
4. `resources/list_renderer.py`: Line 201 — change `qs.to_query()` to `qs`
5. `handlers/admin_command_handlers.py`: Line 238 — change `query.to_query()` to `query`

- [ ] **Step 1: One bridge point at a time, test, commit**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5` after each change
Expected: All pass

- [ ] **Step 2: Remove to_query() method from QuerySpec (optional — keep for backward compat)**

---

### Task 8: Update exports — deprecate Query/QueryBuilder

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/data/__init__.py`
- Modify: `lexigram-admin/src/lexigram/admin/data/query_builder.py` (add deprecation warning)

- [ ] **Step 1: Add deprecation warning to query_builder.py**

At the top of `query_builder.py`, add:
```python
import warnings
warnings.warn(
    "QueryBuilder and Query are deprecated. Use QuerySpec from lexigram.admin.data.query instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

- [ ] **Step 2: Update __init__.py**

Keep `Query` and `QueryBuilder` in exports for backward compatibility.

- [ ] **Step 3: Run test with deprecation warnings**

Run: `uv run pytest lexigram-admin/tests/ -W error::DeprecationWarning --tb=short -q --no-header | tail -5`
Expected: If deprecation warnings cause failures, add `-W ignore::DeprecationWarning` to the pytest config

- [ ] **Step 4: Full regression**

Run: `uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5`
Expected: All pass

- [ ] **Step 5: Commit**

---

### Task 9: Run full CI

- [ ] **Step 1: Run full CI**

```bash
uv run ruff check lexigram-admin/src/lexigram/admin/data/ &&
uv run ruff format --check lexigram-admin/src/lexigram/admin/data/ &&
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -10
```

- [ ] **Step 2: Commit CI fixes if needed**
