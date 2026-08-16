"""Focused runtime hook tests for lexigram-queue."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.contracts.core import HookRegistryProtocol
from lexigram.contracts.queue.types import BusMessage
from lexigram.queue.backends.memory import InMemoryQueue
from lexigram.queue.config import NamedQueueConfig, QueueConfig
from lexigram.queue.di.provider import QueueProvider
from lexigram.queue.hooks import MessageConsumedHook, MessagePublishedHook


class _RecordingHooks:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def register_action(
        self,
        hook_name: str,
        handler: Any,
        priority: int = 100,
        *,
        once: bool = False,
    ) -> None:
        raise NotImplementedError

    def register_filter(
        self,
        hook_name: str,
        handler: Any,
        priority: int = 100,
        *,
        once: bool = False,
    ) -> None:
        raise NotImplementedError

    def unregister_action(self, hook_name: str, handler: Any) -> bool:
        raise NotImplementedError

    def unregister_filter(self, hook_name: str, handler: Any) -> bool:
        raise NotImplementedError

    async def call_action(self, hook_name: str, **kwargs: Any) -> None:
        self.calls.append((hook_name, kwargs["payload"]))

    async def apply_filter(self, hook_name: str, value: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def has_action(self, hook_name: str) -> bool:
        raise NotImplementedError

    def has_filter(self, hook_name: str) -> bool:
        raise NotImplementedError

    def clear(self, hook_name: str | None = None) -> None:
        raise NotImplementedError


def _payloads_for(hooks: _RecordingHooks, hook_name: str) -> list[object]:
    return [payload for name, payload in hooks.calls if name == hook_name]


class _PublishedPayload:
    pass


class _ConsumedPayload:
    pass


class _HookingContainer:
    def __init__(self, hooks: HookRegistryProtocol | None) -> None:
        self._hooks = hooks

    def singleton(
        self,
        service_type: object,
        instance: object | None = None,
        *,
        name: str | None = None,
        factory: object | None = None,
        validate: bool = True,
    ) -> None:
        _ = (service_type, instance, name, factory, validate)

    async def resolve_optional(self, protocol: type[object]) -> object | None:
        from lexigram.contracts.core import HookRegistryProtocol
        from lexigram.contracts.observability.tracing import TracerProtocol

        if protocol is HookRegistryProtocol:
            return self._hooks
        if protocol is TracerProtocol:
            return None
        return None

    async def resolve(self, protocol: type[object]) -> object | None:
        _ = protocol
        return None


@pytest.mark.asyncio
async def test_in_memory_publish_emits_message_published_hook() -> None:
    hooks = _RecordingHooks()
    queue = InMemoryQueue()
    queue.set_hook_registry(hooks)
    await queue.connect()

    message = BusMessage(topic="orders", payload=_PublishedPayload())

    await queue.publish("orders", message)

    assert _payloads_for(hooks, "message.published") == [
        MessagePublishedHook(queue_name="orders", message_type="_PublishedPayload")
    ]

    await queue.close()


@pytest.mark.asyncio
async def test_in_memory_successful_consume_emits_message_consumed_hook() -> None:
    hooks = _RecordingHooks()
    queue = InMemoryQueue()
    queue.set_hook_registry(hooks)
    await queue.connect()

    received: list[BusMessage] = []

    async def handler(message: BusMessage) -> None:
        received.append(message)

    await queue.subscribe("orders", handler)
    await queue.publish("orders", BusMessage(topic="orders", payload=_ConsumedPayload()))
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert _payloads_for(hooks, "message.consumed") == [
        MessageConsumedHook(queue_name="orders", message_type="_ConsumedPayload")
    ]

    await queue.close()


@pytest.mark.asyncio
async def test_in_memory_failed_consume_does_not_emit_message_consumed_hook() -> None:
    hooks = _RecordingHooks()
    queue = InMemoryQueue()
    queue.set_hook_registry(hooks)
    await queue.connect()

    async def handler(message: BusMessage) -> None:
        _ = message
        raise RuntimeError("boom")

    await queue.subscribe("orders", handler)
    await queue.publish("orders", BusMessage(topic="orders", payload=_ConsumedPayload()))
    await asyncio.sleep(0.05)

    assert _payloads_for(hooks, "message.consumed") == []

    await queue.close()


@pytest.mark.asyncio
async def test_queue_provider_boot_wires_optional_hook_registry_into_backends() -> None:
    hooks = _RecordingHooks()
    provider = QueueProvider(
        config=QueueConfig(
            backends=[NamedQueueConfig(name="memory", driver="memory", primary=True)]
        )
    )

    await provider.register(_HookingContainer(hooks))
    await provider.boot(_HookingContainer(hooks))

    assert len(provider._queue_services) == 1
    assert provider._queue_services[0][1]._hooks is hooks

    await provider.shutdown()
