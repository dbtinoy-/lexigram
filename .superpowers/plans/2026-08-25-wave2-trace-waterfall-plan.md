# Plan: Trace Waterfall (`demos/trace-waterfall`)

> Conventions: wave-2 overview. Port 7095, pkg `trace_waterfall`.

> **Task 0 — recon:** pin `ObservabilityModule` tracing registration:
> decorator idiom vs explicit span API, custom exporter hook, metric counters
> surface. Confirm `AITracerProtocol` contract shape. Record in
> `src/trace_waterfall/pipeline.py` docstring.

> **Blueprint:** the acceptance checklist in `specs/2026-08-25-demos-code-alignment.md` §6 applies to this demo end-to-end.

**Goal:** every pipeline run produces a queryable nested span tree rendered as a waterfall; four deterministic scenarios incl. error + cache-hit paths.
**Architecture:** TracedPipelineService (guard→prompt→cache→llm→memory, scripted stages, seeded latency RNG) · SpanCollectorExporter (in-memory ring, trace summaries + full trees) · metrics aggregation from same exporter events.

### Task 1: Pipeline stages — TDD
- [ ] Tests: happy run returns answer + spans for all 5 stages nested under root http.request; guard-block scenario emits ERROR guard span and skips llm/memory spans; repeat identical question → second run has cache.hit=true attr and no llm span duration >0 (skipped); latencies reproducible under fixed seed.
- [ ] Implement stages + service with injected clock/sleep. Gates. Commit `✨ feat(demos): traced pipeline stages`.

### Task 2: Exporter + metrics
- [ ] Tests: exporter receives finished spans with parent links + durations; trace summary list capped at 25; metrics endpoint aggregates call counts/error counts/histogram buckets matching two scripted runs.
- [ ] Implement SpanCollectorExporter + MetricsView. Commit `✨ feat(demos): span collector + metrics`.

### Task 3: HTTP + observability wiring
- [ ] Register exporter via ObservabilityModule config; controller routes per spec; integration test POST /api/run → GET /api/traces/{id} round-trips tree; scenario param selects canned question/faults. Module wiring TRACE_PORT. Gates. Commit `✨ feat(demos): trace API`.

### Task 4: Console
- [ ] Waterfall renderer: rows sorted by start offset, x-offset/duration scaled to max span end, colour legend per stage, red error bars; click bar → attribute inspector pane (key/values incl. token usage); scenario dropdown + Run button; traces list + metrics strip (counts + bucket bars).
- [ ] Manual check all four scenarios render correctly. Commit `✨ feat(demos): waterfall console`.

### Task 5: Fleet + docs registration
- [ ] Registry/Makefile/README; `make check-demos`. Commit `📝 docs(demos): register trace-waterfall`.
