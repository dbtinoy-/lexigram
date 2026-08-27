# Spec: Webhook Hub

Slug `webhook-hub` · package `webhook_hub` · port 7078 (`HOOKS_PORT`)
Subsystems: `lexigram-webhook` (subscriptions, HMAC signing, backoff retries, DLQ, secret rotation), event bus bridge

## Story

Register a subscription whose target URL points **back at this hub's own sink**
(`/sink/{name}`), publish an event, and watch the delivery timeline: signed POST
flies out, sink answers 200, entry goes green. Flip the sink to "reject" mode
and publish again: attempt 1 red → backoff countdown → attempt 2 red → … →
dead-letter. Rotate the signing secret mid-stream and show old-signature
deliveries still verifying during the grace period. Auto-disable kicks in
after N consecutive failures — every resilience knob made visible.

## Architecture

- **Self-sink**: `SinkController` receives deliveries at `/sink/{name}`,
  records envelopes+headers verbatim into `SinkStore`, replies per mode
  (`200 ok | 500 fail | timeout`). Because targets are loopback HTTP to our own
  server, the whole story is offline yet uses real wire semantics.
- `SubscriptionsService` — CRUD over `lexigram-webhook` manager; secret +
  rotation grace configured per subscription (recon task pins manager API).
- `PublisherService` — emits domain events on the bus; webhook bridge fans out.
- `HooksController` — API + console.

## API

| Route | Purpose |
|---|---|
| `POST /api/subscriptions {name, events[], sink_mode}` | create (target auto = own sink URL) |
| `PATCH /api/subscriptions/{id} {sink_mode?, rotate_secret?}` | flip behaviour / rotate |
| `POST /api/publish {event_type, payload}` | emit through bus bridge |
| `GET /api/deliveries?subscription=` | timeline incl. attempts, latencies, signatures valid |
| `GET /api/sink/{name}/received` | what the sink actually got (raw headers/body) |
| `GET /api/dlq` / `POST /api/dlq/{id}/replay` | dead-letter inspection & replay |

## Console

Left: subscriptions list (mode toggle buttons inline, secret age + "rotate").
Center: delivery timeline for selected subscription — attempt rows with
status chip, backoff countdown, signature ✓/✗; DLQ section with Replay
buttons. Right: raw sink inspector showing received body + `X-Signature`
header; verify button recomputes HMAC client-side-free via API.

Seeded state: one healthy subscription (`order.paid`), one failing.

## Testing

Unit: sink store capture; mode switching. Integration: happy publish → one
attempt, signature verifies against subscription secret; failing mode →
retries with growing delays land in DLQ after max attempts; replay succeeds
once sink healed; consecutive-failure threshold disables subscription
(documented constant). Rotation: secret v2 accepted while grace active.
Console smoke.

## Non-goals

Outbound calls to real external URLs (documented how to point elsewhere);
retry-policy editing UI (fixed demo policy).
