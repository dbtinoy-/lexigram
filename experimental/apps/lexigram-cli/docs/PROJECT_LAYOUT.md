# Lexigram Project Layout — Implemented

**One project layout.** Every project has the same tree, built from the same
48 `lexigram gen` generators against one canonical generator→path map
(`lexigram/cli/layout.py`), so scaffolding and code generation stay in
lockstep.

There is no `--structure` flag and no `[tool.lexigram] structure` key. What
used to be three project shapes is one shape plus a *per-node* fact: whether
that node has joined a module.

Implementation status (all shipped in this CLI):

- `lexigram new project --template <t>` — 6 templates, one layout
- `lexigram new module <name>` — bounded-context creation + registry
- `lexigram gen <generator> <name> [--module <feature>]` — path resolution
- Canonical map enforced by the dev gate (`dev/checks/generator_output.py`)
  and the unit suite (`tests/unit/test_layout.py`)
- SDK renames `src/graphql → src/schema` (+ `schema/dataloaders`) and
  `src/collections → src/vector/collections`

---

## 1. The rule

Two questions decide every path.

1. **Is this component cross-cutting?** Cross-cutting components are one per
   application by definition (errors, middleware, providers, health…). They
   land in `src/<app>/shared/<component>/` and stay there whatever module the
   node belongs to.
2. **Is this node in a module?** A module-local component lands in
   `src/<app>/<component>/` while the node is unscoped, and moves to
   `src/<app>/modules/<slug>/<component>/` the moment it joins a module.

The composition root is always `src/<app>/app.py`, and the ASGI target is
always `<app>.app:app`.

Unscoped feature code sits at the **app package root**, not in `shared/`, so
`shared/` keeps exactly one meaning: cross-cutting. A project that never
draws a module simply never has a `modules/<slug>/` directory.

---

## 2. The tree

```
my-platform/
├── application.yaml
├── application.production.yaml        # optional profile overlays
├── pyproject.toml                     # [tool.lexigram] module = "my_platform.app:app"
├── README.md
├── .env.example
├── migrations/versions/               # lexigram gen migration
├── seeds/                             # lexigram gen seeder
├── src/
│   └── my_platform/
│       ├── __init__.py
│       ├── app.py                     # create_app() — the composition root
│       ├── py.typed
│       ├── controllers/               # unscoped feature code: app-root components
│       ├── models/                    #   appear as they are generated
│       ├── services/
│       ├── infrastructure/            # framework wiring: db, cache, events, monitoring
│       │   └── __init__.py            # infrastructure_modules()
│       ├── shared/                    # cross-cutting components (see §3)
│       │   ├── errors/
│       │   ├── filters/
│       │   ├── middleware/
│       │   ├── interceptors/
│       │   ├── metrics/
│       │   ├── health/
│       │   ├── audit/
│       │   ├── tenancy/
│       │   ├── features/
│       │   ├── search/
│       │   ├── storage/backends/
│       │   ├── providers/
│       │   ├── schema/dataloaders/
│       │   ├── vector/collections/
│       │   └── mcp/
│       └── modules/
│           ├── __init__.py            # MODULES registry
│           ├── auth/
│           │   ├── __init__.py        # @module AuthModule(controllers=[…], exports=[…])
│           │   ├── protocols.py       # the module contract
│           │   ├── provider.py        # AuthProvider (register/boot/shutdown)
│           │   ├── services.py
│           │   ├── controllers/       # the same components, now module-local
│           │   ├── models/
│           │   ├── repositories/
│           │   └── tests/             # lexigram gen test --module auth
│           └── billing/
│               └── …same shape…
└── tests/
    ├── conftest.py                    # boots create_app()
    ├── test_app.py
    └── unit/                          # lexigram gen test (unscoped)
```

A fresh project ships no sample module: `modules/__init__.py` exports an
empty `MODULES`, and `lexigram new module <name>` fills it in.

---

## 3. Which components are cross-cutting

**Cross-cutting** (`src/<app>/shared/<component>/`, module ignored):

`audit`, `errors`, `features`, `filters`, `health`, `interceptors`, `mcp`,
`metrics`, `middleware`, `providers`, `schema`, `schema/dataloaders`,
`search`, `storage/backends`, `tenancy`, `vector/collections`

**Module-local** (`src/<app>/<component>/` → `src/<app>/modules/<slug>/<component>/`):

`admin/actions`, `admin/resources`, `clients`, `commands`, `consumers`,
`controllers`, `events`, `handlers`, `models`, `notifications`, `pipelines`,
`policies`, `projections`, `queries`, `repositories`, `sagas`, `services`,
`tasks`, `webhooks`, `websocket`, `workflows`

**Project root, never moved**: `migrations/versions`, `seeds`.
`tests/unit` is the exception that follows its node: with `--module auth` a
generated test lands in `src/<app>/modules/auth/tests/`.

---

## 4. Full generator map (48)

Paths below are the *declared* defaults in the generator definitions; the
resolver rewrites them per §1. `src/controllers` therefore means
`src/<app>/controllers` unscoped and `src/<app>/modules/<m>/controllers`
scoped, while `src/errors` always means `src/<app>/shared/errors`.

| Generator(s) | Declared directory |
|---|---|
| controller | `src/controllers` |
| model | `src/models` |
| service | `src/services` |
| repository, cache_repo, document_repo | `src/repositories` |
| provider | `src/providers` |
| query | `src/queries` |
| error | `src/errors` |
| event / event_handler | `src/events` / `src/handlers` |
| command | `src/commands` |
| consumer (message_consumer) | `src/consumers` |
| task | `src/tasks` |
| saga, saga_step | `src/sagas` |
| pipeline | `src/pipelines` |
| projection | `src/projections` |
| workflow_def | `src/workflows` |
| middleware | `src/middleware` |
| interceptor | `src/interceptors` |
| filter, exception_filter | `src/filters` |
| guard, auth_guard | `src/guards` |
| policy (auth_policy) | `src/policies` |
| health | `src/health` |
| metric | `src/metrics` |
| webhook | `src/webhooks` |
| websocket | `src/websocket` |
| api_client | `src/clients` |
| notification_template | `src/notifications` |
| feature_flag | `src/features` |
| tenant_resolver | `src/tenancy` |
| search_index | `src/search` |
| storage_driver | `src/storage/backends` |
| mcp-controller, mcp-server | `src/mcp` |
| admin_action / admin_resource | `src/admin/actions` / `src/admin/resources` |
| audited | `src/audit` |
| graphql / dataloader | `src/schema` / `src/schema/dataloaders` |
| vector_collection | `src/vector/collections` |
| (special) resource | `src` — writes `src/<app>/<name>_resource.py`, or into the module |
| migration / seeder | `migrations/versions` / `seeds` |
| test | `tests/unit` |

Two default dirs were renamed because they shadowed real modules on
`sys.path`: `src/graphql → src/schema` (shadowed `graphql`, used by
strawberry) and `src/collections → src/vector/collections` (shadowed the
stdlib `collections`). Because every component now lives under the app
package, importing `src/<app>/` can never shadow stdlib or site-packages —
the layout is import-safe by construction.

---

## 5. Composition root

```python
def create_app(config: LexigramConfig | None = None) -> Application:
    application = Application(name="my-platform", config=config)
    application.add_modules(
        [
            *infrastructure_modules(),   # db, cache, events, monitoring
            *MODULES,                    # the bounded contexts
            WebModule.configure(
                discover=[
                    "my_platform.controllers",
                    "my_platform.modules",
                ]
            ),
        ]
    )
    return application


app = create_app()
```

Controllers are **discovered**, never registered by hand — in both roots,
because an unscoped controller lives at the app root and a scoped one lives
inside its module. Listing them explicitly would let the composition root
wire a controller the module should own.

---

## 6. CLI surface

```bash
lexigram new project my-app --template web-api
lexigram new module auth                       # adds src/my_app/modules/auth/
lexigram gen controller users                  # src/my_app/controllers/…
lexigram gen controller users --module auth    # src/my_app/modules/auth/controllers/…
lexigram gen error not_found                   # src/my_app/shared/errors/… (module ignored)
```

`--module` is a per-invocation fact, never project state. Nothing has to be
migrated, converted or "switched": a project grows a bounded context by
adding one, and the components that move are exactly the ones scoped into it.

## 7. Alignment guarantees

1. **One canonical map.** `lexigram/cli/layout.py` holds a single
   `component → (directory, cross-cutting?)` table used by `lexigram gen`
   (path resolution), `lexigram new project` (scaffold dirs) and the
   alignment gate (`dev/checks/generator_output.py`).
2. **Same files everywhere.** `application.yaml`, `pyproject.toml`,
   `README.md`, `.env.example`, `tests/conftest.py` and `tests/test_app.py`
   come from the one `render_project()`.
3. **Runtime parity.** `[tool.lexigram] module` always names
   `<app>.app:app`, so `lexigram dev` / `lexigram run` boot the object the
   composition root exposes rather than a re-export of it.
4. **Import safety.** No generated package name may collide with stdlib or
   installed site-packages — enforced by the alignment gate.
