# Plan: Flag Console (`demos/flag-console`)

> Conventions: wave-2 overview. Port 7086, pkg `flag_console`.

> **Task 0 — recon:** pin `packages/lexigram-features` FlagManager API:
> override/evaluate signatures, variant flags, percent-rollout support (or
> whether stickiness is ours to add), TTL cache knobs, audit log read seam,
> decorator gate name. Record in `src/flag_console/flag_service.py` docstring.

> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

**Goal:** live checkout preview that visibly reacts to flag flips; audited overrides; kill-switch-protected endpoint; sticky percentage rollout.
**Architecture:** FlagService over FlagManager · CheckoutPreview pure renderer · GatedController demo endpoints · simulated users with segments + stable hash.

### Task 1: Preview core — TDD
- [ ] Tests: preview matrix (user×flag states) asserts currency symbol, wallet visibility (beta ≥30 %, ga never), express flow availability; sticky: same user evaluated twice → same wallet decision across 100 seeded users at 37 %; kill switch removes express from preview and gate returns 403 FEATURE_DISABLED body.
- [ ] Implement CheckoutPreview + user registry + hashing. Gates. Commit `✨ feat(demos): flag preview core`.

### Task 2: Manager wiring + audit
- [ ] Tests: override → evaluate reflects new value with source chip `override`; revert restores default; every mutation appends audit row {actor, key, old, new, ts}; env-backend flag shows source `env` in chained mode.
- [ ] Implement FlagService mutations + audit read. Commit `✨ feat(demos): flag manager + audit`.

### Task 3: HTTP + module
- [ ] Controller routes per spec; integration: PUT override → POST /api/preview changes payload → DELETE reverts; gated endpoint blocked when killed via HTTP; module wiring FLAGS_PORT. Gates. Commit `✨ feat(demos): flags API`.

### Task 4: Console
- [ ] User picker; checkout card re-renders after each change (currency glyph, wallet button, express lane); flag rows with type-appropriate controls (toggle/slider/select), source chip, cache-age chip; big red kill toggle w/ confirm flash; audit stream below. Poll nothing — mutate-and-refresh is enough.
- [ ] Manual demo script in README (three flips → visible changes). Commit `✨ feat(demos): flag console`.

### Task 5: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register flag-console`.
