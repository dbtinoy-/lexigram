# Trash Tab List View Implementation Plan

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Add a "Trash" tab to the admin list view that shows soft-deleted records with Restore/Purge actions.

**Architecture:** Add `include_deleted` field to `TableState` → plumb through `ListRenderer` → `Resource.fetch_list()` → `QuerySpec`. Render Active/Trash tabs in `DataTableRenderer`. Restore/Purge actions only visible in Trash scope.

---

### Task 1: Add `include_deleted` to TableState

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/ui/state.py`
- Modify: `lexigram-admin/tests/unit/ui/test_state.py` (or create if needed)

- [ ] **Step 1: Add field + modifier method**

Add to `TableState` class:
```python
include_deleted: bool = False
```

Add method:
```python
def with_include_deleted(self, include_deleted: bool) -> TableState:
    return self.model_copy(
        update={"include_deleted": include_deleted, "page": 1, "cursor": None},
    )
```

- [ ] **Step 2: Update `from_request()`**

Add `"include_deleted"` to the `known_keys` blocklist so it's not treated as a filter. Then parse it:
```python
include_deleted_raw = q.get("include_deleted", "false")
include_deleted = include_deleted_raw.lower() == "true"
```

Add `include_deleted=include_deleted` to the `state = cls(...)` constructor call.

- [ ] **Step 3: Update `to_query_params()`**

Add:
```python
add("include_deleted", self.include_deleted, False)
```

- [ ] **Step 4: Verify no regression**

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 5: Commit**

---

### Task 2: Add `include_deleted` parameter to `Resource.fetch_list()`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/resources/base.py`

- [ ] **Step 1: Add parameter and plumb to QuerySpec**

In `resources/base.py`, update `fetch_list()`:
```python
async def fetch_list(
    self,
    *,
    limit: int = 20,
    offset: int = 0,
    filters: dict[str, Any] | None = None,
    search: str | None = None,
    search_fields: list[str] | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    include_deleted: bool = False,
) -> tuple[list[Any], int]:
```

After the pagination/search/filter/sort QuerySpec building, add:
```python
if include_deleted:
    qs = qs.with_deleted(True)
```

- [ ] **Step 2: Verify no regression**

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 3: Commit**

---

### Task 3: Plumb through `ListRenderer._fetch_data()`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/resources/list_renderer.py`

- [ ] **Step 1: Pass `include_deleted` from TableState to `fetch_list()`**

In `list_renderer.py`, update the `resource.fetch_list()` call to pass:
```python
include_deleted=state.include_deleted,
```

Also add the same parameter to the legacy fallback path's `QuerySpec` builder:
```python
if state.include_deleted:
    qs = qs.with_deleted(True)
```

- [ ] **Step 2: Verify no regression**

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 3: Commit**

---

### Task 4: Render Active/Trash tabs in DataTableRenderer

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/ui/organisms/data_table/rendering.py`

- [ ] **Step 1: Add `_render_scope_tabs()` method**

Add to `DataTableRenderer`:
```python
def _render_scope_tabs(self) -> str:
    """Render Active/Trash scope tabs."""
    from lexigram.admin.ui.htmx_attrs import HTMXAttrs
    from lexigram.htpy import el, render_to_string

    state = self.state
    prefix = self.config.resource_prefix or ""
    active = not state.include_deleted

    active_state = state.with_include_deleted(False)
    trash_state = state.with_include_deleted(True)

    active_url = active_state.to_url(prefix)
    trash_url = trash_state.to_url(prefix)

    active_attrs = HTMXAttrs.for_full_refresh(active_state, prefix, push_url=True)
    trash_attrs = HTMXAttrs.for_full_refresh(trash_state, prefix, push_url=True)

    def _tab(label: str, is_active: bool, url: str, htmx: dict) -> el:
        return el(
            "button" if is_active else "a",
            label,
            href=url if not is_active else None,
            class_=" ".join([
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                "border-indigo-500 text-indigo-600" if is_active
                else "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
            ]),
            **htmx if not is_active else {},
        )

    return render_to_string(
        el("div",
            el("div",
                el("nav", {"class": "flex space-x-8 border-b border-gray-200"},
                    _tab("Active", active, active_url, active_attrs),
                    _tab("Trash", not active, trash_url, trash_attrs),
                ),
                class_="px-6",
            ),
            class_="mb-4",
        )
    )
```

- [ ] **Step 2: Call it from `render()` method**

Between `header_section` and `container` in the `render()` method:
```python
tabs_html = self._render_scope_tabs() if not self.props.get("render_fragment") else ""
```

Then in the final output:
```python
el("div",
    header_section,
    tabs_html,  # ← injected
    container,
    id=Zones.TABLE.id,
    ...
)
```

- [ ] **Step 3: Verify rendering**

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 4: Commit**

---

### Task 5: Filter actions by scope and write integration tests

**Files:**
- Create: `lexigram-admin/tests/unit/ui/test_trash_tab.py`

- [ ] **Step 1: Write integration test**

```python
"""Tests for trash tab in the admin list view."""
from __future__ import annotations

from lexigram.admin.ui.state import TableState


class TestTableStateIncludeDeleted:
    def test_default_is_false(self) -> None:
        state = TableState()
        assert state.include_deleted is False

    def test_with_include_deleted_true(self) -> None:
        state = TableState()
        new_state = state.with_include_deleted(True)
        assert new_state.include_deleted is True
        assert state.include_deleted is False  # immutability
        assert new_state.page == 1

    def test_with_include_deleted_false(self) -> None:
        state = TableState(include_deleted=True)
        new_state = state.with_include_deleted(False)
        assert new_state.include_deleted is False

    def test_to_query_params_includes(self) -> None:
        state = TableState(include_deleted=True)
        params = state.to_query_params()
        assert params.get("include_deleted") is True

    def test_to_query_params_omits_default(self) -> None:
        state = TableState()
        params = state.to_query_params()
        assert "include_deleted" not in params

    def test_from_request_parses_true(self) -> None:
        class FakeRequest:
            query_params = {"include_deleted": "true"}
        state = TableState.from_request(FakeRequest())
        assert state.include_deleted is True

    def test_from_request_parses_false(self) -> None:
        class FakeRequest:
            query_params = {}
        state = TableState.from_request(FakeRequest())
        assert state.include_deleted is False
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest lexigram-admin/tests/unit/ui/test_trash_tab.py -v
```
Expected: PASS

- [ ] **Step 3: Full regression**

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 4: Commit**

---

### Task 6: Full CI

- [ ] **Step 1: Ruff + pytest**

```bash
uv run ruff check lexigram-admin/src/lexigram/admin/ui/state.py lexigram-admin/src/lexigram/admin/resources/ lexigram-admin/src/lexigram/admin/ui/organisms/data_table/rendering.py &&
uv run ruff format --check lexigram-admin/src/lexigram/admin/ui/state.py lexigram-admin/src/lexigram/admin/resources/ lexigram-admin/src/lexigram/admin/ui/organisms/data_table/rendering.py &&
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```
