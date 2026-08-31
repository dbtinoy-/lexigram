# Lexigram Admin Dashboard Delivery Tracker

**Scope:** `experimental/apps/lexigram-admin` and `experimental/apps/lexigram-ui`, with
contributor-contract compatibility fixes where an integrated dashboard surface
requires them.

**Status:** Core implementation complete; follow-up gap-hardening passes have
also covered optional extension integrations, the resource/form submission
boundary, and the settings form interaction and validation contract. The shared
form UX pass now covers settings, generated/declarative resource forms, the
legacy builder form, and the resource wizard without merging their domain
contracts. Browser/live-preview verification and remaining primitive parity are
still explicit follow-ups. This file is the working plan and durable audit
record for the `lexigram-admin` dashboard.

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
| Forms | Generated, declarative, builder, and wizard forms; coercion, validation, CSRF, errors, sections/layouts, relations, modal/slide-over/page flows | All current resource form paths carry hidden CSRF fields, shared markers/status/action metadata, preserve submitted values and validation errors, render field-level and form-level errors for native and HTMX responses, accept consistent boolean representations, and provide working submit/cancel paths for page, overlay, wizard, and custom-prefix modes. Edit validation also merges persisted values so disabled/hidden required fields do not produce false failures; relation controls avoid unauthorized option loads and degrade cleanly when their data source is unavailable. |
| Settings forms | Field widgets, effective-value context, validation recovery, readonly state, HTMX/native parity, navigation safety | Settings forms now resolve duplicate checkbox submissions correctly, reject invalid values without persisting defaults, preserve submitted values with inline accessible errors, expose bounds/scope/source metadata, use textarea/URL/numeric controls where appropriate, show dormant profiler status, provide sticky reset/save actions with duplicate-submit protection, and warn before leaving dirty forms. |
| Shared form UX alignment | Resource `SchemaField`/`FormBase` and settings `ConfigNode`/`ConfigRegistry` contracts, common `lexigram.ui` controls, loading/dirty/error behavior, page/modal/slide-over parity | Initial adoption delivered: resource and settings forms retain separate domain contracts, while generated/declarative/builder/wizard resource forms and settings forms opt into shared `lexigram.ui` form/action semantics and one shell-loaded delegated dirty/loading/duplicate-submit behavior layer that survives HTMX swaps and overlays. |
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

- Readonly/environment-backed specs render without save controls; deployment
  metadata supports both legacy namespaced environment variables and explicit
  standard names such as `ENVIRONMENT` and `LOG_LEVEL`.
- The former settings-only interaction script is now removed from `ConfigLayout`.
  A single idempotent shell script handles settings, generated resource forms,
  and declarative `FormBase` forms, including externally associated modal/footer
  submit buttons.
- Resource form surfaces now carry the shared form marker, status region, action
  marker, sticky action styling, and submit lifecycle behavior without changing
  resource validation, relation, field-RBAC, or overlay contracts.
- The legacy builder `Form` and resource wizard now carry the same marker,
  status, action, and CSRF contract. Wizard fields reuse relation option loading,
  field view/edit authorization, submitted values, and field errors when those
  adapters are available; empty wizard definitions fail with an accessible
  `422` response.

## Shared form UX alignment plan

### Why the contracts remain separate

Resource forms and settings forms already use the same low-level
`lexigram.ui` atoms in many places (`TextInput`, `TextArea`, `NumberInput`,
`Select`, `MultiSelect`, `Switch`/`Toggle`, and shared accessibility-aware
input primitives). They must not be collapsed into one persistence model:

- Resource forms are driven by `SchemaField`, `FormBase`, `FormRenderer`, and
  the field renderer registry. They need model coercion, record create/edit
  semantics, relations, relation-option authorization, field-level RBAC,
  sections/tabs/wizards, and page/modal/slide-over rendering.
- Settings forms are driven by `ConfigSpec`, `ConfigNode`, `ConfigRegistry`, and
  `ConfigDashboardUI`. They need global/tenant scope, environment/database
  stores, readonly deployment values, secret retention, effective-value
  metadata, and runtime applicability status.

The target is therefore shared presentation and interaction behavior, not a
resource-shaped wrapper around configuration persistence.

### Current implementation inventory

| Surface | Current path | Reuse status | Alignment gap |
| --- | --- | --- | --- |
| Generated resource fields | `admin/resources/field_renderer.py` and `field_renderers_*.py` | Uses `lexigram.ui` atoms through `FieldRendererRegistry` | Generated create/edit forms now attach the shared form marker/status/action contract; field-level semantics remain owned by `SchemaField`. |
| Declarative resource forms | `admin/forms/components.py`, `admin/forms/form.py`, `admin/forms/layout.py` | `SchemaField.render_form()` uses shared UI field primitives and renders field/global errors | `FormBase` and the legacy builder `Form` expose the shared marker/status/action contract without losing layouts or model validation. |
| Settings forms | `admin/settings/panel/ui.py` and `controllers/settings.py` | Uses shared UI atoms, `FieldSchema`, `Form`, and `FormActions` | Settings retains its legacy markers and domain metadata while using the shell-level delegated behavior; no resource CRUD assumptions were introduced. |
| Form state/validation | `admin/forms/state.py`, `admin/forms/validation.py`, settings node validation | Domain-appropriate server-side implementations already exist | Browser interaction state and server validation responses need one explicit cross-form contract. |

### Target architecture

1. **Preserve domain adapters.** Keep `ConfigNode` and `SchemaField` as the
   source of truth for their respective validation, coercion, persistence, and
   authorization rules. Add small adapters/metadata mappers where a field must
   be rendered, rather than converting one model into the other.
2. **Use one presentation vocabulary.** Standardize labels, required markers,
   help text, readonly state, error IDs, `aria-invalid`, `aria-describedby`,
   numeric constraints, input types, and action button states through
   `lexigram.ui` components. Prefer `FormField`/`FieldSchema`, `FormActions`,
   `TextArea`, and the existing input atoms over per-surface HTML.
3. **Introduce one admin form behavior contract.** All editable admin forms
   should opt into stable attributes such as `data-admin-form`,
   `data-admin-form-status`, and `data-admin-navigation`. The behavior layer
   should be event-delegated so it survives HTMX swaps and dynamically loaded
   modal/slide-over content.
4. **Load the behavior once from the admin shell.** Move the current settings
   interaction script out of `ConfigLayout` into a shared shell/admin form UX
   script. It must be idempotent and must not depend on a form being present at
   initial page load.
5. **Keep response contracts explicit.** Native invalid submissions return a
   full page with `422`; HTMX invalid submissions return a swappable `200`
   fragment containing the form and field errors, because the default HTMX
   response policy does not swap `4xx` responses. Successful saves preserve the
   existing redirect/fragment behavior.
6. **Keep security server-side.** Client-side dirty checks, browser constraints,
   disabled buttons, and confirmations are usability features only. CSRF,
   permissions, mass-assignment protection, readonly enforcement, relation
   authorization, secret masking, and validation remain authoritative on the
   server.

### Delivery phases

#### Phase A — Shared contracts and primitive parity

- Add a documented shared admin-form UX contract and stable data attributes.
- Extend the shared form/action components only through backwards-compatible
  optional arguments.
- Normalize action buttons to one primary submit action, optional reset/cancel,
  visible focus states, loading text, disabled duplicate submits, and a polite
  status region.
- Ensure all field families expose the same required/help/error/readonly
  semantics and that number bounds reach both browser markup and server
  validators.
- Decide and document the `Switch` versus `Toggle` naming compatibility path;
  do not remove either public component without a deprecation window.

#### Phase B — Shared browser behavior

- Move dirty tracking, `beforeunload`, settings/resource navigation warnings,
  submit locking, loading status, and HTMX failure recovery into one delegated
  script.
- Mark forms rendered by `ConfigDashboardUI`, generated resource forms, and
  declarative `FormBase` forms with the shared contract.
- Reset dirty state after a successful swap/redirect and restore the submit
  button after network or server failures.
- Protect against duplicate listeners after body or fragment swaps.
- Do not use browser `confirm()` for ordinary navigation; use it only for
  unsaved changes or explicitly dangerous changes.

#### Phase C — Settings adapter cleanup

- Retain settings-specific persistence and validation, but route field/action
  rendering through the shared form contract.
- Keep tenant/global scope, source metadata, readonly environment values,
  dormant-runtime warnings, and secret retention intact.
- Add explicit high-impact setting metadata for security, anonymous access,
  cache, rate-limit, and branding changes. Confirmation is opt-in per field,
  not global to every settings save.
- Keep “Reset form” as a client-side discard-to-loaded-values action. Add a
  separate, confirmed server-side “Reset to application defaults” operation
  only if its audit and authorization contract is defined.
- Remove the legacy query-parameter form path after compatibility tests confirm
  no active route depends on it.

#### Phase D — Resource form adoption

- Apply the shared form attributes and browser behavior to all resource form
  paths: generated model forms, custom `FormBase` forms, the legacy builder
  `Form`, and wizard forms.
- Preserve resource-specific relation controls, searchable relation endpoints,
  field RBAC, excluded fields, sections, tabs, wizard steps, and overlay forms.
- Add sticky actions only where the form container can safely own them; avoid
  placing a second action bar inside modal/slide-over footers.
- Preserve submitted values and field/global errors on create and edit failures,
  including errors after HTMX overlay swaps.
- Ensure readonly and hidden resource fields are not accidentally submitted or
  required during edit validation.

#### Phase E — Operational completeness

- Add read-versus-edit permission metadata for settings where read-only
  operators need visibility.
- Add effective-value source/scope metadata to resource/configuration views
  where an override chain exists.
- Define runtime applicability (`active`, `restart required`, or `dormant`) for
  settings before exposing a control as operational.
- Add safe audit diffs and rollback only for non-secret values; never record or
  render secret contents.
- Add optimistic concurrency checks where two administrators can overwrite the
  same resource or settings namespace.

### Acceptance criteria

Every editable admin form must satisfy all of the following in both native and
HTMX modes:

- One accessible primary submit action; no accidental duplicate submit buttons.
- CSRF token/header is present and validated for the active mount.
- View/edit permissions and readonly/mass-assignment rules are enforced on the
  server, not only represented by disabled controls.
- Invalid input remains visible, is associated with the correct field, and is
  announced through accessible error/status markup.
- Validated values are saved with the declared type; invalid values never become
  silent defaults.
- Blank secrets retain the existing secret; submitted secret values never occur
  in HTML, toast content, audit metadata, or logs.
- Duplicate submissions are prevented while a request is in flight, but failed
  requests re-enable the form and preserve the user's data.
- Dirty navigation warnings work for full navigation, HTMX namespace/resource
  navigation, modal/slide-over opening, and browser unload, without warning
  after a successful save or a clean reset.
- Default `/admin` and custom mounted prefixes generate identical relative
  behavior for form actions, relation endpoints, redirects, breadcrumbs, and
  HTMX targets.
- Desktop, mobile, keyboard, screen-reader, light-mode, and dark-mode layouts
  remain usable; sticky actions do not cover fields or trap focus.
- Resource relation options remain bounded, escaped, permission-checked, and
  unavailable when their data source is unavailable.

### Required regression matrix

| Test seam | Required coverage |
| --- | --- |
| Shared controls | Required markers, help/error associations, `aria-invalid`, readonly, number min/max/step, textarea, URL/email/color/password controls, focus styles. |
| Submission | Native and HTMX success/failure, duplicate submit, network failure recovery, missing fields, repeated checkbox values, omitted unchecked booleans, malformed types, atomic invalid saves. |
| Settings | Global and tenant scope, environment aliases, source metadata, secret preservation/non-leakage, dormant status, dangerous-setting confirmation, reset behavior, custom prefixes. |
| Resources | Generated and declarative forms, create/edit, model errors, field/global errors, field RBAC, excluded/readonly fields, relation option access, sections/tabs/wizards, page/modal/slide-over flows. |
| Navigation | Dirty HTMX namespace/resource links, browser unload, cancel/reset, redirect after save, body swaps, repeated script initialization, mobile navigation. |
| Security | CSRF session selection, permission denial, mass assignment, readonly POSTs, tenant isolation, audit metadata redaction, no unsafe external URL rewriting. |
| Quality | Full admin suite, full UI suite, focused form/accessibility suite, compile/lint/format/diff checks, browser/live-preview smoke tests. |

### Planned file ownership

- `experimental/apps/lexigram-ui/src/lexigram/ui/atoms/inputs/*`: shared
  input semantics and visual primitives only.
- `experimental/apps/lexigram-ui/src/lexigram/ui/molecules/form_actions.py`
  and `organisms/forms.py`: backwards-compatible shared form/action APIs.
- `experimental/apps/lexigram-admin/src/lexigram/admin/forms/*`: shared admin
  form UX contract, behavior metadata, and declarative-form integration.
- `experimental/apps/lexigram-admin/src/lexigram/admin/ui/templates/shell_scripts.py`:
  one idempotent delegated browser behavior script loaded by the shell.
- `experimental/apps/lexigram-admin/src/lexigram/admin/resources/*`: resource
  adapters and generated/custom form adoption; no removal of relation/RBAC
  safeguards.
- `experimental/apps/lexigram-admin/src/lexigram/admin/settings/*`: settings
  adapters and registry-specific validation/persistence; no conversion to a
  resource CRUD model.
- `experimental/apps/lexigram-admin/tests` and `experimental/apps/lexigram-ui/tests`:
  contract, regression, accessibility, and mounted-prefix coverage.

### Rollout and compatibility rules

- Implement the shared contract behind opt-in attributes first, then migrate
  resource/settings forms, then remove only demonstrably unused local markup.
- Keep existing public component signatures and route contracts compatible;
  introduce optional parameters and deprecation warnings where needed.
- Deliver in reviewable commits: shared contract, browser behavior, settings
  adoption, resource adoption, then cleanup and verification.
- Commit completed work without author/co-author attribution, push only
  `arena/01a054ce-lexigram`, and keep PR #24 open and unmerged.
- Docker/PostgreSQL/Redis, GitHub Actions, and browser/live-preview checks remain
  explicit verification gates rather than assumptions from unit tests.

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
- Shared form UX adoption regression suite: passed (`117 passed, 1 warning`),
  covering generated, declarative, builder, settings, overlay/page, wizard, and
  mounted resource form contracts; the shell behavior suite passed (`22 passed,
  1 warning`).
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
- [x] Establish the shared form marker/status/action contract and backwards-
      compatible form APIs for settings and resource forms.
- [x] Move dirty/loading/duplicate-submit behavior to one idempotent shell-loaded
      delegated script, including externally associated overlay submit buttons.
- [ ] Complete Phase A primitive parity: unify remaining action styling,
      reset/cancel semantics, and field metadata across all form families.
- [x] Implement the initial Phase B delegated, HTMX-safe dirty/loading/
      duplicate-submit behavior layer for settings and generated/declarative
      resource page and overlay forms.
- [ ] Complete Phase B browser-level verification, including failure recovery,
      dirty HTMX navigation, focus behavior, and mobile sticky actions.
- [x] Complete the initial resource-form adoption matrix for relation-option and
      wizard flows, while retaining generated/declarative page/modal/slide-over
      coverage. Browser-level verification remains separately tracked below.
- [ ] Add effective-value/runtime applicability/read-versus-edit metadata and
      audited non-secret history where the underlying contracts support it.
- [ ] Resolve the current GitHub Actions startup failure: runs through
      `cd9f99a` fail all jobs before any workflow step executes, so the quality,
      integration, and coverage gates have not produced actionable results yet.
- [ ] Run browser/live-preview QA for desktop/mobile shell behavior, dark mode,
      dashboard reorder feedback, HTMX swaps, and resource/form flows.
- [x] Resolve the local auth-provider test dependency by provisioning
      `argon2-cffi`; the complete admin unit suite now passes locally.
- [ ] Resolve remaining CI/integration environment gaps when the missing AI
      dependencies and PostgreSQL/Redis services are available.
