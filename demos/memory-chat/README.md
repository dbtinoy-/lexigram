# memory-chat — conversational memory, zero LLM

> Module name: `memory_chat` — run with `PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat`

A personal concierge that remembers what you tell it. Facts stated in
turn 1 shape replies turns later — and never leak across owners. No model
anywhere: a deterministic template responder proves the memory subsystem
works standalone.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Module pattern | `MemoryModule` | Add your own modules |
| Provider lifecycle | `di/provider.py` | Replace with your registrations |
| Result<T,E> pattern | `controllers/api.py` | Return Result from handlers |
| Protocol binding | `repository/memory_repository.py` | Swap impl for vector DB/etc |
| Constructor injection | Everywhere | Declare deps as typed params |
| Domain models | `services/*.py` | Plain dataclasses, no framework imports |
| Ambient clock | `chat_service.py`, `memory_repository.py` | `clock.use(FixedClock(...))` for tests |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Three-tier memory | `app.py` | `MemoryModule` registers working/episodic/semantic protocols |
| Episodic record + recall | `repository/memory_repository.py` | `EpisodicMemoryProtocol.record`, `.recall(MemoryQuery)` |
| Semantic fact storage | `repository/memory_repository.py` | `SemanticMemoryProtocol.store_fact`, `.get_entity_facts` |
| Working-memory assembly | `repository/memory_repository.py` | `WorkingMemoryProtocol.assemble(query, token_budget)` |
| Regex extraction | `services/extraction.py` | Pure function — no framework imports |
| Template responder | `services/responder.py` | Pure function — no framework imports |
| Owner isolation | `repository/memory_repository.py` | Subject namespacing (`subject == owner_id`) |
| Scripted demo replay | `services/chat_service.py` | Proves recall + cross-owner isolation |

## Memory tiers

```
┌─────────────────────────────────────────────────────────────┐
│                    memory-chat demo                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐   record    ┌──────────────┐                  │
│  │  User    │────────────→│   Episodic   │  every turn      │
│  │  input   │             │   memory     │  stored by id    │
│  └────┬─────┘             └──────┬───────┘                  │
│       │                          │ recall(MemoryQuery)      │
│       │ extract_facts            │                          │
│       ▼                          ▼                          │
│  ┌──────────┐   store_fact  ┌──────────────┐                │
│  │ Semantic │←──────────────│   Working    │  token-budgeted │
│  │ memory   │  facts_for()  │   memory     │  context each   │
│  └──────────┘               └──────────────┘  turn           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Run it

From this demo's root (so `application.yaml` is discovered):

```bash
cd demos/memory-chat
PYTHONPATH=src uv run python -m memory_chat
```

Open http://127.0.0.1:8083. The chat page has alice/bob tabs, a shared
thread view, and a facts sidebar.  Override the port without touching
yaml: `LEX_WEB__SERVER__PORT=9000`.

Try: as alice say *"I'm vegetarian"* then *"I'm allergic to peanuts"*, then
ask for a dinner menu — the reply cites both constraints. Switch to bob and
ask the same: *"anything goes."* The **Run demo replay** button scripts the
whole two-session story.

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/memory_chat/app.py` | Composition root: config → modules → providers |
| 2 | `src/memory_chat/main.py` | Lifecycle: `Application.start/stop`, graceful shutdown |
| 3 | `src/memory_chat/di/provider.py` | `register()` (bind) vs `boot()` (initialize); DI patterns |
| 4 | `src/memory_chat/repository/memory_repository.py` | Protocol binding (contracts ↔ implementation) |
| 5 | `src/memory_chat/controllers/api.py` | Result-returning handlers → auto HTTP status mapping |
| 6 | `src/memory_chat/services/chat_service.py` | Domain service: record → extract → recall → respond |
| 7 | `src/memory_chat/services/extraction.py` | Regex extraction — pure function, no framework imports |
| 8 | `src/memory_chat/services/responder.py` | Template responder — pure function, no framework imports |
| 9 | `src/memory_chat/ui/pages.py` | Page controller: serve HTML/assets only, no logic |

```
demos/memory-chat/
├── src/memory_chat/
│   ├── app.py                          # composition root (start here)
│   ├── main.py                         # entry point / lifecycle
│   ├── __main__.py                     # python -m memory_chat
│   ├── di/
│   │   ├── __init__.py                 # DI wiring
│   │   └── provider.py                 # register() + boot() seeding
│   ├── repository/
│   │   ├── memory_repository.py        # protocol binding (3 protocols)
│   │   └── demo_script.py              # scripted two-session replay
│   ├── controllers/api.py              # JSON API: chat/facts/demo
│   ├── services/
│   │   ├── chat_service.py             # domain service orchestration
│   │   ├── extraction.py               # regex fact extraction
│   │   └── responder.py                # template reply renderer
│   ├── ui/                             # pages controller + views/ + static/
│   └── data/                           # empty (memory is the data layer)
├── application.yaml                    # web/ai_memory sections (LEX_* overrides win)
└── tests/                              # 23 tests: service, extraction, responder, e2e
```

## Tests

```bash
uv run pytest demos/memory-chat/tests -q
```

Covers: extraction rules, template selection, fact deduplication, isolated
replay (bob never sees alice's facts), cross-owner isolation, ambient clock
determinism, and end-to-end chat/facts/demo HTTP endpoints via ASGITransport.
