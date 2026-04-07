# Data Sources

Guide to the data source system in `lexigram-admin`.

---

## 1. Overview

The data source system provides a **unified data access layer** that abstracts
away the underlying storage backend (SQL database, REST API, in-memory store,
etc.) behind a consistent CRUD interface. Every Resource in the admin panel
communicates with its data backend through an `IDataSource` implementation.

The system lives in `src/lexigram/admin/data/` and consists of:

| Component       | File                        | Role                               |
|-----------------|-----------------------------|------------------------------------|
| `IDataSource`   | `data_source.py`            | Protocol (interface)               |
| `DataSourceBase`| `data_source.py`            | Abstract base class                |
| `SqlDataSource` | `data_source.py`            | SQL-backed implementation          |
| `QuerySpec`     | `query.py`                  | Immutable query specification      |
| `QueryResult`   | `data_source.py`            | Paginated result container         |
| `PagedResult`   | `query.py`                  | Lightweight paginated result       |

---

## 2. `IDataSource` Protocol

`IDataSource[T]` is a `@runtime_checkable` protocol in
`lexigram.admin.data.data_source`. It defines the contract that every
data backend must satisfy:

```python
class IDataSource(Protocol[T]):

    async def find_one(self, item_id: Any) -> T | None: ...
    async def find_many(self, query: QuerySpec) -> QueryResult[T]: ...
    async def count(self, query: QuerySpec) -> int: ...
    async def create(self, data: dict[str, Any]) -> T: ...
    async def update(self, item_id: Any, data: dict[str, Any]) -> T: ...
    async def delete(self, item_id: Any) -> bool: ...
    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]: ...
    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int: ...
    async def bulk_delete(self, ids: list[Any]) -> int: ...
```

### Method reference

| Method            | Returns                        | Description                              |
|-------------------|--------------------------------|------------------------------------------|
| `find_one`        | `T \| None`                    | Fetch a single entity by ID              |
| `find_many`       | `QueryResult[T]`               | Fetch entities matching a `QuerySpec`    |
| `count`           | `int`                          | Count entities matching a `QuerySpec`    |
| `create`          | `T`                            | Insert a new entity                      |
| `update`          | `T`                            | Update an existing entity                |
| `delete`          | `bool`                         | Delete an entity by ID                   |
| `bulk_create`     | `list[T]`                      | Insert multiple entities                 |
| `bulk_update`     | `int`                          | Update multiple entities                 |
| `bulk_delete`     | `int`                          | Delete multiple entities by IDs          |

Because `IDataSource` is `@runtime_checkable`, you can test compliance at
the boundary:

```python
from lexigram.admin.data.data_source import IDataSource

assert isinstance(my_source, IDataSource), "Must implement IDataSource"
```

---

## 3. `DataSourceBase` ABC

`DataSourceBase[T]` is an abstract base class that provides a partial
implementation of `IDataSource`. It is the recommended starting point for
custom data sources.

```python
class DataSourceBase(ABC, Generic[T]):

    @abstractmethod
    async def find_one(self, item_id: Any) -> T | None: ...
    @abstractmethod
    async def find_many(self, query: QuerySpec | None = None, **filters: Any) -> QueryResult[T]: ...
    @abstractmethod
    async def create(self, entity: T | dict[str, Any]) -> T: ...
    @abstractmethod
    async def update(self, item_id: Any, data: dict[str, Any] | None = None) -> T | None: ...
    @abstractmethod
    async def delete(self, item_id: Any) -> bool: ...
```

### Differences from `IDataSource`

- `find_many` accepts `**filters` as a shortcut alongside `QuerySpec`.
- `create` accepts `T | dict[str, Any]` (typed entity or raw dict).
- `update` has `data` as optional (allows passing a full entity).
- `count` has a default implementation that delegates to `find_many`.

---

## 4. `SqlDataSource` Concrete Implementation

`SqlDataSource[T]` is the primary production implementation, backed by
`DatabaseProviderProtocol` from `lexigram-contracts`.

```python
from lexigram.admin.data.data_source import SqlDataSource

class UserDataSource(SqlDataSource[User]):
    def __init__(self, db: DatabaseProviderProtocol):
        super().__init__(db, table_name="users")
```

### Constructor

| Parameter    | Type                        | Description                        |
|--------------|-----------------------------|------------------------------------|
| `db`         | `DatabaseProviderProtocol`  | SQL database provider from DI      |
| `table_name` | `str`                       | Name of the database table         |
| `id_field`   | `str`                       | Primary key column name (default: `"id"`) |

### Query building

- Uses parameterized queries (`$1`, `$2`, ...) for injection safety.
- Column and table names are validated via `_quote_identifier()`.
- `find_many` supports:
  - Pagination (`page`, `per_page` → `LIMIT`/`OFFSET`)
  - Simple key-value filters (`**filters` → `WHERE col = $N`)
  - `QuerySpec` with sort, search, and structured conditions

---

## 5. `QuerySpec` and `QueryResult`

### `QuerySpec`

`QuerySpec` is an immutable, composable query specification defined in
`lexigram.admin.data.query`. It is the canonical type for passing query
parameters across all layers (controller → service → data source).

```python
from lexigram.admin.data.query import QuerySpec

query = (
    QuerySpec()
    .with_page(2)
    .with_per_page(50)
    .with_sort("created_at", "desc")
    .with_search("john", fields=["name", "email"])
    .with_filters(status="active")
)
```

**Key methods:**

| Method                       | Purpose                              |
|------------------------------|--------------------------------------|
| `with_page(n)`               | Set page number (1-indexed)          |
| `with_per_page(n)`           | Set items per page                   |
| `with_cursor(cursor)`        | Switch to cursor-based pagination    |
| `with_sort(field, order)`    | Set sort field and direction         |
| `with_search(term, fields)`  | Set full-text search                 |
| `with_filters(**kwargs)`     | Set key-value filters                |
| `with_where(field, op, val)` | Add structured filter condition      |
| `with_include(*relations)`   | Eager-load relations                 |
| `from_dict(data)`            | Create from query params dict        |
| `to_dict()`                  | Serialize to dict                    |

**Supported filter operators** (`FilterOperator` enum):

`EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `NOT_IN`, `CONTAINS`,
`ICONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `IS_NULL`, `BETWEEN`

### `QueryResult`

`QueryResult[T]` is the result container returned by `IDataSource.find_many()`.

```python
@dataclass
class QueryResult(Generic[T]):
    items: list[T]
    total: int = 0
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_prev: bool = False
    cursor: str | None = None
```

### `PagedResult`

`PagedResult[T]` is a lighter alternative in `query.py` with computed
properties (`has_next`, `has_prev`, `total_pages`, `start_index`, `end_index`)
and a `map()` transform method.

---

## 6. How Resources Use Data Sources

A Resource references its data source through the `get_data_source()`
classmethod, which resolves it from the container:

```python
class MyResource(Resource):
    model = MyModel

    @classmethod
    async def get_data_source(cls) -> IDataSource[MyModel]:
        from lexigram.admin.di.container import admin_container
        return await admin_container.resolve(IDataSource[MyModel])
```

The framework provides a default resolution path:

1. Resource declares `model = MyModel`.
2. At registration time, a `DataSourceProvider` binds
   `IDataSource[MyModel]` to a `SqlDataSource[MyModel]` for that model's table.
3. At request time, the controller resolves `IDataSource[MyModel]`
   and calls `find_many(query)`, `find_one(id)`, `create(data)`, etc.

The controller never knows which concrete data source it is using — it
depends only on the protocol.

---

## 7. Creating Custom Data Sources

### API-backed data source

```python
from lexigram.admin.data.data_source import DataSourceBase, QueryResult
from lexigram.admin.data.query import QuerySpec

class ApiDataSource(DataSourceBase[MyModel]):
    def __init__(self, base_url: str, api_key: str):
        self._base_url = base_url
        self._session = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})

    async def find_one(self, item_id: Any) -> MyModel | None:
        resp = await self._session.get(f"{self._base_url}/{item_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return MyModel(**resp.json())

    async def find_many(self, query: QuerySpec | None = None, **filters: Any) -> QueryResult[MyModel]:
        params = {}
        if query:
            params.update(query.to_dict())
        params.update(filters)
        resp = await self._session.get(self._base_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        return QueryResult(
            items=[MyModel(**item) for item in data["items"]],
            total=data["total"],
            page=data.get("page", 1),
            per_page=data.get("per_page", 20),
            has_next=data.get("has_next", False),
            has_prev=data.get("has_prev", False),
        )

    async def create(self, entity: MyModel | dict[str, Any]) -> MyModel:
        data = entity if isinstance(entity, dict) else entity.model_dump()
        resp = await self._session.post(self._base_url, json=data)
        resp.raise_for_status()
        return MyModel(**resp.json())

    async def update(self, item_id: Any, data: dict[str, Any] | None = None) -> MyModel | None:
        resp = await self._session.patch(f"{self._base_url}/{item_id}", json=data or {})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return MyModel(**resp.json())

    async def delete(self, item_id: Any) -> bool:
        resp = await self._session.delete(f"{self._base_url}/{item_id}")
        return resp.status_code == 204
```

### Registering a custom data source

In your provider:

```python
class MyProvider(Provider):
    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(
            IDataSource[MyModel],
            ApiDataSource(base_url="https://api.example.com", api_key="..."),
        )
```

---

## 8. Testing with In-Memory Data Sources

For tests, use the in-memory data source to avoid database dependencies:

```python
from lexigram.admin.data.data_source import DataSourceBase, QueryResult
from lexigram.admin.data.query import QuerySpec

class InMemoryDataSource(DataSourceBase[dict]):
    """In-memory data source for testing."""

    def __init__(self, items: list[dict] | None = None):
        self._items: dict[str, dict] = {}
        for item in items or []:
            self._items[str(item.get("id", id(item)))] = dict(item)

    async def find_one(self, item_id: Any) -> dict | None:
        return self._items.get(str(item_id))

    async def find_many(self, query: QuerySpec | None = None, **filters: Any) -> QueryResult[dict]:
        items = list(self._items.values())
        if filters:
            items = [
                item for item in items
                if all(item.get(k) == v for k, v in filters.items())
            ]
        return QueryResult(
            items=items,
            total=len(items),
            page=1,
            per_page=len(items) or 20,
        )

    async def create(self, entity: dict) -> dict:
        entity = dict(entity)
        entity.setdefault("id", str(len(self._items) + 1))
        self._items[str(entity["id"])] = entity
        return entity

    async def update(self, item_id: Any, data: dict[str, Any] | None = None) -> dict | None:
        key = str(item_id)
        if key not in self._items:
            return None
        self._items[key].update(data or {})
        return self._items[key]

    async def delete(self, item_id: Any) -> bool:
        key = str(item_id)
        if key not in self._items:
            return False
        del self._items[key]
        return True
```

Then in a test:

```python
@pytest.mark.asyncio
async def test_resource_list():
    source = InMemoryDataSource([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ])
    result = await source.find_many(QuerySpec().with_page(1).with_per_page(10))
    assert result.total == 2
    assert len(result.items) == 2
```

---

## 9. Interface Diagram

```
┌──────────────┐     implements      ┌──────────────────┐
│ IDataSource  │ ◄───────────────── │ DataSourceBase    │
│  (Protocol)  │                     │   (ABC)           │
└──────────────┘                     └────────┬─────────┘
                                              │ extends
                                              ▼
                                    ┌──────────────────┐
                                    │ SqlDataSource    │
                                    │  (PG via DBP)    │
                                    └──────────────────┘
                                              │
                                    ┌──────────────────┐
                                    │ ApiDataSource    │
                                    │  (user-defined)  │
                                    └──────────────────┘
                                              │
                                    ┌──────────────────┐
                                    │ InMemoryDS       │
                                    │  (testing only)  │
                                    └──────────────────┘

Resource ──► get_data_source() ──► IDataSource[T]
                           │
                           ▼
                    QuerySpec ──► find_many() ──► QueryResult[T]
```
