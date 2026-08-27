# Plan: Workflow Studio (`demos/workflow-studio`)

> Conventions: wave-2 overview. Port 7080, pkg `workflow_studio`.
> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

> **Task 0 — recon:** pin `packages/lexigram-workflow` saga/state-machine/
> persistence APIs (WorkflowProvider registrations, transition-history read
> seam, optimistic-lock version field). Decide how "kill engine" maps to
> in-process semantics: cancel running saga task + drop runtime, keep store.
> Record in `src/workflow_studio/engine_host.py` docstring.

**Goal:** visual saga with live node states, armed per-step failures, reverse compensation, and kill→restart durability — all in-memory, deterministic.
**Architecture:** FulfilmentSaga (3 steps + compensations over seeded inventory/invoice/shipment tables) · EngineHost (single worker task, killable; rehydrates from persisted transitions on restart) · SagasController API.

### Task 1: Saga definition + happy path — TDD
- [ ] Tests: place order → steps run in order → terminal `completed`; inventory decremented then shipment exists; transition history rows have monotonic versions.
- [ ] Implement definitions + EngineHost.run(). Gates. Commit `✨ feat(demos): fulfilment saga core`.

### Task 2: Failure + compensation
- [ ] Tests: fault armed on charge_card → reserve_stock compensation executed (inventory restored), terminal `compensated`, history shows forward+reverse rows; disarm → subsequent saga completes normally.
- [ ] Implement FaultArm + compensation wiring. Commit `✨ feat(demos): saga failure + compensation`.

### Task 3: Kill / restart durability
- [ ] Tests: crash_after=2 during active saga → runtime dropped, store still lists saga `in_progress` with last completed step; restart() resumes exactly remaining steps once; second restart is no-op; concurrent sagas unaffected.
- [ ] Implement kill/restart endpoints' service logic. Commit `✨ feat(demos): engine kill/restart`.

### Task 4: HTTP + module
- [ ] Controller routes per spec; integration test drives full lifecycle through HTTP incl. kill window (deterministic via injected step barrier event). Module wiring port STUDIO_PORT. Gates. Commit `✨ feat(demos): studio API`.

### Task 5: Console UI
- [ ] SVG graph (nodes grey/running/green/red/undone), toolbar with fault toggles + New order + Kill/Restart buttons (disabled states mirror engine), transition table w/ version column, recent-sagas list. Poll `/api/sagas/{id}` at 700 ms while active.
- [ ] Manual demo script documented in README (the three-act walkthrough). Commit `✨ feat(demos): workflow studio console`.

### Task 6: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register workflow-studio`.
