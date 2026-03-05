# Host integration guide — `lexigram-ai-relay-gateway`

This guide shows a host application how to (a) build `RelayGatewayConfig`
dynamically from its own configuration store and (b) inject real per-channel
credentials into every upstream call. The gateway package itself never
stores or logs a credential value — it only forwards opaque headers a host
chose to inject.

## 1. Building `RelayGatewayConfig` from your own store

`RelayGatewayConfig` is a frozen dataclass. It is *not* loaded from a file
by the gateway; the host constructs it and passes it to the provider at
construction time:

```python
import asyncio
from lexigram.ai.relay.gateway import RelayGatewayConfig, RelayGatewayProvider
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat


async def build_config_from_store() -> RelayGatewayConfig:
    rows = await settings_db.fetch("SELECT name, base_url, models FROM channels")
    channels = tuple(
        RelayChannel(
            name=row.name,
            upstream_base_url=row.base_url,
            target_format=RelayFormat.OPENAI_CHAT,
            models=tuple(row.models),
        )
        for row in rows
    )
    return RelayGatewayConfig(
        channels=channels,
        model_suffix={"primary": ":prod"},
        provider_options={"openai": {"organization": "acme"}},
    )


async def main() -> None:
    config = await build_config_from_store()
    provider = RelayGatewayProvider(config=config, http_client=my_http_client)
    ...
```

Because `RelayGatewayConfig` is frozen, a settings change means **rebuilding
the whole config and re-registering the provider** (process restart, or an
explicit re-registration in the container) — never mutating it in place.

The one thing that already supports live mutation without a rebuild is
`RelayChannelRegistry.set_runtime_enabled(channel, enabled)` — enable/disable
only. Use it (through `RelayControlsService` or directly on the registry)
for operational toggles; use a config rebuild for structural changes
(URLs, models, suffixes).

## 2. Injecting real per-channel credentials

The gateway resolves each outbound request with `channel_name` set to the
selected channel's name and forwards it to the injected
`HTTPClientProtocol` as the `channel_name` kwarg. A host wires credential
injection by wrapping its real HTTP client with `CredentialInjectingHTTPClient`
and implementing `RelayChannelCredentialProvider`:

```python
from collections.abc import Mapping

from lexigram.ai.relay.gateway import (
    CredentialInjectingHTTPClient,
    RelayChannelCredentialProvider,
)
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat


class StoreBackedCredentialProvider(RelayChannelCredentialProvider):
    """Resolve per-channel credential headers from the host's store."""

    async def headers_for(self, channel_name: str) -> Mapping[str, str]:
        row = await secrets_db.fetchone(
            "SELECT api_key FROM channel_credentials WHERE name = $1",
            channel_name,
        )
        if row is None:
            return {}
        return {"authorization": f"Bearer {row.api_key}"}
```

Then wrap the client the gateway will use, and pass the wrapped client as
`RelayGatewayProvider(http_client=wrapped, ...)`:

```python
wrapped = CredentialInjectingHTTPClient(
    wrapped=my_http_client,          # e.g. lexigram-http's HTTPClient
    provider=StoreBackedCredentialProvider(),
)

provider = RelayGatewayProvider(config=config, http_client=wrapped)
```

The decorator pops `channel_name` from the call, merges the provider's
headers under the caller-supplied `headers` (provider headers win on key
collision), and delegates. A deployment that registers no credential
provider keeps today's behavior exactly: `NullChannelCredentialProvider`
returns no headers and calls pass through unchanged.

## 3. Compatibility caveat for custom HTTP clients

`HTTPClientProtocol.request(method, url, **kwargs)` accepts arbitrary
kwargs, so most implementations work unchanged. The gateway now always
passes `channel_name` on every upstream call. A custom implementation
with a keyword-only signature that **rejects unrecognized kwargs** must
either:

- add `channel_name: str = ""` to its `request()` signature, or
- accept `**kwargs` and ignore the key.

This includes wrapping clients that forward `**kwargs` to a lower-level
library (e.g. `lexigram-http`'s `HTTPClient`, which forwards kwargs to
`aiohttp`): the `CredentialInjectingHTTPClient` decorator consumes
`channel_name` before delegating, which is why hosts should keep the
decorator (or an equivalent stripping wrapper) in the path.
