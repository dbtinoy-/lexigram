# Lexigram Project Structures — Proposed Plan

Goal: three first-class project structures, all built from the **same 48
`lexigram gen` generators** so scaffolding and code generation stay in
lockstep. One canonical generator→path map; each structure resolves it
differently.

Structures (matching `docs/getting-started/`):

| # | Name | Docs pattern | Layout |
|---|------|--------------|--------|
| 1 | `minimal` | first-app | single package `src/<app>/`, no generator dirs |
| 2 | `structured` | Pattern 2 (current generators) | `src/<app>/` + sibling component packages |
| 3 | `modular` | Pattern 3 | `src/<app>/modules/<feature>/` with `@module` boundaries |

`lexigram new project <name> --structure <1|2|3>` keeps the existing feature
profiles (`--template api|web-api|graphql|worker|full`) orthogonal: any
profile × any structure.

---

## 1. `minimal` — single-package starter

```
my-app/
├── application.yaml            # app_name, env, logging, ...
├── pyproject.toml              # [tool.lexigram] module = "my_app.app:app"
├── README.md
├── .env.example
└── src/
    └── my_app/
        ├── __init__.py
        ├── app.py              # create_app() — Application + modules
        └── py.typed
└── tests/
    ├── conftest.py             # boots create_app()
    └── test_app.py
```

- No components are pre-created; `lexigram gen` writes **inside the app
  package** (`src/my_app/<component>/…`) via a layout-aware resolver.
- Composition root stays framework-idiomatic:
  `Application(name=…) + WebModule.configure(discover=["my_app.controllers"])`.

---

## 2. `structured` — generator-native layout (Pattern 2)

This is what the generators already do; the scaffold simply pre-creates every
component package so `lexigram gen` drops files straight into a working tree
and `WebModule.configure(discover=["controllers"])` picks them up.

```
my-app/
├── application.yaml
├── pyproject.toml
├── README.md
├── .env.example
├── migrations/versions/
│   └── __init__.py             # lexigram gen migration
├── seeds/
│   └── __init__.py             # lexigram gen seeder
├── src/
│   ├── my_app/                 # composition root ONLY
│   │   ├── __init__.py
│   │   ├── app.py              # create_app()
│   │   └── py.typed
│   ├── admin/{actions,resources}/
│   ├── audit/
│   ├── clients/
│   ├── commands/
│   ├── consumers/
│   ├── controllers/            # lexigram gen controller (auto-discovered)
│   ├── errors/
│   ├── events/
│   ├── features/
│   ├── filters/
│   ├── guards/
│   ├── handlers/
│   ├── health/
│   ├── interceptors/
│   ├── mcp/
│   ├── metrics/
│   ├── middleware/
│   ├── models/
│   ├── notifications/
│   ├── pipelines/
│   ├── policies/
│   ├── projections/
│   ├── providers/
│   ├── queries/
│   ├── repositories/
│   ├── sagas/
│   ├── schema/
│   │   └── dataloaders/
│   ├── search/
│   ├── services/
│   ├── storage/backends/
│   ├── tasks/
│   ├── tenancy/
│   ├── vector/collections/
│   ├── webhooks/
│   ├── websocket/
│   └── workflows/
└── tests/
    ├── conftest.py
    ├── test_app.py
    └── unit/                   # lexigram gen test
```

### Required generator-dir cleanup (2 renames)

Two current default dirs shadow real Python modules on `sys.path` and must
move. This is a **SDK change** (contributor definition + generator default +
docs table + gate):

| Generator | Today (broken) | Proposed | Why |
|-----------|----------------|----------|-----|
| `graphql`, `dataloader` | `src/graphql`, `src/graphql/dataloaders` | `src/schema`, `src/schema/dataloaders` | `src/graphql` shadows `graphql` (graphql-core used by strawberry) |
| `vector_collection` | `src/collections` | `src/vector/collections` | `src/collections` shadows stdlib `collections` |

After the rename, the scaffold can pre-create **every** component package —
no shadow exclusions, no import-order surprises.

### Full generator map (48) → structured paths

| Generator(s) | Directory |
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
| graphql / dataloader | `src/schema` / `src/schema/dataloaders` *(renamed)* |
| vector_collection | `src/vector/collections` *(renamed)* |
| (special) resource | `src` — writes `src/<name>_resource.py` beside components |
| migration / seeder | `migrations/versions` / `seeds` |
| test | `tests/unit` |

- **Wheel packages**: every top-level `src/` dir (hatchling `packages=[…]`).
- **pyproject**: `[tool.lexigram] module = "<app>.app:app"`, pytest-asyncio,
  ruff, mypy config.
- **Composition root** (example `web-api`):
  ```python
  application.add_modules([
      DatabaseModule.configure(),                  # reads `sql:` section
      WebModule.configure(discover=["controllers"]),
  ])
  ```

---

## 3. `modular` — module-boundary layout (Pattern 3)

Component packages live **inside each feature module**; cross-cutting
packages live in one shared layer. Importing `src/<app>/` never shadows
stdlib/site-packages (no `src/collections`, no `src/graphql` at top level) —
the layout is import-safe by construction.

```
my-platform/
├── application.yaml
├── application.production.yaml        # optional profile overlays
├── pyproject.toml
├── README.md
├── .env.example
├── migrations/versions/               # shared infra migrations
├── seeds/                             # shared seeders
├── src/
│   └── my_platform/
│       ├── __init__.py
│       ├── app.py                     # create_app(profile=None)
│       ├── py.typed
│       ├── infrastructure/            # shared infra modules
│       │   ├── __init__.py            # @module InfraModule
│       │   ├── db.py                  # DatabaseModule.configure() wiring
│       │   ├── cache.py               # CacheModule.configure()
│       │   ├── events.py              # EventsModule wiring
│       │   └── monitoring.py          # MonitorModule wiring (shared)
│       ├── shared/                    # cross-cutting app packages
│       │   ├── __init__.py
│       │   ├── errors/                # lexigram gen error
│       │   ├── filters/               # exception_filter, filter
│       │   ├── middleware/            # middleware
│       │   ├── interceptors/          # interceptor
│       │   ├── metrics/               # metric
│       │   ├── health/                # health
│       │   ├── audit/                 # audited
│       │   ├── tenancy/               # tenant_resolver
│       │   ├── features/              # feature_flag
│       │   ├── search/                # search_index
│       │   ├── storage/backends/      # storage_driver
│       │   ├── providers/             # provider (app-level)
│       │   └── mcp/                   # mcp-controller, mcp-server
│       └── modules/
│           ├── auth/
│           │   ├── __init__.py        # @module AuthModule(controllers=[…], exports=[…])
│           │   ├── protocols.py       # the module contract
│           │   ├── provider.py        # AuthProvider (register/boot/shutdown)
│           │   ├── controllers/       # lexigram gen controller
│           │   ├── models/
│           │   ├── services/
│           │   ├── repositories/
│           │   ├── queries/           # read models
│           │   ├── events/ handlers/  # domain events
│           │   ├── sagas/ projections/ pipelines/ workflows/
│           │   ├── tasks/             # module-local scheduled jobs
│           │   ├── policies/ guards/  # module security
│           │   ├── schema/ dataloaders/   # module GraphQL surface
│           │   ├── commands/ consumers/
│           │   ├── webhooks/ websocket/
│           │   ├── clients/ notifications/
│           │   ├── admin/{actions,resources}/
│           │   ├── audit/ (optional module-local audit)
│           │   └── tests/             # lexigram gen test
│           ├── billing/
│           │   └── …same shape…
│           └── <feature>/
└── tests/
    ├── conftest.py                    # boots the whole app
    ├── unit/
    └── integration/
```

### Module boundary template (`lexigram new module <name>`)

```
modules/<name>/
├── __init__.py            # @module NameModule(imports=[…], controllers=[…], exports=[…])
├── protocols.py           # NameServiceProtocol etc. — what other modules may import
├── provider.py            # NameProvider — registers the module's services
├── services.py            # implementations (lazy imports inside register())
└── (empty component dirs created on first `lexigram gen … --module <name>`)
```

### Composition root (modular)

```python
def create_app(profile: str | None = None) -> Application:
    config = LexigramConfig.from_env_profile(profile) if profile else LexigramConfig.from_yaml()
    app = Application(name="my-platform", config=config)
    app.add_modules([
        InfrastructureModule,      # db, cache, events, monitoring
        AuthModule,                # module boundary: declares controllers=[…]
        BillingModule,
        WebModule.configure(discover=["my_platform.modules"]),
    ])
    return app
```

Each module's `@module(controllers=[…])` declares its own controllers; the
web module collects them (or `discover` scans the module packages).

### Generator resolution (modular)

`lexigram gen <gen> <name> --module auth` resolves:

- module-local components → `src/my_platform/modules/auth/<component>/…`
  (exact suffix from the canonical map, e.g. controller → `controllers/`)
- cross-cutting components → `src/my_platform/shared/<component>/…`
  when no `--module` is given
- infrastructural → `migrations/versions`, `seeds` stay at project root
- `test` → `src/my_platform/modules/<module>/tests/test_<name>.py`
  (module-local if `--module`, else `tests/unit`)

---

## Cross-structure alignment guarantees

1. **One canonical map.** `scaffold.py` keeps a single
   `generator → (structured, modular-suffix, shared?)` table used by:
   `lexigram gen` (path resolution), `lexigram new project` (scaffold dirs),
   and the alignment gate (`dev/checks/generator_output.py`).
2. **Same files everywhere.** `application.yaml`, `pyproject.toml`
   (`[tool.lexigram] structure`, `module`), `README.md`, `.env.example`,
   `tests/conftest.py`, `tests/test_app.py` are generated by the one
   `render_project()` — only the tree shape differs.
3. **CLI surface.**
   ```bash
   lexigram new project my-app --template web-api --structure structured
   lexigram new project my-app --template api     --structure minimal
   lexigram new project my-app --template full    --structure modular
   lexigram new module auth                       # inside a modular app
   lexigram gen controller users --module auth    # modular-aware
   ```
4. **Runtime parity.** Every structure produces a `create_app()` the CLI
   auto-detects (`[tool.lexigram] module` + `src/**/{main,app}.py`), boots
   with `lexigram dev` / `lexigram run`, and passes the same smoke tests
   (`/` + `/health/ready`).
5. **Import safety.** No generated package name may collide with stdlib or
   installed site-packages — enforced by the alignment gate and by the two
   generator renames above.

## Decision points for you

1. **Rename `src/graphql`→`src/schema` and `src/collections`→`src/vector/collections`**
   (SDK change, ~2 packages + docs) — or keep the old dirs and leave them
   un-pre-created (import-unsafe when generated).
2. **Minimal structure generator paths**: nest inside `src/<app>/`
   (recommended) vs. no generator support in `minimal`.
3. **Modular cross-cutting**: `src/<app>/shared/` (recommended) vs.
   `src/<app>/infrastructure/` — keep one shared layer, not two.
4. **`--structure` flag vs. separate template names.** Recommend adding the
   flag and keeping `--template` as the feature profile (4×3 matrix, no
   template-name explosion).
