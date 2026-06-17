# lexigram-ai-relay

Protocol-neutral conversion engine for the Lexigram AI relay — OpenAI Chat, Responses, Anthropic, and Gemini

---

## Overview

Protocol-neutral conversion engine for the Lexigram AI relay. Converts between OpenAI Chat Completions, OpenAI Responses, Anthropic Messages, and Gemini generateContent wire formats through one canonical intermediate representation.

The engine is synchronous and side-effect free: it never performs HTTP, channel selection, billing, or model selection. Host capabilities (Claude default `max_tokens`, Gemini safety thresholds, media resolution, model suffixes) are supplied as typed callbacks through `RelayConversionContext` from `lexigram-contracts`.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)

## Install

```bash
uv add lexigram-ai-relay
```

## Quick Start

```python
from lexigram import Application
from lexigram.ai.relay import RelayModule


async def main() -> None:
    async with Application.boot(modules=[RelayModule.configure()]) as app:
        # ... conversion engine available via the registry ...
        ...


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

Convert a payload directly with the built-in registry:

```python
from lexigram.ai.relay import RelayConverterRegistry, convert_request_by_id
from lexigram.contracts.ai.relay import OpenAIChatMessage, OpenAIChatRequest, RelayFormat
from lexigram.contracts.ai.relay.context import RelayConversionContext

registry = RelayConverterRegistry.with_defaults()
context = RelayConversionContext(default_max_tokens=lambda model: 8192)

result = convert_request_by_id(
    registry,
    payload=OpenAIChatRequest(
        model="gpt-4o",
        messages=[OpenAIChatMessage(role="user", content="hi")],
    ),
    converter_id="openai_chat_to_claude",
    context=context,
)
# Result[RelayConvertResult[RelayRequestPayload], RelayError]
```

> `RelayConversionContext` supplies host capabilities (Claude needs
> `default_max_tokens`); see the host-context reference below.

## Configuration

> **Zero-config usage:** Call `RelayModule.configure()` with no arguments. The engine needs no configuration; host capabilities are optional.

### Option 1 — Python (host context)

```python
from lexigram.contracts.ai.relay.context import RelayConversionContext

context = RelayConversionContext(
    default_max_tokens=lambda model: 8192,
    upstream_model="claude-3-5-sonnet",
    request_id="req_123",
)
```

### Host context reference

| Field | Default | Description |
|-------|---------|-------------|
| `options` | `RelayOptions()` | Cross-protocol adaptation options |
| `default_max_tokens` | `None` | Claude `max_tokens` fallback per model |
| `safety_setting` | `None` | Gemini safety-threshold lookup per category |
| `supports_image_generation` | `None` | Gemini image-generation capability lookup per model |
| `preserve_thinking_suffix` | `None` | Thinking-suffix bypass policy lookup |
| `media_resolver` | `None` | URL media resolution (data URIs decode locally) |
| `upstream_model` | `""` | Model name substituted when the payload carries none |
| `losses` | `[]` | Per-conversion loss records appended by mappers |
| `request_id` | `""` | Caller-supplied request id stamped on losses and errors |
| `channel_name` | `""` | Selected relay channel name for channel-aware adaptation |

All callbacks are nil-safe: mappers never guard against `None`.

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `RelayModule.configure()` | Conversion engine with the built-in converter routes |
| `RelayModule.stub()` | Same in-memory engine, suitable for unit tests |

## Key Features

- **Four wire formats**: OpenAI Chat Completions, OpenAI Responses, Anthropic Messages, Gemini generateContent
- **Canonical IR**: every conversion goes source → IR → target with route-quality reporting
- **Synchronous and side-effect free**: no HTTP, channel selection, billing, or model selection
- **Typed host callbacks**: `RelayConversionContext` supplies Claude, Gemini, and media capabilities
- **Result-typed conversions**: `Result[RelayConvertResult, RelayError]` with full error translation
- **Media handling**: local data-URI decoding and host-supplied URL resolution
- **Stream scaffolding**: per-format stream session state (stateful conversion not yet enabled)

## Testing

```python
async with Application.boot(modules=[RelayModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/relay/module.py` | `RelayModule.configure()` and `RelayModule.stub()` |
| `src/lexigram/ai/relay/engine.py` | `RelayConverterEngine` and `convert_*_via` / `convert_*_by_id` helpers |
| `src/lexigram/ai/relay/context.py` | Nil-safe `ConversionContext` over `RelayConversionContext` |
| `src/lexigram/ai/relay/mappers/` | `FormatMapper` base plus `openai_chat`, `openai_responses`, `claude`, `gemini` |
| `src/lexigram/ai/relay/stream/` | Per-format stream session scaffolds and state |
| `src/lexigram/ai/relay/registry.py` | `RelayConverterRegistry`, `Route`, `RouteSpec` |
| `src/lexigram/ai/relay/quality.py` | Conversion route-quality computation |
| `src/lexigram/ai/relay/media.py` | Data-URI decoding and URL media resolution |
| `src/lexigram/ai/relay/errors.py` | Error translation helpers |