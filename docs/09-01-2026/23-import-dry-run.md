# 23 — Import dry-run: validate before commit (R27)

## 1. Problem

Deferred from doc 19 (R23). The import pipeline validates rows
non-destructively at parse time — but no caller can reach that step by
itself. Picking a file in the UI **immediately commits** whatever parses:
there is no way to answer "what would this file do?" before rows start
landing in the data source. Failed rows are only discoverable *after*
half the file has already been imported. Professional admin tools
(Django import-export, Filament) treat validate-then-confirm as the
default import flow.

## 2. Design

**Service/action layer**

- `_run_import(service, content, filename, dry_run=False)`: when
  `dry_run`, stop after `parse()` and return a summary payload —
  `Validated N row(s): V ready to import, F with error(s). Nothing was
  imported.` plus `dry_run: True`, `created: 0`, `failed`, `total`.
- When a dry run finds errors, the new
  `AdminImportService.store_validation_report(job)` persists the row
  errors as a normal `ImportReport`, so the existing
  `import-report` download route serves dry-run reports too.
- `ImportAction` / `ImportBulkAction` read `ctx.metadata["dry_run"]`.

**Routes (both stacks)**

- The upload handlers read a truthy `dry_run` form field (`1/true/on/
  yes`) alongside `file` and pass it through. Permission gate stays
  `can_create` — a dry run reveals nothing an importer couldn't learn
  by importing.
- The HTMX response omits the `refresh-list` trigger on dry runs
  (nothing changed), keeping the toast + failed-report link.

**Client (`LexigramImportUpload`)**

- New default flow: pick file → POST with `dry_run=1` → show the
  server's validation summary in a `confirm()` → on OK, POST again
  without `dry_run` to commit; on cancel, toast "Import cancelled —
  nothing was written." Upload happens twice; files are capped at
  10 MiB so this is cheap, and it keeps the client dependency-free.

## 3. Changes

| File | Change |
|---|---|
| `services/import_/service.py` | `store_validation_report(job)` (reuses `ImportReport`). |
| `actions/standard/imports.py` | `_run_import(..., dry_run=...)` summary path; both actions forward `ctx.metadata["dry_run"]`. |
| `controllers/resource/imports.py` | Parse `dry_run` field; conditional `refresh-list` trigger. |
| `resources/action_handlers.py` | Same for the declarative stack. |
| `lexigram-ui/.../data_table_client_logic.py` | Validate-then-confirm flow in `LexigramImportUpload`. |
| tests | Dry run writes nothing; summary message/payload; validation report downloadable; both routes omit `refresh-list` on dry runs and still refresh on commits; client script carries `dry_run` + `confirm`. |

## 4. Implementation notes (post-verify)

- Landed exactly as designed; `_run_import` gained the `dry_run` branch
  and both actions forward `ctx.metadata["dry_run"]`. The declarative
  and controller routes parse the same truthy set (`1/true/on/yes`).
- Verified: 9 new regressions green (dry run writes nothing, commit
  still writes, dry-run→commit sequence, validation report downloadable
  via `report_csv`, both routes omit `refresh-list` on dry runs, client
  script carries the validate-then-confirm flow). Full admin unit suite
  **5498 passed / 7 skipped (76.60% coverage)**; lexigram-ui 1275
  passed; ruff check + format clean.
- Live-verified on the playground: `dry_run=1` upload → "Validated 2
  row(s): 2 ready to import, 0 with error(s). Nothing was imported."
  with a toast-only HX-Trigger (no `refresh-list`), and the rows are
  verifiably absent from the list; the follow-up commit POST imports
  them and restores `refresh-list: true`.
- Note: validation-error counts depend on the resource's import service
  config (`required_fields`/`allowed_fields`); the playground products
  resource declares none, so blank cells validate clean there.

