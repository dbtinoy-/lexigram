# 24 — Job-based export lifecycle: DI wiring + download route (R28 / B30)

## 1. Problem

`ExportService` (services/export/service.py) implements a full async export
job lifecycle — job creation, chunked execution with cancellation (B21),
format backends (CSV/JSON/XLSX/PDF), background tasks, audit events — but it
is **dead infrastructure**:

- It is never registered in the admin DI bundle, so nothing can resolve it.
- Its two required constructor deps have no admin-side implementation:
  `BlobStoreProtocol` (the `storage = []` pyproject extra is empty) and
  `TaskManagerProtocol`.
- `_get_file_size` is a placeholder returning `0`.
- `_generate_download_url` is a placeholder that emits
  `/admin/exports/download/{file_path}` — a URL that (a) leaks the raw
  storage path, (b) invites path traversal if ever routed, and (c) has no
  route serving it anyway.

So a completed job carries a `download_url` no user can ever fetch.

## 2. Design

Goal: make the job flow *actually work* end to end with zero host
configuration, while remaining pluggable when a host provides real
implementations.

1. **Local fallbacks** (`services/export/fallbacks.py`, new):
   - `LocalExportBlobStore` — filesystem `BlobStoreProtocol` implementation
     rooted at `{tempdir}/lexigram-admin-exports` (configurable). All paths
     resolve *under* the root with a traversal guard; implements the surface
     the export stack uses: `upload`, `download`, `stream`, `exists`,
     `delete`, `info`, `list`. `upload` returns a proper `FileInfo`.
   - `InlineTaskRunner` — minimal `TaskManagerProtocol`: wraps
     `asyncio.create_task`, tracks live tasks, `shutdown_gracefully` cancels
     background tasks, `get_task_counts` reports.
2. **Service fixes** (`services/export/service.py`):
   - New ctor param `download_url_prefix: str = "/admin"`.
   - `_get_file_size` → `await self.storage.info(path)` and return
     `FileInfo.size` (fail-soft 0 on any storage error).
   - `_generate_download_url(job)` → `{prefix}/exports/{job_id}/download`.
     Keyed by **job id (uuid4)**, never by storage path.
3. **Download route** (`services/export/download.py`, new):
   `build_export_download_handler(export_service)` → Starlette handler for
   `GET {prefix}/exports/{job_id}/download`. Fail-closed checks in order:
   401 no authenticated user → 404 unknown job → 403 not owner
   (`job.user_id` must match `user.user_id`/`user.id`, superuser
   `is True` bypass; ownerless jobs are superuser-only) → 409 job not
   COMPLETED / no file yet → 410 file missing in storage. Success streams
   bytes with the format's MIME type, `Content-Disposition: attachment`,
   and `Cache-Control: no-store`.
4. **DI wiring**:
   - `di/sub_providers/export.py` (new): `AdminExportSubProvider`.
     `register()` builds `ExportService` with the local fallbacks and
     `download_url_prefix=config.prefix` and binds it as a singleton.
     `boot()` opportunistically upgrades `storage` / `task_manager` /
     `audit` / `messaging` from container-registered protocol
     implementations when a host provides them (try/except per dep —
     absence is normal).
   - `bundle_provider.py`: add the sub-provider to the list; call a new
     `_mount_export_download(admin_resolver, ctx)` step during mount.
   - `di/mount/contributors.py`: `_mount_export_download` mirrors the SSE
     pattern — resolve `ExportService`, `router.add_route("/exports/{job_id}/download", "GET", …)`,
     non-fatal on failure.

Non-goals (kept out deliberately): an exports UI page listing jobs, and
wiring bulk-action exports through the job flow (direct download already
covers those; queue item remains).

## 3. Changes

| File | Change |
| --- | --- |
| `services/export/fallbacks.py` | NEW — `LocalExportBlobStore`, `InlineTaskRunner`. |
| `services/export/service.py` | `download_url_prefix` ctor param; real `_get_file_size` via `storage.info`; job-id `_generate_download_url`. |
| `services/export/download.py` | NEW — `build_export_download_handler`. |
| `di/sub_providers/export.py` | NEW — `AdminExportSubProvider`. |
| `di/bundle_provider.py` | Register sub-provider; add `_mount_export_download` step. |
| `di/mount/contributors.py` | `_mount_export_download` route mounting. |
| `tests/unit/services/test_export_job_lifecycle.py` | NEW — fallback store (traversal guard, round-trip, info), inline runner, url/size fixes, download handler auth/status matrix, end-to-end job → download. |

## 4. Implementation notes (post-verify)

- **Tests:** new `tests/unit/services/test_export_job_lifecycle.py` — 25/25
  passed first try. Existing export suites still green (71 total targeted).
  Full admin unit suite: **5523 passed / 7 skipped / 77% cov**.
- **Pre-existing test updates:** sub-provider count assertions in
  `test_bundle_provider.py` / `test_integration_boot.py` went 9 → 10 (the
  new `AdminExportSubProvider`), and one `test_background_jobs.py` assertion
  pinned the *old placeholder* URL shape
  (`/admin/exports/download/{path}`) — updated to the job-id shape.
- **Live verify** (playground, restarted with R28 code): boot log shows
  `admin.export_download_route_registered path=/admin/exports/{job_id}/download`;
  unauthenticated `GET /admin/exports/x/download` → **307** to
  `/admin/login?next=…` (auth guard fires before the handler);
  authenticated GET with a bogus job id → **404** "Export job not found"
  from the handler, proving the route resolves the DI singleton. The
  200/403/409/410 paths need an in-process job (registry is in-memory), and
  are covered by the end-to-end unit tests (`execute_export` → handler →
  200 CSV with `attachment` + `no-store` headers).
- **Design notes:** the auth guard already 307s anonymous requests, so the
  handler's 401 branch is defense-in-depth for stacks that mount the route
  without the middleware chain. `boot()` upgrades are per-dependency and
  identity-checked, so a host registering only `BlobStoreProtocol` keeps the
  inline task runner. `LocalExportBlobStore.upload` accepts bytes/str/
  file-like/async-iterator payloads because the contract's `Uploadable`
  union allows all four.
- **Deliberately unchanged:** the B21 cancellation checks in
  `execute_export`; the bulk-action direct-download exports (R25) — the job
  flow is additive infrastructure, and a jobs UI page remains a queue item.

