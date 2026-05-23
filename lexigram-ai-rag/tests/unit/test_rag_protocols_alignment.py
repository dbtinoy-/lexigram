"""Tests locking RAG protocol imports to the canonical contracts layer.

Enforces R5 of docs/lexigram-docs/guides/contracts.md: protocols shared
across packages have one canonical definition in lexigram-contracts; the
deleted local duplicate modules (lexigram.ai.rag.protocols and
lexigram.ai.rag.reranking.protocols) must not be resurrected, and the RAG
root resolves ChunkerProtocol to the contracts layer.
"""

from __future__ import annotations

import importlib
import importlib.util

from lexigram.contracts.ai.vector import ChunkerProtocol


class TestNoLocalProtocolDuplicates:
    """The local duplicate protocol modules are gone and stay gone."""

    def test_rag_protocols_module_deleted(self) -> None:
        """lexigram.ai.rag.protocols must not exist as a local duplicate."""
        assert importlib.util.find_spec("lexigram.ai.rag.protocols") is None

    def test_reranking_protocols_module_deleted(self) -> None:
        """lexigram.ai.rag.reranking.protocols must not exist as a duplicate."""
        assert importlib.util.find_spec("lexigram.ai.rag.reranking.protocols") is None

    def test_root_no_longer_exports_dead_protocols(self) -> None:
        """RAG root no longer exports the dead Reranker/ContextCompressor names."""
        rag = importlib.import_module("lexigram.ai.rag")
        assert not hasattr(rag, "RerankerProtocol")
        assert not hasattr(rag, "ContextCompressorProtocol")


class TestRootChunkerProtocolIsCanonical:
    """RAG root ChunkerProtocol resolves to the contracts definition."""

    def test_same_object_as_contracts(self) -> None:
        """lexigram.ai.rag.ChunkerProtocol is the contracts ChunkerProtocol."""
        rag = importlib.import_module("lexigram.ai.rag")
        assert rag.ChunkerProtocol is ChunkerProtocol

    def test_lazy_map_targets_contracts(self) -> None:
        """The lazy import map points ChunkerProtocol at lexigram.contracts."""
        rag = importlib.import_module("lexigram.ai.rag")
        assert rag._LAZY_IMPORTS["ChunkerProtocol"] == "lexigram.contracts.ai.vector"
