"""Tests for RAG synthesis types."""

from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    OutputFormat,
    SynthesisStrategy,
)
from lexigram.contracts.ai.chunks import ContextChunk as SharedContextChunk


class TestSynthesisStrategy:
    """Tests for SynthesisStrategy enum."""

    def test_synthesis_strategy_values(self) -> None:
        """Test SynthesisStrategy enum values."""
        assert SynthesisStrategy.DIRECT.value == "direct"
        assert SynthesisStrategy.EXTRACTIVE.value == "extractive"
        assert SynthesisStrategy.ABSTRACTIVE.value == "abstractive"
        assert SynthesisStrategy.HYBRID.value == "hybrid"

    def test_synthesis_strategy_members(self) -> None:
        """Test SynthesisStrategy has expected members."""
        members = list(SynthesisStrategy)
        assert len(members) == 4


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self) -> None:
        """Test OutputFormat enum values."""
        assert OutputFormat.PLAIN_TEXT.value == "plain_text"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.HTML.value == "html"

    def test_output_format_members(self) -> None:
        """Test OutputFormat has expected members."""
        members = list(OutputFormat)
        assert len(members) == 4


class TestContextChunk:
    """Tests for shared context chunk usage."""

    def test_context_chunk_is_shared_ai_context_chunk(self) -> None:
        """ContextChunk should extend the shared AI context chunk contract."""
        chunk = ContextChunk(text="snippet", source="doc-1", score=0.8, rank=1)

        assert isinstance(chunk, SharedContextChunk)
