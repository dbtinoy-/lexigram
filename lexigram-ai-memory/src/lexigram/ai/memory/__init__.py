"""lexigram-ai-memory — three-tier AI memory for the Lexigram Framework.

Provides working, episodic, and semantic memory tiers with pluggable
backends, consolidation scheduling, and multi-source retrieval.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.ai.memory.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.memory.config import MemoryConfig
    from lexigram.ai.memory.di.provider import MemoryProvider
    from lexigram.ai.memory.events import (
        MemoryRetrievedEvent,
        MemoryStoredEvent,
    )
    from lexigram.ai.memory.hooks import (
        MemoryConsolidatedHook,
        MemoryRetrievedHook,
        MemoryWrittenHook,
    )
    from lexigram.ai.memory.module import MemoryModule
    from lexigram.ai.memory.protocols import (
        ConsolidationStrategyProtocol,
        MemoryIndexProtocol,
    )
    from lexigram.ai.memory.pruning.pruner import DynamicContextPruner
    from lexigram.ai.memory.retrieval.retriever import MemoryRetriever
    from lexigram.ai.memory.working.conversation_buffer import ConversationBuffer

_LAZY_IMPORTS: dict[str, str] = {
    # --- Events ---
    "MemoryRetrievedEvent": "lexigram.ai.memory.events",
    "MemoryStoredEvent": "lexigram.ai.memory.events",
    # --- Hooks ---
    "MemoryConsolidatedHook": "lexigram.ai.memory.hooks",
    "MemoryRetrievedHook": "lexigram.ai.memory.hooks",
    "MemoryWrittenHook": "lexigram.ai.memory.hooks",
    # --- Backends ---
    "CacheMemoryBackend": "lexigram.ai.memory.backends.cache",
    "DatabaseMemoryBackend": "lexigram.ai.memory.backends.database",
    "InMemoryMemoryBackend": "lexigram.ai.memory.backends.in_memory",
    "VectorMemoryBackend": "lexigram.ai.memory.backends.vector",
    # --- Config ---
    "ConsolidationConfig": "lexigram.ai.memory.config",
    "EpisodicMemoryConfig": "lexigram.ai.memory.config",
    "MemoryConfig": "lexigram.ai.memory.config",
    "SemanticMemoryConfig": "lexigram.ai.memory.config",
    "WorkingMemoryConfig": "lexigram.ai.memory.config",
    # --- Consolidation ---
    "MemoryConsolidator": "lexigram.ai.memory.consolidation.consolidator",
    "ConsolidationScheduler": "lexigram.ai.memory.consolidation.scheduler",
    "AccessFrequencyStrategy": "lexigram.ai.memory.consolidation.strategies",
    "DeduplicationStrategy": "lexigram.ai.memory.consolidation.strategies",
    "RecencyDecayStrategy": "lexigram.ai.memory.consolidation.strategies",
    # --- DI ---
    "MemoryModule": "lexigram.ai.memory.module",
    "MemoryProvider": "lexigram.ai.memory.di.provider",
    # --- Episodic ---
    "EpisodicCompressor": "lexigram.ai.memory.episodic.compressor",
    "EpisodicMemoryStore": "lexigram.ai.memory.episodic.store",
    # --- Exceptions ---
    "ConsolidationError": "lexigram.ai.memory.exceptions",
    "EmbeddingError": "lexigram.ai.memory.exceptions",
    "FactExtractionError": "lexigram.ai.memory.exceptions",
    "MemoryCapacityError": "lexigram.ai.memory.exceptions",
    "MemoryStoreError": "lexigram.ai.memory.exceptions",
    "MemorySystemError": "lexigram.ai.memory.exceptions",
    # --- Retrieval ---
    "RelevanceRanker": "lexigram.ai.memory.retrieval.ranking",
    "MemoryRetriever": "lexigram.ai.memory.retrieval.retriever",
    # --- Semantic ---
    "EntityExtractor": "lexigram.ai.memory.semantic.entity_extractor",
    "FactStore": "lexigram.ai.memory.semantic.fact_store",
    "SemanticMemoryStore": "lexigram.ai.memory.semantic.store",
    # --- Stores ---
    "BufferMemoryStore": "lexigram.ai.memory.stores.buffer",
    "ConversationMemoryStore": "lexigram.ai.memory.stores.conversation",
    "EntityMemoryStore": "lexigram.ai.memory.stores.entity",
    "SummaryMemoryStore": "lexigram.ai.memory.stores.summary",
    # --- Pruning ---
    "DynamicContextPruner": "lexigram.ai.memory.pruning.pruner",
    "HybridScorerImpl": "lexigram.ai.memory.pruning.scorer",
    "RecencyScorerImpl": "lexigram.ai.memory.pruning.scorer",
    "RelevanceScorerProtocol": "lexigram.ai.memory.pruning.scorer",
    "PruningResult": "lexigram.ai.memory.pruning.types",
    "PruningStrategy": "lexigram.ai.memory.pruning.types",
    # --- Working ---
    "ConversationBuffer": "lexigram.ai.memory.working.conversation_buffer",
    "WorkingMemoryManager": "lexigram.ai.memory.working.manager",
    "TokenBudgetAllocator": "lexigram.ai.memory.working.token_budget",
    # Internal protocols
    "MemoryIndexProtocol": "lexigram.ai.memory.protocols",
    "ConsolidationStrategyProtocol": "lexigram.ai.memory.protocols",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
