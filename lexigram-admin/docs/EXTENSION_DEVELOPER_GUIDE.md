# Extension Developer Guide

This guide walks you through building a **plugin package** that contributes
capabilities to `lexigram-admin` — resources, pages, widgets, settings panels,
dashboard widgets, navigation items, custom routes, and background actions.

## Who this is for

Third-party package authors who want to extend the admin dashboard without
modifying the host application's `AdminBuilder` calls. If you are writing an
app that uses admin directly, you do not need this guide — just declare your
Resources in the host app's builder.

## Prerequisites

- Python 3.11+
- `lexigram-admin>=0.2.0`
- `lexigram-contracts>=0.2.0`

## 1. Create the package skeleton

```
my-plugin/
├── pyproject.toml
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       └── contributor.py
└── tests/
    └── test_contributor.py
```

**`pyproject.toml`:**

```toml
[project]
name = "my-plugin"
version = "0.1.0"
description = "Example admin plugin"
requires-python = ">=3.11"
dependencies = ["lexigram-admin>=0.2.0", "lexigram-contracts>=0.2.0"]

[project.entry-points."lexigram.admin.contributors"]
my_plugin = "my_plugin.contributor:MyContributor"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

The entry-points block is what makes admin discover your plugin at boot time.
The key (`my_plugin`) becomes the contributor's name in the registry.

## 2. Your first contributor

```python
# src/my_plugin/contributor.py
from lexigram.contracts.admin import BaseAdminContributor

class MyContributor(BaseAdminContributor):
    name = "my_plugin"
    display_name = "My Plugin"
    group = "plugins"
    icon = "puzzle"
    priority = 500
    version = "0.1.0"
    package_source = "my_plugin"
    required_permissions = frozenset()
```

| Field | Required | Default | Purpose |
|---|---|---|---|
| `name` | Yes | `""` | Unique identifier for the contributor |
| `display_name` | Yes | `""` | Human-readable name shown in dashboards |
| `group` | No | `"framework"` | Navigation group for sidebar grouping |
| `icon` | No | `"box"` | Lucide icon identifier |
| `priority` | No | `100` | Lower numbers boot first |
| `version` | No | `"0.0.0"` | Your package version |
| `package_source` | No | `"built-in"` | Used as namespace prefix for contributed names |
| `required_permissions` | No | `frozenset()` | Permissions the current user must have |

That's it — admin discovers this class via the entry point and it's ready
to contribute capabilities.

## 3. Contribute a resource

Resources are the primary way to expose CRUD admin interfaces.

```python
# src/my_plugin/resources/widget.py
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import TextField, EnumField, DateField
from lexigram.admin.rbac.schema import ResourcePermissions

class WidgetResource(Resource):
    model = Widget  # your domain model
    name = "widgets"
    cluster = "plugins"
    icon = "box"

    fields = [
        TextField(name="title", required=True, sortable=True),
        EnumField(name="status", enum=WidgetStatus),
        DateField(name="created_at", sortable=True),
    ]

    permissions = ResourcePermissions(
        can_list={"admin"},
        can_view={"admin"},
        can_create={"admin"},
        can_edit={"admin"},
        can_delete={"admin"},
    )
```

Then wire it into your contributor:

```python
# in contributor.py
def get_resources(self):
    from my_plugin.resources.widget import WidgetResource
    return [WidgetResource]
```

Admin automatically namespaces your resource name with your `package_source`,
so `"widgets"` becomes `"my_plugin.widgets"`. The route prefix becomes
`/admin/my_plugin/widgets`.

### Optional integration knobs

| Attribute | Type | Effect |
|---|---|---|
| `cacheable` | `bool` | Cache `list()` results; auto-invalidate on create/update/delete (requires `lexigram-cache`) |
| `searchable` | `bool` | Index resources on create/update/delete; search via `?q=` (requires `lexigram-search`) |

## 4. Contribute a page

```python
# src/my_plugin/pages/overview.py
from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse, NavigationEntry

class OverviewPage(Page):
    title = "Plugin Overview"
    path = "/admin/my_plugin/overview"

    async def view(self, request):
        return PageResponse(
            title="Plugin Overview",
            content="<div>Custom page content</div>",
        )
```

Wire into your contributor:

```python
from lexigram.contracts.admin.types import ManagementPageDefinition, PageCategory

def get_management_pages(self):
    from my_plugin.pages.overview import OverviewPage
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
```

## 5. Contribute a settings panel

Same pattern as pages but uses `SettingsPanelDefinition`:

```python
from lexigram.contracts.admin.types import SettingsPanelDefinition

def get_settings_panels(self):
    return [
        SettingsPanelDefinition(
            name="demo_settings",
            title="Demo Settings",
            contributor="my_plugin",
            route_path="/admin/my_plugin/settings",
            handler=DemoSettingsPanel(),
        ),
    ]
```

## 6. Contribute a dashboard widget

Widgets are composed of two parts: a **definition** (metadata for the
dashboard layout) and a **route** (endpoint that renders the widget's
HTML fragment).

```python
# src/my_plugin/widgets/widget_count.py
from lexigram.contracts.admin.types import DashboardWidgetDefinition, WidgetType

def make_widget_definitions():
    return [
        DashboardWidgetDefinition(
            name="widget_count",
            title="Widget Count",
            contributor="my_plugin",
            render_endpoint="/admin/my_plugin/widgets/count",
            size=WidgetSize.SMALL,
            category=WidgetCategory.METRICS,
            refresh_interval_seconds=60,
            description="Widget count metric",
        ),
    ]
```

Wire into your contributor:

```python
def get_dashboard_widgets(self):
    from my_plugin.widgets.widget_count import make_widget_definitions
    return make_widget_definitions()

def get_routes(self):
    from lexigram.contracts.admin.types import AdminRouteSpec
    return [
        AdminRouteSpec(
            path="/admin/my_plugin/widgets/count",
            method="GET",
            handler=self.render_widget_count,
            name="widgets.count",
        ),
    ]
```

## 7. Contribute an action

Actions can be row-level, bulk, or header actions:

```python
from lexigram.admin.actions.standard import ExportAction, ExportBulkAction

class ArchiveWidgetsAction(ExportBulkAction):
    name = "archive_old"
    label = "Archive Selected"
    # Optional: run via background tasks
    task_runner = "tasks"  # requires lexigram-tasks

    async def execute(self, records, ctx):
        for record in records:
            record.status = "archived"
        return Ok({"archived": len(records)})
```

Wire into your contributor:

```python
def get_actions(self):
    from lexigram.contracts.admin.types import AdminActionDefinition
    return [
        AdminActionDefinition(
            name="archive_old",
            title="Archive Selected",
            contributor="my_plugin",
            handler="my_plugin.actions.archive_old:handle",
        ),
    ]
```

## 8. Contribute navigation

```python
from lexigram.contracts.admin.types import NavigationContribution

def get_navigation_items(self):
    return [
        NavigationContribution(
            label="Plugins",
            url="/admin",
            icon="puzzle",
            group="plugins",
            order=10,
        ),
    ]
```

## 9. Permissions and RBAC

Each contributor has a `required_permissions` frozenset. The current user
must have all permissions in the set for the contributor's items to appear.

Resources can also define their own `ResourcePermissions` that restrict
CRUD operations by role:

```python
from lexigram.admin.rbac.schema import ResourcePermissions

permissions = ResourcePermissions(
    can_list={"admin", "viewer"},
    can_view={"admin", "viewer"},
    can_create={"admin"},
    can_edit={"admin"},
    can_delete={"admin"},
)
```

## 10. Naming and collisions

Admin namespaces every contributed name using `package_source.name`. If
two contributors both register a resource called `"widgets"`, admin
distinguishes them as `"pkg1.widgets"` and `"pkg2.widgets"`.

There is a configurable collision policy:

```python
AdminConfig(contributor_collision_mode="warn")   # default — log warning
AdminConfig(contributor_collision_mode="error")  # raise on collision
```

In `warn` mode, the first contributor's name wins. In `error` mode, a
`NameCollisionError` is raised.

## 11. Test your contributor

```python
# tests/test_contributor.py
from lexigram.contracts.admin import BaseAdminContributor
from my_plugin.contributor import MyContributor

def test_is_valid_contributor():
    assert issubclass(MyContributor, BaseAdminContributor)

def test_has_required_metadata():
    c = MyContributor()
    assert c.name == "my_plugin"
    assert c.package_source == "my_plugin"

def test_resources_are_namespaced():
    c = MyContributor()
    for r in c.get_resources():
        name = getattr(r, "name", "") or r.__name__
        assert name.startswith("my_plugin."), f"{name} is not namespaced"
```

## 12. Publish to PyPI

1. Set version in `pyproject.toml`.
2. Build: `uv build`
3. Publish: `uv publish`
4. Users install: `uv pip install my-plugin`

## 13. Troubleshooting

**"My contributor is not showing up"**
- Verify the entry point group: `lexigram.admin.contributors`
- Run: `python -c "from importlib.metadata import entry_points; print(list(entry_points(group='lexigram.admin.contributors')))"`
- Check that your package is installed in the same environment as admin.

**"Name collision error"**
- Two contributors are trying to register the same name.
- Switch to `warn` mode or rename one of them.

**"Optional integration not working"**
- Ensure the optional package is installed: `uv pip list | grep lexigram-cache`
- Check that you've set the declarative knob (e.g., `cacheable=True`).

**"Import error"**
- Admin uses lazy imports. Ensure your handler modules are importable at
  resolution time, not at package import time.
