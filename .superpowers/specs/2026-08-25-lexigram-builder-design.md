# Spec — Lexigram Builder v1 (visual node canvas → CRUD Lexigram apps)

**Date:** 2026-08-25
**Status:** Draft for review (recon-aligned rev 2)
**Location:** **STANDALONE** `/home/admin/Documents/AI/applications/lexigram-dev/lexigram-builder/` — moved out of the framework 2026-08-26; consumes framework packages via editable-path deps (shorts-creator/nms pattern). The framework has zero knowledge of it.
**Packages consumed:** `lexigram`, `lexigram-contracts`, `lexigram-web`, `lexigram-sql`, `lexigram-ui` — declared as bare names with `>=` floors (house style); resolved by root `[tool.uv.sources] { workspace = true }` (one line to add)
**Kind:** New developer-tool application built ON the framework — the builder server is itself a Lexigram app (dogfood).

---

## 1. Purpose & success criteria

A visual node-canvas application builder: users drag framework-shaped nodes
onto a canvas, wire typed edges, and generate a **real standalone Lexigram
project** (one-way codegen; the canvas graph is the source of truth).

**Vertical (v1):** CRUD API apps only. Custom-code nodes, AI-palette nodes,
and round-trip code→graph parsing are explicitly out of scope.

**Done means:** draw an `Entity` node (`User: name, email`) plus `Route`
nodes onto the canvas → press Generate → a runnable Lexigram project appears
under the projects dir, its own pytest suite passes, a preview server boots,
and `POST /users` returns 201 through the UI's request runner.

## 2. Decisions locked during brainstorming

| Decision | Choice |
|---|---|
| Interaction model | Visual node canvas (n8n-style), not Node.js tooling |
| Scope strategy | Narrow first (CRUD vertical), grow palette later |
| Execution model | **A: one-way codegen** — graph JSON ⇒ generated project ⇒ subprocess pytest + uvicorn. No runtime interpreter, no hybrid |
| Source of truth | Canvas graph document; regeneration overwrites generated code (destructive, documented) |
| Canvas tech | **REVISED 2026-08-26** — admin-style SSR: `lexigram-ui` components (el/render_to_string, organisms, htmx, realtime SSE) for every page/panel + ONE zero-dependency vanilla JS canvas island (static file, no build step). Original "Vite SPA" decision replaced after examining `lexigram-ui`/`lexigram-admin`; nms-fe-freezone still not adapted |

## 3. Layout

```
experimental/apps/lexigram-builder/
├── pyproject.toml        # hatchling; v0.1.7001; deps bare-name floors;
│                         # [project.entry-points."lexigram.modules"] builder = …BuilderModule;
│                         # ruff extend="../../../pyproject.toml"; mypy strict-ish; pytest ini
│                         # (asyncio_mode="auto", markers incl. integration, --cov=lexigram.builder)
├── README.md
├── .gitignore            # projects/, .ruff_cache
├── static/canvas.js      # vanilla canvas island (no build): drag 3 node kinds,
│                         # wire typed edges, pan; syncs JSON via fetch to the
│                         # existing /builder/projects/{name}/graph API
└── src/lexigram/
    ├── __init__.py                    # namespace shim (pkgutil extend_path) + py.typed
    ├── py.typed
    └── builder/
        ├── __init__.py  py.typed      # exports-only; __version__ via importlib.metadata
        ├── module.py                  # @module() BuilderModule.configure(...)
        ├── constants.py               # defaults (port 7200, dirs, limits) + __version__
        ├── exceptions.py              # BuilderError(DomainError) base + leaf errors
        ├── types.py                   # diagnostics dataclasses, shared value types
        ├── graph/
        │   ├── models.py              # frozen dataclasses: GraphDocument, Node, Edge, configs
        │   ├── palette.py             # node-kind registry: kind → config schema + ports
        │   └── validation.py          # Result[ValidatedGraph, BuilderValidationError]
        ├── gen/
        │   ├── emitters/              # per-node-kind emitter modules (pure functions)
        │   ├── templates/             # python modules holding file-body string templates
        │   └── writer.py              # thin orchestrator over core codegen
        │                               # StagedGeneration (sorted, atomic commits)
        ├── services/
        │   ├── projects.py            # ProjectService — fs-backed CRUD over projects dir
        │   ├── generation.py          # GenerationService — validate→write→sync→test→boot
        │   └── preview.py             # PreviewService — process mgmt + SSE broadcast
        ├── controllers/
        │   ├── builder_controller.py  # REST + SSE routes (see §7)
        │   └── pages_controller.py    # SSR page routes (see §7b) rendering
        │                              # lexigram-ui components
        ├── ui/
        │   ├── __init__.py            # el/render_to_string re-exports (ui pkg)
        │   ├── pages.py               # projects index + canvas page builders
        │   ├── panels.py              # inspector forms, diagnostics badges,
        │   │                          # log console (ui.realtime SSE), request
        │   │                          # runner modal — all lexigram-ui organisms
        │   └── canvas_bridge.py       # graph JSON <-> island payload helpers
        └── di/provider.py             # BuilderProvider(config_key="builder")
```

The UI is **server-rendered via `lexigram-ui`** (same stack as
`lexigram-admin`): `el()` component trees, htmx for mutations
(mutate-and-refresh), `ui.realtime`/SSE for the live console. The only
JavaScript is `static/canvas.js` — a dependency-free island handling
drag/wire/pan for the three node kinds and syncing the graph JSON to the
existing REST endpoints. No Node/npm/build step exists anywhere in v1.

Root-file policy per AGENTS.md §8 (`module.py`, `exceptions.py`,
`constants.py`, `types.py` enriched at package root). Every file < 500 LOC
(`make lint-loc` scans the whole tree; baseline ratchet applies).

## 4. Graph document (source of truth)

Stored at `<projects_dir>/<project>/graph.json`. Schema v1:

```json
{
  "version": 1,
  "nodes": [
    {"id": "app_1", "kind": "app_settings",
     "position": {"x": 40, "y": 40},
     "config": {"app_name": "notes_api", "port": 8000, "db": "sqlite"}},
    {"id": "ent_user", "kind": "entity",
     "position": {"x": 320, "y": 200},
     "config": {"name": "user", "fields": [
        {"name": "email", "type": "str", "nullable": false},
        {"name": "age", "type": "int", "nullable": true}]}},
    {"id": "rt_create", "kind": "route",
     "position": {"x": 600, "y": 120},
     "config": {"ops": ["create", "list"], "path_prefix": null}}
  ],
  "edges": [
    {"id": "e1", "src": "rt_create", "dst": "ent_user"}
  ]
}
```

### Node kinds (palette v1 — exactly three)

| Kind | Config | Constraints | Emits |
|---|---|---|---|
| `app_settings` | `app_name` (py-identifier, unique), `port` (1024–65535), `db` (`sqlite`\|`postgres`) | exactly one per graph | `main.py`, module wiring, `pyproject.toml`, config/env |
| `entity` | `name` (snake_case identifier, unique per graph), `fields[]` (`name`: identifier, unique per entity; `type`: `str`\|`int`\|`float`\|`bool`\|`datetime`\|`uuid`; `nullable`) | ≥1 field | Pydantic entity model, repository, migration, smoke-test cases |
| `route` | `ops[]` ⊆ {create, get, list, update, delete}, `path_prefix` (optional str) | ≥1 op | controller entries wired into `WebModule.configure(controllers=[…])` |

### Edges

Only `route → entity`. Verbs derive from ops (create→POST, get→GET,
list→GET, update→PUT/PATCH, delete→DELETE). Default paths:
`{prefix}/<plural(entity)>` and `{prefix}/<plural>/{id}` where plural =
`name + "s"` (naive pluralization documented; no inflect dep in v1).

### Diagnostics

Validation returns node-scoped diagnostics:
`{"node_id": str | None, "severity": "error"|"warning", "code": str, "message": str}`
rendered as red badges on canvas nodes. Examples: duplicate entity name,
unknown field type, route without edge, graph without app_settings, cycle
(impossible with route→entity but validated anyway for future kinds).

## 5. Codegen engine

Pure, deterministic (same graph ⇒ byte-identical output; sorted iteration,
stable header comment `# generated by lexigram-builder — do not edit`).
Per-node emission so failures attribute to `node_id`.

**Builds on the solid parts of `lexigram.codegen`** (identified 2026-08-25;
uplifted 2026-08-26 — see `specs/2026-08-26-codegen-uplift-design.md`):

- Name normalization and validation come from contracts' pure helpers
  (`snake_case`, `pascal_case`, `validate_component_name`) — the same
  functions every framework generator uses; no private-API coupling.
- Project writing delegates to **`StagedGeneration`**: stage all rendered
  files per node (traversal-guarded, duplicate-stage raises), then
  `commit(GenerationOptions(policy=CollisionPolicy.OVERWRITE))` writes
  the sorted tree atomically — regeneration-overwrites-graph-wins is
  just the OVERWRITE policy, not custom writer logic.
- Every write reports through contracts'
  `GenerationResult(files_created/skipped/overwritten)`; the writer folds
  per-node results into node-scoped diagnostics and SSE events.
- The generated project lands formatted: builder wraps ruff-format of
  written files as the `finalize()` step (post_write seam).
- The entity-field palette stays **`FieldSpec`-compatible**
  (`name:type[?][!unique][!fk=Model][=default]` semantics from
  `contracts/cli/parsers.py`) so graph configs can round-trip into CLI
  field strings later — but the builder stores structured fields in the
  graph document; `parse_fields` itself is only exercised in tests.
- Note: builder templates are plain Python emitter modules, NOT `.jinja2`
  stubs, so the user-facing stub-override layer does not apply to
  generated-app customization in v1 (deferred).

### Generated project shape (proven consumer pattern, shorts-creator-aligned)

Entities are **Pydantic models** (framework consumers do NOT use SQLAlchemy
declarative classes; persistence identity is
`(table_name, entity_class, key_field)` on a `GenericRepository` subclass):

> **Why not the old `lexigram.codegen.ModelGenerator` shape:** identified
> 2026-08-25 — its template emitted `from lexigram.sql.base import Base`,
> a module that never existed in `lexigram-sql`, and `ServiceGenerator`
> emitted placeholder bodies. **Resolved 2026-08-26 by retirement**
> (commit `8c08a56`): both generators, their templates, and the sql CLI
> verbs were deleted rather than fixed. The shorts-creator trio remains
> the only consumer pattern proven end-to-end with passing tests — the
> builder generates THAT.

```
<projects_dir>/<app_name>/
├── pyproject.toml          # deps: lexigram/lexigram-web/lexigram-sql (+floors);
│                           # [tool.uv.sources] RELATIVE editable paths into this
│                           # checkout (out-of-tree-app pattern; required or else
│                           # uv resolves lexigram from PyPI)
├── README.md               # run instructions
├── .gitignore  .env.example
├── migrations/             # consumer-owned alembic dir (own async env.py reading
│                           # <APP>_DATABASE_URL; one revision per entity)
├── src/<app_name>/
│   ├── __init__.py  main.py  module.py
│   ├── models/<entity>.py          # Pydantic BaseModel (ConfigDict(from_attributes))
│   ├── repositories/<entity>_repository.py
│   │                               # inner GenericRepository[Entity, str] subclass
│   │                               # (_entity_to_dict/_row_to_entity) + wrapper with
│   │                               # typed finders (get/list/create/update/delete)
│   ├── controllers/<entity>_controller.py
│   │                               # Controller subclass; @error_status(...) decorated;
│   │                               # returns Result[T, DomainError]; path params by
│   │                               # name+annotation; bodies read via Request or DTOs
│   └── di/provider.py              # PersistenceProvider: register() binds singletons,
│                                   # boot() resolves DatabaseProviderProtocol, wires
│                                   # repos, publishes via container.bind()
└── tests/
    ├── conftest.py                 # tmp-sqlite fixture: runtime url sqlite:///{path},
    │                               # migration url sqlite+aiosqlite:///{path}; alembic
    │                               # upgrade head via subprocess; DatabaseService direct
    └── test_crud_<entity>.py       # boot + health + op roundtrips for enabled ops
```

Module wiring in generated `module.py`: `DatabaseModule.configure(config=<url>)`
(positional-or-keyword `config` — URL string or `DatabaseConfig`; there are
NO `url=`/`dialect=` kwargs) + `WebModule.configure(controllers=[…],
host=…, port=…)`. Entry point `main.py` uses `run_server` from
`lexigram.web.server` (only `run_server` is exported there; async variant
lives at `lexigram.web.server.runner.run_server_async`).

Pipeline (`GenerationService.generate(project)`), each step a subprocess
with timeout, emitting phase events:

1. `writing` — validate graph; stop-on-first-error with diagnostics
2. `syncing` — `uv sync` in project dir
3. `testing` — `uv run pytest -q` (generated smoke suite)
4. `booting` — spawn `uv run uvicorn <app>.main:app --port <port>`; poll
   `/health` up to 15 s
5. `live` — record pid/port; any failure ⇒ kill process group, phase
   `failed` + captured tail of stderr

Regeneration stops any running preview first. One preview server per
project; port allocation: requested `settings.port`, else first free from
`constants.PREVIEW_PORT_RANGE` (8100–8199).

## 6. Services

| Service | Contract seam | Notes |
|---|---|---|
| `ProjectService` | constructor-injected `projects_dir: Path` | create/list/get/save-graph/delete; atomic writes (tmp + rename) |
| `GenerationService` | injects `ProjectService`, `PreviewService`, `SubprocessRunner` protocol | `SubprocessRunner` is a small protocol (package-local `protocols.py`) so unit tests fake execution; real impl shells out with timeouts |
| `PreviewService` | owns running processes + asyncio broadcast queues | feeds framework-native SSE — `lexigram.web.sse.EventSourceResponse` + `SSEHeartbeatScheduler`/`sse_response`, not hand-rolled streams |

Config via provider `config_key="builder"` (`LexigramConfig.get_section`),
env overrides `LEX_BUILDER_PORT`, `LEX_BUILDER_PROJECTS_DIR`
(default `experimental/apps/lexigram-builder/projects/`, gitignored —
note: the `projects/` subdir is deeper than the `experimental/*/*`
members glob, so generated projects never join the uv workspace).

Logging: `from lexigram.logging import get_logger` (structured key-values,
no f-strings, no print). Ambient capabilities available if needed:
`lexigram.primitives.clock`, `lexigram.identity.ambient`.

## 7. HTTP surface (prefix `/builder`)

| Method/Path | Purpose |
|---|---|
| `GET /builder/health` | liveness (also proves the builder boots as a Lexigram app) |
| `GET /builder/palette` | node kinds + config schemas (drives web forms generically later) |
| `POST /builder/projects` | create project (name validated) |
| `GET /builder/projects` | list with preview status |
| `GET/PUT /builder/projects/{name}/graph` | read / save+validate (returns diagnostics) |
| `DELETE /builder/projects/{name}` | remove project dir (stopped preview required) |
| `POST /builder/projects/{name}/generate` | run pipeline (async task, returns immediately) |
| `GET /builder/projects/{name}/preview/stream` | SSE via `EventSourceResponse`: `phase` / `log` / `diagnostic` events + heartbeat |
| `POST /builder/projects/{name}/preview/request` | request-runner proxy → live preview (avoids CORS) |
| `POST /builder/projects/{name}/preview/stop` | stop preview server |

Auth: none in v1 (localhost developer tool). Documented limitation.

## 7b. UI pages (SSR via lexigram-ui)

| Route | Page |
|---|---|
| `GET /builder` | Projects index: list + create form (htmx POST) |
| `GET /builder/projects/{name}/app` | Canvas page: island host, palette sidebar, inspector panel, diagnostics badges, SSE log console (`ui.realtime`), request-runner modal |

Panels map to existing organisms (modal, form_field, alert/badge,
realtime console); no new JS beyond the island. Island ↔ server contract
= the §4 graph document JSON over the §7 REST endpoints.

## 8. Error handling

Framework-native mapping — no bespoke error layer:

- Controllers **return** `Ok(...)` / `Err(domain_error)`; the web
  serialization pipeline unwraps Results and maps `Err` to RFC 7807
  `ProblemDetail` (`application/problem+json`) automatically via the
  result bridge. Status resolution: `error.status_code` attr → built-in
  registry (`NotFoundError→404`, `ValidationError→422`,
  `PermissionDeniedError→403`, `ConflictError→409`, `DomainError→400`)
  → non-domain ⇒ 500.
- Per-error overrides use the `@error_status(ErrorType, status_code)`
  class decorator from `lexigram.web.routing.result_bridge` (e.g. map
  `ProjectNotFoundError → 404` explicitly even though it derives from a
  base already registered).
- Expected domain failures (bad graph, unknown project, invalid name) →
  `Result[T, BuilderError-subclass]`; infrastructure failures (process
  spawn, fs) → raised exceptions; never swallowed.
- Preview lifecycle guarantees: failed boot or failed health check always
  kills the spawned process tree; SSE emits terminal `phase: stopped|failed`
  so the UI can never hang on a dead stream (heartbeat every 15 s).

## 9. Tests

House patterns (verified against lexigram-web / shorts-creator):

| Layer | Approach |
|---|---|
| graph/validation | unit: happy path + each constraint violation asserts diagnostic node_id/code |
| gen/emitters + writer | **golden-file snapshots**: minimal graph (User + 2 routes) → assert exact tree; per-node-kind units |
| services | fake `SubprocessRunner` (scripted outcomes): pipeline ordering, failure kills preview, diagnostics propagation |
| controllers | `starlette.testclient.TestClient(web_provider.starlette)` (sync) or `httpx.AsyncClient(transport=ASGITransport(app=…))` (async, `pytest.ini_options asyncio_mode="auto"`) — canonical shapes from `packages/lexigram-web/tests/unit/di/test_di_injection.py` and `tests/unit/docs/test_openapi_generation.py` |
| end-to-end (marker `integration`) | real subprocesses in tmp projects dir: generate sample User project → `uv run pytest -q` inside it passes → boot preview → `/health` OK → proxy `POST /users` → 201 → stop |
| ui pages | TestClient GET `/builder` and canvas page: 200 + lexigram-ui markers (layout shell, island script tag, palette entries); htmx create-form flow |

Package `pyproject.toml` declares its own `markers` (incl. `integration`)
because root runs use `--strict-markers`; `asyncio_mode = "auto"`; scoped
`addopts = ["--cov=lexigram.builder", "--cov-report=term",
"--cov-fail-under=40"]` (cli-style floor; root aggregate gate stays 80%).

Aggregate CI safety: everything except the e2e is fully offline (fakes,
tmp dirs) and runs under the default `-m "not integration"` gate. The e2e
carries `integration` so it is excluded there by construction, yet needs
no external services — run it locally with
`uv run pytest experimental/apps/lexigram-builder/tests -m integration`.

## 10. Integration

None in the framework — by design (detached 2026-08-26):
- own git-tracked project at workspace root, own venv (`uv sync` local)
- framework packages consumed as RELATIVE editable `[tool.uv.sources]`
  into `../lexigram/{core,packages,experimental}` (5 packages incl.
  lexigram-ui)
- no root pyproject/testpaths/pythonpath/mypy/importlinter registration
  (all removed); no `lexigram.modules` entry point (framework discovery
  irrelevant); console script `lexigram-builder` serves on :7200
- generated projects keep relative editable sources pointing INTO
  `../lexigram/...` (depth now one level shallower than the old
  experimental nesting)

## 11. Acceptance criteria

- [ ] `uv run pytest tests -m "not integration"` green offline inside lexigram-builder/
- [ ] Integration-marked e2e passes locally: generate → test → boot → proxied 201 → stop
- [ ] Golden snapshots byte-stable across two consecutive generations
- [ ] `ruff format --check .` + `ruff check .` + `mypy` clean on new src; `make lint-loc` green (all files < 500 LOC)
- [ ] Import-linter contracts pass with `lexigram.builder` enumerated
- [ ] SSR pages render: `/builder` index + canvas page contain layout shell, island script tag, palette entries (TestClient)
- [ ] Canvas loop works manually: drag nodes → save → badges on invalid graph → generate → SSE console → request runner 201
- [ ] Feature commits carry their tests (history discipline); version bumpable via `make version-bump PKG=lexigram-builder`

## 12. Gotchas / deferred

- **Upstream defects found while identifying `lexigram.codegen`**
  — **RESOLVED 2026-08-26 by retirement** (commit series with jinja2
  de-coupling): `ModelGenerator`/`ServiceGenerator` and their templates,
  sql re-export shims, and the `lexigram gen model|service` contributor
  entries were deleted rather than fixed; web's `resource` verb now
  generates the controller slice only. The `strict=True` xfail ratchet
  was removed together with its subject.
- **SQLite dual-URL rule (hazard):** runtime URL must be `sqlite:///path`;
  migration/test URLs `sqlite+aiosqlite:///path`. Feeding the async scheme
  into the runtime stack silently creates junk directories instead of
  failing (observed stray `sqlite+aiosqlite:/` dirs in repo roots).
- **Generated smoke tests always run on sqlite** (tmp path) even when
  `db: postgres` — keeps the offline gate honest; postgres preset only
  affects generated runtime config.
- Naive pluralization (`user→users`) may produce odd paths (`box→boxs`) —
  accepted for v1, documented in generated README.
- Editable-path `[tool.uv.sources]` inside generated projects means they
  run only from inside this checkout (same tradeoff as shorts-creator/nms).
- `enable_query_logging` kwarg is silently dropped by DatabaseModule —
  don't emit it.
- Deferred: custom-code nodes, auth, multi-user, round-trip parse, palette
  beyond CRUD. Canvas island may graduate to a built frontend (React Flow)
  behind the same graph API if UX demands it — v1 deliberately ships zero
  Node toolchain. Static island served by a package static route in v1;
  CDN/white-label serving deferred.
