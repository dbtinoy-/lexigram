# Lexigram Admin Dashboard Delivery Tracker

**Scope:** `experimental/apps/lexigram-admin` and `experimental/apps/lexigram-ui`, with
contributor-contract compatibility fixes where an integrated dashboard surface
requires them.

**Status:** Core implementation complete; follow-up gap-hardening passes have
also covered optional extension integrations, the resource/form submission
boundary, and the settings form interaction and validation contract. This file
is the working plan and durable audit record for the `lexigram-admin` dashboard.

## Delivery principles

- Prefer working controls and complete request flows over review-only findings.
- Keep resource, contributor, table, form, and shell behavior compatible with
  both the default `/admin` mount and a configured custom mount such as
  `/backoffice`.
- Treat server-rendered HTML and HTMX fragments as two clients of the same
  behavior: both must carry state, permissions, CSRF, and accessible loading or
  error outcomes.
- Preserve safe defaults: unknown fields, actions, permissions, records, and
  external URLs fail closed or remain non-destructive.
- Add regression coverage at the seam where each bug was fixed.

## Work plan and completion record

| Area | Audit targets | Delivered |
| --- | --- | --- |
| Resource configuration | Resource discovery, names, data-source access, table/form configuration, relation metadata, action declarations | Resource handler now resolves configured data sources and resource controls consistently, validates names, and keeps CRUD/clone/archive/restore/purge behavior aligned with declared capabilities. |
| Resource handlers | CRUD, inline mutation, bulk operations, lifecycle hooks, async permissions, missing records, soft delete | Handlers enforce operation permissions, coerce field values through declared schemas, reject invalid or unknown fields, handle missing records safely, and preserve lifecycle/soft-delete semantics. |
| Resource fields and relations | Field rendering, relation options, belongs-to-many/morph controls, pivot data, HTML escaping | Relation option values and labels are kept distinct, free-form/accessor fields are supported, pivot data is normalized, and untrusted values are escaped before rendering. |
| Tables | State parsing, search, filters, sorting, grouping, pagination, density, visibility, views, columns, row/header/bulk actions | URL-controlled table state is sanitized against available fields; filter/range controls use the declared data source; pagination and bulk controls preserve state; action URLs and empty/error states are wired. |
| Table client behavior | HTMX swaps/OOB, selection, loading, responsive layout, accessibility | Client logic reinitializes after swaps, avoids stale selection state, keeps loading and empty states visible, and uses accessible labels/targets for controls. |
| Forms | Generated and declarative forms, coercion, validation, CSRF, errors, sections/layouts, relations, modal/slide-over/page flows | Both form paths carry hidden CSRF fields, preserve submitted values and validation errors, render field-level and form-level errors for native and HTMX responses, accept consistent boolean representations, and provide working submit/cancel paths for page, overlay, and custom-prefix modes. Edit validation also merges persisted values so disabled/hidden required fields do not produce false failures; relation controls avoid unauthorized option loads and degrade cleanly when their data source is unavailable. |
| Settings forms | Field widgets, effective-value context, validation recovery, readonly state, HTMX/native parity, navigation safety | Settings forms now resolve duplicate checkbox submissions correctly, reject invalid values without persisting defaults, preserve submitted values with inline accessible errors, expose bounds/scope/source metadata, use textarea/URL/numeric controls where appropriate, show dormant profiler status, provide sticky reset/save actions with duplicate-submit protection, and warn before leaving dirty forms. |
| Security boundaries | CSRF headers/forms, permission gates, mass assignment, unsafe redirects, script embedding | JSON/HTMX mutations send CSRF headers, form mutations include tokens, model/form exclusions and readonly fields are enforced server-side, submitted fields require both view and edit permission, relation option access fails closed, and command-palette JSON escapes HTML-significant characters before script embedding. |
| Dashboard widgets | Discovery, structured content, refresh, empty/error states, customization, reorder, filters, responsive grid | Core health/activity/metrics widgets, contributor widgets, refresh controls, widget configuration, page filters, and drag-and-drop reorder are connected to mounted endpoints and render structured fallbacks. |
| Navigation | Sidebar, clusters, secondary navigation, active state, user menu, custom prefix handling | Cluster centers and secondary links are prefix-aware, legacy contributor `/admin` URLs remain compatible, generic contributor links/badges are remounted, and user-menu destinations are generated from the active prefix. |
| Search and command palette | Search forms/results, command URLs, settings destination, safe embedded command data | Search forms, breadcrumbs, result links, static commands, and dynamic commands honor custom mounts; Settings points to a real destination; embedded command data cannot terminate its script element. |
| Shell and UI primitives | Breadcrumbs, system/user boxes, modal, topbar, sidebar, theme, responsive/accessibility behavior | Missing destinations render as non-links, shell URLs use the active mount, topbar notification/tenant controls are wired, and notification mutations carry the page CSRF token. |
| Notifications and observability | Inbox endpoints, SSE endpoint, notification navigation/spec compatibility, health/system pages | Notification navigation and mounted contributor routes remain compatible with custom mounts; the bell uses the active widget stream endpoint, inbox URLs are exposed for integration, and mark-read/mark-all requests include CSRF. Core System Info and health surfaces are available. |
| Optional extension integrations | Cache, tasks, search, resilience, storage, feature flags, and monitoring contract seams | Hardened the cache adapter around primitive `get`/`set` results, materialized the resilience factory into an executable pipeline, fixed async feature-flag evaluation, aligned storage URL expiry with the blob-store contract, and adapted first-party task queues to canonical jobs. Missing optional services remain non-fatal. |
| Regression coverage | Focused tests, custom-prefix seams, handler safety, rendering contracts | Added or updated tests cover omitted required fields, hook/data-source validation re-rendering, native/HTMX form-level errors, boolean representations, view-plus-edit field authorization, readonly/form exclusions, inline mutation, relation/form/table behavior, relation option failures and access gates, cluster/navigation prefixes, command-palette safety, shell wiring, restore/purge flows, contributor/dashboard rendering, and optional integration contracts. |

## Settings form follow-up

The settings pass deliberately keeps the existing registry and resource contracts
intact while closing the highest-risk form gaps:

- Boolean checkbox and hidden fallback pairs are parsed from all submitted values.
- Validation is strict on writes, while legacy reads still retain safe default
  fallback behaviour.
- HTMX validation fragments return `200` so HTMX's default response policy swaps
  the recoverable form; native submissions return `422` with the same form state.
- Secrets remain masked and blank submissions retain the stored value.
- Readonly/environment-backed specs render without save controls; deployment
  metadata supports both legacy namespaced environment variables and explicit
  standard names such as `ENVIRONMENT` and `LOG_LEVEL`.

## Routing and mount contract

Contributors may continue publishing canonical URLs under `/admin` for backwards
compatibility. The admin route integrator strips the canonical or configured
mount before registering inside the mounted admin application. Request-facing
navigation, search, widgets, shell controls, and redirects remount internal
URLs under the active prefix. External URLs are not rewritten.

The live stream endpoint is `/admin/_sse/widgets` by default and is remounted
under custom prefixes. The retired `/admin/_sse/events` path is not used by the
current notification bell.

## Verification record

Commands are run with the repository source paths and the available
`/tmp/lexigram-venv` because the system Python environment does not contain the
workspace packages.

- `compileall` over admin and UI source: passed.
- `git diff --check`: passed.
- Settings/controller/UI focused regression suite: passed (`98 passed, 1 warning`),
  including duplicate checkbox FormData, strict validation recovery, field-level
  errors, numeric constraints, multiline CSP controls, readonly settings, and
  tenant/store handling.
- Workspace `ruff check .` and `ruff format --check .`: passed after formatting
  the remaining baseline files touched by the delivery branch.
- Full admin unit suite after the latest URL and quality passes: passed
  (`4726 passed, 8 skipped, 13 warnings`).
- Full `lexigram-ui` suite after the latest quality passes: passed
  (`1342 passed, 78 skipped`).
- Focused dashboard/navigation/contributor suite: passed (`74 passed, 1 warning`).
- Focused SystemBox/Breadcrumbs/command-palette/settings suite: passed (`12 passed, 1 warning`).
- Cluster/navigation suite: passed (`26 passed, 1 warning`).
- UI notification bell suite: passed (`9 passed`).
- Full available admin unit suite: passed (`4726 passed, 8 skipped, 13 warnings`) after provisioning `argon2-cffi`; the prior auth-provider failure is resolved in the current test environment.
- Complete resource suite after the latest hardening: passed (`255 passed, 2 warnings`), including submission-boundary, relation-option, custom-prefix, wizard, and field-authorization coverage.
- Focused form/HTMX and accessibility UI checks: passed (`115 passed`).
- Earlier complete focused admin regression: passed (`160 passed, 2 warnings`).
- Permissions E2E: passed (`7 passed, 2 warnings`).
- Full UI suite: passed (`1342 passed, 78 skipped`).
- Follow-up custom-prefix regression suite: passed (`80 passed, 1 warning`), covering
  mounted auth/profile/error/plugin flows, action URLs, and UI breadcrumb/palette links.
- Reactive SSE bridge DI regression suite: passed (`11 passed, 1 warning`); the
  bridge now resolves to the callable factory instead of an eagerly-created
  response.
- Optional adapter and dependent resource suites: passed (`46 passed, 1 warning`);
  cache, storage, resilience, feature-flag, and task-queue contract seams are
  covered.
- Local preview smoke test: `/admin/`, `/admin/search`, and
  `/admin/infrastructure` return `200`; `/admin/_sse/widgets` returns a live
  `text/event-stream` response.

Known environment-limited checks from the audit baseline:

- Admin integration tests that import the unavailable `lexigram.ai` contributor
  cannot run in this environment.

## Follow-up checklist

- [x] Keep this tracker in the repository and update it with each dashboard audit pass.
- [x] Commit the completed implementation without author/co-author attribution.
- [x] Push only `arena/01a054ce-lexigram`.
- [x] Open the requested development pull request without merging it.
- [x] Add an explicit custom-prefix wizard regression and normalize legacy
      `/admin` wizard action URLs under the active mount.
- [ ] Resolve the current GitHub Actions startup failure: runs through
      `cd9f99a` fail all jobs before any workflow step executes, so the quality,
      integration, and coverage gates have not produced actionable results yet.
- [ ] Run browser/live-preview QA for desktop/mobile shell behavior, dark mode,
      dashboard reorder feedback, HTMX swaps, and resource/form flows.
- [x] Resolve the local auth-provider test dependency by provisioning
      `argon2-cffi`; the complete admin unit suite now passes locally.
- [ ] Resolve remaining CI/integration environment gaps when the missing AI
      dependencies and PostgreSQL/Redis services are available.
