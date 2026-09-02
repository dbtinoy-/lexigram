# 36 — Effective permissions preview + role duplication (R40)

**Date:** 2026-09-02 · **Status:** implementing · **Roadmap:** doc 06
(Access-control UI) Phase 3 · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

Doc 06 Phase 3 left two gaps in the roles UI:

1. **Inheritance is opaque.** A role's edit page shows only its *direct*
   permission checkboxes; the list page counts only direct permissions.
   When `content-editor` inherits `viewer` (which may inherit further),
   nothing in the UI answers "what can this role actually do?" — the
   operator has to walk `inherits` chains by hand across edit pages.
   Runtime checks *do* resolve chains (lexigram-auth
   `_check_mixin._get_effective_roles`), so the UI systematically
   under-reports what a role grants. That is the dangerous direction:
   an operator can grant more than they think they are granting.
2. **No duplication.** Roles with 20+ matrix selections must be re-keyed
   by hand to create a close variant, which is exactly how checkbox
   drift between "almost identical" roles happens.

## 2. Design

### 2.1 Effective-permission resolver (`rbac/effective.py`, pure)

New module with a frozen dataclass + pure function so the semantics are
unit-testable without a store or controller:

```python
@dataclass(frozen=True)
class EffectivePermissions:
    role: str
    direct: frozenset[str]                       # own permissions
    inherited: Mapping[str, tuple[str, ...]]     # perm -> sorted source roles
    ancestors: tuple[str, ...]                   # resolved chain, sorted
    missing: tuple[str, ...]                     # referenced but not stored

    @property
    def all_permissions(self) -> frozenset[str]  # direct ∪ inherited

def resolve_effective_permissions(
    name: str, roles: Mapping[str, Any]
) -> EffectivePermissions
```

**Semantics mirror the runtime authorizer exactly** (that is the whole
point of the preview — showing anything else would be a lie):

- BFS over `inherits` with a visited set → **cycle-safe** (a↔b edits
  cannot hang the page; the cycle simply stops expanding, same as
  `_get_effective_roles`'s `processed` set).
- Parents referenced but not stored contribute nothing; they are
  reported in `missing` so the UI can warn (the runtime silently treats
  them as permission-less, which is fail-closed and correct, but the
  operator should see the dangling reference).
- `inherited` keeps *which* ancestor(s) contributed each permission —
  "via viewer" badges; a permission that is both direct and inherited
  counts as direct (redundant grants are not an error).
- Duck-typed field access (`getattr` then dict-key fallback) matching
  the authorizer, so `RoleDefinition` objects and plain dicts both work.

Not reused from lexigram-auth directly because `_get_effective_roles`
is a private mixin method on the live service and returns only the role
set — no per-permission provenance, which is the UX we need. The
resolver is deliberately dependency-free so drift is testable: a unit
test asserts our resolution matches the semantics documented above.

### 2.2 Edit-page preview card

`RolesController.edit_page` appends a read-only card below the form:

- **Direct** permissions (count + mono chips).
- **Inherited** permissions with "via `<role>`" provenance.
- Amber warning when `missing` is non-empty ("inherits 'ghost' which no
  longer exists — it grants nothing").
- The card reflects the **stored** role, not unsaved checkbox state
  (a live JS preview is out of scope; the card notes "Save to refresh").

### 2.3 List-page effective counts

The "Permissions" column becomes `direct` + a muted `(+n inherited)`
suffix when n > 0 — all roles are already loaded, so this is free.

### 2.4 Role duplication (prefill, not clone-mutation)

Per-row **Duplicate** link → `GET /admin/roles/new?from=<name>`. The
create form prefills description/permissions/inherits from the source
and proposes `<name>-copy` (still matches `_ROLE_NAME_RE`). Unknown
`from` → redirect to the list with an error.

Chosen over a `POST /{name}/duplicate` mutation because prefill reuses
the existing create POST unchanged: same CSRF, same validation, same
duplicate-name rejection, same audit event — no second mutation path to
guard, and the operator reviews the copy before it exists.

### 2.5 Delete guard: block deletion while inherited (bug found during design)

Found while writing §3: role deletion is blocked while the role is
*assigned to users*, but **not** while other roles inherit it. Deleting
`viewer` while `editor` inherits it silently narrows `editor`'s
effective permissions (runtime treats the missing parent as
permission-less — fail-closed but invisible). R40 extends the delete
guard with the same pattern as "held by n admins": deletion is rejected
with "still inherited by editor — remove the inheritance first". The
`missing` warning in the preview card remains the safety net for
references that predate this guard (or arrive via direct DB edits).

### 2.6 Out of scope

- Live (unsaved-state) preview via JS — revisit with the Alpine budget.
- Per-user effective permissions on the Users page (this doc's resolver
  makes that a follow-up, not a rewrite).
- Cycle *prevention* at save time — the resolver is cycle-safe and the
  card makes chains visible; hard-blocking edits needs UX for repair
  ordering and is not worth it yet.

## 3. Implementation order

1. `rbac/effective.py` (dataclass + resolver) + export from
   `rbac/__init__.py` if it re-exports; unit tests
   `tests/unit/rbac/test_effective_permissions.py` (linear chain, deep
   chain, diamond, cycle a↔b, self-reference, missing parent, dict
   roles, direct-wins-over-inherited, unknown target role).
2. Controller: `_effective_html()` card; `edit_page` appends it;
   `list_page` count suffix + Duplicate link; `new_page` `?from=`
   prefill; `delete` inherited-by guard. Tests in
   `tests/unit/controllers/test_roles_controller.py`.
3. Live verify (playbook doc 04): seed `viewer` → `editor` (inherits
   viewer) → check edit-page card provenance + list counts; duplicate
   `editor` → prefilled form → create; attempt to delete `viewer` →
   blocked with "inherited by" message.
4. Doc §4 + README row + tick doc 06 P3 + commit/push (no merge).

## 4. Verification

**Unit tests (all green; 687 across controllers + rbac + settings):**

- `tests/unit/rbac/test_effective_permissions.py` (new, 10 tests):
  no-inheritance, single parent, deep chain, diamond provenance
  (`p.shared` via `("base", "left")`), direct-wins-over-inherited,
  two-role cycle terminates, self-reference ignored, missing parent
  reported + grants nothing, unknown target role, dict roles resolve
  like objects.
- `tests/unit/controllers/test_roles_controller.py` (+7): effective
  card provenance/warning/cycle/placeholders; duplicate prefill
  (unknown source → error redirect, prefilled name
  `editor-copy`/description/inherits-checked/permissions, blank form
  without `?from=`); delete blocked while inherited (message names the
  inheritor); list page `(+1 inherited)` + Duplicate link. Existing
  delete tests updated to stub `list_roles` (the new guard reads it).
- Collateral: `test_settings_controller_save_spec.py` visible-spec
  count 9→10 (R39 leftover found by this run's wider sweep).
- ruff + mypy clean.

**Live transcript (playground, 2026-09-02):**

1. Seeded `viewer` (`posts.read`) and `editor` (`posts.write`, inherits
   viewer) through the create form.
2. `/admin/roles/editor/edit` → card shows "Effective permissions
   (2 total)", `posts.write` direct, `posts.read` **via viewer**.
3. `/admin/roles` → editor row shows "1 (+1 inherited)" and a
   Duplicate link to `new?from=editor`.
4. `/admin/roles/new?from=editor` → "Duplicating **editor**", name
   prefilled `editor-copy`, `posts.write` in the custom textarea,
   `viewer` inheritance checked; created `editor-copy` via the normal
   create POST (audit + duplicate-name protection intact).
5. `POST /roles/viewer/delete` while inherited → 302
   `error=Cannot delete 'viewer': still inherited by editor. Remove the
   inheritance first.`
6. Cleanup top-down (`editor-copy` → `editor` → `viewer`) all deleted —
   the guard unblocks once no role inherits the target.
