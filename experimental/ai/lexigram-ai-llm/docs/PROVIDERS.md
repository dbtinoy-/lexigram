---
title: lexigram-ai-llm Providers
description: Supported providers, authentication, features, multi-provider routing, and custom provider setup.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Supported providers

`lexigram-ai-llm` provides built-in clients for the following providers:

| Provider | Client class | Auth method | Extra | Streaming | Thinking | Tools | Structured output |
|----------|-------------|-------------|-------|-----------|----------|-------|-------------------|
| OpenAI | `OpenAIClient` | `api_key` | `openai` | Yes | Via reasoning_effort | Yes | JSON mode / function calling |
| Anthropic | `AnthropicClient` | `api_key` | `anthropic` | Yes | Extended thinking | Yes | Tool use |
| Gemini | `GeminiClient` | `api_key` | `google-genai` | Yes | Native thinking | Yes | JSON mode |
| Ollama | `OllamaClient` | None | `ollama` | Yes | Via model | Yes | JSON mode |
| Groq | `GroqClient` | `api_key` | `groq` | Yes | Via model | Yes | JSON mode |
| Mistral | `MistralClient` | `api_key` | `mistralai` | Yes | — | Yes | JSON mode |
| Cohere | `CohereClient` | `api_key` | `cohere` | Yes | — | Yes | JSON mode |
| OpenRouter | `OpenRouterClient` | `api_key` | `openai` | Yes | Via model routing | Yes | JSON mode |
| Azure OpenAI | `AzureOpenAIClient` | `api_key` + endpoint | `openai` | Yes | reasoning_effort | Yes | JSON mode |
| AWS Bedrock | `BedrockClient` | AWS credentials | `boto3` | Yes | Via model | Yes | Tool use |
| Vertex AI | `VertexAIClient` | GCP credentials | `google-cloud-aiplatform` | Yes | Via model | Yes | JSON mode |
| Cloudflare Workers AI | `CloudflareWorkersAIClient` | `api_key` + account ID | `requests` | Yes | — | — | — |
| OpenAI-Compatible | `OpenAICompatibleClient` | `api_key` (optional) | `openai` | Yes | Via model | Yes | JSON mode |

## Per-provider details

### Authentication

API-key providers accept `SecretStr` via `ClientConfig`:

```python
from lexigram.ai.llm.config import ClientConfig
from lexigram.validation import SecretStr

config = ClientConfig(
    provider="openai",
    model="gpt-4o",
    api_key=SecretStr("sk-..."),
)
```

For providers using SDK credential chains (AWS Bedrock, Vertex AI), set credentials via standard environment variables (`AWS_PROFILE`, `GOOGLE_APPLICATION_CREDENTIALS`).

### Streaming

All providers return an `AsyncStream[StreamChunk, LLMError]` from `stream_chat()`:

```python
from lexigram.ai.llm.types import StreamChunk

async for chunk in client.stream_chat(messages):
    print(chunk.content, end="")
```

### Thinking/reasoning

Configure via `ThinkingConfig` in `ClientConfig`:

```python
from lexigram.contracts.ai.thinking import ThinkingConfig

config = ClientConfig(
    provider="anthropic",
    model="claude-3-7-sonnet-20250219",
    thinking=ThinkingConfig(budget_tokens=5000),
)
```

Supported providers: Anthropic (extended thinking), Gemini (native thinking), OpenAI (reasoning_effort).

### Tool/function calling

```python
from lexigram.ai.llm.types import ToolCall

result = await client.complete(messages, tools=[my_tool_definition])
if result.is_ok():
    for call in result.unwrap().tool_calls:
        print(f"Calling {call.function.name}")
```

### Structured output

```python
from lexigram.ai.llm.structured.extractor import JSONExtractor
from lexigram.ai.llm.structured.parser import StructuredOutputParser

parser = StructuredOutputParser(model="gpt-4o")
result = await parser.parse(messages, output_schema=MyModel)
```

## Multi-provider routing

`LLMRoutingProvider` (from `lexigram.ai.llm.di.routing_provider`) enables multi-provider dispatch via `ProviderRegistry`:

```python
from lexigram.ai.llm.registry.core import ProviderRegistry
from lexigram.ai.llm.selection.core import ModelSelector

registry = ProviderRegistry()
selector = ModelSelector(registry=registry)

# Route by criteria
model = selector.select(query, criteria=SelectionCriteria(min_capabilities={ModelCapabilities.STREAMING}))
```

The `ProviderRegistry` maps provider names to client instances. Routes can be cost-optimized, quality-optimized, or balanced via the selector strategies.

## Adding a custom provider

Register a client in the `ProviderRegistry`:

```python
from lexigram.ai.llm.registry.core import ProviderRegistry
from lexigram.contracts.ai import LLMClientProtocol

class MyCustomClient(LLMClientProtocol):
    async def complete(self, messages, **kwargs):
        ...
    def stream_chat(self, messages):
        ...

registry = ProviderRegistry()
await registry.register_provider("my_custom", MyCustomClient(), models=["my-model-v1"])
```

For full DI integration, subclass the provider pattern or configure via `LLMProvider` with a custom factory.

## Provider-specific config quirks

- **OpenAI Compatible**: Set `api_base` to the custom endpoint URL. Works with any OpenAI-compatible API (vLLM, LiteLLM, etc.).
- **Anthropic**: Extended thinking requires model `claude-3-7-sonnet-20250219` or later. `budget_tokens` controls the thinking budget.
- **Gemini**: The `google-genai` library must be installed. API key or ADC credentials.
- **AWS Bedrock**: Requires `boto3` and configured AWS credentials. Cross-region inference supported.
- **Ollama**: No `api_key` needed when running locally. Set `api_base` for remote instances.

## See also

- `LLMProvider` — DI registration for a single provider
- `LLMRoutingProvider` — multi-provider routing setup
- `ProviderRegistry` — register and query provider clients
- `ModelSelector` — cost/quality/balanced model selection
- `ClientConfig` — provider, model, auth, and feature config
