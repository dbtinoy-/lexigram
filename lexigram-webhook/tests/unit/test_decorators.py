"""Tests for webhook decorators."""

from __future__ import annotations

import pytest

from lexigram.webhook.decorators import webhook_event


@pytest.mark.asyncio
async def test_webhook_event_decorator() -> None:
    """Test webhook_event decorator attaches metadata."""
    
    @webhook_event("test.event", description="A test event")
    async def my_function(x: int) -> int:
        return x + 1
    
    # Check metadata
    assert getattr(my_function, "__webhook_event__") is True
    assert getattr(my_function, "__webhook_event_type__") == "test.event"
    assert getattr(my_function, "__webhook_event_description__") == "A test event"
    
    # Check execution
    result = await my_function(10)
    assert result == 11
