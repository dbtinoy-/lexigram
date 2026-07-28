"""Semantic memory — structured subject/predicate/object knowledge storage."""

from __future__ import annotations

from lexigram.ai.memory.semantic.entity_extractor import EntityExtractor
from lexigram.ai.memory.semantic.fact_store import FactStore, StoredFact
from lexigram.ai.memory.semantic.store import SemanticMemoryStore

__all__ = [
    "EntityExtractor",
    "FactStore",
    "SemanticMemoryStore",
    "StoredFact",
]
