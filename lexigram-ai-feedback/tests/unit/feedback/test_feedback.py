"""Unit tests for lexigram.ai.feedback — collector, middleware, processor registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.ai.feedback.processors.processor_registry import (
    FeedbackProcessorRegistry,
    RatingFeedbackProcessor,
    TextFeedbackProcessor,
)
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.storage.protocols import (
    FeedbackStoreProtocol,
    FeedbackSummary,
)
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
from lexigram.ai.feedback.middleware import FeedbackContext, FeedbackMiddleware
from lexigram.result import Result
from lexigram.result import Ok


class DummyFeedbackStore(FeedbackStoreProtocol):
    def __init__(self) -> None:
        self.items: list[FeedbackItem] = []

    async def save(self, feedback: FeedbackItem) -> Result[str, Exception]:
        self.items.append(feedback)
        return Ok(feedback.id)

    async def find_by_session(self, session_id: str) -> list[FeedbackItem]:
        filtered = [item for item in self.items if item.context.get("session_id") == session_id]
        return sorted(filtered, key=lambda item: item.created_at, reverse=True)

    async def find_by_type(
        self,
        feedback_type: FeedbackType,
        *,
        limit: int = 100,
    ) -> list[FeedbackItem]:
        filtered = [item for item in self.items if item.feedback_type == feedback_type]
        sorted_items = sorted(filtered, key=lambda item: item.created_at, reverse=True)
        return sorted_items[:limit]

    async def aggregate(self, *, window_hours: int = 24) -> FeedbackSummary:
        total = len(self.items)
        ratings = [
            item.value for item in self.items if item.feedback_type == FeedbackType.RATING
        ]
        average_rating = sum(ratings) / len(ratings) if ratings else None
        count_by_type: dict[str, int] = {}
        for item in self.items:
            count_by_type[item.feedback_type.value] = count_by_type.get(
                item.feedback_type.value, 0
            ) + 1
        return FeedbackSummary(
            total_count=total,
            average_rating=average_rating,
            count_by_type=count_by_type,
        )


# ── FeedbackType ─────────────────────────────────────────────────────


class TestFeedbackType:
    def test_values(self) -> None:
        assert FeedbackType.RATING.value == "rating"
        assert FeedbackType.TEXT.value == "text"
        assert FeedbackType.CORRECTION.value == "correction"
        assert FeedbackType.LABEL.value == "label"


# ── FeedbackItem ─────────────────────────────────────────────────────


class TestFeedbackItem:
    def test_creation(self) -> None:
        item = FeedbackItem(feedback_type=FeedbackType.RATING, value=5)
        assert item.type == FeedbackType.RATING
        assert item.value == 5
        assert item.context == {}
        assert item.metadata == {}
        assert item.id  # auto-generated

    def test_with_context(self) -> None:
        item = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value="great answer",
            context={"model": "gpt-4"},
            metadata={"session": "abc"},
        )
        assert item.context["model"] == "gpt-4"
        assert item.metadata["session"] == "abc"

    def test_custom_id(self) -> None:
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=4,
            id="custom-123",
        )
        assert item.id == "custom-123"

    def test_to_dict(self) -> None:
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=5,
            id="test-id",
        )
        d = item.to_dict()
        assert d["id"] == "test-id"
        assert d["type"] == "rating"
        assert d["value"] == 5
        assert "created_at" in d

    def test_repr(self) -> None:
        item = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value="good",
            id="r1",
        )
        assert "r1" in repr(item)
        assert "text" in repr(item)


# ── FeedbackCollector ────────────────────────────────────────────────


class TestFeedbackCollector:
    @pytest.fixture
    def collector(self) -> FeedbackCollector:
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_collect_rating(self, collector: FeedbackCollector) -> None:
        fid = await collector.collect_rating(rating=5, context={"model": "gpt-4"})
        assert fid
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_collect_text(self, collector: FeedbackCollector) -> None:
        fid = await collector.collect_text(text="amazing response")
        assert fid
        items = await collector.get_feedback()
        assert items[0].type == FeedbackType.TEXT
        assert items[0].value == "amazing response"

    @pytest.mark.asyncio
    async def test_collect_correction(self, collector: FeedbackCollector) -> None:
        fid = await collector.collect_correction(
            original="wrong", corrected="right"
        )
        assert fid
        items = await collector.get_feedback()
        assert items[0].value == {"original": "wrong", "corrected": "right"}

    @pytest.mark.asyncio
    async def test_collect_label(self, collector: FeedbackCollector) -> None:
        fid = await collector.collect_label(label="positive", input_data="text")
        assert fid
        items = await collector.get_feedback()
        assert items[0].value == {"label": "positive", "input": "text"}

    @pytest.mark.asyncio
    async def test_get_feedback_filter_by_type(
        self, collector: FeedbackCollector
    ) -> None:
        await collector.collect_rating(rating=5)
        await collector.collect_text(text="nice")
        await collector.collect_rating(rating=3)
        ratings = await collector.get_feedback(feedback_type=FeedbackType.RATING)
        assert len(ratings) == 2
        texts = await collector.get_feedback(feedback_type=FeedbackType.TEXT)
        assert len(texts) == 1

    @pytest.mark.asyncio
    async def test_get_feedback_limit(self, collector: FeedbackCollector) -> None:
        for i in range(5):
            await collector.collect_rating(rating=i)
        items = await collector.get_feedback(limit=2)
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_get_feedback_dict(self, collector: FeedbackCollector) -> None:
        await collector.collect_rating(rating=4)
        dicts = await collector.get_feedback_dict()
        assert len(dicts) == 1
        assert isinstance(dicts[0], dict)
        assert dicts[0]["type"] == "rating"

    @pytest.mark.asyncio
    async def test_get_feedback_uses_storage(self) -> None:
        storage = DummyFeedbackStore()
        collector = FeedbackCollector(storage=storage)
        await collector.collect_text(text="persistent")
        items = await collector.get_feedback()
        assert len(items) == 1
        assert items[0].value == "persistent"
        dicts = await collector.get_feedback_dict()
        assert dicts[0]["value"] == "persistent"

    @pytest.mark.asyncio
    async def test_get_feedback_limit_with_storage(self) -> None:
        storage = DummyFeedbackStore()
        collector = FeedbackCollector(storage=storage)
        for i in range(5):
            await collector.collect_rating(rating=i)
        items = await collector.get_feedback(limit=2)
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_clear(self, collector: FeedbackCollector) -> None:
        await collector.collect_rating(rating=5)
        assert len(collector) == 1
        collector.clear()
        assert len(collector) == 0

    def test_repr(self, collector: FeedbackCollector) -> None:
        assert "items=0" in repr(collector)


# ── FeedbackMiddleware ───────────────────────────────────────────────


class TestFeedbackMiddleware:
    @pytest.fixture
    def middleware(self) -> FeedbackMiddleware:
        collector = FeedbackCollector()
        return FeedbackMiddleware(collector=collector)

    def test_creation(self, middleware: FeedbackMiddleware) -> None:
        assert middleware.capture_inputs is True
        assert middleware.capture_outputs is True

    def test_creation_custom_flags(self) -> None:
        mw = FeedbackMiddleware(
            collector=FeedbackCollector(),
            capture_inputs=False,
            capture_outputs=False,
        )
        assert mw.capture_inputs is False
        assert mw.capture_outputs is False

    @pytest.mark.asyncio
    async def test_call_passes_through(self, middleware: FeedbackMiddleware) -> None:
        context = MagicMock()
        context.body = "test input"
        context.user_id = "u1"
        context.session_id = "s1"
        context.path = "/predict"
        context.request_id = "req-1"

        async def next_handler(ctx: Any) -> str:
            return "result"

        response = await middleware(context, next_handler)
        assert response == "result"

    def test_repr(self, middleware: FeedbackMiddleware) -> None:
        assert "FeedbackMiddleware" in repr(middleware)


# ── FeedbackContext ──────────────────────────────────────────────────


class TestFeedbackContext:
    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        collector = FeedbackCollector()
        async with FeedbackContext(collector, operation="predict") as ctx:
            ctx.set_input("hello")
            ctx.set_result("world")
            assert ctx._context_id is not None

    @pytest.mark.asyncio
    async def test_context_captures_error(self) -> None:
        collector = FeedbackCollector()
        with pytest.raises(ValueError):
            async with FeedbackContext(collector, operation="predict"):
                raise ValueError("test error")

    def test_repr(self) -> None:
        ctx = FeedbackContext(FeedbackCollector(), operation="test")
        assert "test" in repr(ctx)


# ── FeedbackProcessorRegistry ───────────────────────────────────────


class TestFeedbackProcessorRegistry:
    def test_with_defaults(self) -> None:
        registry = FeedbackProcessorRegistry.with_defaults()
        assert FeedbackType.RATING in registry._processors
        assert FeedbackType.TEXT in registry._processors
        assert FeedbackType.CORRECTION in registry._processors
        assert FeedbackType.LABEL in registry._processors

    def test_register_custom(self) -> None:
        registry = FeedbackProcessorRegistry()
        processor = MagicMock()
        registry.register("custom_type", processor)
        assert "custom_type" in registry._processors

    @pytest.mark.asyncio
    async def test_process_rating(self) -> None:
        registry = FeedbackProcessorRegistry.with_defaults()
        collector = FeedbackCollector()
        fid = await registry.process(
            FeedbackType.RATING, 5, {"ctx": "test"}, collector
        )
        assert fid
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_process_text(self) -> None:
        registry = FeedbackProcessorRegistry.with_defaults()
        collector = FeedbackCollector()
        fid = await registry.process(
            FeedbackType.TEXT, "great", {"ctx": "test"}, collector
        )
        assert fid

    @pytest.mark.asyncio
    async def test_process_unknown_type_raises(self) -> None:
        registry = FeedbackProcessorRegistry()
        with pytest.raises(ValueError, match="No processor"):
            await registry.process("unknown", "val", {}, FeedbackCollector())
