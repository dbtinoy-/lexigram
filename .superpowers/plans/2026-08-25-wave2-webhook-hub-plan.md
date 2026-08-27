# Plan: Webhook Hub (`demos/webhook-hub`)

> Conventions: wave-2 overview. Port 7078, pkg `webhook_hub`.
> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

> **Task 0 — recon:** pin `packages/lexigram-webhook` manager APIs:
> subscription CRUD, signing secret + rotation grace, retry/backoff policy,
> consecutive-failure disable threshold, DLQ access, event-bus bridge
> registration. Record in `src/webhook_hub/hooks_service.py` docstring.

**Goal:** self-contained delivery theatre — publish events, watch signed attempts/backoff/DLQ against our own sink, rotate secrets under grace, replay dead letters.
**Architecture:** SinkController loopback target recording raw envelopes · SubscriptionsService over webhook manager · PublisherService emitting through bus bridge · timeline/DLQ read models.

### Task 1: Sink + subscriptions — TDD
- [ ] Tests: sink records body + signature header verbatim per name; mode fail→500, timeout→delayed hang (bounded by test clock); subscription create assigns loopback URL `/sink/{name}` and default secret; rotation issues v2 secret with grace window flag.
- [ ] Implement SinkController/SinkStore + SubscriptionsService. Gates. Commit `✨ feat(demos): webhook sink + subscriptions`.

### Task 2: Publish + deliveries — TDD
- [ ] Tests: happy publish → exactly one attempt row, sink received HMAC valid for current secret; fail mode → attempts 1..N with non-decreasing backoff gaps then terminal failed + DLQ entry containing payload; consecutive-failure threshold disables subscription and further publishes skip it (documented constant).
- [ ] Wire publisher through bus bridge; DeliveryTimeline read model. Commit `✨ feat(demos): delivery pipeline`.

### Task 3: Rotation + replay
- [ ] Tests: during grace, deliveries verify with either secret (timeline shows ✓); after grace old signatures count invalid; DLQ replay after healing sink → new successful attempt row linked to original event id; replay twice does not duplicate.
- [ ] Implement rotation/replay service paths. Commit `✨ feat(demos): rotation + dlq replay`.

### Task 4: HTTP + module
- [ ] Controller routes per spec; integration covers publish→inspect sink→dlq→replay via HTTP only; module wiring HOOKS_PORT. Gates. Commit `✨ feat(demos): hooks API`.

### Task 5: Console
- [ ] Left subscriptions list w/ inline mode buttons + rotate button (age chip); center timeline rows (attempt #, status chip colour, gap countdown while pending, sig ✓/✗); DLQ section w/ Replay; right raw inspector pane showing last envelope + headers and a Verify call result. Poll selected subscription every 1 s.
- [ ] Seeded state boot script matches spec (healthy + failing subs). Manual three-act demo documented in README. Commit `✨ feat(demos): webhook console`.

### Task 6: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register webhook-hub`.
