from unittest.mock import AsyncMock

import pytest

from lexigram.contracts.infra.tasks import TaskQueueProtocol
from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.compose_accessor import ComposeAccessor
from lexigram.multimedia.di.provider import MultimediaProvider
from lexigram.multimedia.video_accessor import VideoAccessor
from lexigram.tasks.di.provider import TaskProvider


class _FakeContainer:
    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(self, key: object, value: object) -> None:
        self.bindings[key] = value

    async def resolve(self, key: object) -> object:
        if key not in self.bindings:
            raise LookupError(key)
        return self.bindings[key]


class _FakeTaskProvider:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}

    def register_handler(self, task_name: str, handler: object) -> None:
        self.handlers[task_name] = handler


@pytest.mark.asyncio
async def test_video_property_returns_video_accessor() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    container.singleton(TaskProvider, _FakeTaskProvider())
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert isinstance(provider.video, VideoAccessor)


@pytest.mark.asyncio
async def test_compose_property_returns_compose_accessor() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    container.singleton(TaskProvider, _FakeTaskProvider())
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert isinstance(provider.compose, ComposeAccessor)
