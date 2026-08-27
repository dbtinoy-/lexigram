# Demo Spec — `memory-chat` (remember: persistent conversational memory, web UI)

**Date:** 2026-08-22
**Status:** Draft for review
**Showcases:** `lexigram-ai-memory` — episodic recall, semantic facts, working-memory assembly across turns and sessions.
**Portfolio position:** Second AI demo — answers *"can it remember?"*
**Structure rationale:** Single-module demo ⇒ house Pattern-2 flat package (`module.py` + `di/provider.py`). Interaction is the artifact ⇒ auth-web pattern verbatim: `ui/pages.py` co-located with `views/`+`static/`.

---

## 1. Scenario

A personal concierge chat. The user states facts early ("I'm vegetarian",
"allergic to peanuts") that shape replies many turns later and across
sessions. Proves memory works **standalone** — no LLM anywhere; replies
come from a deterministic template responder driven by what the memory
stores recalled. Two owner tabs (alice/bob) make isolation visible: bob
never sees alice's allergies.

## 2. Layout

```
demos/memory-chat/
├── conftest.py                        # sys.path shim (src/) + app/client fixtures
├── README.md
└── src/memory_chat/
    ├── __init__.py
    ├── main.py                        # python -m memory chat (see env below)
    ├── module.py                      # @module (see wiring)
    ├── di/provider.py                 # internal provider
    ├── controllers/
    │   ├── __init__.py
    │   └── api.py                     # JSON logic only
    └── ui/                            # auth-web pattern: assets beside static routes
        ├── __init__.py                # docstring only
        ├── pages.py                   # single static-serving controller
        ├── views/
        │   └── chat.html            # owner tabs · thread · facts sidebar
        └── static/
            ├── app.js
            └── style.css
tests/
├── __init__.py
├── test_extraction.py
├── test_responder.py
├── test_chat_service.py               # recall across turns + owner scoping
├── test_pages.py
└── test_api.py                        # end-to-end turns + demo replay
```

## 3. Module wiring

```python
@module()
class MemoryChatModule(Module):
    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                MemoryModule.configure(
                    MemoryConfig(default_backend="in_memory"),
                    enable_consolidation=False,   # no background timer: determinism
                ),
                WebModule.configure(
                    controllers=[ConciergeApiController, ChatPageController],
                    web_config=_web_config(port),
                ),
            ],
            providers=[ConciergeProvider],
            exports=[ConciergeService],
        )
```

`ConciergeProvider.boot()` resolves `WorkingMemoryProtocol`,
`EpisodicMemoryProtocol`, `SemanticMemoryProtocol` (exported by
`MemoryModule`) and assembles `ConciergeService`. Port default 8083 via
`MEMORY_CHAT_PORT`.

## 4. Components

| Component | Implementation |
|---|---|
| `extraction.py` | Pure regex rules for "I am X", "I have X", "I like X", "I'm allergic to X" → `(subject, predicate, object_, confidence)` triples. **Subject is always the `owner_id`** — semantic memory is not owner-scoped by contract, subject namespacing is what isolates users |
| `responder.py` | Template selection over recalled context: dietary/allergy intents cite matching facts verbatim; fallback acknowledges turn |
| `chat_service.py` | One turn: episodic `record()` → extract → new triples via `semantic.store_fact()` → recall via `episodic.recall(MemoryQuery(top_k=5))` + `semantic.get_entity_facts(owner_id)` → working-context assembly logged via `WorkingMemory.assemble(query, token_budget, owner_id=…)` → reply + cited-fact list. **Entry construction:** `MemoryEntry.id`/`timestamp` are required (memory.py:16-38) — use `id=f"{owner}:{turn_n}"` and fabricated timestamps (`datetime(2026,1,1) + timedelta(seconds=turn_index)`); never wall clock |
| `scripts.py` | `DEMO_REPLAY`: ordered (owner, text) pairs replaying alice's fact-stating turns then bob's identical question |
| `api.py` | `POST /api/chat {owner, text}` → `{reply, cited[], context_chars}`; `GET /api/facts/{owner}` → triples + recent entries; `POST /api/demo` → full two-session replay transcript |

## 5. Request flow

Browser tab switch sets active owner → `POST /api/chat` → turn pipeline
above → JS renders reply bubble + "remembered:" chips (cited facts) and
refreshes facts sidebar. Demo button replays the scripted conversation and
prints the transcript proving recall AND cross-owner isolation in one act.

## 6. Error handling

Store methods are void per protocol (in-memory backend ⇒ no expected
failures). Extraction returns empty list on no match. Facts endpoints
return an empty snapshot for unknown owners (any owner string is valid —
no 404). Empty chat text ⇒ 400. No blind excepts.

## 7. Tests

- `test_extraction.py` — positive/negative patterns, confidence values,
  zero false positives.
- `test_responder.py` — template selection given specific recalled
  context; fallback path.
- `test_chat_service.py` — fact stated turn 1 cited turn N; triple
  persisted under owner-subject; **isolation**: `get_entity_facts("bob")`
  empty after alice's facts through one shared backend.
- `test_pages.py` — `/` markers (tabs alice/bob, ids thread/facts);
  `/static/*` content types.
- `test_api.py` — multi-turn recall e2e; facts endpoint; demo replay
  byte-stable; unknown-owner 404; empty-text 400.

## 8. Integration

- Makefile:114-115 append `demos/memory-chat/tests` / `demos/memory-chat`.
- `demos/README.md` section + run command (:8083).

## 9. Acceptance criteria

- [ ] Server boots offline; console usable at :8083.
- [ ] Demo replay byte-stable across invocations.
- [ ] `make check-demos` green; ruff/format clean; files <500 LOC;
      changes confined to `demos/**` + `Makefile`.
- [ ] Own commit(s) including tests.

## 10. Gotchas

- Every episodic/working call requires `owner_id`; omitting it is the
  classic integration failure.
- `SemanticMemoryProtocol.store_fact()` takes **no `owner_id`** — subject
  namespacing carries isolation; the shared-backend leakage test must
  prove it.
- `enable_consolidation=False` mandatory (background timer breaks
  short-lived determinism).
- In-memory backend scoring is recency/importance-weighted with flat
  relevance — assertions must not assume vector semantics.
- `MemoryEntry.id`/`timestamp` have no defaults (memory.py:16-38) —
  fabricate deterministically per §4 or byte-stability dies.
