# 06 — Access Control UI: Roles & Users (roadmap R10)

**Date:** 2026-09-01 · **Status:** Phase 1 shipped (roles CRUD + user role
assignment) · **Depends on:** R6 (canonical permission scheme), doc 05
(Security Center patterns), doc 04 (verification playbook)

## Why

The RBAC backend is complete — `admin_roles` table, `AdminRoleSqlStore`,
`AdminRoleService` (create/update/delete with authorizer mirroring and
audit), `PermissionInventoryService` (per-resource permission options,
populated at mount) — but none of it is reachable from the panel. Role
management is API/DB-only, and user role assignment requires SQL. A
professional admin tool manages access control from the UI.

## Architecture

Two superadmin-only controllers in `controllers/access_control.py`,
reusing the Security Center's gate/CSRF/flash patterns (doc 05) and the
**existing** service layer — no new tables, one new audit event type.

```
RolesController  (prefix /roles)
├── GET  /admin/roles                    List roles
├── GET  /admin/roles/new                Create form (permission matrix)
├── POST /admin/roles/create
├── GET  /admin/roles/{name}/edit        Edit form (name fixed)
├── POST /admin/roles/{name}/update
└── POST /admin/roles/{name}/delete      Blocked while any user holds it

UsersController  (prefix /users)
├── GET  /admin/users                    List admins (roles, status)
├── GET  /admin/users/{id}/edit          Role assignment checkboxes
└── POST /admin/users/{id}/update        Guard: never demote the last superadmin
```

### Data access (all existing)

| Need | Source |
| ---- | ------ |
| Role CRUD | `AdminRoleServiceProtocol` (mirrors into the authorizer, audits `role_created/updated/deleted`) |
| Permission matrix options | `PermissionInventoryService.options()` → `{resource: ["resource.action", ...]}`, refreshed per request |
| User listing / role writes | `AdminUserStoreProtocol.list_users` / `get_user_by_id` / `update_user` (mutable record objects) |
| Audit for assignment | `AdminAuditLogServiceProtocol.log_event` — **new** `AdminSecurityEventType.USER_ROLES_UPDATED` |

### Guard rails

1. **System roles** — service already refuses rename/delete; the UI hides
   the delete button and locks the name field.
2. **Role in use** — deletion is blocked while any user still holds the
   role (prevents dangling role strings on users).
3. **Last superadmin** — a role update that removes superadmin standing
   (the configured `super_admin_role` or the `is_superuser` flag) is
   rejected when no *other* active user would retain it. Fail-closed:
   if the user listing cannot be read, the demotion is rejected.
4. All POSTs CSRF-checked (`admin_form_data` — the CSRF middleware
   consumes the body, doc 05); every assignment change audited with
   acting admin + before/after roles.

### Role options on the user form

Stored roles ∪ roles currently held by any user ∪ the configured
`super_admin_role` — so the first admin's setup-granted `superadmin`
role is editable even though it has no `admin_roles` row.

### Navigation

"Users" and "Roles" user-menu entries, superadmin-gated via the doc 05
`NavigationManager._is_super_admin` helper, ordered before Security.

## Phases

- [x] **Phase 1 (this change):** roles list/create/edit/delete with
      permission matrix, users list + role assignment, guard rails,
      nav entries, tests, live verification.
- [x] **Phase 2 (core, R38 — doc 34):** create admin (password policy +
      duplicate-email guard), deactivate with self- and last-superadmin
      guards + session revocation, reactivate; all audited. Remaining:
      email invites, forced password reset, per-user session panel
      linking to the Security Center.
- [ ] **Phase 3:** permission matrix "effective permissions" preview
      (resolve `inherits` chains); role duplication.

## Verification

- Unit: `tests/unit/controllers/test_roles_controller.py`,
  `tests/unit/controllers/test_users_controller.py` (gates, CRUD flows,
  CSRF, guard rails), nav entry tests.
- Live (playbook doc 04): create role with matrix selections → appears in
  list and `admin_roles`; assign to a second user; delete blocked while
  assigned; demotion of the only superadmin rejected; audit rows present.

## Implementation notes (2026-09-01, done)

- **Shipped:** `controllers/access_control.py` (`RolesController` `/roles`,
  `UsersController` `/users`), both mounted best-effort in
  `di/mount/controllers.py` with mount-time wiring (`_csrf_service`,
  `_role_service`, `_inventory`, `_user_store`, `_audit_service`,
  `_super_admin_role`) — request-time container lookups do not work inside
  the mounted sub-app (see doc 05, B10). Nav: "Users" and "Roles" entries
  precede "Security", superadmin-gated via `NavigationManager._is_super_admin`.
- **New audit event:** `AdminSecurityEventType.USER_ROLES_UPDATED`
  (`user_roles_updated`), logged with acting admin id, target user id/email,
  and roles before/after.
- **B11 (framework bug found + fixed):**
  `controllers/route_collection.py::collect_instance_routes` wrapped handlers
  in a closure that only forwarded `request` — any decorated route with path
  parameters (e.g. `/{role_name}/edit`) crashed with `TypeError` at dispatch.
  Fixed to forward matched `request.path_params` that appear in the handler
  signature. Regression tests: `tests/unit/controllers/test_route_collection.py`
  (5 cases incl. multi-param and percent-decoding).
- **Audit attribution for role CRUD:** `AdminRoleService.create_role/`
  `update_role/delete_role` (and `AdminRoleServiceProtocol`) gained a
  keyword-only `actor_id: str | None = None`, threaded to
  `log_event(admin_user_id=...)`. The controllers pass the acting admin's id;
  older callers are unaffected (defaults to `None`, the previous behaviour).
- **Guard rails, live-verified** on the playground (superadmin session):
  - last-superadmin demotion → 302 `?error=Cannot remove super-admin access…`,
    row untouched;
  - delete of a held role → blocked with holder count (server-side check,
    not just hidden button);
  - role name/permission format validation (`^[a-z0-9][a-z0-9_-]*$`,
    `resource.action[:scope]`) rejects garbage before hitting the service;
  - `user_roles_updated`, `role_created`, `role_updated`, `role_deleted`
    audit rows all attributed to `5b424a06…` (acting admin) in
    `admin_security_audit_log`.
- **Note:** `resources/roles.py::RolesResource` exists but is not registered
  anywhere; the new controllers are the canonical roles UI. Setup-created
  superadmins hold the role via `admin_users.roles` (no `is_superuser`
  column in the SQL store), so the demotion guard is fully effective.
- Full suite after: **5182 passed / 8 skipped**, coverage 75.60%.
