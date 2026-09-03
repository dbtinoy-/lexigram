# 57 — Settings control-plane audit and hardening (Full Plan)

**Date:** 2026-09-03 · **Status:** complete · **Roadmap:** R57 · **Branch:**
`arena/01a05b98-lexigram`

## 1. Purpose and acceptance criteria

The Configuration Center is an important operational boundary, not just a
collection of HTML forms. This Full Plan audits the complete `/settings`
control plane: specification discovery, source ownership, effective-value
loading, validation, persistence, permissions, CSRF, optimistic concurrency,
audit records, history/rollback, and the browser-facing form contract.

The implementation is complete only when:

- every registered spec has a tested source-of-truth declaration and a form
  that either saves through its declared store or is explicitly read-only;
- database-backed falsy values (`false`, `0`, and an intentional empty string)
  remain effective after a round trip and are labelled correctly as configured
  rather than being mistaken for defaults;
- field validation is strict on POST, preserves invalid input for correction,
  reports field-level errors accessibly, and never persists invalid data;
- YAML/application-owned effective configuration is visible in an explicitly
  read-only panel, with secret values redacted and source precedence explained;
- permissions, CSRF, tenant scope, revision checks, conditional writes, audit
  metadata, and rollback boundaries remain fail-closed;
- settings history is useful to operators, does not record failed saves, never
  stores secrets, and is available through a durable adapter when a database is
  present while retaining the in-memory development fallback;
- contributor specs can add typed fields and source metadata without editing
  controller code;
- targeted settings/controller/UI tests, the admin unit suite, lint/type
  checks, and `git diff --check` pass. Playground/browser round-trip testing
  remains intentionally deferred.

## 2. Audit findings

### 2.1 Effective database values were not faithfully read

`AdminSettingsService.get()` used truthiness when selecting a stored value,
so a saved `false`, `0`, or empty string fell through to the default. This
made cache disabling and the documented empty `X-Frame-Options` behavior
impossible through the panel. The cache middleware also called the
tenant-oriented service with a key/default signature, so its runtime override
path did not address the mounted service correctly.

### 2.2 Source metadata was opaque for the production store

The registry already had an origin/default metadata contract, but
`TenantConfigStore` did not implement `contains()`. Every database field was
therefore presented as an unknown external value rather than a configured DB
override or application default. The fix must preserve `None` for genuinely
opaque adapters while making the built-in DB adapter truthful.

### 2.3 Configuration ownership was incomplete in the UI

The built-in specs cover writable runtime overrides and a small environment
info panel, but the effective `AdminConfig` hierarchy (including values
supplied by YAML, environment, or application code) had no discoverable
read-only view. Operators could not tell why a value was present or where to
change it. A read-only effective-configuration panel will expose a redacted
summary and precedence, without pretending that YAML/config-owned state is
admin-writable.

### 2.4 Validation and extensibility were narrower than the model contract

Node derivation handled booleans, integers, literals, and strings, but did not
carry common string constraints or JSON/list/dict field types into the form
contract. Several built-in settings accepted blank or malformed values that
would be unsafe or misleading at runtime. Typed node helpers and strict POST
validation will be additive and override-friendly; legacy loading behavior
will not be changed accidentally.

### 2.5 History existed only as an internal, volatile mechanism

Snapshots were captured before the write, which left a history record when a
conditional write subsequently lost a race. The default store was in memory
and there was no settings history UI. History/rollback must remain optional
and best-effort with respect to the primary save, but successful changes need
an operator-visible record and a durable store when the database is available.

## 3. Design

### 3.1 One source-of-truth boundary

Keep `ConfigSpec` as the contributor-facing contract. Each spec declares its
namespace, scope, permissions, runtime status, and store. The registry will
expose read metadata through `StoreBase.contains()` and a small read-only
configuration store adapter. A store that cannot prove presence continues to
return `configured=None`, so the UI never invents an origin.

The application-configuration panel is deliberately read-only. It presents a
redacted JSON summary of the effective `AdminConfig`, the source precedence
(`runtime override → environment → YAML → model defaults`, as applicable),
and the configured YAML path when the loader knows one. It is not a second
write path and does not expose session secrets, setup tokens, passwords, API
keys, DSNs, or secret-derived identifiers.

### 3.2 Strict, typed form pipeline

Node `validation_error()` remains the non-destructive POST validator; `validate()`
continues to provide the compatibility fallback used while reading legacy
values. Typed JSON, URL/email, string-length/pattern, integer-bound, enum, and
boolean semantics are represented in node metadata so custom specs get the
same renderer and validation behavior. Read-only nodes are filtered on the
server regardless of submitted field names.

The form renders explicit source/origin hints, defaults, read-only state,
runtime applicability, accessible error associations, a stable revision, and
an action bar. Read-only textual values remain selectable for inspection;
mutating controls and save actions are absent when no editable node exists.

### 3.3 Safe persistence and concurrency

The service must preserve stored falsy values and expose presence separately
from value. Controller saves continue to require CSRF and a revision token,
apply tenant scope, validate the complete submitted batch before writing, and
use conditional writes where the store supports them. A no-op does not create
misleading history. A failed conditional write creates no snapshot.

Snapshots are captured after a successful conditional write using the exact
pre-write effective values. The in-memory adapter remains a development
fallback; a database adapter stores redacted values and metadata in an
application-owned table, with namespace/tenant checks on rollback. The UI
shows recent entries and routes restoration back through the normal POST path,
so permissions, CSRF, validation, revision checks, audit, and a new snapshot
still apply.

### 3.4 Contributor ergonomics

New specs continue to be registered by `register_spec(registry)` and do not
need controller changes. Store adapters can opt into `contains()` and
conditional writes independently. A small registry validation/introspection
surface will make duplicate namespaces, missing names, invalid node metadata,
and read-only/store mismatches diagnosable without weakening existing
best-effort contributor boot behavior.

## 4. Implementation order

1. Finish the source audit and add this Full Plan before implementation.
2. Correct `AdminSettingsService` falsy-value semantics, add DB presence
   metadata, and align the cache runtime reader with the tenant service.
3. Extend node derivation/validation and harden the built-in spec models with
   safe lengths, formats, and bounds; add registry/store regression tests.
4. Add the redacted effective-application configuration read-only panel and
   wire the effective provider config into the mounted registry without
   changing default direct-controller test behavior.
5. Improve settings form rendering and accessibility/source hints, then add
   settings history/rollback route/UI and a durable database snapshot adapter.
   Move snapshot capture so races and failed writes are never recorded.
6. Run targeted tests, the full admin unit suite, Ruff/mypy, inspect the final
   diff, update this plan and the roadmap/index with exact results, commit, and
   push only to `arena/01a05b98-lexigram`. Do not merge PR #26.
7. Defer playground/browser round-trip verification as required by the
   standing session decision; record it as an unchecked follow-up rather than
   claiming it passed.

## 5. Verification matrix

- Registry/spec/node/model tests, including all built-in specs and a custom
  JSON/typed contributor spec.
- Settings service/store tests for `false`, `0`, `""`, default presence,
  tenant isolation, and conditional writes.
- Controller read/save tests for every field family, invalid input, missing
  revision, stale revision, late race, read-only POST, secret preservation,
  permissions, CSRF-compatible form data, history, and rollback.
- Renderer tests for origin/default/read-only/runtime badges, accessible
  error markup, responsive layout classes, action-bar behavior, and redaction.
- Full admin unit suite with `--no-cov`; Ruff on changed files; mypy on touched
  admin modules; `git diff --check`.
- Browser/playground verification: intentionally deferred.

## 6. Security and compatibility notes

No secret is rendered, audited, snapshotted, or included in a revision token
by content. Existing legacy `required_permissions` behavior and custom admin
prefix routing remain supported. Existing stores without new optional methods
continue to work through conservative fallbacks, but the UI labels their
origin as unknown. No YAML/config value is made writable through this panel.

## 7. Completion record

Completed 2026-09-03 on `arena/01a05b98-lexigram`. The audit now has one
source-aware settings pipeline: database-backed editable values preserve
falsy values and tenant ownership, effective application/YAML/environment
configuration is exposed through a redacted read-only adapter, and typed
contributor specs retain model constraints while allowing semantic node
overrides. The settings UI reports source/default/runtime state, preserves
invalid submissions, associates help and errors with controls, hides mutation
controls for read-only panels, and routes saves/rollback through the existing
CSRF, permission, revision, conditional-write, audit, and tenant boundaries.
Successful changes alone create redacted history records; rollback restores
explicit ownership as well as effective values, with a durable SQL snapshot
adapter when the database service is available and a safe in-memory fallback.
HTMX save feedback uses the shared accessible toast channel.

Verification completed:

- [x] Implementation and regression tests complete.
- [x] Focused settings/controller suite: `269 passed, 4 warnings`; shared
  UI form/accessibility suite: `98 passed, 4 warnings`.
- [x] Full admin unit suite: `pytest -q --no-cov tests/unit` — `5881 passed,
  7 skipped, 16 warnings in 35.96s`.
- [x] Targeted mypy over 31 changed production files: passed.
- [x] Admin/shared-UI `compileall`: passed.
- [x] Ruff and `git diff --check`: passed.
- [x] Diff reviewed; commit and push to the fixed branch are recorded in the
  final delivery status.
- [ ] Playground/browser round-trip remains intentionally deferred, per the
  standing session decision.
