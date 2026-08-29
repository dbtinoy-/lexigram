# Survey notes: `lexigram-admin` + `lexigram-ui`

> Hand-written survey notes (not a generated audit report — the
> `docs/audit/` tree at the repo root is produced by `make audit-*`).
> Covers both `lexigram-admin` and `lexigram-ui`; filed under admin
> because that is the package the majority of the findings concern.

Verified by reading source and by booting a real panel — not from docs alone.
Everything below was executed against the checkout at `6f41b91`.

Scope: `experimental/apps/lexigram-admin` (1046 py / ~152k LOC) and
`experimental/apps/lexigram-ui` (243 py / ~32k LOC).

---

## 1. Shape of the two packages

| | lexigram-admin | lexigram-ui |
|---|---|---|
| Role | Admin panel *framework* (CRUD, RBAC, dashboards, HTMX) | Component library (htpy) |
| LOC | ~152,000 | ~32,000 |
| Deps on lexigram | contracts, core, **ui**, web | contracts, core |
| Entry points | `lexigram.providers`, `lexigram.modules`, `lexigram.web.contributors`, `lexigram.cli.contributors` | (component CLI `lexigram-ui add`) |

Dependency direction is strictly **admin → ui** (159 `lexigram.ui` imports inside
admin). The two `from lexigram.admin ...` strings inside ui's source are
**docstring doctest examples only**, not real imports — there is no cycle.

UI's declared `starlette>=1.0.0` is inconsistent with the rest of the workspace
(`starlette>=0.28.0` in admin). Starlette 1.x does not exist; harmless today but
a latent pin.

---

## 2. UI: the component model

Five layers, arrows = allowed import direction
(`layouts → organisms → molecules → atoms → core`). Nothing enforces it — the
ARCHITECTURE doc says "caught in code review".

`lexigram/ui/core/base.py`:

- `Component.__init__(*children, as_child=False, **props)` — children may also
  arrive via `children=[...]`.
- `render()` → `el(...)` / atom instance. Subclass hook.
- `__html__()` → the real entry point: runs `asChild` delegation, honours
  `debug_components`, then `render_to_string(result)`.
- `render_to_string(value)` — module-level helper.

### Verified: two render entry points disagree

```python
Button(as_child=True, children=[el("a", "Docs", href="/docs")])

str(btn)            -> <a href="/docs">Docs</a>            # asChild honoured
render_to_string(btn) -> <button class="inline-flex ...">  # asChild IGNORED
```

Cause, in `render_to_string` (`core/base.py:317`):

```python
if isinstance(value, Component):
    return render_to_string(value.render())   # bypasses __html__()
```

The bypass is deliberate (comment: avoid recursion, since `__html__` calls back
into `render_to_string`) but the side effect is that `asChild` — and the
`debug_components` marker — are silently dropped.

This matters because **the README and GUIDE both teach `render_to_string(...)` as
the primary render path**, so the documented usage path is the one that breaks
the documented feature. `str(comp)` / f-strings work correctly.

`asChild` itself is implemented fine and handles three child kinds:
`Slot` → render slot; `Component` → merge parent props into child; anything else
→ `str(child)` (note: raw htpy children get **no** prop merge).

---

## 3. Admin: architecture

Boot contract (README + verified):

```python
AdminModule.configure(config=AdminConfig(...), resources=[SomeResource])
```

- No global admin-site registry.
- Hard requirement: a registered `DatabaseProviderProtocol` (lexigram-sql) **and**
  `FlagManagerProtocol` (lexigram-features). Verified: omitting the DB module
  fails boot with `LEX_ERR_DI_008` listing ~10 admin store protocols.

### Resource system

`Resource` is the core abstraction: `fields`, `actions`, `pages`, `relations`,
`cluster`, `permissions`, lifecycle hooks. Built-in pages: List / Create /
Edit / View; route table `/{name}`, `/{name}/create`, `/{name}/{id}`,
`/{name}/{id}/edit`, `clone`, `delete`, `/{name}/bulk`.

Data sources flow in via `IDataSource` (`InMemoryDataSource`, SQL, API). Wiring
happens at mount time in `di/mount/contributors.py:117-158`, which calls
`resource.set_data_source(...)` — **not** by assigning `Resource._data_source`
yourself. (I did the latter; list pages worked, detail/edit rendered empty
chrome. That was my harness, not a framework defect.)

### Contributor system

`ContributorRegistry` (`contributors/registry.py`) — pure Registry pattern:
empty `__init__`, no built-ins, sorted by `priority`, `get_by_group()`.
Extension base class `BaseAdminContributor` lives in **lexigram-contracts**, so
satellite packages can contribute pages/routes/resources *without* depending on
lexigram-admin. That's the clean extension seam.

### Optional extensions degrade gracefully (verified)

`lexigram-auth` and `lexigram-cache` are **optional extras**, not base deps.
Boot logged warnings, not failures:

```
cache_contributor.cache_backend_unavailable  (CacheBackendProtocol not registered)
auth_contributor.handlers_unavailable        (ActiveSessionsWidgetHandler ...)
```

Mechanism: guarded imports. `admin/auth/adapter.py` wraps
`from lexigram.admin.auth.store import ...` in `try/except ImportError` and sets
the names to `None`. `cache/adapter.py` does the same for `lexigram.cache`. All
`lexigram.auth` imports in `di/sub_providers/auth_registrations.py` are
function-local, so they only fail if you actually call those paths.

One knock-on: `/health` returns **503** because the cache component reports
unhealthy — an optional dep drags the whole probe down.

---

## 4. Doc drift found (docs say X, source does Y)

These are the concrete cases; treat the docs as a sketch, not a spec.

1. **Field construction is wrong in every doc example.**
   `SchemaField` is `@dataclass(frozen=True, kw_only=True)`, and `required` is a
   bool *field*, not a builder method. Verified:

   | example | source | result |
   |---|---|---|
   | `TextField("name").required()` | ARCHITECTURE.md:141 | `TypeError` (positional) |
   | `TextField("name", required=True, sortable=True)` | GUIDE.md:48 | `TypeError` |
   | `TextField("name", required=True)` | HOWTOS.md:16 | `TypeError` |
   | `TextField(name="name", required=True)` | — | **works** |

2. **Setup-token error message names a wrong env var.** The runtime says
   `env LEX_ADMIN_AUTH__SECURITY__SETUP_TOKEN`, but `constants.py:23` defines
   `ENV_PREFIX = "LEX_ADMIN__"` (double underscore), so the working variable is
   `LEX_ADMIN__AUTH__SECURITY__SETUP_TOKEN`. (There is also a dedicated
   `ADMIN_SETUP_TOKEN`, which is what I used.)

3. **ARCHITECTURE.md overstates dependencies.** It claims auth/cache/features/
   resilience "are declared as explicit `pyproject.toml` dependencies". Auth and
   cache are **optional extras**; features and resilience aren't declared at all.

4. Doc-correct after all: `SchemaField.render_filter()` **does** exist
   (`schema/base.py:58`) — I nearly filed it as missing from a truncated read.

---

## 5. Live demo (reproducible)

Booted a real panel: `DatabaseModule` (sqlite) + `FeatureFlagsModule` +
`AdminModule` + `WebModule`, one in-memory `CustomerResource`.

- Requires `ADMIN_SETUP_TOKEN` (or explicit unsafe opt-out) or boot **refuses**.
- First-run `SetupMiddleware` serves `/admin/setup` (Create Administrator).
- With no mailer registered, email-verification *enforcement* blocks login; set
  `auth.email_verification.enforcement = False` (env `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__ENFORCEMENT`).
- After login: `/admin` → dashboard; `/admin/customers` → list rendering
  Ada/Alan/Grace from `InMemoryDataSource`.
- CSRF is on by default (I disabled it in the harness only).

Not yet exercised: actions, bulk actions, relation managers, export/import,
settings panels, contributor-contributed pages.

---

## 6. Test suite health (measured, not assumed)

Ran both suites in a venv with **all optional siblings installed**:

| package | result |
|---|---|
| lexigram-ui | **1259 passed, 78 skipped, 0 failed** (2.5s) |
| lexigram-admin | **4704 passed, 17 skipped, 0 failed** (28s) |

Admin needed `lexigram-tasks`, `-queue`, `-ai`, `-events`, `-tenancy`, `-search`,
`-storage`, `-http`, `-notification`, `-resilience`, `-audit` present. Without
them you get collection errors and 2 failures
(`test_queue_admin_contributor_importable`,
`test_ai_llm_admin_contributor_importable`) that are **environment gaps, not
defects** — admin's suite contains cross-package "is X's admin contributor
importable" tests that assume optional packages are installed.

Repo gates: `loc_limit` reports 5 files over 500 LOC repo-wide, **0 new** — and
`docs/loc_debt.md` confirms admin's own debt is retired (waves A–C, 2026-08-25).

---

## 7. Admin's resource generator has a narrow type map

`AdminResourceGenerator._field_declaration` (`cli/generators/admin_resource.py:231`)
has exactly two type branches:

```python
if field_type in ("bool", "boolean"):        -> BooleanField
if "date" in field_type or "time" in ...:    -> DateField
# everything else                            -> TextField   <-- fallthrough
```

Verified by generating a resource from
`title:str,published:bool,views:int,price:decimal,when:datetime`:

| declared | emitted field | emitted column |
|---|---|---|
| `title:str` | `TextField` | `TextColumn` |
| `published:bool` | `BooleanField` | `BooleanColumn` |
| `views:int` | **`TextField`** | **`TextColumn`** |
| `price:decimal` | **`TextField`** | **`TextColumn`** |
| `when:datetime` | `DateField` | `DateColumn` |

The generated file imports and instantiates fine — this is a **correctness
gap, not a crash**: numeric columns get text inputs with no numeric coercion,
and `decimal` never reaches `CurrencyField`.

What's available in `lexigram.admin.schema` but **never emitted**:
`IntegerField`, `FloatField`, `NumberField`, `CurrencyField`, `DateTimeField`,
`TimeField`, `EmailField`, `URLField`, `TextAreaField`.

Note the asymmetry: the same class already has a **complete** type map in
`_to_pydantic_type` (str/int/bigint/float/decimal/bool/date/datetime…). Only the
field-declaration path is narrow. This is the same *class* of gap as LEX-3
(extended type map) which was fixed for the **sql** generators — admin's
generator carries its own separate map and was not covered by that fix.

Also verified: admin's template emits **keyword** field args
(`TextField(name="title", label="Title", ...)`), so it does *not* share the
doc-drift bug from §4 — it's actually correct where the docs are wrong.

---

## 8. `lexigram-ui add` vendoring is not self-contained

`lexigram-ui add button -o out/` copies both the component **and** a dependency:

```
Created: out/lexigram/ui/atoms/button.py     (4.9 KB)
Created: out/lexigram/ui/core/base.py        (12.6 KB)
```

But the copied `button.py` still starts with:

```python
from lexigram.ui.core.base import Component, el
```

That's an **absolute** import into the installed `lexigram.ui` namespace, so the
vendored `core/base.py` beside it is never used — editing your vendored copy has
no effect. The shadcn-style "copy the component into your project so you own it"
promise doesn't hold unless your output dir shadows the installed package on
`sys.path`. Either the copy should rewrite to relative imports, or
`core/base.py` shouldn't be copied at all.
