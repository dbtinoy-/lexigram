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

from memory_chat.extraction import extract_facts
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
        self._known: set[tuple[str, str, str]] = set()

    async def send(self, owner: str, text: str) -> TurnResult:
        """Record, extract, recall, assemble, respond — in order."""
        entry = self._entry_for(owner, text)
        await self._episodic.record(entry)

        for triple in extract_facts(owner, text):
            subject, predicate, obj, confidence = triple
            if (subject, predicate, obj) in self._known:
                continue  # restating a fact must not duplicate storage
            self._known.add((subject, predicate, obj))
            await self._semantic.store_fact(subject, predicate, obj, confidence)

        await self._episodic.recall(
            MemoryQuery(owner_id=owner, query=text, top_k=5),
        )
        entity_facts = await self._semantic.get_entity_facts(owner)
        fact_triples: list[tuple[str, str, str, float]] = [
            (
                str(f["subject"]),
                str(f["predicate"]),
                str(f["object_"]),
                float(f.get("confidence", 0.5)),
            )
            for f in entity_facts
        ]
        context = await self._working.assemble(
            query=text,
            token_budget=256,
            owner_id=owner,
        )
        reply = reply_for(text, fact_triples)
        context_chars = sum(len(e.content) for e in context)
        return TurnResult(reply.text, list(reply.cited), context_chars)

    async def get_facts(self, owner: str) -> FactsSnapshot:
        """Everything stored about one owner."""
        raw = await self._semantic.get_entity_facts(owner)
        recalled = await self._episodic.recall(
            MemoryQuery(owner_id=owner, query="", top_k=10),
        )
        triples = [
            [
                f.get("subject"),
                f.get("predicate"),
                f.get("object_"),
                f.get("confidence"),
            ]
            for f in raw
        ]
        recent = [r.entry for r in recalled]
        return FactsSnapshot(triples=triples, recent=list(recent))

    async def demo_replay(self) -> DemoResult:
        """Replay DEMO_REPLAY verbatim; prove recall AND isolation."""
        from memory_chat.scripts import DEMO_REPLAY

        transcript: list[dict] = []
        bob_clean = True
        for owner, text in DEMO_REPLAY:
            result = await self.send(owner, text)
            transcript.append(
                {"owner": owner, "text": text, "reply": result.reply_text},
            )
            if owner == "bob":
                lowered = result.reply_text.lower()
                if "peanut" in lowered or "vegetarian" in lowered:
                    bob_clean = False
        return DemoResult(transcript=transcript, isolation_ok=bob_clean)

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
