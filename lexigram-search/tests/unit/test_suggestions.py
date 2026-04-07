"""Tests for SuggestionEngine."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.query.suggestions import (
    Suggestion,
    SuggestionEngine,
    SuggestionResult,
)


class TestSuggestion:
    """Tests for Suggestion dataclass."""

    def test_suggestion_creation(self) -> None:
        """Test creating a Suggestion instance."""
        suggestion = Suggestion(
            text="python",
            score=0.95,
            frequency=150,
            type="completion",
        )
        assert suggestion.text == "python"
        assert suggestion.score == 0.95
        assert suggestion.frequency == 150
        assert suggestion.type == "completion"

    def test_suggestion_with_defaults(self) -> None:
        """Test creating a Suggestion with default values."""
        suggestion = Suggestion(text="python")
        assert suggestion.text == "python"
        assert suggestion.score == 1.0
        assert suggestion.frequency == 0
        assert suggestion.type == "completion"

    def test_suggestion_ordering_by_score(self) -> None:
        """Test that suggestions are ordered by score descending."""
        suggestions = [
            Suggestion(text="java", score=0.5, frequency=10),
            Suggestion(text="python", score=0.95, frequency=100),
            Suggestion(text="ruby", score=0.7, frequency=20),
        ]
        sorted_suggestions = sorted(suggestions, key=lambda s: s.score, reverse=True)
        assert [s.text for s in sorted_suggestions] == ["python", "ruby", "java"]


class TestSuggestionResult:
    """Tests for SuggestionResult dataclass."""

    def test_suggestion_result_creation(self) -> None:
        """Test creating a SuggestionResult instance."""
        suggestions = [
            Suggestion(text="python", score=0.95, frequency=100),
            Suggestion(text="python3", score=0.85, frequency=50),
        ]
        result = SuggestionResult(
            suggestions=suggestions,
            query="py",
            did_you_mean="python",
        )
        assert result.query == "py"
        assert len(result.suggestions) == 2
        assert result.did_you_mean == "python"

    def test_suggestion_result_empty(self) -> None:
        """Test creating an empty SuggestionResult."""
        result = SuggestionResult(query="xyz", suggestions=[])
        assert result.query == "xyz"
        assert result.suggestions == []
        assert result.did_you_mean is None


class TestSuggestionEngine:
    """Tests for SuggestionEngine."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock search engine."""
        engine = MagicMock()
        return engine

    @pytest.fixture
    def engine(self, mock_engine: MagicMock) -> SuggestionEngine:
        """Create a SuggestionEngine instance."""
        return SuggestionEngine(
            search_engine=mock_engine,
            index_name="test_index",
            min_score=0.5,
            max_suggestions=5,
        )

    def test_engine_initialization(self, engine: SuggestionEngine) -> None:
        """Test SuggestionEngine initialization."""
        assert engine._index_name == "test_index"
        assert engine._min_score == 0.5
        assert engine._max_suggestions == 5

    @pytest.mark.asyncio
    async def test_suggest_short_prefix(self, engine: SuggestionEngine) -> None:
        """Test that suggestions are empty for short prefixes."""
        result = await engine.suggest("a")
        assert result.suggestions == []
        assert result.query == "a"

    @pytest.mark.asyncio
    async def test_suggest_empty_prefix(self, engine: SuggestionEngine) -> None:
        """Test that suggestions are empty for empty prefix."""
        result = await engine.suggest("")
        assert result.suggestions == []
        assert result.query == ""

    @pytest.mark.asyncio
    async def test_suggest_with_results(
        self, engine: SuggestionEngine, mock_engine: MagicMock,
    ) -> None:
        """Test getting suggestions with results."""
        # Mock search results
        mock_result = MagicMock()
        mock_result.documents = [
            {"name": "python", "id": "1"},
            {"name": "python3", "id": "2"},
            {"name": "pythonic", "id": "3"},
        ]
        mock_result.total = 3
        mock_engine.search = AsyncMock(return_value=mock_result)

        result = await engine.suggest("py")

        assert result.query == "py"
        assert len(result.suggestions) == 3
        texts = [s.text for s in result.suggestions]
        assert "python" in texts

    @pytest.mark.asyncio
    async def test_suggest_filters_by_field(
        self, engine: SuggestionEngine, mock_engine: MagicMock,
    ) -> None:
        """Test that suggestions are filtered by specified field."""
        mock_result = MagicMock()
        mock_result.documents = [
            {"title": "python book", "id": "1"},
            {"title": "python tutorial", "id": "2"},
        ]
        mock_result.total = 2
        mock_engine.search = AsyncMock(return_value=mock_result)

        result = await engine.suggest("py", field="title")

        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_did_you_mean_short_query(
        self, engine: SuggestionEngine,
    ) -> None:
        """Test did-you-mean returns empty for short queries."""
        result = await engine.did_you_mean("py")
        assert result.suggestions == []
        assert result.query == "py"

    @pytest.mark.asyncio
    async def test_did_you_mean_empty_query(
        self, engine: SuggestionEngine,
    ) -> None:
        """Test did-you-mean returns empty for empty query."""
        result = await engine.did_you_mean("")
        assert result.suggestions == []
        assert result.query == ""

    @pytest.mark.asyncio
    async def test_did_you_mean_with_correction(
        self, engine: SuggestionEngine, mock_engine: MagicMock,
    ) -> None:
        """Test did-you-mean returns correction when found."""
        # First call returns empty (the typo), second call returns results (the correction)
        mock_result_empty = MagicMock()
        mock_result_empty.total = 0

        mock_result_found = MagicMock()
        mock_result_found.total = 1

        mock_engine.search = AsyncMock(side_effect=[
            mock_result_empty,  # "laptap" returns nothing
            mock_result_found,  # "laptop" returns results
        ])

        result = await engine.did_you_mean("laptap")

        assert result.query == "laptap"
        assert result.did_you_mean is not None

    @pytest.mark.asyncio
    async def test_did_you_mean_no_correction_found(
        self, engine: SuggestionEngine, mock_engine: MagicMock,
    ) -> None:
        """Test did-you-mean returns empty when no correction found."""
        mock_result = MagicMock()
        mock_result.total = 0
        mock_engine.search = AsyncMock(return_value=mock_result)

        result = await engine.did_you_mean("xyzabc")

        assert result.suggestions == []
        assert result.did_you_mean is None


class TestCorrectionGeneration:
    """Tests for correction generation logic."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock search engine."""
        engine = MagicMock()
        return engine

    @pytest.fixture
    def engine(self, mock_engine: MagicMock) -> SuggestionEngine:
        """Create a SuggestionEngine instance."""
        return SuggestionEngine(search_engine=mock_engine)

    def test_remove_duplicate_chars(self, engine: SuggestionEngine) -> None:
        """Test removing duplicate characters."""
        assert engine._remove_duplicate_chars("laptopp") == "laptop"
        assert engine._remove_duplicate_chars("python") == "python"
        assert engine._remove_duplicate_chars("aa bb cc") == "a b c"
        assert engine._remove_duplicate_chars("") == ""

    def test_get_keyboard_neighbors(self, engine: SuggestionEngine) -> None:
        """Test keyboard neighbor lookup."""
        neighbors = engine._get_keyboard_neighbors("a")
        assert "q" in neighbors
        assert "w" in neighbors
        assert "s" in neighbors

    def test_generate_corrections_dedup(self, engine: SuggestionEngine) -> None:
        """Test correction generation removes duplicates."""
        corrections = engine._generate_corrections("laptopp", 5)
        assert "laptop" in corrections

    def test_generate_corrections_keyboard(
        self, engine: SuggestionEngine,
    ) -> None:
        """Test correction generation tries keyboard neighbors."""
        corrections = engine._generate_corrections("laptip", 5)
        # Should try neighbors like "laptop"
        assert len(corrections) > 0

    def test_generate_corrections_transposition(
        self, engine: SuggestionEngine,
    ) -> None:
        """Test correction generation tries transposition."""
        corrections = engine._generate_corrections("lapotp", 5)
        # Should try swapping adjacent characters
        assert len(corrections) > 0
