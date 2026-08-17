# Give AI a pattern to follow

*Agents, LLMs, RAG, Skills — wired together, no glue code.*

[![PyPI version](https://img.shields.io/pypi/v/lexigram-ai?color=%2334D058&label=pypi%20package)](https://pypi.org/project/lexigram-ai/)
[![Python versions](https://img.shields.io/pypi/pyversions/lexigram-ai?color=%2334D058)](https://pypi.org/project/lexigram-ai/)
[![License](https://img.shields.io/pypi/l/lexigram-ai?color=%2334D058)](https://github.com/dbtinoy-/lexigram-ai-experimental/blob/main/LICENSE)

![Lexigram AI demo](docs/gifs/hero/lexigram-hero.gif)

`lexigram-ai` is the AI layer of the [lexigram framework](https://lexigram.dev): a thin coordinator that wires the lexigram-ai family — agents, LLMs, RAG, memory, skills, MCP, session, workers, observability, feedback, guard, governance, evaluation, prompt, relay — into the container through entry-point discovery. one install, one `Application.boot`, and the whole family is resolvable by contract. every backend is swappable: run it on your own infra or point it at an API.

- **wired, not glued.** agents, llms, rag, memory — one container, one boot call.
- **async, end to end.** the container, the modules, the controllers — concurrency-safe by construction.
- **contracts everywhere.** every package talks through protocols, so swapping an implementation never ripples.
- **local-first.** defaults point at any OpenAI-compatible server — Ollama, LM Studio, vLLM — hosted providers are a config change away.

→ full docs at [docs.lexigram.dev](https://docs.lexigram.dev)

## install

```bash
uv add "lexigram[ai,web]"    # framework + web + ai + server (what the example below uses)
uv add lexigram-ai           # just the coordinator
pip install "lexigram[ai,web]"
```

## 60 seconds, end to end

```python
from lexigram import Application
from lexigram.web import Controller, get, WebModule
from lexigram.web.server import run_server
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


app = Application()
app.add_modules(
    [
        # Local-first. To talk to a hosted provider instead, set
        # `provider="openai"` (or "anthropic", "groq", ...) and supply
        # the matching API key.
        LLMModule.configure(
            ClientConfig(
                provider="ollama",
                model="llama3.2",
                api_base="http://localhost:11434",
                api_key="ollama",
            )
        ),
        WebModule.configure(controllers=[ChatController]),
    ]
)

run_server(app, port=8000)
```

→ http://localhost:8000/chat?q=hello
> No API key needed if you're pointing at a local model. To talk to a hosted provider instead, set `provider="openai"` (or `"anthropic"`, `"groq"`, …), drop `api_base`, and supply the matching API key — or let `LLMModule.configure()` read the whole block from `LEX_AI_LLM__*` env vars.

what just happened?

- `Application.boot` assembled two modules — an LLM client and a web server — into one container and started them together.
- `LLMModule.configure(...)` declared a provider, a model, and an endpoint. No SDK, no per-provider code.
- `ChatController` resolved `LLMClientProtocol` by type from the container. Swap the provider; the controller never changes.

```text
lexigram-ai
├── umbrella        entry point · discovers subsystems
├── llm             provider-agnostic clients
├── agents          tools, react, and beyond
├── rag             chunkers, embedders, retrieval pipelines
├── memory          working, episodic, semantic stores
├── skills          versioned agent capabilities
├── session         conversation state and resumption
├── mcp             model-context-protocol clients
├── workers         background AI jobs
├── observability   tracing and metrics
├── feedback        quality loops
├── guard           input/output safety gates
├── governance      policy, audit, budgets
├── evaluation      evals and quality gates
├── prompt          versioned prompt templates
├── relay           protocol conversion engine
└── relay-gateway   HTTP gateway for relay
```

## what's in the box

the whole family lives in [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental) — experimental tier, API stability is not guaranteed between releases. same container, same contracts, same rules as the stable core.

- **`lexigram-ai`** — the coordinator (this package)
- **`lexigram-ai-llm`** — provider-agnostic clients for Ollama, OpenAI, Anthropic, Groq, Mistral, and more
- **`lexigram-ai-agents`** — tools, react, and beyond
- **`lexigram-ai-rag`** — chunkers, embedders, retrieval pipelines
- **`lexigram-ai-memory`** — working, episodic, semantic stores
- **`lexigram-ai-skills`** — versioned agent capabilities
- **`lexigram-ai-session`** — conversation state and resumption
- **`lexigram-ai-mcp`** — model-context-protocol clients
- **`lexigram-ai-workers`** — background AI jobs
- **`lexigram-ai-observability`** — tracing and metrics
- **`lexigram-ai-feedback`** — quality loops
- **`lexigram-ai-guard`** — input/output safety gates
- **`lexigram-ai-governance`** — policy, audit, budgets
- **`lexigram-ai-evaluation`** — evals and quality gates
- **`lexigram-ai-prompt`** — versioned prompt templates
- **`lexigram-ai-relay`** — protocol conversion engine
- **`lexigram-ai-relay-gateway`** — HTTP gateway for relay

## early on purpose

The AI layer is in 0.1 — which means you can still change it. APIs may shift before 1.0, so pin your versions, and tell us what feels wrong. Shaping a framework is more fun when it's still soft.

## pointers

- full docs → [docs.lexigram.dev](https://docs.lexigram.dev)
- the stable core → [lexigram](https://github.com/dbtinoy-/lexigram-dev)
- the AI family → [lexigram-ai-experimental](https://github.com/dbtinoy-/lexigram-ai-experimental)