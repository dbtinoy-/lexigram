# Support-Agent Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `demos/support-agent/` — an offline, deterministic ReAct agent demo (scripted LLM) with a vanilla-JS web console, in the house Pattern-2 flat shape with auth-web's co-located `ui/` (`pages.py` + `views/` + `static/`).

**Architecture:** Flat package `src/support_agent/` — root `@module SupportAgentModule` imports `AgentsModule` + `WebModule`; `di/provider.py` binds a scripted `LLMClientProtocol` in the register phase (required by `AgentsProvider.boot()`); `controllers/api.py` serves JSON; `ui/pages.py` serves static assets only, resolving files relative to itself.

**Tech Stack:** Python 3.11+, Lexigram workspace packages (`lexigram-ai-agents`, `lexigram-web`), Starlette via `lexigram.web`, httpx ASGI testing, pytest-asyncio, ruff (root config).

**Spec:** `.superpowers/specs/2026-08-22-support-agent-design.md` (v4) — read it first; this plan argues from it.

## Global Constraints

- Offline only: no network, no API keys, no live models; byte-stable output.
- Absolute imports; import modules via their package surfaces.
- Google docstrings, full type annotations, no `Any` on injected deps.
- Every file <500 LOC.
- **Single sys.path shim:** conftest inserts `demos/support-agent/src`
  only (auth-web pattern — `ui` lives inside the package).
- Commits: emoji conventional format, pathspec commits only — always
  `git commit <paths> -m "…"`. Before each commit run `git status --short`;
  stage+commit in one chain; foreign staged files belong to other lanes.
- Scoped test runs: `uv run pytest demos/support-agent/tests -q`.
- Final gates: `uv run ruff check demos/support-agent && uv run ruff format --check demos/support-agent`.

---

### Task 1: Scaffold + ScriptedLLM

**Files:**
- Create: `demos/support-agent/conftest.py`
- Create: `demos/support-agent/src/support_agent/__init__.py`
- Create: `demos/support-agent/tests/__init__.py` (empty)
- Create: `demos/support-agent/src/support_agent/llm.py`
- Test: `demos/support-agent/tests/test_scripted_llm.py`

**Interfaces:**
- Consumes: `Ok` from `lexigram.result`.
- Produces: `ScriptedUsage(prompt_tokens=12, completion_tokens=24, total_tokens=36)` frozen defaults; `ScriptedCompletion(content, model="scripted", usage)` frozen dataclass; `EmptyScriptError(RuntimeError)`; `ScriptedLLM(script=None)` with `load(lines) -> None`, `remaining -> int`, `async complete(messages, **kw) -> Result[ScriptedCompletion, Exception]`; stubs `stream_chat`, `health_check`, `close`.

- [ ] **Step 1: Write conftest and skeletons**

`demos/support-agent/conftest.py`:
```python
"""Pytest bootstrap for the support-agent demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import
``support_agent`` without installing (auth-web pattern):

    uv run pytest demos/support-agent/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
```

Docstring-only `__init__.py` files at:
`src/support_agent/__init__.py` (`"""Support-desk ReAct agent demo."""`),
`tests/__init__.py` (empty).

- [ ] **Step 2: Write the failing test**

`demos/support-agent/tests/test_scripted_llm.py`:
```python
"""Tests for the scripted LLM boundary."""

from __future__ import annotations

import pytest

from lexigram.result import Ok

from support_agent.llm import EmptyScriptError, ScriptedLLM


class TestScriptedLLM:
    @pytest.mark.asyncio
    async def test_pops_entries_in_fifo_order(self) -> None:
        llm = ScriptedLLM(["first", "second"])

        first = await llm.complete([{"role": "user", "content": "hi"}])
        second = await llm.complete([{"role": "user", "content": "hi"}])

        assert isinstance(first, Ok)
        assert first.unwrap().content == "first"
        assert second.unwrap().content == "second"
        assert llm.remaining == 0

    @pytest.mark.asyncio
    async def test_empty_queue_raises_empty_script_error(self) -> None:
        llm = ScriptedLLM([])

        with pytest.raises(EmptyScriptError):
            await llm.complete([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_load_replaces_script(self) -> None:
        llm = ScriptedLLM(["stale"])
        llm.load(["fresh"])
        result = await llm.complete([])

        assert result.unwrap().content == "fresh"

    @pytest.mark.asyncio
    async def test_completion_carries_deterministic_usage(self) -> None:
        llm = ScriptedLLM(["FINAL_ANSWER: y"])
        result = await llm.complete([])

        completion = result.unwrap()
        assert completion.usage.total_tokens == 36
        assert completion.model == "scripted"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest demos/support-agent/tests/test_scripted_llm.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'support_agent.llm'`)

- [ ] **Step 4: Implement llm.py**

`demos/support-agent/src/support_agent/llm.py`:
```python
"""Scripted LLM client — deterministic stand-in for ``LLMClientProtocol``.

ReAct drives reasoning through text markers inside completion strings.
This client pops pre-written completions from a FIFO queue so the agent
loop runs for real while model output stays byte-stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.result import Ok, Result


@dataclass(frozen=True)
class ScriptedUsage:
    """Token accounting reported with each scripted completion."""

    prompt_tokens: int = 12
    completion_tokens: int = 24
    total_tokens: int = 36


@dataclass(frozen=True)
class ScriptedCompletion:
    """Minimal completion carrying the fields strategies consume."""

    content: str
    model: str = "scripted"
    usage: ScriptedUsage = field(default_factory=ScriptedUsage)


class EmptyScriptError(RuntimeError):
    """Raised when the scripted queue drains before the act ends."""


class ScriptedLLM:
    """FIFO queue of pre-written completions implementing the LLM contract."""

    def __init__(self, script: list[str] | None = None) -> None:
        self._script: list[str] = list(script or [])

    @property
    def remaining(self) -> int:
        """Completions left in the queue."""
        return len(self._script)

    def load(self, lines: list[str]) -> None:
        """Replace the queued script (used per scenario)."""
        self._script = list(lines)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[Any] | None = None,
        stop_sequences: list[str] | None = None,
        **kwargs: Any,
    ) -> Result[ScriptedCompletion, Exception]:
        """Pop the next scripted completion."""
        if not self._script:
            raise EmptyScriptError("script exhausted: no completions remain")
        return Ok(ScriptedCompletion(content=self._script.pop(0)))

    async def stream_chat(self, *args: Any, **kwargs: Any) -> Any:
        """Unused by the ReAct strategy."""
        raise NotImplementedError("ScriptedLLM does not support streaming")

    async def health_check(self, timeout: float = 5.0) -> Any:
        """Unused by the demo."""
        raise NotImplementedError

    async def close(self) -> None:
        """Nothing to release."""
        return None
```

Note: duck-typed against strategies' usage — do NOT subclass
`LLMClientProtocol`; if a runtime check ever requires it, revisit then.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest demos/support-agent/tests/test_scripted_llm.py -q`
Expected: PASS (4)

- [ ] **Step 6: Commit**

```bash
git status --short && git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): scaffold support-agent with scripted LLM"
```

---

### Task 2: Tool set

**Files:**
- Create: `demos/support-agent/src/support_agent/fixtures.py`
- Create: `demos/support-agent/src/support_agent/tools.py`
- Test: `demos/support-agent/tests/test_tools.py`

**Interfaces:**
- Consumes: `tool` decorator from `lexigram.ai.agents`.
- Produces: `ORDERS`, `KB` fixtures; async tools `lookup_order(order_id: str)`, `calculate_refund(order_total: float, days_since_delivery: int)`, `search_kb(query: str)`; `SUPPORT_TOOLS: list[Any]`.

- [ ] **Step 1: Write the failing test**

`demos/support-agent/tests/test_tools.py`:
```python
"""Tests for the support desk tools."""

from __future__ import annotations

import pytest

from support_agent.fixtures import KB
from support_agent.tools import (
    SUPPORT_TOOLS,
    calculate_refund,
    lookup_order,
    search_kb,
)


class TestLookupOrder:
    @pytest.mark.asyncio
    async def test_known_order_returns_details(self) -> None:
        result = await lookup_order(order_id="A-100")

        assert result["found"] is True
        assert result["status"] == "shipped"
        assert result["tracking"] == "FS123456789"

    @pytest.mark.asyncio
    async def test_unknown_order_reports_missing(self) -> None:
        assert (await lookup_order(order_id="NOPE"))["found"] is False


class TestCalculateRefund:
    @pytest.mark.asyncio
    async def test_within_seven_days_full_refund(self) -> None:
        result = await calculate_refund(order_total=100.0, days_since_delivery=5)
        assert (result["tier"], result["amount"]) == ("full", 100.0)

    @pytest.mark.asyncio
    async def test_within_thirty_days_half_refund(self) -> None:
        result = await calculate_refund(order_total=100.0, days_since_delivery=20)
        assert (result["tier"], result["amount"]) == ("half", 50.0)

    @pytest.mark.asyncio
    async def test_beyond_thirty_days_no_refund(self) -> None:
        result = await calculate_refund(order_total=100.0, days_since_delivery=45)
        assert (result["tier"], result["amount"]) == ("none", 0.0)

    @pytest.mark.asyncio
    async def test_tier_boundaries(self) -> None:
        tiers = [
            (await calculate_refund(100.0, d))["tier"] for d in (7, 8, 30, 31)
        ]
        assert tiers == ["full", "half", "half", "none"]


class TestSearchKb:
    @pytest.mark.asyncio
    async def test_keyword_match_returns_snippets(self) -> None:
        results = await search_kb(query="refund shipping")
        assert results
        assert all(set(r) == {"title", "snippet"} for r in results)

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self) -> None:
        assert await search_kb(query="zzzunmatchable") == []


def test_tool_surface() -> None:
    assert {t.name for t in SUPPORT_TOOLS} == {
        "lookup_order",
        "calculate_refund",
        "search_kb",
    }
    assert len(KB) >= 6
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/support-agent/tests/test_tools.py -q`
Expected: FAIL (`ModuleNotFoundError: fixtures`)

- [ ] **Step 3: Implement fixtures and tools**

`demos/support-agent/src/support_agent/fixtures.py`:
```python
"""Seeded offline fixtures for the support desk tools."""

from __future__ import annotations

ORDERS: dict[str, dict] = {
    "A-100": {
        "status": "shipped",
        "items": ["Desk Lamp", "USB-C Cable"],
        "total": 59.98,
        "carrier": "FastShip",
        "tracking": "FS123456789",
    },
    "A-101": {
        "status": "processing",
        "items": ["Mechanical Keyboard"],
        "total": 129.00,
        "carrier": None,
        "tracking": None,
    },
    "A-102": {
        "status": "delivered",
        "items": ["Monitor Arm"],
        "total": 74.50,
        "carrier": "FastShip",
        "tracking": "FS987654321",
    },
}

KB: list[dict[str, str]] = [
    {"title": "Refunds", "snippet": "Full refund within 7 days of delivery. Half refund within 30 days."},
    {"title": "Shipping", "snippet": "Standard shipping takes 3-5 business days with FastShip carrier."},
    {"title": "Tracking", "snippet": "Track your parcel using the tracking id in your shipment email."},
    {"title": "Returns", "snippet": "Start a return from your account page before requesting a refund."},
    {"title": "Warranty", "snippet": "All products include a 24 month limited warranty."},
    {"title": "Payments", "snippet": "We accept major cards and wallet payments; cards are charged at dispatch."},
]
```

`demos/support-agent/src/support_agent/tools.py`:
```python
"""Pure, offline tools the support agent calls during ReAct loops."""

from __future__ import annotations

from typing import Any

from lexigram.ai.agents import tool

from support_agent.fixtures import KB, ORDERS

FULL_REFUND_DAYS = 7
HALF_REFUND_DAYS = 30


@tool(description="Look up an order by ID and return status, items, and total.")
async def lookup_order(order_id: str) -> dict[str, Any]:
    """Return order details, or found=False when the id is unknown."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, **order}


@tool(description="Compute the refund amount for a delivered order.")
async def calculate_refund(
    order_total: float, days_since_delivery: int
) -> dict[str, Any]:
    """Apply the tiered policy: <=7d full, <=30d half, otherwise none."""
    if days_since_delivery <= FULL_REFUND_DAYS:
        tier, factor = "full", 1.0
    elif days_since_delivery <= HALF_REFUND_DAYS:
        tier, factor = "half", 0.5
    else:
        tier, factor = "none", 0.0
    return {"tier": tier, "amount": round(order_total * factor, 2)}


@tool(description="Search the FAQ knowledge base for relevant snippets.")
async def search_kb(query: str) -> list[dict[str, str]]:
    """Rank snippets by overlapping keyword count; top 2 returned."""
    terms = set(query.lower().split())
    scored: list[tuple[int, dict[str, str]]] = []
    for entry in KB:
        overlap = len(terms & set(entry["snippet"].lower().split()))
        if overlap:
            scored.append((overlap, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:2]]


SUPPORT_TOOLS: list[Any] = [lookup_order, calculate_refund, search_kb]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest demos/support-agent/tests/test_tools.py -q`
Expected: PASS (9)

- [ ] **Step 5: Commit**

```bash
git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): add support-agent tool set"
```

---

### Task 3: Scripts registry + agent service

**Files:**
- Create: `demos/support-agent/src/support_agent/scripts.py`
- Create: `demos/support-agent/src/support_agent/agent_service.py`
- Test: `demos/support-agent/tests/test_agent.py`

**Interfaces:**
- Consumes: `AgentBuilder` from `lexigram.ai.agents`; `AgentExecutorProtocol`, `AgentResponse`, `AgentError` from `lexigram.contracts.ai.agents`; `Result` from `lexigram.result`; `SUPPORT_TOOLS`.
- Produces: `Scenario(key, label, script)` frozen dataclass; `SCENARIOS: dict[str, Scenario]`; `HAPPY_SCRIPT`, `MULTI_TOOL_SCRIPT`, `FAILURE_SCRIPT: list[str]`; `build_support_agent() -> AgentProtocol`; `SupportAgent(executor, agent)` with `ask(question) -> Result[AgentResponse, AgentError]`, `last_response`.

- [ ] **Step 1: Write the failing test**

`demos/support-agent/tests/test_agent.py`:
```python
"""Unit-level tests for the agent service (no boot here)."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.ai.agents import AgentResponse
from lexigram.result import Ok

from support_agent.agent_service import SupportAgent, build_support_agent
from support_agent.scripts import SCENARIOS


def _response() -> AgentResponse:
    return AgentResponse(
        message="done",
        steps=[],
        tool_calls=[],
        total_tokens=36,
        prompt_tokens=12,
        completion_tokens=24,
        total_cost=0.0,
        duration_ms=1.0,
        session_id=None,
        metadata={"strategy": "react"},
    )


class _RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str]] = []

    async def run(self, *, agent: object, message: str, **kw: object):
        self.calls.append((agent, message))
        return Ok(_response())


class TestBuildSupportAgent:
    def test_builds_named_agent_with_tools_and_strategy(self) -> None:
        agent = build_support_agent()

        assert agent.name == "support-agent"
        assert len(agent.tools) == 3
        assert getattr(agent, "strategy", None) is not None


class TestScenariosRegistry:
    def test_three_scenarios_registered(self) -> None:
        assert set(SCENARIOS) == {"happy", "multi_tool", "failure"}
        assert all(len(s.script) >= 2 for s in SCENARIOS.values())
        assert {s.label for s in SCENARIOS.values()} == {
            "Happy path",
            "Multi-tool",
            "Failure",
        }


class TestSupportAgentFacade:
    def test_records_last_response(self) -> None:
        executor = _RecordingExecutor()
        facade = SupportAgent(executor=executor, agent=build_support_agent())

        result = asyncio.run(facade.ask("hi"))

        assert isinstance(result, Ok)
        assert facade.last_response is not None
        assert executor.calls[0][1] == "hi"

    def test_infra_error_raises_not_wrapped(self) -> None:
        class _Broken:
            async def run(self, **kw: object):
                raise RuntimeError("not booted")

        facade = SupportAgent(executor=_Broken(), agent=build_support_agent())
        with pytest.raises(RuntimeError, match="not booted"):
            asyncio.run(facade.ask("hi"))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/support-agent/tests/test_agent.py -q`
Expected: FAIL (`support_agent.scripts` / `agent_service` missing)

- [ ] **Step 3: Implement scripts and service**

`scripts.py`:
```python
"""Deterministic scenario scripts driving the scripted LLM.

Each entry is one full completion. ReAct parses THOUGHT/ACTION/
ACTION_INPUT markers and terminates on FINAL_ANSWER (react.py:53-81).
"""

from __future__ import annotations

from dataclasses import dataclass, field

HAPPY_SCRIPT: list[str] = [
    (
        "THOUGHT: I need the order details first.\n"
        "ACTION: lookup_order\n"
        'ACTION_INPUT: {"order_id": "A-100"}'
    ),
    (
        "THOUGHT: The order shipped via FastShip.\n"
        "FINAL_ANSWER: Order A-100 shipped via FastShip, tracking FS123456789."
    ),
]

MULTI_TOOL_SCRIPT: list[str] = [
    (
        "THOUGHT: Look up the order.\n"
        "ACTION: lookup_order\n"
        'ACTION_INPUT: {"order_id": "A-102"}'
    ),
    (
        "THOUGHT: Delivered recently; compute the refund.\n"
        "ACTION: calculate_refund\n"
        'ACTION_INPUT: {"order_total": 74.5, "days_since_delivery": 10}'
    ),
    "THOUGHT: Half refund applies.\nFINAL_ANSWER: You are eligible for a $37.25 half refund.",
]

FAILURE_SCRIPT: list[str] = [
    "THOUGHT: Try the wrong tool.\nACTION: teleport_order\nACTION_INPUT: {}",
    (
        "THOUGHT: That tool does not exist; answer directly.\n"
        "FINAL_ANSWER: I could not complete that request."
    ),
]


@dataclass(frozen=True)
class Scenario:
    """One deterministic demo act: key, display label, scripted turns."""

    key: str
    label: str
    script: list[str] = field(default_factory=list)


SCENARIOS: dict[str, Scenario] = {
    "happy": Scenario("happy", "Happy path", HAPPY_SCRIPT),
    "multi_tool": Scenario("multi_tool", "Multi-tool", MULTI_TOOL_SCRIPT),
    "failure": Scenario("failure", "Failure", FAILURE_SCRIPT),
}
```

`agent_service.py`:
```python
"""Agent construction and the API-facing facade."""

from __future__ import annotations

from lexigram.ai.agents import AgentBuilder
from lexigram.contracts.ai.agents import (
    AgentError,
    AgentExecutorProtocol,
    AgentProtocol,
    AgentResponse,
)
from lexigram.result import Result

from support_agent.tools import SUPPORT_TOOLS

SYSTEM_PROMPT = (
    "You are support-agent, a customer support assistant for an online "
    "store. Use the provided tools to look up orders, compute refunds, "
    "and search the knowledge base before answering. Be precise."
)


def build_support_agent() -> AgentProtocol:
    """Assemble the support-desk agent with its three tools."""
    return (
        AgentBuilder("support-agent")
        .with_system_prompt(SYSTEM_PROMPT)
        .with_tools(*SUPPORT_TOOLS)
        .with_strategy("react")
        .build()
    )


class SupportAgent:
    """Concrete facade: one question in, one traced response out."""

    def __init__(
        self, executor: AgentExecutorProtocol, agent: AgentProtocol
    ) -> None:
        self._executor = executor
        self._agent = agent
        self.last_response: AgentResponse | None = None

    async def ask(self, question: str) -> Result[AgentResponse, AgentError]:
        """Run one ReAct turn against the scripted LLM."""
        result: Result[AgentResponse, AgentError] = await self._executor.run(
            agent=self._agent,
            message=question,
        )
        if result.is_ok():
            self.last_response = result.unwrap()
        return result
```

Note: annotate per contracts' `AgentExecutorProtocol.run` signature
(contracts/ai/agents.py:344) — never widen to `Any`. If `AgentResponse`
rejects a kwarg, correct `_response()` against contracts/ai/agents.py:124
— that field list is authoritative.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest demos/support-agent/tests/test_agent.py -q`
Expected: PASS (4)

- [ ] **Step 5: Commit**

```bash
git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): assemble support agent service and scenarios"
```

---

### Task 4: Provider + module + JSON API (boot path)

**Files:**
- Create: `demos/support-agent/src/support_agent/di/__init__.py` (docstring only)
- Create: `demos/support-agent/src/support_agent/di/provider.py`
- Create: `demos/support-agent/src/support_agent/module.py`
- Create: `demos/support-agent/src/support_agent/controllers/__init__.py` (docstring only)
- Create: `demos/support-agent/src/support_agent/controllers/api.py`
- Modify: `demos/support-agent/conftest.py` (append fixtures)
- Test: `demos/support-agent/tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1–3; `AgentsModule`, `AgentConfig` from `lexigram.ai.agents`; `WebConfig`, `WebModule`, `Controller`, `get`, `post` from `lexigram.web`; `ServerConfig` from `lexigram.web.config`, `SecurityConfig` from `lexigram.web.security`; `Provider` from `lexigram.di.provider`; `LLMClientProtocol` from `lexigram.contracts.ai.llm`; registrar/resolver protocols from `lexigram.contracts.core.di`.
- Produces: `AgentSupportProvider()`; `SupportAgentModule.configure(port=None) -> DynamicModule` exporting `[SupportAgent]`; `GET /api/tools`; `POST /api/ask {question, scenario}` → `{answer, steps[], tool_calls[], total_tokens, duration_ms}`; conftest `app` (Starlette) and `client` (httpx.AsyncClient) fixtures.

- [ ] **Step 1: Extend conftest with boot fixtures (append)**

```python
from collections.abc import AsyncIterator

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.app import Application
from lexigram.web.di.provider import WebProvider


@pytest.fixture
async def app() -> AsyncIterator[Starlette]:
    """Boot the real module graph and expose its ASGI app."""
    from support_agent.module import SupportAgentModule

    async with Application.boot(
        name="support-agent-test",
        modules=[SupportAgentModule.configure()],
    ) as application:
        web = await application.container.resolve(WebProvider)
        yield web.starlette


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client over the running app (no socket bound)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
```

- [ ] **Step 2: Write the failing API test**

`demos/support-agent/tests/test_api.py`:
```python
"""End-to-end scenario tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_lists_three_tools(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/tools")

    assert response.status_code == 200
    names = {t["name"] for t in response.json()}
    assert names == {"lookup_order", "calculate_refund", "search_kb"}


async def test_happy_scenario_end_to_end(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/ask",
        json={"question": "Where is order A-100?", "scenario": "happy"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "Order A-100 shipped via FastShip, tracking FS123456789."
    )
    assert [c["tool_name"] for c in body["tool_calls"]] == ["lookup_order"]
    assert all(c["succeeded"] for c in body["tool_calls"])
    assert body["steps"][0]["thought"].startswith("I need")


async def test_multi_tool_scenario_ordered_calls(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/ask",
        json={
            "question": "Refund my monitor arm order A-102",
            "scenario": "multi_tool",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [c["tool_name"] for c in body["tool_calls"]] == [
        "lookup_order",
        "calculate_refund",
    ]
    assert body["answer"] == "You are eligible for a $37.25 half refund."


async def test_failure_scenario_degrades_without_raising(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/ask",
        json={"question": "Teleport my order", "scenario": "failure"},
    )

    assert response.status_code == 200
    record = response.json()["tool_calls"][0]
    assert record["tool_name"] == "teleport_order"
    assert record["succeeded"] is False
    assert "Unknown tool" in record["error"]


async def test_unknown_scenario_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/ask",
        json={"question": "hi", "scenario": "nope"},
    )

    assert response.status_code == 400
    assert "unknown scenario" in response.json()["error"].lower()


async def test_runs_are_byte_stable(client: httpx.AsyncClient) -> None:
    payload = {"question": "q", "scenario": "happy"}
    first = (await client.post("/api/ask", json=payload)).json()
    second = (await client.post("/api/ask", json=payload)).json()

    del first["duration_ms"], second["duration_ms"]  # timing varies
    assert first == second
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest demos/support-agent/tests/test_api.py -q`
Expected: FAIL (`cannot import name 'SupportAgentModule'`)

- [ ] **Step 4: Implement provider, module, api**

`di/provider.py`:
```python
"""DI wiring for the support-agent demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.agents import AgentExecutorProtocol
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from support_agent.agent_service import SupportAgent, build_support_agent
from support_agent.llm import ScriptedLLM


class AgentSupportProvider(Provider):
    """Binds the scripted LLM and assembles the facade at boot.

    The LLM binding MUST happen in ``register()``: ``AgentsProvider.boot()``
    performs a required resolve of ``LLMClientProtocol``
    (experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/di/provider.py:136).
    """

    name = "agent-support"

    def __init__(self) -> None:
        super().__init__()
        self._llm = ScriptedLLM()
        self._support: SupportAgent | None = None

    def _get_llm(self) -> ScriptedLLM:
        """Registered eagerly so freeze-time validation sees it."""
        return self._llm

    def _get_support(self) -> SupportAgent:
        """Valid only after boot() has assembled the facade."""
        if self._support is None:
            raise RuntimeError("AgentSupportProvider has not been booted yet")
        return self._support

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; collaborators resolve only in boot()."""
        container.singleton(ScriptedLLM, instance=self._llm)
        container.singleton(LLMClientProtocol, factory=self._get_llm)
        container.singleton(SupportAgent, factory=self._get_support)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the facade from the executor wired by AgentsModule."""
        executor = await container.resolve(AgentExecutorProtocol)
        self._support = SupportAgent(
            executor=executor,
            agent=build_support_agent(),
        )


from lexigram.contracts.ai.llm import LLMClientProtocol  # noqa: E402
```

Move that trailing import up beside the other contract imports before
saving (no circularity — final file groups it with the rest).

`module.py`:
```python
"""Root module for the support-agent demo."""

from __future__ import annotations

import os

from lexigram.ai.agents import AgentConfig, AgentsModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import ServerConfig, SecurityConfig, WebConfig, WebModule

from support_agent.agent_service import SupportAgent
from support_agent.controllers.api import AgentApiController
from support_agent.di.provider import AgentSupportProvider
from support_agent.ui.pages import ConsolePageController


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
                        server=ServerConfig(
                            host="127.0.0.1", port=selected_port
                        ),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[AgentSupportProvider],
            exports=[SupportAgent],
        )


__all__ = ["SupportAgentModule"]
```

If `ServerConfig`/`SecurityConfig` are absent from the `lexigram.web`
top-level surface, import them from `lexigram.web.config` /
`lexigram.web.security` instead (auth-web precedent uses those submodules).

`controllers/api.py`:
```python
"""JSON API for the support-agent console — no HTML lives here."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post

from support_agent.agent_service import SupportAgent, build_support_agent
from support_agent.llm import ScriptedLLM
from support_agent.scripts import SCENARIOS


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _serialize(response: Any) -> JSONResponse:
    return JSONResponse(
        {
            "answer": response.message,
            "steps": [
                {
                    "step_number": step.step_number,
                    "thought": step.thought,
                    "action": step.action,
                }
                for step in response.steps
            ],
            "tool_calls": [
                {
                    "tool_name": call.tool_name,
                    "succeeded": call.succeeded,
                    "error": call.error,
                }
                for call in response.tool_calls
            ],
            "total_tokens": response.total_tokens,
            "duration_ms": round(response.duration_ms, 1),
        },
    )


class AgentApiController(Controller):
    """Endpoints consumed by the ui/static/app.js fetch client."""

    def __init__(self, scripted: ScriptedLLM, support: SupportAgent) -> None:
        self._scripted = scripted
        self._support = support

    @get("/api/tools")
    async def tools(self, request: Request) -> JSONResponse:
        """List registered tools for the console sidebar."""
        agent = build_support_agent()
        return JSONResponse(
            [{"name": t.name, "description": t.description} for t in agent.tools],
        )

    @post("/api/ask")
    async def ask(self, request: Request) -> JSONResponse:
        """Run one scenario-scripted ReAct turn."""
        data = await request.json()
        scenario = SCENARIOS.get(str(data.get("scenario", "")))
        if scenario is None:
            return _error(f"unknown scenario: {data.get('scenario')!r}", 400)

        question = str(data.get("question", "")).strip()
        if not question:
            return _error("question is required", 400)

        self._scripted.load(scenario.script)
        result = await self._support.ask(question)
        if result.is_err():
            return _error(str(result.unwrap_err()), 500)
        return _serialize(result.unwrap())


__all__ = ["AgentApiController"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest demos/support-agent/tests -q`
Expected: ALL PASS (17 prior + 6 new API tests). Boot-order gotcha if
`LLMClientProtocol` resolve fails: confirm the binding uses the exact
class imported from `lexigram.contracts.ai.llm` — same object identity
`AgentsProvider.boot()` resolves.

- [ ] **Step 6: Commit**

```bash
git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): wire support-agent module with JSON API"
```

---

### Task 5: Console UI (assets + page controller)

**Files:**
- Create: `demos/support-agent/ui/views/console.html`
- Create: `demos/support-agent/ui/static/style.css`
- Create: `demos/support-agent/ui/static/app.js`
- Create: `demos/support-agent/src/support_agent/ui/__init__.py` (docstring only)
- Create: `demos/support-agent/src/support_agent/ui/pages.py`
- Create: `demos/support-agent/src/support_agent/ui/views/console.html` (move from demo-root plan)
- Create: `demos/support-agent/src/support_agent/ui/static/app.js`, `style.css`
- Test: `demos/support-agent/tests/test_pages.py`

**Interfaces:**
- Consumes: `Controller`, `FileResponse`, `get` from `lexigram.web`; running app via conftest fixtures.
- Produces: routes `/` (console view), `/static/app.js`, `/static/style.css`; DOM ids `tools`, `answer`, `trace`, `meta`, `error`; buttons `data-scenario` in {happy, multi_tool, failure}.

- [ ] **Step 1: Write the failing test**

`demos/support-agent/tests/test_pages.py`:
```python
"""Smoke tests for the console page routes."""

from __future__ import annotations

import httpx


async def test_root_serves_console(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Support Agent Console" in response.text
    assert 'data-scenario="happy"' in response.text
    assert 'data-scenario="multi_tool"' in response.text
    assert 'data-scenario="failure"' in response.text


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/support-agent/tests/test_pages.py -q`
Expected: FAIL (404s — route/controller missing)

- [ ] **Step 3: Write page assets**

`ui/views/console.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Support Agent Console</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header><h1>Support Agent Console</h1></header>
  <main>
    <aside id="tools-panel">
      <h2>Tools</h2>
      <ul id="tools"></ul>
    </aside>
    <section id="console">
      <div id="scenarios">
        <button data-scenario="happy">Happy path</button>
        <button data-scenario="multi_tool">Multi-tool</button>
        <button data-scenario="failure">Failure</button>
      </div>
      <form id="ask-form">
        <input id="question" type="text" autocomplete="off"
               placeholder="Ask about order A-100, refunds, shipping…">
        <button type="submit">Ask</button>
      </form>
      <p id="answer" class="hidden"></p>
      <table id="trace" class="hidden">
        <thead><tr><th>#</th><th>Thought</th><th>Action</th><th>Tool result</th></tr></thead>
        <tbody></tbody>
      </table>
      <p id="meta" class="muted"></p>
      <p id="error" class="hidden"></p>
    </section>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
```

`ui/static/app.js`:
```javascript
/* Vanilla-JS client for the support-agent console (no build step). */
"use strict";

let scenario = "happy";

const $ = (id) => document.getElementById(id);

function setActiveButton() {
  document.querySelectorAll("#scenarios button").forEach((b) => {
    b.classList.toggle("active", b.dataset.scenario === scenario);
  });
}

function hide(id) {
  $(id).classList.add("hidden");
}

function show(id) {
  $(id).classList.remove("hidden");
}

async function loadTools() {
  const res = await fetch("/api/tools");
  const tools = await res.json();
  $("tools").innerHTML = tools
    .map((t) => `<li title="${t.description}"><code>${t.name}</code></li>`)
    .join("");
}

function row(step, call) {
  const outcome = call
    ? `${call.tool_name} ${call.succeeded ? "ok" : `FAILED: ${call.error ?? ""}`}`
    : "";
  return `<tr><td>${step.step_number}</td><td>${step.thought ?? ""}</td>` +
         `<td>${step.action ?? ""}</td><td>${outcome}</td></tr>`;
}

function render(body) {
  $("answer").textContent = body.answer;
  $("trace").querySelector("tbody").innerHTML =
    body.steps.map((s, i) => row(s, body.tool_calls[i])).join("");
  $("meta").textContent = `tokens=${body.total_tokens} · ${body.duration_ms} ms`;
  ["answer", "trace", "meta"].forEach(show);
}

async function ask(event) {
  event.preventDefault();
  ["answer", "trace", "meta", "error"].forEach(hide);
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: $("question").value, scenario }),
  });
  if (!res.ok) {
    const err = await res.json();
    $("error").textContent = err.error ?? `HTTP ${res.status}`;
    show("error");
    return;
  }
  render(await res.json());
}

document.querySelectorAll("#scenarios button").forEach((b) =>
  b.addEventListener("click", () => {
    scenario = b.dataset.scenario;
    setActiveButton();
  }));
$("ask-form").addEventListener("submit", ask);
setActiveButton();
loadTools();
```

`ui/static/style.css`:
```css
/* Support-agent console theme */
:root { --bg:#10151c; --panel:#1a2230; --ink:#dbe4f0; --accent:#4da3ff; }
* { box-sizing: border-box; }
body { margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--ink); }
header h1 { margin:.6rem 1rem; font-size:1.2rem; }
main { display:flex; gap:1rem; padding:0 1rem 1rem; }
aside { width:220px; background:var(--panel); border-radius:8px; padding:.75rem; }
#console { flex:1; background:var(--panel); border-radius:8px; padding:1rem; }
#scenarios button, #ask-form button {
  background:var(--panel); color:var(--ink); border:1px solid #33415c;
  border-radius:6px; padding:.4rem .8rem; cursor:pointer;
}
#scenarios button.active { background:var(--accent); color:#08111e; border-color:var(--accent); }
#ask-form { display:flex; gap:.5rem; margin:.75rem 0; }
#question { flex:1; padding:.45rem .6rem; border-radius:6px; border:1px solid #33415c; background:#0c1118; color:var(--ink); }
.hidden { display:none; }
.muted { color:#7d8ba1; font-size:.85rem; }
#error { color:#ff7a7a; }
table { width:100%; border-collapse:collapse; font-size:.9rem; }
th, td { text-align:left; padding:.35rem .5rem; border-bottom:1px solid #26314a; vertical-align:top; }
```

- [ ] **Step 4: Write the page controller**

`src/support_agent/ui/pages.py`:
```python
"""Console page — static serving only (logic lives in the API controller)."""

from __future__ import annotations

from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse

from lexigram.web import Controller, FileResponse, get

UI_ROOT = Path(__file__).resolve().parent
VIEWS_ROOT = UI_ROOT / "views"
STATIC_ROOT = UI_ROOT / "static"


def _view(name: str) -> FileResponse:
    """Serve one HTML view."""
    return FileResponse(path=VIEWS_ROOT / name, media_type="text/html")


def _static(name: str, media_type: str) -> FileResponse:
    """Serve one static asset."""
    return FileResponse(path=STATIC_ROOT / name, media_type=media_type)


class ConsolePageController(Controller):
    """Serve the agent console; every handler reads from ui/."""

    def __init__(self) -> None:
        """Stateless."""

    @get("/")
    async def console(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("console.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")


__all__ = ["ConsolePageController"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest demos/support-agent/tests -q`
Expected: ALL PASS. If `ConsolePageController` import fails at boot, verify `src/` is on
sys.path and that `UI_ROOT` resolves to the package's `ui/` directory.

- [ ] **Step 6: Commit**

```bash
git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): add support-agent console UI"
```

---

### Task 6: Server entry point

**Files:**
- Create: `demos/support-agent/src/support_agent/main.py`
- Create: `demos/support-agent/src/support_agent/__main__.py`

**Interfaces:**
- Consumes: `SupportAgentModule`, `Application`, `WebProvider`, `run_server_async`.
- Produces: `main() -> int`; `python -m support_agent [--port N]`.

- [ ] **Step 1: Implement entry point**

`main.py`:
```python
"""Entry points for the support-agent demo.

Run::

    PYTHONPATH=demos/support-agent/src \
        uv run python -m support_agent          # serves on :8082
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async

from support_agent.module import SupportAgentModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="support-agent",
        modules=[SupportAgentModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Support agent demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SUPPORT_AGENT_PORT", "8082")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`__main__.py`:
```python
"""Enable ``python -m support_agent``."""

from __future__ import annotations

import sys

from support_agent.main import main

sys.exit(main())
```

- [ ] **Step 2: Manual smoke (no pytest)**

Run:
```bash
PYTHONPATH=demos/support-agent/src timeout 5 uv run python -m support_agent --port 8087 &
sleep 3
curl -s http://127.0.0.1:8087/api/tools
curl -s -X POST http://127.0.0.1:8087/api/ask -H 'Content-Type: application/json' -d '{"question":"Where is A-100?","scenario":"happy"}'
curl -s http://127.0.0.1:8087/ | head -5
```
Expected: tools JSON array; ask JSON with answer containing `FS123456789`;
HTML starting `<!doctype html>`; process exits after timeout (124/130).

- [ ] **Step 3: Full suite re-check**

Run: `uv run pytest demos/support-agent/tests -q`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add demos/support-agent && git commit demos/support-agent -m "✨ feat(demos): add support-agent server entry point"
```

---

### Task 7: README + Makefile gating + full gates

**Files:**
- Create: `demos/support-agent/README.md`
- Modify: `Makefile:114-115`
- Modify: `demos/README.md`

**Interfaces:** none — docs/build wiring.

- [ ] **Step 1: Makefile entries**

Append (diff against current file first — other lanes may have added
entries like auth-web; never clobber):

```make
DEMO_TEST_DIRS := …existing… demos/auth-web/tests demos/support-agent/tests
DEMO_COMPILE_DIRS := …existing… demos/auth-web demos/support-agent
```

- [ ] **Step 2: READMEs**

`demos/support-agent/README.md` — sections: What it proves (real ReAct loop through the framework executor, three `@tool`s, scripted model boundary); Layout note (flat house structure + auth-web-style co-located `ui/`); Run (`PYTHONPATH=demos/support-agent/src uv run python -m support_agent` → http://127.0.0.1:8082); Scenarios table; Tests command.

`demos/README.md` — insert section after rag-docs, house style:

```markdown
### 🤖 [support-agent](support-agent/) — tool-calling ReAct agent

A support-desk agent driven by a scripted LLM:

- 🧠 **Real agent loop** — THOUGHT/ACTION parsing through the framework's react strategy
- 🔧 **Three container-injected tools** — order lookup, refund policy math, KB search
- 🎬 **Deterministic model boundary** — scripted completions, byte-stable reruns
- 🖥️ **Browser console** — pick a scenario, ask, read the trace table
- 💥 **Failure act included** — unknown tools degrade to failed tool-call records
```

- [ ] **Step 3: Full gates**

```bash
uv run ruff check demos/support-agent && uv run ruff format --check demos/support-agent
make test-demos
make verify-demos
find demos/support-agent -name "*.py" | xargs wc -l | sort -n   # all files <500
git status --short                                              # only expected paths
```
Expected: clean; gates green; no foreign paths dirty.

- [ ] **Step 4: Commit**

```bash
git add demos/README.md demos/support-agent/README.md Makefile && git commit demos/README.md demos/support-agent/README.md Makefile -m "📝 docs(demos): document support-agent and gate make targets"
```

---

## Self-Review Notes

- Spec coverage (v4): flat layout ✓(T1–T6), module.py root ✓(T4), provider register/boot split with LLM-in-register ✓(T4), SCENARIOS registry + Scenario dataclass in scripts.py (no protocols.py — concrete export like OrdersApi) ✓(T3/T4), three acts incl. verified unknown-tool behavior ✓(T4 Step 2), ui/pages.py beside assets ✓(T5), byte-stability ✓(T4), single sys.path shim ✓(T1/conftest), Makefile+README ✓(T7).
- Type consistency: `Scenario(key,label,script)` identical across scripts.py/api usage; `SupportAgent.ask` matches facade tests and controller call; `load()/remaining` consistent between llm.py and api.py.
- Known risks carried from spec §10: `LLMClientProtocol` token identity; `AgentResponse` field authority at contracts/ai/agents.py:124; `lexigram.web` top-level vs submodule config imports.
