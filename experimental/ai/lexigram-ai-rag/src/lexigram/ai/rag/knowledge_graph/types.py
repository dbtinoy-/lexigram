from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EntityType(StrEnum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    CONCEPT = "CONCEPT"
    DATE = "DATE"
    OTHER = "OTHER"


class RelationshipType(StrEnum):
    WORKS_AT = "WORKS_AT"
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    RELATED_TO = "RELATED_TO"
    CREATED_BY = "CREATED_BY"
    OCCURRED_AT = "OCCURRED_AT"
    IS_A = "IS_A"
    HAS_PROPERTY = "HAS_PROPERTY"
    OTHER = "OTHER"


@dataclass
class Entity:
    name: str
    type: EntityType | str = EntityType.OTHER
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.name.lower(), self.type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.name.lower() == other.name.lower() and self.type == other.type


@dataclass
class Relationship:
    source: str
    target: str
    type: RelationshipType | str = RelationshipType.OTHER
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source.lower(), self.target.lower(), self.type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Relationship):
            return False
        return (
            self.source.lower() == other.source.lower()
            and self.target.lower() == other.target.lower()
            and self.type == other.type
        )


@dataclass
class GraphPath:
    entities: list[str]
    relationships: list[Relationship]
    length: int
    score: float = 1.0

    def __repr__(self) -> str:
        if not self.entities:
            return "Empty path"
        parts = [self.entities[0]]
        for i, rel in enumerate(self.relationships):
            parts.append(f"--{rel.type}-->")
            parts.append(self.entities[i + 1])
        return " ".join(parts)
