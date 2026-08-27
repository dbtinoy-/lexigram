# Admin Settings Page Hardening — Design Spec

**Status:** Reviewed — awaiting user sign-off
**Author:** architecture session, 2026-08-19
**Source:** session research (live verification against `lexigram-admin`'s `controllers/settings.py`, `settings/panel/{registry,nodes,ui,store,layout,types}.py`, `dashboard/{settings_assembler,route_integrator}.py`, `di/bundle_provider.py`, `middleware/tenant.py`, `controllers/base.py`, all 8 `settings/panel/*_spec.py` files, `lexigram-contracts/src/lexigram/contracts/admin/contributor.py`); user-directed scoping decisions collected via one-question-at-a-time clarification; spec-reviewed twice: round 1 found the sidebar/category path was mis-targeted (corrected against `settings/panel/layout.py`/`types.py` and `controllers/settings.py`'s `_build_categories`, not read in the first verification pass) and the tenant_id threading mechanism was underspecified (corrected with a full 5-layer path); round 2 approved with one cosmetic wording fix.
**Scope:** `lexigram-admin` only (`settings/panel/*`, `controllers/settings.py`, `contributors/core.py`, `di/bundle_provider.py`). No `lexigram-contracts` or cross-package changes required — `ConfigSpec`/`ConfigRegistry`/`SettingsPanelDefinition` are already admin-local or already-defined contracts.
**Process:** verify → spec (this document) → plan → execution.

---

## 1. Background

`/admin/settings` is driven by `ConfigRegistry.with_defaults()`, which registers 8 hardcoded `ConfigSpec` subclasses (branding, cache, features, i18n, profiler, rate_limit, rbac, security), each declaring `AbstractConfigNode` fields rendered as an editable form by `ConfigDashboardUI` and persisted through a pluggable `StoreBase`. Verification this session found the page considerably more built-out than initial framing suggested — a real DB-backed store (`TenantConfigStore` over `AdminSettingsService`), RBAC gating with a superadmin bypass, CSRF protection, and best-effort audit logging are all already wired and working (`controllers/settings.py`, `di/bundle_provider.py:279-286`).

What's missing is not "does it work" but four specific gaps the user asked to close for a "100% working, secured and aligned" settings page:

1. **Security**: `readonly` is enforced only by the HTML `disabled` attribute; nothing stops a direct POST from overwriting a readonly field server-side. `SecretNode` values are rendered as `type="password"` but the actual plaintext value is still embedded in the response HTML.
2. **Working**: `EnvStore` (pre-registered in `ConfigRegistry.__init__`) is dead — `SettingsController._store_name()` never selects it, and no spec is sourced from it, so it's registered but unreachable.
3. **Aligned — tenancy**: `TenantConfigStore` hardcodes `tenant_id="default"` (`di/bundle_provider.py:285`); every tenant shares one settings row today with no way to differ.
4. **Aligned — extensibility**: The settings sidebar is driven by a fixed 3-entry category list (`env`/`app`/`system`, `settings/panel/types.py`'s `DEFAULT_CATEGORIES`) but `SettingsController._build_categories()` only ever populates the `"system"` bucket (hardcoded `_SYSTEM_CATEGORY = "system"`) — the `"env"` and `"app"` categories always render empty, and all 8 built-in specs land in `"system"` regardless of what they configure. Separately, `get_settings_panels()` → `SettingsPanelAssembler` → `_register_settings` is fully wired (routes, assembler, its own integration tests) but zero production contributors use it — only `register_spec` is exercised.

## 2. Verified findings (2026-08-19)

### Persistence already works (not a gap)
- `di/bundle_provider.py:256-286`: on admin boot, `AdminSettingsDbProvider`/`AdminSettingsService` are constructed, the `tenant_configs` table is eagerly created, and `TenantConfigStore(admin_settings_service)` is registered into the `ConfigRegistry` under the name `"db"`.
- `SettingsController._store_name()` (`controllers/settings.py:69`) already prefers `"db"` over the in-memory `"default"` fallback whenever it's registered — which it is, in the normal boot path. Settings changes persist across restarts today.

### `readonly` is UI-only
- `ui.py:render_field` (lines 280, 293, 300, 313) sets `disabled=readonly` on `NumberInput`/`Select`/`TextInput`. Browsers correctly exclude `disabled` fields from form submission, so the **normal UI** cannot edit a readonly field.
- `SettingsController.save_spec` (`controllers/settings.py`) builds `updates: dict[str, str]` from submitted form data filtered only to keys present in `spec.get_nodes()` (excluding `_`-prefixed keys) — **no check against `node.readonly`**.
- `ConfigRegistry.save_values` (`registry.py:142-177`) calls `nodes[key].validate(value)` then `store.set(full_key, validated)` for every key in the passed `updates` dict — **also no `readonly` check**. A crafted direct POST (curl, or a devtools-edited form re-enabling the input) reaches `store.set()` unimpeded.

### `SecretNode` leaks plaintext into rendered HTML
- `nodes.py:171-172`: `SecretNode(StringNode)` — no override of `validate()`, no special handling anywhere in `to_dict()`.
- `ui.py:295-301`: the `secret` branch renders `TextInput(name=name, value=value, input_type="password", disabled=readonly)` — `value` is the actual stored secret. `type="password"` only masks the on-screen character display; the real value is still present in the HTTP response body (view-source, HTTP-layer logging, browser extensions, proxy caches all see it in plaintext).
- Audit logging does **not** leak secrets: `_audit()` calls in `controllers/settings.py` pass metadata of `namespace`/`keys`/`invalid` only, never raw values — confirmed no secondary leak path through the audit trail.

### `EnvStore` is dead — unreachable, not just underused
- `registry.py:19-41`: `StoreBase` (permissive no-op `get`/`set`), `EnvStore(StoreBase)` (`get()` converts `"branding.brand_name"` → `os.environ["BRANDING_BRAND_NAME"]`; no `set()` override, so writes silently no-op — correct for an env-backed store, not a bug). `EnvStore` is pre-registered under `"env"` in `ConfigRegistry.__init__`.
- `SettingsController._store_name()` (`controllers/settings.py:67-69`) only ever returns `"db"` or `"default"` — no code path ever requests the `"env"` store by name. `EnvStore` is registered but structurally unreachable.

### The real sidebar/category path — and where it's actually broken
Corrected after spec review: the first pass of this investigation cited `ConfigDashboardUI.render_sidebar`/`render_header`/`render_dashboard` (`ui.py`) as the category-rendering code. **Those methods are never called by any controller** — verified via grep, they're pre-existing dead code, unrelated to the live page (see §6). The actual rendering path is:

- `settings/panel/types.py`: `ConfigCategory` (dataclass: `name`, `label`, `icon`, `order`, `description`, `specs: list`) and `DEFAULT_CATEGORIES` — a fixed 3-tuple (`env`/`app`/`system`, same shape the registry's old `_category_map` mirrors) — plus `get_default_categories()`, which returns a fresh copy of all three every call.
- `controllers/settings.py:36`: `_SYSTEM_CATEGORY = "system"` — a module-level constant.
- `controllers/settings.py:88-105`: `_build_categories(request)` calls `get_default_categories()` (all three categories, `specs` empty), then does `self._registry.get_specs(_SYSTEM_CATEGORY)` — **only ever reads the `"system"` bucket** — permission-filters those specs, and appends them onto whichever category in the list has `cat.name == _SYSTEM_CATEGORY`. The `"env"` and `"app"` `ConfigCategory` entries are always constructed but their `.specs` list is never populated by any code path — they render as permanently empty groups, not because nothing registers under them (the registry-side `_category_map` in the section below is the same shape but is *also* never read for `"env"`/`"app"` by the controller).
- `settings/panel/layout.py`: `ConfigLayout._render_sidebar()` — the component actually rendered by `spec_view`/`index` (`save_spec`'s htmx branch only re-renders the form via `render_config_form`, and its non-htmx branch just redirects to `spec_view`; it never constructs a `ConfigLayout` or calls `_build_categories` itself) — iterates `self.categories` (built by `_build_categories`) sorted by `.order`, rendering one group per category with its `.specs`.
- `registry.py:58-93`: `ConfigRegistry._category_map` (`{"env": [], "app": [], "system": []}`), `register_spec(category, spec)` (appends `spec.namespace` into the matching bucket, no-ops for unrecognized categories), `get_specs(category)` (resolves a bucket's namespaces back to spec classes, filtered to specs with at least one node). All 8 `*_spec.py` files call `registry.register_spec("system", <Spec>)` — verified via grep, no exceptions — which is why `_build_categories`'s hardcoded read of `"system"` happens to surface everything today; the mismatch is latent, not currently visible, because nothing has ever registered under `"env"`/`"app"` to be silently dropped.

### Tenant scoping — single hardcoded tenant
- `settings/store.py:14,28`: `TenantConfigStore.__init__(self, service, tenant_id: str = DEFAULT_TENANT)` where `DEFAULT_TENANT = "default"`.
- `di/bundle_provider.py:285`: `TenantConfigStore(admin_settings_service)` — constructed with no `tenant_id` argument, so every tenant reads/writes the same `"default"` row.
- `resolve_tenant_id(request, default="default")` (from `lexigram.admin.multitenancy.adapter`) is **already used elsewhere** in the admin controller stack (`controllers/base.py:151-153`) — the mechanism for resolving a per-request tenant id already exists and is a proven pattern; it is simply not called from `SettingsController` today. `controllers/widgets.py` hardcodes `tenant_id = "default"` in several places too (pre-existing, unrelated to this spec, not touched here).

### Contributor surface — wired, unused
- `dashboard/settings_assembler.py`: `SettingsPanelAssembler.assemble()` collects `SettingsPanelDefinition`s from `contributor.get_settings_panels()` across all contributors, namespaces them, and permission-filters them.
- `dashboard/route_integrator.py:590-705`: `_register_settings()` registers real routes for each collected panel; `assembler.py:150-156` wires `SettingsPanelAssembler` into the dashboard assembly pipeline; `di/sub_providers/dashboard.py:50-57` constructs and injects it.
- `get_settings_panels()` default (`contracts/admin/contributor.py`, `contracts/admin/protocols.py`) returns empty. Grep across the repo for non-base overrides of `get_settings_panels` found only `dashboard/assembler.py` (the pass-through) and four test files (`test_contributor_collision_modes.py`, `test_contributor_settings_panel_end_to_end.py`, `test_contributor_registry.py`, `test_settings_assembler.py`) — **zero production contributors** (including the built-in `CoreAdminContributor`) implement it.
- `ConfigSpec.package_source` does not exist today; `BaseAdminContributor.package_source: str = "built-in"` (`contracts/admin/contributor.py:41`) is the established analog, consumed by `NamingPolicy.namespaced()` (`dashboard/naming_policy.py:20-22`) elsewhere in the same contributor system.

## 3. Target design

### D1 — Server-side `readonly` enforcement

`ConfigRegistry.save_values` becomes the authoritative enforcement point (single choke point reached by every current and future caller, not just `SettingsController`): before validating/persisting, drop any key from `updates` where `nodes[key].readonly` is `True`. `SettingsController.save_spec` additionally pre-filters readonly keys out of `updates` before calling `save_values`, purely so the existing audit-log call can report an accurate, separate `ignored_readonly: [...]` list alongside the existing `keys`/`invalid` metadata — a readonly-field write attempt is a signal worth having in the audit trail, not just a silently-dropped no-op.

### D2 — `SecretNode` never round-trips its value to the client

- `render_field`'s `secret` branch renders `TextInput(name=name, value="", input_type="password", disabled=readonly)` — never populates `value` with the real secret, regardless of what's currently stored.
- A "(currently set)" / "(not set)" suffix is appended to the field's help text, computed from a boolean (`bool(stored_value)`) that the controller passes down — never the value itself.
- On save, `save_spec` special-cases `SecretNode` keys: a blank submitted value means "leave unchanged" (the key is dropped from `updates` before it reaches `save_values`, exactly like a readonly key); a non-blank value is a real overwrite and proceeds normally. This matches how most credential-editing UIs (AWS console access keys, GitHub PAT rotation) treat secret fields — the true value never returns to the browser after it is first set.

### D3 — Give `EnvStore` a real consumer

- New built-in `DeploymentInfoSpec` (`settings/panel/deployment_spec.py`), all nodes `readonly=True`, sourced from `EnvStore`. Concretely: environment name, log level, and any other env-var-sourced values worth curated, read-only visibility — never an unfiltered dump of `os.environ` (that would risk exposing unrelated secrets sitting in the process environment; each node is an explicit, individually-declared field, same as every other spec).
- `ConfigSpec` gains `store_name: ClassVar[str] = "db"` (default matches the effective behavior of every existing spec today). `DeploymentInfoSpec` sets `store_name = "env"`.
- `SettingsController._store_name()` changes signature to `_store_name(self, spec: type[ConfigSpec]) -> str`, returning `spec.store_name if self._registry.has_store(spec.store_name) else "default"`. For the 8 existing specs (`store_name` left at the `"db"` default), this reduces to exactly today's behavior (`"db"` if registered else `"default"`); for `DeploymentInfoSpec` it resolves to `"env"` (always registered by `ConfigRegistry.__init__`) unless a caller constructs a bare `ConfigRegistry()` without it. Both call sites in `spec_view`/`save_spec` pass `spec` instead of calling `_store_name()` with no arguments.
- This is also the first spec to exercise D1's readonly enforcement against a store that was never reachable before — closes the `EnvStore`-is-dead finding and the "readonly fields from yaml/env" ask in one motion. Under D5 (below), it's grouped in the sidebar like any other spec — no special-cased "env category" is needed once grouping is dynamic.

### D4 — Mixed tenant scoping

- `ConfigSpec` gains `scope: ClassVar[Literal["global", "tenant"]] = "global"` — default preserves current (global) behavior for any spec that doesn't opt in, including `DeploymentInfoSpec` and any future host-registered spec that doesn't explicitly choose tenant scope.
- `branding_spec.py`, `i18n_spec.py`, `features_spec.py` set `scope = "tenant"` (things a tenant should be able to customize for themselves). `cache_spec.py`, `security_spec.py`, `profiler_spec.py`, `rate_limit_spec.py`, `rbac_spec.py` stay `scope = "global"` (operator-only infra/security config no single tenant should be able to override for themselves or others sharing the deployment).
- `SettingsController.spec_view`/`save_spec` call the already-used `resolve_tenant_id(request, default="default")` and pass the result through only when `spec.scope == "tenant"`; global specs pass `None` (see below) so the store falls back to its own default regardless of the requesting tenant.
- **Full threading path (the concrete mechanism, end to end):**
  - `StoreBase.get`/`set` (`registry.py:22-27`) — base signatures gain `tenant_id: str | None = None`, ignored by the base no-op implementation.
  - `EnvStore.get`/`MemoryStore.get`/`MemoryStore.set` — each override adds the same `tenant_id: str | None = None` parameter to its signature (required so calls passing the kwarg don't raise `TypeError`); both continue to ignore it, since neither store is tenant-aware.
  - `TenantConfigStore.get`/`set` (`settings/store.py`) — signatures become `get(self, key, default=None, tenant_id=None)` / `set(self, key, value, tenant_id=None)`, using `tenant_id or self._tenant` (falls back to the constructor's `DEFAULT_TENANT` when `None` is passed, preserving current behavior for any caller that doesn't supply one).
  - `ConfigRegistry.get_values`/`save_values` (`registry.py:142-177`) — both gain a `tenant_id: str | None = None` parameter and pass it through on every `store.get(...)`/`store.set(...)` call.
  - `SettingsController.spec_view`/`save_spec` — compute `tenant_id = await resolve_tenant_id(request, default="default") if spec.scope == "tenant" else None` and pass it into `get_values`/`save_values`.

### D5 — Dynamic per-package categories

The real category machinery is `ConfigRegistry._category_map` (registry-side bucketing) plus `SettingsController._build_categories()` + `ConfigCategory`/`get_default_categories()` (`types.py`, controller-side rendering prep) feeding `ConfigLayout._render_sidebar()` (`layout.py`, the component actually rendered). All three layers currently share the same fixed 3-key assumption and all three need to change together — `ConfigDashboardUI.render_sidebar`/`render_header` are not part of this (confirmed dead code, out of scope, see §6).

- `ConfigSpec.package_source: str = "built-in"` — mirrors `BaseAdminContributor.package_source` exactly (same name, same default, same purpose).
- `ConfigRegistry.register_spec(spec_class)` drops the `category` positional argument entirely. `_category_map` is removed; specs are grouped on read directly from `self._specs` by each spec's `package_source`. Two methods replace the old category API: `get_package_sources() -> list[str]` (sorted, distinct `package_source` values among registered specs that have at least one node) and `get_specs_by_package(package_source: str) -> list[type[ConfigSpec]]` (same node-filtering behavior `get_specs()` has today). The 8 built-in `register_spec()` call sites in `*_spec.py` drop the now-removed `"system"` argument.
- `types.py`: `DEFAULT_CATEGORIES`/`get_default_categories()` (the fixed 3-tuple) are removed — categories are no longer a static list. `ConfigCategory` (the dataclass shape: `name`/`label`/`icon`/`order`/`description`/`specs`) is kept; `name`/`label` are now derived from a `package_source` string at construction time (e.g. `name=package_source`, `label=package_source.replace("-", " ").replace("_", " ").title()`) rather than looked up from a fixed tuple. `order` defaults to a stable value (e.g. alphabetical by `package_source`, `"built-in"` first) since there's no more curated ordering list to draw from.
- `controllers/settings.py`: `_SYSTEM_CATEGORY` constant and its hardcoded read are removed. `_build_categories(request)` becomes: for each `package_source` in `self._registry.get_package_sources()`, build one `ConfigCategory`, permission-filter `get_specs_by_package(package_source)` exactly as today (same `required_permissions`/superadmin-bypass check, unchanged), and only include the category if it has at least one visible spec (avoids rendering permanently-empty groups — an improvement over today's always-present empty `"env"`/`"app"` entries, not a new requirement, but worth calling out since it changes what index()/the sidebar shows for a permission set with zero visible specs in a group).
- Net effect: a host app registering a spec under its own `package_source` automatically gets its own sidebar group with zero registry/controller changes — matching Django's `app_list` grouping, and finally giving `"built-in"` (all 8 existing specs + the new `DeploymentInfoSpec` from D3) its own real, correctly-populated group instead of relying on a hardcoded `"system"` string that happened to line up by coincidence.

### D6 — Prove out `get_settings_panels()` with a real "System Info" panel

- New read-only diagnostics panel on `CoreAdminContributor.get_settings_panels()`: framework version, detected `lexigram-*` extension packages, Python version, process uptime. Deliberately **not** a `ConfigSpec` — there is nothing to edit, no CSRF/readonly concerns, just a rendered page, which is exactly the shape `get_settings_panels()` was built for and `register_spec`'s edit-a-form model was never a good fit for.
- This exercises the assembler → route-registration → permission-filter pipeline in production for the first time (previously only test fixtures did), giving future contributors a working example to copy instead of only test coverage to read.

## 4. Design decisions

| Decision | Resolution | Rationale |
|---|---|---|
| Readonly enforcement location | Authoritative check in `ConfigRegistry.save_values`; `SettingsController.save_spec` pre-filters for audit-metadata accuracy | `save_values` is the single choke point every caller (current and future) goes through; enforcing only in the controller would leave a gap for any other future caller |
| Secret handling | Never re-populate the real value into rendered HTML; blank submission = unchanged, non-blank = overwrite | Verified `type="password"` only masks on-screen display, not the served HTML; matches common credential-editing UX (AWS/GitHub) and avoids ever letting the plaintext leave the server after first set |
| `"env"` category revival | Give it one real, curated, read-only consumer (`DeploymentInfoSpec` via `EnvStore`) rather than deleting the dead code | Directly satisfies the user's "readonly fields from yaml/env" ask and exercises D1's new enforcement against a previously-unreachable store, instead of just removing unused code |
| Tenant scoping | Mixed — per-spec `scope` attribute, `tenant` for branding/i18n/features, `global` for cache/security/profiler/rate_limit/rbac | User's explicit choice: tenant-customizable surface vs. operator-only infra/security config no tenant should override |
| Tenant id threading | Explicit `tenant_id` parameter on `TenantConfigStore.get`/`set`, resolved via already-used `resolve_tenant_id(request, ...)` | Matches this package's existing explicit-threading convention (`request.state`/`resolve_tenant_id`), distinct from core's ContextVar ambient-capabilities pattern reserved for clock/identity/hashing |
| Category taxonomy | Dynamic per-package grouping via `ConfigSpec.package_source`, fixed 3-key enum removed | User's explicit choice (Django `app_list` style); mirrors the already-established `BaseAdminContributor.package_source` convention exactly rather than inventing a new mechanism |
| Contributor surface | Prove out `get_settings_panels()` now with a real "System Info" panel, not just documentation | User's explicit choice; the panel is a genuine content-shape mismatch for `register_spec` (nothing to edit) so it's also the right first real user of that path, not an arbitrary pick |

## 5. Sequencing (for the follow-up plan)

1. **D1 + D2 (security fixes)**: readonly enforcement in `save_values`/`save_spec`, `SecretNode` masking — no dependency on anything else in this spec, ships first and independently testable.
2. **D5 (categories)**: `ConfigSpec.package_source`, `register_spec()` signature change, sidebar grouping update — touches all 8 existing spec files' registration call, so do this before adding any new specs (D3, D4) to avoid updating new files twice.
3. **D4 (tenant scoping)**: `ConfigSpec.scope`, `TenantConfigStore` explicit `tenant_id` param, controller wiring — independent of D3, but do before D3 since `DeploymentInfoSpec` should be written against the final `ConfigSpec` shape (with `scope` already present, defaulting to `global`).
4. **D3 (`DeploymentInfoSpec` + `env` store selection)**: new spec, `_store_name()` readonly-store rule — depends on D1 (its readonly enforcement is what makes this store selection safe) and D5 (needs `package_source` on the new spec).
5. **D6 (System Info panel)**: independent of D1-D5, can be built in parallel; sequenced last only because it's the lowest-risk, most isolated piece (touches `CoreAdminContributor` and the already-wired assembler pipeline, nothing in `ConfigRegistry`/`ConfigSpec`).
6. Gate: full CI (`ruff`, `mypy`, `pytest`) plus a manual check — direct POST against a readonly field confirms no change persists; a `SecretNode` field's rendered HTML confirmed to never contain the real value via response inspection.

## 6. Explicitly out of scope (and why)

| Item | Why deferred |
|---|---|
| New `YamlStore` implementation | Nothing in-repo needs YAML-sourced deployment config today; `EnvStore` already covers the concrete "env" ask, and `StoreBase` remains an open extension point for any host app that wants a YAML-backed store later — building one speculatively would be exactly the "configurability that wasn't requested" CLAUDE.md warns against |
| Fixing `controllers/widgets.py`'s hardcoded `tenant_id = "default"` | Pre-existing, unrelated to the settings page; not touched by this spec |
| Redesigning `AbstractConfigNode`/`validate()`'s coerce-to-default contract | Sound as-is; the security/alignment gaps are specific to readonly enforcement, secret rendering, categories, and tenancy — not to node validation semantics |
| Migrating other contributors (beyond `CoreAdminContributor`) to `get_settings_panels()` | D6 proves the path works with one real example; broader adoption is each package's own future decision, not part of hardening the settings page itself |
| RBAC/permission model changes | D1-D6 all reuse the existing `required_permissions`/superadmin-bypass mechanism unchanged; no new permission model is introduced |
| `ConfigDashboardUI.render_sidebar`/`render_header`/`render_dashboard`/`render_main_content` (`ui.py`) | Confirmed via grep to be pre-existing dead code — no controller calls them; the live sidebar is `ConfigLayout`/`ConfigCategory` (`layout.py`/`types.py`). Left as-is per CLAUDE.md ("notice unrelated dead code, mention it — don't delete it"); not touched by D5 or any other decision in this spec |
