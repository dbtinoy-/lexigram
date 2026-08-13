"""Context pruning for memory entries — trims to fit token budgets.

Provides pluggable scoring strategies (recency, hybrid) and a greedy
pruning algorithm to keep high-value entries within a token limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ai.memory.pruning.pruner import DynamicContextPruner
    from lexigram.ai.memory.pruning.scorer import (
        HybridScorerImpl,
        RecencyScorerImpl,
        RelevanceScorerProtocol,
    )
    from lexigram.ai.memory.pruning.types import PruningResult, PruningStrategy

_LAZY_IMPORTS: dict[str, str] = {
    "DynamicContextPruner": "lexigram.ai.memory.pruning.pruner",
    "HybridScorerImpl": "lexigram.ai.memory.pruning.scorer",
    "RecencyScorerImpl": "lexigram.ai.memory.pruning.scorer",
    "RelevanceScorerProtocol": "lexigram.ai.memory.pruning.scorer",
    "PruningResult": "lexigram.ai.memory.pruning.types",
    "PruningStrategy": "lexigram.ai.memory.pruning.types",
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
