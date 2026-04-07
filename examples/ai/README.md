# lexigram-example-ai

A reference application demonstrating Lexigram Framework's **AI pipeline capabilities**.

## What It Demonstrates

| Feature | File | Framework Packages |
|---------|------|--------------------|
| Multi-turn chat with history | `pipelines/chat_pipeline.py` | `lexigram-ai-llm` |
| RAG query (retrieve + generate) | `pipelines/rag_pipeline.py` | `lexigram-ai-rag`, `lexigram-vector` |
| Tool implementing `ToolProtocol` | `tools/summarise_tool.py` | `lexigram-ai-agents` |
| Conversation domain model | `domain/conversation.py` | `lexigram-contracts` |
| DI wiring for all AI services | `di/provider.py` | `lexigram` |

## Quick Start

```bash
# Start infrastructure (Qdrant vector store)
docker compose up -d

# Run the application
cd examples/ai
uv run python -m lexigram_example_ai.main
```

## Running Tests

```bash
# Unit tests (no infrastructure needed)
uv run pytest tests/unit/ -v

# Integration smoke tests
uv run pytest tests/integration/ -v

# All tests with coverage
uv run pytest --cov=lexigram_example_ai --cov-fail-under=80
```

## Architecture Overview

```
AIProvider (di/provider.py)
├── registers: AIConfig
├── registers: LLMClientProtocol  → stub in dev / real in prod
├── registers: EmbeddingClientProtocol → stub in dev / real in prod
├── registers: DocumentVectorStoreProtocol → in-memory or Qdrant
├── registers: ChatPipeline
├── registers: RAGPipeline
└── registers: SummariseTool

main.py
└── Application("lexigram-example-ai")
    └── AIProvider
```

## Key Lexigram Patterns Shown

### 1. `Result[T, E]` — AI pipeline outcomes
```python
async def run(self, request: ChatRequest) -> Result[ChatResponse, LLMError]:
    result = await self._llm.complete(messages)
    if result.is_err():
        return Err(result.unwrap_err())
    completion = result.unwrap()
    return Ok(ChatResponse(content=completion.content, model=completion.model))
```

### 2. Constructor Injection — Pipelines receive deps via `__init__`
```python
class ChatPipeline:
    def __init__(
        self,
        llm: LLMClientProtocol,
        token_counter: TokenCounterProtocol,
    ) -> None:
        self._llm = llm
        self._token_counter = token_counter
```

### 3. Protocol Boundaries — Swap backends without touching pipelines
```python
# In tests: inject FakeLLMClient
# In prod: inject OpenAI / Anthropic client via AIProvider
```

### 4. Provider Pattern — `AIProvider` wires everything
```python
class AIProvider(Provider):
    name = "ai"
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(LLMClientProtocol, _StubLLMClient())
        container.singleton(ChatPipeline, ChatPipeline(llm=..., token_counter=...))
        ...
```

### 5. Tool Protocol — Typed agent tool
```python
class SummariseTool:
    name = "summarise"
    description = "Summarise a block of text into a concise paragraph."

    async def execute(self, *, text: str, max_sentences: int = 3) -> str:
        result = await self._llm.complete(messages)
        ...
```

### 6. Conversation Domain Model — Rich entity with value objects
```python
conversation = Conversation.start(session_id="sess-1", title="Support chat")
conversation.add_message(role=MessageRole.USER, content="Hello")
conversation.add_message(role=MessageRole.ASSISTANT, content="Hi there!")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_LLM_DRIVER` | `stub` | LLM backend (`stub`, `openai`, `anthropic`) |
| `AI_LLM_MODEL` | `gpt-4o` | Default model identifier |
| `AI_LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `AI_LLM_MAX_TOKENS` | `2048` | Max output tokens |
| `AI_VECTOR_DRIVER` | `memory` | Vector store backend (`memory`, `qdrant`) |
| `AI_QDRANT_URL` | `http://localhost:6333` | Qdrant base URL |
| `AI_QDRANT_COLLECTION` | `lexigram_example` | Qdrant collection name |
| `AI_RAG_TOP_K` | `5` | Documents to retrieve per query |

## File Layout

```
src/lexigram_example_ai/
├── main.py                    # Boots Application + AIProvider
├── config.py                  # AIConfig (BaseConfig)
├── module.py                  # AIModule (application module)
├── domain/
│   └── conversation.py        # Conversation entity, Message value object
├── pipelines/
│   ├── chat_pipeline.py       # Multi-turn chat using LLMClientProtocol
│   └── rag_pipeline.py        # RAG query: embed → retrieve → generate
├── tools/
│   └── summarise_tool.py      # SummariseTool implementing ToolProtocol
└── di/
    └── provider.py            # AIProvider (DI wiring)
```
