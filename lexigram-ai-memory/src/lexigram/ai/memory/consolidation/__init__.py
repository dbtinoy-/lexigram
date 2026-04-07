"""Memory consolidation — strategies and scheduler for compacting old entries."""

from __future__ import annotations

from lexigram.ai.memory.consolidation.consolidator import MemoryConsolidator
from lexigram.ai.memory.consolidation.scheduler import ConsolidationScheduler
from lexigram.ai.memory.consolidation.strategies import (
    AccessFrequencyStrategy,
    DeduplicationStrategy,
    RecencyDecayStrategy,
    TimeDecayStrategy,
)

__all__ = [
    "AccessFrequencyStrategy",
    "ConsolidationScheduler",
    "DeduplicationStrategy",
    "MemoryConsolidator",
    "RecencyDecayStrategy",
    "TimeDecayStrategy",
]
