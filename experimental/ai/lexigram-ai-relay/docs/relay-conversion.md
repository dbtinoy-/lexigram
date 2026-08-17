# Relay protocol conversion

`lexigram-ai-relay` converts between four LLM wire formats through one
canonical intermediate representation (IR) defined in
`lexigram-contracts`:

| Source format              | Registry slug       | DTO key      |
| -------------------------- | ------------------- | ------------ |
| OpenAI Chat Completions    | `openai_chat`       | `OpenAIChatRequest` / `OpenAIChatResponse` |
| OpenAI Responses           | `openai_responses`  | `ResponsesRequest` / `ResponsesResponse`   |
| Anthropic Messages         | `claude`            | `ClaudeRequest` / `ClaudeResponse`         |
| Gemini generateContent     | `gemini`            | `GeminiRequest` / `GeminiResponse`         |

The engine is synchronous and side-effect free: no HTTP, channel
selection, billing, or model selection. Host capabilities are supplied
as typed callbacks through `RelayConversionContext`.

## Public usage pattern

```python
from lexigram.ai.relay import (
    RelayConverterRegistry,
    convert_request_by_id,
    convert_response_by_id,
)
from lexigram.contracts.ai.relay.dto import (
    OpenAIChatRequest,
    ClaudeRequest,
)

registry = RelayConverterRegistry.with_defaults()

# Convert a request openai_chat -> claude.
claude_payload = OpenAIChatRequest.from_dict(
    {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "hi"}],
    }
)
result = convert_request_by_id(
    registry, claude_payload, "openai_chat_to_claude"
)
claude_wire = result.unwrap().value.to_dict()  # ClaudeRequest.to_dict()

# Convert a response claude -> openai_chat.
from lexigram.contracts.ai.relay.dto import ClaudeResponse

claude_response = ClaudeResponse.from_dict(
    {
        "id": "msg_1",
        "model": "claude-3-5-sonnet",
        "role": "assistant",
        "content": [{"type": "text", "text": "hello"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 5, "output_tokens": 3},
    }
)
result = convert_response_by_id(
    registry, claude_response, "claude_to_openai_chat"
)
openai_wire = result.unwrap().value.to_dict()
```

Converter ids are stable `"<source>_to_<target>"` strings using the
registry slugs above. Results are `Result[RelayConvertResult, RelayError]`;
unwrap to reach the result carrying `.value` (the target DTO), `.losses`,
`.warnings`, `.quality`, and `.steps`; use `.value.to_dict()` for the wire
payload.

Host context (Claude default `max_tokens`, Gemini safety thresholds,
media resolution) is supplied per conversion:

```python
from lexigram.contracts.ai.relay import RelayConversionContext

ctx = RelayConversionContext(
    default_max_tokens=lambda model: 4096,   # Claude max_tokens fallback
    safety_setting=lambda category: "OFF",   # Gemini safety thresholds
    media_resolver=my_resolver,              # MediaResolverProtocol
)
result = convert_request_by_id(registry, payload, route, context=ctx)
```

## Behavior notes

- Unknown upstream fields are preserved in `passthrough` and re-emitted
  verbatim by `to_dict()`, so gateways can forward without data loss.
- `max_tokens` is dropped converting **openai_responses → openai_chat**
  (the Chat API owns it); it survives every other hop.
- Reasoning / thinking text survives only via the Responses hop
  (`summary_text`); it is dropped when converting into Claude or Gemini
  targets.
- Claude ↔ Gemini request hops drop multimodal user text: the
  `generateContent` ↔ Anthropic content block shapes do not overlap.
- Usage is normalized (`RelayUsage`); token totals derive at
  serialization time, so converted DTOs always expose a total.
- `stream` is always serialized (`False` when absent) so request
  round-trips are stable across all routes.
