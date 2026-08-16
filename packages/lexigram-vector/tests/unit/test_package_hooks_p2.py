"""P2 hook surface import verification for lexigram-vector."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_vector_hooks_root_module_exists() -> None:
    import lexigram.vector
    from lexigram.vector.hooks import (
        VectorIndexedHook,
        VectorSearchedHook,
    )

    assert VectorIndexedHook.__name__ == "VectorIndexedHook"
    assert VectorSearchedHook.__name__ == "VectorSearchedHook"
    assert lexigram.vector.VectorIndexedHook is VectorIndexedHook
    assert lexigram.vector.VectorSearchedHook is VectorSearchedHook
    assert "VectorIndexedHook" in lexigram.vector.__all__
    assert "VectorSearchedHook" in lexigram.vector.__all__


def test_vector_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.vector.hooks import VectorIndexedHook, VectorSearchedHook

    indexed = VectorIndexedHook(collection="documents", document_id="doc1")
    searched = VectorSearchedHook(collection="documents", result_count=10)

    assert is_dataclass(indexed)
    assert is_dataclass(searched)

    with pytest.raises(TypeError):
        VectorIndexedHook("documents", "doc1")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        indexed.collection = "other"  # type: ignore[misc]
