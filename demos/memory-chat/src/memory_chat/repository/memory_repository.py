"""Memory access behind one repository façade.

Wraps the three framework contracts (working/episodic/semantic) so the
service never touches store APIs directly.
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
    """Record/recall/fact operations over the memory subsystem."""

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
        """Append one conversational entry to episodic memory."""
        await self._episodic.record(entry)

    async def recall(self, owner: str, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Most relevant past entries for an owner."""
        results = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query=query, top_k=top_k),
        )
        return [r.entry for r in results]

    async def save_fact(self, triple: Triple) -> None:
        """Store one (subject, predicate, object, confidence) fact."""
        subject, predicate, obj, confidence = triple
        await self._semantic.store_fact(subject, predicate, obj, confidence)

    async def facts_for(self, owner: str) -> list[Triple]:
        """All stored triples mentioning the owner (subject namespaced)."""
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
        """Recent entries for an owner (recall-based snapshot)."""
        recalled = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query="", top_k=limit),
        )
        return [r.entry for r in recalled]

    async def context_chars(self, owner: str, query: str) -> int:
        """Total characters of the token-budgeted working context."""
        context = await self._working.assemble(
            query=query,
            token_budget=256,
            owner_id=owner,
        )
        return sum(len(e.content) for e in context)
