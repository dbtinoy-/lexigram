"""Orchestration across episodic, semantic, and working memory.

This is the **domain service** — it owns the use-case logic ("record →
extract → recall → respond") and delegates storage to the repository
facade.  No framework imports except ``Result``, ``clock``, and
``MemoryEntry`` — the service is framework-agnostic by design.

The three-tier memory flow per turn:

1. **Record** — append the user's message to episodic memory
2. **Extract** — regex-fact extraction → semantic store_fact (deduped)
3. **Recall** — episodic recall + semantic facts_for → responder input
4. **Respond** — deterministic template selection from recalled context

Consolidation (episodic → semantic promotion) is switched off so demo
conversations stay deterministic — every store starts empty per process.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.ai.memory import MemoryEntry
from lexigram.contracts.exceptions.domain import ValidationError
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.result import Err, Ok, Result
from memory_chat.repository.memory_repository import MemoryRepository
from memory_chat.services.extraction import extract_facts
from memory_chat.services.responder import reply_for


class EmptyMessageError(ValidationError):
    """Raised when a turn carries no message text."""


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


logger = get_logger(__name__)


class ConciergeService:
    """Drives one turn through record → extract → recall → respond.

    Constructed by ConciergeProvider during boot; all collaborators arrive
    via constructor injection.  The repository facade is resolved from
    ``MemoryModule``'s three protocol bindings (working/episodic/semantic).

    The service is stateful across turns (``_turns`` counter, ``_known``
    dedup set) but stateless per request — each turn is independent.
    """

    def __init__(self, repository: MemoryRepository) -> None:
        self._repo = repository
        self._turns: dict[str, int] = {}
        self._known: set[tuple[str, str, str]] = set()

    async def send(
        self, owner: str, text: str
    ) -> Result[TurnResult, EmptyMessageError]:
        """Record, extract, recall, assemble, respond — in order.

        Returns ``Ok(TurnResult)`` on success with the reply text,
        cited constraint facts, and working-memory character count.
        Returns ``Err(EmptyMessageError)`` for blank messages.
        """
        cleaned = text.strip()
        if not cleaned:
            return Err(EmptyMessageError("message text is required"))

        # 1. Record — append to episodic memory
        entry = self._entry_for(owner, cleaned)
        await self._repo.record_turn(entry)

        # 2. Extract — regex facts → semantic store (deduped)
        for triple in extract_facts(owner, cleaned):
            if triple[:3] in self._known:
                continue  # restating a fact must not duplicate storage
            self._known.add(triple[:3])
            await self._repo.save_fact(triple)

        # 3. Recall — episodic + semantic → responder input
        facts = await self._repo.facts_for(owner)
        context_chars = await self._repo.context_chars(owner, cleaned)

        # 4. Respond — deterministic template selection
        reply = reply_for(cleaned, facts)
        logger.info(
            "chat_turn_processed",
            owner=owner,
            cited=len(reply.cited),
            context_chars=context_chars,
        )
        return Ok(TurnResult(reply.text, list(reply.cited), context_chars))

    async def get_facts(self, owner: str) -> FactsSnapshot:
        """Everything stored about one owner (empty snapshot if unknown).

        Returns semantic triples and recent episodic entries — the two
        memory tiers the demo Demonstrates.
        """
        triples = [list(t) for t in await self._repo.facts_for(owner)]
        recent = await self._repo.recent(owner)
        return FactsSnapshot(triples=triples, recent=list(recent))

    async def demo_replay(self) -> DemoResult:
        """Replay DEMO_REPLAY verbatim; prove recall AND isolation.

        Runs alice (diet + allergy → menu) then bob (no facts → "anything
        goes").  The ``isolation_ok`` flag confirms bob never sees alice's
        facts — the core teaching point of this demo.
        """
        from memory_chat.repository.demo_script import DEMO_REPLAY

        transcript: list[dict] = []
        bob_clean = True
        for owner, text in DEMO_REPLAY:
            result = await self.send(owner, text)
            turn = result.unwrap()
            transcript.append(
                {"owner": owner, "text": text, "reply": turn.reply_text},
            )
            if owner == "bob":
                lowered = turn.reply_text.lower()
                if "peanut" in lowered or "vegetarian" in lowered:
                    bob_clean = False
        return DemoResult(transcript=transcript, isolation_ok=bob_clean)

    def _entry_for(self, owner: str, text: str) -> MemoryEntry:
        """Build the entry; timestamp comes from the ambient clock.

        Uses ``lexigram.primitives.clock`` for testable time — tests
        can freeze it with ``clock.use(FixedClock(...))``.
        """
        n = self._turns.get(owner, 0)
        self._turns[owner] = n + 1
        has_facts = bool(extract_facts(owner, text))
        return MemoryEntry(
            id=f"{owner}:{n}",
            owner_id=owner,
            content=text,
            role="user",
            timestamp=clock.now(),
            importance=0.9 if has_facts else 0.5,
        )
