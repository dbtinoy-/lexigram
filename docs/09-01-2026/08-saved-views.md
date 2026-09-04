# Full Plan — Saved Views & Filter Presets (R13)

**Date:** 2026-09-02 (docs folder pinned to 09-01-2026 per convention)
**Status:** ✅ Done (implementation notes at the bottom)
**Depends on:** docs 01–07 (access-control base, settings service, list renderer facts)

---

## 1. Problem

Admins repeatedly rebuild the same list-view state by hand: a search term,
two or three filters, a sort column, per-page, density, hidden columns.
The DataTable already encodes *all* of that in the URL (`TableState`), and
HTMX keeps the browser URL canonical via `HX-Push-Url` — but nothing lets a
user **name** that state and come back to it with one click. Professional
admin tools (Django admin w/ plugins, Rails Administrate, Retool, Airtable)
all ship "saved views". This is the highest-leverage list-UX gap left after
Phase 2.

## 2. Goals / Non-goals

**Goals**

- Per-user, per-resource **named saved views**: persist the full list query
  string (search, filters, sort, per-page, view/layout/density, grouping,
  hidden columns, include-deleted) under a user-chosen name.
- One-click **apply** (a plain `<a href>` — zero JS required), **save
  current view** (small inline form) and **delete** from the list page.
- **No schema migration** — reuse `AdminSettingsService` (tenant_configs
  JSON storage) with namespaced keys.
- Server-side **sanitization**: only whitelisted query params are ever
  persisted or replayed; volatile params (`page`, `cursor`, flash params)
  are stripped; legacy aliases (`sort`/`order`/`dir`/`q`) are canonicalized.
- Hard limits: ≤ 20 views per user per resource, name ≤ 64 chars, query
  ≤ 2000 chars.

**Non-goals (deliberate, documented for later)**

- Shared/team views (would need an ownership + permission model; the storage
  shape below is forward-compatible — add a `shared` flag + a second key
  namespace later).
- Editing a view in place (delete + re-save is equivalent at this size).

## 3. Architecture facts this design is built on (verified in code)

- Real list pages render via `resources/list_renderer.py::ListRenderer.render()`
  → `TableState.from_request` → `_sanitize_table_state` → `DataTable` →
  `AdminRenderer.render_page(content, ...)`. `render_page` accepts
  `str | Markup | Any` and the `AdminShell` wraps content with
  `raw(render_to_string(...))`, so an HTML string can be prepended to the
  table (same technique the email/security pages use).
- Canonical query params produced by `TableState.to_query_params()`:
  `search, page, per_page, sort_by, sort_order, data_view, layout_type,
  density, cursor, col_order, hide_cols, group_by, collapsed_groups,
  include_deleted` + `filter_<field>` for filters. The renderer additionally
  accepts legacy aliases `sort`, `order`, `dir` (and search boxes may send
  `q`).
- The mounted admin sub-app cannot see the request-scoped container
  (doc 06); services must be resolved at mount time. The mount pipeline
  already exposes `super_admin_role`, `cluster_registry`, etc. on **both**
  outer and inner `app.state` (`di/mount/contributors.py`), and
  `di/mount/core.py` builds `ctx.settings_service`.
- `AdminSettingsService.get/set` JSON-round-trips arbitrary values through
  the `tenant_configs` table with an `admin.` key prefix — a list of dicts
  is stored/retrieved losslessly. Dashboard widget prefs already use this
  exact pattern (`admin_ui.widgets.default`).
- Controller conventions (docs 05/06/07): `_AccessControlController` base
  provides `_guard`, `_csrf_token`/`_csrf_ok`, `_form` (CSRF-middleware-safe
  form read), `_redirect(url, message, is_error)`; path params are forwarded
  by the route-collection wrapper (B11 fix).

## 4. Design

### 4.1 Storage — `SavedViewService` (`services/saved_views.py`)

Wraps `AdminSettingsService`; **no new tables**.

- Key: `saved_views.{user_id}.{resource}` (service adds the `admin.`
  prefix), tenant scope `"default"` — saved views are *user* preferences,
  not tenant data; a future multi-tenant split can move to
  `resolve_tenant_id` without changing the shape.
- Value: `[{"name": str, "query": str, "created_at": iso8601}, ...]`,
  kept sorted case-insensitively by name.
- API (all async, all defensive against a `None`/broken settings service):
  - `list_views(user_id, resource) -> list[dict]`
  - `save_view(user_id, resource, name, query) -> dict` — upsert by
    case-insensitive name; raises `SavedViewError` with a user-facing
    message on invalid name/resource, empty sanitized query, or view-count
    cap.
  - `delete_view(user_id, resource, name) -> bool`
  - `sanitize_query(query) -> str` (staticmethod, shared with the renderer)
- `sanitize_query` rules:
  - parse with `urllib.parse.parse_qsl`, re-encode with `urlencode`
    (normalizes encoding, drops fragments/junk);
  - keep only: `search, per_page, sort_by, sort_order, data_view,
    layout_type, density, group_by, hide_cols, col_order, collapsed_groups,
    include_deleted` and any `filter_*` key;
  - canonicalize legacy aliases: `q→search`, `sort→sort_by`,
    `order|dir→sort_order`;
  - drop `page`, `cursor`, `notice`, `error` and anything unknown;
  - cap result at 2000 chars (reject, don't truncate — truncation could
    silently change filter semantics).
- Name validation: 1–64 chars after strip, no control characters.
  Resource validation: `^[a-z0-9_-]{1,64}$`.
- Cap: 20 views per user per resource (upsert of an existing name is always
  allowed).

### 4.2 Wiring (mount time, doc-06 pattern)

- `di/mount/context.py`: add `saved_view_service: Any | None = None`.
- `di/mount/core.py`: right after `ctx.settings_service` is built,
  construct `ctx.saved_view_service = SavedViewService(admin_settings_service)`
  (best-effort try/except).
- `di/mount/contributors.py`: alongside `super_admin_role`, expose
  `ctx.saved_view_service` on **both** `app.state` and `admin_app.state`
  as `saved_view_service` — this is how `ListRenderer` (which has no DI
  access) reaches storage at render time.
- `di/mount/controllers.py`: resolve `SavedViewsController` best-effort,
  inject CSRF service + `ctx.saved_view_service` (same block style as the
  R11 email controller).

### 4.3 Controller — `SavedViewsController` (`controllers/saved_views.py`)

Prefix `/views`. **POST-only** (apply is a plain link; there is no GET page
— the UI lives inside the list page).

- `POST /admin/views/{resource_name}/save` — form: `csrf_token`, `name`,
  `query`. Sanitizes + saves, then 302 to
  `{admin}/{resource}?{sanitized_query}&notice=…` so the user lands *on*
  the view they just saved.
- `POST /admin/views/{resource_name}/delete` — form: `csrf_token`, `name`.
  302 back to the plain list with a notice.
- Guard: **any authenticated admin** (per-user data — no superadmin gate).
  Subclasses `_AccessControlController` but overrides `_guard` to only
  require a non-guest user. CSRF enforced on both routes. Guard errors
  redirect with `?error=…` per house style.
- Redirect URLs are built exclusively from `self._admin_path(request)`,
  the validated resource slug and the sanitized query — no user-controlled
  redirect targets.

### 4.4 UI — views bar in `ListRenderer`

New method `_render_saved_views_bar(request, state, resource_prefix,
admin_prefix) -> str`, called only in the **full-page** branch (the bar sits
outside the HTMX swap zones, so fragment responses don't need it):

- Resolves the service from `request.app.state.saved_view_service` and the
  user from `request.state.user`; returns `""` (no bar) if either is
  missing — rendering NEVER breaks the list page (whole bar builder is
  wrapped in try/except with a warning log).
- Renders, in one compact flex row: a bookmark icon + "Views" label; one
  pill per saved view — an `<a>` applying the view (href =
  `{resource_prefix}?{query}`) plus an inline delete form (×) with CSRF;
  the pill for the *active* view (sanitized current query == stored query)
  is highlighted; and a small "save current view" form (name input +
  hidden `query` + CSRF) posting to `/admin/views/{resource}/save`.
- The hidden `query` value is server-rendered from
  `state.to_query_params(exclude=["page", "cursor"])`. Because HTMX
  filtering updates the URL *without* re-rendering the bar, `admin.js`
  gains a delegated submit listener on `form[data-saved-view-save]` that
  copies `location.search` into the hidden input at submit time (no-JS
  fallback = the server-rendered value; the server re-sanitizes anyway).
- All names and queries are HTML-escaped; queries are re-encoded via
  `sanitize_query` before being emitted as hrefs.
- Full-page branch changes from `render_page(dt, …)` to
  `render_page(bar_html + render_to_string(dt), …)` when the bar is
  non-empty (unchanged otherwise).

### 4.5 Failure behaviour

- Settings provider down → `list_views` returns `[]`, bar shows only the
  save form; save/delete surface a friendly `?error=…`.
- Corrupt stored payload (not a list / bad items) → tolerated: non-dict
  items skipped, missing fields defaulted; next save rewrites clean data.
- Service absent from app state (e.g. minimal test app) → no bar, list
  page unaffected.

## 5. Test plan

- **Service unit tests** (`tests/unit/services/test_saved_views.py`):
  sanitize whitelist/aliases/drops/cap; name + resource validation; upsert
  by case-insensitive name; sort order; 20-view cap; delete found/missing;
  corrupt-payload tolerance; None settings service.
- **Controller tests** (`tests/unit/controllers/test_saved_views_controller.py`):
  guest → login redirect; authenticated non-superadmin allowed; CSRF
  missing/invalid → error redirect; save happy path (redirect lands on the
  view + notice); invalid name/query → error redirect; delete happy path +
  missing name.
- **Renderer tests** (`tests/unit/resources/test_list_renderer_saved_views.py`):
  bar absent without service/user; bar lists views with escaped names;
  active view highlighted; save form carries CSRF + sanitized current
  query; bar failure does not break `render()`.
- **Live verify** on the playground: save a filtered users view, re-apply
  it from a clean URL, delete it; confirm notices and audit log silence.

## 6. Rollout

No migration, no config flag needed: the feature is inert unless the mount
pipeline can build the service (which it always can when settings storage
exists — the same condition as the Settings page). Docs 02/04/README
updated after implementation; committed to PR #26.

---

## Implementation notes (2026-09-02, done)

- Shipped as designed: `services/saved_views.py`, `controllers/saved_views.py`,
  mount wiring (context/core/contributors/controllers),
  `ListRenderer._render_saved_views_bar` + full-page injection, `admin.js`
  submit-sync listener.
- Two deviations discovered by live verification, both fixed in-place:
  - **CSRF session-id chain**: list pages mint their token from
    `csrf_session_id` *or* `admin_user_id` (see `CsrfMiddleware` and
    `ListRenderer._ensure_csrf_token`), but the access-control base's
    `_csrf_ok` only accepts `csrf_session_id` — which regular list
    sessions don't have. `SavedViewsController._csrf_ok` overrides with
    the middleware's exact fallback chain.
  - **Default-aware active matching**: `to_query_params` drops
    resource-default values for clean URLs, so a saved query that spells a
    default out (e.g. `per_page=10` when the default is 10) never matched
    the current state. The bar now normalizes both sides against
    `TableState._defaults` before comparing.
- The `bg-primary/5` pill class required regenerating admin.css opacity
  utilities (`dev/generators/admin_opacity_utilities.py` — guarded by
  `test_design_tokens.py::test_generated_block_is_not_stale`).
- 65 new unit tests across the three planned test files; full admin suite
  **5274 passed / 8 skipped**, e2e 72 / 2. Verified live on the
  playground: save (volatile `page` stripped) → apply from a clean URL
  (active pill highlighted) → delete, with notices throughout; bad/missing
  CSRF rejected by the middleware (403 + audit `csrf_violation`).

## Follow-up implementation (R54, 2026-09-03)

The default-view follow-up is shipped in [52-default-saved-view.md](52-default-saved-view.md).
Saved-view entries now carry an optional boolean `default` marker, with
legacy records normalized safely. The views bar exposes accessible star/unstar
POST controls, and a clean full-page visit redirects once to the sanitized
default query. Explicit list state, HTMX fragments, and mutation notices are
never overridden. Shared/team views and in-place editing remain intentionally
separate future work.
