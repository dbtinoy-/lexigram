# 21 — Filtered-dataset export (R25)

## 1. Problem

R22 (doc 18) made the toolbar export buttons produce a real CSV/JSON
download — but **only for checked rows on the current page**. The first
deferred follow-up in doc 18 §5 was:

> Export the *filtered* view (forward the list's current URL state), not
> just the checked rows.

Today, with nothing selected, both client helpers dead-end:

- `admin.js::LexigramDownloadBulk` → toast "Select at least one row to
  export." and gives up.
- DataTable inline script `LexigramDownloadBulk` → `alert('Select at
  least one record.')` and gives up.

So "export everything matching my current search/filter" — the single
most common export intent in an admin tool — is impossible from the UI.
Users can only export a hand-checked page worth of rows.

## 2. Design

**Contract (both stacks, same bulk POST route):** when the export action
is submitted with `scope=filtered` and **no** `ids`, the server exports
every record matching the forwarded list state instead of a selection.

- New form fields: `scope=filtered` + `list_query=<current list
  querystring>` (no leading `?`).
- The querystring is parsed by the *same* parser each stack's list page
  uses (`TableState.from_request` for the declarative stack,
  `URLState.from_request` for the controller stack) via a lightweight
  `query_params` stub — so search/filters/sort semantics can never drift
  from what the user is looking at.
- Sort fields are allowlisted against the resource's known fields (same
  posture as the list page) — an unknown `sort_by` is dropped, never
  forwarded to storage.
- Rows are fetched in pages of 1000 and hard-capped at
  `MAX_FILTERED_EXPORT_ROWS = 10_000`; `list_query` itself is capped at
  4096 chars. Permission gate stays `can_view` (read), unchanged.
- Selection export is untouched: `ids` present → existing behavior.
  Missing `ids` *without* `scope=filtered` (or for non-export actions)
  still 400s.

**Clients:** both `LexigramDownloadBulk` implementations now treat "no
rows checked" as "export the current filtered view": they append
`scope=filtered` and `list_query=location.search` instead of bailing.

## 3. Changes

| File | Change |
|---|---|
| `controllers/resource/bulk.py` | `bulk_action` accepts id-less filtered exports; new `bulk_export_filtered()` builds the list `QuerySpec` from the forwarded querystring via `URLState` + `_build_query`, pages through results (cap 10k), and reuses the shared attachment encoder extracted from `bulk_export` (`_export_attachment`). |
| `resources/handler.py` | Export branch accepts `scope=filtered`; `_fetch_filtered_export_records()` parses `list_query` with `TableState.from_request`, allowlists the sort field, and pages through `ListDataFetcher.fetch_data` (same integration path as the list page, cap 10k). Record shaping extracted to `_shape_export_record` and shared with the ids path. |
| `static/js/admin.js` | No selection → filtered export (`scope` + `list_query` from `location.search`), matching toast copy. |
| `lexigram-ui/.../data_table_client_logic.py` | Same for the native-form fallback; the alert dead-end is gone. |
| tests | New regressions for both stacks: filtered export honors search/filters, unknown sort dropped, cap enforced, id-less non-scoped POST still 400, disabled export still 403; client scripts carry the new fields. |

## 4. Implementation notes (post-verify)

- Controller stack: `bulk_export` was refactored to share
  `_export_attachment` with the new `bulk_export_filtered`; the filtered
  path parses `list_query` with `URLState.from_request` over a
  `QueryParams` stub, strips any cursor, and pages `find_many` in
  1000-row batches to the 10k cap. Ordering matches the list: the meta
  default sort applies when the querystring has none.
- Declarative stack: `_fetch_filtered_export_records` reuses
  `TableState.from_request` + `ListDataFetcher.fetch_data` (the exact
  list-page path, including cache/search/resilience integrations), drops
  sort fields not in the resource's column allowlist, and returns `None`
  on fetch failure so the endpoint answers 503 instead of shipping an
  empty file. Record shaping is shared with the ids path via
  `_shape_export_record`.
- Clients: both `LexigramDownloadBulk` implementations now send
  `scope=filtered` + `list_query=location.search` when nothing is
  checked; the "Select at least one…" dead-ends are gone.
- Verified: 20 new regressions green; full admin unit suite **5461
  passed / 8 skipped (76.46% coverage)**; lexigram-ui suite 1275 passed;
  ruff check + format clean.

