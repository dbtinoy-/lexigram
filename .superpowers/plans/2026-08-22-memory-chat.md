# Memory-Chat Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `demos/memory-chat/` — an offline, deterministic conversational-memory demo (no LLM) with a two-owner web console, in the house Pattern-2 flat shape plus a standalone swappable `ui/` frontend.

**Architecture:** Flat package `src/memory_chat/` — root `@module MemoryChatModule` imports `MemoryModule.configure(in_memory, consolidation off)` + `WebModule`; pure extraction/responder modules; `ConciergeService` orchestrates episodic/semantic/working stores; `controllers/api.py` serves JSON; `ui/pages.py` serves static assets only (auth-web co-located pattern).

**Tech Stack:** Python 3.11+, Lexigram workspace packages (`lexigram-ai-memory`, `lexigram-web`), Starlette via `lexigram.web`, httpx ASGI testing, pytest-asyncio, ruff (root config).

**Spec:** `.superpowers/specs/2026-08-22-memory-chat-design.md` — read it first; this plan argues from it.

## Global Constraints

- Offline only; byte-stable output — **fabricated timestamps** (`TURN_EPOCH + timedelta(seconds=n)`), never wall clock (`MemoryEntry.id`/`timestamp` are required, memory.py:16-38).
- Absolute imports; Google docstrings; full type annotations; files <500 LOC.
- **Dual sys-path:** conftest inserts demo-root `src/` AND the demo root.
- Commits: emoji conventional format, pathspec commits only
  (`git commit <paths> -m "…"`); check `git status --short` first; foreign
  staged paths belong to other lanes.
- Scoped runs: `uv run pytest demos/memory-chat/tests -q`.
- Gates: `uv run ruff check demos/memory-chat && uv run ruff format --check demos/memory-chat`.

---

### Task 1: Scaffold + fact extraction

**Files:**
- Create: `demos/memory-chat/conftest.py`
- Create: `demos/memory-chat/src/memory_chat/__init__.py`
- Create: `demos/memory-chat/tests/__init__.py` (empty)
- Create: `demos/memory-chat/src/memory_chat/extraction.py`
- Test: `demos/memory-chat/tests/test_extraction.py`

**Interfaces:**
- Produces: `Triple = tuple[str, str, str, float]` (subject=owner_id, predicate, object, confidence); `extract_facts(owner_id: str, text: str) -> list[Triple]`.

- [ ] **Step 1: Write conftest and skeletons**

`demos/memory-chat/conftest.py`:
```python
"""Pytest bootstrap for the memory-chat demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import
``memory_chat`` without installing (auth-web pattern):

    uv run pytest demos/memory-chat/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
```

Docstring-only `__init__.py` files at `src/memory_chat/__init__.py`
(`"""Conversational-memory concierge demo."""`), `ui/__init__.py`
`tests/__init__.py` (empty).

- [ ] **Step 2: Write the failing test**

`tests/test_extraction.py`:
```python
"""Tests for declarative fact extraction."""

from __future__ import annotations

from memory_chat.extraction import extract_facts


class TestExtractFacts:
    def test_diet_statement(self) -> None:
        triples = extract_facts("alice", "I'm vegetarian")

        assert triples == [("alice", "diet", "vegetarian", 0.9)]

    def test_allergy_statement(self) -> None:
        triples = extract_facts("alice", "I am allergic to peanuts")

        assert triples == [("alice", "allergy", "peanuts", 0.95)]

    def test_preference_statement(self) -> None:
        triples = extract_facts("bob", "I like spicy food")

        assert triples == [("bob", "preference", "spicy", 0.7)]

    def test_have_allergy_form(self) -> None:
        triples = extract_facts("bob", "I have a nut allergy")

        assert triples == [("bob", "allergy", "nut", 0.95)]

    def test_multiple_facts_deduped(self) -> None:
        triples = extract_facts("alice", "I'm vegetarian. I'm vegetarian!")

        assert len(triples) == 1

    def test_no_false_positives(self) -> None:
        assert extract_facts("bob", "The dog likes treats") == []
        assert extract_facts("bob", "Tell me a joke") == []

    def test_subject_is_owner_id(self) -> None:
        alice = extract_facts("alice", "I'm vegan")
        bob = extract_facts("bob", "I'm vegan")

        assert alice[0][0] == "alice"
        assert bob[0][0] == "bob"
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest demos/memory-chat/tests/test_extraction.py -q`
Expected: FAIL (`No module named 'memory_chat.extraction'`)

- [ ] **Step 4: Implement extraction**

`src/memory_chat/extraction.py`:
```python
"""Declarative fact extraction — regex rules over first-person statements.

Pure function; returns empty list on no match. Subject is ALWAYS the
owner_id: semantic memory is not owner-scoped by contract, so subject
namespacing is what keeps users isolated.
"""

from __future__ import annotations

import re

Triple = tuple[str, str, str, float]

_CONFIDENCE: dict[str, float] = {
    "diet": 0.9,
    "allergy": 0.95,
    "preference": 0.7,
}

_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\bi(?:'m| am)\s+(?:a\s+)?(vegetarian|vegan|pescatarian)\b",
            re.IGNORECASE,
        ),
        "diet",
    ),
    (
        re.compile(r"\bi(?:'m| am)\s+allergic\s+to\s+([\w-]+)", re.IGNORECASE),
        "allergy",
    ),
    (
        re.compile(r"\bi\s+have\s+(?:a\s+)?([\w-]+)\s+allergy", re.IGNORECASE),
        "allergy",
    ),
    (
        re.compile(r"\bi\s+(?:really\s+)?like\s+([\w-]+)", re.IGNORECASE),
        "preference",
    ),
]


def extract_facts(owner_id: str, text: str) -> list[Triple]:
    """Extract deduplicated (subject, predicate, object, confidence)."""
    triples: list[Triple] = []
    seen: set[tuple[str, str, str]] = set()
    for pattern, predicate in _RULES:
        for match in pattern.finditer(text):
            obj = match.group(1).lower()
            key = (owner_id, predicate, obj)
            if key in seen:
                continue
            seen.add(key)
            triples.append((owner_id, predicate, obj, _CONFIDENCE[predicate]))
    return triples
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest demos/memory-chat/tests/test_extraction.py -q`
Expected: PASS (7)

- [ ] **Step 6: Commit**

```bash
git status --short && git add demos/memory-chat && git commit demos/memory-chat -m "✨ feat(demos): scaffold memory-chat with fact extraction"
```

---

### Task 2: Deterministic responder

**Files:**
- Create: `demos/memory-chat/src/memory_chat/responder.py`
- Test: `demos/memory-chat/tests/test_responder.py`

**Interfaces:**
- Consumes: `Triple`.
- Produces: `Reply(text: str, cited: list[str])` frozen dataclass; `reply_for(text: str, facts: list[Triple]) -> Reply`.

- [ ] **Step 1: Write the failing test**

`tests/test_responder.py`:
```python
"""Tests for the deterministic template responder."""

from __future__ import annotations

from memory_chat.responder import reply_for


ALICE_FACTS = [
    ("alice", "diet", "vegetarian", 0.9),
    ("alice", "allergy", "peanuts", 0.95),
]
BOB_FACTS: list = []


class TestReplyFor:
    def test_food_intent_with_constraints_cites_them(self) -> None:
        reply = reply_for("Suggest a dinner menu", ALICE_FACTS)

        assert "peanuts" in reply.text
        assert "vegetarian" in reply.text
        assert reply.cited == ["diet: vegetarian", "allergy: peanuts"]

    def test_food_intent_without_constraints_anything_goes(self) -> None:
        reply = reply_for("Suggest a dinner menu", BOB_FACTS)

        assert reply.text == "Here's a menu idea — anything goes!"
        assert reply.cited == []

    def test_remember_intent_lists_facts(self) -> None:
        reply = reply_for("What do you remember about me?", ALICE_FACTS)

        assert "diet: vegetarian" in reply.text
        assert reply.cited == ["diet: vegetarian", "allergy: peanuts"]

    def test_plain_turn_acknowledges(self) -> None:
        reply = reply_for("hello there", [])

        assert reply.text == "Noted! What would you like next?"
        assert reply.cited == []
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/memory-chat/tests/test_responder.py -q`
Expected: FAIL (`responder` missing)

- [ ] **Step 3: Implement responder**

`src/memory_chat/responder.py`:
```python
"""Deterministic template replies driven by recalled context — no LLM."""

from __future__ import annotations

from dataclasses import dataclass, field

from memory_chat.extraction import Triple

_FOOD_WORDS = ("food", "menu", "eat", "dinner", "lunch", "snack", "meal")
_REMEMBER_WORDS = ("remember", "know about me")


@dataclass(frozen=True)
class Reply:
    """A rendered turn: template text plus cited constraint facts."""

    text: str
    cited: list[str] = field(default_factory=list)


def reply_for(text: str, facts: list[Triple]) -> Reply:
    """Select a template from intent + constraint facts."""
    lowered = text.lower()
    constraints = [f for f in facts if f[1] in ("diet", "allergy")]
    cited = [f"{predicate}: {obj}" for _, predicate, obj, _ in constraints]

    if any(word in lowered for word in _FOOD_WORDS):
        return _menu_reply(constraints, cited)
    if any(word in lowered for word in _REMEMBER_WORDS) and constraints:
        return Reply(f"You've told me: {'; '.join(cited)}.", cited)
    return Reply("Noted! What would you like next?")


def _menu_reply(constraints: list[Triple], cited: list[str]) -> Reply:
    """Menu templates — constrained when facts exist, open otherwise."""
    allergies = sorted(o for _, p, o, _ in constraints if p == "allergy")
    diets = sorted(o for _, p, o, _ in constraints if p == "diets")
    diets = sorted(o for _, p, o, _ in constraints if p == "diet")
    parts: list[str] = []
    if allergies:
        parts.append("strictly avoiding " + ", ".join(allergies))
    if diets:
        parts.append("keeping things " + " and ".join(diets))
    if not parts:
        return Reply("Here's a menu idea — anything goes!")
    return Reply("Here's a menu idea — " + " while ".join(parts) + ".", cited)
```

Delete the stray duplicated `diets` line before saving (trap marker —
final file keeps exactly one).

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest demos/memory-chat/tests/test_responder.py -q`
Expected: PASS (4)

- [ ] **Step 5: Commit**

```bash
git add demos/memory-chat && git commit demos/memory-chat -m "✨ feat(demos): add memory-chat deterministic responder"
```

---

### Task 3: Service + provider + module + JSON API (boot path)

**Files:**
- Create: `demos/memory-chat/src/memory_chat/scripts.py`
- Create: `demos/memory-chat/src/memory_chat/chat_service.py`
- Create: `demos/memory-chat/src/memory_chat/di/__init__.py` (docstring only)
- Create: `demos/memory-chat/src/memory_chat/di/provider.py`
- Create: `demos/memory-chat/src/memory_chat/module.py`
- Create: `demos/memory-chat/src/memory_chat/controllers/__init__.py` (docstring only)
- Create: `demos/memory-chat/src/memory_chat/controllers/api.py`
- Modify: `conftest.py` (append fixtures)
- Test: `demos/memory-chat/tests/test_chat_service.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `MemoryEntry`, `MemoryQuery` from `lexigram.contracts.ai.memory`; `WorkingMemoryProtocol`, `EpisodicMemoryProtocol`, `SemanticMemoryProtocol` from `lexigram.contracts.ai.memory`; `AgentsOfWeb`: `Controller/get/post`, `WebConfig/WebModule`, `ServerConfig` (`lexigram.web.config`), `SecurityConfig` (`lexigram.web.security`); `Provider` from `lexigram.di.provider`; `MemoryModule`, `MemoryConfig` from `lexigram.ai.memory`.
- Produces: `TurnResult(reply_text, cited, context_chars)`; `FactsSnapshot(triples, recent)`; `DemoResult(transcript, isolation_ok)`; `ConciergeService(working, episodic, semantic)` with `send(owner, text)`, `get_facts(owner)`, `demo_replay()`; `POST /api/chat`, `GET /api/facts/{owner}`, `POST /api/demo`; conftest `app`/`client` fixtures.

- [ ] **Step 1: Extend conftest (append)**

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
    from memory_chat.module import MemoryChatModule

    async with Application.boot(
        name="memory-chat-test",
        modules=[MemoryChatModule.configure()],
    ) as application:
        web = await application.container.resolve(WebProvider)
        yield web.starlette


@pytest.fixture
async def client(app: Starlette) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http:
        yield http
```

- [ ] **Step 2: Write failing service tests**

`tests/test_chat_service.py`:
```python
"""Service-level tests resolved from the booted container."""

from __future__ import annotations

import pytest

from lexigram.web.di.provider import WebProvider  # noqa: F401  (app fixture lives in conftest)


@pytest.mark.usefixtures("app")
async def test_fact_stated_turn_one_cited_later(app) -> None:
    from memory_chat.chat_service import ConciergeService

    service = await app.container.resolve(ConciergeService)

    await service.send("alice", "I'm vegetarian")
    await service.send("alice", "I'm allergic to peanuts")
    result = await service.send("alice", "Suggest a dinner menu")

    assert "peanuts" in result.reply_text
    assert "vegetarian" in result.reply_text
    assert result.cited == ["diet: vegetarian", "allergy: peanuts"]
    assert result.context_chars > 0


async def test_cross_owner_isolation_through_shared_backend(app) -> None:
    from memory_chat.chat_service import ConciergeService

    service = await app.container.resolve(ConciergeService)

    await service.send("alice", "I'm allergic to peanuts")
    bob_menu = await service.send("bob", "Suggest a dinner menu")

    assert bob_menu.reply_text == "Here's a menu idea — anything goes!"
    snapshot = await service.get_facts("bob")
    assert snapshot.triples == []


async def test_demo_replay_is_byte_stable_and_proves_isolation(app) -> None:
    from memory_chat.chat_service import ConciergeService

    service = await app.container.resolve(ConciergeService)

    first = await service.demo_replay()
    second = await service.demo_replay()

    assert first.isolation_ok is True
    assert first == second


async def test_get_facts_snapshot_shape(app) -> None:
    from memory_chat.chat_service import ConciergeService

    service = await app.container.resolve(ConciergeService)

    await service.send("carol", "I like spicy food")
    snapshot = await service.get_facts("carol")

    assert snapshot.triples == [["carol", "preference", "spicy", 0.7]]
    assert [e.content for e in snapshot.recent] == ["I like spicy food"]
```

(The `pytest.mark.usefixtures` line plus direct `app` argument is
redundant — drop the decorator, keep the plain `app` parameter.)

- [ ] **Step 3: Write failing API tests**

`tests/test_api.py`:
```python
"""End-to-end tests over the JSON API."""

from __future__ import annotations

import httpx


async def test_chat_turn_shape(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/chat",
        json={"owner": "alice", "text": "I'm vegetarian"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cited"] == ["diet: vegetarian"]
    assert isinstance(body["context_chars"], int)


async def test_recall_across_turns(client: httpx.AsyncClient) -> None:
    await client.post("/api/chat", json={"owner": "alice", "text": "I'm allergic to peanuts"})
    menu = await client.post(
        "/api/chat", json={"owner": "alice", "text": "Suggest a dinner menu"}
    )

    body = menu.json()
    assert "peanuts" in body["reply"]


async def test_owner_isolation(client: httpx.AsyncClient) -> None:
    await client.post("/api/chat", json={"owner": "alice", "text": "I'm allergic to peanuts"})
    bob = await client.post(
        "/api/chat", json={"owner": "bob", "text": "What do you remember about me?"}
    )

    assert bob.json()["reply"] == "Noted! What would you like next?"
    facts_bob = (await client.get("/api/facts/bob")).json()
    assert facts_bob["triples"] == []


async def test_demo_endpoint_stable(client: httpx.AsyncClient) -> None:
    first = (await client.post("/api/demo")).json()
    second = (await client.post("/api/demo")).json()

    assert first == second
    assert first["isolation_ok"] is True


async def test_empty_text_is_400(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/chat", json={"owner": "alice", "text": "   "})

    assert response.status_code == 400
```

- [ ] **Step 4: Run to verify failure**

Run: `uv run pytest demos/memory-chat/tests/test_chat_service.py demos/memory-chat/tests/test_api.py -q`
Expected: FAIL (`cannot import name 'MemoryChatModule'`)

- [ ] **Step 5: Implement scripts, service, provider, module, api**

`scripts.py`:
```python
"""Scripted two-session conversation replayed by the demo act."""

from __future__ import annotations

DEMO_REPLAY: list[tuple[str, str]] = [
    ("alice", "I'm vegetarian"),
    ("alice", "I'm allergic to peanuts"),
    ("alice", "Suggest a dinner menu"),
    ("bob", "What do you remember about me?"),
    ("bob", "Suggest a dinner menu"),
]
```

`chat_service.py`:
```python
"""Orchestration across episodic, semantic, and working memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    MemoryEntry,
    MemoryQuery,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)

from memory_chat.extraction import Triple, extract_facts
from memory_chat.responder import reply_for

TURN_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class TurnResult:
    """Outcome of one conversational turn."""

    reply_text: str
    cited: list[str] = field(default_factory=list)
    context_chars: int = 0


@dataclass(frozen=True)
class FactsSnapshot:
    """Everything known about one owner."""

    triples: list[list] = field(default_factory=list)
    recent: list[MemoryEntry] = field(default_factory=list)


@dataclass(frozen=True)
class DemoResult:
    """Transcript of the scripted replay plus the isolation verdict."""

    transcript: list[dict] = field(default_factory=list)
    isolation_ok: bool = False


class ConciergeService:
    """Drives one turn through record → extract → recall → respond."""

    def __init__(
        self,
        working: WorkingMemoryProtocol,
        episodic: EpisodicMemoryProtocol,
        semantic: SemanticMemoryProtocol,
    ) -> None:
        self._working = working
        self._episodic = episodic
        self._semantic = semantic
        self._turns: dict[str, int] = {}

    async def send(self, owner: str, text: str) -> TurnResult:
        """Record, extract, recall, assemble, respond — in order."""
        entry = self._entry_for(owner, text)
        await self._episodic.record(entry)

        for triple in extract_facts(owner, text):
            subject, predicate, obj, confidence = triple
            await self._semantic.store_fact(subject, predicate, obj, confidence)

        recalled = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query=text, top_k=5),
        )
        entity_facts = await self._semantic.get_entity_facts(owner)
        context = await self._working.assemble(
            query=text, token_budget=256, owner_id=owner,
        )
        reply = reply_for(text, entity_facts)
        context_chars = sum(len(e.content) for e in context)
        return TurnResult(reply.text, list(reply.cited), context_chars)

    async def get_facts(self, owner: str) -> FactsSnapshot:
        """Everything stored about one owner."""
        raw = await self._semantic.get_entity_facts(owner)
        recent = await self._episodic.get_recent(10, owner_id=owner)
        triples = [
            [f.get("subject"), f.get("predicate"), f.get("object"), f.get("confidence")]
            for f in raw
        ]
        return FactsSnapshot(triples=triples, recent=list(recent))

    async def demo_replay(self) -> DemoResult:
        """Replay DEMO_REPLAY verbatim; prove recall AND isolation."""
        from memory_chat.scripts import DEMO_REPLAY

        transcript: list[dict] = []
        bob_all_clear = True
        for owner, text in DEMO_REPLAY:
            result = await self.send(owner, text)
            transcript.append(
                {"owner": owner, "text": text, "reply": result.reply_text},
            )
            if owner == "bob":
                lowered = result.reply_text.lower()
                if "peanut" in lowered or "vegetarian" in lowered:
                    bob_all_clear = False
                if owner == "bob" and text.startswith("What do you remember"):
                    if result.reply_text != "Noted! What would you like next?":
                        bob_all_clear = False
        return DemoResult(transcript=transcript, isolation_ok=bob_all_clear)

    def _entry_for(self, owner: str, text: str) -> MemoryEntry:
        """Deterministic entry: fabricated id/timestamp, no wall clock."""
        n = self._turns.get(owner, 0)
        self._turns[owner] = n + 1
        has_facts = bool(extract_facts(owner, text))
        return MemoryEntry(
            id=f"{owner}:{n}",
            owner_id=owner,
            content=text,
            role="user",
            timestamp=TURN_EPOCH + timedelta(seconds=n),
            importance=0.9 if has_facts else 0.5,
        )
```

Note: `get_entity_facts` dict keys (`subject/predicate/object/confidence`)
are pinned against `contracts/ai/memory.py:292-353` at implementation;
adjust key names to actuals if they differ. If `recall` requires
non-default weights, pass explicit `recency_weight/importance_weight/
relevance_weight` copied from `EpisodicMemoryConfig` defaults.

`di/provider.py`:
```python
"""DI wiring for the memory-chat demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import (
        EpisodicMemoryProtocol,
        SemanticMemoryProtocol,
        WorkingMemoryProtocol,
    )
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from memory_chat.chat_service import ConciergeService


class ConciergeProvider(Provider):
    """Resolves the three memory contracts and assembles the service."""

    name = "concierge"

    def __init__(self) -> None:
        super().__init__()
        self._service: ConciergeService | None = None

    def _get_service(self) -> ConciergeService:
        """Valid only after boot()."""
        if self._service is None:
            raise RuntimeError("ConciergeProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy factory; stores resolve only in boot()."""
        container.singleton(ConciergeService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the facade from MemoryModule's exported protocols."""
        working = await container.resolve(WorkingMemoryProtocol)
        episodic = await container.resolve(EpisodicMemoryProtocol)
        semantic = await container.resolve(SemanticMemoryProtocol)
        self._service = ConciergeService(
            working=working, episodic=episodic, semantic=semantic,
        )
```

`module.py`:
```python
"""Root module for the memory-chat demo."""

from __future__ import annotations

import os

from lexigram.ai.memory import MemoryConfig, MemoryModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import ServerConfig, SecurityConfig, WebConfig, WebModule

from memory_chat.chat_service import ConciergeService
from memory_chat.controllers.api import ConciergeApiController
from memory_chat.di.provider import ConciergeProvider
from memory_chat.ui.pages import ChatPageController


@module()
class MemoryChatModule(Module):
    """Conversational memory concierge with a two-owner web console."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = port if port is not None else int(
            os.environ.get("MEMORY_CHAT_PORT", "8083")
        )
        return DynamicModule(
            module=cls,
            imports=[
                MemoryModule.configure(
                    MemoryConfig(default_backend="in_memory"),
                    enable_consolidation=False,
                ),
                WebModule.configure(
                    controllers=[ConciergeApiController, ChatPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[ConciergeProvider],
            exports=[ConciergeService],
        )


__all__ = ["MemoryChatModule"]
```

`controllers/api.py`:
```python
"""JSON API for the memory-chat console — no HTML lives here."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.web import Controller, get, post

from memory_chat.chat_service import ConciergeService


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class ConciergeApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, concierge: ConciergeService) -> None:
        self._concierge = concierge

    @post("/api/chat")
    async def chat(self, request: Request) -> JSONResponse:
        """One conversational turn for an owner."""
        data = await request.json()
        owner = str(data.get("owner", "")).strip()
        text = str(data.get("text", "")).strip()
        if not owner or not text:
            return _error("owner and text are required", 400)

        result = await self._concierge.send(owner, text)
        return JSONResponse(
            {
                "reply": result.reply_text,
                "cited": result.cited,
                "context_chars": result.context_chars,
            },
        )

    @get("/api/facts/{owner}")
    async def facts(self, request: Request) -> JSONResponse:
        """Snapshot of everything stored about one owner."""
        snapshot = await self._concierge.get_facts(request.path_params["owner"])
        return JSONResponse(
            {
                "triples": snapshot.triples,
                "recent": [
                    {"content": e.content, "role": e.role}
                    for e in snapshot.recent
                ],
            },
        )

    @post("/api/demo")
    async def demo(self, request: Request) -> JSONResponse:
        """Scripted two-session replay proving recall and isolation."""
        result = await self._concierge.demo_replay()
        return JSONResponse(
            {
                "transcript": result.transcript,
                "isolation_ok": result.isolation_ok,
            },
        )


__all__ = ["ConciergeApiController"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest demos/memory-chat/tests -q`
Expected: ALL PASS (11 prior + 4 service + 5 API). If protocol resolves
fail at boot, confirm `MemoryProvider.register()` binds all three tokens
(check its di/provider.py before improvising — do NOT construct backends
in our provider).

- [ ] **Step 7: Commit**

```bash
git add demos/memory-chat && git commit demos/memory-chat -m "✨ feat(demos): wire memory-chat service with JSON API"
```

---

### Task 4: Chat UI (assets + page controller)

**Files:**
- Create: `src/memory_chat/ui/__init__.py` (docstring only)
- Create: `src/memory_chat/ui/pages.py`
- Create: `src/memory_chat/ui/views/chat.html`
- Create: `src/memory_chat/ui/static/style.css`, `app.js`
- Test: `tests/test_pages.py`

**Interfaces:**
- Produces: `/` serves chat view; `/static/*`; DOM ids `thread`, `facts`, `ask-form`, `message`, `demo-btn`, `error`; owner buttons `data-owner` in {alice, bob}.

- [ ] **Step 1: Write the failing test**

`tests/test_pages.py`:
```python
"""Smoke tests for the chat page routes."""

from __future__ import annotations

import httpx


async def test_root_serves_chat(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Memory Chat" in response.text
    assert 'data-owner="alice"' in response.text
    assert 'data-owner="bob"' in response.text


async def test_static_assets_served(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    js = await client.get("/static/app.js")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/memory-chat/tests/test_pages.py -q`
Expected: FAIL (404s)

- [ ] **Step 3: Write assets and page controller**

`ui/views/chat.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Memory Chat</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header><h1>Memory Chat</h1>
    <nav id="owners">
      <button data-owner="alice">alice</button>
      <button data-owner="bob">bob</button>
    </nav>
  </header>
  <main>
    <section id="chat-pane">
      <div id="thread"></div>
      <form id="ask-form">
        <input id="message" type="text" autocomplete="off"
               placeholder='Say "I\'m allergic to peanuts" then ask for a menu'>
        <button type="submit">Send</button>
      </form>
      <p id="error" class="hidden"></p>
    </section>
    <aside id="facts-panel">
      <h2>Facts</h2>
      <ul id="facts"></ul>
      <button id="demo-btn">Run demo replay</button>
    </aside>
  </main>
  <script src="/static/app.js"></script>
</body>
</html>
```

`ui/static/app.js`:
```javascript
/* Vanilla-JS client for the memory-chat console (no build step). */
"use strict";

let owner = "alice";
const history = { alice: [], bob: [] };

const $ = (id) => document.getElementById(id);
const show = (id) => $(id).classList.remove("hidden");

function setActiveOwner() {
  document.querySelectorAll("#owners button").forEach((b) => {
    b.classList.toggle("active", b.dataset.owner === owner);
  });
  renderThread();
}

function bubble(sender, text, cited) {
  const chips = (cited ?? [])
    .map((c) => `<span class="chip">${c}</span>`)
    .join("");
  return `<div class="bubble ${sender}"><p>${text}</p>${chips}</div>`;
}

function renderThread() {
  $("thread").innerHTML = history[owner]
    .map((t) => bubble(t.sender, t.text, t.cited))
    .join("");
}

async function loadFacts() {
  const res = await fetch(`/api/facts/${owner}`);
  const data = await res.json();
  $("facts").innerHTML = data.triples.length
    ? data.triples.map((t) => `<li><code>${t[0]}·${t[1]}·${t[2]}</code></li>`).join("")
    : "<li class='muted'>nothing yet</li>";
}

async function send(event) {
  event.preventDefault();
  hideError();
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ owner, text: $("message").value }),
  });
  if (!res.ok) return showError((await res.json()).error);
  const body = await res.json();
  history[owner].push({ sender: "user", text: $("message").value });
  history[owner].push({ sender: "bot", text: body.reply, cited: body.cited });
  $("message").value = "";
  renderThread();
  loadFacts();
}

async function runDemo() {
  hideError();
  const body = await (await fetch("/api/demo", { method: "POST" })).json();
  history.alice = [];
  history.bob = [];
  body.transcript.forEach((t) =>
    history[t.owner].push({ sender: "bot", text: `${t.owner}: ${t.reply}` }));
  renderThread();
  loadFacts();
  if (!body.isolation_ok) showError("isolation violated!");
}

function showError(message) {
  $("error").textContent = message;
  show("error");
}

function hideError() {
  $("error").classList.add("hidden");
}

document.querySelectorAll("#owners button").forEach((b) =>
  b.addEventListener("click", () => {
    owner = b.dataset.owner;
    setActiveOwner();
    loadFacts();
  }));
$("ask-form").addEventListener("submit", send);
$("demo-btn").addEventListener("click", runDemo);
setActiveOwner();
loadFacts();
```

`ui/static/style.css`:
```css
/* Memory-chat console theme */
:root { --bg:#12141a; --panel:#1c2130; --ink:#dde5f2; --accent:#7fd18b; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,sans-serif; background:var(--bg); color:var(--ink); }
header { display:flex; align-items:center; gap:1rem; padding:.6rem 1rem; }
header h1 { font-size:1.15rem; margin:0; }
#owners button { background:var(--panel); color:var(--ink); border:1px solid #34405a;
  border-radius:6px; padding:.3rem .7rem; cursor:pointer; }
#owners button.active { background:var(--accent); color:#0c1710; border-color:var(--accent); }
main { display:flex; gap:1rem; padding:0 1rem 1rem; }
#chat-pane { flex:1; background:var(--panel); border-radius:8px; padding:1rem; }
#thread { display:flex; flex-direction:column; gap:.5rem; min-height:240px; }
.bubble { padding:.45rem .65rem; border-radius:8px; max-width:80%; }
.bubble.user { align-self:flex-end; background:#2a3650; }
.bubble.bot { align-self:flex-start; background:#243024; }
.chip { display:inline-block; margin:.25rem .25rem 0 0; padding:.1rem .45rem;
  border-radius:999px; background:#33472f; font-size:.75rem; }
#ask-form { display:flex; gap:.5rem; margin-top:.75rem; }
#message { flex:1; padding:.45rem .6rem; border-radius:6px; border:1px solid #34405a;
  background:#0d1017; color:var(--ink); }
#facts-panel { width:230px; background:var(--panel); border-radius:8px; padding:.75rem; }
#facts li { margin:.25rem 0; }
#demo-btn { margin-top:.6rem; width:100%; padding:.4rem; cursor:pointer;
  border-radius:6px; border:1px solid #34405a; background:#243046; color:var(--ink); }
.hidden { display:none; }
.muted { color:#7e8aa0; }
#error { color:#ff8484; }
```

`src/memory_chat/ui/pages.py`:
```python
"""Chat page — static serving only (logic lives in the API controller)."""

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


class ChatPageController(Controller):
    """Serve the memory-chat console; every handler reads from ui/."""

    def __init__(self) -> None:
        """Stateless."""

    @get("/")
    async def chat(self, request: Request) -> FileResponse:
        """The single-page console."""
        return _view("chat.html")

    @get("/static/style.css")
    async def stylesheet(self, request: Request) -> FileResponse:
        return _static("style.css", "text/css")

    @get("/static/app.js")
    async def app_js(self, request: Request) -> FileResponse:
        return _static("app.js", "text/javascript")


__all__ = ["ChatPageController"]
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest demos/memory-chat/tests -q`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add demos/memory-chat && git commit demos/memory-chat -m "✨ feat(demos): add memory-chat console UI"
```

---

### Task 5: Server entry point

**Files:**
- Create: `src/memory_chat/main.py`
- Create: `src/memory_chat/__main__.py`

- [ ] **Step 1: Implement entry point**

`main.py`:
```python
"""Entry points for the memory-chat demo.

Run::

    PYTHONPATH=demos/memory-chat/src \
        uv run python -m memory_chat          # serves on :8083
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from lexigram.app import Application
from lexigram.web.server.runner import run_server_async

from memory_chat.module import MemoryChatModule


async def _serve(port: int) -> None:
    async with Application.boot(
        name="memory-chat",
        modules=[MemoryChatModule.configure(port=port)],
    ) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await run_server_async(web.starlette, host="127.0.0.1", port=port)


def main() -> int:
    parser = argparse.ArgumentParser(description="Memory chat demo")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MEMORY_CHAT_PORT", "8083")),
    )
    args = parser.parse_args()
    asyncio.run(_serve(args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`__main__.py`:
```python
"""Enable ``python -m memory_chat``."""

from __future__ import annotations

import sys

from memory_chat.main import main

sys.exit(main())
```

- [ ] **Step 2: Manual smoke**

```bash
PYTHONPATH=demos/memory-chat/src timeout 5 uv run python -m memory_chat --port 8088 &
sleep 3
curl -s -X POST http://127.0.0.1:8088/api/chat -H 'Content-Type: application/json' -d '{"owner":"alice","text":"I'\''m vegetarian"}'
curl -s http://127.0.0.1:8088/api/facts/alice
curl -s http://127.0.0.1:8088/ | head -3
```
Expected: chat JSON with `diet: vegetarian` cited; facts triple visible; HTML head.

- [ ] **Step 3: Full suite + commit**

```bash
uv run pytest demos/memory-chat/tests -q
git add demos/memory-chat && git commit demos/memory-chat -m "✨ feat(demos): add memory-chat server entry point"
```

---

### Task 6: README + Makefile gating + gates

**Files:**
- Create: `demos/memory-chat/README.md`
- Modify: `Makefile:114-115`
- Modify: `demos/README.md`

- [ ] **Step 1: Makefile append (diff-first, never clobber other lanes)**

Add `demos/memory-chat/tests` to `DEMO_TEST_DIRS`, `demos/memory-chat` to
`DEMO_COMPILE_DIRS`.

- [ ] **Step 2: READMEs**

`demos/README.md` section:

```markdown
### 🧠 [memory-chat](memory-chat/) — conversational memory, zero LLM

A concierge that remembers what you tell it:

- 💬 **Facts persist** — stated once, cited turns later via episodic + semantic stores
- 👥 **Two-owner console** — alice's allergies never leak into bob's session
- 🎬 **Demo replay** — scripted two-session transcript proves recall AND isolation
- 🚫 **No model calls** — deterministic template responder keeps runs byte-stable
```

Demo-local README expands: layout note (flat house shape + swappable
`ui/`), commands, what it proves, gotchas pointer.

- [ ] **Step 3: Gates**

```bash
uv run ruff check demos/memory-chat && uv run ruff format --check demos/memory-chat
make test-demos && make verify-demos
find demos/memory-chat -name "*.py" | xargs wc -l | sort -n   # all <500
git status --short                                            # expected paths only
```

- [ ] **Step 4: Commit**

```bash
git add demos/README.md demos/memory-chat/README.md Makefile && git commit demos/README.md demos/memory-chat/README.md Makefile -m "📝 docs(demos): document memory-chat and gate make targets"
```

---

## Self-Review Notes

- Spec coverage: flat layout ✓, extraction rules incl. subject=owner ✓(T1), responder templates ✓(T2), deterministic entries (fabricated id/timestamp) ✓(T3), cross-owner isolation via shared backend ✓(T3 both levels), demo replay stability ✓(T3/T5), ui/pages named-by-page ✓(T4), ports/env naming ✓(T5).
- Spec deviation fixed during planning: §6 said unknown-owner ⇒ 404; any owner string is valid, so facts endpoints return an empty snapshot instead — plan defines that behavior; update the spec line when executing Task 3 (one-line edit).
- Type consistency: `TurnResult/FactsSnapshot/DemoResult` used identically in service, API serialization, and tests; `Triple` shared between extraction/responder.
- Known risks: `get_entity_facts` returned-dict keys pinned against contracts/ai/memory.py:292-353 at implementation; `MemoryProvider` must bind all three protocol tokens (verified in exploration) — never construct backends in our provider.
