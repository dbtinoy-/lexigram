"""Test suite for QueueAdminContributor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError, WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.admin.contributor import QueueAdminContributor
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler
from lexigram.queue.core.dlq import DeadLetterQueue
from lexigram.result import Err, Ok


class TestQueueAdminContributor:
    """Test suite for QueueAdminContributor."""

    @pytest.fixture
    def contributor(self) -> QueueAdminContributor:
        """Create contributor with mocked handlers returning WidgetContent."""
        depth_handler = MagicMock()
        depth_handler.get_data = AsyncMock(
            return_value=Ok(
                StatContent(
                    stats=(
                        Stat(label="Queue", value="default"),
                        Stat(label="Depth", value="42"),
                        Stat(label="Max", value="100"),
                    )
                )
            )
        )
        lag_handler = MagicMock()
        lag_handler.get_data = AsyncMock(
            return_value=Ok(
                StatContent(
                    stats=(
                        Stat(label="Lag (messages)", value="10"),
                        Stat(label="Lag (seconds)", value="~2.5s"),
                    )
                )
            )
        )
        failed_handler = MagicMock()
        failed_handler.get_data = AsyncMock(
            return_value=Ok(
                StatContent(
                    stats=(
                        Stat(label="Failed messages", value="0", tone=Tone.SUCCESS),
                    )
                )
            )
        )

        contrib = QueueAdminContributor()
        contrib._handlers = {
            "queue_depth": depth_handler,
            "consumer_lag": lag_handler,
            "failed_messages": failed_handler,
        }
        return contrib

    @pytest.fixture
    async def booted_contributor(self) -> QueueAdminContributor:
        """Create a contributor with zero-arg constructor and mock container boot."""
        from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler
        from lexigram.queue.admin.handlers.failed_messages import (
            FailedMessagesWidgetHandler,
        )
        from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler

        container = MagicMock()
        resolve_map = {
            QueueDepthWidgetHandler: object(),
            ConsumerLagWidgetHandler: object(),
            FailedMessagesWidgetHandler: object(),
        }
        container.resolve = AsyncMock(side_effect=resolve_map.get)
        contrib = QueueAdminContributor()
        await contrib.on_admin_boot(container)
        return contrib

    def test_contributor_metadata(self, booted_contributor: QueueAdminContributor) -> None:
        """Test contributor name and display properties."""
        assert booted_contributor.name == "queue"
        assert booted_contributor.display_name == "Queue"
        assert booted_contributor.group == "infrastructure"
        assert booted_contributor.priority == 35

    def test_get_dashboard_widgets(
        self, booted_contributor: QueueAdminContributor
    ) -> None:
        """Test that contributor provides exactly 3 widgets."""
        widgets = booted_contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        widget_names = {w.name for w in widgets}
        assert widget_names == {"queue_depth", "consumer_lag", "failed_messages"}

    def test_get_navigation_items(
        self, booted_contributor: QueueAdminContributor
    ) -> None:
        """Test that contributor provides navigation items."""
        items = booted_contributor.get_navigation_items()
        assert len(items) > 0
        assert any(item.label == "Queue" for item in items)

    def test_get_health_definitions(
        self, booted_contributor: QueueAdminContributor
    ) -> None:
        """Test that contributor provides health checks."""
        defs = booted_contributor.get_health_definitions()
        assert len(defs) > 0
        assert any("queue" in d.name for d in defs)

    def test_get_actions(self, booted_contributor: QueueAdminContributor) -> None:
        """Test that contributor provides actions."""
        actions = booted_contributor.get_actions()
        assert len(actions) > 0

    @pytest.mark.asyncio
    async def test_execute_action_retry_failed_dispatches(self) -> None:
        """execute_action dispatches retry_failed and re-publishes the DLQ."""
        dlq = DeadLetterQueue()
        message = BusMessage(topic="orders", payload={"id": 1})
        await dlq.push(message, "boom")
        queue = MagicMock()
        queue.publish = AsyncMock()

        def _resolve_optional(service_type: type[object]) -> object | None:
            if service_type is DeadLetterQueue:
                return dlq
            if service_type is QueueProtocol:
                return queue
            return None

        container = MagicMock()
        resolve_map = {
            QueueDepthWidgetHandler: object(),
            ConsumerLagWidgetHandler: object(),
            FailedMessagesWidgetHandler: object(),
        }
        container.resolve = AsyncMock(side_effect=resolve_map.get)
        container.resolve_optional = AsyncMock(side_effect=_resolve_optional)
        contributor = QueueAdminContributor()
        await contributor.on_admin_boot(container)

        result = await contributor.execute_action("retry_failed", {})

        assert result["ok"] is True
        assert result["echo"] == {"retried": 1, "failed": 0}
        queue.publish.assert_awaited_once_with("orders", message)
        assert dlq.size == 0

    @pytest.mark.asyncio
    async def test_execute_action_unknown_action_raises_lookup_error(
        self, booted_contributor: QueueAdminContributor
    ) -> None:
        """Unknown action names raise LookupError."""
        with pytest.raises(LookupError):
            await booted_contributor.execute_action("explode", {})

    def test_on_admin_boot_resolves_action_handlers(
        self, booted_contributor: QueueAdminContributor
    ) -> None:
        """on_admin_boot resolves one handler per declared action."""
        assert set(booted_contributor._action_handlers) == {"retry_failed"}
        handler = booted_contributor._action_handlers["retry_failed"]
        assert callable(handler)

    @pytest.mark.asyncio
    async def test_render_widget_queue_depth(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test rendering queue_depth widget."""
        params = WidgetParams()
        result = await contributor.render_widget("queue_depth", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        assert vm.content.stats[1].value == "42"
        assert vm.content.stats[1].tone is Tone.DEFAULT

    @pytest.mark.asyncio
    async def test_render_widget_consumer_lag(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test rendering consumer_lag widget."""
        params = WidgetParams()
        result = await contributor.render_widget("consumer_lag", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        assert vm.content.stats[0].value == "10"

    @pytest.mark.asyncio
    async def test_render_widget_failed_messages(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test rendering failed_messages widget."""
        params = WidgetParams()
        result = await contributor.render_widget("failed_messages", params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert isinstance(vm.content, StatContent)
        assert vm.content.stats[0].value == "0"

    @pytest.mark.asyncio
    async def test_render_widget_unknown_widget(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test rendering an unknown widget returns WidgetNotFoundError."""
        params = WidgetParams()
        result = await contributor.render_widget("unknown_widget", params)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)

    @pytest.mark.asyncio
    async def test_render_widget_handler_error(
        self, contributor: QueueAdminContributor
    ) -> None:
        """Test that handler errors are propagated."""
        error = AdminError("Test error")
        handler = contributor._handlers["queue_depth"]
        assert handler is not None
        handler.get_data = AsyncMock(return_value=Err(error))  # type: ignore[attr-defined]

        params = WidgetParams()
        result = await contributor.render_widget("queue_depth", params)

        assert result.is_err()
        assert result.unwrap_err() is error

    @pytest.mark.asyncio
    async def test_render_widget_no_handlers_returns_not_found(self) -> None:
        """Test that missing handler registry returns not found."""
        contributor = QueueAdminContributor()

        params = WidgetParams()
        result = await contributor.render_widget("queue_depth", params)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)


__all__ = ["TestQueueAdminContributor"]
