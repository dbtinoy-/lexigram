# 🧠 memory-chat — conversational memory, zero LLM

> A personal concierge that remembers what you tell it. Facts stated in
> turn 1 shape replies turns later — and never leak across owners.
> No model anywhere: a deterministic template responder proves the memory
> subsystem works standalone.

## What it proves

- **Episodic recall** — every turn recorded; `MemoryQuery` recall feeds
  later replies
- **Semantic facts** — regex extraction ("I'm allergic to X") →
  subject/predicate/object triples via `store_fact`
- **Working-memory assembly** — token-budgeted context assembled each turn
  (`context_chars` shown per response)
- **Owner isolation** — semantic memory isn't owner-scoped by contract, so
  subject namespacing (`subject == owner_id`) carries isolation; bob's
  console proves it live
- **Deterministic entries** — fabricated ids/timestamps (fixed epoch),
  no wall clock

## Layout

House flat structure with auth-web's co-located `ui/`. The chat page has
alice/bob tabs, a shared thread view, and a facts sidebar.

## Run

```bash
PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat
# → http://127.0.0.1:8083  (override: --port / MEMORY_CHAT_PORT)
```

Try: as alice say *"I'm vegetarian"* then *"I'm allergic to peanuts"*, then
ask for a dinner menu — the reply cites both constraints. Switch to bob and
ask the same: *"anything goes."* The **Run demo replay** button scripts the
whole two-session story.

## Tests

```bash
uv run pytest demos/memory-chat/tests -q
```

