import pytest

from lexigram.contracts.multimedia.protocols import (
    ImageProvider,
    MusicProvider,
    TTSProvider,
    VideoProvider,
)
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


@pytest.mark.asyncio
async def test_register_hardcodes_all_four_siblings() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)

    for protocol in (TTSProvider, MusicProvider, VideoProvider, ImageProvider):
        assert protocol in container.bindings


@pytest.mark.asyncio
async def test_tts_accessor_generate_delegates_to_backend() -> None:
    from unittest.mock import AsyncMock

    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    fake_backend = AsyncMock()
    fake_backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="local-http", bytes_data=b"x")
    )
    provider._sub_providers["tts"]._backend = fake_backend

    accessor = provider.tts
    result = await accessor.generate(TTSRequest(text="hi"))

    assert result.is_ok()
    fake_backend.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_boot_without_optional_services_is_tolerated() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)
    await provider.boot(container)

    assert provider._storage is None
    assert provider._cache_backend is None
    assert provider._event_bus is None
    assert provider._task_manager is None
    assert provider._idempotency_manager is None


@pytest.mark.asyncio
async def test_register_tolerates_metadata_import_failure() -> None:
    from unittest.mock import patch

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    with patch(
        "lexigram.multimedia.di.provider.importlib.metadata.entry_points",
        side_effect=ImportError("no metadata"),
    ):
        await provider.register(container)

    assert set(provider._sub_providers) == {
        "tts",
        "music",
        "video",
        "image",
    }


@pytest.mark.asyncio
async def test_all_four_accessors_are_exposed_with_task_names() -> None:
    from lexigram.multimedia.accessors import SubsystemAccessor

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    for name, task_name in (
        ("tts", "tts_generation"),
        ("music", "music_generation"),
        ("image", "image_generation"),
    ):
        accessor = getattr(provider, name)
        assert isinstance(accessor, SubsystemAccessor)
        assert accessor._task_name == task_name
        assert accessor._media_type == name

    # .video is now a VideoAccessor composing generation + processing
    # SubsystemAccessors (video-processing spec).
    from lexigram.multimedia.accessors import VideoAccessor

    video = provider.video
    assert isinstance(video, VideoAccessor)
    assert video._generation._task_name == "video_generation"
    assert video._processing._task_name == "video_processing"
