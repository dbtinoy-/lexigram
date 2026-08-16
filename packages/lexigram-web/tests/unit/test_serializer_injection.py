"""Tests for constructor injection in serializers and directives."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.web.serialization.serializers import ResponseSerializer
from lexigram.graphql.security.rate_limit import UnifiedRateLimiter


class TestResponseSerializerInjection:
    """Test that ResponseSerializer accepts dependencies via constructor."""

    def test_response_serializer_accepts_command_bus_in_constructor(self) -> None:
        """ResponseSerializer must accept CommandBusProtocol via constructor."""
        # Mock the CommandBusProtocol
        command_bus = MagicMock(name="command_bus")

        # Create serializer with explicit dependency
        serializer = ResponseSerializer(command_bus=command_bus)

        # Verify dependency is stored
        assert serializer.command_bus is command_bus

    def test_response_serializer_accepts_query_bus_in_constructor(self) -> None:
        """ResponseSerializer must accept QueryBusProtocol via constructor."""
        # Mock the QueryBusProtocol
        query_bus = MagicMock(name="query_bus")

        # Create serializer with explicit dependency
        serializer = ResponseSerializer(query_bus=query_bus)

        # Verify dependency is stored
        assert serializer.query_bus is query_bus

    def test_response_serializer_accepts_mapper_in_constructor(self) -> None:
        """ResponseSerializer must accept ObjectMapperProtocol via constructor."""
        # Mock the ObjectMapperProtocol
        mapper = MagicMock(name="mapper")

        # Create serializer with explicit dependency
        serializer = ResponseSerializer(mapper=mapper)

        # Verify dependency is stored
        assert serializer.mapper is mapper


class TestUnifiedRateLimiterInjection:
    """Test that UnifiedRateLimiter uses constructor injection properly."""

    def test_unified_rate_limiter_accepts_container_in_constructor(self) -> None:
        """UnifiedRateLimiter can be created with no arguments (default: allow all)."""
        # When no web_rate_limiter is injected the limiter allows every request.
        rate_limiter = UnifiedRateLimiter()
        assert rate_limiter._web_rate_limiter is None

    @pytest.mark.asyncio
    async def test_unified_rate_limiter_uses_injected_web_rate_limiter(
        self,
    ) -> None:
        """UnifiedRateLimiter should use injected web rate limiter if provided."""
        # Mock the web rate limiter
        web_rate_limiter = MagicMock(name="web_rate_limiter")
        web_rate_limiter.check_rate_limit = AsyncMock(return_value=None)

        # Create rate limiter with injected web_rate_limiter
        rate_limiter = UnifiedRateLimiter(web_rate_limiter=web_rate_limiter)

        # Verify web_rate_limiter is stored
        assert rate_limiter._web_rate_limiter is web_rate_limiter

        # Create a mock context
        context = MagicMock()
        context.raw_request = MagicMock()

        # Check rate limit - should use injected limiter
        result = await rate_limiter.is_allowed(context)

        # Verify the injected limiter was called
        web_rate_limiter.check_rate_limit.assert_awaited_once()
        assert result is True
