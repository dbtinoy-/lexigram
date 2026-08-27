# Admin Settings Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/admin/settings` secure (server-side readonly enforcement, never-leak secrets), working (a real read-only env/deployment panel), and aligned (per-request tenant scoping where it makes sense, dynamic per-package sidebar categories, and one real contributor proving out the unused `get_settings_panels()` path).

**Architecture:** Six independent design decisions (D1-D6) layered onto the existing spec-driven settings system (`ConfigRegistry` → `ConfigSpec`/nodes → `SettingsController` → `ConfigDashboardUI`/`ConfigLayout`). D1/D2 close security gaps in the existing save/render path. D5 replaces the dead fixed 3-category system with dynamic per-`package_source` grouping (mirrors `BaseAdminContributor.package_source`). D4 threads an explicit `tenant_id` parameter through the store stack, opt-in per spec via `ConfigSpec.scope`. D3 adds a new read-only `DeploymentInfoSpec` sourced from the previously-dead `EnvStore`. D6 adds a "System Info" panel via `CoreAdminContributor.get_settings_panels()`, the first production use of that already-wired-but-unused extension point.

**Tech Stack:** Python 3.11+, `lexigram-admin` (Starlette-based admin controllers), `lexigram-contracts` (already has `SettingsPanelDefinition`/`PageContent`/`ManagementPageHandler` — no contracts changes needed), pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-08-19-admin-settings-hardening-design.md` (approved, two review rounds).

**Sequencing (per spec §5):** D1+D2 (security, no deps) → D5 (categories, touches all 8 spec files so do before adding new ones) → D4 (tenant scoping, before D3 so `DeploymentInfoSpec` is written against the final `ConfigSpec` shape) → D3 (`DeploymentInfoSpec`, depends on D1's readonly enforcement and D5's `package_source`) → D6 (independent, lowest-risk, sequenced last) → final CI + manual verification gate.

---

## File Structure

| File | Change | Design decision |
|---|---|---|
| `lexigram-admin/src/lexigram/admin/settings/panel/registry.py` | Modify: `save_values` readonly skip; `register_spec`/`get_specs` → `get_package_sources`/`get_specs_by_package`; `StoreBase`/`EnvStore`/`MemoryStore` gain `tenant_id` kwarg; `get_values`/`save_values` gain `tenant_id` param; `with_defaults()` registers `DeploymentInfoSpec` | D1, D5, D4, D3 |
| `lexigram-admin/src/lexigram/admin/settings/panel/nodes.py` | Modify: `ConfigSpec` gains `package_source`, `scope`, `store_name` class attrs | D5, D4, D3 |
| `lexigram-admin/src/lexigram/admin/settings/panel/ui.py` | Modify: `render_field`'s `secret` branch never puts the real value in `value=` | D2 |
| `lexigram-admin/src/lexigram/admin/settings/panel/store.py` | Modify: `TenantConfigStore.get`/`set` gain `tenant_id` override param | D4 |
| `lexigram-admin/src/lexigram/admin/settings/panel/types.py` | Modify: remove `DEFAULT_CATEGORIES`/`get_default_categories`, keep `ConfigCategory` | D5 |
| `lexigram-admin/src/lexigram/admin/settings/panel/branding_spec.py`, `features_spec.py`, `i18n_spec.py` | Modify: `register_spec()` drops `"system"` arg; add `scope = "tenant"` | D5, D4 |
| `lexigram-admin/src/lexigram/admin/settings/panel/cache_spec.py`, `security_spec.py`, `profiler_spec.py`, `rate_limit_spec.py`, `rbac_spec.py` | Modify: `register_spec()` drops `"system"` arg only (stay `scope = "global"`, the default) | D5 |
| `lexigram-admin/src/lexigram/admin/settings/panel/deployment_spec.py` | **Create**: new read-only `DeploymentInfoSpec`, `store_name = "env"` | D3 |
| `lexigram-admin/src/lexigram/admin/settings/panel/__init__.py` | Modify: drop `DEFAULT_CATEGORIES`/`get_default_categories` exports; add `DeploymentInfoSpec`/`register_deployment_spec` exports | D5, D3 |
| `lexigram-admin/src/lexigram/admin/controllers/settings.py` | Modify: `_store_name(spec)`, `_build_categories()` rewrite, `index()`/`spec_view()`/`save_spec()` updates, readonly pre-filter + audit metadata, blank-secret-unchanged, tenant_id resolution | D1, D2, D5, D4, D3 |
| `lexigram-admin/src/lexigram/admin/contributors/core.py` | Modify: `get_settings_panels()` + `_SystemInfoPageHandler` | D6 |
| `lexigram-admin/tests/unit/settings/test_specs.py` | Modify: `get_specs("system")` → `get_specs_by_package("built-in")`; add `admin.deployment` to `with_defaults()` expectation | D5, D3 |
| `lexigram-admin/tests/unit/controllers/test_settings_controller.py` | Modify: 5x `register_spec("system", X)` → `register_spec(X)` | D5 |
| `lexigram-admin/tests/unit/settings/test_settings_ui.py` | Modify: strengthen secret-node test to assert the real value never appears | D2 |
| `lexigram-admin/tests/unit/settings/test_deployment_spec.py` | **Create**: new tests for `DeploymentInfoSpec` | D3 |
| `lexigram-admin/tests/unit/contributors/test_core_settings_panel.py` | **Create**: new tests for `CoreAdminContributor.get_settings_panels()` | D6 |

No `lexigram-contracts` changes — `SettingsPanelDefinition`, `PageContent`, `ManagementPageHandler` already exist and are already correctly shaped for D6.

---

## Part 1 — D1: Server-side readonly enforcement

### Task 1: `ConfigRegistry.save_values` skips readonly nodes (authoritative check)

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/registry.py:160-177`
- Test: `lexigram-admin/tests/unit/settings/test_specs.py`

- [ ] **Step 1: Write the failing test**

Add to `TestRegistryEdgeCases` in `test_specs.py`:

```python
    async def test_save_values_skips_readonly_nodes(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _ReadonlySpec(ConfigSpec):
            namespace = "admin.readonly_test"
            label = "Readonly Test"
            icon = "lock"
            description = ""
            locked = StringNode(label="Locked", default="original", readonly=True)

        registry = ConfigRegistry()
        registry.register_spec(_ReadonlySpec)
        await registry.save_values("admin.readonly_test", {"locked": "hacked"})
        values = await registry.get_values("admin.readonly_test")
        assert values["locked"] == "original"
```

Note: this test calls `registry.register_spec(_ReadonlySpec)` with the **new** single-arg signature (Task 5). Since Task 5 hasn't run yet, this test will fail for the wrong reason first. To keep Task 1 self-contained and independently verifiable, write it using the **current** signature instead: `registry.register_spec("system", _ReadonlySpec)`. Task 9 will not need to touch this test since it's added fresh after D5 lands — **so add this test in Task 9 instead, using the post-D5 signature.** For now (Task 1), verify the readonly skip with a direct unit test that doesn't go through `register_spec` at all:

```python
    async def test_save_values_skips_readonly_nodes(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _ReadonlySpec(ConfigSpec):
            namespace = "admin.readonly_test"
            label = "Readonly Test"
            icon = "lock"
            description = ""
            locked = StringNode(label="Locked", default="original", readonly=True)

        registry = ConfigRegistry()
        registry._specs["admin.readonly_test"] = _ReadonlySpec
        await registry.save_values("admin.readonly_test", {"locked": "hacked"})
        values = await registry.get_values("admin.readonly_test")
        assert values["locked"] == "original"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestRegistryEdgeCases::test_save_values_skips_readonly_nodes -v`
Expected: FAIL — `values["locked"] == "hacked"` (readonly not enforced).

- [ ] **Step 3: Implement the minimal fix**

In `registry.py`, change `save_values`'s loop body (currently `if key in nodes:`):

```python
    async def save_values(
        self,
        namespace: str,
        values: dict[str, Any],
        store_name: str = "default",
    ) -> None:
        """Save values for a spec to a store, skipping readonly nodes."""
        spec = self._specs.get(namespace)
        if not spec:
            return

        store = self._stores.get(store_name, self._stores["default"])
        nodes = spec.get_nodes()
        for key, value in values.items():
            if key in nodes and not nodes[key].readonly:
                full_key = f"{namespace}.{key}"
                validated = nodes[key].validate(value)
                await store.set(full_key, validated)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py -v`
Expected: PASS (all tests, including pre-existing ones — this change is additive to the `if`, doesn't affect non-readonly nodes).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/registry.py lexigram-admin/tests/unit/settings/test_specs.py
git commit -m "fix(admin): enforce readonly config nodes server-side in ConfigRegistry.save_values"
```

### Task 2: `SettingsController.save_spec` pre-filters readonly and audits it

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/controllers/settings.py:256-282`
- Test: `lexigram-admin/tests/unit/controllers/test_settings_controller.py`

- [ ] **Step 1: Write the failing test**

Add a new test class:

```python
class TestSaveSpecReadonlyEnforcement:
    """save_spec must never persist a readonly field, even via direct POST."""

    @pytest.mark.asyncio
    async def test_readonly_field_in_post_is_ignored_and_audited(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _ReadonlySpec(ConfigSpec):
            namespace = "admin.readonly_post_test"
            label = "Readonly Post Test"
            icon = "lock"
            description = ""
            locked = StringNode(label="Locked", default="original", readonly=True)

        registry = ConfigRegistry()
        registry._specs["admin.readonly_post_test"] = _ReadonlySpec
        audit = AsyncMock()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, audit_service=audit, registry=registry)

        req = _mock_request(method="POST", form_data={"locked": "hacked"})
        req.path_params = {"namespace": "admin.readonly_post_test"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.readonly_post_test")
        assert values["locked"] == "original"
        _, kwargs = audit.log_event.call_args
        assert kwargs["metadata"]["ignored_readonly"] == ["locked"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestSaveSpecReadonlyEnforcement -v`
Expected: FAIL — `ignored_readonly` key missing from audit metadata (Task 1 alone already stops the persistence half, but the audit metadata assertion fails since `_audit` isn't called with that key yet).

- [ ] **Step 3: Implement**

In `controllers/settings.py`, replace the block from `nodes = spec.get_nodes()` through the `await self._audit(...)` call inside `save_spec`:

```python
        nodes = spec.get_nodes()
        multi = getattr(form, "multi_items", None)
        raw_items = list(multi()) if multi else list(form.items())
        updates = {
            key: (
                "true"
                if isinstance(nodes[key], BooleanNode)
                and any(_value == "on" for _key, _value in raw_items if _key == key)
                else value
            )
            for key, value in raw_items
            if not key.startswith("_") and key in nodes
        }

        ignored_readonly = sorted(key for key in updates if nodes[key].readonly)
        editable_updates = {
            key: value for key, value in updates.items() if not nodes[key].readonly
        }

        invalid = [
            key
            for key, value in editable_updates.items()
            if str(nodes[key].validate(value)).lower() != value.lower()
        ]
        await self._registry.save_values(namespace, editable_updates, self._store_name())

        await self._audit(
            request,
            namespace=namespace,
            keys=sorted(editable_updates),
            invalid=invalid,
            ignored_readonly=ignored_readonly,
        )
```

No other line in `save_spec` references the old `updates` variable (the htmx/redirect branches below only use `invalid`), so this is a self-contained swap.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py -v`
Expected: PASS (full file — this narrows `updates`, doesn't change behavior for non-readonly fields).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/controllers/settings.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "fix(admin): pre-filter readonly fields in save_spec and audit ignored writes"
```

---

## Part 2 — D2: Secrets never leak into rendered HTML

### Task 3: `render_field`'s secret branch stops serving the real value

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/ui.py:295-301`
- Test: `lexigram-admin/tests/unit/settings/test_settings_ui.py`

- [ ] **Step 1: Write the failing test**

Replace `test_secret_node_renders_password_input` in `test_settings_ui.py`:

```python
    def test_secret_node_never_leaks_the_stored_value(self) -> None:
        node = {
            "name": "api_key",
            "label": "API Key",
            "type": "secret",
            "default": "sk-123",
            "help_text": None,
            "readonly": False,
            "options": [],
        }
        html = render_to_string(ConfigDashboardUI().render_field(node, {}))
        assert 'type="password" name="api_key"' in html
        assert "sk-123" not in html
        assert "currently set" in html

    def test_secret_node_shows_not_set_when_no_value(self) -> None:
        node = {
            "name": "api_key",
            "label": "API Key",
            "type": "secret",
            "default": None,
            "help_text": None,
            "readonly": False,
            "options": [],
        }
        html = render_to_string(ConfigDashboardUI().render_field(node, {}))
        assert 'type="password" name="api_key"' in html
        assert "not set" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_settings_ui.py -v`
Expected: FAIL — `"sk-123" not in html` fails, since the current code puts `value="sk-123"` on the `TextInput`.

- [ ] **Step 3: Implement**

In `ui.py`, replace the `elif node_type == "secret":` branch:

```python
        elif node_type == "secret":
            has_value = bool(value)
            presence_note = "(currently set)" if has_value else "(not set)"
            help_text = f"{help_text} {presence_note}" if help_text else presence_note
            input_comp = TextInput(
                name=name,
                value="",
                input_type="password",
                placeholder="••••••••" if has_value else "",
                disabled=readonly,
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_settings_ui.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/ui.py lexigram-admin/tests/unit/settings/test_settings_ui.py
git commit -m "fix(admin): never render the real secret value in settings form HTML"
```

### Task 4: Blank secret submission means "leave unchanged"

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/controllers/settings.py` (imports + `save_spec`)
- Test: `lexigram-admin/tests/unit/controllers/test_settings_controller.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSaveSpecSecretHandling:
    """Blank secret submissions must not overwrite the stored value."""

    @pytest.mark.asyncio
    async def test_blank_secret_submission_leaves_stored_value_unchanged(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode

        class _SecretSpec(ConfigSpec):
            namespace = "admin.secret_test"
            label = "Secret Test"
            icon = "key"
            description = ""
            api_key = SecretNode(label="API Key", default="")

        registry = ConfigRegistry()
        registry._specs["admin.secret_test"] = _SecretSpec
        await registry.save_values("admin.secret_test", {"api_key": "sk-original"})

        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(method="POST", form_data={"api_key": ""})
        req.path_params = {"namespace": "admin.secret_test"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.secret_test")
        assert values["api_key"] == "sk-original"

    @pytest.mark.asyncio
    async def test_non_blank_secret_submission_overwrites(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode

        class _SecretSpec2(ConfigSpec):
            namespace = "admin.secret_test2"
            label = "Secret Test 2"
            icon = "key"
            description = ""
            api_key = SecretNode(label="API Key", default="")

        registry = ConfigRegistry()
        registry._specs["admin.secret_test2"] = _SecretSpec2
        await registry.save_values("admin.secret_test2", {"api_key": "sk-original"})

        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(method="POST", form_data={"api_key": "sk-new"})
        req.path_params = {"namespace": "admin.secret_test2"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.secret_test2")
        assert values["api_key"] == "sk-new"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestSaveSpecSecretHandling -v`
Expected: `test_blank_secret_submission_leaves_stored_value_unchanged` FAILs — blank string currently overwrites the stored secret with `""`.

- [ ] **Step 3: Implement**

Add `SecretNode` to the existing import in `controllers/settings.py`:

```python
from lexigram.admin.settings.panel import BooleanNode, SecretNode
```

Then in `save_spec`, insert a filtering step right after the `updates` dict comprehension (before `ignored_readonly = ...` from Task 2):

```python
        # Blank secret submissions mean "leave unchanged" — never overwrite
        # a stored secret with an empty string.
        updates = {
            key: value
            for key, value in updates.items()
            if value != "" or not isinstance(nodes[key], SecretNode)
        }

        ignored_readonly = sorted(key for key in updates if nodes[key].readonly)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/controllers/settings.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "fix(admin): blank secret form submission no longer clears the stored value"
```

---

## Part 3 — D5: Dynamic per-package sidebar categories

### Task 5: `ConfigRegistry` groups specs by `package_source`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/registry.py:58-93`
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/nodes.py:191-198`
- Test: `lexigram-admin/tests/unit/settings/test_specs.py`

- [ ] **Step 1: Write the failing test**

Add to `test_specs.py` (new test class):

```python
class TestPackageSourceGrouping:
    def test_get_package_sources_returns_distinct_sorted_sources(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _SpecA(ConfigSpec):
            namespace = "test.a"
            label = "A"
            icon = "box"
            description = ""
            package_source = "zeta"
            field = StringNode(label="Field")

        class _SpecB(ConfigSpec):
            namespace = "test.b"
            label = "B"
            icon = "box"
            description = ""
            package_source = "alpha"
            field = StringNode(label="Field")

        registry = ConfigRegistry()
        registry.register_spec(_SpecA)
        registry.register_spec(_SpecB)
        assert registry.get_package_sources() == ["alpha", "zeta"]
        assert registry.get_specs_by_package("alpha") == [_SpecB]

    def test_default_package_source_is_built_in(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec

        assert ConfigSpec.package_source == "built-in"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestPackageSourceGrouping -v`
Expected: FAIL — `register_spec()` still requires a `category` positional arg; `get_package_sources`/`get_specs_by_package` don't exist yet.

- [ ] **Step 3: Implement**

In `nodes.py`, add `package_source` to `ConfigSpec`:

```python
class ConfigSpec(metaclass=ConfigSpecMeta):
    """Base class for grouping configuration nodes."""

    namespace: str = ""
    label: str = ""
    icon: str = "cog"
    description: str = ""
    required_permissions: frozenset[str] = frozenset()
    package_source: str = "built-in"

    _nodes: dict[str, AbstractConfigNode] = {}
```

In `registry.py`, replace `__init__` through `get_specs`:

```python
    def __init__(self) -> None:
        self._specs: dict[str, type[ConfigSpec]] = {}
        self._stores: dict[str, StoreBase] = {
            "env": EnvStore(),
            "default": MemoryStore(),
        }

    def register_store(self, name: str, store: StoreBase) -> None:
        """Register a configuration store."""
        self._stores[name] = store

    def register_spec(self, spec: type[ConfigSpec]) -> None:
        """Register a spec, grouped in the sidebar under its ``package_source``."""
        if spec.namespace in self._specs:
            return
        self._specs[spec.namespace] = spec

    def get_package_sources(self) -> list[str]:
        """Return distinct package sources among specs with editable nodes, sorted."""
        return sorted(
            {spec.package_source for spec in self._specs.values() if spec.get_nodes()}
        )

    def get_specs_by_package(self, package_source: str) -> list[type[ConfigSpec]]:
        """Get all registered specs for a package source that have editable nodes."""
        return [
            spec
            for spec in self._specs.values()
            if spec.package_source == package_source and spec.get_nodes()
        ]
```

This removes `_category_map` entirely and the old `get_specs(category)` method. `with_defaults()` (below `get_specs` in the same file) still calls `register_branding_spec(registry)` etc. — those functions are updated in Task 6, so leave `with_defaults()` untouched in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestPackageSourceGrouping -v`
Expected: PASS. (Other tests in this file, and in `test_settings_controller.py`, will now fail because they still call the old `register_spec("system", X)`/`get_specs("system")` signatures — that's expected here and gets fixed in Task 9. Do not run the full suite yet.)

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/registry.py lexigram-admin/src/lexigram/admin/settings/panel/nodes.py lexigram-admin/tests/unit/settings/test_specs.py
git commit -m "feat(admin): group config specs by package_source instead of fixed category"
```

### Task 6: Update the 8 built-in spec files' `register_spec()` calls

**Files:**
- Modify: `branding_spec.py:26`, `cache_spec.py:25`, `features_spec.py:25`, `i18n_spec.py:25`, `profiler_spec.py:25`, `rate_limit_spec.py:25`, `rbac_spec.py:25`, `security_spec.py:25` (all in `lexigram-admin/src/lexigram/admin/settings/panel/`)

- [ ] **Step 1: Write the failing test**

Already covered by Task 5's `test_default_package_source_is_built_in` plus the pre-existing `test_branding_spec_nodes` etc. — no new test needed; the existing `TestSpecs` tests in `test_specs.py` that call `register_branding_spec(registry)` etc. will fail at this call site once we try running them (they currently pass because `register_spec` still accepts `(category, spec)`, but after Task 5 the 1-arg signature is required). Run the check first:

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestSpecs::test_register_spec_deduplicates -v`
Expected: FAIL — `TypeError: register_spec() takes 2 positional arguments but 3 were given`.

- [ ] **Step 2: Fix each file — this single edit pattern applies to all 8 files**

For each of the 8 files, change the one-line `register_spec()` function body. Example for `branding_spec.py:24-26`:

```python
def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(BrandingSpec)
```

Apply the same pattern (drop `"system", `) to:
- `cache_spec.py`: `registry.register_spec(CacheSpec)`
- `features_spec.py`: `registry.register_spec(FeaturesSpec)`
- `i18n_spec.py`: `registry.register_spec(I18nSpec)`
- `profiler_spec.py`: `registry.register_spec(ProfilerSpec)`
- `rate_limit_spec.py`: `registry.register_spec(RateLimitSpec)`
- `rbac_spec.py`: `registry.register_spec(RBACSpec)`
- `security_spec.py`: `registry.register_spec(SecuritySpec)`

- [ ] **Step 3: Run the same test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestSpecs -v`
Expected: still some failures remain (`get_specs("system")` calls) — those are fixed in Task 9. `test_register_spec_deduplicates` itself still fails on its `get_specs("system")` assertion line, not the `register_spec` call — confirm the `TypeError` from Step 1 is gone (check the failure message changed from `TypeError` to an `AttributeError`/assertion about `get_specs`).

- [ ] **Step 4: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/branding_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/cache_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/features_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/i18n_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/profiler_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/rate_limit_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/rbac_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/security_spec.py
git commit -m "refactor(admin): drop the category argument from built-in spec registration"
```

### Task 7: Remove `DEFAULT_CATEGORIES`/`get_default_categories`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/types.py`
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/__init__.py`

- [ ] **Step 1: Write the failing test**

No new behavior to test here (pure removal) — the existing `layout.py`/`ConfigCategory` tests (if any) must keep passing. Skip straight to implementation; verification is "nothing imports the removed names" (Step 3).

- [ ] **Step 2: Implement — types.py**

Replace the whole file:

```python
"""Type definitions for Configuration Center."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field

__all__ = [
    "ConfigCategory",
]


@dataclass(init=False)
class ConfigCategory(DomainModel):
    """A grouping of configuration specs.

    Categories organize related configuration specs into logical groups
    displayed in the Configuration Center sidebar. One category is built
    per distinct ``ConfigSpec.package_source`` registered with the
    ``ConfigRegistry`` — see ``SettingsController._build_categories``.

    Attributes:
        name: Internal identifier — the spec's package_source.
        label: Display label shown in the sidebar.
        icon: Icon identifier for the category header.
        order: Sort order for display (lower = higher priority).
        description: Optional description shown in the UI.
    """

    name: str
    label: str
    icon: str = Field(default="folder")
    order: int = Field(default=100)
    description: str = Field(default="")

    # Populated dynamically from registry
    specs: list = Field(default_factory=list)
```

- [ ] **Step 3: Implement — `__init__.py`**

Change the types import block:

```python
from lexigram.admin.settings.panel.types import ConfigCategory
```

(was importing `DEFAULT_CATEGORIES, ConfigCategory, get_default_categories`)

Remove these two lines from `__all__`:
```python
    "DEFAULT_CATEGORIES",
```
and
```python
    "get_default_categories",
```

- [ ] **Step 4: Verify nothing else imports the removed names**

Run: `cd lexigram-admin && grep -rn "DEFAULT_CATEGORIES\|get_default_categories" src/ tests/`
Expected: no matches (Task 8 will remove `controllers/settings.py`'s usage next — if this grep still shows matches there, that's expected until Task 8 lands; re-run after Task 8).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/types.py lexigram-admin/src/lexigram/admin/settings/panel/__init__.py
git commit -m "refactor(admin): remove the fixed 3-category settings taxonomy"
```

### Task 8: `SettingsController` builds categories dynamically

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/controllers/settings.py:21,36,88-105,144-169,206-208`

- [ ] **Step 1: Write the failing test**

Add to `test_settings_controller.py`:

```python
class TestDynamicCategories:
    @pytest.mark.asyncio
    async def test_categories_are_grouped_by_package_source(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request()
        categories, visible = controller._build_categories(req)
        assert len(categories) == 1
        assert categories[0].name == "built-in"
        assert len(visible) == 8
```

(`renderer` fixture may not exist at module scope in this file — if not, use `MagicMock()` inline instead of a fixture parameter.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestDynamicCategories -v`
Expected: FAIL — `_build_categories` still calls the removed `self._registry.get_specs(_SYSTEM_CATEGORY)`.

- [ ] **Step 3: Implement**

Change the import line (was `from lexigram.admin.settings.panel.types import ConfigCategory, get_default_categories`):

```python
from lexigram.admin.settings.panel.types import ConfigCategory
```

Remove the module constant:
```python
_SYSTEM_CATEGORY = "system"
```

Replace `_build_categories`:

```python
    def _build_categories(
        self, request: Request
    ) -> tuple[list[ConfigCategory], list[Any]]:
        """Build one category per package source, with visible specs for the user."""
        permissions = self._user_permissions(request)
        is_superadmin = self._user_is_superadmin(request)

        def _is_visible(spec: Any) -> bool:
            return (
                not spec.required_permissions
                or is_superadmin
                or permissions.issuperset(spec.required_permissions)
            )

        categories: list[ConfigCategory] = []
        visible: list[Any] = []
        for order, package_source in enumerate(self._registry.get_package_sources()):
            specs = [
                spec
                for spec in self._registry.get_specs_by_package(package_source)
                if _is_visible(spec)
            ]
            visible.extend(specs)
            categories.append(
                ConfigCategory(
                    name=package_source,
                    label=package_source.replace("-", " ").replace("_", " ").title(),
                    order=order * 10,
                    specs=specs,
                )
            )
        return categories, visible
```

Replace `index()`:

```python
    @get("/")
    async def index(self, request: Request) -> Response:
        """Redirect to the first editable spec, or render an empty state."""
        categories, visible = self._build_categories(request)
        if visible:
            return RedirectResponse(
                url=f"/admin/settings/{visible[0].namespace}",
                status_code=302,
            )

        layout = ConfigLayout(
            categories=categories,
            active_category=None,
            active_namespace=None,
            content=None,
            title="Settings",
        )
        return await self.render_admin(
            request,
            layout,
            title="Settings",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Settings",
            ),
        )
```

In `spec_view()`, change:
```python
            active_category=_SYSTEM_CATEGORY,
```
to:
```python
            active_category=spec.package_source,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestDynamicCategories -v`
Expected: PASS. (Full-suite run happens in Task 9 after fixing the remaining old-signature call sites.)

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/controllers/settings.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "feat(admin): render settings sidebar categories dynamically by package_source"
```

### Task 9: Fix remaining tests still on the old category API

**Files:**
- Modify: `lexigram-admin/tests/unit/settings/test_specs.py`
- Modify: `lexigram-admin/tests/unit/controllers/test_settings_controller.py`

- [ ] **Step 1: Update `test_specs.py`**

Change these three `get_specs("system")` call sites to `get_specs_by_package("built-in")`:

```python
    def test_register_spec_deduplicates(self) -> None:
        registry = ConfigRegistry()
        register_cache_spec(registry)
        register_cache_spec(registry)
        assert len(registry.get_specs_by_package("built-in")) == 1

    def test_get_specs_filters_specs_without_nodes(self) -> None:
        registry = ConfigRegistry()
        register_branding_spec(registry)
        register_cache_spec(registry)
        register_security_spec(registry)
        namespaces = [s.namespace for s in registry.get_specs_by_package("built-in")]
        assert namespaces == ["admin.branding", "admin.cache", "admin.security"]

    def test_with_defaults_registers_all_bound_specs(self) -> None:
        registry = ConfigRegistry.with_defaults()
        namespaces = {s.namespace for s in registry.get_specs_by_package("built-in")}
        assert namespaces == {
            "admin.branding",
            "admin.cache",
            "admin.security",
            "admin.features",
            "admin.i18n",
            "admin.profiler",
            "admin.rate_limit",
            "admin.rbac",
        }
        assert registry.get_spec("admin.cache") is CacheSpec
        assert registry.get_spec("admin.nope") is None
```

And in `TestRegistryEdgeCases`:

```python
    def test_get_specs_empty_registry(self) -> None:
        registry = ConfigRegistry()
        assert registry.get_specs_by_package("built-in") == []
```

Note: `test_with_defaults_registers_all_bound_specs` will need `"admin.deployment"` added to the expected set once Task 16 (D3) wires `DeploymentInfoSpec` into `with_defaults()` — leave it as above for now; Task 16 updates it again.

- [ ] **Step 2: Update `test_settings_controller.py`**

Change these 5 call sites from `registry.register_spec("system", X)` to `registry.register_spec(X)`:
- `test_index_superadmin_sees_gated_specs_without_permissions`: `registry.register_spec(GatedSpec2)`
- `test_save_spec_superadmin_bypasses_permission_gate`: `registry.register_spec(GatedSpec3)`
- `test_save_spec_permission_denied`: `registry.register_spec(GatedSpec)`
- `TestSettingsSpecViewPermissionGate._make_controller`: `registry.register_spec(GatedSpec)`
- `test_spec_view_ungated_spec_renders_without_permissions`: `registry.register_spec(UngatedSpec)`

- [ ] **Step 3: Run the full settings test surface**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/ tests/unit/controllers/test_settings_controller.py tests/unit/di/test_bundle_provider_settings.py -v`
Expected: PASS (all).

- [ ] **Step 4: Commit**

```bash
git add lexigram-admin/tests/unit/settings/test_specs.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "test(admin): update settings tests for package_source-based category API"
```

---

## Part 4 — D4: Mixed tenant scoping

### Task 10: `StoreBase`/`EnvStore`/`MemoryStore` accept a `tenant_id` kwarg

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/registry.py:19-55`
- Test: `lexigram-admin/tests/unit/settings/test_specs.py`

- [ ] **Step 1: Write the failing test**

```python
class TestStoreTenantIdParameter:
    async def test_memory_store_accepts_tenant_id_kwarg(self) -> None:
        store = MemoryStore()
        await store.set("k", "v", tenant_id="tenant-a")
        assert await store.get("k", tenant_id="tenant-a") == "v"

    async def test_env_store_accepts_and_ignores_tenant_id_kwarg(self, monkeypatch) -> None:
        from lexigram.admin.settings.panel.registry import EnvStore

        monkeypatch.setenv("FOO_BAR", "baz")
        store = EnvStore()
        assert await store.get("foo.bar", tenant_id="tenant-a") == "baz"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestStoreTenantIdParameter -v`
Expected: FAIL — `TypeError: get() got an unexpected keyword argument 'tenant_id'`.

- [ ] **Step 3: Implement**

```python
class StoreBase:
    """Interface for configuration persistence."""

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value by key."""
        return default

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value by key."""


class EnvStore(StoreBase):
    """Read-only store for environment variables."""

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Read a value from environment variables.

        Converts internal dot-notation keys (e.g. ``app.db.url``) to
        ``SCREAMING_SNAKE_CASE`` environment variable names.
        """
        env_key = key.upper().replace(".", "_")
        return os.environ.get(env_key, default)


class MemoryStore(StoreBase):
    """In-memory store for testing."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value from the in-memory store."""
        return self._data.get(key, default)

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value to the in-memory store."""
        self._data[key] = value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/registry.py lexigram-admin/tests/unit/settings/test_specs.py
git commit -m "feat(admin): add tenant_id parameter to config store interface"
```

### Task 11: `TenantConfigStore` honors an explicit `tenant_id` override

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/store.py:33-40`
- Test: `lexigram-admin/tests/unit/di/test_bundle_provider_settings.py` (verify unaffected) + new test in same file or a settings-focused test file

- [ ] **Step 1: Write the failing test**

Add to `lexigram-admin/tests/unit/di/test_bundle_provider_settings.py` (or create `lexigram-admin/tests/unit/settings/test_tenant_config_store.py` if that file doesn't already cover this — check first with `ls lexigram-admin/tests/unit/settings/`):

```python
class TestTenantConfigStoreOverride:
    async def test_explicit_tenant_id_overrides_constructor_default(self) -> None:
        from unittest.mock import AsyncMock

        from lexigram.admin.settings.store import TenantConfigStore

        service = AsyncMock()
        service.get.return_value = "value-for-b"
        store = TenantConfigStore(service, tenant_id="tenant-a")

        await store.get("k", tenant_id="tenant-b")
        service.get.assert_awaited_once_with("tenant-b", "k")

    async def test_no_tenant_id_falls_back_to_constructor_default(self) -> None:
        from unittest.mock import AsyncMock

        from lexigram.admin.settings.store import TenantConfigStore

        service = AsyncMock()
        service.get.return_value = "value"
        store = TenantConfigStore(service, tenant_id="tenant-a")

        await store.get("k")
        service.get.assert_awaited_once_with("tenant-a", "k")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/di/test_bundle_provider_settings.py::TestTenantConfigStoreOverride -v`
Expected: FAIL — `TypeError: get() got an unexpected keyword argument 'tenant_id'`.

- [ ] **Step 3: Implement**

```python
    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        """Retrieve a value by key, falling back to *default* when unset."""
        value = await self._service.get(tenant_id or self._tenant, key)
        return value if value is not None else default

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        """Persist a value by key."""
        await self._service.set(tenant_id or self._tenant, key, value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/di/test_bundle_provider_settings.py -v`
Expected: PASS (full file — constructor-only tests like `test_build_store_round_trip` are unaffected since the constructor signature didn't change).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/store.py lexigram-admin/tests/unit/di/test_bundle_provider_settings.py
git commit -m "feat(admin): let TenantConfigStore.get/set accept a per-call tenant_id override"
```

### Task 12: `ConfigRegistry.get_values`/`save_values` thread `tenant_id` through

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/registry.py:142-177` (post-Task-1 state)
- Test: `lexigram-admin/tests/unit/settings/test_specs.py`

- [ ] **Step 1: Write the failing test**

```python
class TestRegistryTenantThreading:
    async def test_get_values_passes_tenant_id_to_store(self) -> None:
        from unittest.mock import AsyncMock

        registry = ConfigRegistry()
        register_cache_spec(registry)
        store = AsyncMock()
        store.get.return_value = None
        registry.register_store("test", store)

        await registry.get_values("admin.cache", store_name="test", tenant_id="tenant-a")
        for call in store.get.await_args_list:
            assert call.kwargs.get("tenant_id") == "tenant-a"

    async def test_save_values_passes_tenant_id_to_store(self) -> None:
        from unittest.mock import AsyncMock

        registry = ConfigRegistry()
        register_cache_spec(registry)
        store = AsyncMock()
        registry.register_store("test", store)

        await registry.save_values(
            "admin.cache", {"enabled": "true"}, store_name="test", tenant_id="tenant-a"
        )
        store.set.assert_awaited_once()
        assert store.set.await_args.kwargs.get("tenant_id") == "tenant-a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestRegistryTenantThreading -v`
Expected: FAIL — `TypeError: get_values() got an unexpected keyword argument 'tenant_id'`.

- [ ] **Step 3: Implement**

```python
    async def get_values(
        self,
        namespace: str,
        store_name: str = "default",
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Load current values for a spec from a store."""
        spec = self._specs.get(namespace)
        if not spec:
            return {}

        store = self._stores.get(store_name, self._stores["default"])
        values = {}
        for key, node in spec.get_nodes().items():
            full_key = f"{namespace}.{key}"
            raw_val = await store.get(full_key, node.default, tenant_id=tenant_id)
            values[key] = node.validate(raw_val)
        return values

    async def save_values(
        self,
        namespace: str,
        values: dict[str, Any],
        store_name: str = "default",
        tenant_id: str | None = None,
    ) -> None:
        """Save values for a spec to a store, skipping readonly nodes."""
        spec = self._specs.get(namespace)
        if not spec:
            return

        store = self._stores.get(store_name, self._stores["default"])
        nodes = spec.get_nodes()
        for key, value in values.items():
            if key in nodes and not nodes[key].readonly:
                full_key = f"{namespace}.{key}"
                validated = nodes[key].validate(value)
                await store.set(full_key, validated, tenant_id=tenant_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/registry.py lexigram-admin/tests/unit/settings/test_specs.py
git commit -m "feat(admin): thread tenant_id through ConfigRegistry.get_values/save_values"
```

### Task 13: `ConfigSpec.scope` — mixed tenant/global per built-in spec

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/nodes.py:191-199`
- Modify: `branding_spec.py`, `i18n_spec.py`, `features_spec.py` (add `scope = "tenant"`)
- Test: `lexigram-admin/tests/unit/settings/test_specs.py`

- [ ] **Step 1: Write the failing test**

```python
class TestSpecScope:
    def test_default_scope_is_global(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec

        assert ConfigSpec.scope == "global"

    def test_tenant_customizable_specs_are_scoped_to_tenant(self) -> None:
        from lexigram.admin.settings.panel import BrandingSpec, FeaturesSpec, I18nSpec

        assert BrandingSpec.scope == "tenant"
        assert FeaturesSpec.scope == "tenant"
        assert I18nSpec.scope == "tenant"

    def test_operator_only_specs_stay_global(self) -> None:
        from lexigram.admin.settings.panel import (
            CacheSpec,
            ProfilerSpec,
            RateLimitSpec,
            RBACSpec,
            SecuritySpec,
        )

        for spec in (CacheSpec, SecuritySpec, ProfilerSpec, RateLimitSpec, RBACSpec):
            assert spec.scope == "global"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py::TestSpecScope -v`
Expected: FAIL — `AttributeError: type object 'ConfigSpec' has no attribute 'scope'`.

- [ ] **Step 3: Implement**

In `nodes.py`:

```python
class ConfigSpec(metaclass=ConfigSpecMeta):
    """Base class for grouping configuration nodes."""

    namespace: str = ""
    label: str = ""
    icon: str = "cog"
    description: str = ""
    required_permissions: frozenset[str] = frozenset()
    package_source: str = "built-in"
    scope: Literal["global", "tenant"] = "global"

    _nodes: dict[str, AbstractConfigNode] = {}
```

In `branding_spec.py`, add `scope = "tenant"` inside `BrandingSpec` (after `required_permissions`):
```python
    required_permissions = frozenset({"admin.settings.edit"})
    scope = "tenant"
```

Apply the identical one-line addition to `I18nSpec` in `i18n_spec.py` and `FeaturesSpec` in `features_spec.py`. `cache_spec.py`, `security_spec.py`, `profiler_spec.py`, `rate_limit_spec.py`, `rbac_spec.py` are **not** touched — they inherit the default `scope = "global"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_specs.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/nodes.py \
        lexigram-admin/src/lexigram/admin/settings/panel/branding_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/i18n_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/features_spec.py \
        lexigram-admin/tests/unit/settings/test_specs.py
git commit -m "feat(admin): mark branding/i18n/features specs as tenant-scoped"
```

### Task 14: `SettingsController` resolves `tenant_id` for tenant-scoped specs

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/controllers/settings.py` (imports, `spec_view`, `save_spec`)
- Test: `lexigram-admin/tests/unit/controllers/test_settings_controller.py`

- [ ] **Step 1: Write the failing test**

```python
class TestTenantScopedSettings:
    @pytest.mark.asyncio
    async def test_tenant_scoped_spec_resolves_tenant_id(
        self, monkeypatch
    ) -> None:
        from lexigram.admin.settings.panel import BrandingSpec

        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)

        async def _fake_resolve(request, *, default):
            return "tenant-42"

        monkeypatch.setattr(
            "lexigram.admin.controllers.settings.resolve_tenant_id", _fake_resolve
        )

        called_with = {}
        original_get_values = registry.get_values

        async def _spy_get_values(namespace, store_name="default", tenant_id=None):
            called_with["tenant_id"] = tenant_id
            return await original_get_values(namespace, store_name, tenant_id=tenant_id)

        registry.get_values = _spy_get_values

        req = _mock_request()
        req.path_params = {"namespace": "admin.branding"}
        await controller.spec_view(req)

        assert called_with["tenant_id"] == "tenant-42"
        assert BrandingSpec.scope == "tenant"

    @pytest.mark.asyncio
    async def test_global_scoped_spec_passes_no_tenant_id(self, monkeypatch) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)

        async def _fail_resolve(request, *, default):
            raise AssertionError("resolve_tenant_id should not be called for global specs")

        monkeypatch.setattr(
            "lexigram.admin.controllers.settings.resolve_tenant_id", _fail_resolve
        )

        req = _mock_request()
        req.path_params = {"namespace": "admin.cache"}
        await controller.spec_view(req)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestTenantScopedSettings -v`
Expected: FAIL — `spec_view` doesn't call `resolve_tenant_id` at all yet, so the monkeypatched spy never records a value, and `called_with` stays empty (`KeyError`).

- [ ] **Step 3: Implement**

Add the import (with the other top-level imports):

```python
from lexigram.admin.multitenancy.adapter import resolve_tenant_id
```

In `spec_view()`, change:

```python
        categories, _ = self._build_categories(request)
        values = await self._registry.get_values(namespace, self._store_name())
```

to:

```python
        categories, _ = self._build_categories(request)
        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
        values = await self._registry.get_values(
            namespace, self._store_name(), tenant_id=tenant_id
        )
```

In `save_spec()`, change the block ending in the `_audit` call (post-Task-2/4 state) so the `save_values` call and the `_audit` call site both get a `tenant_id`:

```python
        invalid = [
            key
            for key, value in editable_updates.items()
            if str(nodes[key].validate(value)).lower() != value.lower()
        ]
        tenant_id = (
            await resolve_tenant_id(request, default="default")
            if spec.scope == "tenant"
            else None
        )
        await self._registry.save_values(
            namespace, editable_updates, self._store_name(), tenant_id=tenant_id
        )

        await self._audit(
            request,
            namespace=namespace,
            keys=sorted(editable_updates),
            invalid=invalid,
            ignored_readonly=ignored_readonly,
        )
```

And further down in the same method, the htmx re-render branch's `get_values` call:

```python
            values = await self._registry.get_values(
                namespace, self._store_name(), tenant_id=tenant_id
            )
```

(was `values = await self._registry.get_values(namespace, self._store_name())`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py -v`
Expected: PASS (full file).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/controllers/settings.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "feat(admin): resolve per-request tenant_id for tenant-scoped settings specs"
```

---

## Part 5 — D3: Real `EnvStore` consumer (`DeploymentInfoSpec`)

### Task 15: `SettingsController._store_name` becomes spec-aware

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/nodes.py:191-200`
- Modify: `lexigram-admin/src/lexigram/admin/controllers/settings.py:67-69` + 3 call sites
- Test: `lexigram-admin/tests/unit/controllers/test_settings_controller.py`

- [ ] **Step 1: Write the failing test**

```python
class TestStoreNameResolution:
    def test_store_name_defaults_to_db_when_registered(self) -> None:
        from lexigram.admin.settings.panel.registry import MemoryStore

        registry = ConfigRegistry.with_defaults()
        registry.register_store("db", MemoryStore())
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)

        from lexigram.admin.settings.panel import CacheSpec

        assert controller._store_name(CacheSpec) == "db"

    def test_store_name_falls_back_to_default_when_spec_store_unregistered(self) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)

        from lexigram.admin.settings.panel import CacheSpec

        assert controller._store_name(CacheSpec) == "default"

    def test_env_scoped_spec_resolves_to_env_store(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec

        class _EnvSpec(ConfigSpec):
            namespace = "test.env_spec"
            label = "Env Spec"
            icon = "server"
            description = ""
            store_name = "env"

        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)
        assert controller._store_name(_EnvSpec) == "env"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py::TestStoreNameResolution -v`
Expected: FAIL — `TypeError: _store_name() missing 1 required positional argument: 'spec'` and `AttributeError: type object 'ConfigSpec' has no attribute 'store_name'`.

- [ ] **Step 3: Implement**

In `nodes.py`, add `store_name` to `ConfigSpec` (after `scope`):

```python
class ConfigSpec(metaclass=ConfigSpecMeta):
    """Base class for grouping configuration nodes."""

    namespace: str = ""
    label: str = ""
    icon: str = "cog"
    description: str = ""
    required_permissions: frozenset[str] = frozenset()
    package_source: str = "built-in"
    scope: Literal["global", "tenant"] = "global"
    store_name: str = "db"

    _nodes: dict[str, AbstractConfigNode] = {}
```

In `controllers/settings.py`, replace `_store_name`:

```python
    def _store_name(self, spec: type[Any]) -> str:
        """Use the spec's configured store when registered, else the in-memory default."""
        return spec.store_name if self._registry.has_store(spec.store_name) else "default"
```

Update the 3 call sites (all currently `self._store_name()`) to `self._store_name(spec)`:
1. `spec_view()`: `values = await self._registry.get_values(namespace, self._store_name(spec), tenant_id=tenant_id)`
2. `save_spec()`: `await self._registry.save_values(namespace, editable_updates, self._store_name(spec), tenant_id=tenant_id)`
3. `save_spec()` htmx branch: `values = await self._registry.get_values(namespace, self._store_name(spec), tenant_id=tenant_id)`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/controllers/test_settings_controller.py -v`
Expected: PASS (full file — `"db"` is still the default `store_name`, so every existing spec/test that relied on the old hardcoded `"db"`-or-`"default"` behavior sees identical results).

- [ ] **Step 5: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/nodes.py lexigram-admin/src/lexigram/admin/controllers/settings.py lexigram-admin/tests/unit/controllers/test_settings_controller.py
git commit -m "feat(admin): let each ConfigSpec choose its own store, not just db-or-default"
```

### Task 16: `DeploymentInfoSpec` — real, curated, read-only `EnvStore` consumer

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/settings/panel/deployment_spec.py`
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/registry.py` (`with_defaults`)
- Modify: `lexigram-admin/src/lexigram/admin/settings/panel/__init__.py` (exports)
- Modify: `lexigram-admin/tests/unit/settings/test_specs.py` (`with_defaults` expectation)
- Test: `lexigram-admin/tests/unit/settings/test_deployment_spec.py`

- [ ] **Step 1: Write the failing test**

Create `lexigram-admin/tests/unit/settings/test_deployment_spec.py`:

```python
"""Tests for the built-in DeploymentInfoSpec (read-only env-sourced settings)."""

from __future__ import annotations

import pytest

from lexigram.admin.settings.panel.deployment_spec import (
    DeploymentInfoSpec,
    register_spec,
)
from lexigram.admin.settings.panel.registry import ConfigRegistry


class TestDeploymentInfoSpec:
    def test_nodes_are_readonly(self) -> None:
        nodes = DeploymentInfoSpec.get_nodes()
        assert set(nodes) == {"environment", "log_level"}
        assert all(node.readonly for node in nodes.values())

    def test_scope_is_global(self) -> None:
        assert DeploymentInfoSpec.scope == "global"

    def test_store_name_is_env(self) -> None:
        assert DeploymentInfoSpec.store_name == "env"

    @pytest.mark.asyncio
    async def test_values_reflect_env_var_overrides(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ADMIN_DEPLOYMENT_ENVIRONMENT", "staging")
        registry = ConfigRegistry()
        register_spec(registry)

        values = await registry.get_values("admin.deployment", store_name="env")
        assert values["environment"] == "staging"

    @pytest.mark.asyncio
    async def test_readonly_save_is_ignored(self) -> None:
        registry = ConfigRegistry()
        register_spec(registry)

        await registry.save_values(
            "admin.deployment", {"environment": "hacked"}, store_name="env"
        )
        values = await registry.get_values("admin.deployment", store_name="env")
        assert values["environment"] != "hacked"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/test_deployment_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lexigram.admin.settings.panel.deployment_spec'`.

- [ ] **Step 3: Implement**

Create `lexigram-admin/src/lexigram/admin/settings/panel/deployment_spec.py`:

```python
"""Deployment info configuration specification — read-only, env-sourced."""

from __future__ import annotations

import os

from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["DeploymentInfoSpec", "register_spec"]


class DeploymentInfoSpec(ConfigSpec):
    """Read-only deployment info sourced from environment variables."""

    namespace = "admin.deployment"
    label = "Deployment Info"
    icon = "server"
    description = "Read-only environment and runtime configuration."
    store_name = "env"

    environment = StringNode(
        label="Environment",
        default=os.environ.get("ENVIRONMENT", "unknown"),
        readonly=True,
        help_text="Deployment environment name.",
    )
    log_level = StringNode(
        label="Log Level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        readonly=True,
        help_text="Configured application log level.",
    )


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(DeploymentInfoSpec)
```

In `registry.py`, update `with_defaults()`:

```python
    @classmethod
    def with_defaults(cls) -> ConfigRegistry:
        """Build a registry pre-populated with all built-in bound specs."""
        registry = cls()
        from lexigram.admin.settings.panel import (
            register_branding_spec,
            register_cache_spec,
            register_deployment_spec,
            register_features_spec,
            register_i18n_spec,
            register_profiler_spec,
            register_rate_limit_spec,
            register_rbac_spec,
            register_security_spec,
        )

        register_branding_spec(registry)
        register_cache_spec(registry)
        register_security_spec(registry)
        register_features_spec(registry)
        register_i18n_spec(registry)
        register_profiler_spec(registry)
        register_rate_limit_spec(registry)
        register_rbac_spec(registry)
        register_deployment_spec(registry)
        return registry
```

In `__init__.py`, add the import block (alongside the other spec imports, alphabetically after `cache_spec`):

```python
from lexigram.admin.settings.panel.deployment_spec import DeploymentInfoSpec
from lexigram.admin.settings.panel.deployment_spec import (
    register_spec as register_deployment_spec,
)
```

And add to `__all__` (alphabetically):
```python
    "DeploymentInfoSpec",
```
```python
    "register_deployment_spec",
```

- [ ] **Step 4: Update `test_with_defaults_registers_all_bound_specs`**

In `test_specs.py`, add `"admin.deployment"` to the expected namespace set:

```python
    def test_with_defaults_registers_all_bound_specs(self) -> None:
        registry = ConfigRegistry.with_defaults()
        namespaces = {s.namespace for s in registry.get_specs_by_package("built-in")}
        assert namespaces == {
            "admin.branding",
            "admin.cache",
            "admin.security",
            "admin.features",
            "admin.i18n",
            "admin.profiler",
            "admin.rate_limit",
            "admin.rbac",
            "admin.deployment",
        }
        assert registry.get_spec("admin.cache") is CacheSpec
        assert registry.get_spec("admin.nope") is None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd lexigram-admin && uv run pytest tests/unit/settings/ -v`
Expected: PASS (all files in `tests/unit/settings/`).

- [ ] **Step 6: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/settings/panel/deployment_spec.py \
        lexigram-admin/src/lexigram/admin/settings/panel/registry.py \
        lexigram-admin/src/lexigram/admin/settings/panel/__init__.py \
        lexigram-admin/tests/unit/settings/test_specs.py \
        lexigram-admin/tests/unit/settings/test_deployment_spec.py
git commit -m "feat(admin): add read-only DeploymentInfoSpec sourced from EnvStore"
```

---

## Part 6 — D6: System Info panel proves out `get_settings_panels()`

### Task 17: `CoreAdminContributor.get_settings_panels()` + `_SystemInfoPageHandler`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/contributors/core.py` (imports, new module-level helper + handler class, new method on `CoreAdminContributor`)
- Test: `lexigram-admin/tests/unit/contributors/test_core_settings_panel.py`

- [ ] **Step 1: Write the failing test**

Create `lexigram-admin/tests/unit/contributors/test_core_settings_panel.py`:

```python
"""Tests for CoreAdminContributor's System Info settings panel."""

from __future__ import annotations

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.contracts.admin import PageContent, SettingsPanelDefinition
from lexigram.contracts.admin.widget_content import TableContent
from lexigram.contracts.core import HealthStatus


class _FakeHealthRegistry:
    async def run_all(self) -> tuple[object, dict[str, object]]:
        return (HealthStatus.HEALTHY, {})


async def test_get_settings_panels_returns_system_info_panel() -> None:
    contributor = CoreAdminContributor()
    panels = contributor.get_settings_panels()
    assert len(panels) == 1
    panel = panels[0]
    assert isinstance(panel, SettingsPanelDefinition)
    assert panel.name == "system-info"
    assert panel.contributor == contributor.package_source


async def test_system_info_panel_handler_returns_page_content() -> None:
    contributor = CoreAdminContributor(health=_FakeHealthRegistry())
    panel = contributor.get_settings_panels()[0]
    page = await panel.handler.handle(request=None)
    assert isinstance(page, PageContent)
    assert isinstance(page.body, TableContent)
    fields = {row[0].text for row in page.body.rows}
    assert "Health Status" in fields
    values = {row[0].text: row[1].text for row in page.body.rows}
    assert values["Health Status"] == "healthy"


async def test_system_info_panel_handler_degrades_without_health_registry() -> None:
    contributor = CoreAdminContributor()
    panel = contributor.get_settings_panels()[0]
    page = await panel.handler.handle(request=None)
    values = {row[0].text: row[1].text for row in page.body.rows}
    assert values["Health Status"] == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd lexigram-admin && uv run pytest tests/unit/contributors/test_core_settings_panel.py -v`
Expected: FAIL — `get_settings_panels()` returns `[]` (the `BaseAdminContributor` default), so `len(panels) == 1` fails.

- [ ] **Step 3: Implement**

In `contributors/core.py`, add to the top imports (after `import asyncio`):

```python
import os
import platform
from importlib.metadata import PackageNotFoundError, version
```

Add `PageContent` and `SettingsPanelDefinition` to the existing `from lexigram.contracts.admin import (...)` block (keep alphabetical order):

```python
from lexigram.contracts.admin import (
    ChartContent,
    ChartPoint,
    EmptyContent,
    HealthOverviewProtocol,
    MetricsReadbackProtocol,
    NamedHealthCheckProtocol,
    PageContent,
    SettingsPanelDefinition,
    Stat,
    StatContent,
    TableCell,
    TableContent,
    Tone,
)
```

Add a module-level helper and handler class, right before `class CoreAdminContributor(BaseAdminContributor):` (after the existing `_status_from_value` function):

```python
def _framework_version() -> str:
    """Return the installed lexigram core package version, or 'unknown'."""
    try:
        return version("lexigram")
    except PackageNotFoundError:
        return "unknown"


class _SystemInfoPageHandler:
    """Read-only diagnostics panel — proves out the ``get_settings_panels()`` path."""

    def __init__(self, health: object | None) -> None:
        self._health = health

    async def handle(self, request: Any) -> PageContent:
        """Render framework, runtime, and health diagnostics as a table."""
        health_status = "unknown"
        if isinstance(self._health, HealthOverviewProtocol):
            payload, _details = await self._health.run_all()
            health_status = str(getattr(payload, "value", "unknown"))

        rows = (
            (TableCell(text="Framework Version"), TableCell(text=_framework_version())),
            (TableCell(text="Python Version"), TableCell(text=platform.python_version())),
            (
                TableCell(text="Environment"),
                TableCell(text=os.environ.get("ENVIRONMENT", "unknown")),
            ),
            (
                TableCell(text="Log Level"),
                TableCell(text=os.environ.get("LOG_LEVEL", "INFO")),
            ),
            (TableCell(text="Health Status"), TableCell(text=health_status)),
        )
        return PageContent(
            title="System Info",
            body=TableContent(columns=("Field", "Value"), rows=rows),
        )
```

In `CoreAdminContributor`, add a new method right after `get_health_definitions` (before `render_widget`):

```python
    def get_settings_panels(self) -> Sequence[SettingsPanelDefinition]:
        """Contribute the read-only System Info diagnostics panel."""
        return [
            SettingsPanelDefinition(
                name="system-info",
                title="System Info",
                contributor=self.package_source,
                route_path="/admin/system/info",
                handler=_SystemInfoPageHandler(self._health),
                icon="info",
                category="System",
                order=10,
            )
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd lexigram-admin && uv run pytest tests/unit/contributors/test_core_settings_panel.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full `contributors/core.py` test surface to check for regressions**

Run: `cd lexigram-admin && uv run pytest tests/unit/contributors/test_core_builtin_contributor.py tests/unit/test_core_contributor.py tests/unit/contributors/test_core_settings_panel.py -v`
Expected: PASS (all — the changes are purely additive: new imports, a new module-level class/function, and one new method).

- [ ] **Step 6: Commit**

```bash
git add lexigram-admin/src/lexigram/admin/contributors/core.py lexigram-admin/tests/unit/contributors/test_core_settings_panel.py
git commit -m "feat(admin): add System Info settings panel via get_settings_panels()"
```

---

## Part 7 — Final gate

### Task 18: Full CI + manual security verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full framework CI command**

Run: `cd /home/admin/Documents/AI/applications/framework/lexigram && uv run ruff check . --fix && uv run ruff format . && uv run mypy lexigram-admin/src/ && uv run pytest lexigram-admin/tests --tb=short --cov-fail-under=80`
Expected: all green. If `ruff --fix` or `ruff format` touch files beyond what this plan specified, review the diff before committing — it should only be whitespace/import-order in files this plan already modified.

- [ ] **Step 2: Manual check — readonly enforcement survives a direct POST**

Start the admin app locally (however this repo normally runs it for manual testing — check `lexigram-admin`'s README/dev docs if unfamiliar), then:

```bash
curl -i -X POST http://localhost:8000/admin/settings/admin.deployment \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "environment=hacked" \
  --cookie "<a valid authenticated admin session cookie>"
```

Expected: response succeeds (302/200), but a follow-up `GET /admin/settings/admin.deployment` still shows the original environment value, not `"hacked"`.

- [ ] **Step 3: Manual check — secret HTML never contains the real value**

Set a secret-typed config value (any spec with a `SecretNode`, or add one temporarily for the check if none of the 8 built-ins currently has one), then:

```bash
curl -s http://localhost:8000/admin/settings/<namespace-with-a-secret-node> \
  --cookie "<a valid authenticated admin session cookie>" | grep -o "sk-[a-zA-Z0-9]*"
```

Expected: no match — the real secret value never appears in the response body, only `type="password"` with an empty `value` and a `••••••••` placeholder.

- [ ] **Step 4: Report results to the user**

No commit for this task — it's a verification gate. If Step 1 fails, fix the specific failure (do not proceed to Steps 2-3 with a red CI). If Steps 2-3 reveal a gap, that's a signal a prior task's implementation has a bug — go back and fix that task, add a regression test for the specific gap found, then re-run this gate.
