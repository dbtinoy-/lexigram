# Plan: Multi-Tenant Notes (`demos/tenant-notes`)

> Conventions: wave-2 overview. Port 7087, pkg `tenant_notes`.

> **Task 0 — recon:** pin `packages/lexigram-tenancy` APIs: resolver-chain
> composition, ASGI enforcement middleware mount, row-level scoping protocol
> for repositories, tenant lifecycle service + domain events, per-tenant config
> override store. Record in `src/tenant_notes/tenanted_repo.py` docstring.

> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

**Goal:** one notes workspace where tenant context hard-isolates data; violations fail loudly; lifecycle admin and per-tenant theming are live.
**Architecture:** resolver chain (header→path) + enforcement middleware · NotesRepo scoped by tenancy's row-level strategy over in-memory table · TenantAdminService (lifecycle events feed) · config overrides driving accent/locale.

### Task 1: Resolution + enforcement — TDD
- [ ] Tests: header wins over path prefix; neither → 403 problem detail; unknown slug → 403; suspended tenant fails closed even with valid header.
- [ ] Wire resolver chain + middleware into module config; echo resolved tenant via request state. Gates. Commit `✨ feat(demos): tenant resolution`.

### Task 2: Isolated repo — TDD
- [ ] Tests: CRUD scoped to current tenant; requesting another tenant's note id → NotFound (never leak); listing only own rows even after cross-tenant inserts; scoped repo built through tenancy protocol not hand-rolled filters.
- [ ] Implement TenantedNotesRepo + NotesService. Commit `✨ feat(demos): row-level notes isolation`.

### Task 3: Admin lifecycle + config
- [ ] Tests: create tenant → resolvable immediately with empty notes; suspend → resolution blocked + event in feed; config accent change reflected only in that tenant's preview payload; violation service path returns structured error detail (not generic 500).
- [ ] Implement admin service/config/violation lab. Commit `✨ feat(demos): tenant admin + config`.

### Task 4: HTTP + module
- [ ] Controller routes per spec incl. path-prefix mount variant for comparing resolvers; integration: full CRUD under header mode then same ids under different tenant → 404s; module wiring TENANT_PORT. Gates. Commit `✨ feat(demos): tenants API`.

### Task 5: Console
- [ ] Top bar switcher (sets X-Tenant on fetches) + resolved chip + accent swatch; notes list/editor; Violation lab tab (button → rendered framework error); Admin tab (table, create form, suspend buttons, event feed); Config tab (accent picker). Accent CSS variable applied from preview payload.
- [ ] Seeded tenants per spec incl. suspended `skeleton`. Manual walkthrough documented. Commit `✨ feat(demos): tenant console`.

### Task 6: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register tenant-notes`.
