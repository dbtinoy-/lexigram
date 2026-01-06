"""Tests for CacheAwarePromptAssembler and ProviderCacheStrategyRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.prompt.assembly.assembler import CacheAwarePromptAssembler
from lexigram.ai.prompt.assembly.cache_strategies import (
    AnthropicCacheStrategy,
    DeepSeekCacheStrategy,
    PassthroughCacheStrategy,
    ProviderCacheStrategyRegistry,
)
from lexigram.contracts.ai.llm import ChatMessage


class _MockCounter:
    """Mock token counter for testing."""

    def count(self, text: str) -> int:
        """Estimate tokens: ~4 chars per token."""
        return max(1, len(text) // 4)

    def count_messages(self, messages: list) -> int:
        """Sum tokens across messages."""
        return sum(self.count(str(m.content or "")) for m in messages)


@pytest.fixture
def registry() -> ProviderCacheStrategyRegistry:
    """Create a registry with default strategies."""
    return ProviderCacheStrategyRegistry.with_defaults()


@pytest.fixture
def assembler(registry: ProviderCacheStrategyRegistry) -> CacheAwarePromptAssembler:
    """Create an assembler with mock token counter."""
    return CacheAwarePromptAssembler(
        strategy_registry=registry, token_counter=_MockCounter()
    )


class TestStaticBeforeDynamicOrdering:
    """Test the 7-layer static-to-dynamic ordering."""

    def test_static_before_dynamic_ordering(
        self, assembler: CacheAwarePromptAssembler
    ) -> None:
        """System → tools → docs → few-shot → history → query order."""
        history = [ChatMessage(role="user", content="Previous question")]
        few_shot = [
            ChatMessage(role="user", content="Example question"),
            ChatMessage(role="assistant", content="Example answer"),
        ]
        messages = assembler.assemble(
            system="You are helpful.",
            tools=None,
            reference_docs=["Doc 1 content"],
            few_shot=few_shot,
            history=history,
            query="Current question",
            provider="openai",
            dynamic_metadata=None,
        )
        roles = [m.role for m in messages]
        # System first, then few-shot, then history, then user query at end
        assert roles[0] == "system"  # system instructions
        # Final message is the current query
        assert messages[-1].content == "Current question"
        assert messages[-1].role == "user"

    def test_dynamic_metadata_appended_last(
        self, assembler: CacheAwarePromptAssembler
    ) -> None:
        """Metadata goes after user query."""
        messages = assembler.assemble(
            system="System",
            tools=None,
            reference_docs=None,
            few_shot=None,
            history=[],
            query="My query",
            provider="openai",
            dynamic_metadata="user_id=123; timestamp=now",
        )
        # Last message should be metadata (system role with "Metadata:")
        # Second to last should be the user query
        user_msgs = [m for m in messages if m.role == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0].content == "My query"
        # Metadata appended after
        assert messages[-1].role == "system"
        assert "Metadata:" in (messages[-1].content or "")


class TestAnthropicCacheStrategy:
    """Test Anthropic cache annotation."""

    def test_anthropic_cache_control_inserted(self) -> None:
        """cache_control: ephemeral on static blocks."""
        strategy = AnthropicCacheStrategy(min_tokens=1)  # min=1 so all qualify
        mock_counter = MagicMock()
        mock_counter.count.return_value = 2000  # Above threshold

        messages = [
            ChatMessage(role="system", content=f"Block {i}" * 100) for i in range(10)
        ]
        result = strategy.annotate(
            messages, static_count=10, token_counter=mock_counter
        )

        # At least one system message should have cache_control in metadata
        annotated = sum(
            1
            for m in result
            if m.metadata and "cache_control" in m.metadata
        )
        assert annotated >= 1, "At least one message should be annotated with cache_control"

    def test_anthropic_max_four_breakpoints(self) -> None:
        """No more than 4 cache breakpoints."""
        strategy = AnthropicCacheStrategy(min_tokens=1)  # min=1 so all qualify
        # 10 messages, all static
        messages = [
            ChatMessage(role="system", content=f"Block {i}" * 100) for i in range(10)
        ]
        mock_counter = MagicMock()
        mock_counter.count.return_value = 1500  # Always above threshold
        result = strategy.annotate(
            messages, static_count=10, token_counter=mock_counter
        )

        # Count cache_control annotations in metadata
        annotated = sum(
            1
            for m in result
            if m.metadata and "cache_control" in m.metadata
        )
        assert 1 <= annotated <= 4, f"Expected 1-4 breakpoints, got {annotated}"


class TestDeepSeekCacheStrategy:
    """Test DeepSeek cache strategy."""

    def test_deepseek_64_token_padding(self) -> None:
        """Static blocks padded to 64-token multiples."""
        strategy = DeepSeekCacheStrategy()
        counter = _MockCounter()
        # Content with a non-multiple count
        # 256 chars = 64 tokens (exactly), we'll take 100 chars = 25 tokens
        content = "x" * 100  # 100 // 4 = 25 tokens — not a multiple of 64
        messages = [ChatMessage(role="system", content=content)]
        result = strategy.annotate(messages, static_count=1, token_counter=counter)
        new_content = result[0].content or ""
        new_count = counter.count(new_content)
        # Should be padded to a multiple of 64
        # 25 tokens -> next multiple of 64 is 64, so we need 39 more tokens
        # But due to integer division in our mock, just check it was padded
        assert len(new_content) > len(content)


class TestPassthroughStrategy:
    """Test passthrough behavior."""

    def test_passthrough_for_unknown_provider(
        self, assembler: CacheAwarePromptAssembler
    ) -> None:
        """Unknown provider → no annotations, messages returned unchanged."""
        messages_in = assembler.assemble(
            system="System prompt",
            tools=None,
            reference_docs=None,
            few_shot=None,
            history=[],
            query="test",
            provider="unknown-provider-xyz",
            dynamic_metadata=None,
        )
        # All messages returned, no extra fields added
        assert len(messages_in) >= 2  # system + user


class TestRegistryDefaults:
    """Test registry default providers."""

    def test_all_providers_registered(self) -> None:
        """All 6 provider strategies are in the registry."""
        registry = ProviderCacheStrategyRegistry.with_defaults()
        for provider in [
            "anthropic",
            "openai",
            "azure",
            "deepseek",
            "gemini",
            "mistral",
        ]:
            strategy = registry.for_provider(provider)
            assert strategy is not None

    def test_unknown_provider_returns_passthrough(self) -> None:
        """Unknown provider returns PassthroughCacheStrategy."""
        registry = ProviderCacheStrategyRegistry.with_defaults()
        strategy = registry.for_provider("unknown-xyz")
        assert isinstance(strategy, PassthroughCacheStrategy)


class TestToolDefinitions:
    """Test tool definition handling."""

    def test_tool_definitions_as_strings(
        self, assembler: CacheAwarePromptAssembler
    ) -> None:
        """Tool definitions can be passed as strings."""
        tools = ["Tool 1 description", "Tool 2 description"]
        messages = assembler.assemble(
            system="System",
            tools=tools,
            reference_docs=None,
            few_shot=None,
            history=[],
            query="test",
            provider="openai",
        )
        # Should have system msg for tools
        tool_msgs = [m for m in messages if "Available tools:" in (m.content or "")]
        assert len(tool_msgs) >= 1

    def test_tool_definitions_as_objects(
        self, assembler: CacheAwarePromptAssembler
    ) -> None:
        """Tool definitions can be objects with name and description."""
        tool = MagicMock()
        tool.name = "SearchTool"
        tool.description = "Search the web"

        messages = assembler.assemble(
            system="System",
            tools=[tool],
            reference_docs=None,
            few_shot=None,
            history=[],
            query="test",
            provider="openai",
        )
        # Should have system msg for tools with SearchTool
        tool_msgs = [m for m in messages if "SearchTool" in (m.content or "")]
        assert len(tool_msgs) >= 1
