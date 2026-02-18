from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from lexigram.multimedia.config import MultimediaConfig
from lexigram.multimedia.di.provider import MultimediaProvider


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
async def test_boot_registers_wrapped_handlers_with_task_provider() -> None:
    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.infra.storage.models import FileInfo
    from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol
    from lexigram.contracts.infra.tasks import TaskQueueProtocol
    from lexigram.contracts.multimedia.types import MediaAsset
    from lexigram.tasks.di.provider import TaskProvider

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    fake_store = AsyncMock()
    fake_store.upload.return_value = FileInfo(
        path="multimedia/tts/x.mp3",
        size=1,
        content_type="audio/mpeg",
        last_modified=datetime.now(UTC),
    )
    fake_store.get_url.return_value = "https://cdn.example/x.mp3"
    container.singleton(BlobStoreProtocol, fake_store)

    fake_task_provider = _FakeTaskProvider()
    container.singleton(TaskProvider, fake_task_provider)
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert provider._idempotency_manager is not None

    fake_backend = AsyncMock()
    fake_backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", bytes_data=b"x")
    )
    provider._sub_providers["tts"]._backend = fake_backend
    provider._sub_providers["tts"]._task_handler._backend = fake_backend

    assert "tts_generation" in fake_task_provider.handlers
    adapter = fake_task_provider.handlers["tts_generation"]
    result = await adapter(text="hi", voice=None, format="mp3")

    fake_store.upload.assert_awaited_once()
    assert result["uri"] == "https://cdn.example/x.mp3"
    assert result["bytes_data"] is None


@pytest.mark.asyncio
async def test_wrapped_handler_passthrough_without_storage() -> None:
    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.infra.tasks import TaskQueueProtocol
    from lexigram.contracts.multimedia.types import MediaAsset
    from lexigram.tasks.di.provider import TaskProvider

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    fake_task_provider = _FakeTaskProvider()
    container.singleton(TaskProvider, fake_task_provider)
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert provider._storage is None

    fake_backend = AsyncMock()
    fake_backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", bytes_data=b"x")
    )
    provider._sub_providers["tts"]._backend = fake_backend
    provider._sub_providers["tts"]._task_handler._backend = fake_backend

    adapter = fake_task_provider.handlers["tts_generation"]
    result = await adapter(text="hi", voice=None, format="mp3")

    # Without storage, the raw handler output passes through unchanged:
    # bytes stay inline rather than being uploaded.
    assert result["uri"] is None
    assert result["bytes_data"] == b"x"


@pytest.mark.asyncio
async def test_video_processing_and_timeline_render_tasks_registered() -> None:
    from lexigram.contracts.infra.tasks import TaskQueueProtocol
    from lexigram.tasks.di.provider import TaskProvider

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    fake_task_provider = _FakeTaskProvider()
    container.singleton(TaskProvider, fake_task_provider)
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert "video_processing" in fake_task_provider.handlers
    assert "timeline_render" in fake_task_provider.handlers


@pytest.mark.asyncio
async def test_upscale_and_interpolate_tasks_registered() -> None:
    from lexigram.contracts.infra.tasks import TaskQueueProtocol
    from lexigram.tasks.di.provider import TaskProvider

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    fake_task_provider = _FakeTaskProvider()
    container.singleton(TaskProvider, fake_task_provider)
    container.singleton(TaskQueueProtocol, AsyncMock())

    await provider.register(container)
    await provider.boot(container)

    assert "upscale_generation" in fake_task_provider.handlers
    assert "interpolate_generation" in fake_task_provider.handlers
    assert "beat_analysis" not in fake_task_provider.handlers
