# Give AI a pattern to follow

*Agents, LLMs, RAG, Skills — wired together, no glue code.*

[![PyPI version](https://img.shields.io/pypi/v/lexigram?color=%2334D058&label=pypi%20package)](https://pypi.org/project/lexigram/)
[![Python versions](https://img.shields.io/pypi/pyversions/lexigram?color=%2334D058)](https://pypi.org/project/lexigram/)
[![License](https://img.shields.io/pypi/l/lexigram?color=%2334D058)](https://github.com/dbtinoy-/lexigram/blob/main/LICENSE)

![Lexigram demo](docs/demos/hero/lexigram-hero.gif)

hey — wanna ship an AI app this weekend?

Lexigram is a python framework that hands you Agents, LLMs, RAG, Skills, and memory already wired up — no glue code, no "and then we add the queue," no 200-line config files. The full async backend is right there too: web, sql, cache, auth, queues, events — all wired through one container, all built around one rule. It's async-native, container-managed, and built so the same patterns that get you to a demo on Sunday still hold up when the weekend project turns into the company. Pick a few packages, boot the application, ship the thing.

- **wired, not glued.** agents, llms, rag, memory — one container, one boot call.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.
- **contracts everywhere.** every package talks through protocols, so swapping an implementation never ripples.
- **local-first.** defaults point at any OpenAI-compatible server — Ollama, LM Studio, vLLM — hosted providers are a config change away.

→ full docs at [docs.lexigram.dev](https://docs.lexigram.dev)

## install

```bash
uv add "lexigram[ai]"   # core + the AI family (agents, llms, rag, memory, ...)
pip install "lexigram[ai]"   # or with pip
```

```text
HOOK    agents · llms · rag · mcp · memory
CORE    web · sql · cache · auth · queue · events
TRUST   di · contracts · modules · async
```

## 60 seconds, end to end

```python
import asyncio
from lexigram import Application
from lexigram.web import Controller, get, WebModule
from lexigram.ai.llm import LLMModule, ClientConfig
from lexigram.contracts.ai import LLMClientProtocol, ChatMessage, Role


class ChatController(Controller):
    def __init__(self, llm: LLMClientProtocol):
        self.llm = llm

    @get("/chat")
    async def chat(self, q: str) -> dict:
        messages = [ChatMessage(role=Role.USER, content=q)]
        result = await self.llm.complete(messages)
        return {"reply": result.unwrap().content}


async def main():
    async with Application.boot(modules=[
        # Local-first. To talk to a hosted provider instead, set
        # `provider="openai"` (or "anthropic", "groq", ...) and supply
        # the matching API key.
        LLMModule.configure(ClientConfig(
            provider="ollama",
            model="llama3.2",
            api_base="http://localhost:11434/v1",
            api_key="ollama",
        )),
        WebModule.configure(controllers=[ChatController], port=8000),
    ]):
        await asyncio.Event().wait()


asyncio.run(main())
```

→ http://localhost:8000/chat?q=hello
> No API key needed if you're pointing at a local model. To talk to a hosted provider instead, set `provider="openai"` (or `"anthropic"`, `"groq"`, …), drop `api_base`, and supply the matching API key — or let `LLMModule.configure()` read the whole block from `LEX_AI_LLM__*` env vars.

what just happened?

- `Application.boot` assembled two modules — an LLM client and a web server — into one container and started them together.
- `LLMModule.configure(...)` declared a provider, a model, and an endpoint. No SDK, no per-provider code.
- `ChatController` resolved `LLMClientProtocol` by type from the container. Swap the provider; the controller never changes.

## what's in the box

this repo ships the main ecosystem — the core, the backend, the contracts:

- **`lexigram`** — the core, the container, the boot lifecycle
- **`lexigram-web`** — async routing and controllers
- **`lexigram-sql`** — sqlalchemy, already wired
- **`lexigram-cache`** — redis and in-memory, one contract
- **`lexigram-vector`** / **`lexigram-graph`** — storage for the ai layer
- plus auth, events, queue, tasks, http, resilience, storage, search, notification, monitor, webhook, tenancy, features, audit, graphql, nosql, workflow, and testing

the AI family — agents, llms, rag, memory, skills, mcp, session, workers, observability, feedback, and the guard / governance / evaluation / prompt / relay suite — lives in [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental). multimedia (tts, music, image, video, beat, interpolate, upscale) lives in [lexigram-multimedia-experimental](https://github.com/dbtinoy-/lexigram-multimedia-experimental). same modules, same container, same rules — their own repos and cadence.

the full list — including notification, queue, events, auth, observability, and more — lives in the [docs ecosystem](https://docs.lexigram.dev/ecosystem/).

## early on purpose

Lexigram is in 0.1 — which means you can still change it. APIs may shift before 1.0, so pin your versions, and tell us what feels wrong. Shaping a framework is more fun when it's still soft.

→ [github.com/dbtinoy-/lexigram/issues](https://github.com/dbtinoy-/lexigram/issues)

## why it grows with you

- **contracts.** every package talks through protocols, so swapping the implementation never ripples.
- **providers.** lifecycle and wiring live in one place, so boot order is explicit and tests are trivial.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.

## pointers

- full docs → [docs.lexigram.dev](https://docs.lexigram.dev)
- AI subsystems (experimental) → [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental)
- multimedia subsystems (experimental) → [lexigram-multimedia-experimental](https://github.com/dbtinoy-/lexigram-multimedia-experimental)
- skills for AI coding agents → [lexigram-skills](https://github.com/dbtinoy-/lexigram-framework-skills)
- contributing → [CONTRIBUTING.md](./CONTRIBUTING.md)
- security → [SECURITY.md](./SECURITY.md)
- license → [LICENSE](./LICENSE)

---

*made for people who like building things and keeping them buildable.*