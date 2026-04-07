"""P2 hook surface import verification for lexigram-ai-rag."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_rag_hooks_root_module_exists() -> None:
    import lexigram.ai.rag
    from lexigram.ai.rag.hooks import (
        RAGAnswerSynthesizedHook,
        RAGDocumentsRetrievedHook,
        RAGPipelineStartedHook,
    )

    assert RAGPipelineStartedHook.__name__ == "RAGPipelineStartedHook"
    assert RAGDocumentsRetrievedHook.__name__ == "RAGDocumentsRetrievedHook"
    assert RAGAnswerSynthesizedHook.__name__ == "RAGAnswerSynthesizedHook"
    assert lexigram.ai.rag.RAGPipelineStartedHook is RAGPipelineStartedHook
    assert lexigram.ai.rag.RAGDocumentsRetrievedHook is RAGDocumentsRetrievedHook
    assert lexigram.ai.rag.RAGAnswerSynthesizedHook is RAGAnswerSynthesizedHook


def test_rag_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.ai.rag.hooks import (
        RAGAnswerSynthesizedHook,
        RAGDocumentsRetrievedHook,
        RAGPipelineStartedHook,
    )

    started = RAGPipelineStartedHook(pipeline_name="default")
    retrieved = RAGDocumentsRetrievedHook(chunk_count=8)
    synthesized = RAGAnswerSynthesizedHook(pipeline_name="default")

    assert is_dataclass(started)
    assert is_dataclass(retrieved)
    assert is_dataclass(synthesized)

    with pytest.raises(TypeError):
        RAGPipelineStartedHook("default")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        started.pipeline_name = "other"  # type: ignore[misc]

    with pytest.raises(TypeError):
        RAGAnswerSynthesizedHook("default")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        synthesized.pipeline_name = "other"  # type: ignore[misc]
