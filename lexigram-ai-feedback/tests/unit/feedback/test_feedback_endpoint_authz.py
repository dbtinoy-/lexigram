"""Unit tests for the optional authorization callback on the feedback endpoint."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback.exceptions import FeedbackAuthorizationError
from lexigram.ai.feedback.middleware import (
    FeedbackAuthContext,
    FeedbackMiddleware,
)
from lexigram.ai.feedback.services.collector import FeedbackCollector


class TestFeedbackEndpointAuthz:
    """authorize gates FeedbackMiddleware.create_feedback_endpoint()."""

    @pytest.fixture
    def collector(self) -> FeedbackCollector:
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_unset_callback_behaves_unchanged(
        self, collector: FeedbackCollector
    ) -> None:
        """Default (authorize=None) accepts submissions with no check."""
        middleware = FeedbackMiddleware(collector=collector)
        handler = middleware.create_feedback_endpoint()
        response = await handler("ctx-1", "rating", 5)
        assert response["status"] == "success"
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_callback_returning_false_rejects(
        self, collector: FeedbackCollector
    ) -> None:
        """A False decision raises and nothing is collected."""
        middleware = FeedbackMiddleware(collector=collector, authorize=lambda _: False)
        handler = middleware.create_feedback_endpoint()
        with pytest.raises(FeedbackAuthorizationError):
            await handler("ctx-1", "rating", 5)
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_callback_returning_true_allows(
        self, collector: FeedbackCollector
    ) -> None:
        """A True decision flows through to the existing handler logic."""
        middleware = FeedbackMiddleware(collector=collector, authorize=lambda _: True)
        handler = middleware.create_feedback_endpoint()
        response = await handler("ctx-1", "rating", 5)
        assert response["status"] == "success"
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_callback_receives_context_id_and_kwargs(
        self, collector: FeedbackCollector
    ) -> None:
        """Callback sees the context_id and the handler's trailing kwargs."""
        seen: list[FeedbackAuthContext] = []

        def authorize(ctx: FeedbackAuthContext) -> bool:
            seen.append(ctx)
            return True

        middleware = FeedbackMiddleware(collector=collector, authorize=authorize)
        handler = middleware.create_feedback_endpoint()
        await handler("ctx-42", "rating", 5, user_id="u-7")
        assert len(seen) == 1
        assert seen[0].context_id == "ctx-42"
        assert seen[0].metadata["user_id"] == "u-7"

    @pytest.mark.asyncio
    async def test_async_callback_awaited(self, collector: FeedbackCollector) -> None:
        """Awaitable results are awaited; False still rejects."""

        async def authorize(ctx: FeedbackAuthContext) -> bool:
            return ctx.context_id == "allowed"

        middleware = FeedbackMiddleware(collector=collector, authorize=authorize)
        handler = middleware.create_feedback_endpoint()
        await handler("allowed", "rating", 5)
        assert len(collector) == 1
        with pytest.raises(FeedbackAuthorizationError):
            await handler("denied", "rating", 5)
        assert len(collector) == 1
