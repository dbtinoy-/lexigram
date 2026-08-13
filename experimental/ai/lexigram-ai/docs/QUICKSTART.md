---
title: lexigram-ai Quickstart
description: Install `lexigram-ai`, configure providers, and make your first AI call.
---

:::note[Maturity]
Alpha (0.1.x) — public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-ai
# Or with pip
pip install lexigram-ai
```

`lexigram-ai` depends on `lexigram`, `lexigram-contracts`, `lexigram-ai-llm`, `lexigram-ai-rag`, `lexigram-ai-feedback`, and `lexigram-ai-observability`.

## Minimal wiring

```python
import asyncio
from lexigram import Application
from lexigram.ai.module import AIModule
from lexigram.ai.llm import ClientConfig


async def main() -> None:
    config = AIConfig(
        llm=ClientConfig(
            provider="openai",
            model="gpt-4o",
            api_key="sk-...",
        ),
    )

    async with Application.boot(
        name="ai-demo",
        modules=[AIModule.configure(config)],
    ) as app:
        # LLMClientProtocol is now injectable
        from lexigram.contracts.ai import LLMClientProtocol

        llm = await app.container.resolve(LLMClientProtocol)
        result = await llm.complete([{"role": "user", "content": "Say hello!"}])

        if result.is_ok():
            print(result.unwrap().content)
        else:
            print(f"Error: {result.unwrap_err()}")


asyncio.run(main())
```

## What you get

`AIModule.configure(config)` registers the **AIProvider** which wires:
- **LLM** — multi-provider client (OpenAI, Anthropic, Ollama, Groq, Mistral, …)
- **Vector** — vector store backends (optional, requires `lexigram-vector`)
- **RAG** — retrieval-augmented generation pipelines (optional)
- **Observability** — AI tracing, metrics, and health monitoring
- **Governance** — audit logging and policy enforcement (optional)

## Next steps

- [Guide](/packages/lexigram-ai/guide/) — mental model, core concepts, end-to-end workflows
- [Architecture](/packages/lexigram-ai/architecture/) — provider composition and entry-point discovery
- [Configuration](/packages/lexigram-ai/configuration/) — all config keys and env-var overrides
- [Ecosystem](/ecosystem/) — related AI packages
