# Quickstart

Get up and running in minutes.

## Install

```bash
uv add lexigram-admin
# Optional: install extras for auth, caching, search
uv add "lexigram-admin[auth,cache,search,export]"
```

## Basic Usage

```python
from __future__ import annotations

from lexigram import Application
from lexigram.admin import AdminModule
from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import TextField, EmailField, BooleanField, DateField


class UserResource(Resource):
    model = None
    name = "users"
    cluster = "users"
    icon = "users"
    fields = [
        TextField(name="name", required=True, sortable=True, searchable=True),
        EmailField(name="email", required=True),
        BooleanField(name="is_active", label="Active"),
        DateField(name="created_at", sortable=True),
    ]


module = AdminModule.configure(resources=[UserResource])
app = Application(modules=[module])

if __name__ == "__main__":
    app.run()
```

## What Just Happened

1. `AdminModule.configure()` created a `DynamicModule` with the admin
   bundle provider, registering your resource, its auto-derived CRUD
   pages, and the admin router.
2. `Application(modules=[...])` booted the DI container, resolved the
   admin provider, mounted the admin sub-app at `/admin`.
3. Visiting `/admin/users/` shows a sortable, searchable, filterable
   list page — with zero frontend code.
4. Visiting `/admin/users/create` renders an auto-generated form from
   your SchemaField definitions.

## Next Steps

- [Guide](./GUIDE.md)
- [How-Tos](./HOWTOS.md)
- [Configuration](./CONFIGURATION.md)
