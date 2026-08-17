"""Semantic memory store — structured subject/predicate/object knowledge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.memory.semantic.fact_store import FactStore
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.memory.semantic.entity_extractor import EntityExtractor
    from lexigram.contracts.ai.memory import MemoryEntry

logger = get_logger(__name__)


class SemanticMemoryStore:
    """Semantic memory backed by an in-process FactStore."""

    def __init__(
        self,
        fact_store: FactStore | None = None,
        extractor: EntityExtractor | None = None,
        min_confidence: float = 0.5,
        max_facts_per_entity: int = 100,
    ) -> None:
        self._facts = fact_store or FactStore()
        self._extractor = extractor
        self._min_confidence = min_confidence
        self._max_facts = max_facts_per_entity

    async def store_fact(
        self,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 1.0,
    ) -> str:
        existing = self._facts.query_by_subject(subject)
        if len(existing) >= self._max_facts:
            logger.warning(
                "semantic_max_facts_reached",
                subject=subject,
                cap=self._max_facts,
            )
            lowest = min(existing, key=lambda fact: fact["confidence"])
            self._facts.delete(lowest["id"])

        return self._facts.add(subject, predicate, object_, confidence)

    async def query_facts(self, subject: str) -> list[dict[str, Any]]:
        return [
            fact
            for fact in self._facts.query_by_subject(subject)
            if fact["confidence"] >= self._min_confidence
        ]

    async def get_entity_facts(self, entity: str) -> list[dict[str, Any]]:
        return [
            fact
            for fact in self._facts.get_entity_facts(entity)
            if fact["confidence"] >= self._min_confidence
        ]

    async def update_fact(self, fact_id: str, confidence: float) -> None:
        self._facts.update_confidence(fact_id, confidence)

    async def ingest(self, entry: MemoryEntry) -> int:
        if not self._extractor:
            return 0
        triples = await self._extractor.extract(entry)
        count = 0
        for subject, predicate, object_ in triples:
            await self.store_fact(subject, predicate, object_, confidence=0.8)
            count += 1
        return count

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="memory.semantic",
            status=HealthStatus.HEALTHY,
            details={"facts": len(self._facts), "timeout": timeout},
        )


__all__ = ["SemanticMemoryStore"]
