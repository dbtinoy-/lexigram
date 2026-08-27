"""Memory access behind one repository facade — the **protocol binding** lesson.

Wraps the three framework contracts (working/episodic/semantic) so the
service never touches store APIs directly.  ``MemoryModule`` registers
the three protocols; ``ConciergeProvider.boot`` resolves them and hands
them here::

    container.singleton(MemoryRepository, factory=self._build_repository)

...so the service resolves the facade while tests can import the
concrete class.  Swap this file for a vector-database implementation and
nothing else changes.

Each method maps 1:1 to one contract method — the facade adds no logic,
just convenience.  This is intentional: the demo teaches memory *usage*,
not abstraction over abstraction.
"""

from __future__ import annotations

from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    MemoryEntry,
    MemoryQuery,
    SemanticMemoryProtocol,
    WorkingMemoryProtocol,
)

Triple = tuple[str, str, str, float]


class MemoryRepository:
    """Record/recall/fact operations over the memory subsystem.

    This is the **protocol binding** pattern: ``WorkingMemoryProtocol``,
    ``EpisodicMemoryProtocol``, and ``SemanticMemoryProtocol`` live in
    ``lexigram.contracts.ai.memory``; this class supplies a unified
    facade over all three.  ``di/provider.py`` resolves the protocols
    from the container and hands them here — the service never touches
    store APIs directly.

    To swap for a vector-database or cache-backed implementation,
    replace this class and update di/provider.py — nothing else changes.
    """

    def __init__(
        self,
        working: WorkingMemoryProtocol,
        episodic: EpisodicMemoryProtocol,
        semantic: SemanticMemoryProtocol,
    ) -> None:
        self._working = working
        self._episodic = episodic
        self._semantic = semantic

    async def record_turn(self, entry: MemoryEntry) -> None:
        """Append one conversational entry to episodic memory.

        Uses ambient clock (``lexigram.primitives.clock``) for testable
        time — tests can freeze it with ``clock.use(FixedClock(...))``.
        """
        await self._episodic.record(entry)

    async def recall(self, owner: str, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Most relevant past entries for an owner.

        Delegates to ``EpisodicMemoryProtocol.recall`` with a
        ``MemoryQuery`` — the framework ranks by recency, importance,
        and relevance (configurable via ``ai_memory.episodic``).
        """
        results = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query=query, top_k=top_k),
        )
        return [r.entry for r in results]

    async def save_fact(self, triple: Triple) -> None:
        """Store one (subject, predicate, object, confidence) fact.

        Subject is ALWAYS the owner_id: semantic memory is not
        owner-scoped by contract, so subject namespacing is what
        keeps users isolated.
        """
        subject, predicate, obj, confidence = triple
        await self._semantic.store_fact(subject, predicate, obj, confidence)

    async def facts_for(self, owner: str) -> list[Triple]:
        """All stored triples mentioning the owner (subject namespaced).

        Returns a list of ``(subject, predicate, object, confidence)``
        tuples — the shape the responder template engine expects.
        """
        raw = await self._semantic.get_entity_facts(owner)
        return [
            (
                str(f["subject"]),
                str(f["predicate"]),
                str(f["object_"]),
                float(f.get("confidence", 0.5)),
            )
            for f in raw
        ]

    async def recent(self, owner: str, limit: int = 10) -> list[MemoryEntry]:
        """Recent entries for an owner (recall-based snapshot).

        Uses recall with an empty query to get the most recent entries
        by recency score — not a direct store scan.
        """
        recalled = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query="", top_k=limit),
        )
        return [r.entry for r in recalled]

    async def context_chars(self, owner: str, query: str) -> int:
        """Total characters of the token-budgeted working context.

        Assembles the working-memory context (system prompt + recent
        turns + episodic recall + semantic facts) and returns the
        total character count — shown per response so users see the
        budget in action.
        """
        context = await self._working.assemble(
            query=query,
            token_budget=256,
            owner_id=owner,
        )
        return sum(len(e.content) for e in context)
