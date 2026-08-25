# 🤖 support-agent — tool-calling ReAct agent (scripted LLM)

> A support-desk agent that answers customer questions with three tools.
> The agent loop is real; the model boundary is a deterministic scripted
> stub, so every run replays byte-for-byte.

## What it proves

- **Real ReAct loop** — THOUGHT/ACTION parsing through the framework's
  react strategy and `AgentExecutorImpl`
- **Container-injected tools** — `@tool` order lookup, refund policy math,
  KB search (schemas auto-generated from type hints)
- **Scripted model boundary** — `ScriptedLLM` pops pre-written completions;
  the LLM binding lands in `register()` because `AgentsProvider.boot()`
  hard-requires it
- **Failure act** — an unknown tool degrades to a failed tool-call record,
  never a crash

## Layout

House flat structure (`module.py` + `di/provider.py` + domain modules)
with auth-web's co-located `ui/` (`pages.py`, `views/`, `static/`) — the
frontend is plain HTML/JS/CSS with no build step.

## Run

```bash
PYTHONPATH=demos/support-agent/src uv run python -m support_agent
# → http://127.0.0.1:8082  (override: --port / SUPPORT_AGENT_PORT)
```

Pick a scenario button, ask a question, read the answer + trace table.

| Scenario | Shows |
|---|---|
| Happy path | one tool call, then the final answer |
| Multi-tool | lookup_order → calculate_refund in ordered sequence |
| Failure | unknown tool ⇒ failed record, run still completes |

## Tests

```bash
uv run pytest demos/support-agent/tests -q
```

