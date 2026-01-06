# Action `render_button()` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan.

**Goal:** Implement a proper `render_button()` method on the Action hierarchy that produces HTMX-enabled `ActionButton` elements.

**Architecture:** Each action subclass knows its URL pattern and HTMX semantics. `render_button()` uses `_get_url()` and `_get_htmx_attrs()` to build an `ActionButton` via `lexigram.ui.molecules.action_button.ActionButton`.

**Tech Stack:** Python 3.12, Starlette, HTMX, htpy, lexigram.ui

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/actions/base.py`
- Modify: `lexigram-admin/src/lexigram/admin/actions/standard.py`
- Modify: `lexigram-admin/src/lexigram/admin/actions/types.py`
- Test: `lexigram-admin/tests/unit/actions/test_action_base.py`
- Test: `lexigram-admin/tests/unit/actions/test_action_standard.py`

---

### Task 1: Update `ActionContext` to carry a `record_id` helper

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/actions/types.py`
- Test: `lexigram-admin/tests/unit/actions/test_action_base.py`

- [ ] **Step 1: Write the failing test**

Add to `test_action_base.py`:
```python
class TestActionContext:
    def test_resource_name_default(self) -> None:
        ctx = ActionContext()
        assert ctx.resource_name == ""

    def test_context_creation(self) -> None:
        ctx = ActionContext(resource_name="users", user="admin")
        assert ctx.resource_name == "users"
        assert ctx.user == "admin"
```

- [ ] **Step 2: Verify tests fail (no TestActionContext yet)**

Run: `uv run pytest lexigram-admin/tests/unit/actions/test_action_base.py -v`
Expected: `FAILED` for the new test class

- [ ] **Step 3: Run the test** (the types already exist, so this may pass)

Run: `uv run pytest lexigram-admin/tests/unit/actions/test_action_base.py::TestActionContext -v`

---

### Task 2: Implement `RowAction.render_button()` with URL formatting and HTMX attrs

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/actions/base.py`

**Details:**
- Add `_get_record_id(record) => str` static helper to extract record ID from dict/object
- Add `_get_url(record, ctx) => str | None` to `RowAction` (default: `/{resource_name}/{id}/{action_name}`)
- Add `_get_htmx_attrs(url, record, ctx) => dict[str, str]` to `RowAction` (default: `hx-get` targeting table data zone)
- Implement `render_button()` that calls `ActionButton(label, variant, icon, size="sm", **attrs)`
- Add `_action_color_to_variant()` mapping: `ActionColor.{GRAY→ghost, PRIMARY→primary, DANGER→danger, WARNING→warning, SUCCESS→secondary, SECONDARY→secondary, INFO→secondary}`

- [ ] **Step 1: Write the failing test**

Add to `test_action_base.py::TestActionRenderButton` and a new class:
```python
class TestRowActionRenderButton:
    def test_render_button_returns_string(self) -> None:
        action = ConcreteRowAction(name="view", label="View", icon="eye")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "123"}, ctx)
        assert isinstance(result, str)
        assert "View" in result

    def test_render_button_includes_htmx(self) -> None:
        action = ConcreteRowAction(name="view", label="View")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "123"}, ctx)
        assert "hx-get" in result
        assert "/users/123/view" in result

    def test_render_button_visible_for_only(self) -> None:
        action = ConcreteRowAction(name="hidden", label="Hidden")
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "1"}, ctx)
        assert isinstance(result, str)
```

- [ ] **Step 2: Verify test fails**

Run: `uv run pytest lexigram-admin/tests/unit/actions/test_action_base.py::TestRowActionRenderButton -v`
Expected: FAIL because base class `render_button` still returns htpy button

- [ ] **Step 3: Implement `render_button()` on `RowAction`**

In `actions/base.py`, add to `RowAction`:
```python
def _get_record_id(self, record: Any) -> str:
    if isinstance(record, dict):
        return str(record.get("id", ""))
    if hasattr(record, "id"):
        return str(record.id)
    return ""

def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
    record_id = self._get_record_id(record)
    if not record_id:
        return None
    return f"/{ctx.resource_name}/{record_id}/{self.name}"

def _get_htmx_attrs(self, url: str, record: Any, ctx: ActionContext) -> dict[str, str]:
    attrs: dict[str, str] = {"hx-get": url}
    confirmation = self.confirm()
    if confirmation and confirmation.message:
        attrs["hx-confirm"] = confirmation.message
    attrs["hx-target"] = "#table-data"
    attrs["hx-swap"] = "innerHTML"
    return attrs

def render_button(self, record: Any, ctx: ActionContext) -> str:
    from lexigram.ui.molecules.action_button import ActionButton
    
    if not self.visible_for(record, ctx.user):
        return ""
    
    url = self._get_url(record, ctx)
    if not url:
        return ""
    
    variant = self._color_to_variant()
    htmx_attrs = self._get_htmx_attrs(url, record, ctx)
    
    button = ActionButton(
        label=self.label or self.name,
        variant=variant,
        icon=self.icon,
        size="sm",
        **htmx_attrs,
    )
    result = button.render()
    return str(result) if result else ""
```

Add `_color_to_variant()` to `Action` base:
```python
def _color_to_variant(self) -> str:
    mapping = {
        ActionColor.GRAY: "ghost",
        ActionColor.PRIMARY: "primary",
        ActionColor.SECONDARY: "secondary",
        ActionColor.SUCCESS: "secondary",
        ActionColor.WARNING: "warning",
        ActionColor.DANGER: "danger",
        ActionColor.INFO: "secondary",
    }
    return mapping.get(self.color, "ghost")
```

Also override `_get_url` for `BulkAction` and `HeaderAction`:
```python
class BulkAction(Action[list[Any], Any]):
    def _get_url(self, records: list[Any], ctx: ActionContext) -> str | None:
        return f"/{ctx.resource_name}/bulk/{self.name}"

class HeaderAction(Action[None, Any]):
    def _get_url(self, record: None, ctx: ActionContext) -> str | None:
        return f"/{ctx.resource_name}/{self.name}"
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest lexigram-admin/tests/unit/actions/test_action_base.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Run full lint + format**

Run: `uv run ruff check lexigram-admin/src/lexigram/admin/actions/ && uv run ruff format --check lexigram-admin/src/lexigram/admin/actions/`

- [ ] **Step 6: Commit**

```bash
rtk git add lexigram-admin/src/lexigram/admin/actions/base.py lexigram-admin/tests/unit/actions/test_action_base.py
rtk git commit -m "feat(actions): implement render_button on Action hierarchy

- RowAction._get_url(): /{resource}/{id}/{action} pattern
- BulkAction._get_url(): /{resource}/bulk/{action} pattern
- HeaderAction._get_url(): /{resource}/{action} pattern
- render_button(): ActionButton with HTMX attrs, visibility check
- _color_to_variant(): ActionColor -> ActionButton variant mapping
- 3 new tests for RowAction.render_button"
```

---

### Task 3: Override `render_button()` on standard actions

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/actions/standard.py`
- Create: `lexigram-admin/tests/unit/actions/test_action_standard.py`

- [ ] **Step 1: Write tests for standard action rendering**

```python
"""Tests for standard action render_button behavior."""

from lexigram.admin.actions.standard import (
    CloneAction, CreateAction, DeleteAction, DeleteBulkAction,
    EditAction, PurgeAction, RestoreAction, ViewAction,
)
from lexigram.admin.actions.types import ActionContext


class TestStandardActionRenderButton:
    def test_edit_action_url(self) -> None:
        action = EditAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42/edit" in result
        assert "hx-get" in result
        assert "Edit" in result
        assert "pencil" in result

    def test_view_action_url(self) -> None:
        action = ViewAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42/view" in result
        assert "hx-get" in result

    def test_delete_action_with_confirmation(self) -> None:
        action = DeleteAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "42"}, ctx)
        assert "/users/42/delete" in result
        assert "hx-confirm" in result

    def test_create_action_url(self) -> None:
        action = CreateAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert "/users/create" in result
        assert "hx-get" in result

    def test_create_action_label_and_icon(self) -> None:
        action = CreateAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert "Create" in result
        assert "plus" in result

    def test_clone_action_url(self) -> None:
        action = CloneAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/clone" in result

    def test_restore_action_url(self) -> None:
        action = RestoreAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/restore" in result

    def test_purge_action_with_confirmation(self) -> None:
        action = PurgeAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "7"}, ctx)
        assert "/users/7/purge" in result
        assert "hx-confirm" in result

    def test_delete_bulk_action(self) -> None:
        action = DeleteBulkAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button([{"id": "1"}, {"id": "2"}], ctx)
        assert "/users/bulk/delete" in result
        assert "hx-confirm" in result

    def test_bulk_delete_uses_post(self) -> None:
        action = DeleteBulkAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button([{"id": "1"}], ctx)
        assert "hx-post" in result

    def test_row_action_invisible_for_none(self) -> None:
        action = ViewAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button(None, ctx)
        assert result == ""  # No record, no id

    def test_delete_action_danger_color(self) -> None:
        action = DeleteAction()
        ctx = ActionContext(resource_name="users")
        result = action.render_button({"id": "1"}, ctx)
        assert "red" in result  # DANGER color maps to red variant
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest lexigram-admin/tests/unit/actions/ -v --tb=short`
Expected: Many failures because standard actions don't override rendering

- [ ] **Step 3: Override `render_button()` on each standard action**

For each standard action in `standard.py`, add a `_get_url()` override:

```python
class EditAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}/edit" if rid else None

class ViewAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}" if rid else None

class DeleteAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}" if rid else None
    
    def _get_htmx_attrs(self, url: str, record: Any, ctx: ActionContext) -> dict[str, str]:
        confirmation = self.confirm()
        if confirmation and confirmation.message:
            return {
                "hx-delete": url,
                "hx-confirm": confirmation.message,
                "hx-target": "#table-data",
                "hx-swap": "innerHTML",
            }
        return {"hx-delete": url, "hx-target": "#table-data", "hx-swap": "innerHTML"}

class CreateAction(HeaderAction):
    def _get_url(self, record: None, ctx: ActionContext) -> str | None:
        return f"/{ctx.resource_name}/create"

class CloneAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}/clone" if rid else None

class RestoreAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}/restore" if rid else None

class PurgeAction(RowAction):
    def _get_url(self, record: Any, ctx: ActionContext) -> str | None:
        rid = self._get_record_id(record)
        return f"/{ctx.resource_name}/{rid}/purge" if rid else None
    
    def _get_htmx_attrs(self, url: str, record: Any, ctx: ActionContext) -> dict[str, str]:
        confirmation = self.confirm()
        if confirmation and confirmation.message:
            return {
                "hx-delete": url,
                "hx-confirm": confirmation.message,
                "hx-target": "#table-data",
                "hx-swap": "innerHTML",
            }
        return {"hx-delete": url, "hx-target": "#table-data", "hx-swap": "innerHTML"}

class DeleteBulkAction(BulkAction):
    def _get_url(self, records: list[Any], ctx: ActionContext) -> str | None:
        return f"/{ctx.resource_name}/bulk/delete"
    
    def _get_htmx_attrs(self, url: str, records: list[Any], ctx: ActionContext) -> dict[str, str]:
        confirmation = self.confirm()
        attrs = {
            "hx-post": url,
            "hx-target": "#table-data",
            "hx-swap": "innerHTML",
            "hx-include": "#lexigram-table [name='ids']:checked",
        }
        if confirmation and confirmation.message:
            attrs["hx-confirm"] = confirmation.message
        return attrs
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest lexigram-admin/tests/unit/actions/ -v --tb=short`
Expected: PASS

- [ ] **Step 5: Run full lint + format**

Run: `uv run ruff check lexigram-admin/src/lexigram/admin/actions/ && uv run ruff format --check lexigram-admin/src/lexigram/admin/actions/`

- [ ] **Step 6: Commit**

```bash
rtk git add lexigram-admin/src/lexigram/admin/actions/standard.py lexigram-admin/tests/unit/actions/test_action_standard.py
rtk git commit -m "feat(actions): standard action render_button overrides with HTMX attrs

- Each standard action (Edit, View, Delete, Create, Clone, Restore, Purge, BulkDelete)
  overrides _get_url() with proper route patterns
- DeleteAction/PurgeAction use hx-delete with hx-confirm
- DeleteBulkAction uses hx-post with hx-include for checkbox selection
- 12 new tests covering URL patterns, HTMX attrs, confirmation, visibility"
```

---

### Task 4: Run full CI suite

- [ ] **Step 1: Full CI**

```bash
uv run ruff check lexigram-admin/ && uv run ruff format --check lexigram-admin/ && uv run mypy lexigram-admin/src/lexigram/admin/actions/ lexigram-admin/src/lexigram/admin/openapi/ && uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

- [ ] **Step 2: Commit any fixes**

```bash
rtk git add -A
rtk git commit -m "fix: CI cleanup for action render_button"
```
