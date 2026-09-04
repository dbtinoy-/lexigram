# 17 — Relations Layer Correctness (R21 / B24–B27) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings

| # | Severity | Bug |
|---|---|---|
| **B24** | dead feature + mass-assignment | Inline pivot editing is broken end-to-end: rendered inputs are named `pivot_{col}_{related_id}`, but `_handle_pivot_update` passes the raw form dict to `update_pivot`, which filters against plain column names — **every pivot edit silently no-ops**. Worse, when `pivot_columns` is empty, `update_pivot` writes the whole form (including `csrf_token`) into the pivot row — mass-assignment. |
| **B25** | routing collision | `register_relation_routes` mounts every relation manager at the same wildcard path (`…/relations/{rel_name}`) with the manager bound by closure. With two+ relation managers on one resource, **the first mounted manager serves requests for every `rel_name`** — the second manager is unreachable and requests for relation B silently render relation A. |
| **B26** | dict rows broken | `render()` / `_render_single_row()` / `routes._get_record()` / `manager_ext.render()` read `getattr(item, "id"/…)` — SQL data sources return **dict rows**, for which `getattr` yields the default: empty IDs, blank labels, unfindable records. The dict-aware `_row_id`/`_row_value` helpers exist but are only used for pivot rows. |
| **B27** | dead endpoints | The attach/detach (`…/toggle`), `…/sync`, and `…/pivot/{id}` POST handlers exist only inside `get_pivot_routes()`, which is **never mounted anywhere** — the rendered checkboxes, Save button, and pivot inputs all post into 404s. `get_pivot_routes` also builds absolute `/admin/…` paths (double-prefix if mounted under the admin sub-app) and bakes `self.parent_id` into the path — unmountable as designed. |

Also: exact-match `content-type == "application/json"` misses
`application/json; charset=…` (fixed with `startswith`).

Non-issue verified: CSRF **is** covered — the R12 `AdminCsrfMiddleware`
validates all unsafe methods globally and the layout injects
`X-CSRF-Token` into every htmx request.

## 2. Fixes

| File | Change |
|---|---|
| `relations/manager.py` | `_row_id` / `_row_value` move up to `AbstractRelationManager` (dict + attribute aware; `id` falls back to `pk`). |
| `relations/belongs_to_many.py` | B24: `_extract_pivot_form_data(form, related_id)` maps `pivot_{col}_{related_id}` → `{col: value}` (plain col names also accepted); with no configured `pivot_columns`, only `pivot_`-prefixed keys are accepted — the raw form is never written. B26: `render()`/`_render_single_row()` use `_row_id`/`_row_value`. B27: toggle/sync/pivot handlers become reusable public methods (`handle_toggle`, `handle_sync`, `handle_pivot_update`); `get_pivot_routes` (kept for back-compat) delegates to them and now emits **relative** `/{resource}/…` paths; content-type check uses `startswith`. |
| `relations/routes.py` | B25: routes embed the manager's concrete relationship name (no wildcard collision); each manager gets distinct paths. B27: for managers exposing the pivot surface, `register_relation_routes` now also mounts the three POST routes — auth-gated (`_require_user`) + parent-gated like the other handlers, with `RelationPersistenceError` mapped to a clear 400 instead of a dead 404. |
| `relations/manager_ext.py` | B26: `render()` uses dict-aware row access for id/label/cells. |
| `tests/unit/resources/relations/test_relations_correctness.py` | New regression tests for B24/B25/B26/B27 (each fails on the old code). |

## 3. Verification

- New regression tests green; existing relations tests green; full admin
  unit + e2e suites green.

## 4. Implementation notes (post-verify)

- **Status:** ✅ Complete.
- `_row_id` now uses `is not None` chaining (an `id` of `0` no longer
  falls through to `pk`), and lives on `AbstractRelationManager` so every
  manager and the route helpers share one dict-aware implementation.
- The B27 POST routes are mounted conditionally (`hasattr` check for
  `handle_toggle`/`handle_sync`/`handle_pivot_update`), so plain
  `RelationManager` subclasses without a pivot surface get exactly the
  same 6 routes as before — `test_get_pivot_routes`'s `len == 3`
  contract and the route-count expectations of existing callers hold.
- Pivot POST handlers reuse the module's fail-closed gates: `_require_user`
  (403 + audit), `_require_parent` (parent-IDOR), `can_view_parent`;
  `RelationPersistenceError` maps to `400` with the error message. CSRF
  is enforced globally by `AdminCsrfMiddleware` — no per-handler checks.
- `handle_*` read `request.scope["admin_form_data"]` before falling back
  to `await request.form()` (required under the admin middleware chain).
- `tests/unit/test_relation_routes_mount.py` updated: it asserted the
  buggy `{rel_name}` wildcard paths; it now asserts the concrete
  `/relations/pets` paths.
- **Pre-fix proof:** all 11 new regression tests fail on the stashed
  pre-R21 code and pass post-fix.
- **Verification:** relations suite 54/54; admin unit **5405 passed /
  8 skipped / 76.22 % cov**; admin e2e **72 passed / 2 skipped**.

## 5. Deferred follow-ups

- `render()` N+1: `get_pivot_data` re-fetches all pivot rows per
  attached row — batch once per render.
- `routes._handle_create` / `_handle_delete` are permission-checked
  no-op stubs (no persistence).
- `AbstractRelationManager.get_items(**filters)` ignores its filters.
