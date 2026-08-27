# Plan: Router Playground (`demos/router-playground`)

> Execute with superpowers:executing-plans. Shared conventions, gates, and
> fleet-registration steps live in `specs/2026-08-25-demo-wave-2-overview.md`
> and are not repeated here.
>
> **Blueprint:** the acceptance checklist in
> `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo
> end-to-end.
>
> **Task 0 — API recon (before Task 1):** read
> `experimental/ai/lexigram-ai-relay-gateway/src` public surface +
> `core/lexigram-contracts` routing protocols (`LLMRouterProtocol`,
> `QuotaBackendProtocol`, `InferenceLoggerProtocol`) and the
> `support-agent` scripted-client pattern. Record the chosen seams as a
> comment block in `src/router_playground/router_service.py`; if a contract
> does not fit, implement against the gateway's protocol and note why.

**Goal:** one prompt in → visible channel decision, failover chain, cost/quota/breaker state out; fully offline.
**Architecture:** FakeProviderCluster (4 scripted providers) behind channels with capability tags, quotas, per-channel resilience pipelines; RouterService appends decisions to LedgerStore; vanilla-JS console polls `/api/channels`.
**Stack:** lexigram web/resilience modules, httpx-free, seeded latencies.

### Task 1: Providers, channels, ledger — TDD
- [ ] Failing tests `tests/test_router.py`: cheapest healthy capable channel wins; capability filter (`require:"json"` excludes premium); fallback order on primary failure; breaker opens after N=3 consecutive faults and skips channel until half-open; quota exhaustion routes away and marks channel exhausted; ledger entry records attempt chain `{channel,status,latency,cost}` per attempt.
- [ ] Implement `FakeProviderCluster` (scenarios healthy/flaky/down via FaultController), `ChannelRegistry`, `RouterService.route()`, `LedgerStore` ring buffer.
- [ ] Verify: pytest green · ruff · compileall. Commit feature+tests together: `✨ feat(demos): router service core with selection suite`.

### Task 2: HTTP surface + module wiring
- [ ] `controllers/api.py`: routes from spec table; JSONResponse shapes frozen in tests (contract-style assertions on keys).
- [ ] `module.py` WebModule wiring port `ROUTER_PORT` default 7077, CSRF off; provider registers cluster/service/ledger singletons.
- [ ] Integration test via ASGI: forced failover chat returns answer + ledger shows ≥2 attempts; fault flip endpoint mutates scenario.
- [ ] Verify gates. Commit `✨ feat(demos): router playground API`.

### Task 3: Console UI
- [ ] `ui/pages.py` (clone rates pattern), `views/console.html`, `static/{style.css,app.js}`: prompt box + capability select; decision card; animated attempt list; channel grid with spend meters (CSS width by $spent/$quota), quota bars, breaker dot colours (green/red/amber half-open); ledger table footer; poll `/api/channels` every 2 s.
- [ ] Manual boot smoke: `make demos-up` after Task 4 registration; click through all four scenarios; screenshot-worthy state: kill premium+economy → shadow toggled off → everything red then recovery.
- [ ] Commit `✨ feat(demos): router playground console`.

### Task 4: Fleet + repo integration
- [ ] Registry entry (slug `router-playground`, port 7077), Makefile three lists + smoke line, demos README section + running row, hub card appears automatically.
- [ ] `make check-demos` green. Commit `📝 docs(demos): register router-playground`.
