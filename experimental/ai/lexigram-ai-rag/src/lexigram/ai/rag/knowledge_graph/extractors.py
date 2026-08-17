from __future__ import annotations

from datetime import UTC, datetime

from lexigram import serialization as json
from lexigram.ai.rag.exceptions import RAGError
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from lexigram.contracts import (
    LLMClientProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage, Role
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class EntityExtractor:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        entity_types: list[EntityType | str] | None = None,
        min_confidence: float = 0.5,
    ) -> None:
        self.llm_client = llm_client
        self.entity_types = entity_types
        self.min_confidence = min_confidence

    async def extract(self, text: str) -> list[Entity]:
        # Call the LLM to extract entities as JSON and parse the result.
        try:
            result = await self.llm_client.complete(
                [ChatMessage(role=Role.USER, content=text)],
            )
            if result.is_err():
                raise result.unwrap_err()
            completion = result.unwrap()

            parsed = json.loads(completion.content)
            entities: list[Entity] = []
            for e in parsed:
                name = e.get("name")
                if not isinstance(name, str):
                    continue

                ent = Entity(
                    name=name,
                    type=e.get("type", EntityType.OTHER),
                    properties=e.get("properties", {}),
                    metadata={"extraction_time": datetime.now(UTC).isoformat()},
                )
                entities.append(ent)

            return entities
        except json.JSONDecodeError as e:
            logger.exception(
                "Failed to parse entity extraction JSON. Content: %s",
                completion.content,
            )
            return []
        except Exception as e:
            logger.exception("Unexpected error during entity extraction")
            raise RAGError(f"Entity extraction failed: {e}") from e


class RelationshipExtractor:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        relationship_types: list[RelationshipType | str] | None = None,
        min_confidence: float = 0.5,
    ) -> None:
        self.llm_client = llm_client
        self.relationship_types = relationship_types
        self.min_confidence = min_confidence

    async def extract(
        self,
        text: str,
        entities: list[Entity] | None = None,
    ) -> list[Relationship]:
        try:
            result = await self.llm_client.complete(
                [ChatMessage(role=Role.USER, content=text)],
            )
            if result.is_err():
                raise result.unwrap_err()
            completion = result.unwrap()

            rels_data = json.loads(completion.content)
            relationships: list[Relationship] = []
            for data in rels_data:
                if isinstance(data, dict) and "source" in data and "target" in data:
                    rel = Relationship(
                        source=data["source"],
                        target=data["target"],
                        type=data.get("type", RelationshipType.OTHER),
                        confidence=data.get("confidence", 1.0),
                        metadata={"extraction_time": datetime.now(UTC).isoformat()},
                    )
                    if rel.confidence >= self.min_confidence:
                        relationships.append(rel)
            return relationships
        except json.JSONDecodeError:
            logger.exception(
                "Failed to parse relationship extraction JSON. Content: %s",
                completion.content,
            )
            return []
        except Exception as e:
            logger.exception("Unexpected error during relationship extraction")
            raise RAGError(f"Relationship extraction failed: {e}") from e
