# 20 — Relations Inline Mutations & Follow-ups (R24 / B32–B34) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings

Deferred follow-ups from R21 (doc 17 §5), now confirmed and fixed:

| # | Severity | Bug |
|---|---|---|
| **B32** | silent data loss illusion | The relation routes' create/update/delete handlers are permission-checked **no-ops that fake success**: `_handle_create` ignores the submitted form and re-renders the panel (HTTP 200 — the user's input is silently discarded), `_handle_update` does the same, and `_handle_delete` returns an empty 200 without deleting anything. The default `inline_create/edit/delete = True` means every relation panel renders Add/Edit/Delete affordances that lie. |
| **B33** | N+1 queries | `BelongsToManyRelationManager.render()` calls `get_pivot_data(item_id)` per attached row; each call runs `_find_pivot_rows()`, which fetches **all** pivot rows for the parent — N attached rows → N+1 identical full fetches per render. |
| **B34** | ignored parameters | `AbstractRelationManager.get_items(page, per_page, **filters)` silently ignores `filters` — callers filtering get the unfiltered page. |

## 2. Fixes

| File | Change |
|---|---|
| `relations/manager_ext.py` | B32: new overridable persistence hooks — `create_record(data)`, `update_record(record_id, data)`, `delete_record(record_id)`. Defaults delegate to the attached `_data_source` (`create`/`update`/`delete`-or-`bulk_delete`) and raise `NotImplementedError` when no persistence is available. |
| `relations/routes.py` | B32: `_handle_create`/`_handle_update` now parse the submitted form (`admin_form_data` first, `csrf_token` stripped) and call the hooks; `_handle_delete` calls `delete_record`. Honest status codes replace fake success: disabled `inline_*` flag → 403, empty create/update form → 400, no persistence support → **501** with a clear message, real success → re-rendered panel / empty 200. Permission gates and parent-IDOR checks unchanged. |
| `relations/belongs_to_many.py` | B33: new `get_pivot_data_map(related_ids)` fetches pivot rows **once** and shapes them via the extracted `_shape_pivot_row` helper (shared with `get_pivot_data`); `render()` uses the map. Subclasses that override `get_pivot_data` keep their behavior — the map falls back to per-id calls when an override is detected. |
| `relations/manager.py` | B34: `get_items` applies equality filters via the dict/attribute-aware `_row_value` before paginating. |
| tests | New regression tests (fail pre-fix) + updates to `test_relation_routes_authz.py`, which had pinned the fake-success no-op contract. |

## 3. Verification

- New tests green; relations suites green; full admin unit + e2e green.

## 4. Implementation notes (post-verify)

- Hooks landed on `RelationManager` (`manager_ext.py`): `create_record` /
  `update_record` / `delete_record` delegate to the attached data source
  (`create` / `update` / `delete`-or-`bulk_delete`, `hasattr`-guarded) and
  raise `NotImplementedError` ("attach a data source or override …") when
  no persistence path exists — routes translate that to **501**.
- `_read_form_data` (routes.py) prefers `scope["admin_form_data"]`
  (avoids the known bare `request.form()` hang), tolerates minimal test
  stubs (returns `{}` → 400), and strips `csrf_token` so it can never be
  mass-assigned into a record.
- B33 `render()` now issues a constant 2 data-source fetches
  (`get_attached_ids` + `get_pivot_data_map`) instead of 1 + N; verified
  by a counting fake data source (pre-fix: 6 fetches for 5 attached rows).
- `test_relation_routes_authz.py` had pinned the fake-success contract;
  those pins were rewritten to the honest 400/403/501 codes with predicate
  ordering still asserted.
- Verified: 12 new regressions + 198 relation-scoped tests green; full
  admin unit suite **5441 passed / 8 skipped, 76.32% coverage**; ruff
  check + format clean.
