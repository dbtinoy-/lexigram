import pytest

from lexigram.contracts.multimedia.protocols import (
    BeatAnalysisProvider,
    ImageProvider,
    InterpolationProvider,
    MusicProvider,
    TTSProvider,
    UpscaleProvider,
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
async def test_register_hardcodes_all_seven_siblings() -> None:
    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()

    await provider.register(container)

    for protocol in (
        TTSProvider,
        MusicProvider,
        VideoProvider,
        ImageProvider,
        UpscaleProvider,
        InterpolationProvider,
        BeatAnalysisProvider,
    ):
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
async def test_upscale_accessor_generate_delegates_to_backend_upscale() -> None:
    from unittest.mock import AsyncMock

    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.multimedia.types import MediaAsset, UpscaleRequest

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    fake_backend = AsyncMock()
    fake_backend.upscale.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="real-esrgan", bytes_data=b"x")
    )
    provider._sub_providers["upscale"]._backend = fake_backend

    accessor = provider.upscale
    result = await accessor.generate(
        UpscaleRequest(
            asset=MediaAsset(mime_type="image/png", provider="openai", bytes_data=b"y")
        )
    )

    assert result.is_ok()
    fake_backend.upscale.assert_awaited_once()


@pytest.mark.asyncio
async def test_interpolate_accessor_generate_delegates_to_backend_interpolate() -> None:
    from unittest.mock import AsyncMock

    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.multimedia.types import InterpolationRequest, MediaAsset

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    fake_backend = AsyncMock()
    fake_backend.interpolate.return_value = Ok(
        MediaAsset(mime_type="image/png", provider="rife", bytes_data=b"x")
    )
    provider._sub_providers["interpolate"]._backend = fake_backend

    frame = MediaAsset(mime_type="image/png", provider="openai", bytes_data=b"y")
    accessor = provider.interpolate
    result = await accessor.generate(InterpolationRequest(frame_a=frame, frame_b=frame))

    assert result.is_ok()
    fake_backend.interpolate.assert_awaited_once()


@pytest.mark.asyncio
async def test_beat_accessor_analyze_delegates_to_backend() -> None:
    from unittest.mock import AsyncMock

    from lexigram.contracts.core.result import Ok
    from lexigram.contracts.multimedia.types import (
        BeatAnalysisRequest,
        BeatAnalysisResult,
        MediaAsset,
    )

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    fake_backend = AsyncMock()
    fake_backend.analyze.return_value = Ok(
        BeatAnalysisResult(tempo_bpm=120.0, beat_timestamps=[0.0, 0.5, 1.0])
    )
    provider._sub_providers["beat"]._backend = fake_backend

    asset = MediaAsset(mime_type="audio/wav", provider="local-http", bytes_data=b"y")
    accessor = provider.beat
    result = await accessor.analyze(BeatAnalysisRequest(asset=asset))

    assert result.is_ok()
    assert result.unwrap().tempo_bpm == 120.0
    fake_backend.analyze.assert_awaited_once()


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
        "upscale",
        "interpolate",
        "beat",
    }


@pytest.mark.asyncio
async def test_all_subsystem_accessors_are_exposed_with_task_names() -> None:
    from lexigram.multimedia.accessors import SubsystemAccessor

    provider = MultimediaProvider(config=MultimediaConfig())
    container = _FakeContainer()
    await provider.register(container)

    for name, task_name in (
        ("tts", "tts_generation"),
        ("music", "music_generation"),
        ("image", "image_generation"),
        ("upscale", "upscale_generation"),
        ("interpolate", "interpolate_generation"),
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

    # .beat is a dedicated BeatAccessor — analyze() returns a
    # BeatAnalysisResult, not a MediaAsset, so it doesn't fit SubsystemAccessor.
    from lexigram.multimedia.accessors import BeatAccessor

    beat = provider.beat
    assert isinstance(beat, BeatAccessor)
