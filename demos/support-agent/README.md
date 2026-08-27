# Support Agent Demo

> Module name: `support_agent` — run with `PYTHONPATH=demos/support-agent/src uv run python -m support_agent`

Demonstrates the **AI agents subsystem** from `lexigram-ai-agents` through a
browser: pick a scripted scenario, watch the ReAct agent reason step-by-step,
call tools (order lookup, refund calculation, KB search), and see the traced
response with token counts and timing.

Fully offline against a scripted LLM — no API keys, no network. The agent
runs for real (tools get called, the strategy parser drives the loop) while
model output stays byte-stable across runs.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Module pattern | `AgentsModule`, `WebModule` | Add your own modules |
| Provider lifecycle | `di/provider.py` | Replace with your registrations |
| Result<T,E> pattern | `controllers/api.py` | Return Result from handlers |
| Agent builder | `services/support_service.py` | Build agents with `AgentBuilder` |
| `@tool` decorator | `tools.py` | Wrap functions as agent tools |
| ReAct strategy | `repository/scenarios.py` | Scripted completions drive the loop |
| Scripted LLM | `repository/scripted_llm.py` | Deterministic stand-in for `LLMClientProtocol` |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Agent assembly | `services/support_service.py` | `AgentBuilder`, `AgentProtocol`, `with_strategy("react")` |
| Tool registration | `tools.py` | `@tool(description=...)`, `Registry[str, Any]` |
| Scenario scripts | `repository/scenarios.py` | `Scenario` dataclass, `Registry[str, Scenario]` |
| Scripted LLM | `repository/scripted_llm.py` | `LLMClientProtocol` stand-in, FIFO queue |
| DI wiring | `di/provider.py` | `Provider`, `register()` / `boot()` lifecycle |
| Module wiring | `app.py` | `AgentsModule.configure(...)`, `WebModule.configure(...)` |

## Scenarios

Each scenario is a list of pre-written ReAct completions that the scripted
LLM pops from a FIFO queue:

| Scenario | What happens |
|----------|-------------|
| `happy` | Single tool call — looks up order A-100, returns tracking info |
| `multi_tool` | Two tool calls — looks up order A-102, computes half refund |
| `failure` | Wrong tool name — agent degrades gracefully, answers directly |

## Run it

From this demo's root (so `application.yaml` is discovered):

```bash
cd demos/support-agent
PYTHONPATH=src uv run python -m support_agent
```

Open http://127.0.0.1:8082, pick a scenario, type a question, and watch
the agent reason step-by-step. Override the port without touching yaml:
`LEX_WEB__SERVER__PORT=9000`.

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/support_agent/app.py` | ⭐ Composition root: modules → providers |
| 2 | `src/support_agent/main.py` | Lifecycle: `Application.start/stop`, graceful shutdown |
| 3 | `src/support_agent/di/provider.py` | `register()` (bind) vs `boot()` (initialize); DI patterns |
| 4 | `src/support_agent/services/support_service.py` | Agent builder + facade; `Result` error handling |
| 5 | `src/support_agent/controllers/api.py` | Result-returning handlers → auto HTTP status mapping |
| 6 | `src/support_agent/tools.py` | `@tool` decorator; plain async functions as agent tools |
| 7 | `src/support_agent/repository/scenarios.py` | Scripted completions; `Registry` pattern |
| 8 | `src/support_agent/repository/scripted_llm.py` | `LLMClientProtocol` stand-in; FIFO queue |
| 9 | `src/support_agent/ui/pages.py` | Page controllers: serve HTML/assets only, no logic |

```
demos/support-agent/
├── src/support_agent/
│   ├── app.py                 # ⭐ composition root (start here)
│   ├── main.py                # entry point / lifecycle
│   ├── __main__.py            # python -m support_agent
│   ├── di/
│   │   └── provider.py        # DI wiring + boot() assembly
│   ├── services/
│   │   └── support_service.py # AgentBuilder + SupportAgent facade
│   ├── controllers/
│   │   └── api.py             # JSON API: tools + ask
│   ├── repository/
│   │   ├── scenarios.py       # Scripted ReAct completions
│   │   ├── scripted_llm.py    # LLMClientProtocol stand-in
│   │   └── fixtures.py        # Orders + KB data
│   ├── tools.py               # @tool functions: lookup, refund, search
│   └── ui/                    # pages controller + views/ + static/
├── application.yaml           # web section (LEX_* overrides win)
└── tests/                     # e2e + unit tests
```

## Tests

```bash
uv run pytest demos/support-agent/tests -q
```

Covers: tool registration, tool behavior, scenario registry, agent facade,
end-to-end API calls (happy, multi-tool, failure, unknown scenario, blank
question, byte-stability), and page/static serving.
