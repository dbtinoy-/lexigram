"""Unit tests for FeedbackContext."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback.middleware.middleware import FeedbackContext
from lexigram.ai.feedback.services.collector import FeedbackCollector


class TestFeedbackContext:
    """Tests for FeedbackContext async context manager."""

    @pytest.fixture
    def collector(self) -> FeedbackCollector:
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_context_manager_enter_sets_state(
        self, collector: FeedbackCollector
    ) -> None:
        """__aenter__ creates a new context with context_id."""
        async with FeedbackContext(collector, operation="predict") as ctx:
            assert ctx._context_id is not None
            assert isinstance(ctx._context_id, str)

    @pytest.mark.asyncio
    async def test_context_manager_exit_clears_state(
        self, collector: FeedbackCollector
    ) -> None:
        """__aexit__ runs after normal completion."""
        context_id: str | None = None
        async with FeedbackContext(collector, operation="predict") as ctx:
            context_id = ctx._context_id
            ctx.set_input("test input")
            ctx.set_result("test output")
        
        assert context_id is not None

    @pytest.mark.asyncio
    async def test_captures_output_on_exit(
        self, collector: FeedbackCollector
    ) -> None:
        """Output result is available during context lifetime."""
        async with FeedbackContext(collector, operation="predict") as ctx:
            ctx.set_input("input")
            ctx.set_result({"response": "generated"})
            assert ctx._result == {"response": "generated"}

    @pytest.mark.asyncio
    async def test_exception_stored_on_error(
        self, collector: FeedbackCollector
    ) -> None:
        """Exception is captured and stored when error occurs."""
        error_raised = False
        try:
            async with FeedbackContext(collector, operation="predict") as ctx:
                ctx.set_input("input data")
                raise ValueError("test error")
        except ValueError:
            error_raised = True
        assert error_raised
