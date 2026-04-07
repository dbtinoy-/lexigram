# Plans 2 — Framework Composition & Contributor Extensibility

> **Source review:** `lexigram-admin/REVIEW2.md`
> **Parent plan track:** `docs/plans/2026-05-25-filament-evolution.md` (Phases 3–7) and `docs/plans/2026-05-25-foundation-hardening.md` (Phases 1–2)
> **Track owner question:** "How should `lexigram-admin` use the rest of the Lexigram framework to become a first-class framework package?"

This directory holds the implementation plans for the **second** architectural
review (`REVIEW2.md`). The first track (`plans/`) deals with admin's internal
architecture (field-type triplet, action unification, page abstraction,
relations, schema). This track deals with the *outside* of admin — how it
composes with framework packages and how external contributors plug in.

The two tracks are deliberately layered so they can land in parallel where
independent, and serialize where they interact. See the **Dependency Map**
below.

---

## Phases

| Phase | File | Goal | Risk | Effort |
|-------|------|------|------|--------|
| **A** | [`2026-05-25-phase-A-contract-promotion.md`](./2026-05-25-phase-A-contract-promotion.md) | Move ~15 protocols + CQRS markers from `admin/` to `lexigram-contracts/` | Low | ~1 week |
| **B** | [`2026-05-25-phase-B-contributor-protocol.md`](./2026-05-25-phase-B-contributor-protocol.md) | Wire `get_management_pages()` + `get_settings_panels()`, route auto-registration, namespacing, permission-aware collection | Med-High | ~2 weeks |
| **C** | [`2026-05-25-phase-C-resource-contribution.md`](./2026-05-25-phase-C-resource-contribution.md) | Allow contributors to ship `Resource` classes (`get_resources()`) | Med | ~1 week |
| **D** | [`2026-05-25-phase-D-framework-delegation.md`](./2026-05-25-phase-D-framework-delegation.md) | Delegate identity/sessions → `lexigram-auth`, tenancy → `lexigram-tenancy`, monitoring → `lexigram-monitor` | High | ~3–4 weeks |
| **E** | [`2026-05-25-phase-E-optional-integrations.md`](./2026-05-25-phase-E-optional-integrations.md) | Populate empty `pyproject.toml` extras + add resource-side declarative integration knobs (cache, tasks, search, …) | Med | ~2 weeks |
| **F** | [`2026-05-25-phase-F-docs-and-example.md`](./2026-05-25-phase-F-docs-and-example.md) | Extension Developer Guide + end-to-end third-party example package | Low | ~1 week |

Total: ~10–12 weeks of focused work, parallelizable along the dependency graph
below.

---

## Dependency Map (incl. existing `plans/` track)

```
              ┌─── Phase 1 (foundation-hardening) ────┐  done / in progress
              │   stop the bleeding — phantom imports │
              └────────────────────┬──────────────────┘
                                   │
              ┌─── Phase 2 (foundation-hardening) ────┐  in progress
              │   audit the halo — views/clusters/…   │
              └────────────────────┬──────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│ Phase 3      │         │ Phase A (this)   │         │ Phase D.1    │
│ SchemaField  │         │ Contract Promote │         │ auth         │
└──────┬───────┘         └────────┬─────────┘         │ delegation   │
       │                          │                   └──────────────┘
       ▼                          ▼                          
┌──────────────┐         ┌──────────────────┐         
│ Phase 4      │  ◄──────│ Phase C (this)   │         
│ Action+Page  │         │ Resource Contrib │         
└──────┬───────┘         └────────┬─────────┘         
       │                          │                   
       ▼                          ▼                   
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│ Phase 5      │         │ Phase B (this)   │         │ Phase D.2/D.3│
│ Cluster +    │         │ Contributor      │         │ tenancy +    │
│ RelationMgr  │         │ Protocol Wiring  │         │ monitoring   │
└──────────────┘         └────────┬─────────┘         └──────────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Phase E (this)   │
                         │ Optional Integ.  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Phase F (this)   │
                         │ Docs + Example   │
                         └──────────────────┘
```

### Critical coordination points

1. **Phase B depends on Phase 4 (Action + Page).**
   Phase 4 creates the `Page` ABC. Phase B needs `Page` (or its typed handler
   protocol) in order to wire `get_management_pages()` end-to-end. **Land
   Phase 4 first, then Phase B.**

2. **Phase C depends on Phase A.**
   Phase C extends the contributor protocol with `get_resources()`. That
   addition is a contract change, so it must land in `lexigram-contracts`
   first via Phase A's vehicle.

3. **Phase D is independent of A/B/C but touches RBAC.**
   D.1 (auth) keeps admin's resource-scoped `rbac/` package intact while
   delegating identity. Coordinate with any RBAC work in Phase 2 of
   foundation-hardening (audit halo).

4. **Phase E depends on Phase 3 (SchemaField).**
   The resource-side knobs (`cacheable = True`, `searchable = True`, …) are
   class attributes on `Resource`/`SchemaField`. Adding them before Phase 3
   consolidates the field-type triplet risks creating yet another duplicate
   surface.

5. **Phase 5 (cluster) recommendation alignment.**
   REVIEW2.md classifies `clusters/` as a contributor surface. Phase 5 of
   the existing track treats it as a first-class navigation primitive. The
   two are **compatible**: Phase 5 ships the `Cluster` dataclass; Phase B
   adds a contributor method that contributes `Cluster` instances. No
   conflict.

### Anti-collision rules

- **No rename of an existing symbol** until the new symbol is in `lexigram-
  contracts` and the old import path emits `DeprecationWarning` for at least
  one minor version.
- **No deletion of an admin-internal protocol** until every first-party
  contributor (`lexigram-cache`, `lexigram-events`, `lexigram-web`) has been
  migrated to the promoted contract.
- **No change to `BaseAdminContributor`'s required methods** in a single
  release. Always add optional methods first, mark them required in a
  later major version.
- **No assumption that `lexigram-tenancy` / `lexigram-auth` / `lexigram-
  monitor` have stable APIs for admin's needs.** Phase D opens
  cross-package PRs first, lands the framework changes, then migrates
  admin.

---

## Conventions used in these plans

All plans follow the format already established by `plans/2026-05-25-phase-3-schemafield.md` and `plans/2026-05-25-phase-4-action-page.md`:

- **Bite-sized TDD steps**: each step is 2–15 minutes; test first, implement,
  verify, commit.
- **Exact file paths** for every Create/Modify/Test.
- **Step duration hints** in parentheses.
- **Validation Gate** at the end of each plan with concrete commands.
- **Risk callouts** where a step touches a public contract or could break a
  downstream consumer.

## CI gate per plan

Every plan must finish green on:

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram
uv run ruff check . --fix && uv run ruff format .
uv run mypy lexigram-admin/src/ lexigram-contracts/src/
cd lexigram-admin && uv run pytest --tb=short --cov-fail-under=80
```

Plus the cross-package smoke test introduced in Phase A:

```bash
uv run pytest lexigram-contracts/tests/ lexigram-cache/tests/ \
              lexigram-events/tests/ lexigram-web/tests/ --tb=short
```

This ensures the three first-party contributors keep working through every
phase.
