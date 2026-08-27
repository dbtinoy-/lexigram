# Spec: Flag Console

Slug `flag-console` · package `flag_console` · port 7086 (`FLAGS_PORT`)
Subsystems: `lexigram-features` (FlagManager, evaluation backends, variant flags, TTL cache, runtime overrides, audit log, decorator gates)

## Story

A checkout panel that visibly changes behaviour as you flip flags: currency
symbol switches (variant flag), a "wallet" payment method appears above 30 %
rollout for segment `beta`, and a kill switch instantly disables the experimental
flow mid-session. Every flip lands in an audit log with who/when/old→new; a
cache-bypass toggle demonstrates TTL caching vs fresh reads via latency chips.
The point: runtime gating that product people could drive — with receipts.

## Flags (seeded)

| Key | Type | Default | Notes |
|---|---|---|---|
| `checkout.currency` | variant | `usd` | variants: usd/eur/jpy |
| `checkout.wallet_pay` | boolean rollout | off | % of segment `beta`, sticky per user |
| `checkout.express_flow` | kill-switchable | on | gate protects `/api/checkout/express` |
| `search.fuzzy` | env-backend example | on | shows chained backend precedence |

## Architecture

- `FlagService` — wraps `FlagManager`; runtime overrides + audit entries;
  recon task pins manager API (override, evaluate, audit read).
- `GatedController` — demo endpoints guarded by decorator-based gates:
  express flow returns 403 FEATURE_DISABLED when killed.
- `CheckoutPreview` — pure function returning UI model given
  (user, flags) so tests assert rendering decisions directly.
- Simulated users: dropdown of seeded identities with segments
  (`beta`, `ga`) and stable hashing for sticky rollouts.

## API

| Route | Purpose |
|---|---|
| `GET /api/flags` | definitions + current effective values + source (default/env/override) |
| `PUT /api/flags/{key} {value?, variant?, percent?, enabled?}` | override (audited) |
| `DELETE /api/flags/{key}/override` | revert to default |
| `GET /api/audit?limit=` | change log old→new, actor, ts |
| `POST /api/preview {user_id}` | checkout panel model under current flags |
| `POST /api/checkout/express` | gate-protected endpoint |

## Console

Left: simulated-user picker. Center: live checkout preview card re-rendered on
every change. Right: flag rows — control per type (toggle / slider % / variant
select), source chip, cache indicator; below: audit log stream. Kill switch has
an oversized red toggle with confirm flash.

## Testing

Unit: preview function matrix across users×flag states; sticky rollout
stability (same user same result across evaluations); gate blocks when killed,
passes when enabled; audit entries recorded for every mutation. Integration:
override → evaluate → revert restores default; env backend precedence in
chained mode. Console smoke.

## Non-goals

Auth for the console (sandbox); multi-service flag sync; CSV import.
