# Demo Spec — `support-agent` (reason: tool-calling agent, web UI)

**Date:** 2026-08-22 (v5: reconciled UI to auth-web pattern verbatim)
**Status:** Approved direction — pending review
**Showcases:** `lexigram-ai-agents` — ReAct loop over container-registered tools with a scripted LLM boundary.
**Portfolio position:** First AI demo — answers *"can it reason and act?"*
**Structure rationale:** Single-module demo ⇒ flat package in the house variant of Pattern 2 (`module.py` root + `di/provider.py`, matching all five existing demos). UI present ⇒ auth-web pattern verbatim: `src/<pkg>/ui/pages.py` (single static-serving controller beside its assets), `views/`, `static/`.

---

## 1. Scenario

A support-desk agent answers customer questions using three tools. The LLM
is a **scripted stub**: a FIFO queue of pre-written ReAct completions
(`THOUGHT:` / `ACTION:` / `ACTION_INPUT:` / `FINAL_ANSWER:` lines). The
agent loop, strategy parsing, tool dispatch, and trace accounting run for
real through the framework's executor — only the model boundary is
deterministic.

The browser console offers three scenario buttons mapping to act scripts
(happy path, multi-tool, failure). Picking one and asking a question loads
the matching script into `ScriptedLLM`, runs the agent, and renders the
answer plus the reasoning trace.

## 2. Layout

```
demos/support-agent/
├── conftest.py                        # sys.path shim (src/) + app/client httpx fixtures
├── README.md
└── src/support_agent/
    ├── __init__.py                    # docstring only
    ├── main.py                        # python -m support_agent (--port / SUPPORT_AGENT_PORT)
    ├── module.py                      # @module SupportAgentModule — composition point
    ├── llm.py                         # ScriptedLLM + EmptyScriptError
    ├── scripts.py                     # act scripts + SCENARIOS registry (+ Scenario dataclass)
    ├── fixtures.py                    # ORDERS / KB seeds
    ├── tools.py                       # lookup_order / calculate_refund / search_kb (@tool)
    ├── agent_service.py               # build_support_agent() + SupportAgent facade
    ├── di/
    │   └── provider.py                # AgentSupportProvider (internal wiring)
    ├── controllers/
    │   ├── __init__.py
    │   └── api.py                     # AgentApiController — JSON logic only
    └── ui/                            # auth-web pattern: assets + static routes co-located
        ├── __init__.py                # docstring only
        ├── pages.py                   # ConsolePageController — FileResponse only
        ├── views/
        │   └── console.html           # agent console view
        └── static/
            ├── app.js                 # fetch client, trace rendering
            └── style.css
tests/
├── __init__.py
├── test_scripted_llm.py
├── test_tools.py
├── test_agent.py                      # builder/facade unit level
├── test_pages.py                      # page/static route smoke
└── test_api.py                        # scenarios end-to-end over HTTP
```

## 3. Module wiring

```python
# src/support_agent/module.py
@module()
class SupportAgentModule(Module):
    """Support-desk ReAct agent with a scripted LLM and web console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = port if port is not None else int(
            os.environ.get("SUPPORT_AGENT_PORT", "8082")
        )
        return DynamicModule(
            module=cls,
            imports=[
                AgentsModule.configure(AgentConfig(max_iterations=5)),
                WebModule.configure(
                    controllers=[AgentApiController, ConsolePageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[AgentSupportProvider],
            exports=[SupportAgent],
        )
```

Exports the concrete `SupportAgent` facade — same convention as
`OrdersApi` in event-driven-orders; no protocol indirection in a
single-module demo. Import paths: `from support_agent.module import …`,
`from support_agent.ui.pages import ConsolePageController`.

### Provider phases (`di/provider.py`)

- **`register()`**: binds `ScriptedLLM` singleton instance **and** under
  `LLMClientProtocol` (**required before boot** — `AgentsProvider.boot()`
  resolves it at its di/provider.py:136); lazy factory for the facade.
- **`boot()`**: resolves `AgentExecutorProtocol`, builds the agent via
  `AgentBuilder(...).with_strategy("react")`, instantiates `SupportAgent`.

Controllers receive constructor injection from the container against
concrete types (`AgentApiController(scripted: ScriptedLLM,
support: SupportAgent)`).

## 4. Components

| Component | Implementation |
|---|---|
| `llm.py` | `ScriptedLLM.complete(...) -> Result[ScriptedCompletion, …]` FIFO pops; `EmptyScriptError` on drain (demo bug, not domain failure); protocol stubs raise `NotImplementedError`. Pattern: agents' fakes (`tests/unit/strategies/test_function_calling.py:20`) |
| `scripts.py` | `Scenario(key, label, script)` frozen dataclass + `SCENARIOS: dict[str, Scenario]` keyed `"happy"` / `"multi_tool"` / `"failure"` — registry dispatch, no if/elif |
| `tools.py` | `@tool` pure functions — order dict lookup; refund tiers ≤7d full / ≤30d 50% / else none; KB keyword search over ≥6 snippets |
| `agent_service.py` | Builder assembly + `SupportAgent.ask(question) -> Result[AgentResponse, AgentError]`, keeps `last_response` |
| `api.py` | `GET /api/tools` → names/descriptions; `POST /api/ask` `{question, scenario}` → `{answer, steps[], tool_calls[], total_tokens, duration_ms}`; unknown scenario ⇒ 400 |
| `ui/pages.py` | `/` serves `views/console.html`; `/static/app.js`, `/static/style.css` — FileResponse only, `UI_ROOT = Path(__file__).parent` |

## 5. Request flow

Browser → `POST /api/ask {"question", "scenario"}` → controller looks up
scenario → `scripted.load(scenario.script)` → `support.ask(question)` →
ReAct executes real tools → response serialized with trace rows → JS
renders answer + trace table (step#, thought, action, tool outcome,
tokens, duration).

## 6. Error handling

- `Result[...]` unwrapped only after `is_ok()`; agent errors ⇒ JSON error
  body (500-family), never swallowed.
- Unknown scenario ⇒ 400 before any run; empty question ⇒ 400.
- `EmptyScriptError` propagates (misconfigured act = demo bug).

## 7. Tests

- `test_scripted_llm.py` — FIFO pops, usage payload, `load()` replace,
  drained-queue raise.
- `test_tools.py` — tool contracts incl. tier boundaries (7/8/30/31), KB
  ranking, `SUPPORT_TOOLS` surface.
- `test_agent.py` — builder assertions; facade records `last_response`;
  executor exceptions propagate (infrastructure).
- `test_pages.py` — `/` HTML markers incl. scenario buttons;
  `/static/*` content types.
- `test_api.py` — tools listing; each scenario end-to-end (exact message
  equality, ordered tool calls, failure act yields `succeeded is False` +
  `"Unknown tool"` per react.py:398-405); unknown scenario → 400;
  byte-stability across two runs (duration excluded).

## 8. Integration

- Makefile:114-115 — append `demos/support-agent/tests` /
  `demos/support-agent`.
- `demos/README.md` — section + run command
  (`PYTHONPATH=demos/support-agent/src uv run python -m support_agent`, :8082).
- Root pyproject unchanged (`demos` excluded from aggregate pytest run,
  norecursedirs :159; ruff per-file-ignores cover `demos/**` :568).

## 9. Acceptance criteria

- [ ] Server boots offline and serves the console on :8082 from the
      standalone `ui/` folder.
- [ ] All three scenarios replay byte-stable via the API.
- [ ] `make check-demos` green with new entries.
- [ ] ruff/format clean; no file >500 LOC; changes confined to
      `demos/**` + `Makefile`.
- [ ] Own commit(s) including tests (`✨ feat(demos): …` / `✅ test(demos): …`).

## 10. Gotchas

- LLM binding must happen in `register()` (required resolve during
  `AgentsProvider.boot`).
- Marker lines must match ReAct's template exactly
  (strategies/react.py:53-81).
- The `LLMClientProtocol` binding key must be the exact class object
  imported from `lexigram.contracts.ai.llm` — same token identity
  `AgentsProvider.boot()` resolves.
- Duplicate tool names are rejected by the registry.
- `enable_csrf=False` matches auth-web precedent (local plain JSON posts).
