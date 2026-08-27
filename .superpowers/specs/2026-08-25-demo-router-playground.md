# Spec: Router Playground

Slug `router-playground` · package `router_playground` · port 7077 (`ROUTER_PORT`)
Subsystems: `lexigram-ai-relay-gateway`, `lexigram-contracts` routing protocols, `lexigram-resilience`

## Story

A visitor types one prompt. The UI shows, live: which channel was selected and
why (cost class / capability / health), the fallback chain lighting up when the
primary fails, per-channel cost meters accumulating, quota bars draining, and
per-channel circuit breakers tripping open then half-open probing closed.
One screen answers "how does Lexigram survive a provider outage mid-request?"

## Architecture

- **FakeProviderCluster** — four in-process scripted providers implementing the
  gateway's upstream-call seam (no HTTP): `premium` (fast, $0.03/req),
  `economy` (slow 300 ms, $0.001), `flaky` (503s until fault toggled off), and
  `shadow` (down until toggled on). Same scripted-client pattern as
  `support-agent`.
- **ChannelRegistry** — channels wrap providers with: cost class, capability
  tags (`chat`, `json`, `long-context`), daily quota, and a per-channel
  resilience pipeline (breaker + timeout) from contract configs.
- **RouterService** — resolves the request through channel selection →
  admission → call → settlement; every decision appends to an in-memory
  `LedgerStore` (route decision + attempts + costs). Uses
  `LLMRouterProtocol`/`QuotaBackendProtocol`/`InferenceLoggerProtocol`
  contracts where they fit; recon task confirms exact seams before wiring.
- **FaultController** — flips provider health/scenario live (like rates).

## API

| Route | Purpose |
|---|---|
| `POST /api/chat {prompt, require:"json"|"long-context"?}` | run one routed completion |
| `GET /api/channels` | channel cards incl. breaker state, quota left, spend |
| `POST /api/fault/{provider}/{scenario}` | healthy / flaky / down |
| `GET /api/ledger?limit=50` | recent route decisions with attempt chains |

## Console

Left: prompt box + capability toggle. Center: decision card (chosen channel +
reason) and animated attempt chain (try → fail → next). Right: channel grid
with spend meters, quota bars, breaker dots. Footer: ledger table.

## Testing

Unit: selection prefers cheapest healthy capable channel; fallback order on
failure; breaker opens after threshold and skips channel; quota exhaustion
routes away. Integration: full chat flow under forced failover records ≥2
attempts in ledger. Console smoke: import + boot.

## Non-goals

Real network calls; streaming SSE; multi-tenant quotas; admin persistence
beyond process lifetime.
