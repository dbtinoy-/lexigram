# How-To Guides

Task-oriented recipes for `lexigram-admin`.

## Register a resource

```python
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import TextField, EmailField

class UserResource(Resource):
    model = User
    name = "users"
    cluster = "users"
    fields = [
        TextField("name", required=True),
        EmailField("email", required=True),
    ]

AdminModule.configure(resources=[UserResource])
```

## Add a custom action

```python
from lexigram.admin.actions.base import RowAction
from lexigram.admin.actions.types import ActionColor
from lexigram.result import Ok

class ApproveAction(RowAction):
    def __init__(self):
        super().__init__(name="approve", label="Approve", icon="check", color=ActionColor.SUCCESS)

    async def execute(self, record, ctx):
        record.status = "approved"
        return Ok({"message": "Approved"})
```

Attach via `actions = [ApproveAction()]` on your Resource.

## Add a bulk action

```python
from lexigram.admin.actions.base import BulkAction

class ArchiveBulkAction(BulkAction):
    def __init__(self):
        super().__init__(name="archive", label="Archive Selected", icon="archive", color=ActionColor.WARNING)

    async def execute(self, records, ctx):
        count = len(records)
        return Ok({"message": f"Archived {count} records"})
```

Attach via `bulk_actions = [ArchiveBulkAction()]` on your Resource.

## Add a custom page

```python
from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse

class StatsPage(Page):
    title = "Statistics"
    path = "/admin/stats"

    async def view(self, request):
        return PageResponse(title=self.title, content="<div>Stats here</div>")
```

Register via `AdminModule.configure(pages=[StatsPage])` or through a contributor.

## Add a relation manager

```python
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.schema import TextField

class CommentsRelation(RelationManager):
    relationship_name = "comments"

    @classmethod
    def table(cls, table_config=None):
        return [TextField("author"), TextField("content")]

    async def get_query(self):
        return await comment_service.find_by_post(self.parent_id)
```

Attach via `relations = [CommentsRelation]` on your Resource.

## Configure search

```python
class UserResource(Resource):
    search_fields = ["name", "email"]
    search_title_field = "name"
```

## Add a dashboard widget

```python
from lexigram.contracts.admin.types import DashboardWidgetDefinition, WidgetCategory, WidgetSize

class MyContributor(BaseAdminContributor):
    def get_dashboard_widgets(self):
        return [
            DashboardWidgetDefinition(
                name="stats_widget",
                title="Quick Stats",
                contributor="my_plugin",
                render_endpoint="/admin/my_plugin/stats",
                size=WidgetSize.SMALL,
                category=WidgetCategory.METRICS,
                refresh_interval_seconds=60,
            ),
        ]

    def get_routes(self):
        return [
            AdminRouteSpec(
                path="/admin/my_plugin/stats",
                method="GET",
                handler=self.render_stats,
                name="stats",
            ),
        ]
```

## Write a plugin contributor

```python
from lexigram.contracts.admin import BaseAdminContributor
from lexigram.contracts.admin.types import ManagementPageDefinition, PageCategory

class MyContributor(BaseAdminContributor):
    name = "my_plugin"
    display_name = "My Plugin"
    package_source = "my_plugin"
    group = "plugins"
    icon = "puzzle"

    def get_resources(self):
        return [WidgetResource]

    def get_management_pages(self):
        return [
            ManagementPageDefinition(
                name="overview",
                title="Plugin Overview",
                contributor="my_plugin",
                route_path="/admin/my_plugin/overview",
                handler=OverviewPage(),
                category=PageCategory.CONFIGURATION,
            ),
        ]

    def get_dashboard_widgets(self):
        return [...]
```

Register via `[project.entry-points."lexigram.admin.contributors"]` in `pyproject.toml`.

## Customize the form display mode

```python
class UserResource(Resource):
    form_display_mode = "slider"  # "modal" (default), "page", or "slider"
```

## Use lifecycle hooks

```python
class PostResource(Resource):
    async def before_create(self, data: dict) -> dict:
        data["slug"] = slugify(data.get("title", ""))
        return data

    async def after_create(self, record: Any) -> None:
        await audit_service.log("post_created", record.id)
```

## Notes

- Always use `fields` instead of legacy `columns`/`filters`/`form_class`.
- Actions return `Result[Outcome, ActionError]` — handle both Ok and Err.
- Contributors are discovered via `lexigram.admin.contributors` entry point group.
- Namespacing is automatic using the contributor's `package_source`.
