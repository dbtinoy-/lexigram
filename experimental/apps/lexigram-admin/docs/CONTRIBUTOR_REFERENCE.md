# Contributor Reference

Exhaustive reference for `BaseAdminContributor`.

## Metadata Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `""` | Unique identifier. Used for runtime lookups and as the contributor_id. |
| `display_name` | `str` | `""` | Human-readable name shown in dashboards and admin UI. |
| `group` | `str` | `"framework"` | Navigation group for sidebar grouping. |
| `icon` | `str` | `"box"` | Lucide icon identifier. |
| `priority` | `int` | `100` | Boot order. Lower = earlier. |
| `version` | `str` | `"0.0.0"` | Contributor's version string, shown in admin UI. |
| `package_source` | `str` | `"built-in"` | Namespace prefix for all contributed names. Used to prevent collisions. |
| `required_permissions` | `frozenset[str]` | `frozenset()` | Permissions the current user must have for contributed items to appear. |

## Methods

### `get_resources()`

**Signature:** `() -> Sequence[type[Resource]]`

**Default:** `[]`

Returns Resource classes to register with the admin panel. Each resource
is automatically namespaced with `package_source`.

**Collision policy:** Namespaced — a resource named `"widgets"` from a
contributor with `package_source = "demo"` is registered as
`"demo.widgets"`.

**Permissions:** None — resources are registered for all users. Per-resource
permissions are defined on the Resource class itself.

**Example:**

```python
def get_resources(self):
    from my_plugin.resources import WidgetResource, AuditLogResource
    return [WidgetResource, AuditLogResource]
```

---

### `get_routes()`

**Signature:** `() -> Sequence[AdminRouteSpec]`

**Default:** `[]`

Returns custom Starlette route specifications. Routes are registered at
admin mount time and are accessible under the admin prefix.

**Collision policy:** Namespaced — the route path should include
`package_source` as a prefix to avoid collision.

**Permissions:** The caller is responsible for authorization within the
route handler.

**Example:**

```python
def get_routes(self):
    from lexigram.contracts.admin.types import AdminRouteSpec
    return [
        AdminRouteSpec(
            path="/admin/demo/widgets/count",
            method="GET",
            handler=widget_count_handler,
            name="widgets.count",
        ),
    ]
```

---

### `get_dashboard_widgets()`

**Signature:** `() -> Sequence[DashboardWidgetDefinition]`

**Default:** `[]`

Returns widget definitions for the admin dashboard. Each widget has a
`route_path` that maps to a route handler (typically registered via
`get_routes()` or the contributor's `render_widget` method).

**Collision policy:** Namespaced; the widget name is prefixed with
`package_source`.

**Permissions:** The host (`WidgetController`) enforces each definition's
`permission` field before rendering — a user lacking the declared
permission gets an inline error card and the widget handler is never
called. Superadmin bypasses the gate. With no `permission` declared the
widget is visible to all dashboard users.

**Example:**

```python
def get_dashboard_widgets(self):
    from lexigram.contracts.admin.types import DashboardWidgetDefinition, WidgetKind
    return [
        DashboardWidgetDefinition(
            name="widget_count",
            title="Widget Count",
            view_kind=WidgetKind.STAT,
            render_endpoint="/admin/demo/widgets/count",
            refresh_interval_seconds=60,
        ),
    ]
```

---

### `get_navigation_items()`

**Signature:** `() -> Sequence[NavigationContribution]`

**Default:** `[]`

Returns sidebar navigation entries. Each entry specifies a label, icon,
URL, and priority for ordering.

**Collision policy:** Namespaced; the navigation item name is prefixed
with `package_source`.

**Permissions:** None — items are visible to all users. Use
`required_permissions` on the contributor to restrict all items.

**Example:**

```python
def get_navigation_items(self):
    from lexigram.contracts.admin.types import NavigationContribution
    return [
        NavigationContribution(
            name="demo",
            title="Demo Plugin",
            icon="puzzle",
            url="/admin",
            priority=10,
        ),
    ]
```

---

### `get_management_pages()`

**Signature:** `() -> Sequence[ManagementPageDefinition]`

**Default:** `[]`

Returns custom management pages. Each page is a `Page` instance with a
title, route path, category, and handler.

**Collision policy:** Namespaced; the page name is prefixed with
`package_source`.

**Permissions:** None — all users can access management pages. Use
handler-level auth for fine-grained control.

**Example:**

```python
def get_management_pages(self):
    from lexigram.contracts.admin.types import ManagementPageDefinition, PageCategory
    return [
        ManagementPageDefinition(
            name="overview",
            title="Plugin Overview",
            route_path="/admin/demo/overview",
            handler=OverviewPage(),
            category=PageCategory.OVERVIEW,
        ),
    ]
```

---

### `get_settings_panels()`

**Signature:** `() -> Sequence[SettingsPanelDefinition]`

**Default:** `[]`

Returns settings panel definitions. Follows the same pattern as
management pages but rendered in the settings section of the admin UI.

**Collision policy:** Namespaced; the panel name is prefixed with
`package_source`.

**Permissions:** None — settings panels are visible to all users with
dashboard access.

**Example:**

```python
def get_settings_panels(self):
    from lexigram.contracts.admin.types import SettingsPanelDefinition
    return [
        SettingsPanelDefinition(
            name="demo_settings",
            title="Demo Settings",
            route_path="/admin/demo/settings",
            handler=DemoSettingsPanel(),
        ),
    ]
```

---

### `get_health_definitions()`

**Signature:** `() -> Sequence[AdminHealthDefinition]`

**Default:** `[]`

Returns health check definitions. Each definition has a name and a
handler that performs the health check.

**Collision policy:** Namespaced; the health check name is prefixed with
`package_source`.

**Permissions:** The host (`WidgetController`) enforces each definition's
`permission` field before executing the check; users lacking the declared
permission receive an HTTP 403. Superadmin bypasses the gate.

**Example:**

```python
def get_health_definitions(self):
    from lexigram.contracts.admin.types import AdminHealthDefinition
    return [
        AdminHealthDefinition(
            name="database",
            handler=check_database_health,
        ),
    ]
```

---

### `get_actions()`

**Signature:** `() -> Sequence[AdminActionDefinition]`

**Default:** `[]`

Returns action definitions. Each action has a name, title, and a handler
path (`module:function` format). The handler is resolved at execution time
via `execute_action()`.

**Collision policy:** Namespaced; the action name is prefixed with
`package_source`.

**Permissions:** None — actions are registered for all users. Use
handler-level authorization.

**Example:**

```python
def get_actions(self):
    from lexigram.contracts.admin.types import AdminActionDefinition
    return [
        AdminActionDefinition(
            name="archive_old",
            title="Archive Old Widgets",
            handler="demo.actions.archive:handle",
        ),
    ]
```

---

### `on_admin_boot(container)`

**Signature:** `(container: ContainerResolverProtocol) -> Awaitable[None]`

**Default:** No-op.

Called after the admin panel is fully booted. Use this hook to perform
one-time initialization that requires resolved dependencies from the
container.

**Permissions:** Not applicable — always called for every contributor.

**Example:**

```python
async def on_admin_boot(self, container):
    cache = await container.resolve(CacheService)
    await cache.warm("demo")
```

---

### `on_admin_shutdown()`

**Signature:** `() -> Awaitable[None]`

**Default:** No-op.

Called when the application is shutting down. Use this hook to release
resources, close connections, or persist state.

**Permissions:** Not applicable.

**Example:**

```python
async def on_admin_shutdown(self):
    await self._connection.close()
```

---

### `execute_action(action_name, params)`

**Signature:** `(action_name: str, params: dict[str, object]) -> Awaitable[object]`

**Default:** Dispatches to the handler registered by `get_actions()`.
Raises `ValueError` if the action name is not found.

Looks up the action definition by name, imports the `module:func` handler,
and calls it with `**params`.

**Raises:**
- `ValueError` — action not registered.

**Example:**

```python
# Called by admin internals. You typically don't override this.
result = await contributor.execute_action("archive_old", {"days": 30})
```

---

### `render_widget(widget_name, params)`

**Signature:** `(widget_name: str, params: WidgetParams) -> Awaitable[Result[str, AdminError]]`

**Default:** Returns `Err(WidgetNotFoundError)`.

Renders a dashboard widget's HTML content. Override this method to provide
dynamic widget rendering that doesn't require a separate route.

**Returns:**
- `Ok(html_string)` — widget rendered successfully.
- `Err(WidgetNotFoundError)` — widget not handled by this contributor.

**Example:**

```python
async def render_widget(self, widget_name, params):
    if widget_name == "widget_count":
        count = await get_widget_count()
        return Ok(f"<div>{count} widgets</div>")
    return await super().render_widget(widget_name, params)
```

---

### `render_health_check(check_name)`

**Signature:** `(check_name: str) -> Awaitable[Result[HealthCheckPayload, AdminError]]`

**Default:** Returns `Err(HealthCheckNotFoundError)`.

Override to implement health checks without separate route handlers.
Return a structured
[`HealthCheckPayload`](#healthcheckpayload) (`status`, `component`,
`detail`, `latency_ms`) — the host (`WidgetController`) owns presentation
and renders it as the same status badge for every contributor, so
contributors must not return pre-rendered HTML.

**Permissions:** The host enforces the matching
`AdminHealthDefinition.permission` before dispatch — a user without the
declared permission gets an HTTP 403 and the check is never executed.

**Returns:**
- `Ok(HealthCheckPayload)` — check succeeded, host renders the badge.
- `Err(HealthCheckNotFoundError)` — check not handled.
- `Err(AdminError)` — check failed.

**Example:**

```python
async def render_health_check(self, check_name):
    if check_name == "database":
        result = await db.ping()
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.DEGRADED if result.degraded else HealthStatus.HEALTHY,
                component="Database",
                detail=result.message,
                latency_ms=result.duration_ms,
            )
        )
    return await super().render_health_check(check_name)
```

---

### `HealthCheckPayload`

Frozen value type (`lexigram.contracts.admin.health_payload`) returned by
`render_health_check`.

| Field | Type | Description |
|-------|------|-------------|
| `status` | `HealthStatus` | `HEALTHY`, `DEGRADED`, `UNHEALTHY`, `STARTING`, or `UNKNOWN` |
| `component` | `str` | Component being checked |
| `detail` | `str` | Human-readable detail (default `""`) |
| `latency_ms` | `float \| None` | Optional probe latency in ms |

---

## Definition Types Reference

### `DashboardWidgetDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique widget name |
| `title` | `str` | Display title |
| `contributor` | `str` | Contributor name (used for namespacing) |
| `render_endpoint` | `str` | HTMX endpoint that renders the widget content |
| `size` | `WidgetSize` | `SMALL`, `MEDIUM`, `LARGE`, or `FULL` |
| `category` | `WidgetCategory` | `HEALTH`, `METRICS`, `ACTIVITY`, `RESOURCES`, or `CUSTOM` |
| `refresh_interval_seconds` | `int` | Auto-refresh interval in seconds |
| `order` | `int` | Display order |
| `icon` | `str \| None` | Lucide icon |
| `description` | `str` | Widget description |
| `permission` | `str \| None` | Required permission to view the widget |

### `NavigationContribution`

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Display label |
| `url` | `str` | Link target |
| `icon` | `str` | Lucide icon (default: `"box"`) |
| `group` | `str` | Navigation group (default: `"framework"`) |
| `order` | `int` | Sort order (default: `100`) |
| `permission` | `str \| None` | Required permission |
| `badge_endpoint` | `str \| None` | HTMX endpoint for a badge |
| `children` | `tuple[NavigationContribution, ...]` | Nested navigation items |

### `ManagementPageDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique page name |
| `title` | `str` | Page title |
| `contributor` | `str` | Contributor name |
| `route_path` | `str` | URL path |
| `handler` | `str \| AdminPageHandlerProtocol` | Page instance or dotted path |
| `category` | `PageCategory` | `INFRASTRUCTURE`, `SECURITY`, `AI`, `DATA`, `MONITORING`, `CONFIGURATION` |
| `icon` | `str` | Lucide icon (default: `"settings"`) |
| `permission` | `str \| None` | Required permission |
| `description` | `str` | Page description |
| `order` | `int` | Display order |

### `SettingsPanelDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique panel name |
| `title` | `str` | Panel title |
| `contributor` | `str` | Contributor name |
| `route_path` | `str` | URL path |
| `handler` | `str \| AdminPageHandlerProtocol` | Page instance or dotted path |
| `icon` | `str` | Lucide icon (default: `"sliders"`) |
| `category` | `str` | Settings category (default: `"General"`) |
| `order` | `int` | Display order |
| `permission` | `str \| None` | Required permission |

### `AdminHealthDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique health check name |
| `contributor` | `str` | Contributor name |
| `component` | `str` | Component being checked |
| `check_endpoint` | `str \| None` | Optional endpoint for the check |
| `icon` | `str` | Lucide icon (default: `"heart-pulse"`) |
| `description` | `str` | Health check description |
| `permission` | `str \| None` | Required permission to view the check |

### `AdminActionDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique action name |
| `title` | `str` | Display title |
| `contributor` | `str` | Contributor name |
| `handler` | `str` | `"module:function"` path |
| `icon` | `str` | Lucide icon (default: `"zap"`) |
| `confirmation_message` | `str \| None` | Confirmation dialog message |
| `permission` | `str \| None` | Required permission |
| `destructive` | `bool` | Whether action is destructive |
| `category` | `str` | Action category |
| `parameter_schema` | `ActionParameterSchema \| None` | Action parameter schema |

### `AdminRouteSpec`

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | URL path |
| `method` | `str` | HTTP method (`GET`, `POST`, `PUT`, `DELETE`) |
| `handler` | `Callable` | Async handler |
| `name` | `str` | Route name |

### `WidgetParams`

| Field | Type | Description |
|-------|------|-------------|
| `request` | `Request` | Starlette request |
| `user` | `Any` | Authenticated user |
| `config` | `dict[str, Any]` | Widget configuration |
