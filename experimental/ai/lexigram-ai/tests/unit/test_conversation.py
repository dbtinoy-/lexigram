"""Tests for ConversationManager."""

import pytest

from lexigram.ai.llm import (
    Completion,
    ConversationConfig,
    ConversationManager,
    ConversationStats,
    Role,
)
try:
    from lexigram.ai.llm.clients.mock import MockLLMClient
except ImportError as e:
    pytest.skip(f"mock llm client unavailable: {e}", allow_module_level=True)


@pytest.fixture
def mock_client():
    """Create mock LLM client."""
    return MockLLMClient(model="gpt-4")


@pytest.fixture
def conversation_manager(mock_client):
    """Create conversation manager with mock client."""
    return ConversationManager(
        client=mock_client,
        system_prompt="You are a helpful assistant.",
        max_tokens=4096,
    )


class TestConversationConfig:
    """Test ConversationConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ConversationConfig()

        assert config.max_tokens == 4096
        assert config.reserve_tokens == 1000
        assert config.trim_strategy == "oldest"
        assert config.keep_system is True
        assert config.min_messages == 2

    def test_custom_config(self):
        """Test custom configuration."""
        config = ConversationConfig(
            max_tokens=8192,
            reserve_tokens=2000,
            trim_strategy="middle",
            keep_system=False,
            min_messages=5,
        )

        assert config.max_tokens == 8192
        assert config.reserve_tokens == 2000
        assert config.trim_strategy == "middle"
        assert config.keep_system is False
        assert config.min_messages == 5


class TestConversationStats:
    """Test ConversationStats."""

    def test_default_stats(self):
        """Test default statistics."""
        stats = ConversationStats()

        assert stats.total_messages == 0
        assert stats.total_tokens == 0
        assert stats.user_messages == 0
        assert stats.assistant_messages == 0
        assert stats.system_messages == 0
        assert stats.trimmed_count == 0
        assert stats.created_at is not None
        assert stats.last_updated is not None


class TestConversationManager:
    """Test ConversationManager."""

    def test_initialization(self, mock_client):
        """Test manager initialization."""
        manager = ConversationManager(
            client=mock_client,
            system_prompt="Test prompt",
            max_tokens=2048,
        )

        assert len(manager) == 1  # System message
        assert manager.get_token_count() == 0  # Token counting is deferred
        stats = manager.get_stats()
        assert stats.system_messages == 1

    def test_initialization_without_system_prompt(self, mock_client):
        """Test initialization without system prompt."""
        manager = ConversationManager(client=mock_client)

        assert len(manager) == 0
        assert manager.get_token_count() == 0

    @pytest.mark.asyncio
    async def test_chat(self, conversation_manager):
        """Test sending a chat message."""
        response = await conversation_manager.chat("Hello!")

        assert isinstance(response, Completion)
        assert "mock response" in response.content.lower()
        assert len(conversation_manager) == 3  # System + user + assistant
        stats = conversation_manager.get_stats()
        assert stats.user_messages == 1
        assert stats.assistant_messages == 1

    @pytest.mark.asyncio
    async def test_multiple_chat_turns(self, conversation_manager):
        """Test multiple conversation turns."""
        await conversation_manager.chat("First message")
        await conversation_manager.chat("Second message")
        await conversation_manager.chat("Third message")

        assert len(conversation_manager) == 7  # System + 3*(user+assistant)
        stats = conversation_manager.get_stats()
        assert stats.user_messages == 3
        assert stats.assistant_messages == 3

    @pytest.mark.asyncio
    async def test_add_message(self, conversation_manager):
        """Test adding messages manually."""
        await conversation_manager.add_message(Role.USER, "Test message")

        assert len(conversation_manager) == 2  # System + user
        stats = conversation_manager.get_stats()
        assert stats.user_messages == 1
        assert stats.assistant_messages == 0

    @pytest.mark.asyncio
    async def test_add_multiple_messages(self, conversation_manager):
        """Test adding multiple messages."""
        await conversation_manager.add_message(Role.USER, "User message 1")
        await conversation_manager.add_message(Role.ASSISTANT, "Assistant response 1")
        await conversation_manager.add_message(Role.USER, "User message 2")
        await conversation_manager.add_message(Role.ASSISTANT, "Assistant response 2")

        assert len(conversation_manager) == 5  # System + 4 messages
        stats = conversation_manager.get_stats()
        assert stats.user_messages == 2
        assert stats.assistant_messages == 2

    def test_get_history(self, conversation_manager):
        """Test getting conversation history."""
        history = conversation_manager.get_history()

        assert len(history) == 1  # Just system message
        assert history[0].role == Role.SYSTEM

    def test_get_history_without_system(self, conversation_manager):
        """Test getting history without system message."""
        history = conversation_manager.get_history(include_system=False)

        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, conversation_manager):
        """Test getting limited history."""
        await conversation_manager.chat("Message 1")
        await conversation_manager.chat("Message 2")
        await conversation_manager.chat("Message 3")

        history = conversation_manager.get_history(limit=2)

        assert len(history) == 2
        # Should get last 2 messages (most recent)

    def test_get_stats(self, conversation_manager):
        """Test getting conversation statistics."""
        stats = conversation_manager.get_stats()

        assert isinstance(stats, ConversationStats)
        assert stats.total_messages == 1  # System message
        assert stats.system_messages == 1

    def test_clear_history(self, conversation_manager):
        """Test clearing conversation history."""
        conversation_manager.clear_history(keep_system=True)

        assert len(conversation_manager) == 1  # System message kept
        stats = conversation_manager.get_stats()
        assert stats.system_messages == 1

    def test_clear_history_including_system(self, conversation_manager):
        """Test clearing all history including system."""
        conversation_manager.clear_history(keep_system=False)

        assert len(conversation_manager) == 0
        stats = conversation_manager.get_stats()
        assert stats.system_messages == 0
        assert stats.total_messages == 0

    def test_update_system_prompt(self, conversation_manager):
        """Test updating system prompt."""
        original_len = len(conversation_manager)

        conversation_manager.update_system_prompt("New system prompt")

        assert len(conversation_manager) == original_len
        history = conversation_manager.get_history()
        assert history[0].role == Role.SYSTEM
        assert history[0].content == "New system prompt"

    def test_get_token_count(self, conversation_manager):
        """Test getting token count."""
        token_count = conversation_manager.get_token_count()

        assert isinstance(token_count, int)
        assert token_count == 0  # Token counting is deferred

    def test_get_available_tokens(self, conversation_manager):
        """Test getting available tokens."""
        available = conversation_manager.get_available_tokens()

        assert isinstance(available, int)
        assert available > 0

    @pytest.mark.asyncio
    async def test_token_counting_updates(self, conversation_manager):
        """Test that token counts update correctly."""
        initial_tokens = conversation_manager.get_token_count()

        await conversation_manager.chat("Hello!")

        new_tokens = conversation_manager.get_token_count()
        assert new_tokens > initial_tokens

    def test_export_history(self, conversation_manager):
        """Test exporting conversation history."""
        data = conversation_manager.export_history()

        assert "messages" in data
        assert "stats" in data
        assert "config" in data
        assert "metadata" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) == 1  # System message

    @pytest.mark.asyncio
    async def test_export_with_conversation(self, conversation_manager):
        """Test exporting after conversation."""
        await conversation_manager.chat("Test message")

        data = conversation_manager.export_history()

        assert len(data["messages"]) == 3  # System + user + assistant
        assert data["stats"]["user_messages"] == 1
        assert data["stats"]["assistant_messages"] == 1

    def test_from_history(self, mock_client):
        """Test creating manager from exported history."""
        # Create and export
        manager1 = ConversationManager(
            client=mock_client,
            system_prompt="Test prompt",
            metadata={"session": "123"},
        )
        data = manager1.export_history()

        # Import
        manager2 = ConversationManager.from_history(mock_client, data)

        assert len(manager2) == len(manager1)
        assert manager2.get_token_count() == manager1.get_token_count()

    @pytest.mark.asyncio
    async def test_from_history_with_messages(self, mock_client):
        """Test importing history with messages."""
        # Create conversation
        manager1 = ConversationManager(
            client=mock_client,
            system_prompt="Test prompt",
        )
        await manager1.chat("Test message")
        data = manager1.export_history()

        # Import
        manager2 = ConversationManager.from_history(mock_client, data)

        assert len(manager2) == 3  # System + user + assistant
        history = manager2.get_history()
        assert history[0].content == "Test prompt"
        assert history[1].content == "Test message"

    @pytest.mark.asyncio
    async def test_context_trimming_oldest(self, mock_client):
        """Test trimming oldest messages."""
        manager = ConversationManager(
            client=mock_client,
            system_prompt="System",
            max_tokens=200,  # Small window to trigger trimming
            reserve_tokens=50,
            trim_strategy="oldest",
        )

        # Add many messages to trigger trimming
        for i in range(20):
            await manager.chat(f"Message {i}")

        stats = manager.get_stats()
        assert stats.trimmed_count > 0
        # Should have fewer than 20 conversation pairs
        assert len(manager) < 41  # System + 20*(user+assistant)

    @pytest.mark.asyncio
    async def test_context_trimming_middle(self, mock_client):
        """Test trimming middle messages."""
        manager = ConversationManager(
            client=mock_client,
            system_prompt="System",
            max_tokens=200,  # Small window to trigger trimming
            reserve_tokens=50,
            trim_strategy="middle",
        )

        # Add many messages
        for i in range(20):
            await manager.chat(f"Message {i}")

        stats = manager.get_stats()
        assert stats.trimmed_count > 0

    def test_repr(self, conversation_manager):
        """Test string representation."""
        repr_str = repr(conversation_manager)

        assert "ConversationManager" in repr_str
        assert "messages=" in repr_str
        assert "tokens=" in repr_str
        assert "available=" in repr_str

    def test_len(self, conversation_manager):
        """Test length operator."""
        length = len(conversation_manager)

        assert length == 1  # System message
        assert isinstance(length, int)

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, mock_client):
        """Test that metadata is preserved."""
        metadata = {"session_id": "abc123", "user_id": "user-456"}
        manager = ConversationManager(
            client=mock_client,
            system_prompt="Test",
            metadata=metadata,
        )

        exported = manager.export_history()
        assert exported["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_conversation_flow(self, mock_client):
        """Test complete conversation flow."""
        manager = ConversationManager(
            client=mock_client,
            system_prompt="You are helpful.",
        )

        # Initial state
        assert len(manager) == 1
        assert manager.get_stats().user_messages == 0

        # First exchange
        await manager.chat("Hello")
        assert len(manager) == 3
        assert manager.get_stats().user_messages == 1
        assert manager.get_stats().assistant_messages == 1

        # Second exchange
        await manager.chat("How are you?")
        assert len(manager) == 5
        assert manager.get_stats().user_messages == 2

        # Export and reimport
        data = manager.export_history()
        manager2 = ConversationManager.from_history(mock_client, data)

        # Continue conversation
        await manager2.chat("Goodbye")
        assert len(manager2) == 7
        assert manager2.get_stats().user_messages == 3
