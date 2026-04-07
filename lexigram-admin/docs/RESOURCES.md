# Resources

## 1. What is a Resource?

A **Resource** is a declarative Python class that models an admin entity. It is the central configuration point for everything the admin UI knows about a domain model — which fields appear in forms and tables, which actions are available, how records relate to each other, which navigation cluster the entity belongs to, and what permissions gate each operation.

```python
from lexigram.admin.resources.base import Resource

class MyResource(Resource):
    model = None        # Your domain model class
    name = "my_items"   # URL-friendly identifier
    label = "My Items"  # Human-readable display name (auto-derived from class if omitted)
    icon = "box"        # Lucide icon identifier
    cluster = "content" # Navigation grouping key
```

### Class attributes at a glance

| Attribute | Type | Default | Purpose |
|-----------|------|---------|---------|
| `model` | `type[DomainModel] \| None` | `None` | Domain model class |
| `name` | `str \| None` | `None` | URL-friendly resource identifier |
| `cluster` | `str \| None` | `None` | Navigation group key |
| `group` | `str \| None` | `None` | Deprecated alias for `cluster` |
| `icon` | `str` | `"box"` | Lucide icon name |
| `label` | `str \| None` | `None` | Human-readable display name |
| `visible_in_sidebar` | `bool` | `True` | Show in navigation sidebar |
| `fields` | `list[SchemaField]` | `[]` | Declarative field definitions |
| `columns` | `list[Column]` | `[]` | Legacy column definitions |
| `actions` | `list[Action]` | `[]` | Row-level actions |
| `action_layout` | `str` | `"horizontal"` | Layout of action buttons |
| `bulk_actions` | `list[BulkAction]` | `[]` | Bulk selection actions |
| `filters` | `list[Filter]` | `[]` | Legacy filter definitions |
| `page_size` | `int` | `20` | Items per page in list view |
| `default_sort` | `str \| None` | `None` | Default sort field |
| `form_class` | `type[FormBase] \| None` | `None` | Custom form class |
| `form_display_mode` | `str` | `"modal"` | Form display: `"page"`, `"modal"`, or `"slider"` |
| `relations` | `list[type[RelationManager]]` | `[]` | Inline relation managers |
| `search_fields` | `list[str]` | `[]` | Fields searched by global search |
| `search_title_field` | `str` | `"name"` | Field used as display title in search results |

---

## 2. Minimal Resource

The simplest possible resource needs a `name`, a `cluster`, and at least one `fields` entry:

```python
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import TextField, EmailField, DateField

class UserResource(Resource):
    model = User
    name = "users"
    cluster = "users"
    fields = [
        TextField(name="name", label="Name", required=True, sortable=True, searchable=True),
        EmailField(name="email", label="Email", required=True),
        DateField(name="created_at", label="Created", sortable=True),
    ]
```

That's it. From these declarations the framework auto-derives:

- **Columns** for the list table (via `SchemaField.render_column()`)
- **Filters** for the filter bar (via `SchemaField.render_filter()` — fields that return `None` are excluded)
- **Form fields** for create and edit pages (via `SchemaField.render_form()`)
- **Search** if you set `search_fields`

This auto-derivation only kicks in when you use `fields` and do **not** explicitly set `columns`, `filters`, or `form_class`. If you set both `fields` and `columns`, the explicit columns win for the table rendering.

---

## 3. SchemaField Definitions

`SchemaField` is the abstract base for all field types. It is a frozen dataclass that carries everything needed to render in every context — form, table column, and filter widget.

### All SchemaField options

```python
@dataclass(frozen=True, kw_only=True)
class SchemaField(ABC, Generic[T]):
    name: str                              # Field name, matches the model attribute
    label: str | None = None               # Display label (auto-derived from name if None)
    help_text: str | None = None           # Tooltip or help text shown below the field
    placeholder: str | None = None         # Placeholder text inside the form input

    nullable: bool = True                  # Whether None is a valid value
    readonly: bool = False                 # Whether the field is read-only in forms
    required: bool = False                 # Whether the field requires a value
    sortable: bool = True                  # Whether the list table column is sortable
    searchable: bool = False               # Whether the field is included in searches
    filterable: bool = True                # Whether a filter widget is rendered for this field

    visible_in_form: bool = True           # Show in create/edit forms
    visible_in_list: bool = True           # Show in the list table
    visible_in_view: bool = True           # Show in the read-only detail view

    validators: list[FieldValidator] = field(default_factory=list)
    default: T | None = None               # Default value when creating a new record
```

### Field types taxonomy

#### Text & string fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `TextField` | `<input type="text">` | Plain text | Common single-line text |
| `EmailField` | `<input type="email">` | `mailto:` link | Email addresses |
| `PasswordField` | `<input type="password">` | `••••••` | Masked in columns |
| `URLField` | `<input type="url">` | Clickable link | Opens in new tab |
| `TextAreaField` | `<textarea>` | Plain text | Multi-line text |
| `MarkdownField` | Rich markdown editor | Rendered markdown | Supports preview |
| `RichTextField` | WYSIWYG editor | Rendered HTML | Full rich text |

```python
TextField(name="title", required=True, sortable=True, searchable=True)
EmailField(name="email", required=True, label="Email Address")
URLField(name="website", placeholder="https://example.com")
PasswordField(name="password", visible_in_list=False)
TextAreaField(name="bio", rows=5, help_text="Tell us about yourself")
```

#### Numeric fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `IntegerField` | `<input type="number">` | Integer text | Whole numbers only |
| `FloatField` | `<input type="number" step="any">` | Decimal text | Floating point |
| `NumberField` | `<input type="number">` | Number text | Generic numeric |
| `CurrencyField` | `<input type="number">` | Formatted currency | Takes `currency` kwarg (e.g. `"USD"`) |

```python
IntegerField(name="age", min_value=0, max_value=150)
FloatField(name="price", required=True, min_value=0)
CurrencyField(name="revenue", currency="USD")
```

#### Boolean fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `BooleanField` | Checkbox | Check/cross icon | Standard boolean |
| `ToggleField` | Toggle switch | Check/cross icon | Always renders a switch |

```python
BooleanField(name="is_active", label="Active")
ToggleField(name="notifications", label="Push Notifications")
```

#### Selection fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `SelectField` | `<select>` dropdown | Label text | Options as `list[tuple[str, str]]` or `dict[str, str]` |
| `EnumField` | `<select>` dropdown | Label text | Auto-derives options from `enum_cls` |
| `MultiSelectField` | Multi-select | Comma-separated tags | Multiple values |
| `RadioField` | Radio button group | Label text | Single selection |

```python
SelectField(
    name="status",
    options={
        "draft": "Draft",
        "published": "Published",
        "archived": "Archived",
    },
    default="draft",
    sortable=True,
)

EnumField(name="role", enum_cls=UserRole)

MultiSelectField(
    name="tags",
    options=[("python", "Python"), ("js", "JavaScript"), ("rust", "Rust")],
)
```

#### Date & time fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `DateField` | Date picker | Formatted date | Date only |
| `DateTimeField` | DateTime picker | Formatted datetime | Date + time |
| `TimeField` | Time picker | Formatted time | Time only |

```python
DateField(name="published_at", nullable=True, sortable=True)
DateTimeField(name="created_at", label="Created")
TimeField(name="opens_at", help_text="Store opening time")
```

#### Composite & misc fields

| Field | Form | Column | Notes |
|-------|------|--------|-------|
| `JsonField` | JSON editor | Formatted JSON | Structured data |
| `ColorField` | Color picker | Color swatch | Hex color values |
| `TagsField` | Tag input | Tag badges | Comma/keyword tags |
| `KeyValueField` | Key-value pairs | Table display | Arbitrary metadata |
| `FileField` | File upload | File link | Uploaded files |
| `ImageField` | Image upload | Thumbnail | Uploaded images |
| `AvatarField` | Image upload | Circular avatar | `size` kwarg (default 40) |
| `RatingField` | Star rating | Star icons | Numeric rating |
| `HiddenField` | Hidden input | Hidden | Set programmatically |

#### Relation fields

| Field | Purpose |
|-------|---------|
| `BelongsToField` | Belongs-to relationship (FK lookup) |
| `HasManyField` | Has-many relationship |
| `MorphField` | Polymorphic relationship |
| `RelationField` | Generic relation field |

### Validators

Validators are `FieldValidator` protocol instances. You attach them to any `SchemaField` via the `validators` list:

```python
from lexigram.admin.schema import (
    EmailValidator,
    LengthValidator,
    RangeValidator,
    PatternValidator,
    RequiredValidator,
    URLValidator,
)

TextField(
    name="username",
    validators=[
        RequiredValidator(),
        LengthValidator(min_length=3, max_length=50),
        PatternValidator(r"^[a-zA-Z0-9_]+$"),
    ],
)
NumberField(name="age", validators=[RangeValidator(min_value=0, max_value=150)])
EmailField(name="email", validators=[EmailValidator()])
URLField(name="site", validators=[URLValidator()])
```

Each validator returns `Ok(value)` on success or `Err(FieldError)` on failure. Validators run in order — the first failure short-circuits.

### Derived attributes from `fields`

When `Resource.fields` is set and `columns`/`filters`/`form_class` are **not** explicitly set on the class, the following derivation happens automatically in `__init_subclass__`:

```python
# Auto-derived (behind the scenes):
cls.columns = list(cls.fields)              # Each field knows how to render_column()
cls.filters = [f for f in cls.fields if getattr(f, "filterable", False)]
```

If you **do** set any of `columns`, `filters`, or `form_class` alongside `fields`, the framework emits a `DeprecationWarning` and your explicit definitions take precedence.

---

## 4. Actions

Actions are the primary way users interact with records. The framework provides three action categories — row, bulk, and header — with a full lifecycle for visibility, authorization, confirmation, and execution.

### Standard actions

Import and attach ready-to-use actions:

```python
from lexigram.admin.actions.standard import EditAction, ViewAction, DeleteAction, CreateAction, DeleteBulkAction

class PostResource(Resource):
    actions = [EditAction(), ViewAction(), DeleteAction()]
    bulk_actions = [DeleteBulkAction()]
    # Header actions are defined separately via config or legacy attribute
```

| Standard Action | Category | Icon | Color | Confirmation |
|----------------|----------|------|-------|-------------|
| `EditAction` | Row | `pencil` | `PRIMARY` | No |
| `ViewAction` | Row | `eye` | `GRAY` | No |
| `DeleteAction` | Row | `trash` | `DANGER` | Yes |
| `CreateAction` | Header | `plus` | `PRIMARY` | No |
| `DeleteBulkAction` | Bulk | `trash` | `DANGER` | Yes |

### Action hierarchy

```
Action[R, Outcome]               (abstract base)
├── RowAction[Any, Any]          # operates on a single record
├── BulkAction[list[Any], Any]   # operates on multiple selected records
└── HeaderAction[None, Any]      # no record context, rendered in header
```

### Action lifecycle hooks

Every action subclass can override these hooks, all of which are optional:

```python
class MyAction(RowAction):
    # 1. VISIBILITY — hide the action for certain records
    def visible_for(self, record: Any, user: Any | None = None) -> bool:
        return record.status != "archived"

    # 2. AUTHORIZATION — reject unauthorized users
    def authorize(self, record: Any, user: Any | None = None) -> Result[None, PermissionDenied]:
        if user and user.is_admin:
            return Ok(None)
        return Err(PermissionDenied("Admins only"))

    # 3. CONFIRMATION — show a dialog before executing
    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Archive Post",
            message="This will hide the post from the public site.",
            style=ActionColor.WARNING,
        )

    # 4. PARAMETER COLLECTION — optional form before execution
    def form(self) -> Any | None:
        return None

    # 5. EXECUTION — the actual work
    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        ...
```

### Custom action example

```python
from lexigram.admin.actions.base import RowAction
from lexigram.admin.actions.types import ActionColor, ActionContext
from lexigram.result import Ok, Result

class PublishAction(RowAction):
    """Publish a draft post."""

    def __init__(self):
        super().__init__(
            name="publish",
            label="Publish",
            icon="send",
            color=ActionColor.SUCCESS,
        )

    def visible_for(self, record: Any, user: Any | None = None) -> bool:
        return record.status == "draft"

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Publish Post",
            message="This will make the post visible to everyone.",
            style=ActionColor.WARNING,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        await publish_service.publish(record.id)
        return Ok({"message": f"Published #{record.id}", "published": True})


class ArchiveBulkAction(BulkAction):
    """Archive multiple posts at once."""

    def __init__(self):
        super().__init__(
            name="archive",
            label="Archive Selected",
            icon="archive",
            color=ActionColor.WARNING,
        )

    async def execute(self, records: list[Any], ctx: ActionContext) -> Result[Any, Any]:
        count = len(records)
        async with bulk_archive_service.batch() as batch:
            for record in records:
                await batch.archive(record.id)
        return Ok({"message": f"Archived {count} posts", "archived_count": count})


class ExportAllAction(HeaderAction):
    """Export all records to CSV."""

    def __init__(self):
        super().__init__(
            name="export",
            label="Export All",
            icon="download",
            color=ActionColor.INFO,
        )

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        csv_data = await export_service.export_all()
        return Ok({"message": "Export complete", "csv": csv_data})
```

Attaching custom actions:

```python
class PostResource(Resource):
    actions = [EditAction(), PublishAction(), DeleteAction()]
    bulk_actions = [ArchiveBulkAction()]
```

### Action types and enums

| Type | Purpose |
|------|---------|
| `ActionColor` | `GRAY`, `PRIMARY`, `SUCCESS`, `WARNING`, `DANGER`, `INFO` |
| `ActionContext` | Carries `request`, `user`, `resource_name` |
| `ConfirmationConfig` | `title`, `message`, `style` |

### Action exceptions

| Exception | Code | When |
|-----------|------|------|
| `ActionError` | `LEX_ERR_ADMIN_ACTION_001` | Base for all action errors |
| `PermissionDenied` | `LEX_ERR_ADMIN_ACTION_002` | User lacks permission |

All actions return `Result[Outcome, ActionError]` from `execute()`. On `Ok`, the UI may display the `message`. On `Err`, the error is surfaced to the user.

---

## 5. Pages

Every `Resource` auto-generates four standard pages. You can customize any of them by subclassing the corresponding page class.

### Default pages

| Page | Path | Purpose |
|------|------|---------|
| `ListPage` | `/{resource_name}` | Table with search, pagination, filters |
| `CreatePage` | `/{resource_name}/new` | Form to create a new record |
| `EditPage` | `/{resource_name}/{id}/edit` | Form pre-filled with existing record |
| `ViewPage` | `/{resource_name}/{id}` | Read-only detail with relation panels |

### Customizing pages

```python
from lexigram.admin.pages.resource_pages import ListPage, ViewPage
from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse

class CustomListPage(ListPage):
    title = "Browse Posts"

    async def view(self, request: Any) -> PageResponse:
        response = await super().view(request)
        # Override to inject custom context, stats, etc.
        response.context["stats"] = await stats_service.get_overview()
        return response


class DraftListPage(Page):
    """A completely custom page — not tied to the default CRUD flow."""

    title = "Draft Queue"

    def __init__(self):
        self.path = "/admin/content/posts/drafts"

    async def view(self, request: Any) -> PageResponse:
        drafts = await post_service.find_by_status("draft")
        return PageResponse(
            content=f"<div>Found {len(drafts)} drafts</div>",
            title=self.title,
        )
```

### Form display modes

The `form_display_mode` attribute controls how create/edit forms are presented:

| Mode | Behavior |
|------|----------|
| `"modal"` | Centered modal dialog (default) |
| `"page"` | Full-page form |
| `"slider"` | Side panel slider |

```python
class UserResource(Resource):
    form_display_mode = "slider"  # Side panel for quick editing
```

### Lifecycle hooks on Resource

The Resource class provides hooks that fire before and after each CRUD operation:

```python
class PostResource(Resource):
    async def before_create(self, data: dict) -> dict:
        data["slug"] = slugify(data.get("title", ""))
        return data

    async def after_create(self, record: Any) -> None:
        await audit_service.log("post_created", record.id)

    async def before_update(self, item_id: Any, data: dict) -> dict:
        data["updated_at"] = datetime.utcnow()
        return data

    async def after_update(self, record: Any) -> None:
        await cache_service.invalidate(f"post:{record.id}")

    async def before_delete(self, item_id: Any) -> None:
        if not await post_service.can_delete(item_id):
            raise PermissionError("Cannot delete published post")

    async def after_delete(self, item_id: Any) -> None:
        await cache_service.invalidate(f"post:{item_id}")
```

---

## 6. Relations

Relations let you display and edit related records inline on a resource's ViewPage. They are powered by `RelationManager` subclasses.

### RelationManager anatomy

```python
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.schema import TextField, DateField


class PostCommentsRelation(RelationManager):
    # Required: used as the URL segment and panel heading
    relationship_name = "comments"

    # Optional: inline editing policy (all True by default)
    inline_create = True
    inline_edit = True
    inline_delete = True
    inline_detach = False

    # Required: define the table columns for the related records
    @classmethod
    def table(cls, table_config=None):
        return [
            TextField(name="author"),
            TextField(name="content"),
            DateField(name="created_at"),
        ]

    # Required: fetch the related records for the parent
    async def get_query(self):
        return await comment_service.find_by_post(self.parent_id)

    # Optional: permission predicates
    def can_create(self, user=None):
        return Ok(None) if user else Err(PermissionDeniedError())

    def can_edit(self, record, user=None):
        return Ok(None) if user else Err(PermissionDeniedError())

    def can_delete(self, record, user=None):
        return Ok(None) if user else Err(PermissionDeniedError())

    # Optional: custom inline forms
    def create_form(self) -> str | None:
        return '<form hx-post="...">...</form>'

    def edit_form(self, record: Any) -> str | None:
        return f'<form hx-put="...">{record.author}</form>'
```

### Attaching relations to a Resource

```python
class PostResource(Resource):
    relations = [PostCommentsRelation]
```

Multiple relations are supported — each renders as a separate panel on the ViewPage, lazy-loaded via HTMX:

```python
class PostResource(Resource):
    relations = [PostCommentsRelation, PostRevisionsRelation, PostMetaRelation]
```

### AbstractRelationManager (base class)

The `RelationManager` extends `AbstractRelationManager`, which provides:

| Method | Purpose |
|--------|---------|
| `table(cls, table_config)` | Define columns for related records |
| `get_query()` | Fetch related records |
| `count()` | Count related records |
| `get_items(page, per_page)` | Paginated related records |
| `get_relationship_name()` | Derived from `relationship_name` or class name |

---

## 7. Cluster (Navigation)

Clusters group resources and pages together in the admin sidebar. A `Resource` declares its cluster membership with the `cluster` class attribute (string key).

```python
class PostResource(Resource):
    cluster = "content"

class CategoryResource(Resource):
    cluster = "content"

class UserResource(Resource):
    cluster = "users"
```

Clusters are defined as `Cluster` dataclass instances at registration time:

```python
from lexigram.admin.clusters.base import Cluster

content_cluster = Cluster(
    name="content",
    label="Content",
    icon="file-text",
    order=1,
    collapsible=True,
    collapsed_by_default=False,
)

users_cluster = Cluster(
    name="users",
    label="Users & Access",
    icon="users",
    order=2,
)

# At registration time, resources and pages are populated:
content_cluster.resources.append(PostResource)
content_cluster.resources.append(CategoryResource)
users_cluster.resources.append(UserResource)
```

### Cluster dataclass

| Attribute | Type | Default | Purpose |
|-----------|------|---------|---------|
| `name` | `str` | — | Unique cluster key |
| `label` | `str` | — | Display name in sidebar |
| `icon` | `str \| None` | `None` | Lucide icon identifier |
| `order` | `int` | `0` | Sort order in sidebar |
| `collapsible` | `bool` | `True` | Can be collapsed |
| `collapsed_by_default` | `bool` | `False` | Start collapsed |
| `resources` | `list[type]` | `[]` | Populated at registration |
| `pages` | `list[type]` | `[]` | Populated at registration |

---

## 8. Data Source

Every resource that displays data needs a **data source** — an object that implements the `IDataSource` protocol. This protocol abstracts away whether records come from a SQL database, an HTTP API, an in-memory store, or a search index.

### The IDataSource protocol

```python
from lexigram.admin.data.data_source import IDataSource, QueryResult

class MyAPIAdapter:
    """Implements IDataSource protocol — no base class needed."""

    async def find_one(self, item_id: Any) -> dict | None:
        """Fetch a single record by ID."""
        ...

    async def find_many(self, query: Any) -> QueryResult[dict]:
        """Fetch multiple records matching a query."""
        ...

    async def count(self, query: Any) -> int:
        """Count records matching a query."""
        ...

    async def create(self, data: dict[str, Any]) -> dict:
        """Create a new record."""
        ...

    async def update(self, item_id: Any, data: dict[str, Any]) -> dict:
        """Update an existing record."""
        ...

    async def delete(self, item_id: Any) -> bool:
        """Delete a record. Return True on success."""
        ...

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[dict]:
        """Create multiple records."""
        ...

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        """Update multiple records. Return count of updated."""
        ...

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Delete multiple records. Return count of deleted."""
        ...
```

### SQL data source

For SQL backends, `SqlDataSource` provides a ready-to-use base class:

```python
from lexigram.admin.data.data_source import SqlDataSource

class PostDataSource(SqlDataSource):
    def __init__(self, db: DatabaseProviderProtocol):
        super().__init__(db, table_name="posts", id_field="id")
```

`SqlDataSource` implements every `IDataSource` method using parameterized SQL with proper identifier quoting.

### Attaching a data source to a Resource

```python
resource = PostResource()
resource.set_data_source(PostDataSource(db))
```

The `set_data_source` method validates the protocol at runtime:

```python
def set_data_source(self, data_source: IDataSource) -> None:
    if not isinstance(data_source, IDataSource):
        raise TypeError(
            f"data_source must implement IDataSource, got {type(data_source).__name__}"
        )
    self._data_source = data_source
```

### QueryBuilder

The `Resource.fetch_list` method uses `QueryBuilder` to construct query objects from pagination, search, filter, and sort parameters:

```python
from lexigram.admin.data.query_builder import QueryBuilder

# Constructed behind the scenes in Resource.fetch_list():
query = (
    QueryBuilder.create()
    .page(page, limit)
    .search(term, search_fields)
    .order_by(sort_by, sort_order)
    .where_eq("status", "published")
    .where_in("category_id", [1, 2, 3])
    .build()
)
```

---

## 9. Full Example

A complete `BlogPostResource` that ties together fields, actions, pages, relations, cluster, data source, permissions, search, and lifecycle hooks:

```python
from __future__ import annotations

from typing import Any

from lexigram.admin.actions.base import RowAction
from lexigram.admin.actions.standard import CreateAction, DeleteAction, EditAction
from lexigram.admin.actions.types import ActionColor, ActionContext, ConfirmationConfig
from lexigram.admin.data.data_source import IDataSource
from lexigram.admin.pages.resource_pages import ListPage
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import (
    BooleanField,
    DateField,
    SelectField,
    TextAreaField,
    TextField,
)
from lexigram.result import Ok, Result


# -- Custom action --

class PublishAction(RowAction):
    def __init__(self):
        super().__init__(
            name="publish",
            label="Publish",
            icon="send",
            color=ActionColor.SUCCESS,
        )

    def visible_for(self, record: Any, user: Any | None = None) -> bool:
        return getattr(record, "status", None) == "draft"

    def confirm(self) -> ConfirmationConfig | None:
        return ConfirmationConfig(
            title="Publish Post",
            message="This will make the post visible on the public site.",
            style=ActionColor.WARNING,
        )

    async def execute(self, record: Any, ctx: ActionContext) -> Result[Any, Any]:
        await publish_service.publish(record.id)
        return Ok({"message": f"Published #{record.id}"})


# -- Custom page --

class PostListPage(ListPage):
    title = "All Posts"

    async def view(self, request: Any) -> PageResponse:
        response = await super().view(request)
        response.context["stats"] = await post_stats()
        return response


# -- Relation manager --

class PostCommentsRelation(RelationManager):
    relationship_name = "comments"

    @classmethod
    def table(cls, table_config=None):
        from lexigram.admin.schema import DateTimeField, EmailField
        return [
            TextField(name="author", sortable=True),
            EmailField(name="email"),
            TextField(name="content"),
            DateTimeField(name="created_at", sortable=True),
        ]

    async def get_query(self):
        return await comment_service.find_by_post(self.parent_id)


class PostRevisionsRelation(RelationManager):
    relationship_name = "revisions"
    inline_create = False
    inline_edit = False
    inline_delete = True

    @classmethod
    def table(cls, table_config=None):
        from lexigram.admin.schema import DateTimeField
        return [
            TextField(name="title"),
            TextField(name="author"),
            DateTimeField(name="created_at", sortable=True),
        ]

    async def get_query(self):
        return await revision_service.find_by_post(self.parent_id)


# -- Resource --

class BlogPostResource(Resource):
    # Identity
    model = BlogPost
    name = "posts"
    label = "Blog Posts"
    icon = "file-text"
    cluster = "content"

    # Fields (canonical declaration)
    fields = [
        TextField(name="title", required=True, sortable=True, searchable=True),
        TextField(name="slug", readonly=True, help_text="Auto-generated from title"),
        SelectField(
            name="status",
            options={
                "draft": "Draft",
                "published": "Published",
                "archived": "Archived",
            },
            default="draft",
            sortable=True,
        ),
        TextAreaField(name="excerpt", rows=3, help_text="Short summary for listings"),
        TextAreaField(name="content", rows=20),
        BooleanField(name="featured", label="Featured Post"),
        DateField(name="published_at", nullable=True, sortable=True),
    ]

    # Search
    search_fields = ["title", "excerpt"]
    search_title_field = "title"

    # Actions
    actions = [EditAction(), PublishAction(), DeleteAction()]
    bulk_actions = []  # none for now

    # Relations
    relations = [PostCommentsRelation, PostRevisionsRelation]

    # Form display
    form_display_mode = "page"  # Full-page form for blog posts

    # Custom page
    list_page_class = PostListPage

    # Permissions
    def has_view_permission(self, user: Any) -> bool:
        return user is not None

    def has_add_permission(self, user: Any) -> bool:
        return user and user.is_editor

    def has_change_permission(self, user: Any) -> bool:
        return user and user.is_editor

    def has_delete_permission(self, user: Any) -> bool:
        return user and user.is_admin

    # Lifecycle hooks
    async def before_create(self, data: dict) -> dict:
        data["slug"] = slugify(data.get("title", ""))
        return data

    async def after_create(self, record: Any) -> None:
        await audit_service.log("post_created", record.id)

    async def before_update(self, item_id: Any, data: dict) -> dict:
        if "published_at" not in data and data.get("status") == "published":
            data["published_at"] = datetime.utcnow()
        return data

    async def after_delete(self, item_id: Any) -> None:
        await cache_service.invalidate(f"post:{item_id}")


# -- Data source attachment (at registration) --

class PostDataSource(IDataSource):
    async def find_one(self, item_id): ...
    async def find_many(self, query): ...
    async def count(self, query): ...
    async def create(self, data): ...
    async def update(self, item_id, data): ...
    async def delete(self, item_id): ...
    async def bulk_create(self, items): ...
    async def bulk_update(self, ids, data): ...
    async def bulk_delete(self, ids): ...

# In your registration module:
# resource = BlogPostResource()
# resource.set_data_source(PostDataSource(db))
```

---

## 10. Resources from Plugins

When a plugin contributor declares resources via `get_resources()`, they are
automatically namespaced with the contributor's `package_source`:

```python
from lexigram.contracts.admin import BaseAdminContributor


class MyPluginContributor(BaseAdminContributor):
    name = "my_plugin"
    display_name = "My Plugin"
    package_source = "my_plugin"

    def get_resources(self):
        from my_plugin.resources import WidgetResource
        return [WidgetResource]
```

If `WidgetResource.name = "widgets"`, admin registers it as `"my_plugin.widgets"`
and the route becomes `/admin/my_plugin/widgets/`. This prevents naming collisions
when multiple plugins define a resource called `"widgets"`.

Resources from plugins can be discovered at runtime via the container:

```python
# In any registered service:
from lexigram.admin.contributors.resource_collector import ResourceCollector

collector = await container.resolve(ResourceCollector)
all_resources = collector.collect()  # includes plugin resources
```

See the [Extension Developer Guide](./EXTENSION_DEVELOPER_GUIDE.md) for a complete
walkthrough of writing a plugin.

## 11. Migration from Triplet

If you are familiar with the old `forms/fields/` + `ui/columns/` + `ui/filters/` system (the "Triplet API"), see the dedicated migration guide at:

[`docs/MIGRATION_FROM_TRIPLET.md`](MIGRATION_FROM_TRIPLET.md)

### Summary of the new approach

| Before (Triplet) | After (SchemaField) |
|---|---|
| Three separate classes per field type | One `SchemaField` subclass |
| `Resource.columns` + `Resource.filters` + `form_class` | `Resource.fields` (auto-derives all three) |
| Manual sync between form/column/filter | Single source of truth |
| Import from `forms.fields`, `ui.columns`, `ui.filters` | Import from `lexigram.admin.schema` |

### Quick migration

```python
# BEFORE (old style)
class UserResource(Resource):
    columns = [
        TextColumn("name").sortable().searchable(),
        TextColumn("email").sortable().searchable(),
        DateColumn("created_at").datetime().sortable(),
        BadgeColumn("role", colors={"admin": "purple", "guest": "gray"}),
    ]
    filters = [SelectFilter("role", options=["admin", "guest"])]

# AFTER (new style)
class UserResource(Resource):
    fields = [
        TextField(name="name", sortable=True, searchable=True),
        TextField(name="email", sortable=True, searchable=True),
        SelectField(
            name="role",
            options={"admin": "Admin", "guest": "Guest"},
            sortable=True,
        ),
        DateField(name="created_at", label="Created", sortable=True),
    ]
```

### Transitional approach

During migration you can define both `fields` and `columns` — but the framework will emit a `DeprecationWarning`. Plan to remove the explicit `columns` and `filters` once the SchemaField equivalents are verified.
