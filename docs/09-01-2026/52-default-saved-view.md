# 52 — Default Saved View (R54) (Full Plan)

**Date:** 2026-09-03 · **Status:** ✅ Implemented · **Branch:**
`arena/01a05b98-lexigram`

## 1. Context

R13 shipped per-user named saved views, including safe query
canonicalization, one-click application, and deletion. One deliberate
follow-up remains in that plan: an operator can save a useful view, but the
list page cannot remember which view should open by default.

This is the next smallest high-value saved-view increment. It should reuse
the existing settings-backed storage and POST/redirect patterns without
introducing a migration, JavaScript-only state, or a redirect loop.

## 2. Goals and non-goals

### Goals

- Store one optional default flag per user's resource-specific saved views.
- Let the operator set a view as default and clear the current default from
  the existing views bar.
- On a full-page visit to a resource with no meaningful list query, redirect
  once to the sanitized default view query.
- Keep explicit searches, filters, pagination, HTMX fragment swaps, and
  mutation notices authoritative; they must not be overwritten by the
  default redirect.
- Preserve compatibility with R13 records that do not have a `default` key.
- Keep storage failures and corrupt records fail-soft for list rendering.

### Non-goals

- Shared/team defaults or cross-user views; ownership and permission design
  remains a separate project.
- Automatically changing a user's current URL after they choose a different
  view; explicit URL state always wins.
- A new database table or migration.

## 3. Design

### 3.1 Storage service

Extend `SavedViewService` with a boolean `default` field. Missing or invalid
values normalize to `False`; at most one entry is returned as default. New
views are not silently made default, while an upsert preserves the existing
entry's default flag.

Add:

- `get_default_view(user_id, resource) -> dict | None`, returning a sanitized,
  non-empty default entry or `None`.
- `set_default_view(user_id, resource, name | None) -> bool`, where a name
  selects exactly one existing view and `None` clears the current default.
  Invalid/missing target names raise `SavedViewError`; storage failures are
  converted to the existing friendly error contract.

Deleting a default naturally removes the default. Legacy entries continue to
round-trip unchanged except for the normalized false flag.

### 3.2 Controller

Add `POST /admin/views/{resource_name}/default` to
`SavedViewsController`.

- Require the existing authenticated-user guard and CSRF validation.
- Accept `name` plus a `default` value (`1` selects; `0` clears).
- Redirect to the canonical list URL with a success/error notice.
- Validate the resource and target through `SavedViewService`; never accept a
  user-controlled redirect destination.

### 3.3 List renderer

Add a small star/unstar form to each saved-view pill, using the same CSRF
field and POST/redirect UX as delete. A filled star means the view is the
current default; an empty star sets it. The control remains usable without
JavaScript.

Before parsing/fetching a full-page list request, ask the mounted service for
its default only when:

- the request is not a fragment swap;
- the query has no meaningful sanitized list state; and
- the URL has no `notice` or `error` marker from a mutation redirect.

If a valid default exists, return a 302 to the resource URL with only the
sanitized saved query. The redirected request contains meaningful state, so it
renders normally and cannot redirect again. Service or storage errors log a
warning and fall through to the normal list response.

## 4. Security and compatibility

- Defaults are scoped by the existing user ID and resource slug key.
- Saved query strings still pass through the existing whitelist and length
  limits before storage or redirect.
- Default selection is POST-only and CSRF-protected.
- HTMX data-zone swaps do not redirect, so filtering/pagination behavior is
  unchanged.
- `notice` and `error` query markers suppress auto-apply for one request, so
  users can see the result of setting, clearing, saving, or deleting a view.
- Corrupt/multiple-default payloads are normalized deterministically; the
  first valid default wins and future writes repair the shape.

## 5. Test plan

- Service tests for legacy records, default preservation on upsert, setting a
  default, replacing it, clearing it, missing targets, deletion, corrupt
  multiple-default records, and storage failures.
- Controller tests for authenticated access, CSRF rejection, set/clear
  redirects, missing targets, and unavailable storage.
- Renderer tests for star state, escaped form values, default redirect on a
  clean full-page request, explicit query precedence, notice/error precedence,
  fragment precedence, and service-failure fallback.
- Run the admin and UI package suites, the first-run e2e scenario, static
  checks, and the existing focused toast regression.

## 6. Rollout and acceptance criteria

- [x] Service supports one optional default per user/resource.
- [x] Controller exposes safe CSRF-protected set/clear mutation.
- [x] Views bar exposes set/clear controls with accessible labels.
- [x] Clean full-page list visits apply the default exactly once.
- [x] Explicit state, HTMX fragments, and mutation notices are preserved.
- [x] R13 legacy records remain readable and writable.
- [x] Regression tests and relevant package checks pass.
- [x] Commit and push only to `arena/01a05b98-lexigram`; PR #26 remains open.
- [ ] Playground/browser verification remains a separate resumed step.

## 7. Implementation and verification notes (2026-09-03)

- `SavedViewService` now normalizes legacy entries, preserves the default on
  case-insensitive upserts, enforces one default, and treats invalid marked
  entries safely.
- `SavedViewsController` adds the CSRF-protected set/clear endpoint; the
  views bar uses accessible star/unstar controls without requiring JavaScript.
- `ListRenderer` applies a sanitized default only to a clean full-page visit;
  explicit state, pagination/cursors, HTMX fragments, and mutation notices
  remain authoritative, and failures fall through to the normal list.
- Focused saved-view tests: **88 passed**; admin suite: **6,114 passed / 34
  skipped**; UI suite: **1,452 passed / 78 skipped**; first-run e2e: **2
  passed**; admin mypy: **600 source files, no issues**; ruff, formatting,
  Node syntax validation, and `git diff --check` pass.
- Playground/browser confirmation is intentionally deferred per the active
  tactical direction.
