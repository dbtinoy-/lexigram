"""In-process fact store — stores subject/predicate/object triples."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


@dataclass
class StoredFact:
    """A single structured knowledge triple."""

    id: str
    subject: str
    predicate: str
    object_: str
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


class FactStore:
    """In-memory graph of subject/predicate/object facts.

    Used by SemanticMemoryStore to persist extracted knowledge.
    """

    def __init__(self) -> None:
        """Initialise an empty fact store."""
        self._facts: dict[str, StoredFact] = {}

    def add(
        self,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 1.0,
        metadata: dict | None = None,
    ) -> str:
        """Add a new fact triple.

        Args:
            subject: Subject entity.
            predicate: Relationship type.
            object_: Object value.
            confidence: Confidence score in [0.0, 1.0].
            metadata: Optional additional metadata.

        Returns:
            Unique ID assigned to the stored fact.
        """
        fact_id = str(uuid4())
        self._facts[fact_id] = StoredFact(
            id=fact_id,
            subject=subject,
            predicate=predicate,
            object_=object_,
            confidence=confidence,
            metadata=metadata or {},
        )
        logger.debug(
            "fact_added", fact_id=fact_id, subject=subject, predicate=predicate
        )
        return fact_id

    def query_by_subject(self, subject: str) -> list[dict]:
        """Return all facts where subject matches (case-insensitive prefix).

        Args:
            subject: Subject to filter by.

        Returns:
            List of fact dicts (id, subject, predicate, object_, confidence).
        """
        lower = subject.lower()
        return [
            {
                "id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "object_": f.object_,
                "confidence": f.confidence,
                **f.metadata,
            }
            for f in self._facts.values()
            if f.subject.lower().startswith(lower)
        ]

    def get_entity_facts(self, entity: str) -> list[dict]:
        """Return all facts mentioning *entity* as subject or object.

        Args:
            entity: Entity name to search.

        Returns:
            List of matching fact dicts.
        """
        lower = entity.lower()
        return [
            {
                "id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "object_": f.object_,
                "confidence": f.confidence,
                **f.metadata,
            }
            for f in self._facts.values()
            if lower in f.subject.lower() or lower in f.object_.lower()
        ]

    def update_confidence(self, fact_id: str, confidence: float) -> None:
        """Update the confidence of an existing fact.

        Args:
            fact_id: ID of the fact to update.
            confidence: New confidence value in [0.0, 1.0].
        """
        if fact_id in self._facts:
            fact = self._facts[fact_id]
            self._facts[fact_id] = StoredFact(
                id=fact.id,
                subject=fact.subject,
                predicate=fact.predicate,
                object_=fact.object_,
                confidence=confidence,
                metadata=fact.metadata,
            )

    def delete(self, fact_id: str) -> None:
        """Remove a fact.

        Args:
            fact_id: ID of the fact to remove.
        """
        self._facts.pop(fact_id, None)

    def clear(self) -> None:
        """Remove all facts."""
        self._facts.clear()

    def __len__(self) -> int:
        return len(self._facts)


__all__ = ["FactStore", "StoredFact"]
