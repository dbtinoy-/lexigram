"""Tests for RAG chunking types."""

from lexigram.ai.rag.chunking.types import Chunk, ChunkingStrategy
from lexigram.contracts.ai.chunks import Chunk as SharedChunk


class TestChunkingStrategy:
    """Tests for ChunkingStrategy enum."""

    def test_chunking_strategy_values(self) -> None:
        """Test ChunkingStrategy enum values."""
        assert ChunkingStrategy.FIXED_SIZE.value == "fixed_size"
        assert ChunkingStrategy.RECURSIVE.value == "recursive"
        assert ChunkingStrategy.SEMANTIC.value == "semantic"
        assert ChunkingStrategy.SLIDING_WINDOW.value == "sliding_window"
        assert ChunkingStrategy.TOKEN.value == "token"

    def test_chunking_strategy_members(self) -> None:
        """Test ChunkingStrategy has expected members."""
        members = list(ChunkingStrategy)
        assert len(members) == 5


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_chunk_creation(self) -> None:
        """Test Chunk creation."""
        chunk = Chunk(
            text="This is a test chunk",
            source="document-1",
            chunk_index=0,
        )
        assert chunk.text == "This is a test chunk"
        assert chunk.source == "document-1"
        assert chunk.chunk_index == 0

    def test_chunk_length(self) -> None:
        """Test Chunk length."""
        chunk = Chunk(text="Hello World", chunk_index=0)
        assert len(chunk) == 11

    def test_chunk_defaults(self) -> None:
        """Test Chunk default values."""
        chunk = Chunk(text="test", chunk_index=0)
        assert chunk.source == "unknown"
        assert chunk.start_index is None
        assert chunk.end_index is None
        assert chunk.metadata == {}

    def test_chunk_is_shared_ai_chunk(self) -> None:
        """Chunk should extend the shared AI chunk contract."""
        chunk = Chunk(text="test", source="doc", chunk_index=0)

        assert isinstance(chunk, SharedChunk)
