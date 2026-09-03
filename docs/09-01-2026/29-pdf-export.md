# 29 — R33: PDF export format in the export center

## 1. Problem

The job-flow export service has shipped a `PdfExportBackend`
(`services/export/adapters/pdf.py`, reportlab-based, registered for
`ExportFormat.PDF` in `ExportService.__init__`, download content-type
already mapped) since R28 — but it is **dead weight**: the export center
allowlist (`EXPORT_PAGE_FORMATS`) deliberately excludes `pdf`, so no UI
path can ever reach it. The queue tracked "pdf export format" as the
remaining item.

There is also an availability UX gap shared with xlsx: both `xlsx` and a
future `pdf` option render in the "New export" form even when their
optional library (openpyxl / reportlab) is missing — the user only finds
out via a FAILED job with an ImportError message. `reportlab>=4.0.0` is
already declared in the `export` extra and the dev group of the admin
`pyproject.toml`, so enabling the format adds **no new dependency**.

## 2. Design

### 2.1 Enable `pdf` in the page allowlist

`EXPORT_PAGE_FORMATS` gains `"pdf": ExportFormat.PDF`. Everything
downstream already works: backend registered, `download.py` maps
`ExportFormat.PDF → application/pdf`, the R32 polling region and progress
bar are format-agnostic.

### 2.2 Library-availability gating (applies to xlsx too)

New module-level helper in `pages.py`:

- `page_format_available(key)` — `csv`/`json` always `True`; `xlsx` reads
  `lexigram.admin.services.export.xlsx.HAS_OPENPYXL`; `pdf` reads
  `lexigram.admin.services.export.adapters.pdf.HAS_REPORTLAB`. Flags are
  read **at call time via the module attribute** so tests can monkeypatch
  them (same technique as R29's `HAS_OPENPYXL` tests).
- `_create_form` only offers available formats — no dead options.
- `create` re-checks availability server-side and returns **501** with a
  clear "install <package>" message when a known-but-unavailable format is
  posted directly (form spoofing / stale page). Unknown formats keep the
  existing 400.

This mirrors the R29 contract (missing openpyxl → 501, not a crash) at
the page layer, and fails *before* a job is created — no FAILED job noise.

### 2.3 Backend review (no changes needed)

`PdfExportBackend` was audited: `ExportJob.filters`/`columns` exist,
`LocalExportBlobStore.upload` accepts `content_type`, table cells are
plain strings (no markup interpretation → no injection surface), rows
capped at 1000 with an explicit "use CSV/Excel for complete dataset"
note. reportlab 5.0.1 satisfies the `>=4.0.0` pin.

### 2.4 Out of scope

- PDF as a *bulk action* format (R29's `export_xlsx` pattern) — direct
  synchronous PDF rendering of large selections is a different
  latency/size profile; the job flow is the right home for PDF.
- Custom PDF layout/branding — backend's default report layout is kept.

## 3. Implementation steps

1. `services/export/pages.py` — allowlist entry, `page_format_available`,
   form filtering, 501 guard in `create`.
2. Tests (`tests/unit/services/test_export_center.py`):
   - allowlist now `{csv, json, xlsx, pdf}`;
   - form omits `pdf`/`xlsx` when their flags are monkeypatched off;
   - `create` → 501 for posted-but-unavailable format, job count stays 0;
   - end-to-end pdf job (skipif no reportlab): create → background run →
     COMPLETED, artifact starts with `%PDF`, download URL set.
3. Live verify: create a `products`/`pdf` export in the playground,
   download → 200, `application/pdf`, `%PDF` magic bytes.
4. Fill §4, README index row, commit + push (PR #26 stays unmerged).

## 4. Verification

- Unit: `test_export_center.py` — **28/28 passed** (new class
  `TestFormatAvailability`: csv/json always available, unknown format
  unavailable, `HAS_OPENPYXL`/`HAS_REPORTLAB` monkeypatched flags are read
  at call time, form omits `pdf` when reportlab is flagged off and offers
  it when on, `create` with an unavailable format → **501** naming the
  missing package with **no job created**, end-to-end pdf job →
  COMPLETED + `%PDF-` artifact + download URL; existing
  `test_unknown_format_400` updated to use a genuinely unknown format
  (`dbf`) since `pdf` is now known).
- Full admin unit suite: **5586 passed / 7 skipped** (was 5579/7; +7, no
  regressions), coverage 76.96%.
- Live playground loop (serve.py restarted, fresh login):
  - `GET /admin/exports` form offers all four formats
    (`csv`/`json`/`xlsx`/`pdf`) — reportlab 5.0.1 installed in the venv.
  - POST create products/pdf → 303; jobs fragment shows the job
    `completed` with format `PDF`.
  - Download → 200, `content-type: application/pdf`,
    `content-disposition: attachment; filename="products_export_….pdf"`,
    `X-Content-Type-Options: nosniff`, body starts with `%PDF-1.4`
    (2,635 bytes for 20 products).
- Dependency note: `reportlab>=4.0.0` was **already declared** in the
  admin `export` extra and dev group — no pyproject change needed; the
  sandbox venv install (5.0.1) satisfies the pin. Hosts without reportlab
  simply don't see the pdf option and get a clean 501 on direct POSTs.
- Known limits: PDF table renders the first 1000 rows with an explicit
  truncation note (backend behavior, unchanged); layout is the backend's
  default report style.
