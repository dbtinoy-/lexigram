"""P2 hook surface import verification for lexigram-ai-memory."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_memory_hooks_root_module_exists() -> None:
    import lexigram.ai.memory
    from lexigram.ai.memory.hooks import (
        MemoryConsolidatedHook,
        MemoryRetrievedHook,
        MemoryWrittenHook,
    )

    assert MemoryWrittenHook.__name__ == "MemoryWrittenHook"
    assert MemoryRetrievedHook.__name__ == "MemoryRetrievedHook"
    assert MemoryConsolidatedHook.__name__ == "MemoryConsolidatedHook"
    assert lexigram.ai.memory.MemoryWrittenHook is MemoryWrittenHook
    assert lexigram.ai.memory.MemoryRetrievedHook is MemoryRetrievedHook
    assert lexigram.ai.memory.MemoryConsolidatedHook is MemoryConsolidatedHook


def test_memory_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.memory.hooks import (
        MemoryConsolidatedHook,
        MemoryRetrievedHook,
        MemoryWrittenHook,
    )

    written = MemoryWrittenHook(tier="working", backend="in_memory")
    retrieved = MemoryRetrievedHook(tier="episodic", result_count=5)
    consolidated = MemoryConsolidatedHook(strategy="deduplication")

    assert is_dataclass(written)
    assert is_dataclass(retrieved)
    assert is_dataclass(consolidated)

    with pytest.raises(TypeError):
        MemoryWrittenHook("working", "in_memory")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        written.tier = "semantic"  # type: ignore[misc]

    with pytest.raises(TypeError):
        MemoryConsolidatedHook("deduplication")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        consolidated.strategy = "recency_decay"  # type: ignore[misc]
