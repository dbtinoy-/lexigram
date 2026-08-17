# lexigram-ai-relay-gateway

Protocol-facing relay gateway for the Lexigram AI relay — channel selection, orchestration, upstream I/O, and SSE handling

---

## Overview

Protocol-facing relay gateway for the Lexigram AI relay. Composes the gateway service from a channel registry, payload codec, upstream HTTP adapter, and the conversion engine, and exposes it behind `RelayGatewayProtocol` through `RelayGatewayModule` / `RelayGatewayProvider`.

One request is orchestrated end to end: authorization, channel selection, billing admission, request conversion, the protected upstream call, response conversion, billing settlement, and result metadata assembly. Streaming requests run the same preflight and then consume the upstream SSE stream lazily.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-ai-relay-gateway
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.relay.gateway import RelayGatewayConfig, RelayGatewayModule


@module(
    imports=[
        RelayGatewayModule.configure(
            RelayGatewayConfig.from_mapping(
                {
                    "channels": [
                        {
                            "name": "primary",
                            "upstream_base_url": "https://api.anthropic.com",
                            "target_format": "CLAUDE",
                            "models": ["claude-3-5-sonnet"],
                        }
                    ],
                }
            )
        )
    ]
)
class AppModule(Module):
    pass


async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

The gateway registers its inbound routes automatically through the `lexigram.web.contributors` entry point; bind it through a web-enabled `Application` to serve `/v1/chat/completions`, `/v1/responses`, `/v1/messages`, and the Gemini `/v1beta` surface.

## Configuration

> **Explicit-only configuration:** the gateway is not bound to a `LexigramConfig` section — it declares no `config_key` / `config_model` and reads no environment variables. Configuration is supplied to `RelayGatewayModule.configure()` as a `RelayGatewayConfig`.

### Option 1 — Python

```python
from lexigram.ai.relay.gateway import RelayGatewayConfig

config = RelayGatewayConfig.from_mapping(
    {
        "channels": [...],
        "auto_test_channels": True,
        "auto_test_interval_seconds": 300,
        "require_auth": True,
    }
)
```

When a host binds a `RelayChannelStoreProtocol`, the `DurableChannelLoader` reconciles every durable row over the static table by name at boot; an empty store leaves the static table untouched.

### Config reference

| Field | Default | Description |
|-------|---------|-------------|
| `channels` | `()` | Ordered channel table (name, upstream URL, target format, models) |
| `model_suffix` | `{}` | Channel-name to outbound model-suffix map (e.g. `":thinking"`) |
| `provider_options` | `{}` | Channel-name to provider options merged at conversion time |
| `auto_test_channels` | `False` | Background sweep probing channels, disabling failures |
| `auto_test_interval_seconds` | `600` | Delay between auto-test sweeps |
| `max_upstream_retries` | `0` | Retries across other channels after a retryable upstream failure |
| `load_balancing` | `"deterministic"` | `"deterministic"` or `"weighted"` channel tie-breaking |
| `job_ttl_seconds` | `3600` | Eviction age for job-relay records on next poll |
| `require_auth` | `False` | Require a bound `RelayAuthVerifierProtocol` on relay routes |
| `rate_limits` | `{}` | Per-model `{"max", "window_seconds"}` budgets |
| `auto_disable_on_failures` | `False` | Take a channel out of service on consecutive failures |
| `failover_failure_threshold` | `3` | Consecutive failures that disable a channel |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `RelayGatewayModule.configure(config=None)` | Gateway with the built-in relay routes; empty config = no channels |

## Key Features

- **Inbound relay routes**: OpenAI Chat (`/v1/chat/completions`), OpenAI Responses (`/v1/responses`), Anthropic (`/v1/messages`), Gemini (`/v1beta/models/{model}:generateContent`) plus model list/detail surfaces
- **Channel selection**: deterministic priority + weight resolution over a runtime override table, with weighted load balancing
- **Full request lifecycle**: auth, channel selection, billing admission, conversion, upstream call, settlement, metadata
- **SSE streaming**: lazy upstream stream consumption through a stream session; billing settles exactly once
- **Credential injection**: per-channel credential providers behind an injecting HTTP client
- **Passthrough routes**: `/v1/embeddings`, `/v1/rerank`, `/v1/moderations`, `/v1/audio/*`, `/v1/images/*`
- **Job relay**: submit-then-poll routes (`POST /v1/videos`, `GET /v1/videos/{job_id}`) with eviction TTL
- **Operations**: channel health probing, background auto-tester, route metrics, operator controls, failover tracking
- **Governance**: per-model rate limiting and an optional auth guard on inbound routes
- **Durable channels**: store-backed channel reconciliation at boot via `DurableChannelLoader`
- **Admin surface**: channel CRUD pages and actions for the admin UI

## Testing

```python
async with Application.boot(modules=[RelayGatewayModule.configure()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/relay/gateway/module.py` | `RelayGatewayModule.configure()` |
| `src/lexigram/ai/relay/gateway/config.py` | `RelayGatewayConfig` and channel-table validation |
| `src/lexigram/ai/relay/gateway/channels.py` | `RelayChannelRegistry` — deterministic channel selection |
| `src/lexigram/ai/relay/gateway/service.py` | `RelayGatewayService` — request lifecycle orchestration |
| `src/lexigram/ai/relay/gateway/upstream.py` | `HTTPUpstreamAdapter` and upstream I/O |
| `src/lexigram/ai/relay/gateway/codec.py` | `RelayPayloadCodec` — payload encode/decode |
| `src/lexigram/ai/relay/gateway/stream.py` | `relay_stream` and `UpstreamEventParser` for SSE |
| `src/lexigram/ai/relay/gateway/loader.py` | `DurableChannelLoader` — store reconciliation at boot |
| `src/lexigram/ai/relay/gateway/operations/` | Health, metrics, controls, auto-test, failover, stream registry |
| `src/lexigram/ai/relay/gateway/web/` | Relay routes, SSE, audio and image endpoints |
| `src/lexigram/ai/relay/gateway/ratelimit.py` | Per-model rate-limit guard (Redis-backed variant alongside) |
| `src/lexigram/ai/relay/gateway/admin/` | Admin pages and actions for channel CRUD |