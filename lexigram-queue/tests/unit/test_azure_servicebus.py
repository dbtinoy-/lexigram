"""Tests for AzureServiceBusQueue backend."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.queue.types import BusMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    """Return (mock_client, mock_sender, mock_receiver)."""
    mock_sender = AsyncMock()
    mock_sender.__aenter__ = AsyncMock(return_value=mock_sender)
    mock_sender.__aexit__ = AsyncMock(return_value=None)
    mock_sender.send_messages = AsyncMock()

    mock_receiver = AsyncMock()
    mock_receiver.__aenter__ = AsyncMock(return_value=mock_receiver)
    mock_receiver.__aexit__ = AsyncMock(return_value=None)
    mock_receiver.receive_messages = AsyncMock(return_value=[])
    mock_receiver.peek_messages = AsyncMock(return_value=[])
    mock_receiver.complete_message = AsyncMock()
    mock_receiver.abandon_message = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get_queue_sender = MagicMock(return_value=mock_sender)
    mock_client.get_queue_receiver = MagicMock(return_value=mock_receiver)

    return mock_client, mock_sender, mock_receiver


def _make_queue(**kwargs: Any) -> Any:
    from lexigram.queue.backends.azure_servicebus import AzureServiceBusQueue

    return AzureServiceBusQueue(
        connection_str="Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=k;SharedAccessKey=x",
        queue_name="test-queue",
        **kwargs,
    )


def _inject_fake_azure_module(mock_client_cls: Any) -> None:
    """Inject a minimal fake azure.servicebus.aio into sys.modules."""
    fake_aio = types.ModuleType("azure.servicebus.aio")
    fake_aio.ServiceBusClient = mock_client_cls  # type: ignore[attr-defined]
    fake_sb = types.ModuleType("azure.servicebus")
    fake_sb.ServiceBusMessage = MagicMock()  # type: ignore[attr-defined]
    fake_az = types.ModuleType("azure")
    sys.modules.setdefault("azure", fake_az)
    sys.modules["azure.servicebus"] = fake_sb
    sys.modules["azure.servicebus.aio"] = fake_aio


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAzureServiceBusQueue:
    """Unit tests for AzureServiceBusQueue."""

    # ------------------------------------------------------------------
    # connect / close
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_raises_import_error_without_sdk(self) -> None:
        """connect() raises ImportError when azure-servicebus is absent."""
        queue = _make_queue()
        # Temporarily hide the azure modules. Use None sentinels (not just
        # removals) so the import fails even when the SDK is installed and
        # would otherwise be re-imported from disk.
        saved = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k.startswith("azure.servicebus")
        }
        for _mod in ("azure", "azure.servicebus", "azure.servicebus.aio"):
            if _mod not in sys.modules:
                sys.modules[_mod] = None
        try:
            with pytest.raises(ImportError, match="azure-servicebus"):
                await queue.connect()
        finally:
            for _mod in ("azure", "azure.servicebus", "azure.servicebus.aio"):
                if sys.modules.get(_mod) is None:
                    sys.modules.pop(_mod)
            sys.modules.update(saved)

    @pytest.mark.asyncio
    async def test_connect_stores_client(self) -> None:
        """connect() should store the ServiceBusClient on _client."""
        queue = _make_queue()
        mock_client, _, _ = _make_mock_client()

        mock_cls = MagicMock()
        mock_cls.from_connection_string = MagicMock(return_value=mock_client)
        _inject_fake_azure_module(mock_cls)

        await queue.connect()

        assert queue._client is mock_client

    @pytest.mark.asyncio
    async def test_close_cancels_tasks_and_closes_client(self) -> None:
        """close() should cancel background tasks and exit the client context."""
        queue = _make_queue()
        mock_client, _, _ = _make_mock_client()
        queue._client = mock_client

        done_task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
        await asyncio.sleep(0)
        queue._tasks.add(done_task)

        await queue.close()

        mock_client.__aexit__.assert_awaited_once()
        assert queue._client is None

    # ------------------------------------------------------------------
    # publish
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_publish_raises_when_not_connected(self) -> None:
        """publish() raises RuntimeError when client is None."""
        queue = _make_queue()
        with pytest.raises(RuntimeError, match="not connected"):
            await queue.publish("t", BusMessage(topic="t", payload={"x": 1}))

    @pytest.mark.asyncio
    async def test_publish_sends_json_envelope(self) -> None:
        """publish() serialises BusMessage as a JSON envelope."""
        queue = _make_queue()
        mock_client, mock_sender, _ = _make_mock_client()
        queue._client = mock_client

        # Capture the AzMsg constructor argument
        az_msg_cls = MagicMock()
        fake_sb = types.ModuleType("azure.servicebus")
        fake_sb.ServiceBusMessage = az_msg_cls  # type: ignore[attr-defined]
        sys.modules["azure.servicebus"] = fake_sb

        msg = BusMessage(topic="jobs", payload={"task": "run"})
        await queue.publish("jobs", msg)

        mock_sender.send_messages.assert_awaited_once()
        body_str: str = az_msg_cls.call_args[0][0]
        data = json.loads(body_str)
        assert data["topic"] == "jobs"
        assert data["payload"] == {"task": "run"}

    @pytest.mark.asyncio
    async def test_publish_emits_hook(self) -> None:
        """publish() fires message.published hook with correct queue_name."""
        queue = _make_queue()
        mock_client, _, _ = _make_mock_client()
        queue._client = mock_client

        mock_hooks = AsyncMock()
        queue.set_hook_registry(mock_hooks)

        fake_sb = types.ModuleType("azure.servicebus")
        fake_sb.ServiceBusMessage = MagicMock()  # type: ignore[attr-defined]
        sys.modules["azure.servicebus"] = fake_sb

        await queue.publish("jobs", BusMessage(topic="jobs", payload="hi"))

        mock_hooks.call_action.assert_awaited_once()
        _, call_kwargs = mock_hooks.call_action.call_args
        hook = call_kwargs["payload"]
        assert hook.queue_name == "jobs"

    @pytest.mark.asyncio
    async def test_publish_injects_trace_headers(self) -> None:
        """publish() injects W3C traceparent into the message envelope headers."""
        from lexigram.testing.fakes import FakeTracer

        queue = _make_queue()
        mock_client, _, _ = _make_mock_client()
        queue._client = mock_client
        queue.set_tracer(FakeTracer())

        captured_props: dict[str, Any] = {}

        def capture_msg(body: str, application_properties: dict[str, Any] | None = None) -> MagicMock:
            captured_props.update(application_properties or {})
            return MagicMock()

        fake_sb = types.ModuleType("azure.servicebus")
        fake_sb.ServiceBusMessage = capture_msg  # type: ignore[attr-defined]
        sys.modules["azure.servicebus"] = fake_sb

        await queue.publish("t", BusMessage(topic="t", payload="x"))

        assert "traceparent" in captured_props

    # ------------------------------------------------------------------
    # subscribe
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self) -> None:
        """subscribe() raises RuntimeError when client is None."""
        queue = _make_queue()

        async def handler(msg: BusMessage) -> None:
            pass

        with pytest.raises(RuntimeError, match="not connected"):
            await queue.subscribe("t", handler)

    @pytest.mark.asyncio
    async def test_subscribe_delivers_message_to_handler(self) -> None:
        """Poll loop deserialises the JSON envelope and calls the handler."""
        queue = _make_queue(max_wait_time=0.1)
        mock_client, _, mock_receiver = _make_mock_client()
        queue._client = mock_client

        envelope = json.dumps(
            {"id": "m1", "topic": "jobs", "payload": {"k": "v"}, "headers": {}}
        )
        delivered = asyncio.Event()
        received: list[BusMessage] = []
        call_count = 0

        async def fake_receive(
            max_message_count: int = 10, max_wait_time: float = 5.0
        ) -> list[Any]:
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return [envelope]
            await asyncio.sleep(0.1)  # prevent tight loop on empty queue
            return []

        mock_receiver.receive_messages = fake_receive

        async def handler(msg: BusMessage) -> None:
            received.append(msg)
            delivered.set()

        await queue.subscribe("jobs", handler)
        await asyncio.wait_for(delivered.wait(), timeout=5.0)

        assert len(received) == 1
        assert received[0].payload == {"k": "v"}

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_acks_on_success(self) -> None:
        """Poll loop calls complete_message after the handler succeeds."""
        queue = _make_queue(max_wait_time=0.1)
        mock_client, _, mock_receiver = _make_mock_client()
        queue._client = mock_client

        raw_msg = json.dumps(
            {"id": "m1", "topic": "t", "payload": "data", "headers": {}}
        )
        acked = asyncio.Event()
        ack_calls: list[Any] = []

        async def do_complete(m: Any) -> None:
            ack_calls.append(m)
            acked.set()

        mock_receiver.complete_message = AsyncMock(side_effect=do_complete)

        call_count = 0

        async def fake_receive(
            max_message_count: int = 10, max_wait_time: float = 5.0
        ) -> list[Any]:
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return [raw_msg]
            await asyncio.sleep(0.1)
            return []

        mock_receiver.receive_messages = fake_receive

        async def handler(msg: BusMessage) -> None:
            pass

        await queue.subscribe("t", handler)
        await asyncio.wait_for(acked.wait(), timeout=5.0)

        assert len(ack_calls) == 1
        assert ack_calls[0] == raw_msg

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_abandons_on_handler_failure(self) -> None:
        """Poll loop calls abandon_message when the handler raises."""
        queue = _make_queue(max_wait_time=0.1)
        mock_client, _, mock_receiver = _make_mock_client()
        queue._client = mock_client

        raw_msg = json.dumps(
            {"id": "m2", "topic": "t", "payload": "x", "headers": {}}
        )
        abandoned = asyncio.Event()
        abandon_calls: list[Any] = []

        async def do_abandon(m: Any) -> None:
            abandon_calls.append(m)
            abandoned.set()

        mock_receiver.abandon_message = AsyncMock(side_effect=do_abandon)

        call_count = 0

        async def fake_receive(
            max_message_count: int = 10, max_wait_time: float = 5.0
        ) -> list[Any]:
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return [raw_msg]
            await asyncio.sleep(0.1)
            return []

        mock_receiver.receive_messages = fake_receive

        async def bad_handler(msg: BusMessage) -> None:
            raise ValueError("deliberate failure")

        await queue.subscribe("t", bad_handler)
        await asyncio.wait_for(abandoned.wait(), timeout=5.0)

        assert len(abandon_calls) == 1

        for task in list(queue._tasks):
            task.cancel()

    @pytest.mark.asyncio
    async def test_subscribe_emits_consumed_hook(self) -> None:
        """Poll loop emits message.consumed hook after successful handling."""
        queue = _make_queue(max_wait_time=0.1)
        mock_client, _, mock_receiver = _make_mock_client()
        queue._client = mock_client

        mock_hooks = AsyncMock()
        queue.set_hook_registry(mock_hooks)

        envelope = json.dumps(
            {"id": "h1", "topic": "t", "payload": "p", "headers": {}}
        )
        hook_fired = asyncio.Event()
        original_call_action = mock_hooks.call_action

        async def tracking_call_action(name: str, **kwargs: Any) -> None:
            await original_call_action(name, **kwargs)
            if name == "message.consumed":
                hook_fired.set()

        mock_hooks.call_action = tracking_call_action

        call_count = 0

        async def fake_receive(
            max_message_count: int = 10, max_wait_time: float = 5.0
        ) -> list[Any]:
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return [envelope]
            await asyncio.sleep(0.1)
            return []

        mock_receiver.receive_messages = fake_receive

        async def handler(msg: BusMessage) -> None:
            pass

        await queue.subscribe("t", handler)
        await asyncio.wait_for(hook_fired.wait(), timeout=5.0)

        for task in list(queue._tasks):
            task.cancel()

    # ------------------------------------------------------------------
    # health_check
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_not_connected(self) -> None:
        """health_check() returns UNHEALTHY when client is None."""
        queue = _make_queue()
        result = await queue.health_check()
        assert result.status == HealthStatus.UNHEALTHY
        assert "not connected" in result.details["error"]

    @pytest.mark.asyncio
    async def test_health_check_healthy_on_successful_peek(self) -> None:
        """health_check() returns HEALTHY when peek_messages succeeds."""
        queue = _make_queue()
        mock_client, _, _ = _make_mock_client()
        queue._client = mock_client

        result = await queue.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.details["queue_name"] == "test-queue"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self) -> None:
        """health_check() returns UNHEALTHY when peek_messages raises."""
        queue = _make_queue()
        mock_client, _, mock_receiver = _make_mock_client()
        mock_receiver.peek_messages = AsyncMock(
            side_effect=ConnectionError("cannot connect")
        )
        queue._client = mock_client

        result = await queue.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "cannot connect" in result.details["error"]

    # ------------------------------------------------------------------
    # Wiring helpers
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_set_tracer_stores_and_clears(self) -> None:
        """set_tracer(tracer) stores; set_tracer(None) clears."""
        from lexigram.testing.fakes import FakeTracer

        queue = _make_queue()
        tracer = FakeTracer()
        queue.set_tracer(tracer)
        assert queue._tracer is tracer
        queue.set_tracer(None)
        assert queue._tracer is None

    @pytest.mark.asyncio
    async def test_set_hook_registry_stores(self) -> None:
        """set_hook_registry stores the provided registry."""
        queue = _make_queue()
        mock_hooks = AsyncMock()
        queue.set_hook_registry(mock_hooks)
        assert queue._hooks is mock_hooks

    @pytest.mark.asyncio
    async def test_decrement_in_flight_floors_at_zero(self) -> None:
        """_decrement_in_flight must never go below 0."""
        queue = _make_queue()
        queue._in_flight = 0
        queue._decrement_in_flight()
        assert queue._in_flight == 0


__all__: list[str] = []
