# Spec: Trace Waterfall

Slug `trace-waterfall` · package `trace_waterfall` · port 7095 (`TRACE_PORT`)
Subsystems: `lexigram-ai-observability` (tracing/metrics via `ObservabilityModule`, `AITracerProtocol`)

## Story

Type a question (or click a canned scenario) and watch the request split into
spans rendered as a Gantt waterfall: `http.request` → `guard.input` →
`prompt.render` → `llm.complete` → `cache.get/put` → `memory.append`, each bar
positioned by real start/duration, nestable to children, error spans red with
exception attributes. A second panel shows live metrics counters. This is the
"prove it's observable end-to-end" demo.

## Instrumented pipeline

One fake RAG-ish flow assembled from existing scripted parts:

1. `input_guard` — blocks a banned phrase scenario (span status ERROR)
2. `prompt.render` — template fill
3. `cache.lookup` — hit/miss depends on repeat question (miss = 120 ms fake
   latency)
4. `llm.complete` — scripted completion, 200–400 ms jittered-but-seeded
   latency; token usage attrs
5. `memory.append` — stores exchange

Scenarios dropdown: Happy path · Cache hit · Guard block · LLM error. Seeded
latency RNG so replays are reproducible (reproducibility ethos).

## Architecture

- `TracedPipelineService` — orchestrates the five stages; every stage wrapped
  through observability decorators/tracer per package API (recon task pins the
  decorator vs explicit-span idiom).
- `SpanCollectorExporter` — custom in-memory exporter registered with the
  module; keeps ring buffer of finished traces (id, root span tree, wall
  clock), plus aggregated metric deltas.
- `TraceController` — API + waterfall UI.

## API

| Route | Purpose |
|---|---|
| `POST /api/run {question, scenario?}` | execute traced pipeline, returns trace_id |
| `GET /api/traces?limit=25` | recent trace summaries |
| `GET /api/traces/{id}` | full span tree (nested, with timings/attrs/status) |
| `GET /api/metrics` | stage call counts, error counts, latency histogram buckets |

## Console

Left: question box + scenario select + Run. Center: waterfall of latest trace
(rows = spans, x = offset/duration ms, colour by stage, red errors); click a
bar → attribute inspector. Bottom: traces list + metrics strip.

## Testing

Unit: exporter captures nested spans with parent links; guard-error marks span
and short-circuits pipeline; cache-hit path skips llm span. Integration:
run twice same question → second trace contains cache.hit=true attr; metrics
counters advance. Console smoke.

## Non-goals

OpenTelemetry wire export (documented as config); distributed multi-service
tracing; log tailing.
