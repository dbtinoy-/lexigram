# Phase 5 — Cluster + RelationManager

> **Parent:** `docs/plans/2026-05-25-filament-evolution.md`
> **ADRs:** ADR-004 (Cluster), ADR-005 (RelationManager)
> **Estimate:** 3–4 weeks

## Architecture

Cluster (done per Task 5.1):
- `clusters/base.py` — `Cluster` frozen dataclass
- `Resource.cluster` attribute (backward-compat with `group`)

RelationManager extends the existing `AbstractRelationManager` ABC (115 lines) with:
- Inline create/edit/delete forms
- Permission predicates
- HTMX route handlers
- Zone-based rendering

### HTMX Endpoints

```
GET    /admin/{resource}/{parent_id}/relations/{rel}         → relation panel
GET    /admin/{resource}/{parent_id}/relations/{rel}/new     → create form
POST   /admin/{resource}/{parent_id}/relations/{rel}         → create record
GET    /admin/{resource}/{parent_id}/relations/{rel}/{rid}        → edit form
PUT    /admin/{resource}/{parent_id}/relations/{rel}/{rid}        → update record
DELETE /admin/{resource}/{parent_id}/relations/{rel}/{rid}        → delete record (with confirm)
```

Each response swaps `outerHTML` targeted at the relation panel zone or the row.

## Bite-Sized TDD Steps

### Task 5.3a — Extend AbstractRelationManager

1. Create `relations/manager_ext.py` with `RelationManager(AbstractRelationManager)`:
   - Add `inline_create`, `inline_edit`, `inline_delete`, `inline_detach` attributes
   - Add `create_form()`, `edit_form(record)` — return None by default
   - Add `can_create(user)`, `can_edit(record, user)`, `can_delete(record, user)` — return Ok(None) by default
   - Add `render(request, resource_name)` — returns HTML string
   - Add `get_routes(resource_name)` — returns list of Starlette Route objects

2. Tests:
   - `RelationManager` can be instantiated
   - `inline_*` defaults are True
   - `create_form()` returns None by default
   - `edit_form(record)` returns None by default
   - `can_create()` returns Ok(None) by default
   - `can_edit()` returns Ok(None) by default
   - `can_delete()` returns Ok(None) by default
   - `render()` returns a string/Element
   - `get_routes()` returns a list of Route objects

### Task 5.3b — Relation route handlers

Create route handler methods on RelationManager:
- `_handle_list(request)` — GET → render relation panel
- `_handle_create_form(request)` — GET /new → render create form
- `_handle_create(request)` — POST → create record, return panel
- `_handle_edit_form(request)` — GET /{rid}/edit → render edit form
- `_handle_update(request)` — PUT → update record, return row
- `_handle_delete(request)` — DELETE → delete record, return empty

### Task 5.4 — Wire into Resource

- Add `relations: list[type[RelationManager]] = []` to Resource class
- Add `RelationController` with route registration
- Wire ViewPage to render relation managers

## Validation Gate

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram
uv run ruff check lexigram-admin/ && \
  uv run ruff format --check lexigram-admin/ && \
  uv run mypy lexigram-admin/src/ && \
  uv run pytest lexigram-admin/ --tb=short -x -W ignore::DeprecationWarning
```
